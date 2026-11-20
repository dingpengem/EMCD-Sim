"""Read-only hardware/process capacity; no affinity changes or benchmarks.

Windows CPU Sets expose processor groups, SMT cores and efficiency classes:
https://learn.microsoft.com/windows/win32/api/winnt/ns-winnt-system_cpu_set_information
Higher efficiency-class values identify faster, less power-efficient cores.
"""
import ctypes
from functools import lru_cache
import os
import platform
import struct


@lru_cache(maxsize=1)
def cpu_model():
    if os.name=='nt':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as key:
                return winreg.QueryValueEx(key,'ProcessorNameString')[0].strip()
        except OSError:pass
    return platform.processor().strip() or 'CPU model unavailable'


def summarize_cpu_sets(rows, *, groups=None, affinity=None, selected=None):
    """Apply observed restrictions, keeping group-relative core identities."""
    usable=[r for r in rows if (not r['allocated'] or r['allocated_to_process'])
            and (groups is None or r['group'] in groups)
            and (selected is None or r['id'] in selected)
            and (affinity is None or (r['group'],r['logical']) in affinity)]
    if not usable:raise ValueError('No processors available under the current CPU restrictions')
    cores={}
    for row in usable:cores[row['group'],row['core']]=row['efficiency']
    classes={value:sum(v==value for v in cores.values()) for value in sorted(set(cores.values()))}
    return dict(logical_processors=len(usable),physical_cores=len({(r['group'],r['core']) for r in rows}),
        available_physical_cores=len(cores),efficiency_classes=classes,
        hybrid=len(classes)>1,system_logical_processors=len(rows),
        affinity_restricted=len(usable)<len(rows),processor_groups=sorted({r['group'] for r in usable}))


def _windows_cpu_capacity():
    from ctypes import wintypes as w
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.GetCurrentProcess.restype=w.HANDLE;process=k.GetCurrentProcess()
    size=w.ULONG()
    query=k.GetSystemCpuSetInformation
    query.argtypes=[ctypes.c_void_p,w.ULONG,ctypes.POINTER(w.ULONG),w.HANDLE,w.ULONG]
    query.restype=w.BOOL
    query(None,0,ctypes.byref(size),process,0)
    if not size.value:raise OSError('Windows CPU Set query unavailable')
    buffer=ctypes.create_string_buffer(size.value)
    if not query(buffer,size.value,ctypes.byref(size),process,0):raise ctypes.WinError(ctypes.get_last_error())
    rows=[];offset=0
    while offset+8<=size.value:
        length,kind=struct.unpack_from('<II',buffer,offset)
        if length<8 or offset+length>size.value:raise ValueError('Invalid Windows CPU Set record')
        if kind==0 and length>=32:
            ident,group,logical,core,cache,node,efficiency,flags=struct.unpack_from('<IH6B',buffer,offset+8)
            rows.append(dict(id=ident,group=group,logical=logical,core=core,efficiency=efficiency,
                allocated=bool(flags&2),allocated_to_process=bool(flags&4)))
        offset+=length
    if not rows:raise OSError('Windows supplied no CPU Set records')
    groups=None;count=w.USHORT()
    query_groups=k.GetProcessGroupAffinity
    query_groups.argtypes=[w.HANDLE,ctypes.POINTER(w.USHORT),ctypes.POINTER(w.USHORT)]
    query_groups.restype=w.BOOL
    group_ok=query_groups(process,ctypes.byref(count),None)
    if not group_ok and not count.value:raise ctypes.WinError(ctypes.get_last_error())
    if count.value:
        values=(w.USHORT*count.value)()
        if not query_groups(process,ctypes.byref(count),values):raise ctypes.WinError(ctypes.get_last_error())
        groups=set(values)
    selected=None;needed=w.ULONG()
    defaults=k.GetProcessDefaultCpuSets
    defaults.argtypes=[w.HANDLE,ctypes.POINTER(w.ULONG),w.ULONG,ctypes.POINTER(w.ULONG)]
    defaults.restype=w.BOOL
    default_ok=defaults(process,None,0,ctypes.byref(needed))
    if not default_ok and not needed.value:raise ctypes.WinError(ctypes.get_last_error())
    if needed.value:
        ids=(w.ULONG*needed.value)()
        if not defaults(process,ids,needed.value,ctypes.byref(needed)):raise ctypes.WinError(ctypes.get_last_error())
        selected=set(ids)
    affinity=None;mask=ctypes.c_size_t();system_mask=ctypes.c_size_t()
    get_mask=k.GetProcessAffinityMask
    get_mask.argtypes=[w.HANDLE,ctypes.POINTER(ctypes.c_size_t),ctypes.POINTER(ctypes.c_size_t)]
    get_mask.restype=w.BOOL
    restricted_mask=get_mask(process,ctypes.byref(mask),ctypes.byref(system_mask))
    if restricted_mask and mask.value and groups is not None and len(groups)==1:
        affinity={(next(iter(groups)),i) for i in range(64) if mask.value&(1<<i)}
    info=summarize_cpu_sets(rows,groups=groups,affinity=affinity,selected=selected)
    info['notes']=[]
    if restricted_mask and mask.value and mask.value!=system_mask.value and (groups is None or len(groups)>1):
        # A legacy partial mask cannot identify its primary group here. Do
        # not overstate usable concurrency on a multi-group process.
        info['logical_processors']=min(info['logical_processors'],mask.value.bit_count())
        info['available_physical_cores']=None;info['efficiency_classes']={}
        info['affinity_restricted']=True
        info['notes'].append('Partial multi-group affinity: conservative mask capacity; core classes unavailable.')
    # Job hard CPU caps constrain concurrency even when the affinity is broad.
    class CpuRate(ctypes.Structure):_fields_=[('flags',w.DWORD),('rate',w.DWORD)]
    rate=CpuRate();job_query=k.QueryInformationJobObject
    job_query.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD,ctypes.c_void_p]
    job_query.restype=w.BOOL
    if job_query(None,15,ctypes.byref(rate),ctypes.sizeof(rate),None) and rate.flags&1:
        cap=(rate.rate>>16) if rate.flags&16 else rate.rate if rate.flags&4 else None
        if cap:
            info['cpu_rate_fraction']=cap/10000
            info['logical_processors']=min(info['logical_processors'],max(1,int(info['logical_processors']*cap/10000)))
            info['notes'].append('Windows Job CPU rate cap applied to worker capacity.')
    return info


def cpu_capacity():
    try:
        if os.name=='nt':info=_windows_cpu_capacity()
        else:
            available=len(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else os.cpu_count() or 1
            info=dict(logical_processors=available,system_logical_processors=os.cpu_count() or available,
                physical_cores=None,available_physical_cores=None,hybrid=False,efficiency_classes={},
                affinity_restricted=available<(os.cpu_count() or available),notes=['Physical-core topology unavailable.'])
    except (OSError,ValueError,AttributeError) as exc:
        info=dict(logical_processors=1,system_logical_processors=os.cpu_count(),physical_cores=None,
            available_physical_cores=None,hybrid=False,efficiency_classes={},affinity_restricted=None,
            notes=['CPU topology/restrictions unavailable; conservative one-worker fallback: '+str(exc)])
    return dict(info,cpu_model=cpu_model())


def hardware_snapshot():
    from .memory_budget import memory_snapshot
    return dict(memory_snapshot(),**cpu_capacity())
