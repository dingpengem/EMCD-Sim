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
