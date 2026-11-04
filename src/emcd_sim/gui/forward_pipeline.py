"""One production orchestration for all MDFF providers; accepted kernels unchanged."""
from dataclasses import replace
from time import perf_counter
import numpy as np
from .emcd_forward import _contract, Cancelled
from ..mdff_providers import prepare_provider
from .geometry import elastic_model,geometry
from ..geometry import VirtualDetector
from ..simulation import EMCDSimulation
from ..multislice_reference import coherence_from_amplitudes


def validate_before_resources(structure,settings,cfg,requested=None):
    """Validate declared source/material before geometry or resource estimates."""
    provider=prepare_provider(cfg)
    if not provider.declared:return
    reason=provider.material_reason(structure)
    if reason:raise ValueError(reason)
    if provider.energy_grid(requested)[-1]>=1000*settings.voltage:
        raise ValueError('Energy loss must be below incident electron energy')


def calculate_prepared(structure,settings,cfg,progress,cancelled,*,energy_ev=None,energy_checkpoint=None,execution_policy=None):
    def stage(s):
        if cancelled():raise Cancelled()
        progress(s)
    stage('Validating structure and MDFF')
    provider=prepare_provider(cfg)
    reason=provider.material_reason(structure)
    if reason:raise ValueError(reason)
    energy=provider.energy_grid(energy_ev);elastic=elastic_model(structure,settings,systematic_row=cfg.systematic_row);_,R,hkl,g,_=geometry(structure,settings,systematic_row=cfg.systematic_row)
    if settings.target not in hkl or settings.target==(0,0,0):raise ValueError('Select a nonzero target in the finite diffraction basis')
    memory=64*cfg.grid**2*len(hkl)**2/2**20
    declared=provider.declared
    source=provider.source
    sites=provider.sites(structure)
    if energy[-1]>=1000*settings.voltage:raise ValueError('Energy loss must be below incident electron energy')
    model=EMCDSimulation(elastic,{k:VirtualDetector(tuple(p),cfg.radius) for k,p in zip(('A','B'),cfg.centers)},
        provider.simulation_magnetization)
    # Direct integration requires full physical aperture coverage as well.
    if any(max(abs(np.asarray(p)))+cfg.radius>cfg.halfwidth for p in cfg.centers):raise ValueError('Map halfwidth must fully cover both physical detector apertures')
    from .propagation import propagate, compare_methods, numerical_info
    info=numerical_info(structure,settings,cfg,hkl=hkl,check_memory=False)
    memory=info['dense_working_estimate_mib']
    stage('Generating common +M and -M tensors');ts=provider.tensors(energy,R)
    z=np.linspace(0,settings.thickness,cfg.depth)
    methods={};fft_info={}
    # Finish one solver before preparing the next: cancellation in BW must
    # prevent even the incoming MS propagation from starting in Both mode.
    solvers=('bloch','fft-multislice') if cfg.propagation=='both' else (cfg.propagation,)
    for method in solvers:
        stage('Preparing '+method+' propagation')
        incoming_start=perf_counter()
        waves,method_fft=propagate(elastic,settings,replace(cfg,propagation=method),z,stage,cancelled=cancelled)
        incoming_seconds=perf_counter()-incoming_start
        prepared_incoming=method_fft.pop('_prepared',None)
        if method_fft:fft_info=method_fft
        psi=waves[method]
        stage('Constructing '+method+' depth coherence');C=coherence_from_amplitudes(z,psi)
        stage('Calculating '+method+' EELS and EMCD')
        from .channeling import contract
        checkpoint=(lambda e,data:energy_checkpoint(method,e,data)) if energy_checkpoint is not None else None
        prepared=contract(model,settings,cfg,method,C,energy,ts,stage,cancelled,prepared_incoming,energy_checkpoint=checkpoint,
            execution_workers=execution_policy['effective_workers'][method] if execution_policy else None,
            ionization_sites=sites)
        methods[method]=_contract(structure,settings,cfg,model,R,hkl,g,memory,z,psi,C,energy,ts,stage,cancelled,prepared=prepared)
        methods[method]['method']=method
        methods[method]['metadata'].update(solver=method+' '+cfg.channeling_model+' channeling localized single ionization',numerics=info,
            incoming_propagation_seconds=incoming_seconds,additional_incoming_preparation_seconds=prepared['incoming_preparation_seconds'])
        if declared:methods[method]['metadata'].update(provider_metadata(source,sites,structure,cfg))
        if method=='fft-multislice':methods[method]['metadata']['fft']=fft_info['summary']
    provider.revalidate_source()  # Discard changed declared inputs before publishing results.
    stage('Comparing independent BW/MS propagations')
    comparison=compare_methods(methods,fft_info)
    primary=methods.get('bloch',next(iter(methods.values())))
    # Top-level Stage B arrays remain the primary method; method results do not
    # contain the enclosing collection, avoiding recursive/ambiguous dimensions.
    result=dict(primary,methods=methods,comparison=comparison,fft=fft_info)
    result['metadata']=dict(primary['metadata'],method_labels=list(methods),comparison=comparison)
    from .project_io import structure_snapshot
    result['structure_snapshot']=structure_snapshot(structure)
    for r in methods.values():r['structure_snapshot']=result['structure_snapshot']
    stage('Preparing result visualizations')
    return result



def provider_metadata(source,sites,structure,cfg):
    """Source claims remain distinct from numerical or experimental validation."""
    a=structure.atoms
    result=dict(imported_mdff=source.provenance(),ionization_sites=sites.provenance(),
        mdff_provider=cfg.model,
        unused_legacy_config_fields=['atomic','sigma','radial']+([] if cfg.model=='xmcd' else ['eta','beta']),
        magnetic_structure=dict(model=cfg.magnetic_state,magnetization_crystal=list(cfg.magnetization),
            ase_initial_magmoms=a.get_initial_magnetic_moments().tolist() if a.has('initial_magmoms') else None,
            ase_initial_charges=a.get_initial_charges().tolist() if a.has('initial_charges') else None,
            assumptions='Uniform selected-state tensor; no AFM/SDW; structure moments are consistency annotations'),
        scientific_status='SYNTHETIC TEST ONLY' if source.metadata['status']=='synthetic' else 'RESEARCH / APPROXIMATE',
        reversal=source.metadata['reversal']+'; explicit provider states, fixed detectors; no general conjugation inference',
        detector_evaluation=('Full angular grid at declared selected energies; nonzero fractional-aperture union at other energies' if cfg.angular_maps else 'Only nonzero fractional-aperture support on the unchanged grid; angular maps not calculated'),
        intensity_convention='Declared per-atom relative angstrom^2/eV tensor; mean per selected equivalent site; no absolute cross-section calibration',
        limitations='Dipole; projected neutral IAM; finite ZOLZ; branch-frozen longitudinal transfer; no AFM/SDW or multi-element/site-resolved MDFF; mathematical validity is not quantitative experimental validation')
    if cfg.model=='xmcd':
        result['source_audit']=dict(sha256=source.sha256,bounds=source.energy_ev[[0,-1]].tolist(),
            selected=source.metadata['selected_ev'],provenance=source.metadata['source'],
            selection_origin='Acknowledged provider declaration; no automatic edge-energy shift',audit=None)
    return result


# Documented common entry point. Legacy imports refer to this same callable;
# _calculate remains an admission-test/public-API compatibility hook.
from .emcd_forward import calculate
