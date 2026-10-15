"""Constant post-edge normalization and model magnetic-recovery diagnostics."""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import platform
import subprocess

import numpy as np

from .benchmark import nickel_physical_benchmark
from .crystal import fcc_nickel
from .diffraction import select_diffraction_setup
from .elastic import BeamSet
from .wien2k_xmcd import load_wien2k_xmcd
from .xmcd_geometry_decomposition import GeometryDecompositionConfig, _json_safe
from .xmcd_reversal import run_xmcd_reversal

WINDOWS = ((878.,882.), (874.,878.), (877.,881.))
EDGES = {'L3':(844.,862.), 'L2':(864.,874.)}
LABEL = ('XMCD-constrained effective MDFF | entrance-only | relative intensity\n'
         'Not quantitatively validated Ni EMCD; reversal reference is model-only')


def _spectra(energy_ev, *signals):
    e = np.asarray(energy_ev, float)
    if e.ndim!=1 or len(e)<3 or not np.isfinite(e).all() or np.any(np.diff(e)<=0):
        raise ValueError('Energy must be finite, increasing and contain at least three samples')
    arrays = [np.asarray(s,float) for s in signals]
    if any(s.shape!=e.shape or not np.isfinite(s).all() for s in arrays):
        raise ValueError('Spectra must be finite 1D arrays matching the energy axis')
    return e, arrays


def _window_nodes(energy, window, min_samples=3):
    lo,hi = map(float,window)
    if not np.isfinite([lo,hi]).all() or lo>=hi or lo<energy[0] or hi>energy[-1]:
        raise ValueError('Window must be increasing and inside sampled/source coverage; no extrapolation')
    mask = (energy>=lo)&(energy<=hi)
    if int(mask.sum())<min_samples:
        raise ValueError(f'Window requires at least {min_samples} original energy samples')
    nodes = np.concatenate(([lo],energy[(energy>lo)&(energy<hi)],[hi]))
    return nodes,mask


def _integral(values, energy):
    return float(np.trapezoid(values,x=energy) if hasattr(np,'trapezoid') else np.trapz(values,x=energy))


def normalize_postedge(energy_ev, detector_a, detector_b, window, *, rtol=1e-12):
    """Fit alpha solely from the supplied A/B pair; no reversal reference used.

    Linearly interpolate only to exact window endpoints, then trapezoid both
    spectra on identical nodes. Reject near-zero/negative post-edge integrals.
    """
    e,(a,b) = _spectra(energy_ev,detector_a,detector_b)
    if not np.isfinite(rtol) or rtol<0:
        raise ValueError('Integral tolerance must be finite and nonnegative')
    nodes,mask = _window_nodes(e,window)
    ia,ib = [_integral(np.interp(nodes,e,s),nodes) for s in (a,b)]
    floor = rtol*max(float(np.max(abs(a))),float(np.max(abs(b))))*(nodes[-1]-nodes[0])
    if not np.isfinite([ia,ib]).all() or min(ia,ib)<=floor:
        raise ValueError('Post-edge integrals must be positive and nonnegligible relative to the spectra')
    alpha = ia/ib
    if not np.isfinite(alpha):
        raise ValueError('Invalid post-edge scale')
    return dict(alpha=alpha,difference=a-alpha*b,integral_A=ia,integral_B=ib,
                integral_floor=floor,window_mask=mask,integration_nodes_ev=nodes)


def recovery_diagnostics(energy_ev, magnetic, nonmagnetic, magnetic_processed,
                         nonmagnetic_residual, corrected, sigma_ref, *, window=None, rtol=1e-10):
    """Energy-weighted norms/correlations and signed integrals, without fitting.

    Relative metrics use a detector-sum norm/integral floor. Undefined values
    are NaN with an explicit reason, rather than fabricated percentages.
    """
    e,signals = _spectra(energy_ev,magnetic,nonmagnetic,magnetic_processed,
                         nonmagnetic_residual,corrected,sigma_ref)
    if not np.isfinite(rtol) or rtol<0:
        raise ValueError('Metric tolerance must be finite and nonnegative')
    nodes,_ = _window_nodes(e,(e[0],e[-1]) if window is None else window)
    mag,nonmag,processed,residual,corr,sigma = [np.interp(nodes,e,s) for s in signals]
    def norm(s): return np.sqrt(max(_integral(s*s,nodes),0.))
    mnorm,nnorm = norm(mag),norm(nonmag)
    floor = rtol*norm(sigma)
    ifloor = rtol*_integral(abs(sigma),nodes)
    metrics = dict(raw_nonmag_norm=float(nnorm),residual_nonmag_norm=float(norm(residual)),
        magnetic_reference_norm=float(mnorm),magnetic_processed_norm=float(norm(processed)),
        magnetic_reference_integral=_integral(mag,nodes),
        magnetic_processed_integral=_integral(processed,nodes),
        residual_nonmag_integral=_integral(residual,nodes))
    reasons = {}
    def ratio(key,num,den,threshold,reason,offset=0.):
        if abs(den)<=threshold or not np.isfinite([num,den]).all():
            metrics[key]=np.nan; reasons[key]=reason
        else:
            metrics[key]=float(num/den+offset)
    ratio('nonmag_suppression',-norm(residual),nnorm,floor,
          'Original nonmagnetic difference has negligible spectral norm',1.)
    ratio('magnetic_amplitude_ratio',norm(processed),mnorm,floor,
          'Magnetic reference has negligible spectral norm')
    ratio('magnetic_amplitude_change',norm(processed)-mnorm,mnorm,floor,
          'Magnetic reference has negligible spectral norm')
    ratio('magnetic_relative_error',norm(processed-mag),mnorm,floor,
          'Magnetic reference has negligible spectral norm')
    ratio('corrected_relative_error',norm(corr-mag),mnorm,floor,
          'Magnetic reference has negligible spectral norm')
    ratio('magnetic_projection_gain',_integral(processed*mag,nodes),mnorm*mnorm,floor*floor,
          'Magnetic reference has negligible spectral norm')
    ref_integral = metrics['magnetic_reference_integral']
    ratio('magnetic_integral_change',_integral(processed-mag,nodes),ref_integral,ifloor,
          'Signed reference integral is negligible or cancels over this interval')
    ratio('corrected_integral_change',_integral(corr-mag,nodes),ref_integral,ifloor,
          'Signed reference integral is negligible or cancels over this interval')
    centered = mag-_integral(mag,nodes)/(nodes[-1]-nodes[0])
    for key,s in [('magnetic_shape_correlation',processed),('corrected_shape_correlation',corr)]:
        shifted = s-_integral(s,nodes)/(nodes[-1]-nodes[0])
        x,y = norm(centered),norm(shifted)
        if x<=floor or y<=floor:
            metrics[key]=np.nan; reasons[key]='Centered magnetic reference or compared signal has negligible variance'
        else:
            metrics[key]=float(np.clip(_integral(centered*shifted,nodes)/(x*y),-1.,1.))
    return metrics,reasons


@dataclass
class PostedgeResult:
    spectra: dict
    comparisons: list[dict]
    metadata: dict


def analyze_postedge_spectra(energy_ev, I_A_plus, I_B_plus, I_A_minus, I_B_minus,
                            *, windows=WINDOWS, edge_windows=None):
    """Separate experimental constant scaling from oracle/reversal diagnostics."""
    e,arrays = _spectra(energy_ev,I_A_plus,I_B_plus,I_A_minus,I_B_minus)
    ap,bp,am,bm = [a.copy() for a in arrays]
    if not windows or len(set(map(tuple,windows)))!=len(windows):
        raise ValueError('Post-edge windows must be nonempty and unique')
    edges = dict(EDGES if edge_windows is None else edge_windows)
    for w in edges.values(): _window_nodes(e,w)
    na,nb,ma,mb = (ap+am)/2,(bp+bm)/2,(ap-am)/2,(bp-bm)/2
    magnetic,nonmagnetic = ma-mb,na-nb
    sigma = (ap+bp+am+bm)/2
    spectra = dict(energy_ev=e.copy(),I_A_plus=ap,I_B_plus=bp,I_A_minus=am,I_B_minus=bm,
        N_A=na,N_B=nb,M_A=ma,M_B=mb,D_raw=ap-bp,D_mag=magnetic,D_nonmag=nonmagnetic,
        Sigma_ref=sigma,valid_input=np.ones(e.shape,dtype=bool),postedge_windows_ev=np.asarray(windows,float))
    stacks = {k:[] for k in ('alpha_obs','alpha_nonmag','alpha_obs_minus','alpha_abs_difference',
        'alpha_relative_difference','D_corrected','D_oracle','D_nonmag_residual_obs',
        'D_mag_processed_obs','D_nonmag_residual_oracle','D_mag_processed_oracle',
        'I_B_plus_scaled_obs','I_B_plus_scaled_oracle','postedge_window_mask')}
    rows,window_info = [],[]
    for iw,window in enumerate(windows):
        observed = normalize_postedge(e,ap,bp,window)
        oracle = normalize_postedge(e,na,nb,window)
        negative = normalize_postedge(e,am,bm,window)
        ao,an = observed['alpha'],oracle['alpha']
        values = dict(alpha_obs=ao,alpha_nonmag=an,alpha_obs_minus=negative['alpha'],
            alpha_abs_difference=abs(ao-an),alpha_relative_difference=abs(ao-an)/abs(an),
            D_corrected=observed['difference'],D_oracle=ap-an*bp,
            D_nonmag_residual_obs=na-ao*nb,D_mag_processed_obs=ma-ao*mb,
            D_nonmag_residual_oracle=na-an*nb,D_mag_processed_oracle=ma-an*mb,
            I_B_plus_scaled_obs=ao*bp,I_B_plus_scaled_oracle=an*bp,
            postedge_window_mask=observed['window_mask'])
        errors = {}
        for kind,alpha,corrected in [('obs',ao,values['D_corrected']),('oracle',an,values['D_oracle'])]:
            resid,processed = values['D_nonmag_residual_'+kind],values['D_mag_processed_'+kind]
            error = float(np.max(abs(corrected-resid-processed)))
            if not np.allclose(corrected,resid+processed,rtol=1e-10,atol=1e-12*max(np.max(abs(ap)),np.max(abs(alpha*bp)))):
                raise ArithmeticError('Exact magnetic/nonmagnetic residual identity failed')
            errors[kind]=error
            for scope,interval in {'full':(float(e[0]),float(e[-1])),**edges}.items():
                metrics,reasons = recovery_diagnostics(e,magnetic,nonmagnetic,processed,resid,
                    corrected,sigma,window=interval)
                rows.append(dict(window_index=iw,postedge_start=float(window[0]),postedge_end=float(window[1]),
                    normalization=kind,scope=scope,analysis_start=float(interval[0]),analysis_end=float(interval[1]),
                    alpha_obs=ao,alpha_nonmag=an,alpha_obs_minus=negative['alpha'],
                    alpha_abs_difference=values['alpha_abs_difference'],
                    alpha_relative_difference=values['alpha_relative_difference'],
                    **metrics,undefined_reasons_json=json.dumps(reasons)))
        for key in stacks: stacks[key].append(values[key])
        window_info.append(dict(window_ev=list(window),original_sample_count=int(observed['window_mask'].sum()),
            integration_nodes_ev=observed['integration_nodes_ev'].tolist(),
            plus_integrals=[observed['integral_A'],observed['integral_B']],
            nonmag_integrals=[oracle['integral_A'],oracle['integral_B']],
            minus_integrals=[negative['integral_A'],negative['integral_B']],
            observed_integral_floor=observed['integral_floor'],reconstruction_max_abs_error=errors))
    spectra.update({k:np.asarray(v) for k,v in stacks.items()})
    for name in ('obs','nonmag','obs_minus'):
        spectra['valid_alpha_'+name]=np.isfinite(spectra['alpha_'+name])
    metric_names = list(metrics)
    spectra['metric_names']=np.asarray(metric_names)
    spectra['metric_values']=np.asarray([[r[k] for k in metric_names] for r in rows])
    spectra['metric_valid']=np.isfinite(spectra['metric_values'])
    spectra['metric_window_index']=np.asarray([r['window_index'] for r in rows])
    spectra['metric_normalization']=np.asarray([r['normalization'] for r in rows])
    spectra['metric_scope']=np.asarray([r['scope'] for r in rows])
    metadata = dict(postedge_windows=window_info,edge_windows_ev=edges,
        primary_window_index=0,integration='Exact endpoints by linear interpolation, identical trapezoidal quadrature',
        minimum_original_samples_per_window=3,postedge_integral_rtol=1e-12,recovery_metric_rtol=1e-10,
        metric_floor='Norm/integral relative to Sigma_ref in each analysis interval; centered norms for Pearson correlations',
        undefined_policy='NaN in NPZ/CSV, null in JSON, metric_valid mask and per-row undefined reasons',
        scale_policy='alpha_obs uses only plus A/B; oracle uses only reversal-even A/B; no fitted magnetic gain',
        relative_alpha_definition='abs(alpha_obs-alpha_nonmag)/abs(alpha_nonmag)',
        correlation_definition='Energy-weighted centered Pearson correlation; shape only, not amplitude fidelity')
    return PostedgeResult(spectra,rows,metadata)


@dataclass(frozen=True)
class PostedgeConfig:
    condition: str = 'near-2bc'
    cutoff: float = 1.4
    max_beams: int = 81
    acceleration_kv: float = 200.
    thickness_nm: float = 30.
    eta: float = 1.
    beta: float = 1.
    grid: int = 65
    steps: int = 64
    offzone_tilt_mrad: float = 25.
    integration_mode: str = 'fractional'
    aperture_subpixels: int = 64
    energy_start: float = 837.
    energy_end: float | None = None
    energy_points: int = 185
    postedge_windows: tuple[tuple[float,float], ...] = WINDOWS
    l3_window: tuple[float,float] = EDGES['L3']
    l2_window: tuple[float,float] = EDGES['L2']


def run_postedge_simulation(xmcd_file, config=PostedgeConfig()):
    """Lightweight wrapper of the existing reversal workflow, no kernel changes."""
    GeometryDecompositionConfig(conditions=(config.condition,),cutoff=config.cutoff,max_beams=config.max_beams,
        acceleration_kv=config.acceleration_kv,thickness_nm=config.thickness_nm,eta=config.eta,beta=config.beta,
        grid=config.grid,steps=config.steps,offzone_tilt_mrad=config.offzone_tilt_mrad,finer_grid=None,
        integration_mode=config.integration_mode,aperture_subpixels=config.aperture_subpixels).validate()
    if config.condition not in ('near-2bc','symmetric-3bc','zone-axis'):
        raise ValueError('Choose matched 2D near-2bc, symmetric-3bc or zone-axis geometry')
    source = load_wien2k_xmcd(xmcd_file)
    end = float(source.energy_ev[-1]) if config.energy_end is None else config.energy_end
    if (not np.isfinite([config.energy_start,end]).all() or not source.energy_ev[0]<=config.energy_start<end<=source.energy_ev[-1]
            or not isinstance(config.energy_points,int) or config.energy_points<3):
        raise ValueError('Require increasing spectral bounds within source and >=3 energy points')
    if not config.postedge_windows or len(set(map(tuple,config.postedge_windows)))!=len(config.postedge_windows):
        raise ValueError('Post-edge windows must be nonempty and unique')
    energies = np.linspace(config.energy_start,end,config.energy_points)
    for w in (*config.postedge_windows,config.l3_window,config.l2_window): _window_nodes(energies,w)
    beams = BeamSet.zolz(fcc_nickel(),config.cutoff,config.max_beams)
    if beams.hkl!=BeamSet.zolz(fcc_nickel(),config.cutoff,config.max_beams+2).hkl:
        raise ValueError('Beam cap clips the selected common 2D basis')
    setup = select_diffraction_setup(config.condition,fcc_nickel(),config.acceleration_kv,
                                     offzone_tilt_mrad=config.offzone_tilt_mrad)
    model = nickel_physical_benchmark(acceleration_kv=config.acceleration_kv,
        tilt_mrad_xy=setup.tilt_mrad_xy,beams_override=beams,diffraction_condition=config.condition)
    reversal = run_xmcd_reversal(model,xmcd_file,energies,eta=config.eta,beta=config.beta,
        thickness_nm=config.thickness_nm,grid_size=config.grid,depth_steps=config.steps,
        integration_mode=config.integration_mode,aperture_subpixels=config.aperture_subpixels)
    s = reversal.spectra
    result = analyze_postedge_spectra(energies,s['I_A_plus'],s['I_B_plus'],s['I_A_minus'],s['I_B_minus'],
        windows=config.postedge_windows,edge_windows={'L3':config.l3_window,'L2':config.l2_window})
    qx,qy = reversal.maps['L3']['qx_inv_angstrom'],reversal.maps['L3']['qy_inv_angstrom']
    tails = []
    for window in config.postedge_windows:
        nodes,_ = _window_nodes(source.energy_ev,window)
        tails.append(dict(window_ev=list(window),source_abs_M_over_N=
            _integral(np.interp(nodes,source.energy_ev,abs(source.dichroic)),nodes)/
            _integral(np.interp(nodes,source.energy_ev,source.nonmagnetic),nodes)))
    try:
        root=Path(__file__).resolve().parents[2]
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,stderr=subprocess.DEVNULL).decode().strip()
        dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=root).strip())
    except (OSError,subprocess.CalledProcessError): commit,dirty=None,None
    result.metadata.update(config=asdict(config),condition=config.condition,beam_hkl=beams.hkl,
        basis_kind='matched-2d-zolz',beam_count=len(beams.hkl),tilt_mrad_xy=setup.tilt_mrad_xy,
        detectors={k:dict(center_q_xy=d.center_q_xy,radius_q=d.radius_q,
            **d.integration_info(qx,qy,mode=config.integration_mode,subpixels=config.aperture_subpixels))
            for k,d in model.detectors.items()},chiral_groups=model.chiral_groups,
        source_sha256=source.source_sha256,xmcd_file=str(Path(xmcd_file).resolve()),
        source_energy_bounds_ev=[float(source.energy_ev[0]),float(source.energy_ev[-1])],
        actual_energy_bounds_ev=[float(energies[0]),float(energies[-1])],
        selected_edge_samples_ev={k:float(energies[np.argmin(abs(energies-v))]) for k,v in [('L3',852.7),('L2',870.)]},
        source_postedge_tails=tails,tensor_sources=reversal.tensor_sources,software_commit=commit,
        software_worktree_dirty=dirty,python_version=platform.python_version(),model=LABEL,
        absolute_cross_section=False,outgoing_channeling=False,quantitative_Ni=False,
        extended_continuum=False,experimental_background_subtraction=False,
        normalization_model='One energy-independent factor per detector pair/window',
        limitations='Finite ZOLZ and depth/aperture sampling; limited post-edge with nonzero XMCD; shared effective tensor, no quantitative moment inference')
    return result


def save_postedge_result(result, output):
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(output/'postedge_spectra.npz',**result.spectra)
    with (output/'postedge_window_comparison.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(result.comparisons[0])); writer.writeheader(); writer.writerows(result.comparisons)
    (output/'postedge_metrics.json').write_text(json.dumps(_json_safe(result.comparisons),indent=2,allow_nan=False)+'\n',encoding='utf-8')
    (output/'metadata.json').write_text(json.dumps(_json_safe(result.metadata),indent=2,allow_nan=False)+'\n',encoding='utf-8')


def plot_postedge_result(result, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    s=result.spectra; e=s['energy_ev']; condition=result.metadata.get('condition','synthetic spectra')
    window=s['postedge_windows_ev'][0]; desc=f'{condition}; primary post-edge {window[0]:g}-{window[1]:g} eV'
    fig,axes=plt.subplots(3,2,figsize=(12,10),constrained_layout=True)
    panels=[[(s['I_A_plus'],'Original A+'),(s['I_B_plus'],'Original B+')],
            [(s['I_A_plus'],'Original A+'),(s['I_B_plus_scaled_obs'][0],'Observed alpha times B+')],
            [(s['D_raw'],'Raw A+-B+'),(s['D_corrected'][0],'Observed corrected')],
            [(s['D_corrected'][0],'Observed corrected'),(s['D_oracle'][0],'Oracle corrected'),(s['D_mag'],'Reversal-odd reference')],
            [(s['D_nonmag'],'Original even difference'),(s['D_nonmag_residual_obs'][0],'Observed residual even'),
             (s['D_nonmag_residual_oracle'][0],'Oracle residual even')],
            [(s['D_mag'],'Original magnetic reference'),(s['D_mag_processed_obs'][0],'Observed processed magnetic'),
             (s['D_mag_processed_oracle'][0],'Oracle processed magnetic')]]
    for ax,lines in zip(axes.flat,panels):
        for values,label in lines: ax.plot(e,values,label=label)
        ax.axvspan(*window,color='grey',alpha=.15); ax.legend(fontsize=7)
        ax.set(xlabel='Energy loss (eV)',ylabel='Relative intensity'); ax.grid(alpha=.2)
    fig.suptitle(LABEL+'\n'+desc); fig.savefig(output/'postedge_normalization_comparison.png',dpi=150); plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,4),constrained_layout=True)
    for ax,(edge,interval) in zip(axes,result.metadata['edge_windows_ev'].items()):
        for key,label in [('D_mag','Original magnetic reference'),('D_corrected','Observed corrected'),
                          ('D_mag_processed_obs','Observed processed magnetic'),('D_nonmag_residual_obs','Residual even')]:
            ax.plot(e,s[key] if s[key].ndim==1 else s[key][0],label=label)
        ax.set(xlim=interval,xlabel='Energy loss (eV)',ylabel='Relative intensity',title=f'{edge} integration {interval[0]:g}-{interval[1]:g} eV')
        ax.legend(fontsize=7); ax.grid(alpha=.2)
    fig.suptitle(LABEL+'\n'+desc); fig.savefig(output/'magnetic_recovery_comparison.png',dpi=150); plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(11,7),constrained_layout=True)
    wlabels=[f'{a:g}-{b:g}' for a,b in s['postedge_windows_ev']]; x=np.arange(len(wlabels))
    for key in ('alpha_obs','alpha_nonmag','alpha_obs_minus'):axes[0,0].plot(x,s[key],'o-',label=key)
    for kind in ('obs','oracle'):
        rows=[r for r in result.comparisons if r['normalization']==kind and r['scope']=='full']
        for ax,key in [(axes[0,1],'nonmag_suppression'),(axes[1,0],'magnetic_amplitude_change'),(axes[1,1],'corrected_relative_error')]:
            ax.plot(x,[r[key] for r in rows],'o-',label=kind)
            titles={'nonmag_suppression':'Nonmagnetic norm suppression',
                    'magnetic_amplitude_change':'Processed magnetic norm change',
                    'corrected_relative_error':'Corrected/reference relative norm error'}
            ax.set_title(titles[key]+' (full spectrum)',fontsize=10)
    for ax in axes.flat:
        if ax.lines and not any(np.isfinite(np.asarray(line.get_ydata(),dtype=float)).any() for line in ax.lines):
            ax.text(.5,.5,'Undefined: reference is negligible\n(see saved metric reasons)',
                    transform=ax.transAxes,ha='center',va='center',fontsize=9)
        ax.set_xticks(x,wlabels); ax.set_xlabel('Post-edge window (eV)'); ax.legend(fontsize=8); ax.grid(alpha=.2)
    fig.suptitle(LABEL+'\n'+condition); fig.savefig(output/'normalization_window_sensitivity.png',dpi=150); plt.close(fig)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--xmcd-file',type=Path,required=True)
    p.add_argument('--output',type=Path,default=Path('outputs/ni_postedge_normalization'))
    p.add_argument('--condition',choices=('near-2bc','symmetric-3bc','zone-axis','all'),default='near-2bc')
    for key,default in [('postedge-start',878.),('postedge-end',882.),('thickness-nm',30.),
        ('cutoff',1.4),('acceleration-kv',200.),('eta',1.),('beta',1.),('offzone-tilt-mrad',25.),
        ('energy-start',837.),('l3-start',844.),('l3-end',862.),('l2-start',864.),('l2-end',874.)]:
        p.add_argument('--'+key,type=float,default=default)
    p.add_argument('--energy-end',type=float)
    p.add_argument('--comparison-window',type=float,nargs=2,action='append',help='Additional post-edge window; repeat to replace default sensitivity candidates')
    for key,default in [('grid',65),('steps',64),('max-beams',81),('energy-points',185),('aperture-subpixels',64)]:
        p.add_argument('--'+key,type=int,default=default)
    p.add_argument('--integration-mode',choices=('fractional','binary'),default='fractional')
    args=vars(p.parse_args(argv)); source,output=args.pop('xmcd_file'),args.pop('output')
    window=(args.pop('postedge_start'),args.pop('postedge_end'))
    extra=args.pop('comparison_window'); candidates=WINDOWS if extra is None else extra
    args['postedge_windows']=tuple(dict.fromkeys((window,*(tuple(w) for w in candidates))))
    args['l3_window']=(args.pop('l3_start'),args.pop('l3_end'))
    args['l2_window']=(args.pop('l2_start'),args.pop('l2_end'))
    condition=args.pop('condition')
    for name in (('near-2bc','symmetric-3bc') if condition=='all' else (condition,)):
        try:result=run_postedge_simulation(source,PostedgeConfig(condition=name,**args))
        except ValueError as exc:p.error(str(exc))
        folder=output/name; save_postedge_result(result,folder); plot_postedge_result(result,folder)
        summary=next(r for r in result.comparisons if r['window_index']==0 and r['normalization']=='obs' and r['scope']=='full')
        print(json.dumps(_json_safe(dict(condition=name,postedge_window=window,alpha_obs=summary['alpha_obs'],
            alpha_nonmag=summary['alpha_nonmag'],nonmag_suppression=summary['nonmag_suppression'],
            magnetic_amplitude_change=summary['magnetic_amplitude_change'],
            corrected_relative_error=summary['corrected_relative_error'],output=str(folder))),allow_nan=False))


if __name__=='__main__':main()
