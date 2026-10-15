"""Focused independent-wave phase/coherence and shared-contraction checks."""
from dataclasses import replace
import csv
import json

import numpy as np
import pytest

from emcd_sim.benchmark import nickel_physical_benchmark
from emcd_sim.crystal import fcc_nickel
from emcd_sim.elastic import BeamSet, depth_coherence
from emcd_sim.elastic_reference import FourierCutoffPotential
from emcd_sim.geometry import Microscope
from emcd_sim.multislice_reference import fft_multislice_ni
from emcd_sim.physical_elastic import PhysicalElasticModel
from emcd_sim.scattering import IndependentAtomPotential
from emcd_sim.single_channeling_tensor import run_tensor_single_channeling, run_tensor_with_coherence
from emcd_sim.xmcd_effective_mdff import effective_tensor_from_xmcd
from emcd_sim.multislice_emcd_reference import (
    MultisliceEMCDConfig, coherence_from_amplitudes, complex_wave_diagnostics,
    project_fft_amplitudes, run_multislice_emcd_reference,
    save_multislice_emcd_reference, plot_multislice_emcd_reference, check_propagation_controls,
)


@pytest.fixture
def xmcd(tmp_path):
    path=tmp_path/'synthetic.xmcd'
    e=np.array([837.,852.7,870.,882.])
    rp,lp=np.array([1.,3.,2.,1.]),np.array([1.,2.,3.,1.])
    np.savetxt(path,np.column_stack((e,rp,lp,rp-lp,rp+lp)))
    return path


def test_fft_export_initial_norm_and_historical_behavior():
    opts=dict(grid_points=16,slice_step_nm=.02,potential_cutoff_inv_angstrom=.6,
              tilt_mrad_xy=(-7.,25.),b_factor_angstrom2=.1)
    plain=fft_multislice_ni((0.,.2,1.),**opts)
    exported=fft_multislice_ni((0.,.2,1.),return_amplitudes=True,**opts)
    assert plain.amplitudes is None
    np.testing.assert_array_equal(plain.intensity,exported.intensity)
    np.testing.assert_array_equal(exported.amplitudes[0],np.eye(1,16**2,dtype=complex)[0])
    np.testing.assert_array_equal(abs(exported.amplitudes)**2,exported.intensity)
    assert exported.norm_error<1e-12
    np.testing.assert_allclose(np.sum(abs(exported.amplitudes)**2,axis=1),1.,atol=1e-12)
    np.testing.assert_allclose(exported.reciprocal_xy_inv_angstrom,
                               exported.beam_hkl[:,:2]/3.524,atol=1e-14)


def test_fft_hkl_mapping_positive_fourier_phase():
    fft=fft_multislice_ni((0.,),grid_points=16,potential_cutoff_inv_angstrom=.6,return_amplitudes=True)
    x,y=np.meshgrid(np.arange(16)/16,np.arange(16)/16,indexing='ij')
    # Known +phase waves, with unequal complex coefficients so signs/conjugation matter.
    wave=(.3+.2j)*np.exp(2j*np.pi*(x-2*y))+.4j*np.exp(2j*np.pi*(-x+y))
    coeff=(np.fft.fft2(wave)/16**2).reshape(1,-1)
    synthetic=replace(fft,amplitudes=coeff,intensity=abs(coeff)**2)
    projected,outside=project_fft_amplitudes(synthetic,((2,-4,0),(-2,2,0),(0,0,0)))
    np.testing.assert_allclose(projected,[[.3+.2j,.4j,0]],atol=1e-14)
    np.testing.assert_allclose(outside,0,atol=1e-28)
    one,excluded=project_fft_amplitudes(synthetic,((2,-4,0),))
    assert abs(one[0,0])**2==pytest.approx(.13)
    assert excluded[0]==pytest.approx(.16)  # Projected amplitude was not normalized to one.
    with pytest.raises(ValueError,match='outside FFT'):
        project_fft_amplitudes(synthetic,((100,0,0),))
    with pytest.raises(ValueError,match='return_amplitudes'):
        project_fft_amplitudes(replace(synthetic,amplitudes=None),((0,0,0),))


@pytest.mark.parametrize('tilt',[(0.,0.),(-7.11672544,25.)])
def test_controlled_independent_phase_and_coherence(tilt):
    crystal=fcc_nickel(); beams=BeamSet.zolz(crystal,1.8,81)
    potential=FourierCutoffPotential(IndependentAtomPotential(crystal),.6)
    model=PhysicalElasticModel(crystal,Microscope(200.,tilt),beams,potential)
    depths=np.array([0.,.001,.3,1.])
    fft=fft_multislice_ni(depths,tilt_mrad_xy=tilt,grid_points=16,
        slice_step_nm=.005,potential_cutoff_inv_angstrom=.6,return_amplitudes=True)
    ms,outside=project_fft_amplitudes(fft,beams.hkl)
    bw=model.amplitudes(depths)
    # d psi_g/dz = +i*H_g0 fixes the potential transmission sign independently.
    j=beams.hkl.index((2,0,0)); coupling=model.hamiltonian_nm_inv()[j,0].real
    assert ms[1,j].imag/(coupling*depths[1])==pytest.approx(1.,abs=2e-6)
    np.testing.assert_allclose(ms,bw,atol=2e-6)
    assert outside.max()<1e-7
    for psi in (bw,ms):
        c=coherence_from_amplitudes(depths,psi)
        np.testing.assert_allclose(c,c.conj().T,atol=1e-14)
        assert np.linalg.eigvalsh(c).min()>-1e-12
    np.testing.assert_allclose(coherence_from_amplitudes(depths,bw),
                               coherence_from_amplitudes(depths,ms),atol=2e-6)
    phases=np.array([0.,.4,-.2,1.1])
    rephased=ms*np.exp(1j*phases[:,None])
    np.testing.assert_allclose(coherence_from_amplitudes(depths,ms),
                               coherence_from_amplitudes(depths,rephased),atol=1e-14)
    diagnostics=complex_wave_diagnostics(ms,rephased)
    np.testing.assert_allclose(diagnostics['global_phase_ms_vs_bw'],phases,atol=1e-14)
    assert diagnostics['amplitude_max_abs_aligned'].max()<1e-14


def test_shared_contraction_preserves_original_and_projected_norm(xmcd):
    model=nickel_physical_benchmark(beam_order=1,diffraction_condition='near-2bc')
    t=effective_tensor_from_xmcd(xmcd)
    c=depth_coherence(model.elastic,3.,8)
    sampled=coherence_from_amplitudes(np.linspace(0.,3.,8),model.elastic.amplitudes(np.linspace(0.,3.,8)))
    np.testing.assert_array_equal(c,sampled)
    original=run_tensor_single_channeling(model,t,thickness_nm=3.,grid_size=17,depth_steps=8)
    shared=run_tensor_with_coherence(model,t,c,thickness_nm=3.,grid_size=17)
    half=run_tensor_with_coherence(model,t,.5*c,thickness_nm=3.,grid_size=17)
    for key in original.detector_spectra:
        np.testing.assert_array_equal(original.detector_spectra[key],shared.detector_spectra[key])
        np.testing.assert_allclose(half.detector_spectra[key],.5*shared.detector_spectra[key],atol=1e-14)
    np.testing.assert_array_equal(original.nonmag_map_at_l3,shared.nonmag_map_at_l3)
    np.testing.assert_array_equal(original.magnetic_map_at_l3,shared.magnetic_map_at_l3)
    with pytest.raises(ValueError,match='positive semidefinite'):
        run_tensor_with_coherence(model,t,-c,grid_size=17)


def test_independent_emcd_parity_and_outputs(xmcd,tmp_path):
    config=MultisliceEMCDConfig(conditions=('zone-axis','near-2bc'),thickness_nm=(1.,3.),
        potential_cutoff=.6,beam_cutoff=1.4,fft_grid=16,slice_step_nm=.01,
        depth_steps=8,detector_grid=17)
    plus=run_multislice_emcd_reference(xmcd,config)
    minus=run_multislice_emcd_reference(xmcd,replace(config,eta=-1))
    zero=run_multislice_emcd_reference(xmcd,replace(config,eta=0))
    for p,m,z in zip(plus.records,minus.records,zero.records):
        assert p['A_mag']==pytest.approx(-m['A_mag'],abs=1e-13)
        assert p['A_nonmag']==pytest.approx(m['A_nonmag'],abs=1e-13)
        assert z['Delta_mag']==pytest.approx(0,abs=1e-14)
        assert z['A_mag']==pytest.approx(0,abs=1e-14)
        assert p['delta_plus']==pytest.approx(p['Delta_mag']+p['Delta_nonmag'],abs=1e-13)
        assert p['Sigma_ref']>0
    for c in plus.cases:
        assert c['coherence_fro_abs']<1e-3
        assert c['ms_norm_error']<1e-12
        for m in c['method_maps']:
            assert min(m['I_plus'].min(),m['I_minus'].min())>=-1e-8
            np.testing.assert_allclose(m['I_plus'],m['I_mag']+m['I_nonmag'],atol=1e-13)
        assert abs(np.trace(c['coherence_ms']).real-1)<=c['fft_outside_intensity'].max()+1e-12
    # No calibrated Ni values: agreement assessed for a deliberately short, controlled calculation.
    assert max(c['scalar_discrepancies']['A_mag']['absolute'] for c in plus.cases)<1e-4
    check=check_propagation_controls(plus)
    assert check['common_basis_count']==21 and check['larger_bloch_basis_count']==37
    assert check['slice_steps_nm']==[.01,.005]
    assert check['fine_ms_vs_larger_bw_projected_coherence_fro']<1e-3
    plus.metadata['targeted_propagation_check']=check
    output=tmp_path/'method comparison paths with spaces'
    save_multislice_emcd_reference(plus,output); plot_multislice_emcd_reference(plus,output)
    meta=json.loads((output/'comparison_metadata.json').read_text(encoding='utf-8'))
    for key in ('absolute_cross_section','outgoing_channeling','quantitative_Ni','independent_mdff_validation','atom_layer_resolved_3d'):
        assert meta[key] is False
    assert meta['config']['potential_cutoff']==.6 and meta['config']['beam_cutoff']==1.4
    assert meta['config']['depth_steps']==8 and meta['config']['slice_step_nm']==.01
    assert meta['selected_energy_ev']==852.7
    assert meta['targeted_propagation_check']==json.loads((output/'targeted_propagation_check.json').read_text())
    import hashlib
    assert meta['xmcd_sha256']==hashlib.sha256(xmcd.read_bytes()).hexdigest()
    assert meta['pair_array_memory_estimate_mib']<meta['config']['max_kernel_mib']
    with np.load(output/'elastic_complex_comparison.npz',allow_pickle=False) as e:
        assert e['bw_amplitudes'].shape==e['ms_amplitudes_projected'].shape==(4,8,21)
        np.testing.assert_array_equal(e['beam_hkl'],meta['beam_hkl'])
        assert e['fft_outside_intensity'].min()>=0
        assert e['phase_valid'].all()
    with np.load(output/'coherence_comparison.npz',allow_pickle=False) as c:
        assert c['coherence_bw'].shape==c['coherence_ms'].shape==(4,21,21)
    with np.load(output/'emcd_method_comparison.npz',allow_pickle=False) as d:
        assert d['I_mag'].shape==(8,17,17) and d['I_nonmag'].shape==(8,17,17)
        assert {'A_raw_plus','A_raw_minus','A_mag','A_nonmag','Delta_mag','Delta_nonmag','Sigma_ref','f_mag','valid'}<=set(d.files)
    with (output/'emcd_method_comparison.csv').open(newline='',encoding='utf-8') as f:
        assert len(list(csv.DictReader(f)))==8
    assert (output/'bloch_multislice_emcd_comparison.png').stat().st_size>1000


def test_control_guards(xmcd):
    config=MultisliceEMCDConfig(conditions=('zone-axis',),thickness_nm=(1.,),detector_grid=17)
    for change in ({'slice_step_nm':0},{'fft_grid':13},{'depth_steps':1},{'thickness_nm':(3.,1.)}):
        with pytest.raises(ValueError):
            run_multislice_emcd_reference(xmcd,replace(config,**change))
    with pytest.raises(ValueError,match='working memory'):
        run_multislice_emcd_reference(xmcd,replace(config,max_kernel_mib=.001))
    with pytest.raises(ValueError,match='cap clips'):
        run_multislice_emcd_reference(xmcd,replace(config,max_beams=8))
    with pytest.raises(ValueError,match='Nyquist'):
        run_multislice_emcd_reference(xmcd,replace(config,beam_cutoff=3.,fft_grid=12))
