"""Multi-site BW/MS Double Channeling using established Cartesian responses.

Only local preparation and result accumulation live here. Complete-crystal
incoming/outgoing propagation, Coulomb factors, site phases, depth integration
and tensor contraction are supplied by the existing BW/MS backends.
"""
import numpy as np

from .cancellation import check_cancelled
from .double_channeling import (prepare_incoming_bloch, double_channeling_group_responses,
                                intensities_from_response)
from .imported_mdff import proper_frame
from .mdff_providers import load_site_group_provider
from .multisite_spectrum import _empty_group_intensities, _spectrum_result


def _contract_multisite_double(model, sites, plan, qx, qy, *, crystal_to_microscope,
                                   thickness_nm, depth_steps=257, method='numerical',
                                   memory_budget_mib=2048, prepared_incoming=None,
                                   reverse_magnetization=False, cancelled=None,
                                   propagation='bloch',prepared_grid=None,fft_grid=32,
                                   potential_cutoff=2.2,slice_step_nm=.04,systematic_row=False,
                                   execution_workers=None):
    """Mean per selected atom; explicit reversal pairs share each group response.

    The plan is prepared_multisite_spectrum output from preflight. Window
    exclusions never become source extrapolation. Outgoing states are shared
    across ALL active groups at each loss/pixel, including overlapping windows
    with different requested grids. No additional thickness factor is applied:
    the Cartesian responses already contain the complete depth integral.
    """
    check_cancelled(cancelled)
    rotation=proper_frame(crystal_to_microscope)
    crystal=model.elastic.crystal
    positions=np.asarray(crystal.fractional_positions,float)
    if (tuple(crystal.species)!=sites.species or positions.shape!=(len(sites.species),3)
            or not np.isfinite(positions).all()
            or not np.allclose(crystal.lattice_angstrom,np.asarray(sites.cell)@rotation.T,rtol=0,atol=1e-10)):
        raise ValueError('Site groups do not match the complete oriented elastic crystal')
    delta=positions-np.asarray(sites.fractional_positions)
    delta-=np.rint(delta)
    if not np.allclose(delta,0,rtol=0,atol=1e-9):
        raise ValueError('Site groups do not match the ordered elastic crystal positions')
    energy=np.asarray(plan['energy_ev'],float)
    if (energy.ndim!=1 or not len(energy) or not np.isfinite(energy).all() or np.any(energy<=0)
            or np.any(np.diff(energy)<=0) or energy[-1]>=1000*model.elastic.microscope.acceleration_kv):
        raise ValueError('Require ascending positive losses below incident energy')
    if not isinstance(reverse_magnetization,bool):raise ValueError('Global reversal must be a boolean')
    qx,qy=np.asarray(qx,float),np.asarray(qy,float)
    if qx.shape!=qy.shape or not qx.size or not np.isfinite(qx).all() or not np.isfinite(qy).all():
        raise ValueError('Require matching finite nonempty detector query arrays')
    tensors={}
    for group in sites.groups:
        mask=plan['active'][group.group_id]
        if np.any(mask):
            source=load_site_group_provider(group)
            pair=source.tensors(energy[mask],rotation,group.magnetization)
            if reverse_magnetization:pair=pair[::-1]
            tensors[group.group_id]={ie:tuple(t.tensor_angstrom2_per_ev[j] for t in pair)
                                     for j,ie in enumerate(np.flatnonzero(mask))}
    if propagation=='bloch':
        incoming=prepared_incoming if prepared_incoming is not None else prepare_incoming_bloch(
            model.elastic,thickness_nm,depth_steps,cancelled=cancelled)
        batch_size=64
    else:
        if prepared_grid is None or prepared_incoming is None:
            raise ValueError('Prepared complete-crystal FFT grid and incoming fields required')
        incoming=prepared_incoming
        batch_size=32
    groups,weighted=_empty_group_intensities(sites,plan,qx.shape)
    queries=np.column_stack((qx.ravel(),qy.ravel()))
    from .gui.channeling import worker_count,map_detector_batches
    workers=worker_count(len(model.elastic.beams.hkl),propagation) if execution_workers is None else execution_workers
    diagnostics=[]
    for ie,loss in enumerate(energy):
        active=[group for group in sites.groups if plan['active'][group.group_id][ie]]
        diagnostic=dict(energy_ev=float(loss),active_groups=[group.group_id for group in active],
            required_pixels=len(queries) if active else 0,evaluated_pixels=0,response_batches=0,workers=0)
        if not active:
            diagnostics.append(diagnostic)
            continue
        selected_positions={group.group_id:positions[list(group.indices)] for group in active}
        def batches():
            # The shared executor validates the worker count before iterating.
            # Enough tasks to use small pools without exceeding legacy bounds.
            size=min(batch_size,max(1,int(np.ceil(len(queries)/workers))))
            for start in range(0,len(queries),size):
                sl=slice(start,start+size)
                yield sl,queries[sl]
        def response(batch,task_cancelled):
            sl,points=batch
            check_cancelled(task_cancelled)
            details=None
            if propagation=='bloch':
                responses=double_channeling_group_responses(model.elastic,loss,points,thickness_nm,selected_positions,
                    method=method,depth_steps=depth_steps,memory_budget_mib=memory_budget_mib,
                    prepared_incoming=incoming,cancelled=task_cancelled)
            else:
                from .multislice_double_channeling import multislice_double_channeling_group_responses
                responses,details=multislice_double_channeling_group_responses(model.elastic,loss,points,thickness_nm,selected_positions,
                    fft_grid=fft_grid,potential_cutoff=potential_cutoff,systematic_row=systematic_row,row_reduction=systematic_row,
                    depth_steps=depth_steps,slice_step_nm=slice_step_nm,batch_pixels=batch_size,
                    memory_budget_mib=memory_budget_mib,prepared_grid=prepared_grid,prepared_incoming=incoming,cancelled=task_cancelled)
            # Cartesian responses remain local to the worker. Only compact
            # group intensities and diagnostics wait for ordered collection.
            values={}
            for group in active:
                check_cancelled(task_cancelled)
                pair=np.stack([intensities_from_response(responses[group.group_id],tensor)
                               for tensor in tensors[group.group_id][ie]])
                if not np.isfinite(pair).all() or pair.min() < -1e-10*max(float(np.max(abs(pair))),1e-30):
                    raise ValueError('Negative or nonfinite multi-site double-channeling intensity')
                values[group.group_id]=pair
            return sl,values,details
        results=map_detector_batches(response,batches(),workers,propagation,cancelled)
        diagnostic['workers']=min(workers,len(results))
        for sl,values,details in results:
            check_cancelled(cancelled)
            if details is not None:
                for key in ('incoming_norm_error','outgoing_norm_error','incoming_max_excluded_population',
                            'outgoing_max_excluded_population','estimated_working_mib','dense_working_mib'):
                    diagnostic[key]=max(diagnostic.get(key,0.),details[key])
                for key in ('actual_slice_step_nm','substeps_per_depth_interval','depth_steps','fft_samples','row_reduction','memory_admission'):
                    diagnostic[key]=details[key]
            diagnostic['evaluated_pixels']+=len(queries[sl])
            diagnostic['response_batches']+=1
            for group in active:
                for state,label in enumerate(('plus','minus')):
                    value=values[group.group_id][state]
                    groups[group.group_id][label].reshape(len(energy),-1)[ie,sl]=value
                    weighted.reshape(2,len(energy),-1)[state,ie,sl]+=group.multiplicity*value
        diagnostics.append(diagnostic)
    from .gui.generalized_forward import source_for
    for group in sites.groups:
        check_cancelled(cancelled)
        source_for(group.mdff_reference)
    result=_spectrum_result(sites,plan,groups,weighted,rotation,thickness_nm,reverse_magnetization)
    result['metadata'].update(depth_integration=method if propagation=='bloch' else 'trapezoidal',depth_steps=depth_steps,
        outgoing_energy_ev=(1000*model.elastic.microscope.acceleration_kv-energy).tolist(),
        response_normalization='Per-group site mean with depth integral; multiplicity applied once; no extra thickness factor')
    result['diagnostics']=diagnostics
    return result


def contract_multisite_bloch_double(model, sites, plan, qx, qy, **kwargs):
    """BW Double Channeling with the existing analytic/numerical depth methods."""
    return _contract_multisite_double(model,sites,plan,qx,qy,propagation='bloch',**kwargs)


def contract_multisite_ms_double(model, sites, plan, qx, qy, *, prepared_grid, prepared_incoming, **kwargs):
    """MS Double Channeling reusing one prepared complete-crystal FFT context."""
    return _contract_multisite_double(model,sites,plan,qx,qy,propagation='fft-multislice',
        prepared_grid=prepared_grid,prepared_incoming=prepared_incoming,**kwargs)
