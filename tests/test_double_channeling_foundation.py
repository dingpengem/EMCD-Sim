"""Checkpoint A: independent algebra/units tests; no Ni benchmark dependency."""
import numpy as np
from numpy.testing import assert_allclose
from emcd_sim.double_channeling import dipole_kernel, contract_cartesian
from emcd_sim.mdff_tensor import DipoleTensor


def test_mdff_hermitian_reversal_and_antisymmetric_sign():
    d = np.array([1, 1j, 0])
    t = np.outer(d, d.conj())
    q = np.array([[.2,.3,-.1],[-.4,.2,-.1]])
    s = q@t@q.T
    assert_allclose(s, s.conj().T)
    assert_allclose(q@t.conj()@q.T, s.conj())
    # Txy=-i => Im(S(q,q'))=-(qx*q'y-qy*q'x).
    assert_allclose(s[0,1].imag, -(q[0,0]*q[1,1]-q[0,1]*q[1,0]))
    dt = DipoleTensor(np.array([800.]), t[None], 'synthetic exact transition')
    assert_allclose(dt.mdff(q[:,None],q[None,:])[0], s)


def test_direct_transition_sum_vs_complex_mdff_contraction():
    rng = np.random.default_rng(581)
    d = rng.normal(size=(4,3))+1j*rng.normal(size=(4,3))
    t = d.T@d.conj()
    q = rng.normal(size=(5,3))
    a = rng.normal(size=5)+1j*rng.normal(size=5)
    kernel = dipole_kernel(q)
    reference = sum(abs(sum(a[g]*np.dot(kernel[g],dn) for g in range(5)))**2 for dn in d)
    mdff = kernel@t@kernel.T
    assert_allclose(np.einsum('g,h,gh',a,a.conj(),mdff),reference,atol=1e-12)
    assert_allclose(contract_cartesian(a@kernel,t),reference,atol=1e-12)
    assert reference >= 0
    assert not np.isclose(reference,np.einsum('g,g,gg',a,a.conj(),mdff).real)


def test_momentum_units_and_phase_conjugation():
    q = np.array([.5,-.3,-.1])
    assert_allclose(dipole_kernel(q), q/(2*np.pi*np.dot(q,q)))
    assert_allclose(dipole_kernel(2*q),dipole_kernel(q)/2)
    v = np.array([1,1j,0])
    t = np.outer(v,v.conj())
    assert_allclose(contract_cartesian(v,t),0,atol=1e-14)
    assert_allclose(contract_cartesian(v.conj(),t),4)
    even = contract_cartesian(v,t.real)
    odd = contract_cartesian(v,1j*t.imag)
    assert_allclose(contract_cartesian(v,t),even+odd)
    assert_allclose(contract_cartesian(v,t.conj()),even-odd)
    assert_allclose(contract_cartesian(v*np.exp(.74j),t.conj()),even-odd)



def test_atomic_transition_provider_uses_same_complex_contraction():
    from emcd_sim.ni_atomic_reference import NiAtomicReferenceConfig, ni_atomic_transitions
    from emcd_sim.mdff_tensor import dipole_tensor_from_transitions, gaussian_broadening_ev
    cfg=NiAtomicReferenceConfig(spin_up_hole_weight=.1,spin_down_hole_weight=.6)
    ds=ni_atomic_transitions(cfg)
    energy=np.array([852.7,870.])
    tensor=dipole_tensor_from_transitions(ds,energy,.6)
    v=np.array([.2+.1j,.3-.4j,-.1+.02j])
    line=gaussian_broadening_ev(energy,ds.energy_ev,.6)
    direct=line@(ds.weights*np.abs(ds.dipoles_angstrom@v)**2)
    assert_allclose([contract_cartesian(v,t) for t in tensor.tensor_angstrom2_per_ev],direct,rtol=1e-13)
    assert (direct>0).all()
