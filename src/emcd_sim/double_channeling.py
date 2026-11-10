"""Bloch double channeling, finite ZOLZ basis and branch-independent dipole MDFF.

q = k_out + h - k_in - g, cycles/angstrom; H in radians/nm.
Independent localized sites/events are intensity sums, never amplitude sums.
"""
from dataclasses import dataclass
from collections.abc import Mapping
from time import perf_counter
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
    hamiltonian: np.ndarray | None = None

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
    hamiltonian=elastic.hamiltonian_nm_inv()
    states=BlochStates.solve(hamiltonian,elastic.beams.hkl.index((0,0,0)))
    check_cancelled(cancelled)
    z=np.linspace(0,float(thickness_nm),depth_steps);fields=states.ket(z)
    check_cancelled(cancelled)
    for value in (states.values,states.vectors,z,fields,hamiltonian):value.setflags(write=False)
    return PreparedBlochIncoming(elastic,float(thickness_nm),depth_steps,states,z,fields,hamiltonian)


def dipole_kernel(q_cycles):
    """Cartesian Q/Q², retaining signed longitudinal transfer and angular units."""
    q = 2*np.pi*np.asarray(q_cycles, float)
    if q.shape[-1] != 3 or not np.isfinite(q).all() or np.any(np.sum(q*q, axis=-1) == 0):
        raise ValueError('Finite nonzero three-component transfer required')
    return q/np.sum(q*q, axis=-1)[..., None]


def contract_cartesian(vectors, tensor):
    """v T^T v*, for forward excitation with d=<core|r|final>."""
    return np.einsum('...a,ba,...b->...', vectors, tensor, vectors.conj()).real


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


def _outgoing_microscope(elastic, detector_q_xy, energy_ev):
    kv = elastic.microscope.acceleration_kv-float(energy_ev)/1000
    if not np.isfinite(energy_ev) or energy_ev <= 0 or kv <= 0:
        raise ValueError('Energy loss must lie between zero and incident energy')
    q = np.asarray(detector_q_xy, float)
    if q.shape != (2,) or not np.isfinite(q).all():
        raise ValueError('Detector direction must be a finite reciprocal pair')
    carrier = elastic.microscope.incident_k_xy+q
    tilt = tuple(carrier*electron_wavelength_angstrom(kv)*1000)
    return Microscope(kv,tilt)


def outgoing_elastic(elastic, detector_q_xy, energy_ev, beams=None):
    """Exit reciprocal field at E0-loss; transverse carrier, not tilt, is held.

    Uses the forward H; the reciprocal state is U_out(z-t)e000. Outgoing
    eigenvectors are solved independently, never borrowed from incoming states.
    """
    return PhysicalElasticModel(elastic.crystal, _outgoing_microscope(elastic,detector_q_xy,energy_ev),
                                elastic.beams if beams is None else beams, elastic.potential)


@dataclass(frozen=True)
class PreparedBlochOutgoing:
    """One loss energy's reference Hamiltonian shared across detector batches."""
    elastic: object
    energy_ev: float
    beams: object
    hamiltonian: np.ndarray
    g: np.ndarray
    wavelength: float


def prepare_outgoing_bloch(elastic, energy_ev, *, outgoing_beams=None, prepared_incoming=None, cancelled=None):
    check_cancelled(cancelled)
    ob=elastic.beams if outgoing_beams is None else outgoing_beams
    microscope=_outgoing_microscope(elastic,(0.,0.),energy_ev)
    wavelength=electron_wavelength_angstrom(microscope.acceleration_kv)
    # F_(g-h) and the declared potential cutoff do not depend on electron loss
    # or detector direction. Reuse only for the same validated elastic basis.
    if (prepared_incoming is not None and prepared_incoming.elastic is elastic
            and prepared_incoming.hamiltonian is not None and ob is elastic.beams):
        factor=lambda kv:(1.+1000*kv/510998.95)*electron_wavelength_angstrom(kv)
        # Basis/potential extinctions were already checked by this elastic
        # object. Their energy-independent tests need not be repeated per loss.
        g=elastic.reciprocal_vectors_xy
        h=prepared_incoming.hamiltonian*(factor(microscope.acceleration_kv)/factor(elastic.microscope.acceleration_kv))
        carrier=microscope.incident_k_xy
        np.fill_diagonal(h,-10*np.pi*wavelength*(np.sum((g+carrier)**2,axis=1)-np.dot(carrier,carrier)))
    else:
        eo=outgoing_elastic(elastic,(0.,0.),energy_ev,ob)
        g=eo.reciprocal_vectors_xy;h=eo.hamiltonian_nm_inv()
    check_cancelled(cancelled)
    h.setflags(write=False);g.setflags(write=False)
    return PreparedBlochOutgoing(elastic,float(energy_ev),ob,h,g,wavelength)


def _numerical_site_responses(a,b,kernel,phases,thickness_nm,cancelled,paired_fields=None):
    """Unchanged trapezoid rule, batching independent site amplitudes separately."""
    out=[]
    # Explicit GEMM avoids einsum's repeated-index contraction falling back
    # to a strided C loop. Each row still represents one depth, each column
    # one site/component; sites are squared independently below.
    ab=(a[:,:,None]*b[:,None,:]).reshape(len(a),-1) if paired_fields is None else paired_fields
    for start in range(0,len(phases),8):
        check_cancelled(cancelled)
        k=kernel[None,...]*phases[start:start+8,...,None]
        matrix=k.transpose(1,2,0,3).reshape(ab.shape[1],-1)
        v=(ab @ matrix).reshape(len(a),len(k),3).transpose(1,0,2)
        outer=v[:,:,:,None]*v[:,:,None,:].conj()
        out.extend((outer[:,1:]+outer[:,:-1]).sum(axis=1)*thickness_nm/(2*(len(a)-1)))
    return np.asarray(out)


def equivalent_site_phases(incoming_hkl,outgoing_hkl,positions):
    """Group exactly identical periodic site phases, retaining site multiplicities.

    Integer reciprocal-site cycles are reduced modulo one before exponentiation.
    This removes repeated evaluations for equivalent FCC sites without dropping
    independent events or changing their incoherent per-atom normalization.
    """
    # exp(-i Q.R), dropping only the common detector/longitudinal phase.
    delta=np.asarray(incoming_hkl)[:,None,:]-np.asarray(outgoing_hkl)[None,:,:]
    cycles=np.remainder(np.einsum('ghc,sc->sgh',delta,np.asarray(positions)),1.)
    if not len(cycles):raise ValueError('At least one core site required')
    unique,counts=np.unique(cycles,axis=0,return_counts=True)
    return np.exp(2j*np.pi*unique),counts/len(cycles)


def double_channeling_response(elastic, energy_ev, q_xy, thickness_nm, *, outgoing_beams=None,
        method='analytic', depth_steps=257, memory_budget_mib=2048, outgoing_potential=True,prepared_incoming=None,cancelled=None,ionization_sites=None,prepared_outgoing=None,timings=None):
    """Detector-resolved integrated Cartesian response (pixels,3,3).

    Average over equivalent Ni basis sites, continuous uniform depth density,
    relative per-atom scale identical to entrance-only. No absorption or HOLZ.
    Pixel loop avoids a dense (pixels*Ni*No)^2 MDFF allocation.
    """
    check_cancelled(cancelled)
    if ionization_sites is None and not all(s == 'Ni' for s in elastic.crystal.species):
        raise ValueError('Equivalent-site response currently supports Ni only')
    positions = elastic.crystal.fractional_positions if ionization_sites is None else ionization_sites.positions_for(elastic.crystal)
    return double_channeling_group_responses(elastic,energy_ev,q_xy,thickness_nm,{'sites':positions},
        outgoing_beams=outgoing_beams,method=method,depth_steps=depth_steps,memory_budget_mib=memory_budget_mib,
        outgoing_potential=outgoing_potential,prepared_incoming=prepared_incoming,cancelled=cancelled,
        prepared_outgoing=prepared_outgoing,timings=timings)['sites']


def double_channeling_group_responses(elastic, energy_ev, q_xy, thickness_nm, positions_by_group, *, outgoing_beams=None,
        method='analytic', depth_steps=257, memory_budget_mib=2048, outgoing_potential=True,prepared_incoming=None,cancelled=None,prepared_outgoing=None,timings=None):
    """Per-group mean Cartesian responses, sharing incoming/outgoing Bloch states.

    positions_by_group supplies fractional positions already validated against
    the complete elastic crystal by the calling material adapter. Each response
    averages independent events within its group; no inter-group amplitudes or
    multiplicity factors are included. Depth integration and contraction use
    the same equations and quadrature as the legacy single-group implementation.
    """
    check_cancelled(cancelled)
    q_xy = np.asarray(q_xy, float)
    if q_xy.ndim != 2 or q_xy.shape[1] != 2 or not np.isfinite(q_xy).all():
        raise ValueError('q_xy must be finite (pixels,2)')
    ni = len(elastic.beams.hkl)
    ob = elastic.beams if outgoing_beams is None else outgoing_beams
    no = len(ob.hkl)
    if not isinstance(positions_by_group,Mapping) or not positions_by_group:
        raise ValueError('At least one explicit site-position group required')
    positions_by_group={key:np.asarray(positions,float) for key,positions in positions_by_group.items()}
    if any(p.ndim!=2 or p.shape[1:]!=(3,) or not len(p) or not np.isfinite(p).all() for p in positions_by_group.values()):
        raise ValueError('Groups require finite nonempty explicit fractional positions')
    # Mode-pair integral + complex temporaries, numerical propagation and output.
    dense = 80*(ni*no)**2/2**20
    working = dense+(128*(ni*no+depth_steps*(ni+no+12))+144*len(q_xy)*len(positions_by_group)
                     +64*ni*no*sum(len(p) for p in positions_by_group.values()))/2**20+8
    with reserve_memory(working, memory_budget_mib, dense_mib=dense):
        if prepared_incoming is not None:
            if (not isinstance(prepared_incoming,PreparedBlochIncoming) or prepared_incoming.elastic is not elastic
                or prepared_incoming.thickness_nm!=float(thickness_nm) or prepared_incoming.depth_steps!=depth_steps):
                raise ValueError('Prepared incoming Bloch fields do not match elastic object, thickness or depth grid')
            incoming=prepared_incoming
        else:incoming = BlochStates.solve(elastic.hamiltonian_nm_inv(), elastic.beams.hkl.index((0,0,0)))
        before=perf_counter()
        site_phases={key:equivalent_site_phases(elastic.beams.hkl,ob.hkl,positions)
                     for key,positions in positions_by_group.items()}
        phase_seconds=perf_counter()-before
        gi = elastic.reciprocal_vectors_xy
        result = {key:np.empty((len(q_xy),3,3),complex) for key in positions_by_group}
        qz = -characteristic_qz_angstrom_inv(energy_ev, elastic.microscope.acceleration_kv)
        before=perf_counter()
        prepared_outgoing=prepared_outgoing or prepare_outgoing_bloch(elastic,energy_ev,outgoing_beams=ob,
            prepared_incoming=prepared_incoming,cancelled=cancelled)
        if (prepared_outgoing.elastic is not elastic or prepared_outgoing.energy_ev!=float(energy_ev)
                or prepared_outgoing.beams is not ob):
            raise ValueError('Prepared outgoing Bloch reference does not match elastic object, energy or basis')
        reference_h=prepared_outgoing.hamiltonian;go=prepared_outgoing.g;wavelength=prepared_outgoing.wavelength
        preparation_seconds=perf_counter()-before
        if method not in ('numerical','analytic'):raise ValueError('Depth method must be analytic or numerical')
        if not np.isfinite(thickness_nm) or thickness_nm<0:raise ValueError('Thickness must be finite nonnegative')
        if method=='numerical' and (not isinstance(depth_steps,int) or depth_steps<2):
            raise ValueError('At least two depth nodes required')
        z=np.linspace(0,float(thickness_nm),depth_steps) if method=='numerical' else None
        a=incoming.ket(z) if method=='numerical' else None
        eigen_seconds=field_seconds=site_seconds=kernel_seconds=0.
        for p, q in enumerate(q_xy):
            check_cancelled(cancelled)
            before=perf_counter()
            h = reference_h + np.diag(-20*np.pi*wavelength*(go @ q))
            if not outgoing_potential:
                h = np.diag(np.diag(h))
            outgoing = BlochStates.solve(h, ob.hkl.index((0,0,0)))
            eigen_seconds+=perf_counter()-before
            check_cancelled(cancelled)
            before=perf_counter()
            transfer = np.empty((ni,no,3))
            transfer[..., :2] = q+go[None, :, :]-gi[:, None, :]
            transfer[..., 2] = qz
            kernel = dipole_kernel(transfer)
            kernel_seconds+=perf_counter()-before
            before=perf_counter()
            b=outgoing.ket(z-thickness_nm).conj() if method=='numerical' else None
            paired_fields=(a[:,:,None]*b[:,None,:]).reshape(len(a),-1) if method=='numerical' else None
            field_seconds+=perf_counter()-before
            before=perf_counter()
            for key,(phases,site_weights) in site_phases.items():
                check_cancelled(cancelled)
                if method=='numerical':
                    responses=_numerical_site_responses(a,b,kernel,phases,thickness_nm,cancelled,paired_fields)
                    result[key][p]=np.einsum('s,sab->ab',site_weights,responses)
                else:
                    result[key][p] = sum(weight*depth_response(incoming, outgoing, kernel*phase[..., None], thickness_nm,
                        method=method, depth_steps=depth_steps, cancelled=cancelled) for phase,weight in zip(phases,site_weights))
            site_seconds+=perf_counter()-before
        check_cancelled(cancelled)
        if timings is not None:
            timings.update(site_phase_preparation_seconds=phase_seconds,outgoing_reference_seconds=preparation_seconds,
                outgoing_eigensystem_seconds=eigen_seconds,outgoing_depth_fields_seconds=field_seconds,
                site_depth_response_seconds=site_seconds,transfer_kernel_seconds=kernel_seconds)
        return result


def intensities_from_response(response, tensor):
    """Contract all q-q' interference; no clipping of negative physical results."""
    t = np.asarray(tensor, complex)
    if t.shape != (3,3) or not np.isfinite(t).all() or not np.allclose(t, t.conj().T):
        raise ValueError('Finite Hermitian dipole tensor required')
    if np.linalg.eigvalsh(t).min() < -1e-12*max(np.linalg.norm(t), 1e-30):
        raise ValueError('Dipole tensor must be positive semidefinite')
    return np.einsum('...ab,ba->...', response, t).real



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
            even=np.einsum('pab,ba->p',response,t.real).real.reshape(qx.shape)
            odd=np.einsum('pab,ba->p',response,1j*t.imag).real.reshape(qx.shape)
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
