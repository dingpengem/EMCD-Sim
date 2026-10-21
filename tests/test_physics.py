import numpy as np
import pytest
from emcd_sim.crystal import fcc_nickel
from emcd_sim.benchmark import nickel_physical_benchmark
from emcd_sim.elastic import BeamSet
from emcd_sim.geometry import electron_wavelength_angstrom, characteristic_qz_angstrom_inv
from emcd_sim.elastic import depth_coherence


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
    model = nickel_physical_benchmark(beams_override=BeamSet()).elastic
    assert np.allclose(model.hamiltonian_nm_inv(), model.hamiltonian_nm_inv().conj().T)
    psi = model.amplitudes(np.linspace(0, 60, 17))
    np.testing.assert_allclose(np.sum(abs(psi)**2,axis=1), 1.,atol=1e-12)
    np.testing.assert_allclose(psi[0], [1,0,0],atol=1e-12)
    coherence=depth_coherence(model,30,steps=36)
    np.testing.assert_allclose(coherence,coherence.conj().T,atol=1e-13)
    assert np.trace(coherence).real==pytest.approx(1.,abs=1e-12)
    assert np.min(np.linalg.eigvalsh(coherence))>-1e-11
