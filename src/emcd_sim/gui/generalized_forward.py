"""Provider eligibility and common forward entry point; no propagation kernels."""
from dataclasses import dataclass
import numpy as np
from . import emcd_forward as compatibility
from ..imported_mdff import ImportedMDFF
from ..mdff_edges import selected_samples, validate_selected
from ..mdff_providers import load_provider


@dataclass(frozen=True)
class ImportedSettings(compatibility.ForwardSettings):
    model: str='imported'
    source: str=''
    ionizing_element: str=''
    core_edge: str='L2,3'
    magnetic_state: str=''
    site_indices: tuple|None=None
    selected_edges: tuple=()
    pair_reversed: bool=False
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
    if not isinstance(cfg.pair_reversed,bool):raise ValueError('Physical pair selection must be a boolean')
    if cfg.pair_reversed:
        from .provider_direction import ReversedProviderPair
        source=ReversedProviderPair(source)
    source.tensors(np.array([v for _,v in selections]),np.eye(3),cfg.magnetization)
    return source


def material_reason(structure,cfg=None):
    from ..mdff_providers import prepare_provider
    return prepare_provider(cfg or compatibility.ForwardSettings()).material_reason(structure)


def energy_grid(cfg,requested=None):
    from ..mdff_providers import prepare_provider
    from .provider_preparation import provider_energy_grid
    return provider_energy_grid(prepare_provider(cfg),cfg,requested)


def tensors(cfg,energy,R):
    from ..mdff_providers import prepare_provider
    return prepare_provider(cfg).tensors(energy,R)


# Historical import path, same callable; no extra orchestration wrapper.
from .emcd_forward import calculate
