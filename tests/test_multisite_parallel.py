"""Bounded detector-thread integration checks and one timing case per solver.

Run Windows parallel BW checks in a fresh process with OPENBLAS_NUM_THREADS=1.
No runtime BLAS changes, subprocess pools, saved timing baselines or speed gates.
"""
from dataclasses import replace
import json
import sys
import threading
from time import perf_counter

import numpy as np
import pytest

from emcd_sim import multislice_double_channeling as ms
from emcd_sim import multisite_double_channeling as multi
from emcd_sim.cancellation import Cancelled, check_cancelled
from emcd_sim.gui import channeling, memory_budget, parallel_resources
from emcd_sim.gui.emcd_forward import calculate
from emcd_sim.gui.forward_pipeline import calculate_multisite
from emcd_sim.gui.propagation import numerical_info
from emcd_sim.multisite_spectrum import ModeledEdgeWindow
from test_multisite_forward import configuration, system as ni_system, RAW_KEYS, PARITY_KEYS
from test_multisite_spectrum import system, disjoint_windows
from test_multisite_numerical_validation import case


@pytest.fixture(scope='module',autouse=True)
def verified_native_threads():
    info=parallel_resources.native_backend_info()
    if sys.platform=='win32':
        assert info['threads']==1, 'Start a fresh Python process with OPENBLAS_NUM_THREADS=1'
    if (info['cpu_count'] or 1)<2:pytest.skip('At least two CPUs required for these parallel checks')


def compare(actual,reference):
    entries=[(actual,reference),(actual['weighted_sum'],reference['weighted_sum'])]
    entries.extend((actual['groups'][key],reference['groups'][key]) for key in reference['groups'])
    for a,b in entries:
        for key in RAW_KEYS+PARITY_KEYS:
            np.testing.assert_allclose(a['spectra'][key],b['spectra'][key],rtol=3e-13,atol=1e-17)
        for label in b['maps']:
            for key in ('I_plus','I_minus','I_mag','I_nonmag'):
                np.testing.assert_allclose(a['maps'][label][key],b['maps'][label][key],rtol=3e-13,atol=1e-17)
    assert actual['metadata']['multisite']['channels']==reference['metadata']['multisite']['channels']
    assert actual['metadata']['multisite']['selected_atom_count']==reference['metadata']['multisite']['selected_atom_count']


@pytest.mark.parametrize('method',['bloch','fft-multislice'])
@pytest.mark.parametrize('overlap',[False,True])
@pytest.mark.parametrize('reverse',[False,True])
def test_serial_parallel_group_totals_windows_and_reversal(tmp_path,method,overlap,reverse):
    structure,settings,sites=system(tmp_path,same_element=overlap)
    windows=(dict(A=ModeledEdgeWindow((704.,720.),(710.,716.)),B=ModeledEdgeWindow((715.,735.),(716.,723.)))
             if overlap else disjoint_windows())
    cfg=configuration(propagation=method,channeling_model='double',angular_maps=True)
    kwargs=dict(energy_windows=windows,reverse_magnetization=reverse)
    serial=calculate_multisite(structure,settings,sites,cfg,**kwargs)
    for workers in (2,4):
        if workers>(parallel_resources.native_backend_info()['cpu_count'] or 1):continue
        actual=calculate_multisite(structure,settings,sites,replace(cfg,parallel_workers=workers),**kwargs)
        compare(actual,serial)
        assert actual['metadata']['execution']['effective_workers'][method]==workers
        assert all(d['workers']==workers for d in actual['metadata']['angular_evaluation'])


@pytest.mark.parametrize('method',['bloch','fft-multislice'])
def test_legacy_single_element_parallel_preserved(tmp_path,method):
    structure,settings,_,refs=ni_system(tmp_path)
    cfg=configuration(propagation=method,channeling_model='double',angular_maps=True)
    keys=('grid','depth','fft_grid','slice_step','subpixels','halfwidth','centers','radius',
          'worker_mode','parallel_workers','propagation','channeling_model','angular_maps')
    cfg=replace(refs[0],**{key:getattr(cfg,key) for key in keys})
    serial=calculate(structure,settings,cfg,energy_ev=[710.,723.])
    parallel=calculate(structure,settings,replace(cfg,parallel_workers=2),energy_ev=[710.,723.])
    for key in RAW_KEYS+PARITY_KEYS:
        np.testing.assert_allclose(parallel['spectra'][key],serial['spectra'][key],rtol=3e-13,atol=1e-17)


def test_group_memory_limits_automatic_workers_and_rejects_manual(tmp_path,monkeypatch):
    structure,settings,sites=system(tmp_path)
    # Resource admission only: no propagation or allocation of the estimated
    # 64 MiB result storage occurs in this controlled-memory case.
    monkeypatch.setattr(memory_budget,'memory_snapshot',lambda:dict(available_ram_mib=32768.,process_rss_mib=100.))
    cfg=configuration(propagation='fft-multislice',channeling_model='double',depth=257,fft_grid=64,
                      memory_budget_mib=512,worker_mode='automatic')
    info=numerical_info(structure,settings,cfg,ionization_sites=sites,additional_retained_working_mib=64.)
    assert info['execution']['effective_workers']['fft-multislice']==1
    assert info['retained_results_working_mib']>=64.
    assert any('limited by' in m for m in info['execution']['messages'])
    with pytest.raises(ValueError,match='Memory admission rejected'):
        numerical_info(structure,settings,replace(cfg,worker_mode='manual',parallel_workers=4),
            ionization_sites=sites,additional_retained_working_mib=64.)


def owned_threads():
    return {t.ident for t in threading.enumerate() if t.name.startswith('ThreadPoolExecutor')}


def test_ordered_executor_preserves_cause_and_joins_workers():
    before=owned_threads()
    ready=threading.Event()
    def fail(batch,cancelled):
        if batch==0:
            ready.set()
            deadline=perf_counter()+2.
            while not cancelled():
                assert perf_counter()<deadline, 'Failed worker did not cancel its sibling'
                threading.Event().wait(.002)
            check_cancelled(cancelled)
        assert ready.wait(1.)
        raise ValueError('originating worker error')
    with pytest.raises(ValueError,match='originating worker error'):
        channeling.map_detector_batches(fail,range(8),2,'fft-multislice',lambda:False)
    assert owned_threads()<=before
    def normal(batch,cancelled):
        check_cancelled(cancelled)
        return batch*batch
    assert channeling.map_detector_batches(normal,range(8),2,'fft-multislice',lambda:False)==[i*i for i in range(8)]
    assert owned_threads()<=before
    def interrupted(batch,cancelled):raise KeyboardInterrupt('worker interrupted')
    with pytest.raises(KeyboardInterrupt,match='worker interrupted'):
        channeling.map_detector_batches(interrupted,[0,1],2,'fft-multislice',lambda:False)
    assert owned_threads()<=before


@pytest.mark.parametrize('method',['bloch','fft-multislice'])
@pytest.mark.parametrize('failure',['cancel','error'])
def test_parallel_pipeline_failure_stops_owned_tasks(tmp_path,monkeypatch,method,failure):
    structure,settings,sites=system(tmp_path)
    stop=threading.Event()
    target=multi if method=='bloch' else ms
    name='double_channeling_group_responses' if method=='bloch' else 'multislice_double_channeling_group_responses'
    original=getattr(target,name)
    def response(*args,**kwargs):
        if failure=='error':raise ValueError('injected response error')
        value=original(*args,**kwargs)
        stop.set()
        return value
    monkeypatch.setattr(target,name,response)
    before=owned_threads()
    cfg=configuration(propagation=method,channeling_model='double',parallel_workers=2,angular_maps=True)
    expected=Cancelled if failure=='cancel' else ValueError
    with pytest.raises(expected):
        calculate_multisite(structure,settings,sites,cfg,energy_windows=disjoint_windows(),cancelled=stop.is_set)
    assert owned_threads()<=before


@pytest.mark.skipif(sys.platform!='win32',reason='Windows native thread policy')
def test_windows_nested_blas_blocked_before_work(tmp_path,monkeypatch):
    structure,settings,sites=system(tmp_path)
    native=dict(parallel_resources.native_backend_info(),threads=2)
    monkeypatch.setattr(parallel_resources,'native_backend_info',lambda:native)
    def forbidden(*args,**kwargs):pytest.fail('Blocked worker request started incoming propagation')
    monkeypatch.setattr(multi,'prepare_incoming_bloch',forbidden)
    import emcd_sim.double_channeling as bw
    monkeypatch.setattr(bw,'prepare_incoming_bloch',forbidden)
    cfg=configuration(channeling_model='double',parallel_workers=2)
    with pytest.raises(ValueError,match='single-thread'):
        calculate_multisite(structure,settings,sites,cfg,energy_windows=disjoint_windows())
    with pytest.raises(ValueError,match='single-thread'):
        channeling.map_detector_batches(forbidden,[0,1],2,'bloch',lambda:False)


@pytest.mark.parametrize('method,name',[('bloch','Cr'),('fft-multislice','Fe3O4')])
def test_one_bounded_timing_configuration_per_solver(tmp_path,monkeypatch,method,name):
    structure,settings,sites,energy,windows=case(tmp_path,name)
    settings=replace(settings,basis_mode='full',beam_cutoff=.75 if name=='Cr' else .36,thickness=.5)
    cfg=configuration(propagation=method,channeling_model='double',grid=17,depth=33,slice_step=.02,angular_maps=True)
    target=multi if method=='bloch' else ms
    function='double_channeling_group_responses' if method=='bloch' else 'multislice_double_channeling_group_responses'
    original=getattr(target,function)
    observed={};lock=threading.Lock()
    def response(*args,**kwargs):
        with lock:observed.setdefault(float(args[1]),set()).add(threading.get_ident())
        return original(*args,**kwargs)
    monkeypatch.setattr(target,function,response)
    measurements=[];serial=None
    for workers in (1,2,4):
        if workers>(parallel_resources.native_backend_info()['cpu_count'] or 1):continue
        observed.clear()
        start=perf_counter()
        result=calculate_multisite(structure,settings,sites,replace(cfg,parallel_workers=workers),energy_ev=energy,energy_windows=windows)
        elapsed=perf_counter()-start
        if serial is None:serial=result
        else:compare(result,serial)
        actual=max(map(len,observed.values()))
        assert actual==workers
        measurements.append(dict(workers=workers,observed_workers=actual,seconds=elapsed,
            speedup=1. if not measurements else measurements[0]['seconds']/elapsed,
            estimated_peak_mib=result['metadata']['numerics']['estimated_process_peak_mib']))
    native=parallel_resources.native_backend_info()
    print(json.dumps(dict(solver=method,synthetic_case=name,grid=cfg.grid,depth=cfg.depth,
        beams=len(serial['metadata']['beam_hkl']),energies_ev=serial['spectra']['energy_ev'].tolist(),
        blas_threads=native['threads'],cpu_count=native['cpu_count'],measurements=measurements)))
