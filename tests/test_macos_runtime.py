"""Native resource controls: real memory APIs and per-thread BLAS restoration."""
from concurrent.futures import ThreadPoolExecutor
import sys
import threading

import numpy as np
import pytest

from emcd_sim.gui import parallel_resources as resources
from emcd_sim.gui.channeling import map_detector_batches
from emcd_sim.gui.memory_budget import memory_snapshot

pytestmark=pytest.mark.skipif(sys.platform!='darwin',reason='Native macOS resource APIs')


def test_mach_memory_and_current_rss():
    state=memory_snapshot()
    assert state['available_ram_mib']>0 and state['process_rss_mib']>0
    from resource import getrusage,RUSAGE_SELF
    assert state['process_rss_mib'] <= getrusage(RUSAGE_SELF).ru_maxrss/2**20+1


def test_accelerate_controls_each_thread_and_restores_after_failure():
    runtime=resources._accelerate_blas()
    if runtime is None:pytest.skip('Installed wheels use another BLAS')
    get,_,_=runtime;main=int(get());barrier=threading.Barrier(2)
    def task(fail):
        before=int(get())
        try:
            with resources.detector_blas_guard():
                assert int(get())==1
                barrier.wait(timeout=10)
                np.testing.assert_allclose(np.linalg.eigvalsh([[2.,1.],[1.,2.]]),[1.,3.],rtol=1e-14)
                if fail:raise ValueError('deliberate calculation failure')
        except ValueError:
            if not fail:raise
        assert int(get())==before
        return threading.get_ident()
    with resources.calculation_blas_guard():
        assert int(get())==1
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(task,fail) for fail in (False,True)]
            assert len({f.result() for f in futures})==2
        assert int(get())==1
    assert int(get())==main


def test_detector_dispatch_limits_accelerate_inside_executor():
    runtime=resources._accelerate_blas()
    if runtime is None:pytest.skip('Installed wheels use another BLAS')
    get,_,_=runtime;before=int(get())
    def response(batch,cancelled):
        assert int(get())==1
        return batch*batch
    assert map_detector_batches(response,range(6),2,'bloch',lambda:False)==[n*n for n in range(6)]
    assert int(get())==before
