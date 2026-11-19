"""Physical aperture reduction and reversal-derived detector observables.

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
