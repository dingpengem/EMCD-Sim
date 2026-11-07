"""Multi-site BW Double Channeling using the established Cartesian response.

Only local preparation and result accumulation live here. Complete-crystal
incoming/outgoing propagation, Coulomb factors, site phases, depth integration
and tensor contraction are supplied by double_channeling.py.
"""
import numpy as np

from .cancellation import check_cancelled
from .double_channeling import (prepare_incoming_bloch, double_channeling_group_responses,
                                intensities_from_response)
from .imported_mdff import proper_frame
from .mdff_providers import load_site_group_provider
from .multisite_spectrum import _empty_group_intensities, _spectrum_result


def contract_multisite_bloch_double(model, sites, plan, qx, qy, *, crystal_to_microscope,
                                   thickness_nm, depth_steps=257, method='numerical',
                                   memory_budget_mib=2048, prepared_incoming=None,
                                   reverse_magnetization=False, cancelled=None):
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
    incoming=prepared_incoming if prepared_incoming is not None else prepare_incoming_bloch(
        model.elastic,thickness_nm,depth_steps,cancelled=cancelled)
    groups,weighted=_empty_group_intensities(sites,plan,qx.shape)
    queries=np.column_stack((qx.ravel(),qy.ravel()))
    for ie,loss in enumerate(energy):
        active=[group for group in sites.groups if plan['active'][group.group_id][ie]]
        if not active:continue
        selected_positions={group.group_id:positions[list(group.indices)] for group in active}
        for start in range(0,len(queries),64):
            check_cancelled(cancelled)
            sl=slice(start,start+64)
            responses=double_channeling_group_responses(model.elastic,loss,queries[sl],thickness_nm,selected_positions,
                method=method,depth_steps=depth_steps,memory_budget_mib=memory_budget_mib,
                prepared_incoming=incoming,cancelled=cancelled)
            for group in active:
                for state,label in enumerate(('plus','minus')):
                    values=intensities_from_response(responses[group.group_id],tensors[group.group_id][ie][state])
                    if not np.isfinite(values).all() or values.min() < -1e-10*max(float(np.max(abs(values))),1e-30):
                        raise ValueError('Negative or nonfinite multi-site double-channeling intensity')
                    groups[group.group_id][label].reshape(len(energy),-1)[ie,sl]=values
                    weighted.reshape(2,len(energy),-1)[state,ie,sl]+=group.multiplicity*values
    from .gui.generalized_forward import source_for
    for group in sites.groups:
        check_cancelled(cancelled)
        source_for(group.mdff_reference)
    result=_spectrum_result(sites,plan,groups,weighted,rotation,thickness_nm,reverse_magnetization)
    result['metadata'].update(depth_integration=method,depth_steps=depth_steps,
        outgoing_energy_ev=(1000*model.elastic.microscope.acceleration_kv-energy).tolist(),
        response_normalization='Per-group site mean with depth integral; multiplicity applied once; no extra thickness factor')
    return result
