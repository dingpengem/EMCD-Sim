"""Audit competing elastic reflections using saved full-basis mistilt waves."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from .diffraction import excitation_errors_angstrom_inv
from .ni_mistilt_series import (MistiltConfig, METHODS, model_for_offset, setup,
                               validate_checkpoint, write_json)


def two_beam_diagnostics(depth_nm, amplitudes, coherence, beam_hkl, outside):
    """Fractions of unit incident intensity; never normalize the retained basis."""
    pair=np.array([tuple(h) in ((0,0,0),(2,0,0)) for h in beam_hkl])
    if pair.sum()!=2:raise ValueError('Need both 000 and 200 in the full basis')
    intensity=abs(amplitudes)**2
    average=np.real(np.diag(coherence))
    trap=np.trapezoid if hasattr(np,'trapezoid') else np.trapz
    np.testing.assert_allclose(average,trap(intensity,x=depth_nm,axis=0)/depth_nm[-1],atol=1e-12)
    pair_depth=intensity[:,pair].sum(axis=1)
    competitors=intensity[:,~pair].sum(axis=1)
    np.testing.assert_allclose(pair_depth+competitors+outside,1.,atol=1e-10)
    return dict(pair_exit_fraction=float(pair_depth[-1]),pair_depth_average_fraction=float(average[pair].sum()),
        pair_min_sampled_fraction=float(pair_depth.min()),
        competing_common_exit_fraction=float(competitors[-1]),
        competing_common_depth_average_fraction=float(average[~pair].sum()),
        competing_total_max_sampled_fraction=float(np.max(competitors+outside)),
        outside_common_exit_fraction=float(outside[-1]),outside_common_max_sampled_fraction=float(outside.max()),
        outside_common_depth_average_fraction=float(trap(outside,x=depth_nm)/depth_nm[-1])),intensity,average


def audit(source,output):
    output=Path(output);main=json.loads((output/'mistilt_metadata.json').read_text())
    cfg=MistiltConfig(**main['config']);_,_,provenance=setup(source,cfg)
    if provenance['signature']!=main['provenance']['signature']:
        raise ValueError('Scientific configuration/source differs from the completed sweep')
    rows=[];summary=[];errors=[];waves=[];averages=[];maxima=[]
    for offset in cfg.offsets():
        path=output/'checkpoints'/f'{float(offset):+.6f}.npz'
        meta=json.loads(path.with_suffix('.json').read_text())
        if hashlib.sha256(path.read_bytes()).hexdigest()!=meta['npz_sha256']:
            raise ValueError('Checkpoint checksum mismatch')
        with np.load(path,allow_pickle=False) as f:data={k:f[k] for k in f.files}
        validate_checkpoint(data,meta,provenance['signature'],offset)
        model=model_for_offset(cfg,offset);hkl=model.elastic.beams.hkl
        s=excitation_errors_angstrom_inv(model.elastic);errors.append(s)
        method_waves=[];method_average=[];method_max=[]
        for method,key,ckey in zip(METHODS,('bw_amplitudes','ms_amplitudes_projected'),('coherence_bw','coherence_ms')):
            outside=np.zeros(len(data['depth_nm'])) if method=='bloch' else data['fft_outside_intensity']
            metrics,intensity,average=two_beam_diagnostics(data['depth_nm'],data[key],data[ckey],hkl,outside)
            summary.append(dict(delta_x_mrad=float(offset),method=method,
                theta_x_mrad=model.elastic.microscope.tilt_mrad_xy[0],theta_y_mrad=cfg.fixed_y_mrad,
                s200_inv_angstrom=float(s[hkl.index((2,0,0))]),**metrics))
            for j,h in enumerate(hkl):
                rows.append(dict(delta_x_mrad=float(offset),method=method,h=h[0],k=h[1],l=h[2],
                    s_g_inv_angstrom=float(s[j]),exit_intensity=float(intensity[-1,j]),
                    depth_average_intensity=float(average[j]),max_sampled_depth_intensity=float(intensity[:,j].max()),
                    target_pair=h in ((0,0,0),(2,0,0))))
            method_waves.append(intensity);method_average.append(average);method_max.append(intensity.max(axis=0))
        waves.append(method_waves);averages.append(method_average);maxima.append(method_max)
    for filename,records in (('competing_reflections.csv',rows),('two_beam_quality.csv',summary)):
        with (output/filename).open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
    waves=np.asarray(waves);averages=np.asarray(averages)
    np.savez_compressed(output/'elastic_mistilt_diagnostics.npz',delta_x_mrad=cfg.offsets(),
        beam_hkl=np.asarray(hkl),method_labels=np.asarray(METHODS),depth_nm=data['depth_nm'],
        excitation_error_inv_angstrom=np.asarray(errors),intensity=waves,
        depth_average_intensity=averages,max_sampled_depth_intensity=np.asarray(maxima))
    reference=np.where(np.isclose(cfg.offsets(),0.,rtol=0,atol=1e-12))[0]
    info=dict(reference_geometry='Off-zone (200) exact Bragg alignment, not [001] incidence; full finite 2D basis retained',
        beam_count=len(hkl),source_sha256=provenance['source_sha256'],signature=provenance['signature'],
        intensity_axes='mistilt, method, depth, beam',excitation_error_axes='mistilt, beam',
        intensity_normalization='Fractions of unit incident intensity; no retained-basis renormalization',
        depth_average='Same trapezoidal depth integral as the EMCD coherence; diagonal of C',
        sampled_maximum='Maximum on the saved depth samples, not a continuous-depth bound',
        summary=summary,propagation_recomputed=False,
        interpretation='s200=0 establishes exact Bragg excitation only. Assess two-beam dominance from pair/competitor intensities over depth, not only exit intensity or proximity of s_g to zero. No additional crystallographic minor-zone index is inferred.',
        limitations='Within the same Fourier-truncated projected [001] ZOLZ model; no full-potential, HOLZ, exit-channeling or convergence validation')
    if len(reference):
        ref=int(reference[0]);target=hkl.index((2,0,0))
        if abs(errors[ref][target])>1e-12:raise ArithmeticError('Reference is not at s200=0')
        ref_rows=[r for r in rows if abs(r['delta_x_mrad'])<1e-12]
        with (output/'reference_competing_reflections.csv').open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(ref_rows)
        info['reference_summary']=[r for r in summary if abs(r['delta_x_mrad'])<1e-12]
        plot_reference(output,hkl,data['depth_nm'],np.asarray(errors)[ref],waves[ref],averages[ref])
    write_json(output/'two_beam_readiness.json',info)
    print(json.dumps(info.get('reference_summary',summary),indent=2))


def plot_reference(output,hkl,depth,s,intensity,average):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    pair=[hkl.index(h) for h in ((0,0,0),(2,0,0))]
    competitors=[j for j in np.argsort(average[0])[::-1] if j not in pair][:10]
    indices=pair+competitors;labels=[str(hkl[j]) for j in indices];x=np.arange(len(indices))
    fig,axes=plt.subplots(2,2,figsize=(14,9),constrained_layout=True)
    for ax,values,title in ((axes[0,0],intensity[:,-1,:],'Exit elastic intensity'),
                             (axes[0,1],average,'Depth-averaged elastic intensity')):
        for method in range(2):ax.bar(x+(method-.5)*.36,100*values[method,indices],width=.36,label=METHODS[method])
        ax.set_xticks(x,labels,rotation=65,ha='right',fontsize=7)
        ax.set(title=title,ylabel='% of incident intensity');ax.legend(fontsize=8)
    axes[1,0].bar(x,s[indices]);axes[1,0].axhline(0,color='black',lw=.6)
    axes[1,0].set_xticks(x,labels,rotation=65,ha='right',fontsize=7)
    axes[1,0].set(title='Excitation errors of the displayed reflections',ylabel='s_g (inverse angstrom)')
    for method in range(2):
        p=intensity[method][:,pair].sum(axis=1)
        axes[1,1].plot(depth,100*p,ls='-' if method==0 else '--',label=METHODS[method]+' (000+200)')
        axes[1,1].plot(depth,100*(1-p),ls='-' if method==0 else '--',label=METHODS[method]+' all other modes')
    axes[1,1].set(xlabel='Depth (nm)',ylabel='% of incident intensity',title='Two-beam dominance through the specimen')
    axes[1,1].legend(fontsize=7)
    for ax in axes.flat:ax.grid(axis='y',alpha=.2)
    fig.suptitle('Off-zone Ni (200) reference: exact s200=0; full finite 2D propagation retained\n'
                 'Competitor list ranked by depth-average intensity; Fourier-truncated model, not convergence')
    fig.savefig(output/'two_beam_reference_diagnostics.png',dpi=160);plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=Path('data/wien2k_ni/Ni_fm.xmcd'))
    p.add_argument('--output',type=Path,default=Path('outputs/ni_continuous_mistilt'))
    args=p.parse_args();audit(args.source,args.output)
