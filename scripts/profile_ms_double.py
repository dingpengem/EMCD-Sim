"""Opt-in, external profiling of the unchanged MS Double production function.

No profiling hooks are installed by importing this module. AST instrumentation
adds timing contexts around existing statements in an in-memory copy only;
production source and the mathematical statements themselves are unchanged.
"""
import argparse,ast,cProfile,csv,hashlib,inspect,json,os,platform,pstats,subprocess,sys
import threading,time,tracemalloc
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import asdict,replace
from pathlib import Path
from unittest.mock import patch
import numpy as np
from emcd_sim import multislice_double_channeling as ms
from emcd_sim.double_channeling import intensities_from_response
from emcd_sim.gui import channeling,emcd_forward as forward
from emcd_sim.gui.geometry import elastic_model,geometry
from emcd_sim.gui.project_io import load_project,restore_structure
from emcd_sim.gui.memory_budget import memory_snapshot
from emcd_sim.gui import memory_budget
from emcd_sim.geometry import VirtualDetector
from emcd_sim.benchmark import nickel_physical_benchmark

ROOT=Path('outputs/ms_double_performance_profile')
REFERENCE=Path('outputs/energy_angular_sampling/benchmark/fft-multislice_optimized/project')


class Timings:
    """Per-thread exclusive and inclusive times; merge only after workers finish."""
    def __init__(self):self.local=threading.local();self.threads=[];self.lock=threading.Lock()
    def data(self):
        if not hasattr(self.local,'data'):
            self.local.data=dict(name=threading.current_thread().name,regions={},counts=defaultdict(int),stack=[])
            with self.lock:self.threads.append(self.local.data)
        return self.local.data
    def count(self,name,n=1):self.data()['counts'][name]+=n
    @contextmanager
    def region(self,name):
        data=self.data();entry=[time.perf_counter(),time.thread_time(),0.,0.];data['stack'].append(entry)
        try:yield
        finally:
            wall=time.perf_counter()-entry[0];cpu=time.thread_time()-entry[1];data['stack'].pop()
            if data['stack']:data['stack'][-1][2]+=wall;data['stack'][-1][3]+=cpu
            item=data['regions'].setdefault(name,dict(calls=0,wall_inclusive=0.,cpu_inclusive=0.,wall_exclusive=0.,cpu_exclusive=0.))
            item['calls']+=1;item['wall_inclusive']+=wall;item['cpu_inclusive']+=cpu
            item['wall_exclusive']+=wall-entry[2];item['cpu_exclusive']+=cpu-entry[3]
    def report(self):
        regions={};counts=defaultdict(int);threads=[]
        for thread in self.threads:
            for key,value in thread['regions'].items():
                item=regions.setdefault(key,dict.fromkeys(value,0))
                for name,n in value.items():item[name]+=n
            for key,n in thread['counts'].items():counts[key]+=n
            threads.append({k:v for k,v in thread.items() if k!='stack'})
        return dict(regions=regions,counts=dict(counts),threads=threads)


def instrumented_response(timings,function=None):
    """Wrap named original AST statements, without replacing their operations."""
    function=function or ms.multislice_double_channeling_response
    source=inspect.getsource(function)
    tree=ast.parse(source);sites=[]
    class Regions(ast.NodeTransformer):
        def visit(self,node):
            # Identify statements before descending, preserving their body/math.
            category=None
            if isinstance(node,ast.Assign):
                targets={n.id for target in node.targets for n in ast.walk(target) if isinstance(n,ast.Name)}
                if 'kernel' in targets:category='dipole_kernel'
                elif 'transfer' in targets:category='transfer_allocation_and_fill'
                elif 'phases' in targets:category='equivalent_site_phases'
                elif 'plan' in targets:category='outgoing_plan'
                elif targets & {'out_norm','outgoing_leak','norm_error','incoming_leak','incoming_power','magnitude'}:category='norm_leakage_diagnostics'
            elif isinstance(node,ast.Expr) and isinstance(node.value,ast.Call) and any(k.arg=='out' and isinstance(k.value,ast.Name) and k.value.id=='magnitude' for k in node.value.keywords):
                category='norm_leakage_diagnostics'
            elif isinstance(node,ast.For) and isinstance(node.target,ast.Tuple) and any(isinstance(n,ast.Name) and n.id=='phase' for n in node.target.elts):
                category='depth_cartesian_contraction'
            updated=super().visit(node)
            if category:
                sites.append(dict(category=category,line=node.lineno,statement=ast.unparse(node).splitlines()[0]))
                context=ast.Call(func=ast.Attribute(value=ast.Name(id='_timings',ctx=ast.Load()),attr='region',ctx=ast.Load()),args=[ast.Constant(category)],keywords=[])
                return ast.copy_location(ast.With(items=[ast.withitem(context_expr=context)],body=[updated]),node)
            return updated
    tree=Regions().visit(tree);ast.fix_missing_locations(tree)
    ast.increment_lineno(tree,function.__code__.co_firstlineno-1)
    namespace=dict(function.__globals__,_timings=timings)
    exec(compile(tree,inspect.getsourcefile(function),'exec'),namespace)
    return namespace['multislice_double_channeling_response'],sites


@contextmanager
def fft_hooks(timings,implementation=ms):
    """Process-local hooks only while the explicitly requested profile runs."""
    original_advance=implementation.FFTSplitStep.advance
    def advance(self,coefficients,steps,dz,**kwargs):
        mode='incoming' if dz>=0 else 'outgoing'
        timings.count(mode+'_advance_calls');timings.count(mode+'_split_steps',steps)
        timings.count(mode+'_individual_split_steps',steps*int(np.prod(np.asarray(coefficients).shape[:-1])))
        timings.count(mode+'_factor_cache_hits' if self._cached_dz==dz else mode+'_factor_cache_misses')
        with timings.region(mode+'_advance'):return original_advance(self,coefficients,steps,dz,**kwargs)
    def fft_wrapper(fn,name):
        def call(a,*args,**kwargs):
            axes=kwargs.get('axes',tuple(range(np.asarray(a).ndim)))
            batch=int(np.prod(np.asarray(a).shape[:np.asarray(a).ndim-len(axes)]))
            timings.count(name+'_batched_calls');timings.count(name+'_individual_transforms',batch)
            timings.count(name+'_input_bytes',np.asarray(a).nbytes)
            with timings.region(name):return fn(a,*args,**kwargs)
        return call
    with patch.object(implementation.FFTSplitStep,'advance',advance),patch.object(np.fft,'fftn',fft_wrapper(np.fft.fftn,'fftn')),patch.object(np.fft,'ifftn',fft_wrapper(np.fft.ifftn,'ifftn')):
        yield


class SampleRAM:
    def __enter__(self):
        self.samples=[];self.stop=threading.Event()
        def sample():
            while not self.stop.is_set():
                # Windows' probe configures a ctypes function signature with
                # per-call structure types. Use the admission lock so this
                # optional sampler cannot race concurrent memory checks.
                with memory_budget._lock:self.samples.append(memory_snapshot()['process_rss_mib'])
                self.stop.wait(.05)
        self.thread=threading.Thread(target=sample,daemon=True);self.thread.start();return self
    def __exit__(self,*args):self.stop.set();self.thread.join()


def setup(reference=REFERENCE):
    saved=load_project(reference);settings=saved['settings'];cfg=saved['config']
    assert settings.voltage==300 and settings.thickness==8 and cfg.fft_grid==32 and cfg.slice_step==.5
    assert cfg.channeling_model=='double' and cfg.propagation=='fft-multislice'
    assert hashlib.sha256(Path(cfg.source).read_bytes()).hexdigest()==cfg.source_sha256,'Saved source changed'
    structure=restore_structure(saved['structure_snapshot']);elastic=elastic_model(structure,settings)
    model=replace(nickel_physical_benchmark(),elastic=elastic,detectors={k:VirtualDetector(p,cfg.radius) for k,p in zip(('A','B'),cfg.centers)})
    qx,qy,weights,_,_=channeling.angular_schedule(model,cfg,np.array([cfg.l3,cfg.l2]))
    points=np.column_stack((qx.ravel(),qy.ravel()))
    query,inverse=np.unique(np.column_stack((points[:,0],abs(points[:,1]))),axis=0,return_inverse=True)
    sign=np.ones((len(points),3));sign[points[:,1]<0,1]=-1
    _,R,hkl,_,_=geometry(structure,settings,systematic_row=cfg.systematic_row)
    # The tensor importer requires >=2 energies. Reuse the saved spectral axis
    # exactly; only its L3 tensor is contracted/propagated by this profiler.
    saved_energy=np.asarray(saved['spectra']['energy_ev']);assert saved_energy[0]==cfg.l3
    tensors=forward.tensors(cfg,saved_energy,R)
    return dict(saved=saved,settings=settings,cfg=cfg,elastic=elastic,model=model,qx=qx,qy=qy,
                weights=weights,query=query,inverse=inverse,sign=sign,tensors=tensors)


def response_args(case,grid,incoming):
    s=case['settings'];c=case['cfg']
    return dict(fft_grid=c.fft_grid,potential_cutoff=s.potential_cutoff,systematic_row=c.systematic_row,
        row_reduction=c.systematic_row,projected_geometry=channeling.Ni017Geometry(),depth_steps=c.depth,
        slice_step_nm=c.slice_step,memory_budget_mib=c.memory_budget_mib,prepared_grid=grid,prepared_incoming=incoming)


def evaluate_batches(case,query,grid,incoming,workers,*,timings=None,profile=False,implementation=ms):
    function=implementation.multislice_double_channeling_response
    response,sites=instrumented_response(timings,function) if timings else (function,[])
    kwargs=response_args(case,grid,incoming);s=case['settings'];c=case['cfg'];events=[];profiles=[];lock=threading.Lock()
    batches=[query[i:i+32] for i in range(0,len(query),32)]
    def worker(batch):
        start=time.perf_counter();cpu=time.thread_time();prof=cProfile.Profile(timer=time.thread_time) if profile else None
        if prof:prof.enable()
        try:
            if timings:
                with timings.region('response'):result=response(case['elastic'],c.l3,batch,s.thickness,**kwargs)
            else:result=response(case['elastic'],c.l3,batch,s.thickness,**kwargs)
        finally:
            if prof:prof.disable()
        with lock:
            events.append(dict(worker=threading.current_thread().name,pixels=len(batch),start=start,end=time.perf_counter(),cpu_seconds=time.thread_time()-cpu,diagnostics=result[1]))
            if prof:profiles.append(prof)
        return result[0]
    cpu_start=time.process_time();start=time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        submitted=time.perf_counter();futures=[pool.submit(worker,batch) for batch in batches];submit_seconds=time.perf_counter()-submitted
        arrays=[future.result() for future in futures]
    wall=time.perf_counter()-start;cpu=time.process_time()-cpu_start
    return np.concatenate(arrays),dict(wall_seconds=wall,process_cpu_seconds=cpu,average_active_cores=cpu/wall,
        workers=workers,batches=len(batches),directions=len(query),submit_seconds=submit_seconds,events=events,
        instrumentation_sites=sites),profiles


def reference_maps(case,response):
    c=case['cfg'];r=response[case['inverse']]*case['sign'][:,:,None]*case['sign'][:,None,:]
    maps=np.stack([intensities_from_response(r,t.tensor_angstrom2_per_ev[0]).reshape(c.grid,c.grid) for t in case['tensors']])
    expected=case['saved']['maps']['L3'];np.testing.assert_array_equal(maps[0],expected['I_plus']);np.testing.assert_array_equal(maps[1],expected['I_minus'])
    return dict(bitwise_equal_to_saved_L3=True,max_absolute_difference=float(max(abs(maps[0]-expected['I_plus']).max(),abs(maps[1]-expected['I_minus']).max())))


def dump_stats(profiles):
    stats=pstats.Stats(profiles[0])
    for profile in profiles[1:]:stats.add(profile)
    stats.dump_stats(str(ROOT/'workers.pstats'))
    rows=[]
    for (filename,line,name),(primitive,calls,own,cumulative,callers) in stats.stats.items():
        rows.append(dict(file=filename,line=line,function=name,primitive_calls=primitive,calls=calls,
            internal_profile_cpu_seconds=own,cumulative_profile_cpu_seconds=cumulative))
    rows.sort(key=lambda r:r['cumulative_profile_cpu_seconds'],reverse=True)
    (ROOT/'worker_cprofile.json').write_text(json.dumps(rows,indent=2))


def repeated_batch_checks(case,grid,incoming):
    """Small uninstrumented repeats only; never repeats a complete angular field."""
    subset=case['query'][np.linspace(0,len(case['query'])-1,256,dtype=int)]
    records=[];expected=None
    for repeat,order in enumerate(((1,2,4),(2,4,1),(4,1,2)),1):
        for workers in order:
            values,run,_=evaluate_batches(case,subset,grid,incoming,workers)
            if expected is None:expected=values.copy()
            else:np.testing.assert_array_equal(values,expected)
            run['repeat']=repeat;records.append(run)
            (ROOT/'thread_repeats.json').write_text(json.dumps(records,indent=2))
            print('Repeat',repeat,'workers',workers,'wall',run['wall_seconds'],flush=True)
    return records


def summarize():
    """Read completed measurements only; no simulation/configuration setup."""
    report=json.loads((ROOT/'full_L3.json').read_text());regions=report['timings']['regions']
    response=regions['response'];fft_wall=fft_cpu=0.
    for thread in report['timings']['threads']:
        if thread['name']=='MainThread':continue
        for name in ('fftn','ifftn'):
            fft_wall+=thread['regions'].get(name,{}).get('wall_inclusive',0.)
            fft_cpu+=thread['regions'].get(name,{}).get('cpu_inclusive',0.)
    outgoing=regions['outgoing_advance']
    rows=[dict(component='outgoing_fft_transforms',worker_wall_seconds=fft_wall,worker_cpu_seconds=fft_cpu),
          dict(component='outgoing_advance_non_fft',worker_wall_seconds=outgoing['wall_inclusive']-fft_wall,worker_cpu_seconds=outgoing['cpu_inclusive']-fft_cpu)]
    for name in ('depth_cartesian_contraction','norm_leakage_diagnostics','dipole_kernel','transfer_allocation_and_fill','equivalent_site_phases','outgoing_plan'):
        rows.append(dict(component=name,worker_wall_seconds=regions[name]['wall_inclusive'],worker_cpu_seconds=regions[name]['cpu_inclusive']))
    rows.append(dict(component='response_other',worker_wall_seconds=response['wall_exclusive'],worker_cpu_seconds=response['cpu_exclusive']))
    for row in rows:
        row['worker_wall_percent']=100*row['worker_wall_seconds']/response['wall_inclusive']
        row['worker_cpu_percent']=100*row['worker_cpu_seconds']/response['cpu_inclusive']
    with (ROOT/'components.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    result=dict(component_breakdown=rows,percentage_note='Exclusive partition of summed worker response elapsed/CPU times, not percentages additive across parallel main-thread wall time.')
    if (ROOT/'thread_repeats.json').exists():
        repeats=json.loads((ROOT/'thread_repeats.json').read_text());data={n:[r for r in repeats if r['workers']==n] for n in (1,2,4)}
        baseline=float(np.median([r['wall_seconds'] for r in data[1]]));thread_rows=[]
        for n,runs in data.items():
            walls=[r['wall_seconds'] for r in runs];median=float(np.median(walls))
            thread_rows.append(dict(workers=n,repeats=len(runs),wall_median=median,wall_min=min(walls),wall_max=max(walls),
                process_cpu_median=float(np.median([r['process_cpu_seconds'] for r in runs])),
                average_cores_median=float(np.median([r['average_active_cores'] for r in runs])),speedup=baseline/median,parallel_efficiency=baseline/median/n))
        result['thread_scaling']=thread_rows
        with (ROOT/'thread_summary.csv').open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(thread_rows[0]));writer.writeheader();writer.writerows(thread_rows)
    (ROOT/'summary.json').write_text(json.dumps(result,indent=2));return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',action='store_true')
    parser.add_argument('--batch-checks',action='store_true',help='Only small repeated 1/2/4-worker batches, no full-field calculation')
    parser.add_argument('--summarize',action='store_true',help='Read saved measurements only; no calculations')
    args=parser.parse_args()
    if args.summarize:summarize();return
    if not args.run and not args.batch_checks:parser.print_help();return
    ROOT.mkdir(parents=True,exist_ok=True)
    case=setup();s=case['settings'];c=case['cfg'];timings=Timings()
    if args.batch_checks:
        grid=channeling.fft_geometry(case['elastic'],s,c)
        incoming=ms.incident_fields(grid,s.thickness,depth_steps=c.depth,slice_step_nm=c.slice_step)
        repeated_batch_checks(case,grid,incoming);return
    audit=dict(settings=asdict(s),config=asdict(c),reference=str(REFERENCE),energy_ev=c.l3,
        commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        source_hash=c.source_sha256,source_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(ms.__file__),Path(channeling.__file__))},
        environment=dict(platform=platform.platform(),python=platform.python_version(),numpy=np.__version__,processor=platform.processor(),
            openblas_threads=os.environ.get('OPENBLAS_NUM_THREADS'),omp_threads=os.environ.get('OMP_NUM_THREADS')))
    (ROOT/'audit.json').write_text(json.dumps(audit,indent=2))
    with SampleRAM() as ram,fft_hooks(timings):
        with timings.region('fft_geometry_potential'):grid=channeling.fft_geometry(case['elastic'],s,c)
        with timings.region('incoming_fields'):incoming=ms.incident_fields(grid,s.thickness,depth_steps=c.depth,slice_step_nm=c.slice_step)
        result,run,_=evaluate_batches(case,case['query'],grid,incoming,4,timings=timings)
        with timings.region('magnetization_tensor_and_map_assembly'):equivalence=reference_maps(case,result)
    timing_report=timings.report()
    report=dict(run=run,timings=timing_report,equivalence=equivalence,sampled_rss_max_mib=max(ram.samples),rss_interval_seconds=.05,
        actual_depth_nodes=len(incoming[1]),substeps_per_interval=incoming[3],actual_slice_step_nm=incoming[4],fft_shape=list(grid.potential.shape))
    (ROOT/'full_L3.json').write_text(json.dumps(report,indent=2))
    print('Full L3',run['wall_seconds'],equivalence,flush=True)
    # Fixed representative actual grid directions, spanning q; same batches,
    # settings, energy and prepared incoming fields for each worker count.
    subset=case['query'][np.linspace(0,len(case['query'])-1,256,dtype=int)]
    comparison=[];expected=None
    for workers in (1,2,4):
        values,small_run,_=evaluate_batches(case,subset,grid,incoming,workers)
        if expected is None:expected=values.copy()
        else:np.testing.assert_array_equal(values,expected)
        comparison.append(small_run);print('Workers',workers,small_run['wall_seconds'],small_run['average_active_cores'],flush=True)
    (ROOT/'thread_scaling.json').write_text(json.dumps(comparison,indent=2))
    batch_timings=Timings()
    with fft_hooks(batch_timings):
        values,small_run,_=evaluate_batches(case,subset,grid,incoming,4,timings=batch_timings)
    np.testing.assert_array_equal(values,expected)
    (ROOT/'timing_only_batches.json').write_text(json.dumps(dict(run=small_run,timings=batch_timings.report(),bitwise_equal=True),indent=2))
    batch_timings=Timings()
    with fft_hooks(batch_timings):
        values,small_run,profiles=evaluate_batches(case,subset,grid,incoming,4,timings=batch_timings,profile=True)
    np.testing.assert_array_equal(values,expected);dump_stats(profiles)
    (ROOT/'instrumented_batches.json').write_text(json.dumps(dict(run=small_run,timings=batch_timings.report(),bitwise_equal=True),indent=2))
    tracemalloc.start();ms.multislice_double_channeling_response(case['elastic'],c.l3,subset[:32],s.thickness,**response_args(case,grid,incoming))
    current,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    (ROOT/'traced_memory.json').write_text(json.dumps(dict(current_mib=current/2**20,peak_traced_mib=peak/2**20,
        note='Single 32-direction call; Python/NumPy traced allocations, not complete native/process peak.'),indent=2))


if __name__=='__main__':main()
