"""Scoped native limits and responsive ordered detector execution."""
import threading
from dataclasses import replace
import pytest
from emcd_sim.cancellation import Cancelled,check_cancelled
from emcd_sim.gui import parallel_resources as resources
from emcd_sim.gui.channeling import map_detector_batches
from emcd_sim.gui.geometry import Settings
from emcd_sim.gui.emcd_forward import ForwardSettings


def test_real_runtimes_limit_and_restore_without_environment_overrides():
    before=resources.native_backend_info()
    assert len(before['runtimes'])>=2
    with resources.calculation_blas_guard():
        during=resources.native_backend_info()
        assert all(row['threads']==1 for row in during['runtimes'])
        observed=map_detector_batches(lambda batch,cancelled:resources.native_backend_info()['runtimes'],
                                      range(4),4,'bloch',lambda:False)
        assert all(row['threads']==1 for rows in observed for row in rows)
    assert resources.native_backend_info()['runtimes']==before['runtimes']


@pytest.mark.parametrize('outcome',['success','error','cancel'])
def test_scope_restores_each_runtime_and_rediscovers(monkeypatch,outcome):
    counts=[12,8];seen=[]
    def discover():
        seen.append(True)
        return [(lambda i=i:counts[i],lambda n,i=i:counts.__setitem__(i,n),
                 dict(library=str(i),parallel=1,threads=counts[i])) for i in range(len(counts))]
    monkeypatch.setattr(resources,'_blas_runtimes',discover)
    def run():
        with resources.calculation_blas_guard():
            assert counts==[1,1]
            if outcome=='error':raise ValueError('response failed')
            if outcome=='cancel':raise Cancelled()
    if outcome=='success':run()
    else:
        with pytest.raises(ValueError if outcome=='error' else Cancelled):run()
    assert counts==[12,8]
    counts.append(6)
    with resources.calculation_blas_guard():assert counts==[1,1,1]
    assert counts==[12,8,6] and len(seen)==2


def test_failed_verification_restores_partial_changes(monkeypatch):
    counts=[12,8]
    monkeypatch.setattr(resources,'_blas_runtimes',lambda:[
        (lambda:counts[0],lambda n:counts.__setitem__(0,n),dict(library='numpy',parallel=1)),
        (lambda:counts[1],lambda n:None,dict(library='scipy',parallel=1))])
    with pytest.raises(ValueError,match='verification failed'):
        with resources.calculation_blas_guard():pytest.fail('Dispatch must not start')
    assert counts==[12,8]


def test_preflight_preserves_four_workers_without_claiming_limits_applied():
    native=dict(resources.native_backend_info(),threads=12,automatic_thread_control=True)
    cfg=replace(ForwardSettings(),channeling_model='double',worker_mode='manual',parallel_workers=4)
    plan=resources.worker_plan(Settings(),cfg,21,native=native)
    assert not plan['blocked'] and plan['effective_workers']['bloch']==4
    assert plan['native']['threads']==12
    assert resources.worker_plan(Settings(),cfg,21,native=dict(native,automatic_thread_control=False))['blocked']


def test_memory_admission_still_rejects_without_reducing_manual_workers(monkeypatch):
    from emcd_sim.gui.propagation import numerical_info
    from emcd_sim.gui.geometry import Structure
    monkeypatch.setattr('emcd_sim.gui.memory_budget.memory_snapshot',
                        lambda:dict(available_ram_mib=64,process_rss_mib=120))
    cfg=replace(ForwardSettings(),channeling_model='double',worker_mode='manual',parallel_workers=4)
    info=numerical_info(Structure.nickel(),Settings(),cfg,enforce_execution=False)
    assert info['execution']['risk']=='RESOURCE REJECTED'
    assert info['execution']['effective_workers']['bloch']==4


def test_completion_progress_does_not_wait_for_first_batch_and_keeps_order():
    release=threading.Event();progress=[];diagnostics={}
    def response(batch,cancelled):
        if batch==0:assert release.wait(2)
        return batch*batch
    def notify(done,total):
        progress.append((done,total))
        if done:release.set()
    result=map_detector_batches(response,range(4),4,'fft-multislice',lambda:False,
                                diagnostics=diagnostics,progress=notify)
    assert result==[0,1,4,9] and progress[0]==(0,4) and progress[-1]==(4,4)
    assert diagnostics['active_tasks_after_join']==0


@pytest.mark.parametrize('failure',['cancel','error'])
def test_cancel_error_joins_workers_restores_limits_and_allows_next_run(failure):
    before=resources.native_backend_info()['runtimes'];stop=threading.Event();diagnostics={}
    def response(batch,cancelled):
        if batch==0:
            if failure=='error':raise ValueError('original worker failure')
            stop.set()
        while True:
            check_cancelled(cancelled)
            stop.wait(.01)
    with pytest.raises(Cancelled if failure=='cancel' else ValueError):
        map_detector_batches(response,range(8),4,'bloch',stop.is_set,diagnostics=diagnostics)
    assert diagnostics['active_tasks_after_join']==0
    assert resources.native_backend_info()['runtimes']==before
    assert map_detector_batches(lambda b,c:b,range(4),4,'bloch',lambda:False)==list(range(4))
