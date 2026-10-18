"""GUI adapters to the existing channeling kernels; no scattering model here."""
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from ..double_channeling import double_channeling_response, intensities_from_response
from ..multislice_double_channeling import ProjectedNiFFT, incident_fields, multislice_double_channeling_response
from ..ni_017_geometry import Ni017Geometry
from ..single_channeling_tensor import _tensor_angular_maps, fcc_site_phase_matrix


def fft_geometry(elastic,settings,cfg):
    return ProjectedNiFFT.build(elastic,grid_points=cfg.fft_grid,potential_cutoff=settings.potential_cutoff,
        systematic_row=cfg.systematic_row,row_reduction=cfg.systematic_row,
        projected_geometry=Ni017Geometry() if settings.zone==(0,1,7) else None)


def worker_count(n,method):
    dense=80*n**4/2**20
    return min(4,max(1,int(1200/(dense+40)))) if method=='bloch' else 4


def contract(model,settings,cfg,method,C,energy,tensors,stage,cancelled,prepared_incoming=None):
    """Full maps or explicitly requested detector-only evaluation on the same grid.

    Detector-only skips exactly zero-weight pixels. Fractional weights and all
    physical/numerical parameters are identical; no interpolation or coarsening.
    Double responses already include depth integration; Single needs thickness.
    """
    from .emcd_forward import Cancelled
    q=np.linspace(-cfg.halfwidth,cfg.halfwidth,cfg.grid);qx,qy=np.meshgrid(q,q,indexing='xy')
    weights={k:d.integration_weights(qx,qy,mode='fractional',subpixels=cfg.subpixels) for k,d in model.detectors.items()}
    support=np.ones(qx.size,bool) if cfg.angular_maps else np.logical_or.reduce([w.ravel()>0 for w in weights.values()])
    if not support.any():raise ValueError('No detector support on the requested reciprocal grid')
    points=np.column_stack((qx.ravel()[support],qy.ravel()[support]));dq2=(q[1]-q[0])**2
    w=np.stack([weights[k].ravel()[support] for k in ('A','B')])
    spectra={f'I_{d}_{s}':np.empty(len(energy)) for s in ('plus','minus') for d in ('A','B')}
    maps={};phase=fcc_site_phase_matrix(model);elastic=model.elastic
    folded=(cfg.systematic_row or (settings.zone==(0,1,7) and abs(settings.tilt[1])<1e-14))
    if folded:
        query,inverse=np.unique(np.column_stack((points[:,0],abs(points[:,1]))),axis=0,return_inverse=True)
        sign=np.ones((len(points),3));sign[points[:,1]<0,1]=-1
    else:query=points
    n=len(elastic.beams.hkl);workers=worker_count(n,method)
    selected={int(np.argmin(abs(energy-v))):edge for edge,v in (('L3',cfg.l3),('L2',cfg.l2))}
    diagnostics=[]
    for ie,e in enumerate(energy):
        if cancelled():raise Cancelled()
        stage(f'{method} {cfg.channeling_model}: energy {ie+1}/{len(energy)} ({e:.4f} eV)')
        if cfg.channeling_model=='single':
            values=np.empty((2,len(points)))
            for start in range(0,len(points),64):
                if cancelled():raise Cancelled()
                sl=slice(start,start+64)
                even,odd=_tensor_angular_maps(model,tensors[0].tensor_angstrom2_per_ev[ie],e,C,phase,points[sl,0],points[sl,1])
                values[:,sl]=settings.thickness*np.stack((even+odd,even-odd))
        else:
            def response(batch):
                if cancelled():raise Cancelled()
                if method=='bloch':
                    return double_channeling_response(elastic,float(e),batch,settings.thickness,
                        method='analytic' if cfg.systematic_row else 'numerical',depth_steps=cfg.depth,
                        memory_budget_mib=cfg.memory_budget_mib)
                grid,incoming=prepared_incoming
                r,diag=multislice_double_channeling_response(elastic,float(e),batch,settings.thickness,
                    fft_grid=cfg.fft_grid,potential_cutoff=settings.potential_cutoff,
                    systematic_row=cfg.systematic_row,row_reduction=cfg.systematic_row,
                    projected_geometry=Ni017Geometry() if settings.zone==(0,1,7) else None,
                    depth_steps=cfg.depth,slice_step_nm=cfg.slice_step,memory_budget_mib=cfg.memory_budget_mib,
                    prepared_grid=grid,prepared_incoming=incoming)
                return r
            # MS chunks bound cancellation latency without retaining outgoing
            # depth stacks. BW retains its existing per-call dense admission.
            batches=([query[i:i+32] for i in range(0,len(query),32)] if method=='fft-multislice'
                     else [a for a in np.array_split(query,min(workers,len(query))) if len(a)])
            with ThreadPoolExecutor(max_workers=workers) as pool:
                responses=list(pool.map(response,batches))
            r=np.concatenate(responses)
            if folded:r=r[inverse]*sign[:,:,None]*sign[:,None,:]
            values=np.stack([intensities_from_response(r,t.tensor_angstrom2_per_ev[ie]) for t in tensors])
            diagnostics.append(dict(energy_ev=float(e),workers=workers,query_pixels=len(query),mirror_reuse=folded))
        for si,s in enumerate(('plus','minus')):
            integrated=w@values[si]*dq2
            for di,d in enumerate(('A','B')):spectra[f'I_{d}_{s}'][ie]=integrated[di]
        if cfg.angular_maps and ie in selected:
            plus,minus=values.reshape(2,cfg.grid,cfg.grid)
            maps[selected[ie]]=dict(I_plus=plus,I_minus=minus,I_mag=(plus-minus)/2,I_nonmag=(plus+minus)/2)
    return dict(spectra=spectra,maps=maps,qx=qx,qy=qy,weights=weights,diagnostics=diagnostics)
