"""Infrastructure controls use synthetic factors, never an unverified atomic table."""
import numpy as np
import pytest

from emcd_sim.crystal import Crystal, fcc_nickel
from emcd_sim.elastic import BeamSet
from emcd_sim.geometry import Microscope
from emcd_sim.physical_elastic import PhysicalElasticModel
from emcd_sim.scattering import (IndependentAtomPotential, FourierCutoffPotential,
                                 elastic_reflection_allowed, nickel_lobato_factor)


def cscl():
    return Crystal(np.eye(3)*4.1, np.array([[0.,0,0],[.5,.5,.5]]), ('Cs','Cl'))


def synthetic_potential(crystal):
    # Deliberately NOT physical Cs/Cl factors. Test species weighting only.
    return IndependentAtomPotential(crystal, atomic_factors={
        'Cs': lambda g: 3/(1+g*g), 'Cl': lambda g: 1/(1+g*g)})


def test_cscl_100_weighted_selection_and_bloch_acceptance():
    crystal = cscl(); potential = synthetic_potential(crystal)
    assert not crystal.is_allowed((1,0,0))  # Equal-atom test is wrong for CsCl.
    assert potential.structure_factor((1,0,0)) == pytest.approx(2/(1+(1/4.1)**2))
    beams = BeamSet.zolz(crystal, .36, max_beams=13, potential=potential)
    assert (1,0,0) in beams.hkl and (-1,0,0) in beams.hkl
    model = PhysicalElasticModel(crystal, Microscope(200), beams, potential)
    h = model.hamiltonian_nm_inv()
    np.testing.assert_allclose(h, h.conj().T, atol=1e-15)
    wave = model.amplitudes(np.array([0.,1.,5.]))
    np.testing.assert_allclose(np.sum(abs(wave)**2,axis=1),1,atol=2e-14)
    assert abs(wave[-1,beams.hkl.index((1,0,0))])**2 > 0


def test_true_extinction_and_cutoff_are_distinct():
    crystal = Crystal(np.eye(3)*4.1, np.array([[0.,0,0],[.5,.5,.5]]), ('Ni','Ni'))
    potential = IndependentAtomPotential(crystal)
    assert not elastic_reflection_allowed(crystal,(1,0,0),potential)
    assert elastic_reflection_allowed(crystal,(1,1,0),potential)
    cutoff = FourierCutoffPotential(potential,.1)
    assert cutoff.structure_factor((1,1,0)) == 0j
    assert elastic_reflection_allowed(crystal,(1,1,0),cutoff)
    beams = BeamSet.zolz(crystal,.36,max_beams=13,potential=cutoff)
    assert (1,0,0) not in beams.hkl and (1,1,0) in beams.hkl
    with pytest.raises(ValueError,match='Extinct'):
        PhysicalElasticModel(crystal,Microscope(200),BeamSet(((0,0,0),(1,0,0))),potential)


def test_species_occupancy_b_phase_and_potential_units():
    crystal=cscl();base=synthetic_potential(crystal)
    potential=IndependentAtomPotential(crystal, occupancies=(.5,1.),
        debye_waller_b_angstrom2=(.4,.8),atomic_factors=base.atomic_factors)
    h=(1,0,0);g=1/4.1
    expected=.5*3/(1+g*g)*np.exp(-.4*g*g/4)-1/(1+g*g)*np.exp(-.8*g*g/4)
    assert potential.structure_factor(h)==pytest.approx(expected)
    assert potential.structure_factor((-1,0,0))==pytest.approx(potential.structure_factor(h).conjugate())
    assert potential.fourier_potential_volts(h)==pytest.approx(2*np.pi*7.619964231073853*expected/4.1**3)


def test_historical_ni_factors_beams_and_propagation_unchanged():
    crystal=fcc_nickel();potential=IndependentAtomPotential(crystal)
    legacy=BeamSet.zolz(crystal,1.2,25)
    weighted=BeamSet.zolz(crystal,1.2,25,potential=potential)
    assert legacy.hkl==weighted.hkl
    for h in legacy.hkl:
        g=np.linalg.norm(crystal.g_vector(h))
        expected=np.exp(-2j*np.pi*(crystal.fractional_positions@h)).sum()*nickel_lobato_factor(g)
        assert potential.structure_factor(h)==pytest.approx(expected,abs=1e-14)
    a=PhysicalElasticModel(crystal,Microscope(200),legacy)
    b=PhysicalElasticModel(crystal,Microscope(200),weighted,potential)
    np.testing.assert_array_equal(a.hamiltonian_nm_inv(),b.hamiltonian_nm_inv())
    np.testing.assert_array_equal(a.amplitudes(np.array([0.,9.,30.])),b.amplitudes(np.array([0.,9.,30.])))


def test_invalid_factor_and_wrong_crystal_rejected():
    crystal=cscl()
    bad=IndependentAtomPotential(crystal,atomic_factors={'Cs':lambda g:np.nan,'Cl':lambda g:1.})
    with pytest.raises(ValueError,match='finite scalar'):
        bad.structure_factor((1,0,0))
    with pytest.raises(ValueError,match='same crystal'):
        BeamSet.zolz(fcc_nickel(),1.,potential=synthetic_potential(crystal))


def test_noncentrosymmetric_species_weighted_phases_are_hermitian():
    crystal=Crystal(np.eye(3)*4.1,np.array([[0.,0,0],[.17,.23,.19]]),('Cs','Cl'))
    potential=synthetic_potential(crystal)
    h=(1,1,0)
    g=np.linalg.norm(crystal.g_vector(h))
    expected=(3+np.exp(-2j*np.pi*(.17+.23)))/(1+g*g)
    assert abs(expected.imag)>.1
    assert potential.structure_factor(h)==pytest.approx(expected)
    assert potential.structure_factor(tuple(-v for v in h))==pytest.approx(expected.conjugate())
