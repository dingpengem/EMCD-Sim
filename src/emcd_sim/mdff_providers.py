"""Validated source adapters; no propagation or contraction implementation.

Atomic and XMCD inputs reuse the accepted generators and tensor validator.
Temporary conversion is an internal detail: users select the original input,
and the saved source identity is always that original file's exact bytes.
"""
from dataclasses import replace
from functools import lru_cache
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json
import numpy as np
from .imported_mdff import ImportedMDFF


def load_provider(cfg):
    if hasattr(cfg,'provider_schema') and cfg.provider_schema!=1:
        raise ValueError('Unsupported MDFF provider configuration schema')
    if cfg.model == 'imported':
        return ImportedMDFF.load(cfg.source, cfg.source_sha256)
    if cfg.model not in ('xmcd', 'atomic'):
        raise ValueError('Unsupported MDFF provider')
    if not cfg.source_sha256:
        raise ValueError('Validate the original MDFF input checksum before calculation')
    try:
        raw = Path(cfg.source).read_bytes()
    except OSError as exc:
        raise ValueError('Missing/unreadable MDFF provider source: ' + cfg.source) from exc
    if hashlib.sha256(raw).hexdigest() != cfg.source_sha256:
        raise ValueError('MDFF source checksum changed; invalidate acknowledgement and validate again')
    declaration = json.dumps(getattr(cfg, 'provider_declaration', None), sort_keys=True)
    return _converted(cfg.model, str(Path(cfg.source).resolve()), raw, declaration)


@lru_cache(maxsize=8)
def _converted(model, original_path, raw, declaration_json):
    digest = hashlib.sha256(raw).hexdigest()
    with TemporaryDirectory(prefix='emcd-mdff-provider-') as folder:
        original = Path(folder) / ('parameters.json' if model == 'atomic' else 'source.xmcd')
        original.write_bytes(raw)
        output = Path(folder) / 'tensor.json'
        if model == 'atomic':
            from .atomic_ionization import export_atomic_parameters
            converted = export_atomic_parameters(original, output)
        else:
            from .generalized_xmcd import export_declared_xmcd
            converted = export_declared_xmcd(original, json.loads(declaration_json), output)
    metadata = dict(converted.metadata)
    if model == 'atomic':
        metadata['atomic_parameter_path'] = original_path
    else:
        metadata['xmcd_source_path'] = original_path
    metadata['provider_identity'] = model
    return replace(converted, metadata=metadata, path=original_path, sha256=digest)


def prepare_provider(cfg):
    """One preparation interface for XMCD, atomic and imported MDFF models.

    Historical Ni deliberately uses direct evaluation, not converted-grid
    interpolation. Selection here changes no downstream propagation kernel.
    """
    from .gui.material_inputs import ImportedSettings
    from .gui.forward_settings import NiForwardSettings
    if isinstance(cfg,ImportedSettings):
        from .gui.provider_preparation import DeclaredMDFFProvider
        return DeclaredMDFFProvider(cfg)
    if type(cfg) is NiForwardSettings and cfg.model in ('xmcd','atomic'):
        from .historical_ni import HistoricalNiProvider
        return HistoricalNiProvider(cfg)
    raise ValueError('Unsupported MDFF input: declare a source-backed material or an explicit NiForwardSettings preset')


def load_site_group_provider(group):
    """Resolve an acknowledged group source, preserving existing identity checks."""
    from .gui.material_inputs import ImportedSettings, source_for

    cfg = group.mdff_reference
    if not isinstance(cfg, ImportedSettings):
        raise ValueError('Site MDFF reference must be a declared provider configuration')
    source = source_for(cfg)
    if source.metadata['element'] != group.element:
        raise ValueError('MDFF source element differs from site-group element')
    return source


def prepare_site_group_providers(sites, energy_ev, crystal_to_microscope):
    """Resolve explicit group configurations without the legacy material gate.

    References must be existing ImportedSettings/ProviderSettings declarations,
    including their acknowledged source identity. Bare paths and arbitrary
    provider objects cannot supply those declarations. No per-source amplitude
    normalization or magnetic-axis alignment is inferred.
    """
    from .imported_mdff import proper_frame

    rotation = proper_frame(crystal_to_microscope)
    prepared = []
    for group in sites.groups:
        source = load_site_group_provider(group)
        # Existing provider validation checks explicit states, PSD tensors,
        # source frame and native axis; interpolation never extrapolates.
        tensors = source.tensors(energy_ev, rotation, group.magnetization)
        prepared.append((group, tensors, source.provenance()))
    return tuple(prepared)


def validate_group_reference(row, reference=None, window=None):
    name, element, indices, direction, current = row
    cfg = current if reference is None else reference
    if getattr(cfg,'magnetic_state',None)=='nonmagnetic':direction=cfg.magnetization
    from .multisite import IonizationSiteGroup
    group = IonizationSiteGroup(name,element,indices,cfg,direction,len(indices))
    source = load_site_group_provider(group)
    bounds = source.energy_ev[[0,-1]] if window is None else np.asarray(window.bounds_ev)
    if bounds[0] < source.energy_ev[0] or bounds[-1] > source.energy_ev[-1]:
        raise ValueError('Missing MDFF coverage within required modeled window')
    energy = np.unique(bounds if window is None or window.energy_ev is None else
                       np.r_[bounds,window.energy_ev])
    source.tensors(energy,np.eye(3),group.magnetization)
    return source


def bind_group_direction(row, window=None):
    """Prepare an acknowledged provider binding without changing any live row."""
    from .gui.material_inputs import ImportedSettings
    name,element,indices,direction,current = row
    if current is None:return current
    if not isinstance(current,ImportedSettings):
        raise ValueError(f'Group {name}: configure an acknowledged MDFF provider first')
    if current.magnetic_state=='nonmagnetic':
        validate_group_reference(row,current,window);return current
    if direction is None:raise ValueError(f'Group {name}: declare Material magnetization for this magnetic provider')
    for reversed_pair in (False,True):
        candidate=replace(current,magnetization=direction,pair_reversed=reversed_pair)
        try:
            validate_group_reference(row,candidate,window)
            return current if candidate==current else candidate
        except (ValueError,OSError) as exc:
            if not reversed_pair:first_error=exc
    try:
        d=load_provider(current).metadata
        detail=f"source axis {d['magnetization_crystal']}, frame_to_crystal={d['frame_to_crystal']}"
    except (ValueError,OSError):detail='source axis/frame unavailable because source validation failed'
    raise ValueError(f'Group {name}: requested crystal Cartesian direction {direction} is incompatible with '
        f'{detail} or its physical reversal pair. {first_error}. '
        'Open this group\'s MDFF Editor or supply a compatible validated source; accepted settings are unchanged.')
