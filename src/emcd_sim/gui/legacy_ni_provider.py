"""Historical Ni provider adapter: exact direct evaluation, no interpolation.

Compatibility policy only: conventional Ni eligibility, original energy grid,
rotation/reversal checks and provenance. Propagation is always shared.
"""
import numpy as np
from .geometry import Structure
from ..mdff_tensor import DipoleTensor, dipole_tensor_from_transitions
from ..ni_local_mdff import ni_local_transitions
from ..wien2k_xmcd import load_wien2k_xmcd
from ..xmcd_effective_mdff import effective_tensor_from_xmcd
from ..ionization_sites import single_site_phase_matrix


def material_reason(structure):
    # Conservative Stage B gate: arbitrary CIF inspection is not MDFF validation.
    ref=Structure.nickel().atoms;a=structure.atoms
    # Keep the original Ni-only material restriction independent of the wider
    # elastic capability. Matching coordinates/cell alone do not identify Ni.
    if set(a.get_chemical_symbols())!={'Ni'}:
        return 'Stage B MDFF requires Ni; general-material elastic factors do not provide general-material EMCD.'
    if structure.elastic_reason:return structure.elastic_reason
    if (len(a)!=len(ref) or not np.allclose(a.cell.array,ref.cell.array,atol=1e-7)
        or not np.allclose(a.get_scaled_positions()%1,ref.get_scaled_positions()%1,atol=1e-7)):
        return 'Stage B MDFF requires the verified conventional FCC Ni cell (a=3.524 A, equivalent sites). CIF inspection remains available.'
    return ''


def axis_rotation(axis):
    m=np.asarray(axis,float)
    if m.shape!=(3,) or not np.isfinite(m).all() or np.linalg.norm(m)<1e-12:raise ValueError('Declare a nonzero finite crystal Cartesian magnetization axis')
    z=m/np.linalg.norm(m);x=np.array([1.,0,0]);x-=x.dot(z)*z
    if np.linalg.norm(x)<1e-8:x=np.array([0.,1,0]);x-=x.dot(z)*z
    x/=np.linalg.norm(x);return np.stack((x,np.cross(z,x),z),axis=1)


def tensors(cfg,energy,R):
    if cfg.model=='xmcd':
        if not cfg.axis_declared:raise ValueError('Declare the XMCD magnetic-axis, RP/LP handedness and L3/L2 assignments before running')
        Q=axis_rotation(cfg.magnetization)
        source=[effective_tensor_from_xmcd(cfg.source,energy,eta=s*cfg.eta,beta=cfg.beta) for s in (1,-1)]
    elif cfg.model=='atomic':
        if not np.allclose(cfg.magnetization,(0,0,1)):raise ValueError('Atomic cubic-field model currently supports crystal [001] magnetization only')
        Q=np.eye(3)
        source=[dipole_tensor_from_transitions(ni_local_transitions(cfg.atomic,radial_override_angstrom=cfg.radial,magnetization_sign=s),energy,cfg.sigma) for s in (1,-1)]
    else:raise ValueError('Unknown MDFF model')
    out=[]
    for t in source:
        A=R@Q;v=np.einsum('ia,eab,jb->eij',A,t.tensor_angstrom2_per_ev,A)
        if np.linalg.eigvalsh(v).min() < -1e-12*max(float(abs(v).max()),1e-30):raise ValueError('MDFF tensor is not positive semidefinite')
        out.append(DipoleTensor(energy,v,t.source+';crystal_to_local_R_T_RT'))
    if not np.allclose(out[1].tensor_angstrom2_per_ev,out[0].tensor_angstrom2_per_ev.conj(),rtol=1e-10,atol=1e-13*max(abs(out[0].tensor_angstrom2_per_ev).max(),1e-30)):
        raise ValueError('This model does not pass even/odd reversal symmetry; decomposition disabled')
    return out


def energy_grid(cfg,requested=None):
    if cfg.model=='xmcd':
        s=load_wien2k_xmcd(cfg.source);lo,hi=s.energy_ev[[0,-1]]
        if cfg.source_sha256 and cfg.source_sha256!=s.source_sha256:raise ValueError('XMCD source changed since validation; validate again')
    else:lo,hi=cfg.atomic.l3_ev-10,cfg.atomic.l2_ev+10
    if not lo<=cfg.l3<cfg.l2<=hi:raise ValueError('Selected L3/L2 must be ordered inside the native model energy range')
    if cfg.channeling_model not in ('single','double'):raise ValueError('Unknown channeling model; no automatic substitution')
    if cfg.energy_scope not in ('full','edges'):raise ValueError('Unknown spectral energy coverage')
    if not 9<=cfg.energy_points<=501 or not 9<=cfg.grid<=193 or not 2<=cfg.depth<=1025 or not 4<=cfg.subpixels<=256:raise ValueError('Numerical sampling exceeds supported GUI bounds')
    if not np.isfinite([cfg.halfwidth,cfg.radius,*np.ravel(cfg.centers),*cfg.window]).all() or min(cfg.halfwidth,cfg.radius)<=0:raise ValueError('Invalid map/detector/window controls')
    if requested is not None:
        e=np.asarray(requested,float)
        if e.ndim!=1 or len(e)<2 or not np.isfinite(e).all() or np.any(np.diff(e)<=0):raise ValueError('Requested energies must be finite, increasing and contain at least two samples')
        if e[0]<lo or e[-1]>hi:raise ValueError('No MDFF energy extrapolation')
        if not all(np.any(np.isclose(e,v,rtol=0,atol=1e-9)) for v in (cfg.l3,cfg.l2)):raise ValueError('Requested grid must include the selected native L3/L2 energies')
        return e.copy()
    return np.array([cfg.l3,cfg.l2]) if cfg.energy_scope=='edges' else np.unique(np.r_[np.linspace(lo,hi,cfg.energy_points),cfg.l3,cfg.l2])


class HistoricalNiSites:
    """Original unwrapped positions and per-atom mean, after the legacy gate.

    Unlike declared IonizationSites, this adapter does not wrap coordinates or
    infer new equivalence. It preserves the accepted conventional Ni domain.
    """
    def positions_for(self, crystal):
        positions=np.asarray(crystal.fractional_positions,float)
        if not len(positions) or not all(s=='Ni' for s in crystal.species):
            raise ValueError('Historical Ni sites require only Ni atoms')
        return positions

    def single_phase(self, crystal, hkl):
        return single_site_phase_matrix(hkl,self.positions_for(crystal))


class HistoricalNiProvider:
    """Common provider interface with explicit historical numerical policies."""
    declared=False
    source=None
    simulation_magnetization=(0.,0.,1.)

    def __init__(self,cfg):
        self.cfg=cfg

    def material_reason(self,structure):
        return material_reason(structure)

    def energy_grid(self,requested=None):
        return energy_grid(self.cfg,requested)

    def tensors(self,energy,rotation):
        return tensors(self.cfg,energy,rotation)

    def sites(self,structure):
        return HistoricalNiSites()

    def revalidate_source(self):
        # Preserve historical source-validation timing; no new migration policy.
        pass
