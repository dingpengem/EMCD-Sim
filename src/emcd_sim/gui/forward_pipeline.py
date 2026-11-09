"""One production orchestration for all MDFF providers; accepted kernels unchanged."""
from dataclasses import dataclass, replace
from copy import deepcopy
from time import perf_counter
import numpy as np
from .emcd_forward import _contract, Cancelled, ForwardSettings
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


def request_energy_grid(provider,cfg,requested=None):
    """Validate the full source first, then select declared diagnostic samples."""
    energy=provider.energy_grid(requested)
    if requested is None and cfg.energy_scope=='edges' and cfg.selected_edges:
        declared=getattr(cfg,'provider_declaration',{}).get('selected_ev') or dict(L3=cfg.l3,L2=cfg.l2)
        if any(label not in declared or not np.isclose(value,declared[label],rtol=0,atol=1e-9)
               or not np.any(np.isclose(energy,value,rtol=0,atol=1e-9)) for label,value in cfg.selected_edges):
            raise ValueError('Requested samples must match the validated native source edge selections')
        energy=np.unique([value for _,value in cfg.selected_edges])
    return energy


def calculate_prepared(structure,settings,cfg,progress,cancelled,*,energy_ev=None,energy_checkpoint=None,execution_policy=None):
    def stage(s):
        if cancelled():raise Cancelled()
        progress(s)
    stage('Validating structure and MDFF')
    provider=prepare_provider(cfg)
    reason=provider.material_reason(structure)
    if reason:raise ValueError(reason)
    energy=request_energy_grid(provider,cfg,energy_ev);elastic=elastic_model(structure,settings,systematic_row=cfg.systematic_row);_,R,hkl,g,_=geometry(structure,settings,systematic_row=cfg.systematic_row)
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


@dataclass(frozen=True)
class MultiSiteForwardSettings(ForwardSettings):
    """Numerical/detector controls for the programmatic multi-site entry point.

    MDFF declarations belong exclusively to each site's provider reference.
    selected_edges optionally names exact map energies on the requested grid;
    otherwise use source selections present on that grid (or its endpoints).
    Post-edge correction is outside this entry point's current scope.
    """
    model: str = 'multisite'
    source: str = ''
    source_sha256: str = ''
    correction: bool = False
    l3: float = float('nan')
    l2: float = float('nan')
    selected_edges: tuple = ()


def _multisite_detector_data(raw,cfg,energy,qx,qy,weights,support):
    """Use the existing full-grid fractional reduction, including zero pixels."""
    dq2=(qx[0,1]-qx[0,0])**2
    full_weights=np.stack([weights[k].ravel() for k in ('A','B')])
    spectra={};maps={label:{} for label,_ in cfg.selected_edges} if cfg.angular_maps else {}
    for state in ('plus','minus'):
        plane=np.zeros((len(energy),qx.size))
        plane[:,support]=raw[state]
        integrated=np.sum(full_weights[None,:,:]*plane[:,None,:],axis=-1)*dq2
        for di,detector in enumerate(('A','B')):spectra[f'I_{detector}_{state}']=integrated[:,di]
        for label,loss in cfg.selected_edges if cfg.angular_maps else ():
            ie=int(np.flatnonzero(np.isclose(energy,loss,rtol=0,atol=1e-9))[0])
            maps[label]['I_'+state]=plane[ie].reshape(qx.shape).copy()
    for m in maps.values():
        m.update(I_mag=(m['I_plus']-m['I_minus'])/2,I_nonmag=(m['I_plus']+m['I_minus'])/2)
    ap,bp,am,bm=[spectra[k] for k in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus')]
    na,nb,ma,mb=(ap+am)/2,(bp+bm)/2,(ap-am)/2,(bp-bm)/2
    spectra.update(energy_ev=energy,N_A=na,N_B=nb,M_A=ma,M_B=mb,
        D_mag=ma-mb,D_nonmag=na-nb,D_raw=ap-bp,Sigma_ref=na+nb)
    return dict(spectra=spectra,maps=maps,qx=qx,qy=qy,weights=weights)


def calculate_multisite(structure,settings,sites,cfg=None,progress=lambda s:None,
                       cancelled=lambda:False,*,energy_ev=None,energy_windows=None,reverse_magnetization=False):
    """Multi-site Single or Double Channeling with BW or FFT Multislice.

    Supply a common energy_ev covered by ALL providers, or energy_windows
    mapping group IDs to multisite_spectrum.ModeledEdgeWindow declarations.
    Independent window grids are merged; sources cover their own complete
    modeled windows, without extrapolation. Unlisted groups are explicitly
    omitted from the partial spectrum but remain in its denominator.
    Double Channeling requires propagation='bloch' or 'fft-multislice' and
    follows the existing detector-worker policy and memory admission. Incoming
    fields are prepared once and shared with all group responses. Combined BW/MS
    Double Channeling runs remain outside this entry point's current scope.
    Results follow the existing methods/spectra/maps layout. groups contain
    per-group-atom detector means and contribution_weight=n_group/n_selected;
    weighted_sum retains unnormalized selected-atom sums. No cross-source
    rescaling, physical tail prediction, GUI or project persistence is provided.
    """
    from ..cancellation import check_cancelled
    from ..multisite import MultiSiteIonization
    from ..multisite_spectrum import prepare_multisite_spectrum,contract_multisite_spectrum
    from .propagation import resolve_fft_configuration,numerical_info,propagate,compare_methods
    from .memory_budget import reserve_memory
    from .channeling import angular_schedule

    def stage(message):
        check_cancelled(cancelled)
        progress(message)

    stage('Validating multi-site assignments and required MDFF coverage')
    cfg=cfg or MultiSiteForwardSettings()
    if not isinstance(cfg,MultiSiteForwardSettings) or cfg.model!='multisite' or cfg.channeling_model not in ('single','double'):
        raise ValueError('MultiSiteForwardSettings with Single or Double Channeling required')
    double=cfg.channeling_model=='double'
    if double:
        if cfg.propagation not in ('bloch','fft-multislice'):
            raise ValueError('Multi-site Double Channeling requires an individual Bloch-wave or FFT Multislice run')
    if cfg.correction:raise ValueError('Multi-site post-edge correction is not supported')
    if not isinstance(reverse_magnetization,bool):raise ValueError('Global reversal must be a boolean')
    if not isinstance(sites,MultiSiteIonization):raise ValueError('Explicit multi-site assignments required')
    sites.validate_structure(structure)
    if not np.isfinite(settings.voltage) or settings.voltage<=0:
        raise ValueError('Positive incident voltage required')
    # Source identity, species, explicit states, local frames and native axes
    # are checked before geometry/resource work, including for FFT propagation.
    plan=prepare_multisite_spectrum(sites,energy_ev,energy_windows)
    energy=plan['energy_ev']
    if energy[-1]>=1000*settings.voltage:
        raise ValueError('Require energy losses below incident energy')
    if (type(cfg.grid) is not int or not 9<=cfg.grid<=193 or cfg.grid%2!=1
            or type(cfg.depth) is not int or not 2<=cfg.depth<=1025
            or type(cfg.subpixels) is not int or not 4<=cfg.subpixels<=256):
        raise ValueError('Numerical sampling exceeds supported bounds')
    centers=np.asarray(cfg.centers,float)
    if (centers.shape!=(2,2) or not np.isfinite(centers).all()
            or not np.isfinite([cfg.radius,cfg.halfwidth]).all() or min(cfg.radius,cfg.halfwidth)<=0
            or np.any(abs(centers)+cfg.radius>cfg.halfwidth)):
        raise ValueError('Finite detector apertures must be fully covered by the angular grid')
    selections=cfg.selected_edges
    if not selections:
        selections=tuple((group.group_id+':'+label,loss)
            for group in sites.groups for label,loss in plan['sources'][group.group_id]['selected_ev'].items()
            if np.any(np.isclose(energy,loss,rtol=0,atol=1e-9)&plan['active'][group.group_id]))
        if not selections:selections=tuple((f'E={loss:g}eV',float(loss)) for loss in np.unique(energy[[0,-1]]))
    if (len({label for label,_ in selections})!=len(selections)
            or any(not isinstance(label,str) or not label.strip() or not np.isfinite(loss)
                   or not np.any(np.isclose(energy,loss,rtol=0,atol=1e-9)) for label,loss in selections)):
        raise ValueError('Selected map labels must be unique with energies on the common grid')
    cfg=replace(cfg,energy_points=len(energy),selected_edges=tuple(selections))
    cfg=resolve_fft_configuration(structure,settings,cfg)
    elastic=elastic_model(structure,settings,systematic_row=cfg.systematic_row)
    _,rotation,hkl,g,_=geometry(structure,settings,systematic_row=cfg.systematic_row)
    if settings.target==(0,0,0) or settings.target not in hkl:
        raise ValueError('Select a nonzero target in the finite diffraction basis')
    model=EMCDSimulation(elastic,{k:VirtualDetector(tuple(p),cfg.radius) for k,p in zip(('A','B'),centers)},
                         sites.groups[0].magnetization)
    qx,qy,weights,detector_support,_=angular_schedule(model,cfg,energy)
    support=np.ones(qx.size,bool) if cfg.angular_maps else detector_support
    # Account for retained group/total arrays and full-energy query work in
    # addition to the existing conservative propagation/kernel estimates.
    methods_count=2 if cfg.propagation=='both' else 1
    extra=(16*len(energy)*int(support.sum())*(2*len(sites.groups)+12)
           +576*len(energy)*len(sites.groups)
           +methods_count*64*len(selections)*qx.size*(len(sites.groups)+2)
           +methods_count*256*len(energy)*(len(sites.groups)+2))/2**20
    # Include retained multi-site arrays BEFORE worker admission, so the
    # existing automatic memory limit sees the complete calculation footprint.
    info=numerical_info(structure,settings,cfg,hkl=hkl,ionization_sites=sites,
        additional_retained_working_mib=extra)
    info['multisite_additional_working_mib']=extra
    working=info['estimated_working_mib']
    z=np.linspace(0,settings.thickness,cfg.depth)
    methods={};fft_info={}
    reserved=info['retained_results_working_mib'] if double else working
    with reserve_memory(reserved,cfg.memory_budget_mib,dense_mib=info['dense_working_estimate_mib']) as admission:
        for method in ('bloch','fft-multislice') if cfg.propagation=='both' else (cfg.propagation,):
            stage('Preparing '+method+' complete-crystal propagation')
            start=perf_counter()
            incoming=None
            if double and method=='bloch':
                from ..double_channeling import prepare_incoming_bloch
                incoming=prepare_incoming_bloch(elastic,settings.thickness,cfg.depth,cancelled=cancelled)
                waves,method_fft={method:incoming.fields},{}
            else:
                waves,method_fft=propagate(elastic,settings,replace(cfg,propagation=method),z,stage,cancelled=cancelled)
            incoming_seconds=perf_counter()-start
            prepared_fft=method_fft.pop('_prepared',None)
            if not double:prepared_fft=None  # Single needs only the retained incoming amplitudes.
            if method_fft:fft_info=method_fft
            psi=waves[method]
            coherence=coherence_from_amplitudes(z,psi)
            stage('Contracting '+method+' multi-site '+cfg.channeling_model.title()+' Channeling')
            if double and method=='bloch':
                from ..multisite_double_channeling import contract_multisite_bloch_double
                raw=contract_multisite_bloch_double(model,sites,plan,qx.ravel()[support],qy.ravel()[support],
                    crystal_to_microscope=rotation,thickness_nm=settings.thickness,depth_steps=cfg.depth,
                    method='analytic' if cfg.systematic_row else 'numerical',memory_budget_mib=cfg.memory_budget_mib,
                    prepared_incoming=incoming,reverse_magnetization=reverse_magnetization,cancelled=cancelled,
                    execution_workers=info['execution']['effective_workers'][method])
            elif double:
                from ..multisite_double_channeling import contract_multisite_ms_double
                grid,fields=prepared_fft
                raw=contract_multisite_ms_double(model,sites,plan,qx.ravel()[support],qy.ravel()[support],
                    crystal_to_microscope=rotation,thickness_nm=settings.thickness,depth_steps=cfg.depth,
                    fft_grid=cfg.fft_grid,potential_cutoff=settings.potential_cutoff,slice_step_nm=cfg.slice_step,
                    systematic_row=cfg.systematic_row,memory_budget_mib=cfg.memory_budget_mib,
                    prepared_grid=grid,prepared_incoming=fields,reverse_magnetization=reverse_magnetization,cancelled=cancelled,
                    execution_workers=info['execution']['effective_workers'][method])
            else:
                raw=contract_multisite_spectrum(model,structure,sites,coherence,plan,qx.ravel()[support],qy.ravel()[support],
                    crystal_to_microscope=rotation,thickness_nm=settings.thickness,
                    reverse_magnetization=reverse_magnetization,cancelled=cancelled)
            data=_multisite_detector_data(raw['total'],cfg,energy,qx,qy,weights,support)
            data.update(angular_evaluation_policy='full_grid_all_energies' if cfg.angular_maps else 'fractional_aperture_support',diagnostics=raw.get('diagnostics',[]))
            result=_contract(structure,settings,cfg,model,rotation,hkl,g,info['dense_working_estimate_mib'],z,psi,
                             coherence,energy,(),stage,cancelled,prepared=data)
            result.update(method=method,groups={},weighted_sum=_multisite_detector_data(raw['weighted_sum'],cfg,energy,qx,qy,weights,support))
            for group in sites.groups:
                stage('Integrating '+group.group_id+' fractional detector intensities')
                group_raw=raw['groups'][group.group_id]
                entry=_multisite_detector_data(group_raw,cfg,energy,qx,qy,weights,support)
                entry['metadata']={k:v for k,v in group_raw.items() if k not in ('plus','minus')}
                entry['metadata']['contribution_weight']=group.multiplicity/raw['metadata']['selected_atom_count']
                result['groups'][group.group_id]=entry
            meta=result['metadata']
            for key in ('magnetization_crystal','magnetization_local'):meta.pop(key,None)
            meta.update(multisite=raw['metadata'],mdff={key:entry['metadata'] for key,entry in result['groups'].items()},
                mdff_provider='multisite',
                scientific_status='SYNTHETIC TEST ONLY' if all(source['status']=='synthetic' for source in plan['sources'].values()) else 'RESEARCH / APPROXIMATE',
                numerics=info,execution=info['execution'],memory_admission=admission,
                solver=method+' '+cfg.channeling_model.title()+' Channeling; independent localized site-group intensities',
                incoming_propagation_seconds=incoming_seconds,
                intensity_convention=raw['metadata']['intensity_convention'],
                spectral_coverage=plan['metadata']['coverage_mode'],
                spectrum_kind='modeled_partial_core_edge_spectrum',
                reversal='Explicit provider pairs exchanged together; fixed elastic state, detectors and frames',
                detector_evaluation='Full grid at all energies' if cfg.angular_maps else 'Nonzero fractional-aperture support',
                limitations='Projected neutral IAM; finite ZOLZ; '+(method+' Double Channeling' if double else 'Single Channeling')+'; modeled partial core-edge spectrum; omitted channels/tails are not physical zeros; no absolute or cross-element calibration')
            result['weighted_sum']['metadata']=dict(normalization='sum_over_selected_atoms',spectrum_kind='modeled_partial_core_edge_spectrum')
            if method=='fft-multislice':meta['fft']=fft_info['summary']
            methods[method]=result
            del raw
        # Revalidate every source after both methods and all postprocessing.
        from .generalized_forward import source_for
        for group in sites.groups:
            stage('Revalidating '+group.group_id+' MDFF source')
            source_for(group.mdff_reference)
        comparison=compare_methods(methods,fft_info)
        primary=methods.get('bloch',next(iter(methods.values())))
        result=dict(primary,methods=methods,comparison=comparison,fft=fft_info)
        result['metadata']=dict(primary['metadata'],method_labels=list(methods),comparison=comparison)
        from .project_io import structure_snapshot
        snapshot=structure_snapshot(structure)
        result['structure_snapshot']=snapshot
        for method_result in methods.values():method_result['structure_snapshot']=snapshot
        # Retain declarations for project persistence; no providers are inferred
        # from the already-contracted spectra during restoration.
        result['configuration']=deepcopy(dict(structure=structure,settings=settings,config=cfg,site_groups=sites,
            magnetization_mode='local',reverse_magnetization=reverse_magnetization,
            energy_ev=energy,energy_windows=energy_windows))
        for method_result in methods.values():method_result['configuration']=result['configuration']
        check_cancelled(cancelled)
        return result


# Documented common entry point. Legacy imports refer to this same callable;
# _calculate remains an admission-test/public-API compatibility hook.
from .emcd_forward import calculate
