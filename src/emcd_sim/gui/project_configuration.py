"""Configuration-only extension of the existing project folder.

Public entry points are in project_io. State is a dict with structure, settings,
config, magnetization_mode and optional site_groups (Stage 1), energy_windows,
energy_ev, global_config and editor_drafts (GroupMDFFDialog.snapshot values).
Incomplete rows use group_records with the IonizationSiteGroup field names and
mdff_reference=None; they are form state, never an alternative executable model.
Loaded group_records keep original references; site_groups uses verified portable
source overrides. config/global_config preserve saved declarations; the returned
effective_config/effective_global_config expose verified rebased paths (or None).
ready_for_calculation describes the active mode. No result arrays, source
regeneration or propagation occurs.
"""
from dataclasses import asdict, replace
from pathlib import Path
from datetime import datetime, timezone
import json
import shutil
import uuid

import numpy as np

from .. import __version__
from ..multisite_spectrum import ModeledEdgeWindow, _samples
from . import project_io as io
from .emcd_forward import Cancelled
from .generalized_forward import ImportedSettings
from .site_group_editor import validate_site_rows


def _encode_config(cfg):
    value = asdict(cfg)
    # These two explicitly unset peak fields are NaN in existing source-backed
    # settings. JSON null preserves absence; it does not invent an energy.
    for key in ('l3','l2'):
        if isinstance(value[key],float) and np.isnan(value[key]):value[key] = None
    return value


def _decode_config(value):
    value = dict(value)
    for key in ('l3','l2'):
        if key in value and value[key] is None:value[key] = float('nan')
    return io.config_from_dict(value)


def _records(state):
    if 'group_records' in state:records = [dict(row) for row in state['group_records']]
    else:
        sites = state.get('site_groups')
        if sites is not None:sites.validate_structure(state['structure'])
        records = [dict(group_id=g.group_id,label=state.get('labels',{}).get(g.group_id,g.group_id),
            element=g.element,indices=g.indices,magnetization=g.magnetization,multiplicity=g.multiplicity,
            normalization=g.normalization,mdff_reference=g.mdff_reference) for g in sites.groups] if sites is not None else []
    for record in records:
        if not isinstance(record.get('enabled',True),bool):raise ValueError('Group participation must be a boolean')
        if (isinstance(record['multiplicity'],bool) or not isinstance(record['multiplicity'],(int,np.integer)) or record['multiplicity']!=len(record['indices'])
                or record['normalization']!='mean_per_selected_atom'):
            raise ValueError('Group multiplicity/normalization differs from the Stage 1 per-atom convention')
        reference = record['mdff_reference']
        if reference is not None and not isinstance(reference,ImportedSettings):
            raise ValueError('Group MDFF references must be declared provider settings or unconfigured (None)')
    validate_site_rows(state['structure'].atoms,[(r['group_id'],r['element'],r['indices'],r['magnetization'],r['mdff_reference']) for r in records])
    return records


def _source_state(cfg, override=None, metadata=None):
    status = io.source_status(dict(config=cfg,metadata=metadata or {},
        source_overrides={} if override is None else dict(mdff=override,xmcd=override)))
    if not status:return dict(state='internal',verified=True,available=True)
    entry = next(iter(status.values()))
    entry['state'] = ('verified' if entry['verified'] else 'missing' if not entry['available'] else
                      'changed' if entry['sha256'] else 'unverified')
    return entry


def save_configuration(state,path,*,cancelled=lambda:False,progress=lambda s:None):
    """Save As to a new project folder, using existing manifest/source integrity."""
    mode = state.get('magnetization_mode')
    if mode not in ('global','local'):raise ValueError('Explicit Global/Local magnetization mode is required')
    if not isinstance(state.get('reverse_magnetization',False),bool):raise ValueError('Global reversal must be a boolean')
    records = _records(state)
    snapshot = io.structure_snapshot(state['structure'])
    atoms = state['structure'].atoms
    snapshot.update(cartesian_positions=atoms.positions.tolist(),atom_arrays={name:dict(dtype=str(value.dtype),values=value.tolist())
        for name,value in atoms.arrays.items() if name not in ('numbers','positions')})
    windows = state.get('energy_windows')
    if windows is not None and (set(windows)-{r['group_id'] for r in records}
            or any(not isinstance(w,ModeledEdgeWindow) for w in windows.values())):
        raise ValueError('Energy windows must name declared groups and contain ModeledEdgeWindow values')
    energy = state.get('energy_ev')
    if energy is not None:energy = _samples(energy).tolist()
    root = Path(path).resolve()
    if root.exists():raise FileExistsError('Configuration Save As requires a new folder')
    root.parent.mkdir(parents=True,exist_ok=True)
    temp = root.parent/('.'+root.name+'.saving_'+uuid.uuid4().hex);temp.mkdir()
    def check(stage):
        if cancelled():raise Cancelled()
        progress(stage)
    try:
        sources = {};overrides = state.get('source_overrides',{})
        def source(key,cfg):
            if cfg is None:return
            resolved = str(Path(overrides.get(key,cfg.source)).resolve())
            entry = dict(original_path=cfg.source,resolved_path=resolved,sha256=cfg.source_sha256)
            status = _source_state(cfg,resolved,state.get('metadata') if key=='config' else None)
            if status['state']=='internal':return
            if status['verified'] and status['state']!='internal':
                try:raw = io.portable_mdff_bytes(cfg,resolved)
                except (ValueError,OSError):raw = None  # Preserve an invalid declaration as non-executable form state.
                if raw is not None:
                    name = f'mdff_{len(sources)}.json';(temp/name).write_bytes(raw);entry['attachment'] = name
            sources[key] = entry
        for record in records:
            check('Saving source declarations for '+record['group_id'])
            source('group:'+record['group_id'],record['mdff_reference'])
        source('config',state['config']);source('global_config',state.get('global_config'))
        saved_records = [dict(r,mdff_reference=None if r['mdff_reference'] is None else _encode_config(r['mdff_reference'])) for r in records]
        extension = dict(version=1,magnetization_mode=mode,reverse_magnetization=state.get('reverse_magnetization',False),
            groups=saved_records,normalization='mean_per_selected_ionizing_atom',
            selected_atom_count=sum(r['multiplicity'] for r in records if r.get('enabled',True)),
            energy_windows=None if windows is None else {key:asdict(w) for key,w in windows.items()},energy_ev=energy,
            global_config=None if state.get('global_config') is None else _encode_config(state['global_config']),
            editor_drafts=state.get('editor_drafts',{}))
        io._json(temp/'structure.json',snapshot)
        io._json(temp/'input_parameters.json',dict(settings=asdict(state['settings']),mdff=_encode_config(state['config']),
            structure_snapshot=snapshot,multisite_configuration=extension,configuration_metadata=state.get('metadata',{})))
        check('Writing configuration project manifest')
        manifest = dict(schema_version=io.SCHEMA,kind='configuration',complete=True,
            software_version=__version__,saved_utc=datetime.now(timezone.utc).isoformat(),
            files={p.name:io.sha256(p) for p in temp.iterdir() if p.is_file()},configuration_sources=sources)
        io._json(temp/'project.json',manifest)
        load_configuration(temp,cancelled=cancelled,progress=progress)
        check('Finalizing configuration project');io._rename_folder(temp,root,cancelled)
        return root
    finally:
        if temp.exists() and temp.parent==root.parent and temp.name.startswith('.'+root.name+'.saving_'):shutil.rmtree(temp)


def load_configuration(path,*,cancelled=lambda:False,progress=lambda s:None):
    """Load this extension or extract a legacy project's configuration only.

    Invalid assignments are rejected. Unavailable/changed/invalid MDFF sources
    remain recorded, with ready_for_calculation=False in the active mode. There
    is no fallback to Global M or a default provider. Missing inactive local
    sources do not alter a legacy Global configuration.
    """
    root = Path(path).resolve()
    def check(stage):
        if cancelled():raise Cancelled()
        progress(stage)
    check('Loading saved configuration')
    manifest = json.loads((root/'project.json').read_text(encoding='utf-8'))
    if manifest.get('schema_version')!=io.SCHEMA or manifest.get('complete') is not True:
        raise ValueError('Unsupported or incomplete project manifest')
    configuration = manifest.get('kind')=='configuration'
    names = set(manifest.get('files',{})) if configuration else {'input_parameters.json','structure.json'}
    if not {'input_parameters.json','structure.json'}<=names:raise ValueError('Missing configuration files in manifest')
    for name in names:
        check('Verifying '+name);file = io.safe_path(root,name)
        if not file.is_file() or io.sha256(file)!=manifest['files'].get(name):raise ValueError('Missing or corrupted project file: '+name)
    parameters = json.loads((root/'input_parameters.json').read_text(encoding='utf-8'))
    snapshot = json.loads((root/'structure.json').read_text(encoding='utf-8'))
    legacy_metadata = {}
    if not configuration and 'metadata.json' in manifest.get('files',{}):
        file = root/'metadata.json'
        if io.sha256(file)!=manifest['files']['metadata.json']:raise ValueError('Corrupted legacy metadata')
        legacy_metadata = json.loads(file.read_text(encoding='utf-8'))
    saved_metadata = parameters.get('configuration_metadata',legacy_metadata)
    structure = io.restore_structure(snapshot)
    extension = parameters.get('multisite_configuration')
    if extension is not None and extension.get('version')!=1:raise ValueError('Unsupported multi-site configuration version')
    if configuration and extension is None:raise ValueError('Configuration extension is missing')
    extension = extension or dict(magnetization_mode='global',groups=[],energy_windows=None,energy_ev=None,
                                 reverse_magnetization=False,global_config=None,editor_drafts={})
    mode = extension['magnetization_mode']
    if mode not in ('global','local') or not isinstance(extension['reverse_magnetization'],bool):
        raise ValueError('Invalid saved magnetization mode or reversal state')
    records = [dict(r,indices=tuple(r['indices']),magnetization=None if r['magnetization'] is None else tuple(r['magnetization']),
                    mdff_reference=None if r['mdff_reference'] is None else _decode_config(r['mdff_reference'])) for r in extension['groups']]
    state = dict(structure=structure,structure_snapshot=snapshot,settings=io.settings_from_dict(parameters['settings']),
        config=_decode_config(parameters['mdff']),metadata=saved_metadata,magnetization_mode=mode,reverse_magnetization=extension['reverse_magnetization'],
        group_records=records,global_config=None if extension['global_config'] is None else _decode_config(extension['global_config']),
        editor_drafts=extension['editor_drafts'],energy_ev=extension['energy_ev'],project_path=str(root))
    _records(state)
    if parameters.get('multisite_configuration') is not None and (
            extension['normalization']!='mean_per_selected_ionizing_atom'
            or extension['selected_atom_count']!=sum(r['multiplicity'] for r in records if r.get('enabled',True))):
        raise ValueError('Saved selected-atom normalization is inconsistent')
    windows = extension['energy_windows']
    windows = None if windows is None else {key:ModeledEdgeWindow(**value) for key,value in windows.items()}
    if windows is not None and set(windows)-{r['group_id'] for r in records}:raise ValueError('Unknown group in saved energy windows')
    if state['energy_ev'] is not None:state['energy_ev'] = _samples(state['energy_ev'])
    state.update(energy_windows=windows,source_states={},source_overrides={},issues=[],site_groups=None)
    sources = manifest.get('configuration_sources',{})
    def resolve(key,cfg):
        if cfg.model=='multisite' or (cfg.model=='atomic' and getattr(cfg,'provider_schema',None)!=1):
            status = dict(state='internal',verified=True,available=True);state['source_states'][key] = status
            return cfg,status
        descriptor = sources.get(key,{})
        original = descriptor.get('original_path',cfg.source)
        if descriptor and (original!=cfg.source or descriptor['sha256']!=cfg.source_sha256):
            raise ValueError('Saved source identity differs from provider declaration')
        attachment = descriptor.get('attachment')
        if not configuration and key=='config':
            old = manifest.get('atomic_parameter_source') or manifest.get('manual_tensor_source')
            if old:
                if old['sha256']!=cfg.source_sha256:raise ValueError('Legacy attachment identity mismatch')
                attachment = old['path']
        effective_path = str(io.safe_path(root,attachment)) if attachment else descriptor.get('resolved_path',cfg.source)
        if attachment and manifest['files'].get(attachment)!=cfg.source_sha256:raise ValueError('Portable source identity mismatch')
        status = _source_state(cfg,effective_path,saved_metadata if key=='config' else None)
        status.update(original_path=original,portable=bool(attachment));state['source_states'][key] = status
        if effective_path!=cfg.source:state['source_overrides'][key] = effective_path
        return replace(cfg,source=effective_path),status
    effective = [];invalid_groups = []
    from .group_mdff import validate_group_reference
    for r in records:
        check('Validating '+r['group_id']);key = 'group:'+r['group_id'];reference = r['mdff_reference']
        if not r.get('enabled',True):
            if reference is None:state['source_states'][key]=dict(state='excluded',verified=False)
            else:resolve(key,reference)
            continue
        if reference is None:
            state['source_states'][key] = dict(state='unconfigured',verified=False)
            invalid_groups.append(r['group_id']+': MDFF is unconfigured');continue
        cfg,status = resolve(key,reference)
        if not status['verified']:
            invalid_groups.append(r['group_id']+': source '+status['state']);continue
        row = (r['group_id'],r['element'],r['indices'],r['magnetization'],cfg)
        try:
            provider = validate_group_reference(row,window=None if windows is None else windows.get(r['group_id']))
            if state['energy_ev'] is not None and (windows is None or r['group_id'] in windows):
                samples = state['energy_ev']
                if windows is not None:
                    lo,hi = windows[r['group_id']].bounds_ev;samples = samples[(samples>=lo)&(samples<=hi)]
                if len(samples) and (samples[0]<provider.energy_ev[0] or samples[-1]>provider.energy_ev[-1]):
                    raise ValueError('Missing MDFF coverage within requested energy samples')
        except (ValueError,OSError) as exc:
            status['validation_error'] = str(exc);invalid_groups.append(r['group_id']+': '+str(exc));continue
        effective.append(row)
    state['issues'].extend(invalid_groups)
    active_valid = True
    for key in ('config','global_config'):
        cfg = state[key]
        if cfg is not None:
            effective_cfg,status = resolve(key,cfg)
            state['effective_'+key] = effective_cfg if status['verified'] else None
            if mode=='global' and key=='config' and not status['verified']:
                state['issues'].append('Global source '+status['state']);active_valid = False
            elif mode=='global' and key=='config' and isinstance(cfg,ImportedSettings):
                from .generalized_forward import source_for
                try:source_for(effective_cfg)
                except (ValueError,OSError) as exc:
                    status['validation_error'] = str(exc);state['issues'].append('Global configuration: '+str(exc));active_valid = False
                    state['effective_'+key] = None
        else:state['effective_'+key] = None
    if mode=='local':
        active_valid = any(r.get('enabled',True) for r in records) and not invalid_groups and state['config'].model=='multisite'
        if not records:state['issues'].append('Local mode has no site groups')
        if state['config'].model!='multisite':state['issues'].append('Local mode requires explicit multi-site forward settings; Global M is not a substitute')
        if windows=={} or (windows is None and state['energy_ev'] is None):
            state['issues'].append('Local energy selection is unconfigured: supply requested samples or modeled edge windows');active_valid = False
        if active_valid:state['site_groups'] = validate_site_rows(structure.atoms,effective)
    elif state['config'].model=='multisite':
        state['issues'].append('Global mode requires the saved legacy configuration; no implicit mode conversion');active_valid = False
    elif state['config'].model not in ('atomic','xmcd','imported'):
        state['issues'].append('Unknown Global MDFF model');active_valid = False
    state['ready_for_calculation'] = active_valid
    check('Configuration restored; no physical propagation or result arrays loaded')
    return state
