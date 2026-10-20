"""Optional external instrumentation preserves the production result exactly."""
import importlib.util
from pathlib import Path
import numpy as np
import pytest
from emcd_sim import multislice_double_channeling as ms
from emcd_sim.gui.geometry import Structure,Settings,elastic_model
from emcd_sim.ni_017_geometry import Ni017Geometry


def tool():
    spec=importlib.util.spec_from_file_location('ms_profile_tool',Path(__file__).parents[1]/'scripts/profile_ms_double.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def test_import_has_no_production_hooks():
    before=(ms.multislice_double_channeling_response,ms.FFTSplitStep.advance,np.fft.fftn,np.fft.ifftn)
    tool()
    assert before==(ms.multislice_double_channeling_response,ms.FFTSplitStep.advance,np.fft.fftn,np.fft.ifftn)


def test_profile_copy_and_fft_hooks_are_bitwise_identical():
    p=tool();elastic=elastic_model(Structure.nickel(),Settings(thickness=2,beam_cutoff=.9,potential_cutoff=1.8))
    grid=ms.ProjectedNiFFT.build(elastic,grid_points=24,potential_cutoff=1.8,projected_geometry=Ni017Geometry())
    incoming=ms.incident_fields(grid,2,depth_steps=5,slice_step_nm=.04)
    kwargs=dict(fft_grid=24,potential_cutoff=1.8,projected_geometry=Ni017Geometry(),depth_steps=5,slice_step_nm=.04,prepared_grid=grid,prepared_incoming=incoming)
    q=np.array([[.2,.3],[.2,-.3],[0.,0.]])
    expected,diag=ms.multislice_double_channeling_response(elastic,831.4778,q,2,**kwargs)
    timings=p.Timings();instrumented,sites=p.instrumented_response(timings)
    original_advance=ms.FFTSplitStep.advance
    with p.fft_hooks(timings):
        with timings.region('response'):actual,new_diag=instrumented(elastic,831.4778,q,2,**kwargs)
    np.testing.assert_array_equal(actual,expected)
    assert ms.FFTSplitStep.advance is original_advance
    for key in ('incoming_norm_error','outgoing_norm_error','incoming_max_excluded_population','outgoing_max_excluded_population','actual_slice_step_nm','substeps_per_depth_interval'):
        assert new_diag[key]==diag[key]
    report=timings.report();counts=report['counts'];steps=4*incoming[3]
    assert counts['outgoing_advance_calls']==4 and counts['outgoing_split_steps']==steps
    assert counts['fftn_batched_calls']==counts['ifftn_batched_calls']==steps
    assert counts['fftn_individual_transforms']==counts['ifftn_individual_transforms']==3*steps
    assert report['regions']['depth_cartesian_contraction']['calls']==5
    assert {'dipole_kernel','equivalent_site_phases','depth_cartesian_contraction','norm_leakage_diagnostics'}<={s['category'] for s in sites}


def test_hooks_restore_after_exception():
    p=tool();before=(ms.FFTSplitStep.advance,np.fft.fftn,np.fft.ifftn)
    with pytest.raises(RuntimeError):
        with p.fft_hooks(p.Timings()):raise RuntimeError('interrupted profile')
    assert before==(ms.FFTSplitStep.advance,np.fft.fftn,np.fft.ifftn)


def test_saved_reference_setup_never_propagates():
    from unittest.mock import patch
    p=tool()
    if not p.REFERENCE.exists():pytest.skip('Optional saved benchmark unavailable')
    with patch.object(ms,'incident_fields',side_effect=AssertionError('Setup must not propagate')),patch.object(ms,'multislice_double_channeling_response',side_effect=AssertionError('Setup must not calculate outgoing response')):
        case=p.setup()
    assert case['cfg'].depth==64 and len(case['query'])==7857
    assert case['tensors'][0].energy_ev[0]==case['cfg'].l3


def test_optional_ram_sampler_serializes_with_admission(monkeypatch):
    import threading
    p=tool();called=threading.Event()
    def snapshot():
        assert p.memory_budget._lock._is_owned()
        called.set();return dict(process_rss_mib=1.)
    monkeypatch.setattr(p,'memory_snapshot',snapshot)
    with p.SampleRAM() as ram:assert called.wait(1)
    assert ram.samples and ram.samples[0]==1.
