"""Goal-focused physical consistency tests for the Ni Bloch-wave backend."""
import numpy as np
import pytest
from emcd_sim.crystal import fcc_nickel
from emcd_sim.elastic import BeamSet, depth_coherence
from emcd_sim.geometry import Microscope, electron_wavelength_angstrom
from emcd_sim.scattering import IndependentAtomPotential, nickel_lobato_factor
from emcd_sim.physical_elastic import PhysicalElasticModel
from emcd_sim.benchmark import nickel_physical_benchmark
from emcd_sim.voltage import ConstantMagnetization


def test_ni_lobato_2014_reference_values():
    assert nickel_lobato_factor(0.0) == pytest.approx(6.5649, abs=2e-6)
    assert nickel_lobato_factor(2.0/3.524) == pytest.approx(2.6207411459, rel=1e-8)
    g = np.linspace(0,2.5,50)
    f=nickel_lobato_factor(g)
    assert np.all(np.isfinite(f)) and np.all(f>0)
    assert np.all(np.diff(f)<0)
    with pytest.raises(ValueError):
        nickel_lobato_factor(-.1)


def test_fcc_structure_factor_and_debye_waller():
    ni=fcc_nickel()
    potential=IndependentAtomPotential(ni)
    f200=nickel_lobato_factor(2/3.524)
    assert abs(potential.structure_factor((2,0,0))) == pytest.approx(4*f200)
    assert abs(potential.structure_factor((1,0,0))) < 1e-12
    assert abs(potential.structure_factor((1,1,0))) < 1e-12
    assert potential.structure_factor((2,2,0)) == pytest.approx(
        potential.structure_factor((-2,-2,0)).conjugate())
    b=0.6
    g2=(2/3.524)**2
    with_dw=IndependentAtomPotential(ni, debye_waller_b_angstrom2=b)
    assert abs(with_dw.structure_factor((2,0,0))/potential.structure_factor((2,0,0))) == pytest.approx(np.exp(-b*g2/4))
    assert with_dw.cell_volume_angstrom3 == pytest.approx(3.524**3)
    assert potential.fourier_potential_volts((2,0,0)).real > 0
    with pytest.raises(ValueError):
        IndependentAtomPotential(ni,occupancies=1.1)
    with pytest.raises(ValueError):
        IndependentAtomPotential(ni,debye_waller_b_angstrom2=-.1)


def test_real_hermitian_propagation_and_extinction_distance():
    ni=fcc_nickel()
    model=PhysicalElasticModel(ni, Microscope(200), BeamSet.systematic_row(3))
    H=model.hamiltonian_nm_inv()
    np.testing.assert_allclose(H,H.conj().T,atol=1e-14)
    lam=electron_wavelength_angstrom(200)
    assert H[1,1].real==pytest.approx(-10*np.pi*lam*(2/3.524)**2)
    assert model.extinction_distance_nm((2,0,0)) == pytest.approx(np.pi/abs(H[0,1]))
    assert 35 < model.extinction_distance_nm((2,0,0)) < 41
    z=np.linspace(0,80,101)
    psi=model.amplitudes(z)
    np.testing.assert_allclose(np.sum(abs(psi)**2,axis=1), 1,atol=5e-13)
    np.testing.assert_allclose(psi[0],[1,0,0,0,0,0,0],atol=1e-13)
    coherence=depth_coherence(model,30,steps=33)
    np.testing.assert_allclose(coherence,coherence.conj().T,atol=1e-13)
    assert np.min(np.linalg.eigvalsh(coherence))>-1e-12
    assert np.trace(coherence).real==pytest.approx(1,abs=1e-12)


def test_two_beam_exact_bragg_pendellosung():
    ni=fcc_nickel()
    g200=2/3.524
    lam=electron_wavelength_angstrom(200)
    # At this incident angle the paraboloid diagonal mismatch vanishes.
    bragg_tilt_mrad=-500*lam*g200
    model=PhysicalElasticModel(ni,Microscope(200,(bragg_tilt_mrad,0)),
                               BeamSet(((0,0,0),(2,0,0))))
    H=model.hamiltonian_nm_inv()
    assert abs(H[0,0]-H[1,1]) < 1e-12
    xi=model.extinction_distance_nm((2,0,0))
    assert abs(model.amplitudes(np.array([xi/2]))[0,1])**2==pytest.approx(1,abs=1e-12)
    assert abs(model.amplitudes(np.array([xi]))[0,0])**2==pytest.approx(1,abs=1e-12)


def test_zolz_complete_pairs_and_backend_usage():
    ni=fcc_nickel()
    beams=BeamSet.zolz(ni,1.0,max_beams=13)
    assert len(beams.hkl)>3
    assert all(tuple(-h for h in hkl) in beams.hkl for hkl in beams.hkl)
    assert all(ni.is_allowed(hkl) for hkl in beams.hkl)
    sim=nickel_physical_benchmark(ConstantMagnetization(.6),zone2d_max_g_angstrom_inv=1.0)
    result=sim.run(np.array([850.,852.7,860.,870.]),grid_size=19,depth_steps=10)
    assert np.all(np.isfinite(result.asymmetry()))
    assert np.all(result.detector_spectra['A']>=0)
