"""Approved correction controls: production paths vs independent references.

The proposed phases/transposes are explicit test inputs or local expressions.
Current production uses the approved contractions and forward amplitudes.
"""
from types import SimpleNamespace

import numpy as np
from numpy.testing import assert_allclose

from emcd_sim.double_channeling import BlochStates, depth_response, equivalent_site_phases, intensities_from_response
from emcd_sim.multislice_double_channeling import (
    transition_modes, FFTSplitStep, forward_event_amplitudes,
)
from emcd_sim.single_channeling_tensor import _tensor_angular_maps, fcc_site_phase_matrix
from emcd_sim.geometry import characteristic_qz_angstrom_inv


def exp2(h, z):
    center = np.trace(h).real/2
    a = h-center*np.eye(2)
    omega = np.sqrt(np.trace(a@a).real/2)
    return np.exp(1j*center*z)*(np.cos(omega*z)*np.eye(2)
        + 1j*z*np.sinc(omega*z/np.pi)*a)


def case():
    hi = np.array([[.013, .11+.04j], [.11-.04j, -.021]])
    ho = np.diag([.017, -.03]).astype(complex)
    hkl = np.array([[0,0,0], [2,0,0]])
    positions = np.array([[.137,.081,.019], [.219,.043,.11]])
    g = np.array([[0.,0.], [.57,0.]])
    q = np.array([.23,.31]); energy = 831.271; voltage = 200.
    qz = -characteristic_qz_angstrom_inv(energy,voltage)
    transfer = np.concatenate((q[None,None,:]+g[None,:,:]-g[:,None,:],
                              np.full((2,2,1),qz)),axis=-1)
    angular = 2*np.pi*transfer
    kernel = angular/np.sum(angular**2,axis=-1)[...,None]
    dipoles = np.array([[1.,.3j,.2], [.4-.2j,.6,.1j]])
    weights = np.array([.7,1.3])
    tensor = sum(w*np.outer(d,d.conj()) for w,d in zip(weights,dipoles))
    model = SimpleNamespace(elastic=SimpleNamespace(
        crystal=SimpleNamespace(fractional_positions=positions,species=('Ni','Ni')),
        beams=SimpleNamespace(hkl=tuple(map(tuple,hkl))),
        reciprocal_vectors_xy=g,microscope=SimpleNamespace(acceleration_kv=voltage)))
    return hi,ho,hkl,positions,kernel,dipoles,weights,tensor,model,q,energy


def measurements():
    hi,ho,hkl,sites,k,d,w,t,model,q,e = case(); thickness = 7.
    x,weights = np.polynomial.legendre.leggauss(128)
    coherence = np.zeros((2,2),complex); direct=0.
    for z,wz in zip((x+1)*thickness/2,weights*thickness/2):
        a = exp2(hi,z)[:,0]
        coherence += wz*np.outer(a,a.conj())/thickness
        for site in sites:
            phase = np.exp(2j*np.pi*(hkl@site))
            for dn,wn in zip(d,w):
                amplitude = sum(a[g]*phase[g]*np.dot(k[g,0],dn.conj()) for g in range(2))
                direct += wz*wn*abs(amplitude)**2/len(sites)
    phase_single = fcc_site_phase_matrix(model)
    # Actual corrected Single kernel, using the original tensor unchanged.
    ev,od = _tensor_angular_maps(model,t,e,coherence,phase_single,
                                np.array([q[0]]),np.array([q[1]]))
    proposed_single = thickness*(ev[0]+od[0])
    current_r = np.zeros((3,3),complex); proposed_r=current_r.copy()
    phases,site_weights=equivalent_site_phases(hkl,hkl,sites)
    for phase,weight in zip(phases,site_weights):
        current_r += weight*depth_response(BlochStates.solve(hi),BlochStates.solve(ho),
                                           k*phase.conj()[...,None],thickness)
    # Independent construction from physical positions; not current helper.conj.
    delta = hkl[:,None,:]-hkl[None,:,:]
    for site in sites:
        proposed_phase=np.exp(2j*np.pi*(delta@site))
        proposed_r += depth_response(BlochStates.solve(hi),BlochStates.solve(ho),
                                     k*proposed_phase[...,None],thickness)/len(sites)
    return dict(direct=direct,proposed_single=proposed_single,
        proposed_double=intensities_from_response(proposed_r,t),
        contraction_only=np.sum(current_r*t.T).real,
        phase_only=np.sum(proposed_r*t).real,
        current_double=np.sum(current_r*t).real)


def test_proposed_nontrivial_site_free_exit_limit_matches_born():
    """Physics proposal: true complex-site SC/DC reduction with independent H."""
    values=measurements()
    assert_allclose(values['proposed_single'],values['direct'],rtol=2e-13,atol=1e-14)
    assert_allclose(values['proposed_double'],values['direct'],rtol=2e-13,atol=1e-14)


def test_both_corrections_are_required_for_complex_sites_and_dipoles():
    """Physics/algebra: isolate phase-only from contraction-only correction."""
    values=measurements()
    for key in ('current_double','contraction_only','phase_only'):
        assert abs(values[key]-values['direct']) > 1e-4


def test_transition_factor_is_unchanged_but_forward_modes_are_conjugated():
    """Algebra: L* L^T=T^T; do not conjugate K, fast fields or factor twice."""
    *_, t, model, q, energy = case()
    d = case()[5]; w=case()[6]
    l = transition_modes(t)
    v = np.array([.21+.13j, -.32+.17j, .11-.07j])
    direct = sum(wn*abs(np.dot(v,dn.conj()))**2 for wn,dn in zip(w,d))
    assert_allclose(l@l.conj().T,t,atol=1e-14)
    assert_allclose(l.conj()@l.T,t.T,atol=1e-14)
    assert_allclose(np.sum(abs(v@l.conj())**2),direct,rtol=2e-14)
    assert_allclose(np.sum(np.outer(v,v.conj())*t.T).real,direct,rtol=2e-14)
    assert abs(np.sum(abs(v@l)**2)-direct) > 1e-4


def test_site_origin_covariance_under_rephased_elastic_coefficients():
    """Physics proposal: pure origin shift, not movement within fixed potential."""
    hi,ho,hkl,sites,k,d,w,t,*_=case()
    ho=np.array([[-.017,.083-.03j],[.083+.03j,.032]])
    shift=np.array([.173,-.031,.07]); thickness=4.; z=1.2
    # Coordinates r'=r-shift; potential and waves transform with the basis.
    diagonal=np.diag(np.exp(2j*np.pi*(hkl@shift)))
    shifted_hi=diagonal@hi@diagonal.conj().T
    shifted_ho=diagonal@ho@diagonal.conj().T
    a=exp2(hi,z)[:,0]; bra=exp2(ho,thickness-z)[0]
    shifted_a=exp2(shifted_hi,z)[:,0]
    shifted_bra=exp2(shifted_ho,thickness-z)[0]
    for site in sites:
        delta=hkl[:,None,:]-hkl[None,:,:]
        phase=np.exp(2j*np.pi*(delta@site))
        shifted_phase=np.exp(2j*np.pi*(delta@(site-shift)))
        v=np.einsum('g,h,gha,gh->a',a,bra,k,phase)
        shifted_v=np.einsum('g,h,gha,gh->a',shifted_a,shifted_bra,k,shifted_phase)
        assert_allclose(shifted_v,v,atol=2e-15)


def test_proposed_forward_mode_use_with_complex_kernel_and_exit():
    """Prospective solver check: direct dipoles and explicit DFT exit matrix.

    The actual helper receives T; T* below represents the historical wrong
    excitation convention and must disagree with the independent reference.
    """
    d=case()[5]; weights=case()[6]; t=case()[7]
    incoming=np.array([.8+.2j,-.1+.3j]);rng=np.random.default_rng(593)
    kernel=rng.normal(size=(2,3,3))+.2j*rng.normal(size=(2,3,3))
    u=np.array([.2,-.1,.4,.05]);kinetic=np.array([.04,-.03,.09,.1])
    n=4;indices=np.array([0,1,3]);dz=.03;count=20
    points=np.arange(n);f=np.exp(-2j*np.pi*points[:,None]*points[None,:]/n)/np.sqrt(n)
    half=np.diag(np.exp(.5j*dz*kinetic))
    step=half@f@np.diag(np.exp(1j*dz*u))@f.conj().T@half
    exit_matrix=np.linalg.matrix_power(step,count)
    direct=0.
    for dn,wn in zip(d,weights):
        scattered=np.zeros(n,complex)
        for j,h in enumerate(indices):
            scattered[h]=sum(incoming[g]*np.dot(kernel[g,j],dn.conj()) for g in range(2))
        direct += wn*abs((exit_matrix@scattered)[0])**2
    plan=FFTSplitStep(u,kinetic);slices=[(plan,dz)]*count
    current=forward_event_amplitudes(incoming,kernel,t.conj(),plan,slices,indices)
    candidate=forward_event_amplitudes(incoming,kernel,t,plan,slices,indices)
    assert_allclose(np.sum(abs(candidate)**2),direct,rtol=2e-13,atol=1e-14)
    assert abs(np.sum(abs(current)**2)-direct)>1e-4
