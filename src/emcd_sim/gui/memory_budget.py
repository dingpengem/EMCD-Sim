"""Conservative admission checks; no numerical settings are adjusted.

Budgets constrain estimated total process peak, not just the dense kernel.
Reservations coordinate concurrent calculations in this Python process; other
processes are reflected in a fresh available-physical-RAM reading.
"""
from contextlib import contextmanager
import ctypes
import math
import os
from pathlib import Path
import threading

BUDGETS_MIB = (512, 1024, 2048, 4096, 8192)
DEFAULT_BUDGET_MIB = 2048
AVAILABLE_RAM_FRACTION = .5
ALLOCATION_MARGIN = 1.25
PROCESS_RESERVE_MIB = 128.
_lock = threading.RLock()
_reservations = {}


def memory_snapshot():
    # Windows ctypes signatures below contain per-call structure types. Keep
    # concurrent previews/admission calls from replacing each other's argtypes.
    with _lock:return _memory_snapshot()


def _memory_snapshot():
    """Available physical RAM and current process RSS, in MiB; stdlib only."""
    if os.name == 'nt':
        from ctypes import wintypes

        class Status(ctypes.Structure):
            _fields_ = [('length', wintypes.DWORD), ('load', wintypes.DWORD)] + [
                (k, ctypes.c_ulonglong) for k in ('total', 'available', 'page_total', 'page_available', 'virtual_total', 'virtual_available', 'extended')]

        status = Status(); status.length = ctypes.sizeof(status)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            raise OSError('GlobalMemoryStatusEx failed')

        class Counters(ctypes.Structure):
            _fields_ = [('cb', wintypes.DWORD), ('faults', wintypes.DWORD)] + [
                (k, ctypes.c_size_t) for k in ('peak_ws', 'ws', 'peak_paged', 'paged', 'peak_nonpaged', 'nonpaged', 'pagefile', 'peak_pagefile')]

        counters = Counters(); counters.cb = ctypes.sizeof(counters)
        ctypes.windll.kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        get_memory = ctypes.windll.psapi.GetProcessMemoryInfo
        get_memory.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        if not get_memory(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            raise OSError('GetProcessMemoryInfo failed')
        installed=ctypes.c_ulonglong()
        get_installed=ctypes.windll.kernel32.GetPhysicallyInstalledSystemMemory
        get_installed.argtypes=[ctypes.POINTER(ctypes.c_ulonglong)];get_installed.restype=wintypes.BOOL
        installed_mib=installed.value/1024 if get_installed(ctypes.byref(installed)) else status.total/2**20
        return dict(available_ram_mib=status.available/2**20, process_rss_mib=counters.ws/2**20,
            total_ram_mib=status.total/2**20,installed_ram_mib=installed_mib,
            process_commit_mib=counters.pagefile/2**20,commit_limit_mib=status.page_total/2**20,
            commit_available_mib=status.page_available/2**20,virtual_available_mib=status.virtual_available/2**20)
    # Linux supports MemAvailable (includes reclaimable memory), not swap.
    values = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
    available = float(values['MemAvailable'].split()[0])/1024
    resident_pages = int(Path('/proc/self/statm').read_text().split()[1])
    total=float(values['MemTotal'].split()[0])/1024
    return dict(available_ram_mib=available, process_rss_mib=resident_pages*os.sysconf('SC_PAGE_SIZE')/2**20,
                total_ram_mib=total,installed_ram_mib=total)


def memory_limits(state):
    """Additional allocation headroom, not a second allowance for existing RSS.

    Windows ullAvailPageFile is the maximum the current process can commit;
    ullAvailVirtual also bounds its address space. Retain the existing 50%
    physical-RAM guard, applying it to NEW allocations instead of existing RSS.
    """
    limits={'50% of currently available RAM':AVAILABLE_RAM_FRACTION*state['available_ram_mib']}
    for key,label in (('commit_available_mib','50% of available process commit'),
                      ('virtual_available_mib','50% of available virtual address space')):
        if key in state:
            value=state[key]
            if not math.isfinite(value) or value<0:raise ValueError('Invalid '+label)
            limits[label]=AVAILABLE_RAM_FRACTION*value
    return limits


def selected_memory_budget(requested, mode, state):
    if mode not in ('automatic','manual'):raise ValueError('Memory mode must be Auto or Manual')
    if type(requested) is not int or requested<=0:raise ValueError('Memory budget must be a positive integer MiB value.')
    return int(math.floor(state['process_rss_mib']+min(memory_limits(state).values()))) if mode=='automatic' else requested


def resource_budget(cfg):
    """Accepted Run allocation; retain the requested Manual value in cfg."""
    allocation=getattr(cfg,'resource_allocation',None)
    return allocation['memory_budget_mib'] if allocation is not None else cfg.memory_budget_mib


def assess_memory(working_mib, budget_mib=DEFAULT_BUDGET_MIB, *, dense_mib=0., snapshot=None,reject=True,mode='manual'):
    """Reject over-budget jobs before large allocations; include active workers."""
    if not math.isfinite(working_mib) or working_mib < 0:
        raise ValueError('Estimated allocation must be finite and nonnegative.')
    try:
        state = memory_snapshot() if snapshot is None else snapshot
        available, rss = state['available_ram_mib'], state['process_rss_mib']
        if not math.isfinite(available) or available <= 0 or not math.isfinite(rss) or rss < 0:
            raise ValueError('invalid RAM/RSS measurement')
    except (OSError, KeyError, ValueError) as exc:
        raise ValueError('Cannot verify available physical RAM/process RSS; calculation not started: '+str(exc)) from exc
    budget_mib=selected_memory_budget(budget_mib,mode,state)
    limits=memory_limits(state)
    with _lock:
        active = sum(value[0] for value in _reservations.values())
        count = len(_reservations)
        baseline=min((value[1] for value in _reservations.values()),default=rss)
    # Active allocations are either already resident or still represented by
    # their reservation. Count the larger, not their sum, then add new work.
    peak = max(rss,baseline+ALLOCATION_MARGIN*active)+PROCESS_RESERVE_MIB+ALLOCATION_MARGIN*working_mib
    additional=max(0.,peak-rss);headroom=min(limits.values())
    ram_limit = AVAILABLE_RAM_FRACTION*available
    info = dict(memory_budget_mib=budget_mib, available_ram_mib=available,
        available_ram_fraction=AVAILABLE_RAM_FRACTION, available_ram_limit_mib=ram_limit,
        process_rss_mib=rss, estimated_process_peak_mib=peak,
        concurrent_reserved_working_mib=active, concurrent_calculations=count,
        allocation_margin=ALLOCATION_MARGIN, process_reserve_mib=PROCESS_RESERVE_MIB,
        reservation_baseline_rss_mib=baseline,additional_allocation_mib=additional,
        memory_headroom_mib=headroom,memory_constraints_mib=limits,memory_mode=mode)
    if peak > budget_mib or additional > headroom:
        cause = []
        if peak > budget_mib:
            cause.append(f'selected budget {budget_mib} MiB')
        for label,limit in limits.items():
            if additional>limit:cause.append(f'{label} ({limit:.1f} MiB additional headroom)')
        message=(f'Memory admission rejected: dense kernel {dense_mib:.1f} MiB; estimated arrays {working_mib:.1f} MiB; '
            f'estimated total process peak {peak:.1f} MiB exceeds '+ ' and '.join(cause)+
            f'. Includes current RSS {rss:.1f} MiB, {count} active calculation(s), 25% allocation margin and 128 MiB reserve. '
            'No simulation parameters were changed. Free RAM or explicitly revise Manual resources; any sampling change must be explicit.')
        if reject:raise ValueError(message)
        info.update(rejected=True,rejection_reason=message)
    return info


@contextmanager
def reserve_memory(working_mib, budget_mib=DEFAULT_BUDGET_MIB, *, dense_mib=0.):
    """Atomic admission/reservation with cleanup on success, error or cancel."""
    token = object()
    with _lock:
        admission = assess_memory(working_mib, budget_mib, dense_mib=dense_mib)
        _reservations[token] = (working_mib,admission['reservation_baseline_rss_mib'])
    try:
        yield admission
    except MemoryError as exc:
        raise ValueError('Memory allocation failed despite the conservative estimate. Calculation stopped; '
                         'no simulation settings were reduced. Free RAM or choose an explicitly smaller job.') from exc
    finally:
        with _lock:
            del _reservations[token]
