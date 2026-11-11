"""Bounded existing Ni/AFM Cr fixtures; resource changes only, no benchmarks."""
from dataclasses import replace
import threading
import numpy as np
import pytest

from emcd_sim.cancellation import Cancelled,check_cancelled
from emcd_sim.gui import memory_budget
from emcd_sim.gui.channeling import map_detector_batches
from emcd_sim.gui.parallel_resources import calculation_blas_guard,_blas_runtimes
from emcd_sim.gui.forward_pipeline import calculate_multisite
from test_multisite_forward import system,configuration
from test_multisite_parallel import compare


@pytest.mark.parametrize('method',['bloch','fft-multislice'])
@pytest.mark.parametrize('channel',['single','double'])
def test_cr_auto_and_manual_preserve_existing_serial_intensities(tmp_path,method,channel):
    structure,settings,sites,_=system(tmp_path,'Cr')
    cfg=configuration(propagation=method,channeling_model=channel,angular_maps=True,
        selected_edges=(('first',710.),('last',723.)))
    before=[int(get()) for get,_,_ in _blas_runtimes()]
    with calculation_blas_guard():
        reference=calculate_multisite(structure,settings,sites,cfg,energy_ev=[710.,723.])
        changed=replace(cfg,memory_mode='automatic',worker_mode='automatic' if channel=='single' else 'manual',
            parallel_workers=1 if channel=='single' else 5)
        actual=calculate_multisite(structure,settings,sites,changed,energy_ev=[710.,723.])
        compare(actual,reference)
        assert actual['config'].memory_budget_mib==2048 and actual['config'].memory_mode=='automatic'
        assert actual['config'].calculation_memory_budget_mib==actual['metadata']['numerics']['memory_budget_mib']
        if channel=='double':
            assert actual['metadata']['execution']['effective_workers'][method]==5
            assert all(d['executor']['requested_workers']==5 for d in actual['metadata']['angular_evaluation'])
        for key in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus'):
            assert np.isfinite(actual['spectra'][key]).all() and np.min(actual['spectra'][key])>=-1e-14
        assert all(int(get())==1 for get,_,_ in _blas_runtimes())
    assert [int(get()) for get,_,_ in _blas_runtimes()]==before


@pytest.mark.parametrize('method',['bloch','fft-multislice'])
def test_cancel_failure_restore_blas_and_allow_restart(method):
    before=[int(get()) for get,_,_ in _blas_runtimes()]
    stop=threading.Event();entered=threading.Barrier(2);diagnostic={}
    def response(batch,cancelled):
        entered.wait(timeout=3);stop.set();check_cancelled(cancelled)
    with pytest.raises(Cancelled):map_detector_batches(response,range(4),2,method,stop.is_set,diagnostics=diagnostic)
    assert diagnostic['max_concurrent_tasks']==2
    assert [int(get()) for get,_,_ in _blas_runtimes()]==before
    def fail(batch,cancelled):raise ValueError('deliberate resource-test failure')
    with pytest.raises(ValueError,match='deliberate resource-test failure'):
        map_detector_batches(fail,range(2),2,method,lambda:False)
    assert [int(get()) for get,_,_ in _blas_runtimes()]==before
    def success(batch,cancelled):
        check_cancelled(cancelled);assert all(int(get())==1 for get,_,_ in _blas_runtimes());return batch*2
    assert map_detector_batches(success,range(4),2,method,lambda:False)==[0,2,4,6]
    assert [int(get()) for get,_,_ in _blas_runtimes()]==before


def test_resident_reserved_arrays_are_not_added_to_rss_twice(monkeypatch):
    state=dict(available_ram_mib=16384.,process_rss_mib=64.)
    monkeypatch.setattr(memory_budget,'memory_snapshot',lambda:dict(state))
    with memory_budget.reserve_memory(200,512):
        state['process_rss_mib']+=250  # The admitted array allowance is now resident.
        info=memory_budget.assess_memory(10,512)
        assert info['estimated_process_peak_mib']==454.5
    assert memory_budget.assess_memory(10,512)['concurrent_calculations']==0


@pytest.mark.parametrize('sampling,requested,actual',[('edges',241,2),('uniform',9,11)])
def test_saved_energy_diagnostics_distinguish_request_from_evaluated_grid(tmp_path,sampling,requested,actual):
    from emcd_sim.gui.emcd_forward import ForwardSettings,calculate
    from emcd_sim.gui.geometry import Structure,Settings
    from emcd_sim.gui.project_io import save_project,load_project
    cfg=ForwardSettings(axis_declared=True,grid=9,depth=5,subpixels=8,
        energy_scope='edges' if sampling=='edges' else 'full',energy_sampling=sampling,
        energy_points=requested,worker_mode='manual',parallel_workers=1)
    with calculation_blas_guard():
        result=calculate(Structure.nickel(),Settings(thickness=.2,beam_cutoff=.9,potential_cutoff=1.8),cfg)
    assert len(result['spectra']['energy_ev'])==actual
    info=result['metadata']['numerics']
    assert info['energy_samples']==info['evaluated_energy_samples']==actual
    assert info['requested_uniform_energy_points']==(requested if sampling=='uniform' else None)
    assert result['config'].energy_points==requested
    save_project(result,tmp_path/'saved');restored=load_project(tmp_path/'saved')
    assert restored['config'].energy_points==requested
    for key in ('energy_samples','evaluated_energy_samples','requested_uniform_energy_points'):
        assert restored['metadata']['numerics'][key]==info[key]
    np.testing.assert_array_equal(restored['spectra']['energy_ev'],result['spectra']['energy_ev'])
