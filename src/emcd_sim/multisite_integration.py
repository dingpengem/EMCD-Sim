"""Bounded energy/support scheduling for multisite detector spectra.

integrate_single_channeling_spectrum and integrate_double_channeling_spectrum
share already prepared complete-crystal waves across material groups. The
former contracts incoming coherence; the latter delegates depth-integrated
responses to the BW/MS kernels. Both reduce the original fractional aperture
grid, retain selected maps, and preserve group/selected-atom normalization.
This is application orchestration, with no widgets or alternate physics.
"""
from dataclasses import replace
from time import perf_counter
import numpy as np
from .detector_signals import integrate_detector_block


def contract_single_channeling_block(model,sites,coherence,plan,selection,points,prepared,rotation,thickness_nm,reverse,cancelled):
    """One bounded support/energy cohort using already validated group inputs."""
    from .multisite_spectrum import _empty_group_intensities,_spectrum_result
    from .multisite_single_channeling import _group_intensity_pair
    energy=plan['energy_ev'][selection]
    block_plan=dict(plan,energy_ev=energy)
    groups,weighted=_empty_group_intensities(sites,block_plan,points[0].shape)
    calls=0
    for group in sites.groups:
        if group.group_id not in prepared:continue
        phase,pair,index=prepared[group.group_id]
        active=index[selection]>=0
        if not active.any():continue
        tensors=[tensor[index[selection][active]] for tensor in pair]
        raw=_group_intensity_pair(model,coherence,phase,energy[active],tensors[::-1] if reverse else tensors,
                                  *points,thickness_nm,cancelled)
        for state,label in enumerate(('plus','minus')):
            groups[group.group_id][label][active]=raw[state]
            weighted[state,active]+=group.multiplicity*raw[state]
        calls+=2*int(active.sum())*((len(points[0])+63)//64)
    result=_spectrum_result(sites,plan,groups,weighted,rotation,thickness_nm,reverse)
    result['kernel_calls']=calls
    return result


def integrate_single_channeling_spectrum(model,structure,sites,coherence,plan,cfg,qx,qy,weights,detector_support,
                                    rotation,thickness_nm,reverse_magnetization,stage,cancelled):
    """Reduce bounded raw blocks; retain all detector samples and selected maps.

    The existing localized-event contraction still evaluates every requested
    energy/pixel. Full energy-by-pixel group/cohort/parity arrays are temporary,
    not final results, and must not survive into the next block.
    """
    from emcd_sim.propagation import MULTISITE_ENERGY_BATCH
    from .mdff_providers import prepare_site_group_providers
    from .multisite import MultiSiteIonization
    from .ionization_sites import single_site_phase_matrix
    energy=plan['energy_ev']
    from .multisite_single_channeling import _validate_multisite_inputs
    rotation,positions,_,_,_,coherence=_validate_multisite_inputs(model,sites,coherence,energy,qx,qy,
        rotation,thickness_nm,reverse_magnetization,cancelled)
    # The kernel only reads these elastic inputs. Freeze this request's basis
    # locally instead of rebuilding reciprocal vectors for every pixel batch.
    # qz and all Coulomb factors remain energy-dependent inside the kernel.
    from types import SimpleNamespace
    kernel_model=SimpleNamespace(elastic=SimpleNamespace(microscope=model.elastic.microscope,
        reciprocal_vectors_xy=model.elastic.reciprocal_vectors_xy))
    result=dict(total={},weighted_sum={},groups={group.group_id:{} for group in sites.groups})
    start_preparation=perf_counter();prepared={}
    for group in sites.groups:
        active=plan['active'][group.group_id]
        if not active.any():continue
        _,pair,_=prepare_site_group_providers(MultiSiteIonization(structure,[group]),energy[active],rotation)[0]
        phase=single_site_phase_matrix(model.elastic.beams.hkl,positions[list(group.indices)])
        index=np.full(len(energy),-1,dtype=int);index[active]=np.arange(int(active.sum()))
        prepared[group.group_id]=(phase,[t.tensor_angstrom2_per_ev for t in pair],index)
    result['preparation_seconds']=perf_counter()-start_preparation
    full=np.zeros(len(energy),bool)
    if cfg.angular_maps:
        if cfg.angular_evaluation=='all':full[:]=True
        else:
            for _,loss in cfg.selected_edges:full|=np.isclose(energy,loss,rtol=0,atol=1e-9)
    supports={False:detector_support,True:np.ones(qx.size,bool)}
    points={key:(qx.ravel()[mask],qy.ravel()[mask]) for key,mask in supports.items()}
    diagnostics=[];contraction_seconds=0.;reduction_seconds=0.

    def integrate(target,part,block_cfg,block_energy,selection):
        reduced=integrate_detector_block(part,block_cfg,block_energy,qx,qy,weights,support)
        if not target:
            target.update(spectra={key:np.empty(len(energy)) for key in reduced['spectra']},
                          maps={},qx=qx,qy=qy,weights=weights)
        for key,values in reduced['spectra'].items():target['spectra'][key][selection]=values
        target['maps'].update(reduced['maps'])

    for start in range(0,len(energy),MULTISITE_ENERGY_BATCH):
        stage(f'Single Channeling energies {start+1}–{min(start+MULTISITE_ENERGY_BATCH,len(energy))}/{len(energy)}')
        candidates=np.arange(start,min(start+MULTISITE_ENERGY_BATCH,len(energy)))
        for is_full in (False,True):
            selection=candidates[full[candidates]==is_full]
            if not len(selection):continue
            block_energy=energy[selection];support=supports[is_full]
            block_cfg=replace(cfg,angular_maps=cfg.angular_maps and is_full,
                selected_edges=tuple((label,loss) for label,loss in cfg.selected_edges
                    if np.any(np.isclose(block_energy,loss,rtol=0,atol=1e-9))))
            before=perf_counter()
            raw=contract_single_channeling_block(kernel_model,sites,coherence,plan,selection,points[is_full],prepared,
                rotation,thickness_nm,reverse_magnetization,cancelled)
            elapsed=perf_counter()-before;contraction_seconds+=elapsed
            diagnostics.append(dict(energy_indices=selection.tolist(),energy_count=len(selection),full_field=is_full,
                required_pixels=int(support.sum()),evaluated_pixels=int(support.sum())*len(selection),
                kernel_calls=raw['kernel_calls'],mdff_contraction_seconds=elapsed))
            before=perf_counter()
            integrate(result['total'],raw['total'],block_cfg,block_energy,selection)
            integrate(result['weighted_sum'],raw['weighted_sum'],block_cfg,block_energy,selection)
            for group in sites.groups:
                entry=result['groups'][group.group_id]
                integrate(entry,raw['groups'][group.group_id],block_cfg,block_energy,selection)
                entry['metadata']={key:value for key,value in raw['groups'][group.group_id].items()
                                   if key not in ('plus','minus')}
            reduction_seconds+=perf_counter()-before
            result['metadata']=raw['metadata']
            del raw
    result['diagnostics']=diagnostics
    result['timings']=dict(group_preparation_seconds=result.pop('preparation_seconds'),
        mdff_contraction_seconds=contraction_seconds,detector_reduction_seconds=reduction_seconds)
    return result


def integrate_double_channeling_spectrum(model,sites,plan,cfg,qx,qy,weights,detector_support,
                                   rotation,thickness_nm,incoming,workers,reverse_magnetization,stage,cancelled,
                                   *,propagation='bloch',prepared_fft=None,potential_cutoff=None):
    """Schedule existing BW/MS DC responses on selected maps or detector support.

    Each energy is evaluated once; complete-crystal incoming fields are shared
    across blocks. Reduction retains original fractional weights and group means.
    """
    from .multisite_double_channeling import contract_multisite_bloch_double,contract_multisite_ms_double
    from emcd_sim.propagation import MULTISITE_ENERGY_BATCH
    energy=plan['energy_ev'];full=np.zeros(len(energy),bool)
    if cfg.angular_maps:
        for _,loss in cfg.selected_edges:full|=np.isclose(energy,loss,rtol=0,atol=1e-9)
    result=dict(total={},weighted_sum={},groups={g.group_id:{} for g in sites.groups},diagnostics=[])
    contraction_seconds=0.;reduction_seconds=0.
    tensor_preparation_seconds=0.
    def integrate(target,part,block_cfg,block_energy,selection,support):
        reduced=integrate_detector_block(part,block_cfg,block_energy,qx,qy,weights,support)
        if not target:target.update(spectra={key:np.empty(len(energy)) for key in reduced['spectra']},maps={},qx=qx,qy=qy,weights=weights)
        for key,value in reduced['spectra'].items():target['spectra'][key][selection]=value
        target['maps'].update(reduced['maps'])
    for is_full in (False,True):
        candidates=np.flatnonzero(full==is_full);support=np.ones(qx.size,bool) if is_full else detector_support
        for start in range(0,len(candidates),MULTISITE_ENERGY_BATCH):
            selection=candidates[start:start+MULTISITE_ENERGY_BATCH];block_energy=energy[selection]
            stage(f'{propagation} Double Channeling: {"selected maps" if is_full else "detector support"}; energies {start+1}–{start+len(selection)}/{len(candidates)}, {int(support.sum())} pixels')
            block_plan=dict(plan,energy_ev=block_energy,active={gid:mask[selection] for gid,mask in plan['active'].items()})
            block_cfg=replace(cfg,angular_maps=cfg.angular_maps and is_full,selected_edges=tuple((label,loss) for label,loss in cfg.selected_edges if np.any(np.isclose(block_energy,loss,rtol=0,atol=1e-9))))
            before=perf_counter()
            common=dict(crystal_to_microscope=rotation,thickness_nm=thickness_nm,depth_steps=cfg.depth,
                memory_budget_mib=cfg.calculation_memory_budget_mib,reverse_magnetization=reverse_magnetization,
                cancelled=cancelled,execution_workers=workers,progress=stage)
            if propagation=='bloch':
                raw=contract_multisite_bloch_double(model,sites,block_plan,qx.ravel()[support],qy.ravel()[support],
                    method='analytic' if cfg.systematic_row else 'numerical',prepared_incoming=incoming,**common)
            else:
                grid,fields=prepared_fft
                raw=contract_multisite_ms_double(model,sites,block_plan,qx.ravel()[support],qy.ravel()[support],
                    prepared_grid=grid,prepared_incoming=fields,fft_grid=cfg.fft_grid,
                    potential_cutoff=potential_cutoff,
                    slice_step_nm=cfg.slice_step,systematic_row=cfg.systematic_row,**common)
            contraction_seconds+=perf_counter()-before;before=perf_counter()
            tensor_preparation_seconds+=raw.get('timings',{}).get('tensor_preparation_seconds',0.)
            integrate(result['total'],raw['total'],block_cfg,block_energy,selection,support)
            integrate(result['weighted_sum'],raw['weighted_sum'],block_cfg,block_energy,selection,support)
            for group in sites.groups:
                entry=result['groups'][group.group_id];part=raw['groups'][group.group_id]
                integrate(entry,part,block_cfg,block_energy,selection,support)
                entry['metadata']={key:value for key,value in part.items() if key not in ('plus','minus')}
            del part
            for i,diagnostic in enumerate(raw['diagnostics']):
                diagnostic.update(energy_index=int(selection[i]),full_field=is_full,
                    outgoing_energy_ev=float(1000*model.elastic.microscope.acceleration_kv-block_energy[i]))
                result['diagnostics'].append(diagnostic)
            result['metadata']=raw['metadata'];reduction_seconds+=perf_counter()-before
            del raw
    result['diagnostics'].sort(key=lambda row:row['energy_index'])
    result['metadata']['outgoing_energy_ev']=(1000*model.elastic.microscope.acceleration_kv-energy).tolist()
    result['timings']=dict(outgoing_response_and_mdff_seconds=contraction_seconds,detector_reduction_seconds=reduction_seconds,
                           tensor_preparation_seconds=tensor_preparation_seconds)
    return result
