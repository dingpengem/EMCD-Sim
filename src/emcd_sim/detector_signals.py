"""Physical aperture reduction, reversal observables and existing percentage masks.

reversal_components constructs the existing even/odd spectra; it performs no
normalization. integrate_detector_block reduces a bounded (energy,pixel) block
onto fixed fractional apertures and retains requested map planes. Raw saved
intensities, tensor units and elastic propagation remain outside this module.
"""
import numpy as np


def reversal_components(spectra, energy):
    """Return parity spectra on the supplied eV axis, preserving operation order.

    Each input I_{A,B}_{plus,minus} is (n_energy,) in relative intensity units.
    N=(I+ + I-)/2, M=(I+ - I-)/2; D_raw=D_mag+D_nonmag and
    Sigma_ref=N_A+N_B. Return new derived arrays without modifying raw inputs.
    """
    ap,bp,am,bm=[spectra[k] for k in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus')]
    na,nb,ma,mb=(ap+am)/2,(bp+bm)/2,(ap-am)/2,(bp-bm)/2
    return dict(energy_ev=energy,N_A=na,N_B=nb,M_A=ma,M_B=mb,
        D_mag=ma-mb,D_nonmag=na-nb,D_raw=ap-bp,Sigma_ref=na+nb)


def integrate_detector_block(raw,cfg,energy,qx,qy,weights,support):
    """Integrate a bounded spectral block with the existing fractional apertures.

    raw['plus'/'minus'] has axes (energy, supported flattened pixel); support
    selects from the original (qy,qx) map grid in cycles/Angstrom. cfg supplies
    angular_maps and selected_edges only. Restore zero-weight pixels before
    summation to retain the original reduction order, then multiply by dq^2.
    Maps are copies; the input intensity block and aperture weights are read-only
    to this operation. No source, propagation or Qt work belongs here.
    """
    dq2=(qx[0,1]-qx[0,0])**2
    full_weights=np.stack([weights[k].ravel() for k in ('A','B')])
    spectra={};maps={label:{} for label,_ in cfg.selected_edges} if cfg.angular_maps else {}
    for state in ('plus','minus'):
        plane=np.zeros((len(energy),qx.size))
        plane[:,support]=raw[state]
        integrated=np.sum(full_weights[None,:,:]*plane[:,None,:],axis=-1)*dq2
        for di,detector in enumerate(('A','B')):spectra[f'I_{detector}_{state}']=integrated[:,di]
        for label,loss in cfg.selected_edges if cfg.angular_maps else ():
            ie=int(np.flatnonzero(np.isclose(energy,loss,rtol=0,atol=1e-9))[0])
            maps[label]['I_'+state]=plane[ie].reshape(qx.shape).copy()
    for m in maps.values():
        m.update(I_mag=(m['I_plus']-m['I_minus'])/2,I_nonmag=(m['I_plus']+m['I_minus'])/2)
    spectra.update(reversal_components(spectra,energy))
    return dict(spectra=spectra,maps=maps,qx=qx,qy=qy,weights=weights)


POLICY = 'Positive finite denominator > relative floor times its positive finite 95th percentile; undefined values remain NaN.'


EELS_FLOOR = 1e-8


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


DEFINITION = '100 * (I_A_plus - I_B_plus) / (I_A_plus + I_B_plus); raw +M detectors; no factor 2, peak scaling or post-edge correction'


def relative_dichroism_percent(detector_a, detector_b):
    """Signed raw paired percentage; NaN for invalid or near-zero denominators."""
    a, b = np.broadcast_arrays(np.asarray(detector_a, float), np.asarray(detector_b, float))
    with np.errstate(over='ignore', invalid='ignore'):
        value, mask = divide_percent(a-b, a+b, EELS_FLOOR, support=(a >= 0) & (b >= 0))
    return value, dict(mask, definition=DEFINITION)


def benchmark_spectra(spectra):
    """Primary +M curve and separately labeled reversal diagnostics."""
    a, b = np.asarray(spectra['I_A_plus'], float), np.asarray(spectra['I_B_plus'], float)
    primary, mask = relative_dichroism_percent(a, b)
    curves = dict(prb_relative_dichroism_percent=primary)
    masks = dict(prb=mask)
    if all(k in spectra for k in ('I_A_minus', 'I_B_minus')):
        am, bm = np.asarray(spectra['I_A_minus'], float), np.asarray(spectra['I_B_minus'], float)
        if am.shape != a.shape or bm.shape != a.shape:
            raise ValueError('Reversal spectra must share the same saved energy sampling.')
        with np.errstate(over='ignore', invalid='ignore'):
            na, nb = (a+am)/2, (b+bm)/2
            ma, mb = (a-am)/2, (b-bm)/2
            support = (a >= 0) & (b >= 0) & (am >= 0) & (bm >= 0)
            curves['magnetic_only_percent'], masks['magnetic'] = divide_percent(ma-mb, na+nb, support=support)
            curves['nonmagnetic_imbalance_percent'], masks['even'] = divide_percent(na-nb, na+nb, support=support)
    return curves, masks
