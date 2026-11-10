"""Loss-specific preparation and batched independent events against scalar equations."""
from dataclasses import replace
import threading
import numpy as np
import pytest
from emcd_sim import double_channeling as bw
from emcd_sim.benchmark import nickel_physical_benchmark
from emcd_sim.elastic import BeamSet
from emcd_sim.cancellation import Cancelled
from emcd_sim.gui.channeling import map_detector_batches


@pytest.fixture
def elastic():
    original=nickel_physical_benchmark().elastic
    return replace(original,beams=BeamSet(((0,0,0),(2,0,0),(-2,0,0))))


@pytest.mark.parametrize('loss',[708.1,854.7])
@pytest.mark.parametrize('different_basis',[False,True])
def test_prepared_reference_matches_direct_hamiltonian(elastic,loss,different_basis):
    incoming=bw.prepare_incoming_bloch(elastic,9.,17)
    beams=BeamSet(((0,0,0),(2,0,0))) if different_basis else elastic.beams
    prepared=bw.prepare_outgoing_bloch(elastic,loss,outgoing_beams=beams,prepared_incoming=incoming)
    expected=bw.outgoing_elastic(elastic,(0.,0.),loss,beams).hamiltonian_nm_inv()
    np.testing.assert_allclose(prepared.hamiltonian,expected,rtol=2e-14,atol=1e-15)
    assert not prepared.hamiltonian.flags.writeable
    assert not incoming.hamiltonian.flags.writeable


def test_numerical_sites_match_unchanged_scalar_depth_rule(elastic):
    incoming=bw.prepare_incoming_bloch(elastic,9.,17)
    outgoing=bw.BlochStates.solve(bw.outgoing_elastic(elastic,(.1,.2),831.).hamiltonian_nm_inv())
    rng=np.random.default_rng(19)
    kernel=rng.normal(size=(3,3,3))+.1j*rng.normal(size=(3,3,3))
    phases=np.exp(2j*np.pi*rng.random((11,3,3)))
    actual=bw._numerical_site_responses(incoming.fields,outgoing.ket(incoming.z-9.).conj(),kernel,phases,9.,None)
    expected=np.array([bw.depth_response(incoming,outgoing,kernel*phase[...,None],9.,
        method='numerical',depth_steps=17) for phase in phases])
    np.testing.assert_allclose(actual,expected,rtol=3e-13,atol=1e-13)
    assert np.linalg.eigvalsh(actual).min()>=-1e-12
    calls=[]
    with pytest.raises(Cancelled):
        bw._numerical_site_responses(incoming.fields,outgoing.ket(incoming.z-9.).conj(),kernel,phases,9.,
            lambda:bool(calls) or calls.append(True))


def test_pixel_batches_reuse_reference_and_reject_wrong_energy(elastic,monkeypatch):
    incoming=bw.prepare_incoming_bloch(elastic,9.,17)
    prepared=bw.prepare_outgoing_bloch(elastic,831.,prepared_incoming=incoming)
    def forbidden(*args,**kwargs):pytest.fail('A prepared pixel batch rebuilt the outgoing reference')
    monkeypatch.setattr(bw,'prepare_outgoing_bloch',forbidden)
    kwargs=dict(method='numerical',depth_steps=17,prepared_incoming=incoming,prepared_outgoing=prepared)
    for q in ([[.1,.2]],[[.2,.3]]):
        response=bw.double_channeling_group_responses(elastic,831.,q,9.,{'Ni':elastic.crystal.fractional_positions},**kwargs)
        assert np.linalg.eigvalsh(response['Ni']).min()>=-1e-12
    with pytest.raises(ValueError,match='energy'):
        bw.double_channeling_group_responses(elastic,832.,[[.1,.2]],9.,{'Ni':elastic.crystal.fractional_positions},**kwargs)


@pytest.mark.parametrize('workers',[1,2,4])
def test_executor_records_actual_shared_process_activity(workers):
    barrier=threading.Barrier(workers)
    details={}
    def task(i,cancelled):
        barrier.wait(timeout=3.)
        return i*i
    actual=map_detector_batches(task,range(workers),workers,'bloch',lambda:False,diagnostics=details)
    assert actual==[i*i for i in range(workers)]
    assert len(details['worker_thread_ids'])==workers
    assert details['max_concurrent_tasks']==workers
    assert details['started_tasks']==workers
    assert details['executor']=='ThreadPoolExecutor'
    assert details['active_tasks_after_join']==0


def test_qt_worker_surfaces_executor_failure_without_partial_results(monkeypatch):
    from types import SimpleNamespace
    from emcd_sim.gui import stage_b
    from emcd_sim.gui.geometry import Settings
    from emcd_sim.gui.emcd_forward import ForwardSettings
    before={t.ident for t in threading.enumerate() if t.name.startswith('ThreadPoolExecutor')}
    def fail(*args,**kwargs):
        def task(i,cancelled):raise ValueError('Detector task failed: diagnostic error')
        map_detector_batches(task,range(4),2,'bloch',kwargs['cancelled'] if 'cancelled' in kwargs else args[5])
    monkeypatch.setattr(stage_b,'calculate_multisite',fail)
    worker=stage_b.EMCDWorker(None,Settings(),ForwardSettings(),sites=SimpleNamespace(groups=()))
    failures=[];results=[]
    worker.failed.connect(failures.append);worker.result.connect(results.append)
    worker.run()
    assert failures==['Detector task failed: diagnostic error']
    assert results==[] and 'stopped' in worker.cancellation_times
    assert {t.ident for t in threading.enumerate() if t.name.startswith('ThreadPoolExecutor')}<=before
