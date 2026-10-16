"""Derived visualization only. Pure NumPy; no source reads or forward model."""
from dataclasses import dataclass, field
import numpy as np

MODES = {'raw': 'Raw (a.u.)', 'asymmetry': 'Asymmetry (%)', 'peak': 'EELS Peak (%)'}
MAP_MODES = {'raw': 'Raw (a.u.)', 'local': 'Local magnetic fraction (%)', 'paired': 'Paired angular asymmetry (%)'}
POLICY = 'Positive finite denominator > relative floor times its positive finite 95th percentile; undefined values remain NaN.'
EELS_FLOOR = 1e-8
MAP_FLOOR = 1e-6


@dataclass
class DisplaySettings:
    mode: str = 'raw'
    peak_edge: str = 'Auto'
    windows: dict = field(default_factory=dict)
    scope: str = 'shared'
    reference: int = 0
    map_mode: str = 'raw'
    shared_scale: bool = True


def scale95(a):
    a=np.asarray(a,float);positive=a[np.isfinite(a)&(a>0)]
    return float(np.percentile(positive,95)) if positive.size else 0.


def divide_percent(numerator, denominator, relative_floor=EELS_FLOOR, support=None):
    a,b=np.broadcast_arrays(np.asarray(numerator,float),np.asarray(denominator,float))
    floor=relative_floor*scale95(b)
    valid=np.isfinite(a)&np.isfinite(b)&(b>floor)&(b>0)
    if support is not None:valid &= np.broadcast_to(support,a.shape)
    out=np.full(a.shape,np.nan)
    with np.errstate(divide='ignore',invalid='ignore',over='ignore'):
        np.divide(a,b,out=out,where=valid);out*=100
    valid &= np.isfinite(out);out=np.where(valid,out,np.nan)
    return out,dict(policy=POLICY,relative_floor=relative_floor,absolute_floor=floor,valid_count=int(valid.sum()),undefined_count=int((~valid).sum()))


def sigma_even(spectra):
    if 'N_A' in spectra and 'N_B' in spectra:return np.asarray(spectra['N_A'])+np.asarray(spectra['N_B'])
    keys=('I_A_plus','I_A_minus','I_B_plus','I_B_minus')
    if all(k in spectra for k in keys):return sum(np.asarray(spectra[k]) for k in keys)/2
    if 'Sigma_ref' in spectra:return np.asarray(spectra['Sigma_ref'])
    raise ValueError('Saved spectra lack the reversal-even A+B reference.')


def default_windows(result):
    e=np.asarray(result['spectra']['energy_ev']);c=result['config'];mid=(c.l3+c.l2)/2
    if not e[0]<c.l3<mid<c.l2<e[-1]:raise ValueError('Saved edge energies must lie inside the native saved range.')
    width=min(5.,(c.l2-c.l3)/3)
    return {'L3':(max(float(e[0]),c.l3-width),min(mid,c.l3+width)),
            'L2':(max(mid,c.l2-width),min(float(e[-1]),c.l2+width))}


def peak_reference(result, edge, windows=None):
    s=result['spectra'];e=np.asarray(s['energy_ev'],float);sigma=sigma_even(s)
    windows=windows or default_windows(result)
    if edge not in ('L3','L2') or edge not in windows:raise ValueError('Choose an L3 or L2 peak window.')
    lo,hi=map(float,windows[edge]);c=result['config'];mid=(c.l3+c.l2)/2
    if not np.isfinite([lo,hi]).all() or not e[0]<=lo<hi<=e[-1]:raise ValueError('Peak window must lie inside the saved native spectral range.')
    if (edge=='L3' and hi>=mid) or (edge=='L2' and lo<=mid):raise ValueError('Peak window crosses the L3/L2 edge-region boundary.')
    mask=(e>=lo)&(e<=hi)&np.isfinite(sigma)
    if mask.sum()<2:raise ValueError('Peak window needs at least two finite saved energy samples.')
    ids=np.flatnonzero(mask);i=int(ids[np.argmax(sigma[ids])]);p=float(sigma[i])
    if not np.isfinite(p) or p<=0:raise ValueError('Peak reference must be finite and positive.')
    return dict(value=p,edge=edge,window_ev=[lo,hi],peak_energy_ev=float(e[i]),samples=int(mask.sum()),
                definition='max_E in window [N_A(E)+N_B(E)]; summed detectors, not their mean; no background subtraction or energy shift')


def selected_edge(settings,zoom='Full spectrum'):
    return settings.peak_edge if settings.peak_edge in ('L3','L2') else ('L2' if zoom=='L2 zoom' else 'L3')


def normalized_spectra(entries,settings=None,zoom='Full spectrum'):
    settings=settings or DisplaySettings();out=[];edge=selected_edge(settings,zoom)
    if not entries:return out
    reference=min(max(settings.reference,0),len(entries)-1)
    ref=entries[reference][1]
    digest=lambda r:r['config'].source_sha256 or (r['metadata'].get('source_audit') or {}).get('sha256')
    incompatible=lambda r:(r['config'].model!=ref['config'].model or
        (r['config'].model=='xmcd' and digest(r)!=digest(ref)) or
        r['metadata'].get('intensity_convention')!=ref['metadata'].get('intensity_convention'))
    if settings.mode=='peak' and settings.scope=='shared' and any(incompatible(r) for _,r,_ in entries):
        raise ValueError('Shared peak disabled across different models/source normalizations/units. Choose Per-run peaks for a qualitative overlay.')
    shared=peak_reference(entries[reference][1],edge,settings.windows) if settings.mode=='peak' and settings.scope=='shared' else None
    for label,r,method in entries:
        s=r['spectra'];derived={};meta=dict(mode=settings.mode,units='Relative intensity (a.u.)',
            reference_run=entries[reference][0] if shared else label,reference_method=entries[reference][2] if shared else method,
            scope=settings.scope,derived_visualization_only=True,mask_policy=POLICY)
        if settings.mode=='peak':
            own_windows=settings.windows or None
            # A foreign model/energy axis cannot inherit reference-run windows.
            # Explicit independent presentation uses each model's native defaults.
            foreign=incompatible(r) or abs(r['config'].l3-ref['config'].l3)>1e-8 or abs(r['config'].l2-ref['config'].l2)>1e-8
            if settings.scope!='shared' and foreign:own_windows=None
            peak=shared or peak_reference(r,edge,own_windows)
            meta.update(peak=peak,units=f'% of nonmagnetic {edge} EELS peak',
                warning='' if shared else 'Independently normalized — not suitable for raw BW/MS amplitude-difference evaluation; per-run/method peak can hide total-intensity changes.')
            if foreign:meta['window_note']='Qualitative independent overlay: this model uses its own native default edge windows.'
        elif settings.mode=='asymmetry':meta.update(units='% of Sigma_ref(E) = N_A(E)+N_B(E)',denominator='N_A(E)+N_B(E)')
        elif settings.mode!='raw':raise ValueError('Unknown spectral display mode')
        for key,a in s.items():
            if key=='energy_ev' or np.asarray(a).shape!=np.asarray(s['energy_ev']).shape:continue
            if settings.mode=='raw':derived[key]=np.array(a,copy=True)
            elif settings.mode=='peak':derived[key],_=divide_percent(a,peak['value'],0.)
            else:
                derived[key],mask=divide_percent(a,sigma_even(s));meta.setdefault('masks',{})[key]=mask
        out.append((derived,meta))
    return out


def validate_pair(result,edge):
    c=result['config'];qx,qy=np.asarray(result['qx']),np.asarray(result['qy'])
    centers=np.asarray(c.centers)
    if centers.shape!=(2,2) or not np.allclose(centers[0],centers[1]*[1,-1],rtol=0,atol=1e-12):raise ValueError('Paired percentages disabled: physical A/B apertures are not y mirrors.')
    if not np.allclose(qx,qx[::-1],rtol=0,atol=1e-13) or not np.allclose(qy,-qy[::-1],rtol=0,atol=1e-13):raise ValueError('Paired percentages require the validated qy reflection grid.')
    wa,wb=[np.asarray(result['weights'][k]) for k in ('A','B')]
    if not np.allclose(wa,wb[::-1],rtol=0,atol=1e-13) or np.any((wa>0)&(wb>0)) or not wa.any():raise ValueError('Paired aperture weights are not a nonoverlapping bijection.')
    if 'D_mag' not in result['maps'][edge]:raise ValueError(result['metadata'].get('pair_reason','Saved paired maps are unavailable.'))
    return wa>0


def angular_display(result,edge,key,mode='raw'):
    maps=result['maps'][edge]
    if key not in maps:raise ValueError('Requested saved map is unavailable.')
    if mode=='raw':return np.array(maps[key],copy=True),dict(units='Relative intensity (a.u.)',mode=mode)
    if mode=='local':
        if key!='I_mag':raise ValueError('Local magnetic fraction is defined only for intrinsic I_mag / I_nonmag; choose Magnetic odd.')
        value,meta=divide_percent(maps[key],maps['I_nonmag'],MAP_FLOOR)
        return value,dict(meta,mode=mode,units='Local magnetic fraction (%)',denominator='I_nonmag(q,E)',definition='100 I_mag(q,E) / I_nonmag(q,E)')
    if mode=='paired':
        if not key.startswith('D_'):raise ValueError('Paired percentage requires a paired D_* contrast, not an intrinsic intensity.')
        support=validate_pair(result,edge);n=maps['I_nonmag'];den=n+n[::-1]
        value,meta=divide_percent(maps[key],den,MAP_FLOOR,support)
        return value,dict(meta,mode=mode,units='Paired angular asymmetry (%)',denominator='I_nonmag(q,E)+I_nonmag(reflect_y(q),E)',support='Original fractional A support only; qy reflection is array[::-1].')
    raise ValueError('Peak-percent density maps are not supported: integrated EELS and angular-density units differ.')


def percentage_metrics(result,windows=None,reference_result=None):
    if reference_result is not None:
        a,b=result,reference_result
        digest=lambda r:r['config'].source_sha256 or (r['metadata'].get('source_audit') or {}).get('sha256')
        if (a['config'].model!=b['config'].model or
            (a['config'].model=='xmcd' and digest(a)!=digest(b)) or
            a['metadata'].get('intensity_convention')!=b['metadata'].get('intensity_convention')):
            raise ValueError('Shared scalar peak unavailable across different models/source normalizations/units.')
    s=result['spectra'];e=s['energy_ev'];sigma=sigma_even(s);rows={}
    for edge,energy in (('L3',result['config'].l3),('L2',result['config'].l2)):
        i=int(np.argmin(abs(e-energy)));row={};p=peak_reference(reference_result or result,edge,windows)
        for key in ('D_mag','D_nonmag','D_raw','D_corrected','D_mag_processed_obs','D_nonmag_residual_obs','magnetic_bias'):
            if key not in s:continue
            asym,_=divide_percent(s[key],sigma)
            row[key+'_asymmetry_percent']=float(asym[i]) if np.isfinite(asym[i]) else None
            row[key+'_peak_percent']=float(100*s[key][i]/p['value']) if np.isfinite(s[key][i]) else None
        legacy_den=float(s['I_A_plus'][i]+s['I_B_plus'][i]);legacy_floor=1e-10*max(float(np.max(s['Sigma_ref'])),1e-30)
        row.update(legacy_raw_plus_sum_percent=float(100*s['D_raw'][i]/legacy_den) if legacy_den>legacy_floor else None,
            legacy_definition='100 D_raw / (I_A_plus+I_B_plus), distinct from common-even asymmetry',
            peak_reference_intensity=p['value'],peak_energy_ev=p['peak_energy_ev'],peak_window_start_ev=p['window_ev'][0],peak_window_end_ev=p['window_ev'][1])
        rows[edge]=row
    return rows
