"""Opt-in imported-tensor orchestration; historical Ni forward adapter is unchanged."""
from dataclasses import dataclass,replace
from time import perf_counter
import numpy as np
from . import emcd_forward as ni
from .geometry import elastic_model,geometry
from ..geometry import VirtualDetector
from ..simulation import EMCDSimulation
from ..ionization_sites import IonizationSites
from ..imported_mdff import ImportedMDFF
from ..multislice_reference import coherence_from_amplitudes
from ..cancellation import check_cancelled


@dataclass(frozen=True)
class ImportedSettings(ni.ForwardSettings):
    model: str='imported'
    source: str=''
    ionizing_element: str=''
    core_edge: str='L2,3'
    magnetic_state: str=''
    site_indices: tuple|None=None
    l3: float=float('nan')
    l2: float=float('nan')
    correction: bool=False


def settings_for_source(path,**kwargs):
    source=ImportedMDFF.load(path);d=source.metadata
    fields=dict(source=source.path,source_sha256=source.sha256,ionizing_element=d['element'],core_edge=d['edge'],
        magnetic_state=d['magnetic_state'],magnetization=tuple(d['magnetization_crystal']),axis_declared=True,
        l3=d['selected_ev']['L3'],l2=d['selected_ev']['L2'])
    fields.update(kwargs)
    return ImportedSettings(**fields)


def source_for(cfg):
    source=ImportedMDFF.load(cfg.source,cfg.source_sha256)
    d=source.metadata
    if not cfg.source_sha256:raise ValueError('Validate the imported MDFF checksum before calculation')
    if (cfg.ionizing_element!=d['element'] or cfg.core_edge!=d['edge'] or cfg.magnetic_state!=d['magnetic_state']):
        raise ValueError('Selected ionizing element, edge or magnetic state differs from imported source')
    if not cfg.axis_declared:raise ValueError('Explicitly acknowledge the imported tensor frame, magnetic axis and reversal assumptions')
    if not np.allclose([cfg.l3,cfg.l2],[d['selected_ev'][k] for k in ('L3','L2')],rtol=0,atol=1e-9):
        raise ValueError('Imported selections must match declared source; no inherited Ni edge calibration')
    source.tensors(np.array([cfg.l3,cfg.l2]),np.eye(3),cfg.magnetization)
    return source


def material_reason(structure,cfg=None):
    if cfg is None or cfg.model!='imported':return ni.material_reason(structure)
    try:
        source_for(cfg)
        IonizationSites.from_structure(structure,cfg.ionizing_element,cfg.site_indices)
        if structure.elastic_reason:return structure.elastic_reason
    except (ValueError,OSError,TypeError,KeyError) as exc:return str(exc)
    return ''


def energy_grid(cfg,requested=None):
    if cfg.model!='imported':return ni.energy_grid(cfg,requested)
    source=source_for(cfg);lo,hi=source.energy_ev[[0,-1]]
    if not np.allclose([cfg.l3,cfg.l2],[source.metadata['selected_ev'][k] for k in ('L3','L2')],rtol=0,atol=1e-9):
        raise ValueError('Imported L3/L2 selections must match the declared source; no inherited Ni edge calibration')
    if cfg.channeling_model not in ('single','double') or cfg.energy_scope not in ('full','edges'):raise ValueError('Unsupported imported tensor propagation/energy scope')
    if not 9<=cfg.energy_points<=501 or not 9<=cfg.grid<=193 or cfg.grid%2!=1 or not 2<=cfg.depth<=1025 or not 4<=cfg.subpixels<=256:raise ValueError('Numerical sampling exceeds supported bounds')
    if not np.isfinite([cfg.halfwidth,cfg.radius,*np.ravel(cfg.centers),*cfg.window]).all() or min(cfg.halfwidth,cfg.radius)<=0:raise ValueError('Invalid detector/grid controls')
    if requested is None:
        e=np.array([cfg.l3,cfg.l2]) if cfg.energy_scope=='edges' else np.unique(np.r_[np.linspace(lo,hi,cfg.energy_points),cfg.l3,cfg.l2])
    else:e=np.asarray(requested,float)
    if e.ndim!=1 or len(e)<2 or not np.isfinite(e).all() or np.any(np.diff(e)<=0) or e[0]<lo or e[-1]>hi:raise ValueError('No imported MDFF energy extrapolation')
    if not all(np.any(np.isclose(e,v,rtol=0,atol=1e-9)) for v in (cfg.l3,cfg.l2)):raise ValueError('Requested grid must include declared L3/L2 energies')
    return e.copy()


def tensors(cfg,energy,R):
    return source_for(cfg).tensors(energy,R,cfg.magnetization) if cfg.model=='imported' else ni.tensors(cfg,energy,R)


def calculate(structure,settings,cfg,progress=lambda s:None,cancelled=lambda:False,*,energy_ev=None,energy_checkpoint=None,execution_policy=None):
    if cfg.model!='imported':
        return ni.calculate(structure,settings,cfg,progress,cancelled,energy_ev=energy_ev,energy_checkpoint=energy_checkpoint,execution_policy=execution_policy)
    check_cancelled(cancelled)
    reason=material_reason(structure,cfg)
    if reason:raise ValueError(reason)
    source=source_for(cfg);energy=energy_grid(cfg,energy_ev)
    sites=IonizationSites.from_structure(structure,cfg.ionizing_element,cfg.site_indices)
    from .propagation import resolve_fft_configuration,numerical_info,propagate,compare_methods
    from .memory_budget import reserve_memory
    from .channeling import contract
    from .project_io import structure_snapshot
    cfg=resolve_fft_configuration(structure,settings,cfg)
    info=numerical_info(structure,settings,cfg)
    if execution_policy is not None and execution_policy['effective_workers']!=info['execution']['effective_workers']:
        raise ValueError('Resources changed since preflight; review worker counts again')
    execution_policy=info['execution']
    reserved=info['retained_results_working_mib'] if cfg.channeling_model=='double' else info['estimated_working_mib']
    def stage(text):check_cancelled(cancelled);progress(text)
    with reserve_memory(reserved,cfg.memory_budget_mib,dense_mib=info['dense_working_estimate_mib']) as admission:
        stage('Validating imported tensor and equivalent localized events')
        elastic=elastic_model(structure,settings,systematic_row=cfg.systematic_row)
        _,R,hkl,g,_=geometry(structure,settings,systematic_row=cfg.systematic_row)
        if settings.target not in hkl or settings.target==(0,0,0):raise ValueError('Select a nonzero target in the finite diffraction basis')
        if any(max(abs(np.asarray(p)))+cfg.radius>cfg.halfwidth for p in cfg.centers):raise ValueError('Grid must fully cover physical detector apertures')
        model=EMCDSimulation(elastic,{k:VirtualDetector(tuple(p),cfg.radius) for k,p in zip(('A','B'),cfg.centers)},cfg.magnetization)
        ts=source.tensors(energy,R,cfg.magnetization);z=np.linspace(0,settings.thickness,cfg.depth)
        methods={};fft_info={}
        for method in (('bloch','fft-multislice') if cfg.propagation=='both' else (cfg.propagation,)):
            stage('Preparing '+method+' imported tensor calculation');start=perf_counter()
            waves,extra=propagate(elastic,settings,replace(cfg,propagation=method),z,stage,cancelled=cancelled)
            elapsed=perf_counter()-start;incoming=extra.pop('_prepared',None)
            if extra:fft_info=extra
            psi=waves[method];C=coherence_from_amplitudes(z,psi)
            checkpoint=(lambda e,data:energy_checkpoint(method,e,data)) if energy_checkpoint is not None else None
            prepared=contract(model,settings,cfg,method,C,energy,ts,stage,cancelled,incoming,energy_checkpoint=checkpoint,
                execution_workers=execution_policy['effective_workers'][method],ionization_sites=sites)
            r=ni._contract(structure,settings,cfg,model,R,hkl,g,info['dense_working_estimate_mib'],z,psi,C,energy,ts,stage,cancelled,prepared=prepared)
            r['method']=method
            r['metadata'].update(imported_mdff=source.provenance(),ionization_sites=sites.provenance(),
                unused_legacy_config_fields=['atomic','sigma','radial','eta','beta'],
                scientific_status='SYNTHETIC TEST ONLY' if source.metadata['status']=='synthetic' else 'RESEARCH / APPROXIMATE',
                reversal=source.metadata['reversal']+'; independently supplied states, fixed detectors; no conjugation inference',
                intensity_convention='Declared per-atom relative angstrom^2/eV tensor; mean per selected equivalent site; no absolute cross-section calibration',
                limitations='Dipole; projected neutral IAM; finite ZOLZ; branch-frozen longitudinal transfer; no AFM/SDW or multi-element/site-resolved MDFF; imported/synthetic is not quantitative experimental validation',
                solver=method+' '+cfg.channeling_model+' channeling localized single ionization',numerics=info,
                execution=execution_policy,memory_admission=admission,incoming_propagation_seconds=elapsed,
                additional_incoming_preparation_seconds=prepared['incoming_preparation_seconds'])
            if method=='fft-multislice':r['metadata']['fft']=fft_info['summary']
            methods[method]=r
        # Discard results if the external source changed while workers ran.
        ImportedMDFF.load(cfg.source,source.sha256);check_cancelled(cancelled)
        comparison=compare_methods(methods,fft_info);primary=methods.get('bloch',next(iter(methods.values())))
        result=dict(primary,methods=methods,comparison=comparison,fft=fft_info)
        result['metadata']=dict(primary['metadata'],method_labels=list(methods),comparison=comparison)
        result['structure_snapshot']=structure_snapshot(structure)
        for r in methods.values():r['structure_snapshot']=result['structure_snapshot']
        return result
