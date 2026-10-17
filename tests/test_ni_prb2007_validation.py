"""Focused geometry, unchanged kernel, explicit row projection and study checks."""
import importlib.util
import json
from dataclasses import replace
from pathlib import Path
import sys

import numpy as np
import pytest
from emcd_sim.elastic import BeamSet
from emcd_sim.multislice_reference import fft_multislice_ni, _projected_ni_potential
from emcd_sim.multislice_emcd_reference import coherence_from_amplitudes
from emcd_sim.single_channeling_tensor import run_tensor_with_coherence
from emcd_sim.ni_017_geometry import Ni017Geometry

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def study():
    sys.path.insert(0,str(ROOT/'scripts'))
    try:
        spec=importlib.util.spec_from_file_location('prb_study',ROOT/'scripts/ni_prb2007_geometry_validation.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        yield module
    finally:
        sys.path.remove(str(ROOT/'scripts'))


@pytest.fixture(scope='module')
def saved(study):
    path=ROOT/'outputs/gui_stage_d/windows_20261016/reference_project'
    if not path.exists():pytest.skip('Local saved Ni project unavailable')
    return study.base.load_project(path)


def test_actual_geometry_bragg_detectors_and_tensor(study,saved):
    c=study.make_context(saved,(0,0,1),2048,systematic_row=True)
    assert len(c['hkl'])==11
    assert all(k==l==0 for h,k,l in c['hkl'])
    np.testing.assert_allclose(c['R'],np.eye(3),atol=1e-14)
    assert abs(c['s'][c['hkl'].index((2,0,0))])<1e-12
    G=c['g'][c['hkl'].index((2,0,0))]
    np.testing.assert_allclose(c['centers'],[G/2+[0,G[0]/2],G/2-[0,G[0]/2]])
    np.testing.assert_allclose(c['ts'][1].tensor_angstrom2_per_ev,c['ts'][0].tensor_angstrom2_per_ev.conj())
    assert c['cfg'].eta==c['cfg'].beta==1
    assert c['settings'].tilt[1]==35


def test_batched_kernel_matches_existing_public_contraction(study,saved):
    c=study.make_context(saved,(0,1,7),2048)
    d=study.DetectorGrid(c['centers'],[c['cfg'].radius],17,1.)
    C=study.analytic_bw_coherence(c['model'].elastic,12.)
    value=study.contract_detectors(c,C,12.,d,batch=3)[0]
    results=[run_tensor_with_coherence(c['model'],tensor,C,thickness_nm=12.,grid_size=17,
        reference_energy_ev=study.base.ENERGIES[0],integration_mode='fractional',aperture_subpixels=64) for tensor in c['ts']]
    raw=np.stack([r.chiral_spectrum(det) for r in results for det in ('A','B')],axis=1)
    np.testing.assert_allclose(value,raw,rtol=1e-12,atol=1e-14)


def test_analytic_bw_integral_against_independent_dense_quadrature(study,saved):
    c=study.make_context(saved,(0,1,7),2048)
    elastic=replace(c['model'].elastic,beams=BeamSet(((0,0,0),(2,0,0),(4,0,0))))
    z=np.linspace(0,3.,2049)
    numeric=coherence_from_amplitudes(z,elastic.amplitudes(z))
    exact=study.analytic_bw_coherence(elastic,3.)
    np.testing.assert_allclose(exact,numeric,atol=1e-8,rtol=1e-6)
    assert np.linalg.eigvalsh(exact).min()>-1e-12
    assert np.trace(exact).real==pytest.approx(1.)


def test_aperture_support_bounds_area_and_symmetry(study,saved):
    c=study.make_context(saved,(0,0,1),2048,systematic_row=True)
    d=study.DetectorGrid(c['centers'],study.RADII,193,.5)
    assert np.all((d.weights>=0)&(d.weights<=1))
    np.testing.assert_allclose(d.weights[:,0],d.weights[:,1,::-1,:],atol=0,rtol=0)
    np.testing.assert_allclose(d.areas[:,0],np.pi*np.array(study.RADII)**2,rtol=1e-3)
    assert 2*min(study.RADII)/np.sqrt(d.dq2)>11


def test_optional_row_potential_and_propagation(study,saved):
    row,_,g=_projected_ni_potential(32,200.,0.,2.2,systematic_row_hkl=(2,0,0))
    np.testing.assert_allclose(row,row[:,0,None]*np.ones((1,32)),atol=1e-14)
    c=study.make_context(saved,(0,0,1),2048,systematic_row=True)
    z=np.array([0.,10.])
    fft=fft_multislice_ni(z,tilt_mrad_xy=c['settings'].tilt,grid_points=32,slice_step_nm=.04,
        potential_cutoff_inv_angstrom=2.2,return_amplitudes=True,systematic_row_hkl=(2,0,0))
    assert fft.systematic_row_hkl==(2,0,0)
    assert fft.norm_error<1e-11
    assert fft.intensity[:,fft.beam_hkl[:,1]!=0].max()<1e-25
    from emcd_sim.multislice_emcd_reference import project_fft_amplitudes
    projected,_=project_fft_amplitudes(fft,c['hkl'])
    np.testing.assert_allclose(projected,c['model'].elastic.amplitudes(z),atol=2e-4,rtol=1e-3)
    for invalid in ((0,0,0),(1.5,0,0),(1,0),(np.nan,0,0)):
        with pytest.raises(ValueError,match='Systematic row'):
            _projected_ni_potential(32,200.,0.,2.2,systematic_row_hkl=invalid)


def test_default_projected_fft_stays_byte_identical_to_saved(study,saved):
    cfg=saved['config'];settings=saved['settings']
    fft=fft_multislice_ni(saved['depth_nm'],acceleration_kv=settings.voltage,tilt_mrad_xy=settings.tilt,
        grid_points=cfg.fft_grid,slice_step_nm=cfg.slice_step,potential_cutoff_inv_angstrom=settings.potential_cutoff,
        b_factor_angstrom2=settings.b_factor,return_amplitudes=True,projected_geometry=Ni017Geometry())
    assert fft.systematic_row_hkl is None
    np.testing.assert_array_equal(fft.amplitudes,saved['fft']['full_amplitudes'])


def test_completed_study_and_honest_3d_status(study):
    root=ROOT/'outputs/ni_prb2007_geometry_validation'
    if not (root/'summary.json').exists():pytest.skip('Local completed study unavailable')
    with np.load(root/'results.npz',allow_pickle=False) as data:
        np.testing.assert_array_equal(np.unique(data['energy_ev']),study.base.ENERGIES)
        assert not any('atomic-3D' in str(m) for m in data['potential_model'])
        ids=(data['stage']=='A')&(data['solver']=='bloch')&(data['edge']=='L3')
        np.testing.assert_array_equal(np.sort(data['thickness_nm'][ids]),study.base.thickness_sequence())
        zeros=data['thickness_nm']==0
        assert np.isnan(data['prb_relative_dichroism_percent'][zeros]).all()
        assert (data['I_A_plus'][zeros]==0).all()
        valid=~zeros
        np.testing.assert_allclose(data['prb_relative_dichroism_percent'][valid],
            100*(data['I_A_plus'][valid]-data['I_B_plus'][valid])/(data['I_A_plus'][valid]+data['I_B_plus'][valid]),atol=1e-12)
        assert np.all(data['eta']==1) and np.all(data['beta']==1)
        with np.load(ROOT/'outputs/ni_017_thickness_0_100nm/thickness_series.npz') as old:
            for method in study.base.METHODS:
                for t in study.DEPTH_THICKNESSES:
                    for ie,edge in enumerate(study.base.EDGES):
                        ids=(data['stage']=='C')&(data['solver']==method)&(data['thickness_nm']==t)&(data['depth_nodes']==64)&(data['edge']==edge)
                        for key in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus'):
                            assert data[key][ids][0]==old[method+'__'+key][int(t/2),ie]
        np.testing.assert_allclose(data['D_raw'],data['D_mag']+data['D_even'],atol=1e-13)
    status=json.loads((root/'atomic_3d_readiness.json').read_text())
    assert status['no_full_3d_scan'] and status['no_projected_potential_substitution']
    assert status['atoms_per_repeat']==status['planes_per_repeat']==50
    assert json.loads((root/'preservation.json').read_text())['original_017_files_unchanged']
    for n in range(1,6):
        for ext in ('png','svg'):assert (root/f'figure_{n}.{ext}').stat().st_size>1000
