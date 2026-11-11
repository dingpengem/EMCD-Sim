"""Snapshot adapter: independent BW/FFT waves and one shared tensor contraction."""
from dataclasses import dataclass, asdict, replace, field
from pathlib import Path
import hashlib, json, platform, subprocess
from time import perf_counter
import numpy as np
from .geometry import Structure, Settings, geometry, elastic_model, excitation, za_from_tilt
from ..geometry import VirtualDetector, electron_wavelength_angstrom
from ..historical_ni import NiLocalConfig
from ..wien2k_xmcd import load_wien2k_xmcd
from ..emcd_angular_plots import paired_geometry, paired_maps
from ..xmcd_postedge_normalization import analyze_postedge_spectra

from .runtime import reference_source, build_info

DEFAULT_SOURCE = reference_source()


def inspect_source(path):
    """Basic import is independent of optional original WIEN2k companion audit."""
    s=load_wien2k_xmcd(path); n=s.nonmagnetic
    maxima=np.flatnonzero((n[1:-1]>n[:-2]) & (n[1:-1]>=n[2:]))+1
    peaks=[]
    for i in sorted(maxima,key=lambda i:n[i],reverse=True):
        if all(abs(s.energy_ev[i]-s.energy_ev[j])>8 for j in peaks):peaks.append(i)
        if len(peaks)==2:break
    selected=None
    if len(peaks)==2:
        selected={}
        for edge,i in zip(('L3','L2'),sorted(peaks)):
            ix=np.flatnonzero(abs(s.energy_ev-s.energy_ev[i])<=3)
            selected[edge]=float(s.energy_ev[ix[np.argmax(abs(s.dichroic[ix]))]])
    info=dict(sha256=s.source_sha256,bounds=[float(s.energy_ev[0]),float(s.energy_ev[-1])],
              selected=selected,provenance='Five-column validated. User must declare source magnetic axis, RP/LP convention and edge assignment.',audit=None)
    suffixes=('raw1','raw2','broad1','broad2','rawxmcd','inso','injoint','inc')
    if Path(path).resolve()==DEFAULT_SOURCE.resolve() and all(Path(path).with_suffix('.'+k).exists() for k in suffixes):
        from ..wien2k_source_audit import energy_audit
        info['audit']=energy_audit(path);info['selected']=info['audit']['selected_magnetic_energies_ev']
        info['provenance']='Original Ni companion audit passed; cubic [001], native unshifted L3/L2.'
    return info


@dataclass(frozen=True)
class ForwardSettings:
    model: str='xmcd'
    source: str=str(DEFAULT_SOURCE)
    source_sha256: str=''
    axis_declared: bool=False
    magnetization: tuple=(0.,0.,1.)
    eta: float=1.
    beta: float=1.
    l3: float=831.271
    l2: float=848.698
    atomic: NiLocalConfig=field(default_factory=NiLocalConfig)
    sigma: float=.8
    radial: float|None=None
    energy_points: int=241
    grid: int=97
    depth: int=64
    subpixels: int=64
    halfwidth: float=1.
    centers: tuple=((.2837684449489217,.2837684449489217),(.2837684449489217,-.2837684449489217))
    radius: float=.0908059024
    correction: bool=True
    window: tuple=(878.,882.)
    propagation: str='bloch'
    fft_grid: int=32
    slice_step: float=2.
    memory_budget_mib: int=2048
    # Missing fields in historical projects retain their explicit fixed budget.
    memory_mode: str='manual'
    resource_allocation: dict|None=None
    channeling_model: str='single'
    energy_scope: str='full'
    energy_sampling: str='uniform'
    angular_maps: bool=True
    angular_evaluation: str='selected'
    systematic_row: bool=False
    worker_mode: str='automatic'
    parallel_workers: int=1
    fft_generators: tuple|None=None

    @property
    def calculation_memory_budget_mib(self):
        from .memory_budget import resource_budget
        return resource_budget(self)


# Historical imports remain aliases, not additional forward implementations.
from ..historical_ni import material_reason, tensors, energy_grid
from ..mdff_orientation import axis_rotation


from ..cancellation import Cancelled, check_cancelled


def calculate(structure,settings,cfg,progress=lambda s:None,cancelled=lambda:False,*,energy_ev=None,energy_checkpoint=None,execution_policy=None):
    check_cancelled(cancelled)
    if execution_policy is None:cfg=replace(cfg,resource_allocation=None)
    from .forward_pipeline import validate_before_resources
    validate_before_resources(structure,settings,cfg,energy_ev)
    from .propagation import numerical_info,resolve_fft_configuration
    cfg=resolve_fft_configuration(structure,settings,cfg)
    from .memory_budget import reserve_memory
    from ..mdff_providers import prepare_provider
    from .provider_preparation import provider_energy_grid
    actual_energy=provider_energy_grid(prepare_provider(cfg),cfg,energy_ev)
    info=numerical_info(structure,settings,replace(cfg,energy_points=len(actual_energy)))
    if execution_policy is not None and execution_policy['effective_workers']!=info['execution']['effective_workers']:
        raise ValueError('Resources changed since preflight; Run again to review the new effective worker counts.')
    execution_policy=info['execution']
    from .parallel_resources import bind_allocation
    cfg=bind_allocation(cfg,info)
    check_cancelled(cancelled)
    # Double kernels make their own concurrent reservations. Reserve retained
    # GUI arrays here, after admitting the complete estimated working set.
    reserved=info['retained_results_working_mib'] if cfg.channeling_model=='double' else info['estimated_working_mib']
    with reserve_memory(reserved,cfg.calculation_memory_budget_mib,dense_mib=info['dense_working_estimate_mib']) as admission:
        result=_calculate(structure,settings,cfg,progress,cancelled,energy_ev=energy_ev,energy_checkpoint=energy_checkpoint,execution_policy=execution_policy)
        result['metadata']['execution']=execution_policy
        check_cancelled(cancelled)
        result['metadata']['memory_admission']=admission
        for r in result['methods'].values():r['metadata']['memory_admission']=admission
        return result


def _calculate(structure,settings,cfg,progress,cancelled,*,energy_ev=None,energy_checkpoint=None,execution_policy=None):
    """Historical API delegates to the common production orchestration."""
    from .forward_pipeline import calculate_prepared
    return calculate_prepared(structure,settings,cfg,progress,cancelled,energy_ev=energy_ev,
        energy_checkpoint=energy_checkpoint,execution_policy=execution_policy)


def _contract(structure,settings,cfg,model,R,hkl,g,memory,z,psi,C,energy,ts,stage,cancelled,*,prepared):
    """Stage B EELS/parity/post-edge implementation, shared by both coherences."""
    stage('Computing energy-resolved EELS and fractional detector integrals')
    spectra,maps,qx,qy,weights=[prepared[k] for k in ('spectra','maps','qx','qy','weights')]
    stage('Computing selected-edge map decomposition and post-edge diagnostics')
    ap,bp,am,bm=[spectra[k] for k in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus')]
    na,nb,ma,mb=(ap+am)/2,(bp+bm)/2,(ap-am)/2,(bp-bm)/2
    spectra.update(energy_ev=energy,N_A=na,N_B=nb,M_A=ma,M_B=mb,D_mag=ma-mb,D_nonmag=na-nb,D_raw=ap-bp,Sigma_ref=na+nb)
    from .prb_benchmark import benchmark_spectra
    spectra.update(benchmark_spectra(spectra)[0])
    alpha=None;correction_reason='Correction disabled by user.'
    if cfg.correction:
        try:
            post=analyze_postedge_spectra(energy,ap,bp,am,bm,windows=(cfg.window,),edge_windows={})
            alpha=float(post.spectra['alpha_obs'][0]);correction_reason='Observed +M A/B post-edge integral ratio; corrected contrast is not intrinsically magnetic.'
            for key in ('D_corrected','D_mag_processed_obs','D_nonmag_residual_obs'):spectra[key]=post.spectra[key][0]
            spectra['magnetic_bias']=spectra['D_mag_processed_obs']-spectra['D_mag']
        except ValueError as exc:correction_reason='Correction disabled: '+str(exc)
    try:pg=paired_geometry(model,qx,qy,subpixels=cfg.subpixels);pair_reason='Validated y-reflected physical aperture pair.'
    except ValueError as exc:pg=None;pair_reason='Mirrored maps disabled: '+str(exc)
    if pg is not None:
        for edge,m in maps.items():
            m.update(paired_maps(m['I_plus'],m['I_minus'],alpha if alpha is not None else 1.,pg))
            if alpha is None:
                for key in ('D_corrected','D_mag_processed','D_nonmag_residual'):m.pop(key)
    if not np.allclose(spectra['D_raw'],spectra['D_mag']+spectra['D_nonmag'],rtol=1e-10,atol=1e-13*max(ap.max(),bp.max())):raise ArithmeticError('Detector parity identity failed')
    audit=inspect_source(cfg.source) if cfg.model=='xmcd' else None
    if audit and cfg.source_sha256 and audit['sha256']!=cfg.source_sha256:
        raise ValueError('XMCD source changed during calculation; result discarded')
    build=build_info();commit=build['commit'];dirty=build.get('dirty')
    from ..elastic_providers import provider_provenance
    meta=dict(settings=asdict(settings),elastic_provider=provider_provenance(model.elastic.crystal.species,settings.elastic_provider),mdff=asdict(cfg),structure=structure.description(),frame=R.tolist(),beam_hkl=[list(h) for h in hkl],g=g.tolist(),
        source_audit=audit,energy_ev=energy.tolist(),magnetization_crystal=(np.asarray(cfg.magnetization)/np.linalg.norm(cfg.magnetization)).tolist(),
        magnetization_local=(R@np.asarray(cfg.magnetization)/np.linalg.norm(cfg.magnetization)).tolist(),
        reversal='XMCD: eta reversed in crystal frame; atomic: swap spin holes and reverse exchange at transition level, fixed core-SOC amplitudes; then R T R^T',
        za_q=za_from_tilt(settings.tilt,settings.voltage).tolist(),transmitted_q=[0.,0.],wavelength_angstrom=electron_wavelength_angstrom(settings.voltage),
        s_target=float(excitation(g[hkl.index(settings.target)],settings.tilt,settings.voltage)),alpha=alpha,correction_reason=correction_reason,pair_reason=pair_reason,
        detector_areas={k:float(w.sum()*(qx[0,1]-qx[0,0])**2) for k,w in weights.items()},integration='fractional',dense_estimate_mib=memory,
        channeling_model=cfg.channeling_model,angular_maps_calculated=cfg.angular_maps,spectral_coverage=cfg.energy_scope,
        outgoing_energy_ev=(1000*settings.voltage-energy).tolist() if cfg.channeling_model=='double' else None,
        longitudinal_transfer='q_z=-E_loss/(h*v_in), evaluated at each loss; frozen across branches, not across energy; no new branch or angular corrections',
        systematic_row=cfg.systematic_row,incoming_hkl=[list(h) for h in hkl],outgoing_hkl=[list(h) for h in hkl] if cfg.channeling_model=='double' else None,
        outgoing_energy='incident energy minus actual energy loss' if cfg.channeling_model=='double' else None,
        normalization=dict(raw_components='D_mag=M_A-M_B; D_nonmag=N_A-N_B (a.u.)',components_percent='100 * signed component / (N_A+N_B)',prb='100 * (I_A_plus-I_B_plus)/(I_A_plus+I_B_plus)'),
        precision='float64/complex128',reciprocal_convention='Crystallographic g=1/d (Å⁻¹); angular momentum transfer Q=2πg (Å⁻¹). Numerical values unchanged.',
        detector_evaluation='Full angular grid at selected L3/L2; nonzero fractional-aperture union at other energies' if cfg.angular_maps else 'Only nonzero fractional-aperture support on the unchanged grid; angular maps not calculated',
        angular_evaluation_policy=prepared.get('angular_evaluation_policy','legacy_full_grid_per_energy') if prepared is not None else 'legacy_full_grid_per_energy',
        angular_evaluation=prepared.get('diagnostics',[]) if prepared is not None else [],
        solver='Bloch-wave depth-integrated entrance-only localized single ionization',software_commit=commit,software_worktree_dirty=dirty,
        software_version=build['application_version'],software_display_version=build['display_version'],physics_convention=build['physics_convention'],
        implementation_sha256=build['implementation_sha256'],
        python=platform.python_version(),numpy=np.__version__,
        intensity_convention=('XMCD-effective; transverse source-maximum normalization; intensity in a.u.' if cfg.model=='xmcd' else 'Atomic length-gauge Å²/eV tensor; intensity in a.u.; no absolute cross-section calibration'),
        limitations='Projected IAM; '+('entrance-only, no outgoing channeling; ' if cfg.channeling_model=='single' else 'incoming and post-loss outgoing channeling; ')+ 'XMCD-effective is not full DFT MDFF; atomic non-DFT not quantitative Ni; arbitrary intensity units, no electron-count calibration; representative convergence controls do not certify all configurations.')
    stage('Preparing result visualizations')
    return dict(metadata=meta,model=model,settings=settings,config=cfg,maps=maps,spectra=spectra,qx=qx,qy=qy,weights=weights,coherence=C,depth_nm=z,amplitudes=psi)


def metrics(result):
    s=result['spectra'];rows={}
    from ..mdff_edges import selected_samples
    for edge,e in selected_samples(result['config']):
        i=int(np.argmin(abs(s['energy_ev']-e)));sigma=s['Sigma_ref'][i];floor=1e-10*max(float(s['Sigma_ref'].max()),1e-30)
        row={k:float(s[k][i]) if k in s else None for k in ('D_mag','D_nonmag','D_raw','D_corrected','magnetic_bias','D_nonmag_residual_obs','Sigma_ref')}
        row.update(A_mag=float(s['D_mag'][i]/sigma) if sigma>floor else None,A_nonmag=float(s['D_nonmag'][i]/sigma) if sigma>floor else None,alpha=result['metadata']['alpha'],energy_ev=float(s['energy_ev'][i]))
        rows[edge]=row
    return rows


def _export_single(result,path):
    from matplotlib.figure import Figure
    from .results import draw_maps,draw_eels
    root=Path(path);root.mkdir(parents=True,exist_ok=False)
    meta=dict(result['metadata'],edge_metrics=metrics(result))
    for name,value in (('input_parameters',dict(settings=meta['settings'],mdff=meta['mdff'],structure=meta['structure'])),('metadata',meta)):
        (root/(name+'.json')).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    np.savez_compressed(root/'virtual_detector_eels.npz',**result['spectra'])
    arrays=dict(qx=result['qx'],qy=result['qy'],coherence=result['coherence'],depth_nm=result['depth_nm'],amplitudes=result['amplitudes'])
    for edge,m in result['maps'].items():
        arrays.update({edge+'_'+k:v for k,v in m.items()})
        fig=Figure(figsize=(15,9),layout='constrained');draw_maps(fig,result,edge);fig.savefig(root/(edge+'_angular_maps.png'),dpi=145)
    arrays.update({'weight_'+k:v for k,v in result['weights'].items()});np.savez_compressed(root/'angular_maps.npz',**arrays)
    fig=Figure(figsize=(11,9),layout='constrained');draw_eels(fig,result);fig.savefig(root/'virtual_detector_eels.png',dpi=150)


def export_result(result,path,*,component_mode='raw',advanced=False,map_signal_mode=None):
    """One numerical bundle; raw and percentage spectra survive every display."""
    if advanced:
        _export_single(result,path)
        from .propagation import export_comparison
        export_comparison(result,Path(path),_export_single)
        return
    import csv
    from matplotlib.figure import Figure
    from .project_io import save_project
    from .results import draw_eels,draw_maps
    from .prb_benchmark import benchmark_spectra
    from .component_display import MODES,DEFINITIONS,exported_spectra,exported_angular
    if component_mode not in (*MODES,'relative'):raise ValueError('Unknown EMCD display mode')
    map_signal_mode=map_signal_mode or (component_mode if component_mode in MODES else 'raw')
    if map_signal_mode not in MODES:raise ValueError('Unknown angular signal display')
    root=save_project(result,path)
    derived={};unavailable={}
    methods=result.get('methods',{result.get('method','bloch'):result})
    for name,r in methods.items():
        spectra=dict(r['spectra'],**benchmark_spectra(r['spectra'])[0]);keys=list(spectra)
        with (root/(name+'_spectra.csv')).open('w',newline='',encoding='utf-8') as f:
            writer=csv.writer(f);writer.writerow(['solver','channeling_model']+keys)
            writer.writerows((name,r['config'].channeling_model,*values) for values in zip(*(spectra[k] for k in keys)))
        explicit=exported_spectra(r['spectra']);derived.update({name+'__'+k:v for k,v in explicit.items()})
        with (root/(name+'_signal_display.csv')).open('w',newline='',encoding='utf-8') as f:
            writer=csv.writer(f);writer.writerow(list(explicit));writer.writerows(zip(*explicit.values()))
        prefix='' if name==result.get('method','bloch') else name+'_'
        fig=Figure(figsize=(10,7),layout='constrained');draw_eels(fig,r,component_mode=component_mode)
        for ext in ('png','svg'):fig.savefig(root/(prefix+'virtual_detector_eels.'+ext),dpi=170)
        for edge in r['maps']:
            fig=Figure(figsize=(11,5),layout='constrained');draw_maps(fig,r,edge,signal_mode=map_signal_mode)
            try:derived.update({name+'__'+edge+'__'+k:v for k,v in exported_angular(r,edge).items()})
            except (ValueError,KeyError) as exc:unavailable[name+'__'+edge]=str(exc)
            for ext in ('png','svg'):fig.savefig(root/(prefix+edge+'_angular_maps.'+ext),dpi=170)
    derived['definitions_json']=np.array(json.dumps(DEFINITIONS))
    np.savez_compressed(root/'signal_display.npz',**derived)
    (root/'figure_display.json').write_text(json.dumps(dict(component_mode=component_mode,map_signal_mode=map_signal_mode,definitions=DEFINITIONS,unavailable_paired_maps=unavailable,
        note='Display only. CSV/NPZ retain signed raw components, both relative percentages, raw reversal spectra and denominators.',
        prb='Separate raw +M difference/sum; no factor two or post-edge correction'),indent=2)+'\n',encoding='utf-8')
