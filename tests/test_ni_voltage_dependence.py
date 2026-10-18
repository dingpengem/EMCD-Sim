"""Focused voltage physics, geometry, reference reuse and study-output checks."""
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'outputs/ni_voltage_dependence_100_200_300kv'


@pytest.fixture(scope='module')
def voltage():
    sys.path.insert(0,str(ROOT/'scripts'))
    try:
        spec=importlib.util.spec_from_file_location('voltage_study',ROOT/'scripts/ni_voltage_dependence.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        yield module
    finally:
        sys.path.remove(str(ROOT/'scripts'))


@pytest.fixture(scope='module')
def contexts(voltage):
    path=ROOT/'outputs/gui_stage_d/windows_20261016/reference_project'
    if not path.exists():pytest.skip('Local saved Ni project unavailable')
    saved=voltage.base.load_project(path)
    from dataclasses import replace
    return {kv:voltage.study.make_context(dict(saved,settings=replace(saved['settings'],voltage=float(kv))),
        (0,0,1),2048,systematic_row=True) for kv in voltage.VOLTAGES}


def test_relativistic_quantities_and_extinction_units(voltage,contexts):
    physics={k:voltage.voltage_physics(c)[0] for k,c in contexts.items()}
    expected={100:.03701436614,200:.02507934045,300:.01968748901}
    for kv,p in physics.items():
        assert p['wavelength_angstrom']==pytest.approx(expected[kv],rel=1e-8)
        # Independent SI phase/velocity relation, checked against H/V_G sigma.
        sigma_si=1.602176634e-19/((6.62607015e-34/(2*np.pi))*p['electron_velocity_m_per_s'])*1e-10
        assert p['interaction_constant_rad_per_V_angstrom']==pytest.approx(sigma_si,rel=1e-7)
        assert p['interaction_constant_rad_per_V_nm']==10*p['interaction_constant_rad_per_V_angstrom']
        assert p['xi_200_nm']*p['H_000_200_magnitude_per_nm']==pytest.approx(np.pi,rel=1e-12)
        assert p['ideal_eigenvalue_gap_period_nm']==pytest.approx(p['xi_200_nm'],rel=1e-12)
    assert physics[100]['xi_200_nm']/physics[200]['xi_200_nm']==pytest.approx(.79,abs=.01)
    assert physics[300]['xi_200_nm']/physics[200]['xi_200_nm']==pytest.approx(1.12,abs=.01)
    assert physics[100]['interaction_constant_rad_per_V_angstrom']>physics[200]['interaction_constant_rad_per_V_angstrom']>physics[300]['interaction_constant_rad_per_V_angstrom']
    for kv in (100,300):
        assert physics[kv]['xi_200_nm']/physics[200]['xi_200_nm']==pytest.approx(physics[kv]['electron_velocity_m_per_s']/physics[200]['electron_velocity_m_per_s'],rel=1e-12)


def test_voltage_specific_bragg_tilt_and_fixed_acceptance(voltage,contexts):
    tilts=[]
    for kv,c in contexts.items():
        target=c['hkl'].index((2,0,0));G=c['g'][target]
        assert abs(c['s'][target])<1e-12
        expected=-500*voltage.electron_wavelength_angstrom(kv)*np.linalg.norm(G)
        assert c['settings'].tilt[0]==pytest.approx(expected,abs=1e-12)
        tilts.append(c['settings'].tilt[0])
        np.testing.assert_array_equal(c['centers'],contexts[200]['centers'])
        assert c['cfg'].radius==contexts[200]['cfg'].radius
        np.testing.assert_array_equal(c['ts'][0].tensor_angstrom2_per_ev,contexts[200]['ts'][0].tensor_angstrom2_per_ev)
        assert c['cfg'].eta==c['cfg'].beta==1 and not c['cfg'].correction
    assert len(set(tilts))==3


def test_hamiltonian_does_not_scale_only_by_extinction(voltage,contexts):
    normalized={}
    for kv,c in contexts.items():
        p,a=voltage.voltage_physics(c)
        normalized[kv]=a['hamiltonian_nm_inv']*p['xi_200_nm']
        assert tuple(a['beam_hkl'][p['target_beam_index']])==(2,0,0)
    # Couplings collapse, higher-beam detunings retain gamma dependence.
    offdiag=~np.eye(len(contexts[200]['hkl']),dtype=bool)
    np.testing.assert_allclose(normalized[100][offdiag],normalized[200][offdiag],atol=1e-12)
    assert not np.allclose(np.diag(normalized[100]),np.diag(normalized[200]))


def test_reference_gate_and_fine_point_reuse(voltage,contexts):
    c=contexts[200];d=voltage.study.DetectorGrid(c['centers'],(c['cfg'].radius,),193,.5)
    audit=voltage.inspect_reference(c,d)
    assert audit['coarse_full_curve_recalculated'] is False
    assert audit['coarse_reference_grid']==33 and audit['primary_grid']==193
    point=voltage.reuse_fine_200(12.,c,d)
    with np.load(ROOT/'outputs/ni_prb2007_geometry_validation/checkpoints/B_001_t012_d64_g193_row.npz') as old:
        np.testing.assert_array_equal(point['bloch__raw'][0],old['bloch__raw'][2])
    assert voltage.reuse_fine_200(14.,c,d) is None


@pytest.mark.skipif(not (OUTPUT/'results.npz').exists(),reason='Completed local voltage study unavailable')
def test_complete_sequence_normalization_and_zero_handling(voltage):
    with np.load(OUTPUT/'results.npz',allow_pickle=False) as a:
        assert len(a['thickness_nm'])==612
        for kv in voltage.VOLTAGES:
            for m in voltage.base.METHODS:
                for edge in voltage.base.EDGES:
                    ids=(a['voltage_kv']==kv)&(a['solver']==m)&(a['edge']==edge)
                    np.testing.assert_array_equal(np.sort(a['thickness_nm'][ids]),voltage.base.thickness_sequence())
        zero=a['thickness_nm']==0;valid=~zero
        assert (a['I_A_plus'][zero]==0).all() and (a['I_B_plus'][zero]==0).all()
        for key in voltage.base.METRICS:assert np.isnan(a[key][zero]).all() and np.isfinite(a[key][valid]).all()
        np.testing.assert_allclose(a['prb_relative_dichroism_percent'][valid],100*(a['I_A_plus'][valid]-a['I_B_plus'][valid])/(a['I_A_plus'][valid]+a['I_B_plus'][valid]),atol=1e-12)
        np.testing.assert_allclose(a['D_raw'],a['D_mag']+a['D_even'],atol=1e-13)
        np.testing.assert_allclose(a['normalized_thickness'],a['thickness_nm']/a['xi_200_nm'])
        assert np.max(abs(a['nonmagnetic_imbalance_percent'][valid]))<1e-10
        assert (a['detector_grid']==193).all()


@pytest.mark.skipif(not (OUTPUT/'summary.json').exists(),reason='Completed local voltage study unavailable')
def test_target_population_lookup_and_method_agreement(voltage):
    summary=json.loads((OUTPUT/'summary.json').read_text())
    with np.load(OUTPUT/'results.npz') as a,np.load(OUTPUT/'dynamical_coefficients.npz') as coeff:
        for kv in voltage.VOLTAGES:
            hkl=coeff[f'{kv}kv__beam_hkl'];j=int(np.flatnonzero(np.all(hkl==[2,0,0],axis=1))[0])
            pop=a[f'{kv}kv__bloch__elastic_exit']
            np.testing.assert_allclose(pop.sum(axis=1),1.,atol=1e-12)
            ms=a[f'{kv}kv__fft-multislice__elastic_exit']
            assert np.max(abs(ms-pop))<1e-3
            periods=next(r for r in summary['elastic_periods'] if r['voltage_kv']==kv and r['solver']=='bloch')
            np.testing.assert_array_equal(periods['multibeam_200_peak_thicknesses_nm'],voltage.base.thickness_sequence()[voltage.peak_indices(pop[:,j])])
            for edge in voltage.base.EDGES:
                assert summary['bw_ms_max_abs_prb_difference_pp'][str(kv)][edge]<.001


@pytest.mark.skipif(not (OUTPUT/'preservation.json').exists(),reason='Completed local voltage study unavailable')
def test_preservation_and_figure_exports():
    assert json.loads((OUTPUT/'preservation.json').read_text())['reference_200_files_unchanged']
    assert json.loads((OUTPUT/'preservation.json').read_text())['source_unchanged']
    reference=json.loads((OUTPUT/'reference_reproduction.json').read_text())
    assert max(reference['raw_max_absolute_difference'].values())<1e-12
    meta=json.loads((OUTPUT/'configuration.json').read_text())
    assert meta['numerical_checks']['max_grid_control_prb_difference_pp']<.001
    assert meta['numerical_checks']['max_100nm_BW_depth_error_pp']<.01
    assert meta['post_edge_correction_applied'] is False
    for n in range(1,8):
        for ext in ('png','svg'):assert (OUTPUT/f'figure_{n}.{ext}').stat().st_size>1000
