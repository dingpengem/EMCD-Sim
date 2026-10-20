"""GUI adapters to the existing channeling kernels; no scattering model here."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import sys,threading
from time import perf_counter
import numpy as np
from ..double_channeling import double_channeling_response, intensities_from_response,prepare_incoming_bloch
from ..multislice_double_channeling import ProjectedNiFFT, incident_fields, multislice_double_channeling_response
from ..ni_017_geometry import Ni017Geometry
from ..single_channeling_tensor import _tensor_angular_maps, fcc_site_phase_matrix


def fft_geometry(elastic,settings,cfg):
    return ProjectedNiFFT.build(elastic,grid_points=cfg.fft_grid,potential_cutoff=settings.potential_cutoff,
        systematic_row=cfg.systematic_row,row_reduction=cfg.systematic_row,
        projected_geometry=Ni017Geometry() if settings.zone==(0,1,7) else None)


_windows_bw_lock=threading.Lock()


@contextmanager
def bw_executor_guard(method,cancelled):
    """Serialize Windows BW detector executors, including independent requests.

    The Windows NumPy OpenBLAS runtime can access-violate when concurrent
    outgoing eigh calls use its native thread pool. Do not change global BLAS
    settings or scientific inputs. Waiting for another request is cancellable.
    """
    if method!='bloch' or sys.platform!='win32':
        yield;return
    from ..cancellation import check_cancelled
    while not _windows_bw_lock.acquire(timeout=.05):check_cancelled(cancelled)
    try:
        check_cancelled(cancelled)
        yield
    finally:_windows_bw_lock.release()


def worker_count(n,method):
    if method=='bloch' and sys.platform=='win32':return 1
    dense=80*n**4/2**20
    return min(4,max(1,int(1200/(dense+40)))) if method=='bloch' else 4


EVALUATION_POLICY='full_at_selected_edges_detector_only_elsewhere'


def angular_schedule(model,cfg,energy):
    """Two fixed supports on the original q grid; weights are computed once."""
    q=np.linspace(-cfg.halfwidth,cfg.halfwidth,cfg.grid);qx,qy=np.meshgrid(q,q,indexing='xy')
    weights={k:d.integration_weights(qx,qy,mode='fractional',subpixels=cfg.subpixels) for k,d in model.detectors.items()}
    detector_support=np.logical_or.reduce([weights[k].ravel()>0 for k in ('A','B')])
    if not detector_support.any():raise ValueError('No detector support on the requested reciprocal grid')
    selected={int(np.argmin(abs(energy-v))):edge for edge,v in (('L3',cfg.l3),('L2',cfg.l2))}
    return qx,qy,weights,detector_support,selected


def contract(model,settings,cfg,method,C,energy,tensors,stage,cancelled,prepared_incoming=None,*,energy_checkpoint=None):
    """Full field at selected map energies, detector-only elsewhere, on one grid.

    Detector-only skips exactly zero-weight pixels. Fractional weights and all
    physical/numerical parameters are identical; no interpolation or coarsening.
    Double responses already include depth integration; Single needs thickness.
    """
    from .emcd_forward import Cancelled
    qx,qy,weights,detector_support,selected=angular_schedule(model,cfg,energy)
    dq2=(qx[0,1]-qx[0,0])**2
    full_weights=np.stack([weights[k].ravel() for k in ('A','B')])
    spectra={f'I_{d}_{s}':np.empty(len(energy)) for s in ('plus','minus') for d in ('A','B')}
    maps={};phase=fcc_site_phase_matrix(model);elastic=model.elastic
    folded=(cfg.systematic_row or (settings.zone==(0,1,7) and abs(settings.tilt[1])<1e-14))
    supports={}
    for full in (False,True) if cfg.angular_maps else (False,):
        support=np.ones(qx.size,bool) if full else detector_support
        points=np.column_stack((qx.ravel()[support],qy.ravel()[support]))
        if folded and cfg.channeling_model=='double':
            query,inverse=np.unique(np.column_stack((points[:,0],abs(points[:,1]))),axis=0,return_inverse=True)
            sign=np.ones((len(points),3));sign[points[:,1]<0,1]=-1
        else:query=points;inverse=sign=None
        supports[full]=(support,points,query,inverse,sign)
    n=len(elastic.beams.hkl);workers=worker_count(n,method)
    start_incoming=perf_counter()
    incoming_bw=prepare_incoming_bloch(elastic,settings.thickness,cfg.depth,cancelled=cancelled) if cfg.channeling_model=='double' and method=='bloch' else None
    incoming_seconds=perf_counter()-start_incoming
    diagnostics=[]
    for ie,e in enumerate(energy):
        if cancelled():raise Cancelled()
        full=cfg.angular_maps and ie in selected
        support,points,query,inverse,sign=supports[full]
        diagnostic=dict(energy_ev=float(e),full_field=full,required_pixels=len(points),
            evaluated_pixels=0,query_pixels=0,response_batches=0,outgoing_directions=0,
            mirror_reuse=folded and cfg.channeling_model=='double',checkpoint_reused=False,
            outgoing_response_seconds=0.,mdff_contraction_seconds=0.)
        stage(f'{method} {cfg.channeling_model}: energy {ie+1}/{len(energy)} ({e:.4f} eV)')
        cached=energy_checkpoint(float(e),None) if energy_checkpoint is not None else None
        if cached is not None:
            raw=np.asarray(cached['raw'])
            if raw.shape!=(4,) or raw.dtype!=np.float64 or not np.isfinite(raw).all() or np.any(raw<0):raise ValueError('Invalid energy checkpoint detector intensities')
            # A legacy raw-only entry is sufficient away from map energies.
            # At selected edges require complete maps, or recalculate this one
            # energy. Never treat partial arrays as a completed full-field map.
            if full and 'maps' in cached:
                saved_maps=np.asarray(cached['maps'])
                if saved_maps.shape!=(2,cfg.grid,cfg.grid) or saved_maps.dtype!=np.float64 or not np.isfinite(saved_maps).all():raise ValueError('Invalid energy checkpoint angular maps')
            if not full or 'maps' in cached:
                for j,key in enumerate(('I_A_plus','I_B_plus','I_A_minus','I_B_minus')):spectra[key][ie]=raw[j]
                if full:
                    plus,minus=saved_maps
                    maps[selected[ie]]=dict(I_plus=plus,I_minus=minus,I_mag=(plus-minus)/2,I_nonmag=(plus+minus)/2)
                diagnostic['checkpoint_reused']=True;diagnostics.append(diagnostic)
                continue
        if cfg.channeling_model=='single':
            start_contract=perf_counter()
            values=np.empty((2,len(points)))
            for start in range(0,len(points),64):
                if cancelled():raise Cancelled()
                sl=slice(start,start+64)
                for si,t in enumerate(tensors):
                    even,odd=_tensor_angular_maps(model,t.tensor_angstrom2_per_ev[ie],e,C,phase,points[sl,0],points[sl,1])
                    values[si,sl]=settings.thickness*(even+odd)
            if values.min() < -1e-8*max(1.,values.max()):raise ValueError('Negative tensor-derived inelastic intensity: check conventions/phase')
            diagnostic['mdff_contraction_seconds']=perf_counter()-start_contract
        else:
            def response(batch):
                if cancelled():raise Cancelled()
                if method=='bloch':
                    return double_channeling_response(elastic,float(e),batch,settings.thickness,
                        method='analytic' if cfg.systematic_row else 'numerical',depth_steps=cfg.depth,
                        memory_budget_mib=cfg.memory_budget_mib,prepared_incoming=incoming_bw,cancelled=cancelled)
                grid,incoming=prepared_incoming
                r,diag=multislice_double_channeling_response(elastic,float(e),batch,settings.thickness,
                    fft_grid=cfg.fft_grid,potential_cutoff=settings.potential_cutoff,
                    systematic_row=cfg.systematic_row,row_reduction=cfg.systematic_row,
                    projected_geometry=Ni017Geometry() if settings.zone==(0,1,7) else None,
                    depth_steps=cfg.depth,slice_step_nm=cfg.slice_step,memory_budget_mib=cfg.memory_budget_mib,
                    prepared_grid=grid,prepared_incoming=incoming,cancelled=cancelled)
                return r
            # MS chunks bound cancellation latency without retaining outgoing
            # depth stacks. BW retains its existing per-call dense admission.
            batches=([query[i:i+32] for i in range(0,len(query),32)] if method=='fft-multislice'
                     else [a for a in np.array_split(query,min(workers,len(query))) if len(a)])
            start_response=perf_counter()
            with bw_executor_guard(method,cancelled):
                with ThreadPoolExecutor(max_workers=workers) as pool:
                    responses=list(pool.map(response,batches))
            r=np.concatenate(responses)
            diagnostic.update(outgoing_response_seconds=perf_counter()-start_response,response_batches=len(batches),outgoing_directions=len(query),workers=workers)
            start_contract=perf_counter()
            if inverse is not None:r=r[inverse]*sign[:,:,None]*sign[:,None,:]
            values=np.stack([intensities_from_response(r,t.tensor_angstrom2_per_ev[ie]) for t in tensors])
            diagnostic['mdff_contraction_seconds']=perf_counter()-start_contract
        diagnostic.update(evaluated_pixels=len(points),query_pixels=len(query))
        diagnostics.append(diagnostic)
        if cancelled():raise Cancelled()
        for si,s in enumerate(('plus','minus')):
            # Preserve the historical full-grid reduction length/order for map
            # requests. Filling omitted, zero-weight pixels is integration work
            # only; no non-selected full-field intensity array is exported.
            if cfg.angular_maps or cfg.channeling_model=='single':
                plane=np.zeros(qx.size);plane[support]=values[si]
                integrated=(np.sum(full_weights*plane,axis=1) if cfg.channeling_model=='single' else full_weights@plane)*dq2
            else:integrated=full_weights[:,support]@values[si]*dq2
            for di,d in enumerate(('A','B')):spectra[f'I_{d}_{s}'][ie]=integrated[di]
        if cfg.angular_maps and ie in selected:
            plus,minus=values.reshape(2,cfg.grid,cfg.grid)
            maps[selected[ie]]=dict(I_plus=plus,I_minus=minus,I_mag=(plus-minus)/2,I_nonmag=(plus+minus)/2)
        if cancelled():raise Cancelled()
        if energy_checkpoint is not None:
            compact=dict(raw=np.array([spectra[k][ie] for k in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus')]))
            if cfg.angular_maps and ie in selected:compact['maps']=values.reshape(2,cfg.grid,cfg.grid)
            energy_checkpoint(float(e),compact)
    if cancelled():raise Cancelled()
    return dict(spectra=spectra,maps=maps,qx=qx,qy=qy,weights=weights,diagnostics=diagnostics,
        angular_evaluation_policy=EVALUATION_POLICY,incoming_preparation_seconds=incoming_seconds)
