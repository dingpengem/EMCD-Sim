"""Display-only raw/relative components from immutable reversal intensities."""
import numpy as np
from .prb_benchmark import benchmark_spectra,benchmark_readout
from .signal_normalization import divide_percent,MAP_FLOOR,EELS_FLOOR,validate_pair

MODES={'raw':'Raw (a.u.)','asymmetry':'EMCD Asymmetry (%)'}
TOOLTIPS={'raw':'Signed magnetic and nonmagnetic intensity differences.',
    'asymmetry':'Relative A/B intensity difference. May include nonmagnetic diffraction asymmetry.'}
DEFINITIONS=dict(schema=2,primary_total='100 * (I_A_plus-I_B_plus)/(I_A_plus+I_B_plus)',
    magnetic_only='100 * D_mag/(N_A+N_B)',nonmagnetic='100 * D_nonmag/(N_A+N_B)',
    angular='Actual saved (qx,qy)/(qx,-qy) point pairs; never average pixel percentages to obtain a detector asymmetry',
    legacy_alias={'emcd_asymmetry_percent':'prb_relative_dichroism_percent',
        'nonmagnetic_asymmetry_percent':'nonmagnetic_imbalance_percent'},
    intensity_units='Original signed a.u.; no count/SNR calibration')


def migrate_display_state(state):
    """Old Relative meant magnetic-only; never relabel it as total asymmetry."""
    out=dict(state);notes=[]
    if out.get('component_mode')=='relative':
        out.update(component_mode='raw',advanced=True,component_diagnostic='relative')
        notes.append('Legacy Relative EMCD preference opened as Magnetic-only / Nonmagnetic Asymmetry in Advanced Diagnostics; primary defaults to Raw.')
    if out.get('component_mode','raw') not in MODES:
        out['component_mode']='raw';notes.append('Unknown saved signal display reset to Raw.')
    out.setdefault('map_signal_mode','raw')
    if out['map_signal_mode'] not in MODES:out['map_signal_mode']='raw'
    out['signal_display_schema']=2
    return out,notes


def reversal_signals(ap,bp,am,bm,*,floor=EELS_FLOOR):
    """Pure post-processing of original samples; never normalize detectors."""
    ap,bp,am,bm=np.broadcast_arrays(*[np.asarray(v,float) for v in (ap,bp,am,bm)])
    na,nb=(ap+am)/2,(bp+bm)/2;ma,mb=(ap-am)/2,(bp-bm)/2
    magnetic,even=ma-mb,na-nb
    total,mask=divide_percent(ap-bp,ap+bp,floor,support=(ap>=0)&(bp>=0))
    support=(ap>=0)&(bp>=0)&(am>=0)&(bm>=0)
    mag,_=divide_percent(magnetic,na+nb,floor,support)
    nonmag,_=divide_percent(even,na+nb,floor,support)
    return dict(D_mag=magnetic,D_nonmag=even,D_raw=ap-bp,
        emcd_asymmetry_percent=total,magnetic_only_percent=mag,
        nonmagnetic_asymmetry_percent=nonmag,total_asymmetry_denominator=ap+bp,
        magnetic_asymmetry_denominator=na+nb),mask


def exported_spectra(spectra):
    """Add explicit aliases/denominators without replacing historical arrays."""
    legacy=benchmark_spectra(spectra)[0]
    out=dict(spectra,**legacy)
    out['emcd_asymmetry_percent']=legacy['prb_relative_dichroism_percent'].copy()
    out['total_asymmetry_denominator']=np.asarray(spectra['I_A_plus'])+np.asarray(spectra['I_B_plus'])
    if 'magnetic_only_percent' in legacy:
        out['nonmagnetic_asymmetry_percent']=legacy['nonmagnetic_imbalance_percent'].copy()
        out['magnetic_asymmetry_denominator']=(np.asarray(spectra['I_A_plus'])+spectra['I_A_minus'])/2+(np.asarray(spectra['I_B_plus'])+spectra['I_B_minus'])/2
    return out


def components(spectra,mode='raw'):
    if mode not in (*MODES,'relative'):raise ValueError('Choose Raw (a.u.) or EMCD Asymmetry (%)')
    ap,bp,am,bm=[np.asarray(spectra[k],float) for k in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus')]
    magnetic=np.asarray(spectra.get('D_mag',((ap-am)-(bp-bm))/2),float)
    nonmagnetic=np.asarray(spectra.get('D_nonmag',((ap+am)-(bp+bm))/2),float)
    if mode=='asymmetry':
        value=benchmark_spectra(spectra)[0]['prb_relative_dichroism_percent']
        return {'EMCD Asymmetry':value.copy()},dict(mode=mode,units=MODES[mode],
            denominator='I_A_plus(E) + I_B_plus(E)',definition='100 * (I_A_plus-I_B_plus)/(I_A_plus+I_B_plus)',
            includes_nonmagnetic=True,derived_visualization_only=True)
    if mode=='relative':
        curves,_=benchmark_spectra(spectra)
        magnetic,nonmagnetic=[curves[k] for k in ('magnetic_only_percent','nonmagnetic_imbalance_percent')]
    return dict(Magnetic=magnetic.copy(),Nonmagnetic=nonmagnetic.copy()),dict(
        mode=mode,units='Intensity difference (a.u.)' if mode=='raw' else 'Magnetic-only / Nonmagnetic Asymmetry (%)',
        denominator=None if mode=='raw' else 'N_A + N_B (one common denominator)',
        raw_definition='D_mag=M_A-M_B; D_nonmag=N_A-N_B; signed original intensities',
        derived_visualization_only=True)


def readouts(result):
    rows=[benchmark_readout(result,selection='selected',energy_ev=e) for e in (result['config'].l3,result['config'].l2)]
    fmt=lambda v:'undefined' if v is None else f'{v:+.4f}%'
    text='\n'.join(f"{r['selected_edge']} @ {r['evaluation_energy_ev']:.4f} eV: EMCD Asymmetry {fmt(r['prb_relative_dichroism_percent'])}" for r in rows)
    return rows,text


def primary_angular(result,edge,mode='raw'):
    """Actual qy-mirrored samples; not detector-integrated intensities."""
    if mode not in MODES:raise ValueError('Unknown primary angular signal display')
    if not getattr(result['config'],'angular_maps',True) or result.get('metadata',{}).get('angular_maps_calculated') is False:
        raise ValueError('Full-field angular maps were not calculated')
    if edge not in result['maps']:
        raise ValueError('Full-field angular maps are unavailable; genuine angular calculation required')
    qx,qy=np.asarray(result['qx']),np.asarray(result['qy'])
    if (qx.ndim!=2 or qy.shape!=qx.shape or not np.isfinite(qx).all() or not np.isfinite(qy).all()
        or not np.allclose(qx,qx[0:1],rtol=0,atol=1e-13)
        or not np.allclose(qy,qy[:,0:1],rtol=0,atol=1e-13)
        or np.any(np.diff(qx[0])<=0) or np.any(np.diff(qy[:,0])<=0)
        or not np.allclose(np.diff(qx[0]),np.diff(qx[0])[0],rtol=1e-12,atol=1e-13)
        or not np.allclose(np.diff(qy[:,0]),np.diff(qy[:,0])[0],rtol=1e-12,atol=1e-13)):
        raise ValueError('Paired angular display requires the stored regular increasing reciprocal coordinate grid')
    if not np.allclose(qy,-qy[::-1],rtol=0,atol=1e-13):
        raise ValueError('Insufficient actual mirrored reciprocal-space support')
    maps=result['maps'][edge];ap=np.asarray(maps['I_plus']);am=np.asarray(maps['I_minus'])
    if ap.shape!=qx.shape or am.shape!=qx.shape:raise ValueError('Angular reversal arrays do not match saved coordinates')
    if not np.isfinite(ap).all() or not np.isfinite(am).all():
        raise ValueError('Insufficient complete angular intensity support; genuine full-field calculation required')
    s,mask=reversal_signals(ap,ap[::-1],am,am[::-1],floor=MAP_FLOOR)
    values=({'Magnetic paired difference':s['D_mag'],'Nonmagnetic paired difference':s['D_nonmag']}
        if mode=='raw' else {'EMCD Asymmetry':s['emcd_asymmetry_percent']})
    meta=dict(mode=mode,units='Angular intensity difference (a.u.)' if mode=='raw' else MODES[mode],
        denominator=None if mode=='raw' else 'I_plus(qx,qy,E) + I_plus(qx,-qy,E)',
        pairing='Actual saved qy reflection; array[::-1]; independent of detector aperture locations',
        support='Full-field mirrored-point EMCD; full actual saved grid, not finite-aperture integrals',mask=mask,
        derived_visualization_only=True)
    return {k:np.array(v,copy=True) for k,v in values.items()},meta


def exported_angular(result,edge):
    # Validate before deriving; retained legacy D_* maps are never replaced.
    primary_angular(result,edge)
    m=result['maps'][edge];ap=np.asarray(m['I_plus']);am=np.asarray(m['I_minus'])
    s,_=reversal_signals(ap,ap[::-1],am,am[::-1],floor=MAP_FLOOR)
    names=dict(D_mag='paired_magnetic_difference',D_nonmag='paired_nonmagnetic_difference',
        D_raw='paired_total_difference',magnetic_only_percent='magnetic_only_paired_asymmetry_percent',
        nonmagnetic_asymmetry_percent='nonmagnetic_paired_asymmetry_percent')
    return {names.get(k,k):v for k,v in s.items()}


def mirrored_angular_components(result,edge):
    """Point-pair angular densities, distinct from finite-aperture integrals."""
    if edge not in result['maps']:raise ValueError('Angular maps were not calculated for this result')
    qx,qy=result['qx'],result['qy']
    if not np.allclose(qx,qx[::-1],rtol=0,atol=1e-13) or not np.allclose(qy,-qy[::-1],rtol=0,atol=1e-13):
        raise ValueError('Mirrored angular display requires the qy-reflection grid')
    m=result['maps'][edge];n=m['I_nonmag'];den=n+n[::-1]
    values={key:divide_percent(m[field]-m[field][::-1],den,MAP_FLOOR)[0]
            for key,field in (('Magnetic','I_mag'),('Nonmagnetic','I_nonmag'))}
    return values,dict(units='Mirrored angular component (%)',
        definition='100 * [component(qx,qy)-component(qx,-qy)] / [I_nonmag(qx,qy)+I_nonmag(qx,-qy)]',
        support='Full saved angular grid; point pairs, not finite-aperture A/B integrals',derived_visualization_only=True)
