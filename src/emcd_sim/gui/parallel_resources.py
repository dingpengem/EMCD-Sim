"""Native thread introspection, scoped control and detector-worker policy."""
import ctypes,hashlib,os,platform,sys,threading
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
import numpy as np

IMPLICATED_DLL_SHA256='63c857e738469261263c764a36be9436ebdeaa272e340a828f42047a97131080'
MAX_WORKERS=4
_blas_control_lock=threading.RLock()


def _blas_runtimes():
    # Import the LAPACK consumer before taking the execution snapshot. NumPy
    # and SciPy wheels can load DIFFERENT OpenBLAS runtimes. Rediscover on each
    # request rather than caching the first library seen by a GUI preview.
    import scipy.linalg
    import scipy
    runtimes=[]
    for package in (np,scipy):
        folder=Path(package.__file__).resolve().parent.parent/(package.__name__+'.libs')
        for path in sorted(set(folder.glob('*openblas*.dll'))|set(folder.glob('*openblas*.so*'))):
            library=ctypes.CDLL(str(path))
            for prefix,suffix in ((p,s) for p in ('scipy_openblas_','openblas_') for s in ('64_','','_')):
                try:
                    get=getattr(library,prefix+'get_num_threads'+suffix)
                    set_threads=getattr(library,prefix+'set_num_threads'+suffix)
                    parallel=getattr(library,prefix+'get_parallel'+suffix)
                    config=getattr(library,prefix+'get_config'+suffix)
                except AttributeError:continue
                get.argtypes=[];get.restype=ctypes.c_int
                set_threads.argtypes=[ctypes.c_int];set_threads.restype=None
                parallel.argtypes=[];parallel.restype=ctypes.c_int
                config.argtypes=[];config.restype=ctypes.c_char_p
                runtimes.append((get,set_threads,dict(library=str(path),configuration=config().decode(),
                    threads=int(get()),parallel=int(parallel()))))
                break
            else:
                raise ValueError('Cannot verify OpenBLAS control API: '+str(path))
    return runtimes


@contextmanager
def calculation_blas_guard(cancelled=None):
    """Limit both wheel runtimes for the entire calculation; restore after join.

    OpenBLAS normal threading uses process-wide setters. Serialize requests
    while limits are active. OpenMP/unknown implementations are not asserted
    controllable through this API. Nested detector dispatch is reentrant.
    """
    from ..cancellation import check_cancelled
    while not _blas_control_lock.acquire(timeout=.05):check_cancelled(cancelled)
    previous=[]
    try:
        check_cancelled(cancelled)
        runtimes=_blas_runtimes()
        if not runtimes or any(info['parallel'] not in (0,1) for _,_,info in runtimes):
            raise ValueError('Automatic single-thread BLAS control unavailable for this numerical runtime.')
        for get,set_threads,info in runtimes:
            previous.append((get,set_threads,int(get())))
            set_threads(1)
            if int(get())!=1:raise ValueError('Single-thread BLAS verification failed: '+info['library'])
        yield [dict(info,threads=int(get())) for get,_,info in runtimes]
    finally:
        try:
            restoration_error=None
            for get,set_threads,count in reversed(previous):
                try:
                    set_threads(count)
                    if int(get())!=count:raise RuntimeError('Could not restore native BLAS thread limit')
                except Exception as exc:restoration_error=exc
            if restoration_error is not None:raise restoration_error
        finally:_blas_control_lock.release()


@lru_cache(maxsize=1)
def _numpy_blas():
    folder=Path(np.__file__).resolve().parent.parent/'numpy.libs'
    candidates=list(folder.glob('*openblas*.dll'))+list(folder.glob('*openblas*.so*'))
    for path in candidates:
        try:
            library=ctypes.CDLL(str(path))
            for prefix in ('scipy_openblas_','openblas_'):
                for suffix in ('64_','','_'):
                    try:
                        threads=getattr(library,prefix+'get_num_threads'+suffix)
                        config=getattr(library,prefix+'get_config'+suffix)
                    except AttributeError:continue
                    threads.restype=ctypes.c_int;threads.argtypes=[]
                    config.restype=ctypes.c_char_p;config.argtypes=[]
                    details=config().decode()
                    version=details.split()[1] if details.startswith('OpenBLAS ') else details
                    return library,threads,dict(backend='OpenBLAS',version=version,configuration=details,
                        library=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        except (OSError,ValueError,AttributeError):continue
    return None


def native_backend_info():
    """Query the active NumPy runtime, not environment-variable/CPU guesses."""
    result=dict(backend='Unknown',version='Unknown',threads=None,library=None,sha256=None,
                numpy_version=np.__version__,platform=sys.platform,machine=platform.machine(),
                cpu_count=os.cpu_count(),calculation_threads=1)
    found=_numpy_blas()
    if found:
        _,threads,info=found;result.update(info)
        value=int(threads());result['threads']=value if value>0 else None
    else:
        # Optional introspection supports other installed runtimes, including MKL.
        # It is never required or used to change their process-global settings.
        try:
            from threadpoolctl import threadpool_info
            rows=[r for r in threadpool_info() if r.get('user_api')=='blas']
            if len(rows)==1:
                r=rows[0];result.update(backend=r.get('internal_api','Unknown'),version=r.get('version') or 'Unknown',
                    threads=r.get('num_threads'),library=r.get('filepath'))
        except ImportError:pass
    try:
        rows=[info for _,_,info in _blas_runtimes()]
        result['runtimes']=rows
        result['automatic_thread_control']=bool(rows) and all(row['parallel'] in (0,1) for row in rows)
    except (OSError,ValueError,ImportError):
        result['runtimes']=[];result['automatic_thread_control']=False
    return result


def worker_plan(settings,cfg,n,*,native=None):
    native=native_backend_info() if native is None else native
    mode=cfg.worker_mode;requested=cfg.parallel_workers
    if mode not in ('automatic','manual') or type(requested) is not int or not 1<=requested<=MAX_WORKERS:
        raise ValueError('Parallel Workers requires Automatic or Manual and an integer from 1 to 4.')
    methods=('bloch','fft-multislice') if cfg.propagation=='both' else (cfg.propagation,)
    effective={};messages=[];blocked=False;risk='VALIDATED POLICY'
    matched=(native.get('sha256')==IMPLICATED_DLL_SHA256 and native.get('platform')=='win32'
        and native.get('numpy_version')=='2.4.6' and settings.zone==(0,1,7)
        and abs(settings.voltage-300)<1e-9 and abs(settings.thickness-8)<1e-9
        and abs(settings.potential_cutoff-2)<1e-9 and settings.b_factor==0 and cfg.depth==64
        and np.allclose(settings.tilt,(-7.11672544,0),rtol=0,atol=1e-8) and n in (21,27))
    if not matched:risk='UNVERIFIED COMBINATION'
    for method in methods:
        if cfg.channeling_model=='single':auto=1
        elif method=='bloch':
            dense=80*n**4/2**20
            auto=1 if native.get('platform')=='win32' else min(4,max(1,int(1200/(dense+40))))
        else:auto=min(MAX_WORKERS,native.get('cpu_count') or 1)
        count=auto if mode=='automatic' else requested;effective[method]=count
        if cfg.channeling_model=='single' and count!=1:
            blocked=True;risk='UNVERIFIED COMBINATION';messages.append('Single Channeling has no parallel detector executor; request 1 or Automatic.')
        if cfg.channeling_model=='double' and method=='bloch' and native.get('platform')=='win32':
            if count>1 and native.get('threads')!=1 and not native.get('automatic_thread_control',False):
                blocked=True
                if matched and n==27 and count==4 and native.get('threads')==12:
                    risk='KNOWN UNSAFE';messages.append('4 BW workers with 12 OpenBLAS threads previously caused a native crash in this matching Windows configuration.')
                else:
                    risk='UNVERIFIED COMBINATION';messages.append('Concurrent Windows BW workers require verified single-thread BLAS. Automatic control is unavailable for this runtime; choose 1 worker or use a supported numerical runtime. No calculation started.')
            elif not (matched and (count==1 and native.get('threads') in (1,12) or count==4 and native.get('threads')==1)):
                if risk!='KNOWN UNSAFE':risk='UNVERIFIED COMBINATION'
        elif cfg.channeling_model=='double':risk='UNVERIFIED COMBINATION'
    if native.get('threads') is None:
        if risk!='KNOWN UNSAFE':risk='UNVERIFIED COMBINATION'
        messages.append('Native backend/thread count Unknown; this combination is not verified safe.')
    if risk=='UNVERIFIED COMBINATION' and not blocked:
        messages.append('Conservative execution allowed with a caution; passing memory admission is not native-stability certification.')
    if native.get('automatic_thread_control'):
        messages.append('Execution will set and verify 1 BLAS thread in each NumPy/SciPy runtime, then restore prior limits after workers stop.')
    return dict(mode=mode,requested_workers='Automatic' if mode=='automatic' else requested,
        policy_version='parallel-workers-v1',
        effective_workers=effective,native=native,risk=risk,blocked=blocked,
        status='Blocked' if blocked else ('Warning' if risk=='UNVERIFIED COMBINATION' else 'Supported'),
        messages=messages,policy='One calculation QThread; detector workers separate from native BLAS/LAPACK threads.',
        evidence='Bounded Ni [017] 300 kV, 8 nm, 21/27-beam tests; not global numerical convergence.')


def require_supported(plan):
    if plan['blocked']:raise ValueError(plan['risk']+': '+' '.join(plan['messages']))


def memory_contributors(info):
    terms=sorted(info.get('memory_breakdown_mib',{}).items(),key=lambda item:item[1],reverse=True)
    return 'Largest array bounds: '+', '.join(f'{key.replace("_"," ")} {value:.1f} MiB' for key,value in terms[:3])+'.'


def preview_text(settings,cfg,info):
    p=info['execution'];native=p['native'];counts=', '.join(k+': '+str(v) for k,v in p['effective_workers'].items())
    peak=info.get('estimated_process_peak_mib')
    peak_text=f'{peak:.1f} MiB' if peak is not None else 'Unknown'
    return (f'Voltage: {settings.voltage:g} kV | Beam cutoff: {settings.beam_cutoff:g} Å⁻¹ | Potential cutoff: {settings.potential_cutoff:g} Å⁻¹\n'
        f"Retained beams: {info['bw_beams']} / {info['fft_harmonics']} FFT harmonics | Propagation: {cfg.propagation} | {cfg.channeling_model.title()} Channeling\n"
        f"Energy samples: {cfg.energy_points} | Angular grid: {cfg.grid}×{cfg.grid}\n"
        f"Requested workers: {p['requested_workers']} | Effective workers: {counts}\n"
        f"NumPy BLAS: {native['backend']} {native['version']} | BLAS threads: {native['threads'] if native['threads'] is not None else 'Unknown'} | CPUs: {native['cpu_count']}\n"
        f"Estimated peak RAM: {peak_text} | Budget: {cfg.memory_budget_mib} MiB\n"
        f"Available RAM: {info.get('available_ram_mib',0):.1f} MiB (50% guard); active reservations: {info.get('concurrent_reserved_working_mib',0):.1f} MiB. Dense bound: {info['dense_working_estimate_mib']:.1f} MiB.\n") + (
        f"Status: {p['status']} — {p['risk']}\n"+' '.join(p['messages'])+'\n'+p['policy']+
        ('\n'+memory_contributors(info) if info.get('memory_breakdown_mib') else ''))
