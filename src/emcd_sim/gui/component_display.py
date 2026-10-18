"""Display-only raw/relative components from immutable reversal intensities."""
import numpy as np
from .prb_benchmark import benchmark_spectra,benchmark_readout
from .signal_normalization import divide_percent,MAP_FLOOR

MODES={'raw':'Raw EMCD (a.u.)','relative':'Relative EMCD (%)'}


def components(spectra,mode='raw'):
    if mode not in MODES:raise ValueError('Choose Raw EMCD (a.u.) or Relative EMCD (%)')
    ap,bp,am,bm=[np.asarray(spectra[k],float) for k in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus')]
    magnetic=np.asarray(spectra.get('D_mag',((ap-am)-(bp-bm))/2),float)
    nonmagnetic=np.asarray(spectra.get('D_nonmag',((ap+am)-(bp+bm))/2),float)
    if mode=='relative':
        curves,_=benchmark_spectra(spectra)
        magnetic,nonmagnetic=[curves[k] for k in ('magnetic_only_percent','nonmagnetic_imbalance_percent')]
    return dict(Magnetic=magnetic.copy(),Nonmagnetic=nonmagnetic.copy()),dict(
        mode=mode,units='EMCD intensity difference (a.u.)' if mode=='raw' else 'Relative EMCD (%)',
        denominator=None if mode=='raw' else 'N_A + N_B (one common denominator)',
        raw_definition='D_mag=M_A-M_B; D_nonmag=N_A-N_B; signed original intensities',
        derived_visualization_only=True)


def readouts(result):
    rows=[benchmark_readout(result,selection='selected',energy_ev=e) for e in (result['config'].l3,result['config'].l2)]
    fmt=lambda v:'undefined' if v is None else f'{v:+.4f}%'
    text='\n'.join(f"{r['selected_edge']} @ {r['evaluation_energy_ev']:.4f} eV: PRB {fmt(r['prb_relative_dichroism_percent'])}; magnetic {fmt(r['magnetic_only_percent'])}; nonmagnetic {fmt(r['nonmagnetic_imbalance_percent'])}" for r in rows)
    return rows,text


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
