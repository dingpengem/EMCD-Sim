"""Admission follows the actual bounded schedulers and shared FFT preparation."""
from dataclasses import replace
from unittest.mock import patch
import numpy as np
from emcd_sim.gui import memory_budget
from emcd_sim.gui.geometry import Settings,Structure
from emcd_sim.gui.emcd_forward import ForwardSettings
from emcd_sim.gui.propagation import numerical_info
from emcd_sim.multislice_double_channeling import multislice_response_memory_terms
from emcd_sim.gui.parallel_resources import worker_plan,preview_text
from test_multisite_gui_run import sites_for

SNAP=dict(available_ram_mib=32768.,process_rss_mib=150.)


def test_single_full_maps_use_64_pixel_scratch():
    s=Settings(zone=(0,0,1),target=(2,0,0),beam_cutoff=2.)
    with patch.object(memory_budget,'memory_snapshot',return_value=SNAP):
        small=numerical_info(Structure.nickel(),s,ForwardSettings(grid=33))
        large=numerical_info(Structure.nickel(),s,ForwardSettings(grid=97))
    assert small['dense_working_estimate_mib']==large['dense_working_estimate_mib']
    assert large['estimated_working_mib']>small['estimated_working_mib']
    assert large['estimated_process_peak_mib']<512


def test_both_double_backends_share_bounded_local_result_schedule(tmp_path):
    structure,sites=sites_for(tmp_path)
    from emcd_sim.gui.forward_pipeline import MultiSiteForwardSettings
    c=MultiSiteForwardSettings(grid=97,energy_points=4000,depth=64,
        channeling_model='double',selected_edges=(('first',705.),('second',720.)))
    s=Settings(zone=(0,0,1),target=(1,1,0),beam_cutoff=.6,potential_cutoff=1.2,basis_mode='two-beam')
    with patch.object(memory_budget,'memory_snapshot',return_value=SNAP):
        bw=numerical_info(structure,s,c,ionization_sites=sites)
        ms=numerical_info(structure,s,replace(c,propagation='fft-multislice'),ionization_sites=sites)
    for key in ('multisite_energy_block','provider_tensors','selected_group_maps','group_detector_spectra'):
        assert bw['memory_breakdown_mib'][key]==ms['memory_breakdown_mib'][key]
    assert ms['estimated_process_peak_mib']<2048
    assert ms['multislice_worker_memory_mib']['incoming_preparation']==0
    assert sum(ms['memory_breakdown_mib'].values())==ms['estimated_working_mib']


def test_fft_task_accounts_for_owned_fields_only():
    args=(21,21,257,48**2,32,56,3)
    owned=multislice_response_memory_terms(*args)
    shared=multislice_response_memory_terms(*args,prepared_incoming=True)
    assert shared['incoming_preparation']==0 and owned['incoming_preparation']>0
    assert shared['depth_diagnostics']>0 and shared['site_phases']>0
    for key in shared:
        if key!='incoming_preparation':assert shared[key]==owned[key]


def test_accelerate_automatic_mode_has_explicit_reporting():
    native=dict(backend='Accelerate',version='test',threads=None,cpu_count=10,
        platform='darwin',automatic_thread_control=True)
    c=ForwardSettings(channeling_model='double')
    plan=worker_plan(Settings(),c,21,native=native)
    assert not any('Unknown' in s for s in plan['messages'])
    info=dict(execution=plan,bw_beams=21,fft_harmonics=0,dense_working_estimate_mib=1.)
    text=preview_text(Settings(),c,info)
    assert 'fixed count unavailable' in text and 'execution uses verified single-thread mode' in text


def test_local_worker_rejects_a_changed_accepted_concurrency(tmp_path):
    import pytest
    from emcd_sim.gui.forward_pipeline import calculate_multisite,MultiSiteForwardSettings
    structure,sites=sites_for(tmp_path)
    s=Settings(zone=(0,0,1),target=(1,1,0),beam_cutoff=.6,potential_cutoff=1.2,basis_mode='two-beam')
    c=MultiSiteForwardSettings(grid=9,depth=3,channeling_model='double',worker_mode='manual',parallel_workers=1)
    with patch.object(memory_budget,'memory_snapshot',return_value=SNAP):
        with pytest.raises(ValueError,match='Resources changed since preflight'):
            calculate_multisite(structure,s,sites,c,energy_ev=[705.,720.],
                execution_policy={'effective_workers':{'bloch':2}})


def test_automatic_bw_admission_can_reduce_concurrency_but_manual_is_exact():
    native=dict(backend='Accelerate',version='test',threads=1,cpu_count=10,
        platform='darwin',automatic_thread_control=True)
    s=Settings()
    c=ForwardSettings(channeling_model='double',grid=97,depth=64,energy_points=2,memory_budget_mib=512)
    with patch('emcd_sim.gui.parallel_resources.native_backend_info',return_value=native),patch.object(
            memory_budget,'memory_snapshot',return_value=dict(available_ram_mib=32768.,process_rss_mib=360.)):
        automatic=numerical_info(Structure.nickel(),s,c)
        manual=numerical_info(Structure.nickel(),s,replace(c,worker_mode='manual',parallel_workers=4),enforce_execution=False)
    assert 1<=automatic['execution']['effective_workers']['bloch']<4
    assert not automatic['execution']['blocked'] and manual['execution']['blocked']
    assert manual['execution']['effective_workers']['bloch']==4
    assert any('counts limited' in message for message in automatic['execution']['messages'])


def test_depth_quadrature_peak_is_shared_and_not_a_single_pair():
    s=Settings(zone=(0,0,1),target=(2,0,0),beam_cutoff=3.2)
    c=ForwardSettings(depth=1025,grid=33,memory_budget_mib=512)
    with patch.object(memory_budget,'memory_snapshot',return_value=SNAP):
        info=numerical_info(Structure.nickel(),s,c,enforce_execution=False)
    n=info['bw_beams']
    assert info['coherence_working_mib']==64*1025*n*n/2**20
    assert info['execution']['blocked'] and info['estimated_process_peak_mib']>512
