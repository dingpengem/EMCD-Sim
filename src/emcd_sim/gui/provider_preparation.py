"""Declared provider preparation; source models remain physically distinct.

The common interface also serves historical Ni through a separate compatibility
adapter. Neither class implements propagation or tensor contraction.
"""
import numpy as np
from ..ionization_sites import IonizationSites
from ..mdff_edges import selected_samples
from .generalized_forward import source_for


def declared_material_reason(structure,cfg):
    try:
        source_for(cfg)
        IonizationSites.from_structure(structure,cfg.ionizing_element,cfg.site_indices)
        a=structure.atoms
        if a.has('initial_magmoms'):
            moments=np.asarray(a.get_initial_magnetic_moments(),float)
            if np.max(abs(moments))>1e-10:
                if cfg.magnetic_state=='nonmagnetic':raise ValueError('Nonmagnetic tensor conflicts with explicit nonzero structure moments; declare a consistent magnetic structure')
                if moments.ndim==2:
                    m=np.asarray(cfg.magnetization,float)
                    if not np.allclose(moments[0]/np.linalg.norm(moments[0]),m/np.linalg.norm(m),rtol=0,atol=1e-10):
                        raise ValueError('Explicit structure moments disagree with the imported +M crystal axis')
                elif moments[0]<0:raise ValueError('Negative collinear structure moments disagree with the declared +M state; declare the axis/state consistently')
        if structure.elastic_reason:return structure.elastic_reason
    except (ValueError,OSError,TypeError,KeyError) as exc:return str(exc)
    return ''


def sampling_mode(cfg):
    return 'edges' if cfg.energy_scope=='edges' else cfg.energy_sampling


def provider_energy_grid(provider,cfg,requested=None):
    # Preserve the historical adapter and its validation. An explicitly chosen
    # native XMCD grid is supplied through its existing requested-grid API.
    if requested is None and not provider.declared and cfg.model=='xmcd' and sampling_mode(cfg)=='native':
        from ..wien2k_xmcd import load_wien2k_xmcd
        requested=np.unique(np.r_[load_wien2k_xmcd(cfg.source).energy_ev,[v for _,v in selected_samples(cfg)]])
    return provider.energy_grid(requested)


def declared_energy_grid(cfg,requested=None):
    source=source_for(cfg);lo,hi=source.energy_ev[[0,-1]]
    values=[v for _,v in selected_samples(cfg)]
    if cfg.channeling_model not in ('single','double') or cfg.energy_scope not in ('full','edges'):raise ValueError('Unsupported imported tensor propagation/energy scope')
    if not 9<=cfg.energy_points<=501 or not 9<=cfg.grid<=193 or cfg.grid%2!=1 or not 2<=cfg.depth<=1025 or not 4<=cfg.subpixels<=256:raise ValueError('Numerical sampling exceeds supported bounds')
    if not np.isfinite([cfg.halfwidth,cfg.radius,*np.ravel(cfg.centers),*cfg.window]).all() or min(cfg.halfwidth,cfg.radius)<=0:raise ValueError('Invalid detector/grid controls')
    if requested is None:
        mode=sampling_mode(cfg)
        if mode not in ('uniform','native','edges'):raise ValueError('Unknown energy sampling')
        e=(np.array(values) if mode=='edges' else
           np.unique(np.r_[source.energy_ev if mode=='native' else np.linspace(lo,hi,cfg.energy_points),values]))
    else:e=np.asarray(requested,float)
    if e.ndim!=1 or not len(e) or not np.isfinite(e).all() or np.any(np.diff(e)<=0) or e[0]<lo or e[-1]>hi:raise ValueError('No imported MDFF energy extrapolation')
    if not all(np.any(np.isclose(e,v,rtol=0,atol=1e-9)) for v in values):raise ValueError('Requested grid must include declared selected energies')
    return e.copy()


class DeclaredMDFFProvider:
    declared=True

    def __init__(self,cfg):
        self.cfg=cfg

    @property
    def source(self):
        return source_for(self.cfg)

    @property
    def simulation_magnetization(self):
        return self.cfg.magnetization

    def material_reason(self,structure):
        return declared_material_reason(structure,self.cfg)

    def energy_grid(self,requested=None):
        return declared_energy_grid(self.cfg,requested)

    def tensors(self,energy,rotation):
        return self.source.tensors(energy,rotation,self.cfg.magnetization)

    def sites(self,structure):
        return IonizationSites.from_structure(structure,self.cfg.ionizing_element,self.cfg.site_indices)

    def revalidate_source(self):
        source_for(self.cfg)
