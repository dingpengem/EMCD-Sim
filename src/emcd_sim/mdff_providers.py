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
from .ionization_sites import IonizationSites
from .mdff_edges import selected_samples, validate_selected
from emcd_sim.material_inputs import ImportedSettings, ProviderSettings
from emcd_sim.forward_settings import NiForwardSettings
from .historical_ni import HistoricalNiProvider


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
    if isinstance(cfg,ImportedSettings):
        return DeclaredMDFFProvider(cfg)
    if type(cfg) is NiForwardSettings and cfg.model in ('xmcd','atomic'):
        return HistoricalNiProvider(cfg)
    raise ValueError('Unsupported MDFF input: declare a source-backed material or an explicit NiForwardSettings preset')


def load_site_group_provider(group):
    """Resolve an acknowledged group source, preserving existing identity checks."""

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


def is_declared(cfg):
    return cfg.model=='imported' or isinstance(cfg,ImportedSettings)


def settings_from_source(provider,cls=ImportedSettings,**kwargs):
    """Build saved inputs from a validated source and explicit caller controls.

    Both file-based constructors and editors with an already validated source
    use this translation. Caller declarations remain explicit and are checked
    against the source by source_for before calculation.
    """
    d=provider.metadata
    selections=validate_selected(d['element'],d['edge'],d['selected_ev'],provider.energy_ev[[0,-1]])
    fields=dict(source=provider.path,source_sha256=provider.sha256,ionizing_element=d['element'],core_edge=d['edge'],
        magnetic_state=d['magnetic_state'],magnetization=tuple(d['magnetization_crystal']),axis_declared=True,
        selected_edges=() if d['edge']=='L2,3' else selections,
        l3=selections[0][1],l2=selections[-1][1])
    fields.update(kwargs)
    return cls(**fields)


def settings_for_source(path,**kwargs):
    return settings_from_source(ImportedMDFF.load(path),**kwargs)


def settings_for_provider(path,model,declaration=None,**kwargs):
    if model not in ('xmcd','atomic'):raise ValueError('Expected XMCD or atomic provider')
    cfg=ProviderSettings(model=model,source=str(path),source_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),
        provider_declaration=declaration)
    return settings_from_source(load_provider(cfg),ProviderSettings,model=model,provider_declaration=declaration,**kwargs)


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
        source=ReversedProviderPair(source)
    source.tensors(np.array([v for _,v in selections]),np.eye(3),cfg.magnetization)
    return source


def material_reason(structure,cfg):
    return prepare_provider(cfg).material_reason(structure)


def energy_grid(cfg,requested=None):
    return provider_energy_grid(prepare_provider(cfg),cfg,requested)


def tensors(cfg,energy,R):
    return prepare_provider(cfg).tensors(energy,R)


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
        from .wien2k_xmcd import load_wien2k_xmcd
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


class ReversedProviderPair:
    def __init__(self, source):
        if (source.metadata['magnetic_state'] != 'uniform_fm' or
                source.metadata['reversal'] != 'explicit_pair_shared_even'):
            raise ValueError('Direction reversal requires an explicitly declared, validated physical tensor pair')
        self.source = source

    def __getattr__(self, name):
        return getattr(self.source, name)

    @property
    def plus(self):return self.source.minus

    @property
    def minus(self):return self.source.plus

    def tensors(self, energy, crystal_to_microscope, magnetization):
        # The underlying provider still validates its native axis and full frame.
        m=np.asarray(magnetization,float);native=np.asarray(self.metadata['magnetization_crystal'],float)
        if (m.shape!=(3,) or not np.isfinite(m).all() or not np.isfinite(np.linalg.norm(m))
                or np.linalg.norm(m)<1e-12 or not np.allclose(m/np.linalg.norm(m),-native/np.linalg.norm(native),rtol=0,atol=1e-10)):
            raise ValueError('Physical minus-state selection requires the opposite of the declared source axis; it does not rotate the tensor frame')
        pair = self.source.tensors(energy,crystal_to_microscope,-m)
        return pair[1],pair[0]

    def provenance(self):
        return dict(self.source.provenance(),direction_binding=dict(
            pair_state='minus',source_magnetization_crystal=self.metadata['magnetization_crystal'],
            effective_magnetization_crystal=(-np.asarray(self.metadata['magnetization_crystal'])).tolist()))
