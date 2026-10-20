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
        return dict(available_ram_mib=status.available/2**20, process_rss_mib=counters.ws/2**20)
    # Linux supports MemAvailable (includes reclaimable memory), not swap.
    values = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
    available = float(values['MemAvailable'].split()[0])/1024
    resident_pages = int(Path('/proc/self/statm').read_text().split()[1])
    return dict(available_ram_mib=available, process_rss_mib=resident_pages*os.sysconf('SC_PAGE_SIZE')/2**20)


def assess_memory(working_mib, budget_mib=DEFAULT_BUDGET_MIB, *, dense_mib=0., snapshot=None,reject=True):
    """Reject over-budget jobs before large allocations; include active workers."""
    if budget_mib not in BUDGETS_MIB:
        raise ValueError(f'Memory budget must be one of {BUDGETS_MIB} MiB.')
    if not math.isfinite(working_mib) or working_mib < 0:
        raise ValueError('Estimated allocation must be finite and nonnegative.')
    try:
        state = memory_snapshot() if snapshot is None else snapshot
        available, rss = state['available_ram_mib'], state['process_rss_mib']
        if not math.isfinite(available) or available <= 0 or not math.isfinite(rss) or rss < 0:
            raise ValueError('invalid RAM/RSS measurement')
    except (OSError, KeyError, ValueError) as exc:
        raise ValueError('Cannot verify available physical RAM/process RSS; calculation not started: '+str(exc)) from exc
    with _lock:
        active = sum(_reservations.values())
        count = len(_reservations)
    peak = rss+PROCESS_RESERVE_MIB+ALLOCATION_MARGIN*(working_mib+active)
    ram_limit = AVAILABLE_RAM_FRACTION*available
    info = dict(memory_budget_mib=budget_mib, available_ram_mib=available,
        available_ram_fraction=AVAILABLE_RAM_FRACTION, available_ram_limit_mib=ram_limit,
        process_rss_mib=rss, estimated_process_peak_mib=peak,
        concurrent_reserved_working_mib=active, concurrent_calculations=count,
        allocation_margin=ALLOCATION_MARGIN, process_reserve_mib=PROCESS_RESERVE_MIB)
    if peak > budget_mib or peak > ram_limit:
        cause = []
        if peak > budget_mib:
            cause.append(f'selected budget {budget_mib} MiB')
        if peak > ram_limit:
            cause.append(f'50% of currently available RAM ({ram_limit:.1f} MiB of {available:.1f} MiB)')
        message=(f'Memory admission rejected: dense kernel {dense_mib:.1f} MiB; estimated arrays {working_mib:.1f} MiB; '
            f'estimated total process peak {peak:.1f} MiB exceeds '+ ' and '.join(cause)+
            f'. Includes current RSS {rss:.1f} MiB, {count} active calculation(s), 25% allocation margin and 128 MiB reserve. '
            'No simulation parameters were changed. Choose a larger supported budget or free RAM; any sampling change must be explicit.')
        if reject:raise ValueError(message)
        info.update(rejected=True,rejection_reason=message)
    return info


@contextmanager
def reserve_memory(working_mib, budget_mib=DEFAULT_BUDGET_MIB, *, dense_mib=0.):
    """Atomic admission/reservation with cleanup on success, error or cancel."""
    token = object()
    with _lock:
        admission = assess_memory(working_mib, budget_mib, dense_mib=dense_mib)
        _reservations[token] = working_mib
    try:
        yield admission
    except MemoryError as exc:
        raise ValueError('Memory allocation failed despite the conservative estimate. Calculation stopped; '
                         'no simulation settings were reduced. Free RAM or choose an explicitly smaller job.') from exc
    finally:
        with _lock:
            del _reservations[token]
