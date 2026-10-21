"""Independent FCC Ni elastic FFT versus Bloch-wave reference checks."""
import json
import numpy as np
import pytest

from emcd_sim.multislice_reference import _projected_ni_potential, fft_multislice_ni
from emcd_sim.scattering import FourierCutoffPotential
from runtime_fixtures import _compare_spots
from emcd_sim.scattering import IndependentAtomPotential
from emcd_sim.crystal import fcc_nickel
from emcd_sim.geometry import electron_wavelength_angstrom, Microscope
from emcd_sim.elastic import BeamSet
from emcd_sim.physical_elastic import PhysicalElasticModel


def test_fft_potential_matches_physical_structure_factor_and_reality():
    u,hkl,g = _projected_ni_potential(24,200.,0.,2.2)
    assert u.shape == (24,24)
    assert tuple(hkl[0]) == (0,0,0)
    crystal = fcc_nickel()
    source = IndependentAtomPotential(crystal)
    prefactor = 10*(1+200000/510998.95)*electron_wavelength_angstrom(200.) / source.cell_volume_angstrom3
    fft = np.fft.fft2(u)/u.size
    # Projected [001] periodic cell has hkl=(2m,2n,0).
    np.testing.assert_allclose(fft[1,0],prefactor*source.structure_factor((2,0,0)),atol=1e-12)
    np.testing.assert_allclose(fft[0,1],prefactor*source.structure_factor((0,2,0)),atol=1e-12)
    np.testing.assert_allclose(fft[0,0],0,atol=1e-12)


def test_fft_propagation_preserves_flux_and_responds_to_tilt():
    depth=(0.,10.,30.)
    zero = fft_multislice_ni(depth,grid_points=24,slice_step_nm=.15,
                            potential_cutoff_inv_angstrom=1.8)
    tilted = fft_multislice_ni(depth,tilt_mrad_xy=(0.,25.),grid_points=24,
                              slice_step_nm=.15,potential_cutoff_inv_angstrom=1.8)
    assert zero.norm_error < 1e-10
    assert tilted.norm_error < 1e-10
    assert zero.intensity_at((0,0,0))[0] == pytest.approx(1.,abs=1e-12)
    assert abs(zero.intensity_at((0,0,0))[2]-tilted.intensity_at((0,0,0))[2])>1e-3


def test_independent_fft_matches_bloch_same_truncated_potential():
    crystal=fcc_nickel()
    cutoff=2.2
    beams=BeamSet.zolz(crystal,3.4,max_beams=150)
    original=IndependentAtomPotential(crystal)
    bloch=PhysicalElasticModel(crystal,Microscope(200.,(0.,0.)),beams,
                               potential=FourierCutoffPotential(original,cutoff))
    depth=np.asarray((10.,30.))
    bint=np.abs(bloch.amplitudes(depth))**2
    fft=fft_multislice_ni(tuple(depth),potential_cutoff_inv_angstrom=cutoff,
                          grid_points=32,slice_step_nm=.08)
    np.testing.assert_allclose(fft.intensity_at((0,0,0)),bint[:,0],atol=0.002)
    for i in range(len(depth)):
        assert _compare_spots(beams.hkl,bint[i],fft.beam_hkl,fft.intensity[i])<0.003
