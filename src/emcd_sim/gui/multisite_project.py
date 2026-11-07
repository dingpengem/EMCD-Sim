"""Multi-site records within the established project JSON/NPZ files.

Group means and original total/weighted-sum arrays are retained losslessly.
Additive group/element curves are reconstructed by the existing results helper;
no extra copies of those derived curves are stored. Loading never reads MDFFs.
"""
from dataclasses import asdict
from pathlib import Path
import numpy as np

from .project_configuration import _encode_config, _decode_config, _records
from .multisite_results import SPECTRAL_KEYS


def _entry(prefix,entry,shared=False):
    return dict(prefix=prefix,spectra=[key for key in entry['spectra'] if key!='energy_ev' or not shared],
        maps={edge:dict(prefix=prefix+'map'+str(i)+'__',fields=list(values)) for i,(edge,values) in enumerate(entry['maps'].items())},
        metadata=entry.get('metadata') if shared else None)


def _method(name,result):
    return dict(config=_encode_config(result['config']),total=_entry(name+'__total__',result),
        groups=[dict(group_id=gid,**_entry(name+'__group'+str(i)+'__',entry,True)) for i,(gid,entry) in enumerate(result['groups'].items())],
        weighted_sum=_entry(name+'__sum__',result['weighted_sum'],True) if 'weighted_sum' in result else None)


def _entries(result,descriptor):
    yield result,descriptor['total']
    for record in descriptor['groups']:yield result['groups'][record['group_id']],record
    if descriptor['weighted_sum'] is not None:yield result['weighted_sum'],descriptor['weighted_sum']


def pack_method(name,result,angular,spectra):
    for entry,record in _entries(result,_method(name,result)):
        if not np.array_equal(entry['spectra']['energy_ev'],result['spectra']['energy_ev']):
            raise ValueError('Stored multi-site entries must retain the same calculated union energy grid')
        spectra.update({record['prefix']+key:entry['spectra'][key] for key in record['spectra']})
        for edge,fields in entry['maps'].items():
            angular.update({record['maps'][edge]['prefix']+key:value for key,value in fields.items()})


def project_metadata(result):
    methods=result.get('methods',{result.get('method','bloch'):result})
    configuration=result.get('configuration');saved=None
    if configuration is not None:
        records=_records(configuration)
        saved=dict(groups=[dict(row,mdff_reference=None if row['mdff_reference'] is None else _encode_config(row['mdff_reference'])) for row in records],
            config=_encode_config(configuration['config']),magnetization_mode=configuration['magnetization_mode'],
            reverse_magnetization=configuration.get('reverse_magnetization',False),
            energy_ev=None if configuration.get('energy_ev') is None else np.asarray(configuration['energy_ev']).tolist(),
            energy_windows=None if configuration.get('energy_windows') is None else {key:asdict(w) for key,w in configuration['energy_windows'].items()},
            global_config=None if configuration.get('global_config') is None else _encode_config(configuration['global_config']),
            editor_drafts=configuration.get('editor_drafts',{}))
    return dict(version=1,methods={name:_method(name,r) for name,r in methods.items()},configuration=saved)


def attach_sources(result,root,managed):
    from . import project_io as io
    configuration=result.get('configuration')
    references={r['group_id']:r['mdff_reference'] for r in _records(configuration)} if configuration is not None else {}
    attached={}
    for i,(gid,entry) in enumerate(result['groups'].items()):
        source=entry['metadata']['source'];cfg=references.get(gid)
        path=Path(result.get('source_overrides',{}).get('group:'+gid,source['path']))
        if cfg is None or not source.get('sha256') or cfg.source_sha256!=source['sha256']:continue
        try:
            raw=io.portable_mdff_bytes(cfg,path,source.get('atomic_parameter_source_utf8'))
        except (ValueError,OSError):continue  # Missing/stale sources never prevent viewing saved arrays.
        if raw is not None:
            name=f'group{i}_mdff.json';(root/name).write_bytes(raw);managed.add(name)
            attached[gid]=dict(path=name,sha256=cfg.source_sha256)
    return attached


def restore_entry(record,angular,spectra,energy=None):
    values={key:spectra[record['prefix']+key] for key in record['spectra']}
    if energy is not None:values['energy_ev']=energy
    maps={edge:{key:angular[desc['prefix']+key] for key in desc['fields']} for edge,desc in record['maps'].items()}
    entry=dict(spectra=values,maps=maps)
    if record['metadata'] is not None:entry['metadata']=record['metadata']
    return entry


def restore_groups(result,descriptor,angular,spectra):
    from .site_group_editor import validate_site_rows
    from .project_io import restore_structure
    energy=result['spectra']['energy_ev'];n=result['metadata']['multisite']['selected_atom_count']
    groups={};rows=[]
    for record in descriptor['groups']:
        gid=record['group_id']
        if gid in groups:raise ValueError('Duplicate saved site-group identity')
        entry=restore_entry(record,angular,spectra,energy);meta=entry['metadata']
        if (meta['multiplicity']!=len(meta['indices']) or meta['normalization']!='mean_per_selected_atom'
                or not np.isclose(meta['contribution_weight'],meta['multiplicity']/n,rtol=1e-12,atol=0)):
            raise ValueError('Inconsistent saved site multiplicity/normalization')
        if not set(SPECTRAL_KEYS)<=set(entry['spectra']):raise ValueError('Saved group spectrum is incomplete')
        if any(entry['spectra'][key].shape!=energy.shape or not np.isfinite(entry['spectra'][key]).all() for key in SPECTRAL_KEYS):
            raise ValueError('Saved group spectrum dimensions/values are inconsistent')
        for fields in entry['maps'].values():
            if not {'I_plus','I_minus','I_nonmag','I_mag'}<=set(fields) or any(a.shape!=result['qx'].shape or not np.isfinite(a).all() for a in fields.values()):
                raise ValueError('Saved group maps are inconsistent')
        rows.append((gid,meta['element'],meta['indices'],meta['magnetization_crystal'],None))
        entry.update(qx=result['qx'],qy=result['qy'],weights=result['weights']);groups[gid]=entry
    validate_site_rows(restore_structure(result['structure_snapshot']).atoms,rows)
    if not groups or sum(g['metadata']['multiplicity'] for g in groups.values())!=n:raise ValueError('Saved total selected-atom denominator is inconsistent')
    channels=result['metadata']['multisite']['channels']
    if set(channels)!=set(groups) or any(np.asarray(c['active_energy_mask']).shape!=energy.shape for c in channels.values()):
        raise ValueError('Saved channel coverage is inconsistent')
    result['groups']=groups
    if descriptor['weighted_sum'] is not None:
        entry=restore_entry(descriptor['weighted_sum'],angular,spectra,energy)
        if (not set(SPECTRAL_KEYS)<=set(entry['spectra'])
                or any(entry['spectra'][key].shape!=energy.shape or not np.isfinite(entry['spectra'][key]).all() for key in SPECTRAL_KEYS)):
            raise ValueError('Saved unnormalized weighted spectrum is inconsistent')
        entry.update(qx=result['qx'],qy=result['qy'],weights=result['weights']);result['weighted_sum']=entry


def restore_context(result,descriptor,manifest,root):
    from . import project_io as io
    if descriptor.get('version')!=1:raise ValueError('Unsupported saved multi-site result extension')
    saved=descriptor.get('configuration')
    if saved is not None:
        from ..multisite_spectrum import ModeledEdgeWindow
        state=dict(structure=io.restore_structure(result['structure_snapshot']),settings=result['settings'],
            config=_decode_config(saved['config']),magnetization_mode=saved['magnetization_mode'],
            reverse_magnetization=saved['reverse_magnetization'],
            group_records=[dict(row,mdff_reference=None if row['mdff_reference'] is None else _decode_config(row['mdff_reference'])) for row in saved['groups']],
            energy_ev=saved['energy_ev'],energy_windows=None if saved['energy_windows'] is None else {key:ModeledEdgeWindow(**w) for key,w in saved['energy_windows'].items()},
            global_config=None if saved['global_config'] is None else _decode_config(saved['global_config']),editor_drafts=saved['editor_drafts'])
        records=_records(state)
        if {r['group_id'] for r in records}!=set(result['groups']):raise ValueError('Saved provider assignments differ from result groups')
        for row in records:
            meta=result['groups'][row['group_id']]['metadata'];ref=row['mdff_reference']
            if (ref is None or ref.source_sha256!=meta['source'].get('sha256') or row['element']!=meta['element']
                    or tuple(row['indices'])!=tuple(meta['indices']) or row['multiplicity']!=meta['multiplicity']
                    or not np.allclose(row['magnetization'],meta['magnetization_crystal'],rtol=0,atol=1e-12)):
                raise ValueError('Saved provider declaration differs from calculated group identity')
        if state['magnetization_mode']!='local' or state['config'].model!='multisite':raise ValueError('Saved multi-site result is not a Local configuration')
        if state['reverse_magnetization']!=result['metadata']['multisite']['global_reversal']:
            raise ValueError('Saved configuration reversal differs from calculated magnetic state')
        result['configuration']=state
    overrides={}
    for gid,attachment in (manifest or {}).get('multisite_sources',{}).items():
        source=result['groups'][gid]['metadata']['source']
        if attachment['sha256']!=source['sha256'] or manifest['files'].get(attachment['path'])!=source['sha256']:
            raise ValueError('Saved group attachment identity mismatch')
        overrides['group:'+gid]=str(io.safe_path(root,attachment['path']))
    result['source_overrides']=overrides
    if saved is not None:result['configuration']['source_overrides']=overrides
    for method in result['methods'].values():
        method['source_overrides']=overrides
        if saved is not None:method['configuration']=result['configuration']
