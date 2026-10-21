"""Focused independent-wave phase/coherence and shared-contraction checks."""
from dataclasses import replace
import csv
import json

import numpy as np
import pytest

from emcd_sim.benchmark import nickel_physical_benchmark
from emcd_sim.crystal import fcc_nickel
from emcd_sim.elastic import BeamSet, depth_coherence
from emcd_sim.scattering import FourierCutoffPotential
from emcd_sim.geometry import Microscope
from emcd_sim.multislice_reference import fft_multislice_ni
from emcd_sim.physical_elastic import PhysicalElasticModel
from emcd_sim.scattering import IndependentAtomPotential
from emcd_sim.single_channeling_tensor import run_tensor_single_channeling, run_tensor_with_coherence
from emcd_sim.xmcd_effective_mdff import effective_tensor_from_xmcd
from emcd_sim.multislice_reference import coherence_from_amplitudes, complex_wave_diagnostics, project_fft_amplitudes


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
