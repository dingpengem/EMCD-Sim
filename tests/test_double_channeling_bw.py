"""Checkpoint B: direct propagator and finite-basis double-channel verification."""
from dataclasses import replace
import numpy as np
import pytest
from numpy.testing import assert_allclose
from emcd_sim.double_channeling import (BlochStates, depth_response, dipole_kernel,
    double_channeling_response, intensities_from_response, outgoing_elastic)
from emcd_sim.benchmark import nickel_physical_benchmark
from emcd_sim.elastic import BeamSet


def pauli_propagator(h, z):
    """Independent closed 2x2 exponential, no eigensolver."""
    center = np.trace(h)/2
    a = h-center*np.eye(2)
    omega = np.sqrt(np.trace(a@a).real/2)
    return np.exp(1j*center*z)*(np.eye(2)*np.cos(omega*z)+1j*a*np.sin(omega*z)/omega)


def test_two_beam_direct_reference_and_depth_convergence():
    hi = np.array([[.013,.11+.04j],[.11-.04j,-.021]])
    ho = np.array([[-.017,.083-.03j],[.083+.03j,.032]])
    si, so = BlochStates.solve(hi), BlochStates.solve(ho)
    k = dipole_kernel(np.array([[[.21,.3,-.1],[.77,.3,-.1]],
                               [[-.35,.3,-.1],[.21,.3,-.1]]]))
    t = 17.
    z, w = np.polynomial.legendre.leggauss(160)
    reference = np.zeros((3,3),complex)
    for zi, wi in zip((z+1)*t/2,w*t/2):
        a = pauli_propagator(hi,zi)[:,0]
        b = pauli_propagator(ho,t-zi)[0,:]
        v = sum(a[g]*b[h]*k[g,h] for g in range(2) for h in range(2))
        reference += wi*np.outer(v,v.conj())
    exact = depth_response(si,so,k,t)
    assert_allclose(exact,reference,rtol=2e-13,atol=1e-14)
    errors=[]
    for n in (65,129,257):
        numerical=depth_response(si,so,k,t,method='numerical',depth_steps=n)
        errors.append(np.linalg.norm(numerical-exact))
    assert errors[1]<errors[0]/3.9 and errors[2]<errors[1]/3.9
    assert_allclose(depth_response(si,so,k,t,method='numerical',depth_steps=2049),exact,rtol=3e-6,atol=1e-8)
    # Boundary/reciprocity: direct propagation from site to detector.
    assert_allclose(so.ket(0),[1,0],atol=1e-15)
    assert_allclose(so.ket(-t).conj(),pauli_propagator(ho,t)[0],atol=1e-15)
    # Common phase changes cancel, including independently shifted H means.
    assert_allclose(depth_response(BlochStates.solve(hi+.31*np.eye(2)),
        BlochStates.solve(ho-.28*np.eye(2)),k,t),exact,atol=2e-14)


@pytest.fixture
def row():
    m=nickel_physical_benchmark()
    return replace(m,elastic=replace(m.elastic,beams=BeamSet(((0,0,0),(2,0,0),(-2,0,0)))))


def test_free_outgoing_reduces_to_existing_entrance_kernel(row):
    from emcd_sim.single_channeling_tensor import _tensor_angular_maps, fcc_site_phase_matrix
    e,t=831.4778,12.
    elastic=row.elastic
    ev,vec=np.linalg.eigh(elastic.hamiltonian_nm_inv())
    c=vec[0].conj()
    p=(ev[:,None]-ev[None,:])*t
    coh=vec@(c[:,None]*c[None,:].conj()*np.exp(.5j*p)*np.sinc(p/(2*np.pi)))@vec.conj().T
    q=np.array([[.2,.25],[.2,-.25]])
    tensor=np.array([[1,-.3j,0],[.3j,1,0],[0,0,1]])
    even,odd=_tensor_angular_maps(row,tensor,e,coh,fcc_site_phase_matrix(row),q[:,0],q[:,1])
    response=double_channeling_response(elastic,e,q,t,outgoing_potential=False)
    assert_allclose(intensities_from_response(response,tensor),t*(even+odd),rtol=1e-12,atol=1e-14)
    assert_allclose(intensities_from_response(response,tensor.conj()),t*(even-odd),rtol=1e-12,atol=1e-14)


def test_outgoing_energy_boundary_and_carrier(row):
    eo=outgoing_elastic(row.elastic,[.2,-.3],831.4778)
    assert eo.microscope.acceleration_kv==pytest.approx(row.elastic.microscope.acceleration_kv-.8314778)
    assert_allclose(eo.microscope.incident_k_xy,row.elastic.microscope.incident_k_xy+[.2,-.3])
    assert not np.allclose(eo.hamiltonian_nm_inv(),row.elastic.hamiltonian_nm_inv())
    from emcd_sim.geometry import electron_wavelength_angstrom
    ref=outgoing_elastic(row.elastic,[0,0],831.4778)
    shifted=ref.hamiltonian_nm_inv()+np.diag(-20*np.pi*electron_wavelength_angstrom(
        ref.microscope.acceleration_kv)*(ref.reciprocal_vectors_xy@np.array([.2,-.3])))
    assert_allclose(shifted,eo.hamiltonian_nm_inv(),rtol=1e-13,atol=1e-13)
    with pytest.raises(ValueError):outgoing_elastic(row.elastic,[0,0],3e5)


def test_parity_symmetric_detectors_zero_and_thin_limit(row):
    q=np.array([[.28,.28],[.28,-.28]])
    t=np.array([[1,-.3j,0],[.3j,1,0],[0,0,1]])
    response=double_channeling_response(row.elastic,831.4778,q,12.)
    plus=intensities_from_response(response,t)
    minus=intensities_from_response(response,t.conj())
    assert (plus>=0).all() and (minus>=0).all()
    assert_allclose(plus,minus[::-1],rtol=1e-12)
    assert_allclose((plus+minus)/2,[(plus+minus).mean()/2]*2,rtol=1e-12)
    assert_allclose((plus-minus)/2,-((plus-minus)/2)[::-1],rtol=1e-12)
    zero=double_channeling_response(row.elastic,831.4778,q,0.)
    assert_allclose(zero,0,atol=0)
    with np.errstate(invalid='ignore'):
        assert np.isnan((zero[0,0,0]-zero[1,0,0])/(zero[0,0,0]+zero[1,0,0]))
    i1=intensities_from_response(double_channeling_response(row.elastic,831.4778,q,1e-5),t)
    i2=intensities_from_response(double_channeling_response(row.elastic,831.4778,q,2e-5),t)
    assert_allclose(i2,2*i1,rtol=1e-5)


def test_invalid_inputs_and_tensor_positivity(row):
    with pytest.raises(ValueError):BlochStates.solve([[0,1j],[1j,0]])
    with pytest.raises(ValueError):intensities_from_response(np.eye(3),np.diag([1,1,-1]))
    with pytest.raises(ValueError):dipole_kernel([0,0,0])
    with pytest.raises(ValueError):double_channeling_response(row.elastic,831.,[[0,0]],-1)



def test_incoming_outgoing_basis_convergence(row):
    # Fixed physical point, potential and q; expand each basis independently.
    q=[[.2837684449,.2837684449]]
    bases=[BeamSet(tuple([(0,0,0)]+[(s*2*j,0,0) for j in range(1,n+1) for s in (1,-1)])) for n in (3,4,5)]
    t=np.array([[1,-.3j,0],[.3j,1,0],[0,0,1]])
    raw=[]
    for b in bases:
        e=replace(row.elastic,beams=b)
        raw.append(intensities_from_response(double_channeling_response(e,831.4778,q,12.,outgoing_beams=b),t)[0])
    assert abs(raw[-1]-raw[-2])/raw[-1]<.005
    # Separate incoming vs outgoing changes, no claim based on percentages.
    i=intensities_from_response(double_channeling_response(replace(row.elastic,beams=bases[-2]),831.4778,q,12.,outgoing_beams=bases[-1]),t)[0]
    o=intensities_from_response(double_channeling_response(replace(row.elastic,beams=bases[-1]),831.4778,q,12.,outgoing_beams=bases[-2]),t)[0]
    assert abs(i-raw[-1])/raw[-1]<.005
    assert abs(o-raw[-1])/raw[-1]<.005


def test_shared_fractional_detector_maps_and_reversal(row):
    from emcd_sim.double_channeling import run_tensor_double_channeling
    from emcd_sim.mdff_tensor import DipoleTensor
    t=np.array([[1,-.3j,0],[.3j,1,0],[0,0,1]])
    def run(t):
        return run_tensor_double_channeling(row,DipoleTensor(np.array([831.4778]),t[None],'synthetic'),
            thickness_nm=2.,grid_size=9,integration_mode='fractional',aperture_subpixels=16)
    a,b=run(t),run(t.conj())
    assert_allclose(a.magnetic_map_at_l3,-b.magnetic_map_at_l3)
    assert_allclose(a.nonmag_map_at_l3,b.nonmag_map_at_l3)
    for k in row.detectors:
        assert a.detector_masks[k].dtype==bool
        assert_allclose(a.detector_weights[k],b.detector_weights[k])
        dq=a.qx_angstrom_inv[0,1]-a.qx_angstrom_inv[0,0]
        total=a.nonmag_map_at_l3+a.magnetic_map_at_l3
        assert_allclose(a.detector_spectra[k][0],(total*a.detector_weights[k]).sum()*dq*dq)
        assert_allclose(a.detector_masks[k],row.detectors[k].mask(a.qx_angstrom_inv,a.qy_angstrom_inv))
