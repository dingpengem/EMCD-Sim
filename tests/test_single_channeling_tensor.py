"""Focused physics tests for entrance-only complex tensor coupling."""
import json
import subprocess
import sys
import numpy as np
import pytest
from emcd_sim.benchmark import nickel_physical_benchmark
from emcd_sim.geometry import characteristic_qz_angstrom_inv
from emcd_sim.mdff_tensor import TransitionDataset, dipole_tensor_from_transitions, cycles_to_angular_q
from emcd_sim.ni_local_mdff import NiLocalConfig, ni_local_transitions
from emcd_sim.single_channeling_tensor import _tensor_angular_maps, fcc_site_phase_matrix, run_tensor_single_channeling


def test_site_phase_hermitian_psd():
    sim = nickel_physical_benchmark(diffraction_condition="near-2bc")
    phase = fcc_site_phase_matrix(sim)
    assert np.allclose(phase, phase.conj().T)
    assert np.linalg.eigvalsh(phase).min() >= -1e-12
    assert np.allclose(phase, 1.0)


def test_complex_contraction_equals_direct_transition_amplitude_sum():
    sim = nickel_physical_benchmark(diffraction_condition="near-2bc")
    d = np.array([.5+.1j,-.3+.2j,.2],complex)
    qx,qy = np.array([[.13]]),np.array([[.31]])
    psi = sim.elastic.amplitudes(np.array([9.]))[0]
    coherence = psi[:,None]*psi[None,:].conj()
    n,m = _tensor_angular_maps(sim,np.outer(d,d.conj()),852.7,coherence,
                               fcc_site_phase_matrix(sim),qx,qy)
    g = sim.elastic.reciprocal_vectors_xy
    qz = -characteristic_qz_angstrom_inv(852.7,sim.elastic.microscope.acceleration_kv)
    Q=cycles_to_angular_q(np.column_stack((qx.item()-g[:,0],qy.item()-g[:,1],
                                            np.full(len(g),qz))))
    direct=0.
    frac=sim.elastic.crystal.fractional_positions
    for r in frac:
        amplitude=np.sum(psi*np.exp(2j*np.pi*(np.asarray(sim.elastic.beams.hkl)@r))
                          *(Q@d)/np.sum(Q**2,axis=1))
        direct+=abs(amplitude)**2/len(frac)
    assert (n+m).item()==pytest.approx(direct,rel=1e-11,abs=1e-14)


def test_complex_dipole_conjugation_reverses_chiral_component():
    sim=nickel_physical_benchmark(diffraction_condition="near-2bc")
    transitions=ni_local_transitions()
    reverse=TransitionDataset(transitions.energy_ev,transitions.dipoles_angstrom.conj(),
        transitions.weights,transitions.edge,transitions.site,"Reversed benchmark")
    grid=np.array([852.7,870.])
    t=dipole_tensor_from_transitions(transitions,grid,.9)
    tr=dipole_tensor_from_transitions(reverse,grid,.9)
    a=run_tensor_single_channeling(sim,t,grid_size=21,depth_steps=12)
    b=run_tensor_single_channeling(sim,tr,grid_size=21,depth_steps=12)
    assert np.allclose(a.nonmag_map_at_l3,b.nonmag_map_at_l3,atol=1e-13)
    assert np.allclose(a.magnetic_map_at_l3,-b.magnetic_map_at_l3,atol=1e-13)


def test_spin_degenerate_local_model_has_no_chiral_component():
    sim=nickel_physical_benchmark(diffraction_condition="near-2bc")
    cfg=NiLocalConfig(exchange_split_ev=0.,eg_up_holes=.3,eg_down_holes=.3,
                      t2g_up_holes=.3,t2g_down_holes=.3)
    transitions=ni_local_transitions(cfg)
    t=dipole_tensor_from_transitions(transitions,np.array([852.7,870.]),.8)
    r=run_tensor_single_channeling(sim,t,grid_size=21,depth_steps=12)
    assert np.max(np.abs(r.magnetic_map_at_l3))<1e-12
    assert all(a.min()>-1e-12 for a in r.detector_spectra.values())
    assert r.moment_muB is None
