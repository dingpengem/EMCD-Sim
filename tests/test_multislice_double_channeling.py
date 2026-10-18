"""FFT double-channel focused algebra, forward/adjoint and physics checks."""
from dataclasses import replace
import numpy as np
from numpy.testing import assert_allclose
import pytest
from emcd_sim.multislice_double_channeling import (transition_modes,FFTSplitStep,
    propagate_slices,forward_event_amplitudes,depth_quadrature,ProjectedNiFFT,
    incident_fields,multislice_double_channeling_response)
from emcd_sim.double_channeling import dipole_kernel,intensities_from_response
from emcd_sim.benchmark import nickel_physical_benchmark
from emcd_sim.elastic import BeamSet


def test_factorized_complex_mdff_against_dense_reference():
    d=np.array([[1,.3j,.2],[.4-.2j,.6,.1j]])
    t=d.T@d.conj()
    l=transition_modes(t)
    assert_allclose(l@l.conj().T,t,atol=1e-14)
    q=np.array([[.2,.3,-.1],[-.4,.3,-.1],[.6,.2,-.1]])
    k=dipole_kernel(q);a=np.array([1,.3j,-.2+.1j])
    dense=k@t@k.T
    reference=sum(a[g]*a[h].conjugate()*dense[g,h] for g in range(3) for h in range(3))
    modes=a@k@l
    assert_allclose(np.vdot(modes,modes),reference,atol=1e-14)
    assert not np.isclose(reference.real,np.sum(abs(a)**2*np.diag(dense).real))
    with pytest.raises(ValueError,match='Non-PSD'):transition_modes(np.diag([1,1,-.01]))
    assert_allclose(transition_modes(np.zeros((3,3))),0)


def dense_split(u,d,dz):
    """Explicit DFT matrix, independent of FFT stepping implementation."""
    n=len(u);x=np.arange(n)
    f=np.exp(-2j*np.pi*x[:,None]*x[None,:]/n)/np.sqrt(n)
    k=np.diag(np.exp(.5j*dz*d))
    return k@f@np.diag(np.exp(1j*dz*u))@f.conj().T@k


def test_forward_adjoint_complex_amplitudes_and_reversed_order():
    rng=np.random.default_rng(481)
    n=6
    u1,u2=rng.normal(size=(2,n))*.3
    d1,d2=rng.normal(size=(2,n))*.1
    p1,p2=FFTSplitStep(u1,d1),FFTSplitStep(u2,d2)
    slices=[(p1,.13),(p2,.21),(p1,.07)]
    direct=np.eye(n,dtype=complex)
    for p,z in slices:direct=dense_split(p.u,p.d,z)@direct
    incoming=rng.normal(size=3)+1j*rng.normal(size=3)
    kernel=rng.normal(size=(3,4,3))+1j*rng.normal(size=(3,4,3))
    d=np.array([[1,-.3j,0],[.3j,1,0],[0,0,.7]])
    oi=np.array([0,1,3,5])
    modes=transition_modes(d)
    scattered=np.einsum('g,gha,af->fh',incoming,kernel,modes)
    wave=np.zeros((3,n),complex);wave[:,oi]=scattered
    expected=(direct@wave.T)[0]
    forward=forward_event_amplitudes(incoming,kernel,d,p1,slices,oi)
    exit_state=np.zeros(n,complex);exit_state[0]=1
    adjoint=propagate_slices(exit_state,slices,adjoint=True)
    reciprocal=np.einsum('h,g,gha,af->f',adjoint[oi].conj(),incoming,kernel,modes)
    assert_allclose(forward,expected,rtol=1e-13,atol=1e-13)
    assert_allclose(reciprocal,forward,rtol=1e-13,atol=1e-13)
    assert_allclose(adjoint,direct.conj().T@exit_state,atol=1e-14)
    wrong=propagate_slices(exit_state,[(p,-z) for p,z in slices])
    assert np.linalg.norm(wrong-adjoint)>1e-5


def test_vacuum_fft_parseval_and_free_exit_phase():
    n=12;d=np.linspace(-.5,.3,n)
    p=FFTSplitStep(np.zeros(n),d)
    rng=np.random.default_rng(42)
    c=rng.normal(size=n)+1j*rng.normal(size=n)
    out=p.advance(c,7,.03)
    assert_allclose(out,c*np.exp(1j*d*.21),atol=1e-14)
    assert_allclose(np.sum(abs(out)**2),np.mean(abs(np.fft.ifft(out)*n)**2),rtol=1e-14)
    assert_allclose(p.advance(out,7,-.03),c,atol=1e-14)
    # Off-axis boundary has a nontrivial free-space phase, with no rescaling.
    e=np.zeros(n,complex);e[3]=1
    assert_allclose(p.advance(e,7,.03)[3],np.exp(1j*d[3]*.21),atol=1e-14)


@pytest.fixture
def row():
    model=nickel_physical_benchmark()
    return replace(model,elastic=replace(model.elastic,beams=BeamSet(((0,0,0),(2,0,0),(-2,0,0)))))


def test_projected_potential_and_legacy_entrance_fields(row):
    from emcd_sim.multislice_reference import _projected_ni_potential,fft_multislice_ni
    g=ProjectedNiFFT.build(row.elastic,grid_points=16,potential_cutoff=.75,systematic_row=True,row_reduction=True)
    b=row.elastic.potential.debye_waller_b_angstrom2[0]
    u,h,gv=_projected_ni_potential(16,row.elastic.microscope.acceleration_kv,b,.75,systematic_row_hkl=(2,0,0))
    assert_allclose(g.potential,u[:,0],atol=1e-14)
    fields,z,w,n,dz=incident_fields(g,2.,depth_steps=17,slice_step_nm=.04)
    legacy=fft_multislice_ni(z,acceleration_kv=row.elastic.microscope.acceleration_kv,
        tilt_mrad_xy=row.elastic.microscope.tilt_mrad_xy,grid_points=16,slice_step_nm=.04,
        potential_cutoff_inv_angstrom=.75,return_amplitudes=True,systematic_row_hkl=(2,0,0))
    indices=np.flatnonzero(legacy.beam_hkl[:,1]==0)
    assert_allclose(fields,legacy.amplitudes[:,indices],atol=2e-14)
    assert_allclose(np.sum(abs(legacy.amplitudes[:,legacy.beam_hkl[:,1]!=0])**2),0,atol=1e-26)


def test_disabled_outgoing_recovers_entrance_and_reversal(row):
    from emcd_sim.multislice_emcd_reference import coherence_from_amplitudes
    from emcd_sim.single_channeling_tensor import _tensor_angular_maps,fcc_site_phase_matrix
    g=ProjectedNiFFT.build(row.elastic,grid_points=16,potential_cutoff=.75,systematic_row=True,row_reduction=True)
    fields,z,w,n,dz=incident_fields(g,3.,depth_steps=33)
    coh=coherence_from_amplitudes(z,fields[:,g.indices(row.elastic.beams.hkl)])
    q=np.array([[.28,.28],[.28,-.28]])
    t=np.array([[1,-.3j,0],[.3j,1,0],[0,0,1]])
    response,diag=multislice_double_channeling_response(row.elastic,831.4778,q,3.,fft_grid=16,
        potential_cutoff=.75,systematic_row=True,row_reduction=True,depth_steps=33,outgoing_potential=False)
    even,odd=_tensor_angular_maps(row,t,831.4778,coh,fcc_site_phase_matrix(row),q[:,0],q[:,1])
    assert_allclose(intensities_from_response(response,t),3*(even+odd),rtol=1e-12,atol=1e-14)
    assert_allclose(intensities_from_response(response,t.conj()),3*(even-odd),rtol=1e-12,atol=1e-14)
    assert diag['outgoing_norm_error']<1e-13


def test_magnetic_parity_mirror_nonmagnetic_positivity(row):
    q=np.array([[.28,.28],[.28,-.28]])
    response,diag=multislice_double_channeling_response(row.elastic,831.4778,q,4.,fft_grid=16,
        potential_cutoff=.75,systematic_row=True,row_reduction=True,depth_steps=65)
    t=np.array([[1,-.3j,0],[.3j,1,0],[0,0,1]])
    p,m=[intensities_from_response(response,x) for x in (t,t.conj())]
    assert np.all(p>=0) and np.all(m>=0)
    assert_allclose(p,m[::-1],atol=1e-13)
    assert_allclose((p+m)/2,intensities_from_response(response,t.real),atol=1e-13)
    assert_allclose((p-m)/2,-((p-m)/2)[::-1],atol=1e-13)
    assert_allclose(transition_modes(t.real)@transition_modes(t.real).conj().T,t.real)
    assert np.min(np.linalg.eigvalsh(response))>-1e-12


def test_depth_endpoints_and_zero_thin_limit(row):
    z,w=depth_quadrature(3.,17)
    assert_allclose(w.sum(),3.)
    assert_allclose(w[0],w[-1]);assert_allclose(2*w[0],w[1])
    q=[[.28,.28]]
    def run(t):return multislice_double_channeling_response(row.elastic,831.4778,q,t,fft_grid=16,
        potential_cutoff=.75,systematic_row=True,row_reduction=True,depth_steps=17)[0]
    assert_allclose(run(0),0,atol=0)
    from emcd_sim.gui.prb_benchmark import relative_dichroism_percent
    percent,_=relative_dichroism_percent(np.array([0.]),np.array([0.]))
    assert np.isnan(percent[0])
    a,b=run(1e-5),run(2e-5)
    assert_allclose(b,2*a,rtol=1e-5,atol=1e-12)
    assert_allclose(np.diagonal(a[0]).real/1e-5,
        dipole_kernel([.28,.28,-831.4778/(12398.419843320026*.6953144712627447)])**2,rtol=1e-5)


def test_full_2d_vs_exact_row_reduction_and_slice_convergence(row):
    q=np.array([[.28,.28],[.28,-.28]])
    def run(reduced,step):return multislice_double_channeling_response(row.elastic,831.4778,q,4.,fft_grid=16,
        potential_cutoff=.75,systematic_row=True,row_reduction=reduced,depth_steps=17,slice_step_nm=step)[0]
    assert_allclose(run(True,.04),run(False,.04),rtol=1e-12,atol=1e-14)
    ref=run(True,.005)
    e1=np.linalg.norm(run(True,.08)-ref)
    e2=np.linalg.norm(run(True,.04)-ref)
    assert e2<e1/2


def test_basis_fft_grid_and_potential_cutoff_sensitivity(row):
    q=[[.28,.28]]
    def run(n,cut,beams):
        e=replace(row.elastic,beams=beams)
        return multislice_double_channeling_response(e,831.4778,q,4.,fft_grid=n,
            potential_cutoff=cut,systematic_row=True,row_reduction=True,depth_steps=65)[0]
    basis=BeamSet(((0,0,0),(2,0,0),(-2,0,0),(4,0,0),(-4,0,0),(6,0,0),(-6,0,0)))
    a=run(16,.75,basis);b=run(24,.75,basis)
    assert_allclose(a,b,rtol=1e-9,atol=1e-10)
    small=run(16,.75,row.elastic.beams)
    assert np.linalg.norm(small-a)/np.linalg.norm(a)<.02
    changed=run(24,1.5,basis)
    assert np.linalg.norm(changed-a)>1e-8


def test_outgoing_energy_kinematics_and_full_2d_fft():
    from emcd_sim.geometry import electron_wavelength_angstrom
    model=nickel_physical_benchmark()
    grid=ProjectedNiFFT.build(model.elastic,grid_points=16,potential_cutoff=.75)
    out=grid.plan(831.4778,[.2,-.3])
    lam=electron_wavelength_angstrom(model.elastic.microscope.acceleration_kv-.8314778)
    expected=-10*np.pi*lam*(np.sum(grid.g**2,axis=1)+2*grid.g@(grid.carrier+[.2,-.3]))
    assert_allclose(out.d.ravel(),expected,atol=1e-12)
    assert not np.allclose(out.u,grid.potential)
    # Two-dimensional DFT matrix reference on a small nonseparable potential.
    rng=np.random.default_rng(74);u=rng.normal(size=(4,4))*.1;d=rng.normal(size=(4,4))*.1
    n=np.arange(4);f=np.exp(-2j*np.pi*n[:,None]*n[None,:]/4)/2
    f=np.kron(f,f);k=np.diag(np.exp(.5j*.13*d.ravel()))
    operator=k@f@np.diag(np.exp(1j*.13*u.ravel()))@f.conj().T@k
    c=rng.normal(size=16)+1j*rng.normal(size=16)
    assert_allclose(FFTSplitStep(u,d).advance(c,1,.13),operator@c,atol=1e-14)


def test_map_interface_fractional_weights_and_nonmagnetic_reversal(row):
    from emcd_sim.multislice_double_channeling import run_tensor_multislice_double_channeling
    from emcd_sim.mdff_tensor import DipoleTensor
    tensor=DipoleTensor(np.array([831.4778]),np.eye(3)[None],'synthetic nonmagnetic')
    result=run_tensor_multislice_double_channeling(row,tensor,thickness_nm=1.,grid_size=9,
        integration_mode='fractional',fft_grid=16,potential_cutoff=.75,systematic_row=True,
        row_reduction=True,depth_steps=9)
    assert_allclose(result.magnetic_map_at_l3,0,atol=0)
    for k,d in row.detectors.items():
        assert result.detector_masks[k].dtype==bool
        assert_allclose(result.detector_masks[k],d.mask(result.qx_angstrom_inv,result.qy_angstrom_inv))
        dq=result.qx_angstrom_inv[0,1]-result.qx_angstrom_inv[0,0]
        assert_allclose(result.detector_spectra[k][0],np.sum(result.nonmag_map_at_l3*result.detector_weights[k])*dq*dq)


def test_complete_direct_forward_depth_sum_matches_adjoint(row):
    from emcd_sim.geometry import characteristic_qz_angstrom_inv
    grid=ProjectedNiFFT.build(row.elastic,grid_points=16,potential_cutoff=.75,systematic_row=True,row_reduction=True)
    fields,z,w,n,dz=incident_fields(grid,2.,depth_steps=9,slice_step_nm=.04)
    ii=grid.indices(row.elastic.beams.hkl)
    q=np.array([.28,.28]);energy=831.4778
    transfer=np.empty((3,3,3));transfer[...,:2]=q+grid.g[ii][None,:,:]-grid.g[ii][:,None,:]
    transfer[...,2]=-characteristic_qz_angstrom_inv(energy,row.elastic.microscope.acceleration_kv)
    kernel=dipole_kernel(transfer)
    tensor=np.array([[1,-.3j,0],[.3j,1,0],[0,0,1]])
    out=grid.plan(energy,q)
    direct=0.
    for i in range(len(z)):
        amplitudes=forward_event_amplitudes(fields[i,ii],kernel,tensor,out,
            [(out,dz)]*(n*(len(z)-1-i)),ii)
        direct+=w[i]*np.sum(abs(amplitudes)**2)
    response,_=multislice_double_channeling_response(row.elastic,energy,q[None],2.,fft_grid=16,
        potential_cutoff=.75,systematic_row=True,row_reduction=True,depth_steps=9)
    assert_allclose(intensities_from_response(response,tensor)[0],direct,rtol=1e-12,atol=1e-14)


def test_memory_budgets_and_available_ram_rejection(row,monkeypatch):
    from emcd_sim.gui import memory_budget
    monkeypatch.setattr(memory_budget,'memory_snapshot',lambda:dict(available_ram_mib=32768.,process_rss_mib=100.))
    for budget in (512,1024,2048,4096,8192):
        response,diag=multislice_double_channeling_response(row.elastic,831.4778,[[.28,.28]],0.,
            fft_grid=16,potential_cutoff=.75,systematic_row=True,row_reduction=True,
            depth_steps=2,memory_budget_mib=budget)
        assert_allclose(response,0,atol=0)
        assert diag['memory_admission']['memory_budget_mib']==budget
    monkeypatch.setattr(memory_budget,'memory_snapshot',lambda:dict(available_ram_mib=64.,process_rss_mib=100.))
    with pytest.raises(ValueError,match='currently available RAM'):
        multislice_double_channeling_response(row.elastic,831.4778,[[.28,.28]],1.,
            fft_grid=16,potential_cutoff=.75,systematic_row=True,row_reduction=True)
