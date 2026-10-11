import numpy as np
import pytest
from emcd_sim.crystal import fcc_nickel
from emcd_sim.benchmark import nickel_three_beam
from emcd_sim.geometry import electron_wavelength_angstrom, characteristic_qz_angstrom_inv
from emcd_sim.elastic import depth_coherence
from emcd_sim.voltage import ConstantMagnetization, TabulatedMagnetization


def test_fcc_extinction_and_reciprocal_vectors():
    ni = fcc_nickel()
    assert ni.is_allowed((2, 0, 0))
    assert ni.is_allowed((1, 1, 1))
    assert not ni.is_allowed((1, 0, 0))
    assert not ni.is_allowed((1, 1, 0))
    np.testing.assert_allclose(ni.g_vector((2, 0, 0)), [2 / 3.524, 0, 0])


def test_relativistic_wavelength_and_characteristic_qz():
    assert electron_wavelength_angstrom(200.) == pytest.approx(.02508, rel=0.001)
    assert characteristic_qz_angstrom_inv(852.7, 200.) > 0
    with pytest.raises(ValueError):
        electron_wavelength_angstrom(0)


def test_unitary_elastic_propagation_and_coherence():
    model = nickel_three_beam().elastic
    assert np.allclose(model.hamiltonian_nm_inv(), model.hamiltonian_nm_inv().conj().T)
    psi = model.amplitudes(np.linspace(0, 60, 17))
    np.testing.assert_allclose(np.sum(abs(psi)**2,axis=1), 1.,atol=1e-12)
    np.testing.assert_allclose(psi[0], [1,0,0],atol=1e-12)
    coherence=depth_coherence(model,30,steps=36)
    np.testing.assert_allclose(coherence,coherence.conj().T,atol=1e-13)
    assert np.trace(coherence).real==pytest.approx(1.,abs=1e-12)
    assert np.min(np.linalg.eigvalsh(coherence))>-1e-11


def simulate(moment):
    s=nickel_three_beam(ConstantMagnetization(moment))
    return s.run(np.array([845.,852.7,860.,870.,880.]),grid_size=45,depth_steps=24)


def test_magnetic_reversal_and_nonmagnetic_symmetry():
    plus, minus, zero = simulate(.6),simulate(-.6),simulate(0)
    for key in ("A","B"):
        np.testing.assert_allclose(plus.detector_spectra[key]+minus.detector_spectra[key],
                                    2*zero.detector_spectra[key], rtol=1e-12,atol=1e-12)
        assert np.all(plus.detector_spectra[key]>=0)
        assert np.all(minus.detector_spectra[key]>=0)
    assert np.max(abs(zero.difference()))<1e-11
    np.testing.assert_allclose(plus.difference(),-minus.difference(),atol=1e-11)
    assert abs(plus.at_edge()[2])>1e-4
    assert plus.at_edge()[2]*minus.at_edge()[2]<0


def test_l3_l2_sign_and_bias_scaling():
    p = simulate(.60)
    half = simulate(.30)
    assert np.sign(p.difference()[1]) != np.sign(p.difference()[3])
    np.testing.assert_allclose(half.difference(),0.5*p.difference(),rtol=1e-10,atol=1e-11)
    table=TabulatedMagnetization((0.,1.,2.),(.60,.45,.30))
    assert table(1.5)==pytest.approx(.375)
    with pytest.raises(ValueError):
        table(3)


def test_invalid_geometry_rejected():
    from emcd_sim.elastic import BeamSet, ElasticModel
    sim = nickel_three_beam()
    with pytest.raises(ValueError):
        ElasticModel(sim.elastic.crystal,sim.elastic.microscope,BeamSet(((0,0,0),(1,0,0))))
    with pytest.raises(ValueError):
        sim.run(np.array([853.,850.]))
    with pytest.raises(ValueError):
        sim.run(np.array([850.,853.]),thickness_nm=-1)
    with pytest.raises(ValueError):
        sim.run(np.array([850.,853.]),grid_size=3)


def test_tabulated_energy_model_and_magnetic_direction():
    from emcd_sim.inelastic import TabulatedEdgeSpectrum, DipoleMDFF
    tab=TabulatedEdgeSpectrum((850, 855, 860), (1.,2.,1.), (.1,.2,-.1))
    N, M = DipoleMDFF(tab, reference_energy_ev=855).terms(np.array([852.5]),.60)
    assert N[0] == pytest.approx(1.5)
    assert M[0] == pytest.approx(.15)
    with pytest.raises(ValueError):
        tab.values(np.array([840.]))
    with pytest.raises(ValueError):
        TabulatedEdgeSpectrum((850,855),(1.,1.),(1.1,0.))

    from emcd_sim.simulation import EMCDSimulation
    base=nickel_three_beam()
    transverse=EMCDSimulation(base.elastic,base.mdff,base.magnetization,base.detectors,
                               magnetization_direction_xyz=(0.,1.,0.))
    res=transverse.run(np.array([852.,853.]),grid_size=25,depth_steps=10)
    assert np.all(np.isfinite(res.asymmetry()))
