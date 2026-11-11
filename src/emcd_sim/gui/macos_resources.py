"""Read-only Apple Silicon discovery and conservative, ephemeral resource policy."""
import ctypes,math,os,platform,sys
from functools import lru_cache


@lru_cache(maxsize=1)
def _system():
    library=ctypes.CDLL('/usr/lib/libSystem.B.dylib',use_errno=True)
    library.sysctlbyname.argtypes=[ctypes.c_char_p,ctypes.c_void_p,ctypes.POINTER(ctypes.c_size_t),ctypes.c_void_p,ctypes.c_size_t]
    library.sysctlbyname.restype=ctypes.c_int
    return library


def _read(name,kind='integer'):
    if sys.platform!='darwin':return None
    try:
        size=ctypes.c_size_t()
        call=_system().sysctlbyname
        if call(name.encode(),None,ctypes.byref(size),None,0)!=0 or not size.value:return None
        buffer=ctypes.create_string_buffer(size.value)
        if call(name.encode(),buffer,ctypes.byref(size),None,0)!=0:return None
        raw=buffer.raw[:size.value]
        if kind=='string':return raw.rstrip(b'\0').decode()
        if kind=='bytes':return raw
        return int.from_bytes(raw,sys.byteorder)
    except (OSError,ValueError,UnicodeError):return None


@lru_cache(maxsize=1)
def hardware_info():
    logical=_read('hw.logicalcpu') or os.cpu_count() or 1
    result=dict(architecture=platform.machine(),model=_read('hw.model','string'),
        chip=_read('machdep.cpu.brand_string','string'),logical_cores=logical,
        performance_cores=None,efficiency_cores=None,physical_memory_mib=None,topology_source='unavailable')
    memory=_read('hw.memsize')
    if memory:result['physical_memory_mib']=memory/2**20
    levels=_read('hw.nperflevels')
    if levels is not None and 0<levels<=32:
        rows=[(_read(f'hw.perflevel{i}.name','string'),_read(f'hw.perflevel{i}.logicalcpu')) for i in range(levels)]
        for name,count in rows:
            if name and count and 0<count<=logical:
                if name.lower()=='performance':result['performance_cores']=count
                elif name.lower()=='efficiency':result['efficiency_cores']=count
        if (result['performance_cores'] is not None and result['efficiency_cores'] is not None
                and result['performance_cores']+result['efficiency_cores']==logical):
            result['topology_source']='sysctl named performance levels'
        else:
            result['performance_cores']=result['efficiency_cores']=None
    return result


def pressure_info():
    # XNU exports dispatch memory-pressure values (normal=1, warning=2,
    # critical=4), not its internal pressure enumeration.
    raw=_read('kern.memorystatus_vm_pressure_level')
    result=dict(memory_pressure={1:'normal',2:'warning',4:'critical'}.get(raw,'unavailable'),memory_pressure_raw=raw)
    swap=_read('vm.swapusage','bytes')
    if swap is not None and len(swap)>=24:
        result['swap_used_mib']=int.from_bytes(swap[16:24],sys.byteorder)/2**20
    else:result['swap_used_mib']=None
    return result


def manual_worker_limit(hardware=None):
    if sys.platform!='darwin':return 4
    return max(1,int((hardware or hardware_info())['logical_cores']))


def auto_memory_budget(snapshot=None):
    from .memory_budget import memory_snapshot
    state=memory_snapshot() if snapshot is None else snapshot
    total=state.get('physical_memory_mib') or hardware_info().get('physical_memory_mib')
    if not total:raise ValueError('Auto memory budget unavailable: total physical RAM could not be determined; choose Manual MiB.')
    pressure=state.get('memory_pressure','unavailable')
    available=state['available_ram_mib'];rss=state['process_rss_mib']
    reserve=max(1024.,.1*total)
    fraction=.5 if pressure=='normal' else .35  # Missing pressure data is conservative too.
    headroom=max(0.,available-reserve)*fraction
    limit=min(.5*total,.5*available,rss+headroom)
    if not math.isfinite(limit) or limit<1:raise ValueError('Auto memory admission rejected: no safe process headroom is currently available.')
    return dict(mode='automatic',effective_budget_mib=int(limit),physical_memory_mib=total,
        admission_rejected=pressure=='critical',
        available_ram_mib=available,baseline_process_rss_mib=rss,memory_pressure=pressure,
        swap_used_mib=state.get('swap_used_mib'),system_reserve_mib=reserve,
        headroom_fraction=fraction,policy='macos-memory-v1; advisory current availability, rechecked at admission')


def adaptive_worker_count(settings,cfg,n,hardware,*,detector_pixels=None):
    """Capacity estimate, not an optimality claim or a persistent calibration."""
    logical=max(1,int(hardware.get('logical_cores') or 1))
    p=hardware.get('performance_cores')
    capacity=min(logical,p if p else max(1,logical//2))
    if cfg.channeling_model=='single':return 1,dict(cpu_capacity=capacity,independent_tasks=1,reason='Single Channeling has no detector executor')
    pixels=cfg.grid**2
    # The GUI passes exact detector support where available. Otherwise use the
    # physical aperture area plus a boundary allowance, bounded by the full grid.
    if detector_pixels is None:
        step=2*cfg.halfwidth/max(1,cfg.grid-1)
        detector_pixels=min(pixels,max(1,int(2*math.pi*(cfg.radius/step+1)**2)))
    selected=min(cfg.energy_points,len({float(v) for _,v in getattr(cfg,'selected_edges',())}) or 2) if cfg.angular_maps else 0
    full=cfg.angular_maps and cfg.angular_evaluation=='all'
    average=pixels if full else (selected*pixels+max(0,cfg.energy_points-selected)*detector_pixels)/max(1,cfg.energy_points)
    tasks=max(1,math.ceil(average/(16 if cfg.propagation=='bloch' else 8)))
    if cfg.propagation=='bloch':
        work=average*(n**4 if cfg.systematic_row else cfg.depth*n*n)
    else:
        mesh=cfg.fft_grid**(1 if cfg.systematic_row else 2)
        work=average*cfg.depth*(mesh*math.log2(max(mesh,2))+n*n)
    # Bounded Ni/Cr measurements show tiny bases do not benefit from large
    # pools. Larger-request thresholds are conservative starting heuristics.
    proposed=1 if n<=8 or work<2e5 else 2 if work<2e6 else 4 if work<2e7 else capacity
    count=max(1,min(capacity,tasks,proposed))
    return count,dict(cpu_capacity=capacity,independent_tasks=tasks,estimated_work_units=work,
        average_query_pixels=average,reason='Small-basis scaling evidence; otherwise workload/P-core starting policy. Memory admission may reduce Auto only.',
        efficiency_cores_policy='Available to Manual scheduling; no affinity or claim about actual core placement')
