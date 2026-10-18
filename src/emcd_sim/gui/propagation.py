"""Verified [017] incoming FFT adapter, numerical diagnostics and labeled exports."""
from pathlib import Path
import json
import numpy as np
from .geometry import geometry,orientation
from ..ni_017_geometry import Ni017Geometry
from ..multislice_reference import fft_multislice_ni
from ..multislice_emcd_reference import project_fft_amplitudes,complex_wave_diagnostics

METHOD_NAMES={'bloch':'Bloch-wave','fft-multislice':'FFT Multislice','difference':'BW-MS numerical difference'}


def numerical_info(structure,settings,cfg,*,hkl=None,check_memory=True):
    if cfg.propagation not in ('bloch','fft-multislice','both'):raise ValueError('Unknown propagation method')
    if cfg.channeling_model not in ('single','double'):raise ValueError('Unknown channeling model')
    if hkl is None:hkl=geometry(structure,settings,systematic_row=cfg.systematic_row)[2]
    n=len(hkl);pixels=cfg.grid**2;mesh=cfg.fft_grid**2
    pair=16*(pixels if cfg.angular_maps else min(pixels,64))*n*n/2**20;dense=4*pair
    info=dict(bw_beams=n,fft_harmonics=0,potential_nonzero_harmonics=0,single_complex_pair_mib=pair,dense_working_estimate_mib=dense,
        fft_storage_working_mib=0.,coherence_working_mib=16*cfg.depth*n*n/2**20,propagation=cfg.propagation,
        fft_grid=cfg.fft_grid,slice_step_nm=cfg.slice_step,depth_nodes=cfg.depth)
    if cfg.propagation!='bloch':
        if settings.zone!=(0,1,7) and not (settings.zone==(0,0,1) and cfg.systematic_row):raise ValueError('FFT EMCD supports verified Ni [017] or the explicit [001] (200) systematic row; no automatic fallback.')
        from .emcd_forward import material_reason
        reason=material_reason(structure)
        if reason:raise ValueError(reason)
        if not isinstance(cfg.fft_grid,int) or not 12<=cfg.fft_grid<=128 or cfg.fft_grid%2:raise ValueError('FFT grid must be even, 12–128')
        if not np.isfinite(cfg.slice_step) or not .001<=cfg.slice_step<=1:raise ValueError('Maximum slice step must be 0.001–1 nm')
        if int(np.ceil(settings.thickness/(cfg.depth-1)/cfg.slice_step))*(cfg.depth-1)>200000:raise ValueError('Requested FFT propagation exceeds 200000 split steps; increase slice step or reduce thickness explicitly')
        geo=Ni017Geometry() if settings.zone==(0,1,7) else None
        if geo is not None:
            if not np.allclose(orientation(structure.atoms.cell.array,settings.zone),geo.frame,atol=1e-14):raise ValueError('FFT and BW orientation frames differ')
            harmonics,g=geo.harmonics(cfg.fft_grid,max(settings.beam_cutoff,settings.potential_cutoff))
        else:
            if max(settings.beam_cutoff,settings.potential_cutoff)>=(cfg.fft_grid//2-1)*2/3.524:raise ValueError('Beam/potential support reaches unsafe FFT Nyquist boundary')
            v=np.rint(np.fft.fftfreq(cfg.fft_grid)*cfg.fft_grid).astype(int);x,y=np.meshgrid(v,v,indexing='ij')
            harmonics=np.stack((2*x,2*y,np.zeros_like(x)),axis=-1).reshape(-1,3);g=harmonics[:,:2]/3.524
        lookup={tuple(h):i for i,h in enumerate(harmonics)}
        if len(lookup)!=mesh or any(tuple(h) not in lookup for h in hkl):raise ValueError('FFT mesh does not contain the exact ordered common hkl basis')
        actual=geometry(structure,settings,systematic_row=cfg.systematic_row)[3]
        if not np.allclose(g[[lookup[tuple(h)] for h in hkl]],actual,atol=1e-13):raise ValueError('FFT and BW reciprocal coordinates differ')
        allowed=np.array([geo.crystal.is_allowed(tuple(h)) for h in harmonics]) if geo is not None else harmonics[:,1]==0
        count=int(np.sum(allowed & (np.linalg.norm(g,axis=1)<=settings.potential_cutoff) & np.any(harmonics!=0,axis=1)))
        info.update(fft_harmonics=mesh,potential_nonzero_harmonics=count,fft_storage_working_mib=(24*cfg.depth+160)*mesh/2**20,
            projected_geometry='Actual oriented Ni [017] full 2D, or explicitly selected [001] (200) systematic row; exact common hkl, IAM, B and Fourier cutoff as BW')
    methods=2 if cfg.propagation=='both' else 1
    info['retained_results_working_mib']=(methods*(24*cfg.depth*n+32*n*n+160*pixels+128*cfg.energy_points)+96*pixels*n)/2**20
    info['estimated_working_mib']=dense+info['fft_storage_working_mib']+info['coherence_working_mib']+info['retained_results_working_mib']
    if cfg.channeling_model=='double':
        from .channeling import worker_count
        bw_dense=80*n**4/2**20
        bw_work=bw_dense+(128*(n*n+cfg.depth*(2*n+12))+144*pixels)/2**20+8
        samples=cfg.fft_grid if cfg.systematic_row else mesh
        ms_dense=96*32*n*n/2**20
        ms_work=ms_dense+(64*cfg.depth*samples+192*32*samples+32*32*9+64*len(structure.atoms)*n*n)/2**20+8
        engines=[];densities=[]
        if cfg.propagation in ('bloch','both'):engines.append(worker_count(n,'bloch')*bw_work);densities.append(bw_dense)
        if cfg.propagation in ('fft-multislice','both'):engines.append(worker_count(n,'fft-multislice')*ms_work);densities.append(ms_dense)
        dense=max(densities);info['dense_working_estimate_mib']=dense
        info['estimated_working_mib']=max(engines)+info['retained_results_working_mib']+info['fft_storage_working_mib']
        info['detector_workers']={k:worker_count(n,k) for k in ('bloch','fft-multislice')}
    info['memory_note']='Dense arrays plus FFT/depth storage, retained method results and coordinate/work arrays. Total process estimate adds current RSS, concurrent reservations, 25% allocation margin and 128 MiB reserve. Conservative estimate, not guaranteed peak RSS.'
    if check_memory:
        from .memory_budget import assess_memory
        info.update(assess_memory(info['estimated_working_mib'],cfg.memory_budget_mib,dense_mib=dense))
    return info


def propagate(elastic,settings,cfg,z,stage,*,cancelled=None):
    waves={};extra={}
    if cfg.propagation in ('bloch','both'):
        stage('Running Bloch-wave propagation');waves['bloch']=elastic.amplitudes(z)
    if cfg.propagation in ('fft-multislice','both'):
        if cfg.channeling_model=='double' or cfg.systematic_row:
            from .channeling import fft_geometry,incident_fields
            stage('Running incoming FFT propagation in the matched projected potential')
            grid=fft_geometry(elastic,settings,cfg)
            incoming=incident_fields(grid,settings.thickness,depth_steps=cfg.depth,slice_step_nm=cfg.slice_step,cancelled=cancelled)
            psi=incoming[0][:,grid.indices(elastic.beams.hkl)];waves['fft-multislice']=psi
            total=np.sum(abs(incoming[0])**2,axis=1);outside=total-np.sum(abs(psi)**2,axis=1)
            extra=dict(beam_hkl=grid.hkl,reciprocal_gxy=grid.g,exit_intensity=abs(incoming[0][-1])**2,
                total_norm=total,excluded_intensity=outside,_prepared=(grid,incoming),
                summary=dict(norm_error=float(abs(total-1).max()),max_excluded_population=float(outside.max()),exit_excluded_population=float(outside[-1]),
                    projected_norm_exit=float(np.sum(abs(psi[-1])**2)),renormalized=False,phase_convention='raw FFT coefficients; no conjugation or fitted factor'))
            return waves,extra
        stage('Running FFT multislice propagation in actual [017] projected potential')
        fft=fft_multislice_ni(z,acceleration_kv=settings.voltage,tilt_mrad_xy=settings.tilt,grid_points=cfg.fft_grid,
            slice_step_nm=cfg.slice_step,potential_cutoff_inv_angstrom=settings.potential_cutoff,b_factor_angstrom2=settings.b_factor,
            return_amplitudes=True,projected_geometry=Ni017Geometry())
        stage('Projecting complex FFT amplitudes onto exact ordered common hkl')
        psi,outside=project_fft_amplitudes(fft,elastic.beams.hkl);waves['fft-multislice']=psi
        extra=dict(beam_hkl=fft.beam_hkl,reciprocal_gxy=fft.reciprocal_xy_inv_angstrom,exit_intensity=fft.intensity[-1],
            full_amplitudes=fft.amplitudes,total_norm=fft.intensity.sum(axis=1),excluded_intensity=outside,
            summary=dict(norm_error=fft.norm_error,max_excluded_population=float(outside.max()),exit_excluded_population=float(outside[-1]),
                projected_norm_exit=float(np.sum(abs(psi[-1])**2)),renormalized=False,phase_convention='raw fft2(wave)/N²; no conjugation, sign remapping or fitted factor'))
    return waves,extra


def error_pair(a,b,floor=0.):
    a,b=np.asarray(a),np.asarray(b);delta=a-b;scale=max(float(np.linalg.norm(a)),float(np.linalg.norm(b)))
    return dict(max_abs=float(np.max(abs(delta))),l2_absolute=float(np.linalg.norm(delta)),
                l2_relative=float(np.linalg.norm(delta)/scale) if scale>max(floor,1e-30) else None,
                relative_floor=float(floor))


def compare_methods(methods,fft):
    out=dict(warning='BW/MS agreement tests numerical propagation at fixed settings; it does not establish physical-potential or EMCD convergence.')
    if fft:out['fft']=fft['summary']
    if len(methods)!=2:return out
    from .emcd_forward import metrics
    b,m=[methods[k] for k in ('bloch','fft-multislice')];C,D=b['coherence'],m['coherence']
    diag=complex_wave_diagnostics(b['amplitudes'],m['amplitudes'])
    out.update(amplitudes=dict(max_abs_raw=float(diag['amplitude_max_abs_raw'].max()),max_abs_global_phase_aligned_diagnostic_only=float(np.nanmax(diag['amplitude_max_abs_aligned']))),
        coherence=error_pair(C,D,1e-14),elastic_exit=error_pair(abs(b['amplitudes'][-1])**2,abs(m['amplitudes'][-1])**2,1e-12),
        elastic_depth_average=error_pair(np.diag(C).real,np.diag(D).real,1e-12),edges={},spectra={})
    bm,mm=metrics(b),metrics(m)
    intensity_floor=1e-10*max(float(r['spectra']['Sigma_ref'].max()) for r in (b,m))
    for key in ('I_A_plus','I_B_plus','D_mag','D_nonmag','D_raw','D_corrected'):
        if key in b['spectra'] and key in m['spectra']:out['spectra'][key]=error_pair(b['spectra'][key],m['spectra'][key],intensity_floor*np.sqrt(len(b['spectra'][key])))
    for edge in ('L3','L2'):
        maps={}
        if all(edge in r['maps'] for r in (b,m)):
            scale=max(np.linalg.norm(r['maps'][edge]['I_nonmag']) for r in (b,m))
            maps={key:error_pair(b['maps'][edge][key],m['maps'][edge][key],1e-10*scale) for key in ('I_mag','I_nonmag','I_plus')}
        scalars={}
        for key in ('D_mag','D_nonmag','D_raw','D_corrected','A_mag','A_nonmag','Sigma_ref','alpha'):
            x,y=bm[edge][key],mm[edge][key]
            if x is None or y is None:scalars[key]=dict(absolute=None,relative=None)
            else:
                floor=1e-10 if key.startswith('A_') or key=='alpha' else intensity_floor
                scalars[key]=dict(absolute=abs(x-y),relative=abs(x-y)/max(abs(x),abs(y)) if max(abs(x),abs(y))>floor else None)
        out['edges'][edge]=dict(maps=maps,detector=scalars)
    return out


def export_comparison(result,root,export_single):
    methods=result.get('methods',{result.get('method','bloch'):result});labels=list(methods)
    # Preserve all historical primary arrays. Additional fields have explicit
    # method prefixes; no hidden axis changes for Stage B consumers.
    for filename,kind in (('angular_maps','maps'),('virtual_detector_eels','spectra')):
        with np.load(root/(filename+'.npz'),allow_pickle=False) as saved:arrays={k:saved[k] for k in saved.files}
        arrays['method_labels']=np.asarray(labels)
        for name,r in methods.items():
            if kind=='spectra':arrays.update({name+'__'+k:v for k,v in r['spectra'].items()})
            else:
                arrays.update({name+'__'+edge+'__'+key:v for edge,fields in r['maps'].items() for key,v in fields.items()})
                arrays[name+'__coherence']=r['coherence']
        np.savez_compressed(root/(filename+'.npz'),**arrays)
    arrays=dict(method_labels=np.asarray(labels),beam_hkl=np.asarray(result['metadata']['beam_hkl']),g=np.asarray(result['metadata']['g']),depth_nm=result['depth_nm'])
    for name,r in methods.items():
        arrays.update({name+'__amplitudes':r['amplitudes'],name+'__exit_intensity':abs(r['amplitudes'][-1])**2,name+'__depth_average_intensity':np.diag(r['coherence']).real})
    fft=result.get('fft',{})
    for key in ('beam_hkl','reciprocal_gxy','exit_intensity','total_norm','excluded_intensity','full_amplitudes'):
        if key in fft:arrays['fft_full__'+key]=fft[key]
    if len(methods)==2:
        diag=complex_wave_diagnostics(methods['bloch']['amplitudes'],methods['fft-multislice']['amplitudes']);arrays.update(diag)
    np.savez_compressed(root/'diffraction_pattern.npz',**arrays)
    from .emcd_forward import metrics
    meta=dict(method_labels=labels,methods={name:dict(r['metadata'],edge_metrics=metrics(r)) for name,r in methods.items()},
        diagnostics=result.get('comparison',{}),array_schema='Unprefixed arrays: primary method. method__field and method__edge__field: explicit arrays; maps (qy,qx), spectra (energy), amplitudes (depth,beam). No implicit method dimension.',primary_method=result.get('method','bloch'))
    (root/'comparison_metadata.json').write_text(json.dumps(meta,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    if len(methods)>1:
        from matplotlib.figure import Figure
        from .results import draw_comparison,draw_eels,draw_maps
        for name,r in methods.items():
            export_single(r,root/name)
            for edge in ('L3','L2'):
                fig=Figure(figsize=(15,9),layout='constrained');draw_maps(fig,result,edge,method=name);fig.savefig(root/name/(edge+'_angular_maps.png'),dpi=145)
        fig=Figure(figsize=(15,10),layout='constrained');draw_comparison(fig,result);fig.savefig(root/'bw_ms_comparison.png',dpi=145)
        fig=Figure(figsize=(12,9),layout='constrained');draw_eels(fig,result,method='overlay');fig.savefig(root/'virtual_detector_eels.png',dpi=145)
        for edge in ('L3','L2'):
            fig=Figure(figsize=(15,9),layout='constrained');draw_maps(fig,result,edge,method='difference');fig.savefig(root/(edge+'_bw_minus_ms.png'),dpi=145)
