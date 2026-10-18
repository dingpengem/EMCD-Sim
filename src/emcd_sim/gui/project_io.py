"""Versioned, checksummed project folders and read-only Stage B/C import.

Loading constructs saved plotting context only. No potential, tensor or
propagation routines are called, and external sources are never read to plot.
"""
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime,timezone
import hashlib,json,os,shutil,uuid,zipfile,time
import numpy as np
from ase import Atoms
from .geometry import Structure,Settings,excitation
from .emcd_forward import ForwardSettings,Cancelled
from ..ni_local_mdff import NiLocalConfig
from ..geometry import VirtualDetector

SCHEMA=1
ARRAY_FILES=('angular_maps.npz','virtual_detector_eels.npz','diffraction_pattern.npz')


def sha256(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def structure_snapshot(structure):
    a=structure.atoms
    return dict(species=a.get_chemical_symbols(),lattice_angstrom=a.cell.array.tolist(),fractional_positions=a.get_scaled_positions().tolist(),
        pbc=a.pbc.tolist(),occupancies=a.info.get('occupancy',{}),source=structure.source,sha256=structure.sha256,import_warnings=structure.import_warnings,
        description=structure.description())


def restore_structure(snapshot):
    if not snapshot:raise ValueError('Legacy export has no complete numeric crystal snapshot; inspect results read-only, or prepare a verified structure explicitly.')
    atoms=Atoms(snapshot['species'],cell=snapshot['lattice_angstrom'],scaled_positions=snapshot['fractional_positions'],pbc=snapshot['pbc'])
    atoms.info['occupancy']=snapshot.get('occupancies',{})
    return Structure(atoms,snapshot['source'],snapshot.get('sha256',''),snapshot.get('import_warnings',''))


def structures_match(snapshot,structure):
    current=structure_snapshot(structure)
    return (snapshot['species']==current['species'] and snapshot.get('sha256','')==current.get('sha256','')
        and snapshot.get('occupancies',{})==current.get('occupancies',{})
        and all(np.allclose(snapshot[k],current[k],rtol=0,atol=1e-12) for k in ('lattice_angstrom','fractional_positions','pbc')))


def settings_from_dict(value):
    return Settings(**{k:tuple(v) if k in ('zone','target','tilt') else v for k,v in value.items()})


def config_from_dict(value):
    d=dict(value);d['atomic']=NiLocalConfig(**d.get('atomic',{}))
    for k in ('magnetization','centers','window'):
        if k in d:d[k]=tuple(tuple(v) if isinstance(v,list) else v for v in d[k])
    return ForwardSettings(**d)


class SavedCrystal:
    def __init__(self,metadata,snapshot):
        self.positions={tuple(h):np.r_[g,0.] for h,g in zip(metadata['beam_hkl'],metadata['g'])}
        R=np.asarray(metadata['frame'])
        self.lattice_angstrom=np.asarray(snapshot['lattice_angstrom'])@R.T if snapshot else None
        self.fractional_positions=np.asarray(snapshot['fractional_positions']) if snapshot else None
        self.species=tuple(snapshot['species']) if snapshot else ()
    def g_vector(self,hkl):
        try:return self.positions[tuple(hkl)].copy()
        except KeyError as exc:raise ValueError('Reflection absent from saved diffraction context') from exc


def plotting_model(meta,snapshot):
    cfg=config_from_dict(meta['mdff']);settings=settings_from_dict(meta['settings'])
    elastic=SimpleNamespace(crystal=SavedCrystal(meta,snapshot),beams=SimpleNamespace(hkl=tuple(tuple(h) for h in meta['beam_hkl'])),
        reciprocal_vectors_xy=np.asarray(meta['g']),microscope=SimpleNamespace(incident_k_xy=-np.asarray(meta['za_q']),acceleration_kv=settings.voltage,tilt_mrad_xy=settings.tilt))
    return SimpleNamespace(elastic=elastic,detectors={k:VirtualDetector(tuple(p),cfg.radius) for k,p in zip(('A','B'),cfg.centers)},chiral_groups=None)


def pack_arrays(result):
    methods=result.get('methods',{result.get('method','bloch'):result});labels=list(methods)
    angular=dict(qx=result['qx'],qy=result['qy'],method_labels=np.asarray(labels))
    meta=result['metadata']
    spectra=dict(method_labels=np.asarray(labels),channeling_model=np.array(result['config'].channeling_model));diffraction=dict(method_labels=np.asarray(labels),depth_nm=result['depth_nm'],beam_hkl=np.asarray(meta['beam_hkl']),g=np.asarray(meta['g']),frame=np.asarray(meta['frame']),
        excitation_errors_inv_angstrom=excitation(np.asarray(meta['g']),result['settings'].tilt,result['settings'].voltage),zone_axis_q=np.asarray(meta['za_q']),transmitted_q=np.asarray(meta['transmitted_q']))
    for name,r in methods.items():
        angular.update({name+'__'+edge+'__'+k:v for edge,m in r['maps'].items() for k,v in m.items()})
        angular[name+'__coherence']=r['coherence']
        from .prb_benchmark import benchmark_spectra
        sp=dict(r['spectra'],**benchmark_spectra(r['spectra'])[0])
        spectra.update({name+'__'+k:v for k,v in sp.items()})
        diffraction[name+'__amplitudes']=r['amplitudes']
    angular.update({'weight_'+k:v for k,v in result['weights'].items()})
    fft=result.get('fft',{})
    for k,v in fft.items():
        if isinstance(v,np.ndarray):diffraction['fft_full__'+k]=v
    # Store the primary arrays once under the explicit method name. Stage C
    # labels/prefixes remain; no duplicated large primary-array copies.
    return dict(zip(ARRAY_FILES,(angular,spectra,diffraction)))


def safe_path(root,name):
    p=(root/name).resolve()
    if p.parent!=root.resolve():raise ValueError('Project filenames must be simple files inside the project directory')
    return p


def _read_npz(path):
    with zipfile.ZipFile(path) as z:
        if sum(i.file_size for i in z.infolist())>1024**3:raise ValueError('Project NPZ exceeds 1 GiB uncompressed array limit')
    with np.load(path,allow_pickle=False) as f:
        arrays={k:f[k] for k in f.files}
    for a in arrays.values():
        if a.dtype.hasobject:raise ValueError('Object arrays are not supported')
        a.setflags(write=False)
    return arrays


def _json(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def _rename_folder(source,target,cancelled=lambda:False):
    # Windows indexers/virus scanners can briefly hold a just-closed NPZ or
    # directory. Retry only sharing/access errors, without bypassing access
    # controls; persistent errors still fail and leave the previous project.
    for attempt in range(8):
        if cancelled():raise Cancelled()
        try:return source.rename(target)
        except PermissionError:
            if attempt==7:raise
            time.sleep(.05*(attempt+1))


def save_project(result,path,*,replace_existing=False,cancelled=lambda:False,progress=lambda s:None):
    """Write/validate a sibling temporary folder, then atomically install it.

    Existing folder replacement requires an explicit caller decision. On any
    failure before installation the previous folder is untouched; failed final
    replacement restores the previous folder. Temporary cleanup is scoped.
    """
    root=Path(path).resolve();root.parent.mkdir(parents=True,exist_ok=True)
    if root.exists() and not replace_existing:raise FileExistsError('Save As requires a new folder or explicit replacement approval')
    if root.exists() and not (root/'project.json').exists():raise ValueError('Only an existing EMCD project can be replaced; choose a new project folder')
    temp=root.parent/('.'+root.name+'.saving_'+uuid.uuid4().hex);backup=root.parent/('.'+root.name+'.previous_'+uuid.uuid4().hex);temp.mkdir()
    def check(stage):
        if cancelled():raise Cancelled()
        progress(stage)
    try:
        check('Saving complete numerical arrays');arrays=pack_arrays(result);shapes={}
        for name,values in arrays.items():
            check('Saving '+name);np.savez_compressed(temp/name,**values)
            shapes[name]={k:dict(shape=list(v.shape),dtype=str(v.dtype)) for k,v in values.items()}
        methods=result.get('methods',{result.get('method','bloch'):result})
        snapshot=result.get('structure_snapshot');meta=result['metadata']
        _json(temp/'metadata.json',meta)
        _json(temp/'comparison_metadata.json',dict(method_labels=list(methods),primary_method=result.get('method','bloch'),methods={name:r['metadata'] for name,r in methods.items()},diagnostics=result.get('comparison',{})))
        _json(temp/'input_parameters.json',dict(settings=asdict(result['settings']),mdff=asdict(result['config']),structure_snapshot=snapshot))
        _json(temp/'structure.json',snapshot)
        from .emcd_forward import metrics
        _json(temp/'validity.json',{name:dict(postedge_valid=r['metadata']['alpha'] is not None,
            paired_map_valid={edge:'D_raw' in m for edge,m in r['maps'].items()},available_fields={edge:list(m) for edge,m in r['maps'].items()},
            scalar_metric_valid={edge:{key:value is not None for key,value in row.items()} for edge,row in metrics(r).items()}) for name,r in methods.items()})
        if snapshot:
            from ase.io import write
            write(temp/'structure.cif',restore_structure(snapshot).atoms,format='cif')
        managed=set(ARRAY_FILES)|{'project.json','metadata.json','comparison_metadata.json','input_parameters.json','structure.json','structure.cif','validity.json'}
        if root.exists():
            for child in root.iterdir():
                if child.name in managed:continue
                check('Preserving project attachment '+child.name)
                if (child.is_symlink() or not child.resolve().is_relative_to(root)
                    or (child.is_dir() and any(p.is_symlink() or not p.resolve().is_relative_to(root) for p in child.rglob('*')))):
                    raise ValueError('Project attachments contain links; use Save As to a new directory')
                if child.is_dir():shutil.copytree(child,temp/child.name)
                else:shutil.copy2(child,temp/child.name)
        files={p.name:sha256(p) for p in temp.iterdir() if p.is_file() and p.name in managed}
        stamp=datetime.now(timezone.utc).isoformat();created=stamp
        if root.exists():
            try:created=json.loads((root/'project.json').read_text(encoding='utf-8')).get('created_utc',stamp)
            except (OSError,ValueError):pass
        manifest=dict(schema_version=SCHEMA,complete=True,reproducible_structure=bool(snapshot),created_utc=created,saved_utc=stamp,software_commit=meta.get('software_commit'),
            model=result['config'].model,channeling_model=result['config'].channeling_model,methods=list(methods),files=files,arrays=shapes,
            units=dict(reciprocal='Å^-1; crystallographic g=1/d; legacy cycles/angstrom values unchanged',energy='eV',depth='nm',intensity=meta.get('intensity_convention','relative research intensity; model-specific normalization')),
            source_provenance=dict(xmcd_path=result['config'].source if result['config'].model=='xmcd' else None,xmcd_sha256=(meta.get('source_audit',{}).get('sha256') if meta.get('source_audit') else result['config'].source_sha256) if result['config'].model=='xmcd' else None,
                crystal_path=snapshot.get('source') if snapshot else None,crystal_sha256=snapshot.get('sha256') if snapshot else None),
            limitations=result.get('project_warnings',[]),array_convention='method__edge__field maps(qy,qx); method__field spectra(energy); method__amplitudes(depth,beam); explicit labels; no pickle')
        _json(temp/'project.json',manifest);check('Validating saved project');load_project(temp,progress=lambda s:None)
        check('Finalizing complete project')
        if root.exists():_rename_folder(root,backup,cancelled)
        try:_rename_folder(temp,root,cancelled)
        except BaseException:
            if backup.exists():_rename_folder(backup,root)
            raise
        if backup.exists() and backup.resolve().parent==root.parent and backup.name.startswith('.'+root.name+'.previous_'):shutil.rmtree(backup)
        return root
    finally:
        if temp.exists() and temp.resolve().parent==root.parent and temp.name.startswith('.'+root.name+'.saving_'):shutil.rmtree(temp)


def source_status(result):
    cfg=result['config'];status={}
    def entry(path,expected,original):
        try:available=path.is_file();verified=bool(expected and available and sha256(path)==expected)
        except OSError:available=False;verified=False
        return dict(path=str(path),original_path=original,sha256=expected,available=available,verified=verified)
    if cfg.model=='xmcd':
        expected=cfg.source_sha256 or (result['metadata'].get('source_audit') or {}).get('sha256','')
        p=Path(result.get('source_overrides',{}).get('xmcd',cfg.source))
        status['xmcd']=entry(p,expected,cfg.source)
    s=result.get('structure_snapshot')
    if s and s.get('sha256'):
        p=Path(result.get('source_overrides',{}).get('cif',s['source']));status['cif']=entry(p,s['sha256'],s['source'])
    return status


def rerun_reason(result):
    if not result.get('structure_snapshot'):return 'Original numeric crystal snapshot is missing; legacy results are read-only.'
    for name,s in source_status(result).items():
        if not s['verified']:return name+' source unavailable or SHA256 mismatch; locate the original source before rerunning.'
    return ''


def load_project(path,*,legacy=False,cancelled=lambda:False,progress=lambda s:None):
    root=Path(path).resolve();manifest_path=root/'project.json';manifest=None
    def check(stage):
        if cancelled():raise Cancelled()
        progress(stage)
    check('Validating project metadata')
    if manifest_path.exists():
        manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
        if manifest.get('schema_version')!=SCHEMA or manifest.get('complete') is not True:raise ValueError('Unsupported or incomplete project manifest')
        required=set(ARRAY_FILES)|{'metadata.json','comparison_metadata.json','input_parameters.json','structure.json','validity.json'}
        if not required<=set(manifest.get('files',{})):raise ValueError('Incomplete project required-file manifest')
        for name,digest in manifest['files'].items():
            check('Verifying '+name);p=safe_path(root,name)
            if not p.is_file() or sha256(p)!=digest:raise ValueError('Missing or corrupted project file: '+name)
    elif not legacy:raise ValueError('No project.json; use Import Existing Result for read-only Stage B/C exports')
    check('Loading numeric arrays')
    angular=_read_npz(root/'angular_maps.npz');spectra=_read_npz(root/'virtual_detector_eels.npz')
    diffraction=_read_npz(root/'diffraction_pattern.npz') if (root/'diffraction_pattern.npz').exists() else {}
    if manifest:
        for name,values in zip(ARRAY_FILES,(angular,spectra,diffraction)):
            specs=manifest['arrays'][name]
            if set(values)!=set(specs):raise ValueError('Project array names differ from manifest')
            for key,a in values.items():
                if list(a.shape)!=specs[key]['shape'] or str(a.dtype)!=specs[key]['dtype']:raise ValueError('Project array shape/dtype mismatch: '+key)
    meta=json.loads((root/'metadata.json').read_text(encoding='utf-8'))
    cm=json.loads((root/'comparison_metadata.json').read_text(encoding='utf-8')) if (root/'comparison_metadata.json').exists() else {}
    snapshot=json.loads((root/'structure.json').read_text(encoding='utf-8')) if manifest else meta.get('structure_snapshot')
    labels=cm.get('method_labels',meta.get('method_labels',[meta.get('method','bloch')]))
    methods={};q=angular['qx'];qy=angular['qy']
    for name in labels:
        check('Reconstructing saved '+name+' plotting context');mmeta=cm.get('methods',{}).get(name,meta)
        settings=settings_from_dict(mmeta['settings']);cfg=config_from_dict(mmeta['mdff'])
        hkl=np.asarray(mmeta['beam_hkl']);g=np.asarray(mmeta['g']);frame=np.asarray(mmeta['frame']);za=np.asarray(mmeta['za_q'])
        if (hkl.ndim!=2 or hkl.shape[1]!=3 or g.shape!=(len(hkl),2) or len(set(map(tuple,hkl)))!=len(hkl)
            or settings.target not in set(map(tuple,hkl)) or frame.shape!=(3,3) or za.shape!=(2,)
            or not np.isfinite(g).all() or not np.isfinite(za).all() or not np.allclose(frame@frame.T,np.eye(3),atol=1e-12)):
            raise ValueError('Saved diffraction/frame/target plotting context is inconsistent')
        if not {'alpha','pair_reason','correction_reason','limitations'}<=set(mmeta):raise ValueError('Saved method metadata lacks required interpretation/normalization fields')
        fields={edge:{k.split('__')[2]:v for k,v in angular.items() if k.startswith(name+'__'+edge+'__')} for edge in ('L3','L2')}
        if not fields['L3']:
            fields={edge:{k[len(edge)+1:]:v for k,v in angular.items() if k.startswith(edge+'_')} for edge in ('L3','L2')}
        sp={k.split('__',1)[1]:v for k,v in spectra.items() if k.startswith(name+'__')}
        if not sp:sp={k:v for k,v in spectra.items() if k!='method_labels' and '__' not in k}
        C=angular.get(name+'__coherence',angular.get('coherence'))
        amps=diffraction.get(name+'__amplitudes',angular.get('amplitudes'));z=diffraction.get('depth_nm',angular.get('depth_nm'))
        if C is None or amps is None or z is None:raise ValueError('Saved result lacks coherence/depth/complex amplitudes')
        if q.shape!=qy.shape or q.ndim!=2 or amps.shape!=(len(z),len(mmeta['beam_hkl'])) or C.shape!=(amps.shape[1],amps.shape[1]):raise ValueError('Saved diffraction/map dimensions are inconsistent')
        if mmeta.get('angular_maps_calculated',True) is False:
            if any(fields.values()):raise ValueError('Spectra-only metadata conflicts with saved maps')
            fields={}
        for edge,m in fields.items():
            if not {'I_plus','I_minus','I_mag','I_nonmag'}<=set(m) or any(v.shape!=q.shape for v in m.values()):raise ValueError('Missing or inconsistent selected-edge maps')
            if any(not np.isfinite(m[key]).all() for key in ('I_plus','I_minus','I_mag','I_nonmag')):raise ValueError('Saved intrinsic maps must be finite')
            if any(key.startswith('D_') and not np.isfinite(v).any() for key,v in m.items()):raise ValueError('Saved available paired map has no finite support')
        if not {'energy_ev','I_A_plus','I_B_plus','I_A_minus','I_B_minus','D_raw','D_mag','D_nonmag','Sigma_ref'}<=set(sp):raise ValueError('Saved EELS is incomplete')
        e=sp['energy_ev']
        for value in (q,qy,C,amps,z,e):
            if not np.issubdtype(value.dtype,np.number) or not np.isfinite(value).all():raise ValueError('Saved coordinates/coherence/amplitudes/energy must be finite numeric arrays')
        if e.ndim!=1 or len(e)<2 or np.any(np.diff(e)<=0) or np.any(e<=0):raise ValueError('Saved energy axis must be positive and strictly increasing')
        for key in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus','D_raw','D_mag','D_nonmag','Sigma_ref'):
            if sp[key].shape!=e.shape or not np.isfinite(sp[key]).all():raise ValueError('Saved detector spectrum dimensions/values are inconsistent')
        if not np.allclose(C,C.conj().T,rtol=1e-10,atol=1e-12):raise ValueError('Saved coherence is not Hermitian')
        model=plotting_model(mmeta,snapshot)
        weights={k:angular['weight_'+k] for k in ('A','B')}
        if any(w.shape!=q.shape or not np.isfinite(w).all() or np.any(w<0) or np.any(w>1) or not w.any() for w in weights.values()):raise ValueError('Saved fractional detector weights are inconsistent')
        methods[name]=dict(method=name,metadata=mmeta,model=model,settings=settings,config=cfg,maps=fields,spectra=sp,qx=q,qy=qy,weights=weights,coherence=C,depth_nm=z,amplitudes=amps,structure_snapshot=snapshot)
    primary=cm.get('primary_method','bloch' if 'bloch' in methods else labels[0]);result=dict(methods[primary],methods=methods,comparison=cm.get('diagnostics',meta.get('comparison',{})))
    result['metadata']=meta;result['fft']={k[len('fft_full__'):]:v for k,v in diffraction.items() if k.startswith('fft_full__')}
    if result['fft']:result['fft']['summary']=result['comparison'].get('fft',{})
    warnings=list(manifest.get('limitations',[])) if manifest else ['Legacy read-only import: no integrity manifest; only available metadata retained.']
    if not snapshot:warnings.append('Missing numeric crystal snapshot: full reproducibility and Use These Settings/rerun are unavailable.')
    result.update(project_path=str(root),project_manifest=manifest,project_warnings=warnings,structure_snapshot=snapshot,read_only_legacy=manifest is None)
    check('Saved results ready; no physical recalculation')
    return result
