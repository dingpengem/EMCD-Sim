"""Provider eligibility and common forward entry point; no propagation kernels."""
from dataclasses import dataclass
import numpy as np
from . import emcd_forward as ni
from ..ionization_sites import IonizationSites
from ..imported_mdff import ImportedMDFF
from ..mdff_edges import selected_samples, validate_selected
from ..mdff_providers import load_provider


@dataclass(frozen=True)
class ImportedSettings(ni.ForwardSettings):
    model: str='imported'
    source: str=''
    ionizing_element: str=''
    core_edge: str='L2,3'
    magnetic_state: str=''
    site_indices: tuple|None=None
    selected_edges: tuple=()
    l3: float=float('nan')
    l2: float=float('nan')
    correction: bool=False


@dataclass(frozen=True)
class ProviderSettings(ImportedSettings):
    """Explicit source-backed XMCD/atomic inputs without inherited Ni physics."""
    model: str='xmcd'
    provider_schema: int=1
    provider_declaration: dict|None=None


def is_declared(cfg):
    return cfg.model=='imported' or isinstance(cfg,ImportedSettings)


def _source_settings(source,cls=ImportedSettings,**kwargs):
    d=source.metadata
    selections=validate_selected(d['element'],d['edge'],d['selected_ev'],source.energy_ev[[0,-1]])
    fields=dict(source=source.path,source_sha256=source.sha256,ionizing_element=d['element'],core_edge=d['edge'],
        magnetic_state=d['magnetic_state'],magnetization=tuple(d['magnetization_crystal']),axis_declared=True,
        selected_edges=() if d['edge']=='L2,3' else selections,
        l3=selections[0][1],l2=selections[-1][1])
    fields.update(kwargs)
    return cls(**fields)


def settings_for_source(path,**kwargs):
    return _source_settings(ImportedMDFF.load(path),**kwargs)


def settings_for_provider(path,model,declaration=None,**kwargs):
    from pathlib import Path
    import hashlib
    if model not in ('xmcd','atomic'):raise ValueError('Expected XMCD or atomic provider')
    cfg=ProviderSettings(model=model,source=str(path),source_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),
        provider_declaration=declaration)
    return _source_settings(load_provider(cfg),ProviderSettings,model=model,provider_declaration=declaration,**kwargs)


def source_for(cfg):
    if isinstance(cfg,ProviderSettings):
        if cfg.model not in ('xmcd','atomic'):raise ValueError('Declared provider identity must remain XMCD or atomic')
    elif isinstance(cfg,ImportedSettings) and cfg.model!='imported':
        raise ValueError('Imported MDFF provider identity cannot be changed into a historical Ni configuration')
    source=load_provider(cfg);d=source.metadata
    if not cfg.source_sha256:raise ValueError('Validate the imported MDFF checksum before calculation')
    if (cfg.ionizing_element!=d['element'] or cfg.core_edge!=d['edge'] or cfg.magnetic_state!=d['magnetic_state']):
        raise ValueError('Selected ionizing element, edge or magnetic state differs from imported source')
    if not cfg.axis_declared:raise ValueError('Explicitly acknowledge the source frame, magnetic axis and reversal assumptions')
    selections=validate_selected(d['element'],d['edge'],d['selected_ev'],source.energy_ev[[0,-1]])
    actual=selected_samples(cfg)
    if ([k for k,_ in actual]!=[k for k,_ in selections] or
        not np.allclose([v for _,v in actual],[v for _,v in selections],rtol=0,atol=1e-9)):
        raise ValueError('Imported selections must match declared source; no inherited Ni edge calibration')
    source.tensors(np.array([v for _,v in selections]),np.eye(3),cfg.magnetization)
    return source


def material_reason(structure,cfg=None):
    if cfg is None or not is_declared(cfg):return ni.material_reason(structure)
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


def energy_grid(cfg,requested=None):
    if not is_declared(cfg):return ni.energy_grid(cfg,requested)
    source=source_for(cfg);lo,hi=source.energy_ev[[0,-1]]
    values=[v for _,v in selected_samples(cfg)]
    if cfg.channeling_model not in ('single','double') or cfg.energy_scope not in ('full','edges'):raise ValueError('Unsupported imported tensor propagation/energy scope')
    if not 9<=cfg.energy_points<=501 or not 9<=cfg.grid<=193 or cfg.grid%2!=1 or not 2<=cfg.depth<=1025 or not 4<=cfg.subpixels<=256:raise ValueError('Numerical sampling exceeds supported bounds')
    if not np.isfinite([cfg.halfwidth,cfg.radius,*np.ravel(cfg.centers),*cfg.window]).all() or min(cfg.halfwidth,cfg.radius)<=0:raise ValueError('Invalid detector/grid controls')
    if requested is None:
        e=np.array(values) if cfg.energy_scope=='edges' else np.unique(np.r_[np.linspace(lo,hi,cfg.energy_points),values])
    else:e=np.asarray(requested,float)
    if e.ndim!=1 or not len(e) or not np.isfinite(e).all() or np.any(np.diff(e)<=0) or e[0]<lo or e[-1]>hi:raise ValueError('No imported MDFF energy extrapolation')
    if not all(np.any(np.isclose(e,v,rtol=0,atol=1e-9)) for v in values):raise ValueError('Requested grid must include declared selected energies')
    return e.copy()


def tensors(cfg,energy,R):
    return source_for(cfg).tensors(energy,R,cfg.magnetization) if is_declared(cfg) else ni.tensors(cfg,energy,R)


def calculate(*args,**kwargs):
    """Compatibility entry point to the one production orchestration."""
    return ni.calculate(*args,**kwargs)
