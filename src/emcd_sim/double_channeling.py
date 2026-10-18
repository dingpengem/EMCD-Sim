"""Bloch double channeling, finite ZOLZ basis and branch-independent dipole MDFF.

q = k_out + h - k_in - g, cycles/angstrom; H in radians/nm.
Independent localized sites/events are intensity sums, never amplitude sums.
"""
from dataclasses import dataclass
import numpy as np
from .geometry import Microscope, electron_wavelength_angstrom, characteristic_qz_angstrom_inv
from .physical_elastic import PhysicalElasticModel
from .gui.memory_budget import reserve_memory
from .cancellation import check_cancelled


@dataclass(frozen=True)
class BlochStates:
    values: np.ndarray
    vectors: np.ndarray
    boundary_index: int

    @classmethod
    def solve(cls, hamiltonian, boundary_index=0):
        h = np.asarray(hamiltonian, complex)
        if (h.ndim != 2 or h.shape[0] != h.shape[1] or not np.isfinite(h).all()
                or not np.allclose(h, h.conj().T, rtol=1e-12, atol=1e-13)):
            raise ValueError('Finite Hermitian Hamiltonian required')
        if not 0 <= boundary_index < len(h):
            raise ValueError('Boundary index outside basis')
        e, v = np.linalg.eigh(h)
        return cls(e, v, boundary_index)

    def ket(self, distance_nm):
        z = np.asarray(distance_nm)
        return (np.exp(1j*z[..., None]*self.values)*self.vectors[self.boundary_index].conj()) @ self.vectors.T


@dataclass(frozen=True)
class PreparedBlochIncoming:
    """Read-only incoming eigensystem/depth fields reused across loss energies.

    Bound to the exact elastic object, thickness and quadrature. Outgoing
    eigenproblems and Coulomb/MDFF energy dependence are never cached here.
    """
    elastic: object
    thickness_nm: float
    depth_steps: int
    states: BlochStates
    z: np.ndarray
    fields: np.ndarray

    @property
    def values(self):return self.states.values
    @property
    def vectors(self):return self.states.vectors
    @property
    def boundary_index(self):return self.states.boundary_index
    def ket(self,z):return self.fields if np.array_equal(z,self.z) else self.states.ket(z)


def prepare_incoming_bloch(elastic,thickness_nm,depth_steps=257,*,cancelled=None):
    check_cancelled(cancelled)
    if not np.isfinite(thickness_nm) or thickness_nm<0 or not isinstance(depth_steps,int) or depth_steps<2:
        raise ValueError('Finite nonnegative thickness and at least two depth nodes required')
    states=BlochStates.solve(elastic.hamiltonian_nm_inv(),elastic.beams.hkl.index((0,0,0)))
    check_cancelled(cancelled)
    z=np.linspace(0,float(thickness_nm),depth_steps);fields=states.ket(z)
    check_cancelled(cancelled)
    for value in (states.values,states.vectors,z,fields):value.setflags(write=False)
    return PreparedBlochIncoming(elastic,float(thickness_nm),depth_steps,states,z,fields)


def dipole_kernel(q_cycles):
    """Cartesian Q/Q², retaining signed longitudinal transfer and angular units."""
    q = 2*np.pi*np.asarray(q_cycles, float)
    if q.shape[-1] != 3 or not np.isfinite(q).all() or np.any(np.sum(q*q, axis=-1) == 0):
        raise ValueError('Finite nonzero three-component transfer required')
    return q/np.sum(q*q, axis=-1)[..., None]


def contract_cartesian(vectors, tensor):
    """v T v*, matching existing d=<core|r|final>, T=d d* convention."""
    return np.einsum('...a,ab,...b->...', vectors, tensor, vectors.conj()).real


def depth_response(incoming, outgoing, kernel, thickness_nm, *, method='analytic', depth_steps=257, cancelled=None):
    """Integral of v_a(z) v_b*(z), with v=sum_gh a_g(z) Uout(t-z)_0h K_gha.

    kernel has shape (incoming beams, outgoing beams, 3), including site phase.
    Returns Hermitian PSD 3x3 response, usable with any complex dipole tensor.
    Numerical reference uses direct depth propagation, not mode-pair integration.
    """
    check_cancelled(cancelled)
    t = float(thickness_nm)
    if not np.isfinite(t) or t < 0:
        raise ValueError('Thickness must be finite nonnegative')
    k = np.asarray(kernel, complex)
    if k.shape != (len(incoming.values), len(outgoing.values), 3) or not np.isfinite(k).all():
        raise ValueError('Kernel must match incoming/outgoing bases and Cartesian components')
    if method not in ('analytic', 'numerical'):
        raise ValueError('Depth method must be analytic or numerical')
    if t == 0:
        return np.zeros((3, 3), complex)
    if method == 'numerical':
        if not isinstance(depth_steps, int) or depth_steps < 2:
            raise ValueError('At least two depth nodes required')
        z = np.linspace(0, t, depth_steps)
        a = incoming.ket(z)
        # Reciprocal ket U(z-t)e0 conjugated gives the forward detector bra.
        check_cancelled(cancelled)
        b = outgoing.ket(z-t).conj()
        v = np.einsum('zg,zh,gha->za', a, b, k, optimize=True)
        check_cancelled(cancelled)
        outer = v[:, :, None]*v[:, None, :].conj()
        return (outer[1:]+outer[:-1]).sum(axis=0)*t/(2*(depth_steps-1))
    ci = incoming.vectors*incoming.vectors[incoming.boundary_index].conj()[None, :]
    co = outgoing.vectors.conj()*outgoing.vectors[outgoing.boundary_index][None, :]
    f = np.einsum('gj,hl,gha->jla', ci, co, k, optimize=True)
    check_cancelled(cancelled)
    f *= np.exp(1j*outgoing.values*t)[None, :, None]
    f = f.reshape(-1, 3)
    omega = (incoming.values[:, None]-outgoing.values[None, :]).ravel()
    phase = (omega[:, None]-omega[None, :])*t
    check_cancelled(cancelled)
    integral = t*np.exp(.5j*phase)*np.sinc(phase/(2*np.pi))
    check_cancelled(cancelled)
    result = f.T @ integral @ f.conj()
    check_cancelled(cancelled)
    return result


def outgoing_elastic(elastic, detector_q_xy, energy_ev, beams=None):
    """Exit reciprocal Bloch field at E0-loss, carrier k_in_perp+q_detector.

    Uses the forward H; the reciprocal state is U_out(z-t)e000. No incoming
    eigenvectors are reused. Transverse momentum is held, not absolute tilt.
    """
    kv = elastic.microscope.acceleration_kv-float(energy_ev)/1000
    if not np.isfinite(energy_ev) or energy_ev <= 0 or kv <= 0:
        raise ValueError('Energy loss must lie between zero and incident energy')
    q = np.asarray(detector_q_xy, float)
    if q.shape != (2,) or not np.isfinite(q).all():
        raise ValueError('Detector direction must be a finite reciprocal pair')
    carrier = elastic.microscope.incident_k_xy+q
    tilt = tuple(carrier*electron_wavelength_angstrom(kv)*1000)
    return PhysicalElasticModel(elastic.crystal, Microscope(kv, tilt),
                                elastic.beams if beams is None else beams, elastic.potential)


def equivalent_site_phases(incoming_hkl,outgoing_hkl,positions):
    """Group exactly identical periodic site phases, retaining site multiplicities.

    Integer reciprocal-site cycles are reduced modulo one before exponentiation.
    This removes repeated evaluations for equivalent FCC sites without dropping
    independent events or changing their incoherent per-atom normalization.
    """
    delta=np.asarray(outgoing_hkl)[None,:,:]-np.asarray(incoming_hkl)[:,None,:]
    cycles=np.remainder(np.einsum('ghc,sc->sgh',delta,np.asarray(positions)),1.)
    if not len(cycles):raise ValueError('At least one core site required')
    unique,counts=np.unique(cycles,axis=0,return_counts=True)
    return np.exp(2j*np.pi*unique),counts/len(cycles)


def double_channeling_response(elastic, energy_ev, q_xy, thickness_nm, *, outgoing_beams=None,
        method='analytic', depth_steps=257, memory_budget_mib=2048, outgoing_potential=True,prepared_incoming=None,cancelled=None):
    """Detector-resolved integrated Cartesian response (pixels,3,3).

    Average over equivalent Ni basis sites, continuous uniform depth density,
    relative per-atom scale identical to entrance-only. No absorption or HOLZ.
    Pixel loop avoids a dense (pixels*Ni*No)^2 MDFF allocation.
    """
    check_cancelled(cancelled)
    q_xy = np.asarray(q_xy, float)
    if q_xy.ndim != 2 or q_xy.shape[1] != 2 or not np.isfinite(q_xy).all():
        raise ValueError('q_xy must be finite (pixels,2)')
    ni = len(elastic.beams.hkl)
    ob = elastic.beams if outgoing_beams is None else outgoing_beams
    no = len(ob.hkl)
    # Mode-pair integral + complex temporaries, numerical propagation and output.
    dense = 80*(ni*no)**2/2**20
    working = dense+(128*(ni*no+depth_steps*(ni+no+12))+144*len(q_xy))/2**20+8
    with reserve_memory(working, memory_budget_mib, dense_mib=dense):
        if prepared_incoming is not None:
            if (not isinstance(prepared_incoming,PreparedBlochIncoming) or prepared_incoming.elastic is not elastic
                or prepared_incoming.thickness_nm!=float(thickness_nm) or prepared_incoming.depth_steps!=depth_steps):
                raise ValueError('Prepared incoming Bloch fields do not match elastic object, thickness or depth grid')
            incoming=prepared_incoming
        else:incoming = BlochStates.solve(elastic.hamiltonian_nm_inv(), elastic.beams.hkl.index((0,0,0)))
        delta = np.asarray(elastic.beams.hkl)[:, None, :]-np.asarray(ob.hkl)[None, :, :]
        if not all(s == 'Ni' for s in elastic.crystal.species):
            raise ValueError('Equivalent-site response currently supports Ni only')
        positions = elastic.crystal.fractional_positions
        if len(positions) == 0:
            raise ValueError('At least one core site required')
        phases,site_weights = equivalent_site_phases(elastic.beams.hkl,ob.hkl,positions)
        gi = elastic.reciprocal_vectors_xy
        result = np.empty((len(q_xy),3,3), complex)
        qz = -characteristic_qz_angstrom_inv(energy_ev, elastic.microscope.acceleration_kv)
        eo = outgoing_elastic(elastic, (0., 0.), energy_ev, ob)
        reference_h = eo.hamiltonian_nm_inv()
        go = eo.reciprocal_vectors_xy
        wavelength = electron_wavelength_angstrom(eo.microscope.acceleration_kv)
        for p, q in enumerate(q_xy):
            check_cancelled(cancelled)
            h = reference_h + np.diag(-20*np.pi*wavelength*(go @ q))
            if not outgoing_potential:
                h = np.diag(np.diag(h))
            outgoing = BlochStates.solve(h, ob.hkl.index((0,0,0)))
            check_cancelled(cancelled)
            transfer = np.empty((ni,no,3))
            transfer[..., :2] = q+go[None, :, :]-gi[:, None, :]
            transfer[..., 2] = qz
            kernel = dipole_kernel(transfer)
            result[p] = sum(weight*depth_response(incoming, outgoing, kernel*phase[..., None], thickness_nm,
                method=method, depth_steps=depth_steps, cancelled=cancelled) for phase,weight in zip(phases,site_weights))
        check_cancelled(cancelled)
        return result


def intensities_from_response(response, tensor):
    """Contract all q-q' interference; no clipping of negative physical results."""
    t = np.asarray(tensor, complex)
    if t.shape != (3,3) or not np.isfinite(t).all() or not np.allclose(t, t.conj().T):
        raise ValueError('Finite Hermitian dipole tensor required')
    if np.linalg.eigvalsh(t).min() < -1e-12*max(np.linalg.norm(t), 1e-30):
        raise ValueError('Dipole tensor must be positive semidefinite')
    return np.einsum('...ab,ab->...', response, t).real



def _run_tensor_double_channeling(model, tensor, *, thickness_nm=30., grid_size=65,
        map_halfwidth_q=1., reference_energy_ev=852.7, integration_mode='binary',
        aperture_subpixels=64, outgoing_beams=None, method='analytic', depth_steps=257,
        memory_budget_mib=2048):
    """Angular maps and detector spectra; existing Boolean mask meanings retained.

    Explicit opt-in solver. Existing single-channeling APIs/defaults are untouched.
    Both reversal states use the same response, obtained by T -> T.conj().
    """
    from .simulation import SimulationResult
    if not np.isfinite(thickness_nm) or thickness_nm < 0:
        raise ValueError('Thickness must be finite nonnegative')
    if grid_size < 9 or not np.isfinite(map_halfwidth_q) or map_halfwidth_q <= 0:
        raise ValueError('grid >=9 and positive finite map halfwidth required')
    if not np.isfinite(reference_energy_ev) or reference_energy_ev <= 0:
        raise ValueError('Reference energy must be finite positive')
    q=np.linspace(-map_halfwidth_q,map_halfwidth_q,grid_size)
    qx,qy=np.meshgrid(q,q,indexing='xy')
    masks={k:d.mask(qx,qy) for k,d in model.detectors.items()}
    weights={k:d.integration_weights(qx,qy,mode=integration_mode,subpixels=aperture_subpixels)
             for k,d in model.detectors.items()}
    if not all(w.any() for w in weights.values()):
        raise ValueError('At least one virtual aperture is outside reciprocal map')
    spectra={k:np.empty(len(tensor.energy_ev)) for k in weights}
    selected=int(np.argmin(abs(tensor.energy_ev-reference_energy_ev)))
    pixels=np.column_stack((qx.ravel(),qy.ravel()))
    for ie,e in enumerate(tensor.energy_ev):
        response=double_channeling_response(model.elastic,float(e),pixels,thickness_nm,
            outgoing_beams=outgoing_beams,method=method,depth_steps=depth_steps,
            memory_budget_mib=memory_budget_mib)
        t=tensor.tensor_angstrom2_per_ev[ie]
        total=intensities_from_response(response,t).reshape(qx.shape)
        if total.min() < -1e-10*max(float(abs(total).max()),1e-30):
            raise ValueError('Negative physical double-channeling intensity')
        for k in spectra:
            spectra[k][ie]=(total[masks[k]].sum() if integration_mode=='binary'
                            else (total*weights[k]).sum())*(q[1]-q[0])**2
        if ie==selected:
            even=np.einsum('pab,ab->p',response,t.real).real.reshape(qx.shape)
            odd=np.einsum('pab,ab->p',response,1j*t.imag).real.reshape(qx.shape)
    return SimulationResult(tensor.energy_ev,qx,qy,even,odd,spectra,masks,None,
        thickness_nm,0.,model.chiral_groups,weights,integration_mode,aperture_subpixels)


def run_tensor_double_channeling(model, tensor, *, thickness_nm=30., grid_size=65,
        map_halfwidth_q=1., reference_energy_ev=852.7, integration_mode='binary',
        aperture_subpixels=64, outgoing_beams=None, method='analytic', depth_steps=257,
        memory_budget_mib=2048):
    """Opt-in map/spectrum solver with admission before allocating map arrays."""
    if not isinstance(grid_size, int) or grid_size < 9:
        raise ValueError('Integer grid >=9 required')
    working = ((192+32*len(model.detectors))*grid_size**2
               +16*len(model.detectors)*len(tensor.energy_ev))/2**20
    with reserve_memory(working, memory_budget_mib):
        return _run_tensor_double_channeling(model, tensor, thickness_nm=thickness_nm,
            grid_size=grid_size, map_halfwidth_q=map_halfwidth_q,
            reference_energy_ev=reference_energy_ev, integration_mode=integration_mode,
            aperture_subpixels=aperture_subpixels, outgoing_beams=outgoing_beams,
            method=method, depth_steps=depth_steps, memory_budget_mib=memory_budget_mib)
