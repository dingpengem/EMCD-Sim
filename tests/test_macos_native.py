"""Native platform contracts; no synthetic scientific references."""
import sys
import pytest

pytestmark=pytest.mark.skipif(sys.platform!='darwin',reason='native macOS APIs')

def test_current_memory_units_and_auto_semantics():
    from emcd_sim.memory_budget import memory_snapshot,selected_memory_budget
    s=memory_snapshot()
    assert s['total_ram_mib']>1024
    assert 0<s['available_ram_mib']<=s['total_ram_mib']
    assert 0<s['process_rss_mib']<s['total_ram_mib']
    assert s['process_footprint_mib']>0
    assert selected_memory_budget(1,'automatic',s)==int(s['process_rss_mib']+.5*s['available_ram_mib'])

def test_accelerate_thread_local_control_restored_in_executor():
    from concurrent.futures import ThreadPoolExecutor
    from emcd_sim.parallel_resources import _accelerate_blas,calculation_blas_guard,detector_blas_guard
    runtime=_accelerate_blas()
    if runtime is None:pytest.skip('not an Accelerate build')
    get,_,_=runtime;before=int(get())
    def task():
        initial=int(get())
        with detector_blas_guard():assert int(get())==1
        assert int(get())==initial
    with calculation_blas_guard():
        assert int(get())==1
        with ThreadPoolExecutor(2) as pool:list(pool.map(lambda _:task(),range(4)))
    assert int(get())==before
