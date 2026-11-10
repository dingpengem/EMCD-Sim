"""BW admission follows live numerical/analytic allocations; no large jobs."""
from dataclasses import replace
from unittest.mock import patch
import numpy as np
import pytest

from emcd_sim.double_channeling import bloch_response_memory_terms
from emcd_sim.gui import memory_budget as memory
from emcd_sim.gui.forward_pipeline import MultiSiteForwardSettings
from emcd_sim.gui.propagation import numerical_info,multisite_bw_double_memory_terms
from emcd_sim.gui.geometry import Settings,Structure


def test_depth_methods_charge_only_allocated_mode_integrals():
    args=(59,59,64,64,(8,8,8))
    numeric=bloch_response_memory_terms(*args,'numerical')
    analytic=bloch_response_memory_terms(*args,'analytic')
    assert numeric['analytic_mode_integrals']==0
    assert analytic['analytic_mode_integrals']==80*59**4/2**20
    assert numeric['paired_depth_fields']==16*64*59**2/2**20
    assert sum(numeric.values())<sum(analytic.values())
    with pytest.raises(ValueError,match='Depth method'):
        bloch_response_memory_terms(*args,'unknown')


@pytest.mark.parametrize('evaluation',['selected','all'])
def test_multisite_blocks_respect_actual_sampling_and_map_aliases(evaluation):
    c=MultiSiteForwardSettings(grid=97,energy_points=486,angular_evaluation=evaluation,
        selected_edges=(('a:first',1.),('b:first',1.),('a:second',2.),('b:second',3.)))
    terms=multisite_bw_double_memory_terms(c,3,160)
    count=max(3*97**2,16*160) if evaluation=='selected' else 486*97**2
    assert terms['multisite_energy_block']==16*count*18/2**20
    assert terms['selected_group_maps']==128*4*97**2*5/2**20
    assert terms['provider_tensors']==576*486*3/2**20
    assert terms['detector_reduction_work']==(32*(16 if evaluation=='selected' else 486)*97**2+16*97**2)/2**20
    no_maps=multisite_bw_double_memory_terms(replace(c,angular_maps=False),3,160)
    assert no_maps['selected_group_maps']==0


def test_thread_workers_share_preparation_and_retained_data_once():
    c=MultiSiteForwardSettings(channeling_model='double',worker_mode='manual',parallel_workers=1,
        grid=9,energy_points=3,selected_edges=(('one',708.1),))
    snap=dict(available_ram_mib=32768.,process_rss_mib=100.)
    with patch.object(memory,'memory_snapshot',return_value=snap):
        a=numerical_info(Structure.nickel(),Settings(),c,enforce_execution=False)
        b=numerical_info(Structure.nickel(),Settings(),replace(c,parallel_workers=4),enforce_execution=False)
    assert a['retained_results_working_mib']==b['retained_results_working_mib']
    scratch=a['memory_breakdown_mib']['per_worker_scratch']
    np.testing.assert_allclose(b['estimated_working_mib']-a['estimated_working_mib'],3*scratch)
    assert a['process_rss_mib']==b['process_rss_mib']==100.
    assert a['allocation_margin']==1.25 and a['process_reserve_mib']==128.


def test_budget_and_ram_rejections_remain_active():
    c=MultiSiteForwardSettings(channeling_model='double',worker_mode='manual',parallel_workers=4)
    with patch.object(memory,'memory_snapshot',return_value=dict(available_ram_mib=32768.,process_rss_mib=5000.)):
        with pytest.raises(ValueError,match='Memory admission rejected'):
            numerical_info(Structure.nickel(),Settings(),c)
