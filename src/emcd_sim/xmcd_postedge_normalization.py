"""Constant post-edge scaling and magnetic-recovery diagnostics; no simulations."""
from dataclasses import dataclass
import json
import numpy as np

WINDOWS = ((878.,882.), (874.,878.), (877.,881.))
EDGES = {"L3":(844.,862.), "L2":(864.,874.)}

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
