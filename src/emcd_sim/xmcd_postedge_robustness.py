"""Targeted basis and one-control sampling checks for constant post-edge recovery."""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import platform
import subprocess

import numpy as np

from .crystal import fcc_nickel
from .elastic import BeamSet
from .wien2k_xmcd import load_wien2k_xmcd
from .xmcd_geometry_decomposition import _json_safe
from .xmcd_postedge_normalization import (
    LABEL, PostedgeConfig, _integral, analyze_postedge_spectra, run_postedge_simulation,
)

CORE_METRICS = ('alpha_obs','alpha_nonmag','nonmag_suppression','magnetic_amplitude_change',
                'corrected_relative_error','magnetic_integral_change','corrected_integral_change')
MODEL_FILES = ('benchmark.py','crystal.py','diffraction.py','elastic.py','physical_elastic.py',
    'scattering.py','geometry.py','simulation.py','single_channeling_tensor.py','mdff_tensor.py',
    'wien2k_xmcd.py','xmcd_effective_mdff.py','xmcd_reversal.py','xmcd_postedge_normalization.py')


def _canonical(value):
    return json.loads(json.dumps(value))


def _norm(signal, energy):
    return float(np.sqrt(max(_integral(np.asarray(signal)**2,energy),0.)))


def normalization_bias_diagnostics(result):
    """Oracle ratio is diagnostic only; retain three exact error contributions."""
    s=result.spectra
    floor=1e-12*float(np.max(abs(s['N_B'])))
    valid=np.isfinite(s['N_A']) & np.isfinite(s['N_B']) & (s['N_B']>floor)
    ratio=np.divide(s['N_A'],s['N_B'],out=np.full_like(s['N_A'],np.nan),where=valid)
    oracle=s['D_nonmag_residual_oracle'].copy()
    tail_bias=-(s['alpha_obs']-s['alpha_nonmag'])[:,None]*s['N_B'][None,:]
    scaling=s['D_mag_processed_obs']-s['D_mag'][None,:]
    error=s['D_corrected']-s['D_mag'][None,:]-oracle-tail_bias-scaling
    if not np.allclose(error,0,atol=1e-12*max(float(np.max(abs(s['I_A_plus']))),1e-30)):
        raise ArithmeticError('Three-term corrected/reference error identity failed')
    return dict(R_nonmag=ratio,valid_R_nonmag=valid,oracle_even_mismatch=oracle,
                postedge_magnetic_bias_even=tail_bias,magnetic_scaling_change=scaling,
                bias_identity_max_error=float(np.max(abs(error))),ratio_denominator_floor=floor)


def _run_id(config):
    return f'{config.condition}_cut{config.cutoff:g}_grid{config.grid}_steps{config.steps}'.replace('.','p')


def _load_or_run(source, config, output, source_hash, fingerprints, max_kernel_mib):
    folder=output/'runs'/_run_id(config)
    beams=BeamSet.zolz(fcc_nickel(),config.cutoff,config.max_beams)
    estimate=64.*config.grid**2*len(beams.hkl)**2/2**20
    if estimate>max_kernel_mib:
        raise ValueError(f'{_run_id(config)}: estimated pair arrays {estimate:.1f} MiB exceed memory guard')
    metadata_file=folder/'metadata.json'
    if metadata_file.exists():
        metadata=json.loads(metadata_file.read_text(encoding='utf-8'))
        if (metadata['config']!=_canonical(asdict(config)) or metadata['source_sha256']!=source_hash
                or metadata.get('simulation_file_sha256')!=fingerprints):
            raise ValueError(f'Checkpoint provenance/settings mismatch: {folder}; use a separate output directory')
        with np.load(folder/'spectra.npz',allow_pickle=False) as data:
            # Recompute all signal processing from immutable original detector spectra.
            result=analyze_postedge_spectra(data['energy_ev'],data['I_A_plus'],data['I_B_plus'],
                data['I_A_minus'],data['I_B_minus'],windows=config.postedge_windows,
                edge_windows={'L3':config.l3_window,'L2':config.l2_window})
        result.metadata.update(metadata)
        cached=True
    else:
        result=run_postedge_simulation(source,config)
        result.metadata['simulation_file_sha256']=fingerprints
        result.metadata['pair_array_estimate_mib']=estimate
        cached=False
    result.spectra.update(normalization_bias_diagnostics(result))
    if not cached:
        folder.mkdir(parents=True,exist_ok=True)
        np.savez_compressed(folder/'spectra.npz',**result.spectra)
        metadata_file.write_text(json.dumps(_json_safe(result.metadata),indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return result,cached


def comparison_rows(run_id, result):
    s=result.spectra; config=result.metadata['config']; rows=[]
    for source_row in result.comparisons:
        r=dict(run_id=run_id,condition=config['condition'],cutoff=config['cutoff'],
            beam_count=result.metadata['beam_count'],grid=config['grid'],steps=config['steps'],
            energy_points=config['energy_points'],integration_mode=config['integration_mode'],
            aperture_subpixels=config['aperture_subpixels'],**source_row)
        e=s['energy_ev']; lo,hi=r['analysis_start'],r['analysis_end']
        nodes=np.concatenate(([lo],e[(e>lo)&(e<hi)],[hi]))
        iw=r['window_index']
        for key in ('oracle_even_mismatch','postedge_magnetic_bias_even','magnetic_scaling_change'):
            r[key+'_norm']=_norm(np.interp(nodes,e,s[key][iw]),nodes)
        valid=s['valid_R_nonmag'] & (e>=lo) & (e<=hi)
        values=s['R_nonmag'][valid]
        r['R_nonmag_min']=float(values.min()) if len(values) else np.nan
        r['R_nonmag_max']=float(values.max()) if len(values) else np.nan
        r['ratio_valid_samples']=int(valid.sum())
        r['bias_identity_max_error']=s['bias_identity_max_error']
        rows.append(r)
    return rows


def compare_runs(left, right, control, metric_atol=.005):
    """Reject confounded comparisons; report absolute errors even near cancellation."""
    a,b=left.metadata['config'],right.metadata['config']
    changed={k for k in a if _canonical(a[k])!=_canonical(b[k])}
    if changed!={control}:
        raise ValueError(f'Comparison must change only {control}; changed {sorted(changed)}')
    if (left.metadata['source_sha256']!=right.metadata['source_sha256']
            or _canonical(left.metadata['tilt_mrad_xy'])!=_canonical(right.metadata['tilt_mrad_xy'])
            or not np.array_equal(left.spectra['energy_ev'],right.spectra['energy_ev'])):
        raise ValueError('Matched comparisons require identical source, physical tilt and energy grid')
    if len(left.comparisons)!=len(right.comparisons):
        raise ValueError('Comparison row counts do not match')
    changes=[]
    for ar,br in zip(left.comparisons,right.comparisons):
        if (ar['window_index'],ar['normalization'],ar['scope'])!=(br['window_index'],br['normalization'],br['scope']):
            raise ValueError('Comparison window/method/scope rows do not match')
        for key in CORE_METRICS:
            x,y=ar[key],br[key]; finite=bool(np.isfinite([x,y]).all())
            absolute=float(abs(x-y)) if finite else np.nan
            changes.append(dict(window_index=ar['window_index'],normalization=ar['normalization'],
                scope=ar['scope'],metric=key,absolute_difference=absolute,
                relative_difference=absolute/max(abs(x),abs(y)) if finite and max(abs(x),abs(y))>1e-8 else np.nan,
                exceeds_tolerance=bool(finite and absolute>metric_atol),valid=finite))
    e=left.spectra['energy_ev']
    absolute={k:_norm(right.spectra[k]-left.spectra[k],e) for k in ('D_raw','D_mag','D_nonmag')}
    ref=max(_norm(r.spectra['Sigma_ref'],e) for r in (left,right))
    return dict(condition=a['condition'],control=control,left_id=_run_id(PostedgeConfig(**a)),
        right_id=_run_id(PostedgeConfig(**b)),metric_absolute_tolerance=metric_atol,
        sensitive=any(c['exceeds_tolerance'] for c in changes),changes=changes,
        signal_norm_absolute_differences=absolute,
        signal_norm_differences_over_detector_sum={k:v/ref if ref>0 else np.nan for k,v in absolute.items()})


def summarize_robustness(runs, pairs):
    decisions={}
    for condition in sorted({r.metadata['condition'] for r in runs.values()}):
        related=[p for p in pairs if p['condition']==condition]
        basis=[p for p in related if p['control']=='cutoff']
        sampling=[p for p in related if p['control'] in ('grid','steps')]
        def status(group,label):
            if not group:return 'Insufficiently tested'
            return label if any(p['sensitive'] for p in group) else 'Stable within tested numerical/basis settings'
        results=[r for r in runs.values() if r.metadata['condition']==condition]
        primary=[next(x for x in r.comparisons if x['window_index']==0 and x['scope']=='full'
                      and x['normalization']=='obs') for r in results]
        pure=all(_norm(r.spectra['D_nonmag'],r.spectra['energy_ev'])<=
                 1e-10*_norm(r.spectra['Sigma_ref'],r.spectra['energy_ev']) for r in results)
        decisions[condition]=dict(basis_classification=status(basis,'Sensitive to diffraction-basis truncation'),
            sampling_classification=status(sampling,'Sensitive to detector/depth sampling'),
            sampling_controls_tested=sorted({p['control'] for p in sampling}),
            strong_suppression_with_substantial_scaling_change=all(np.isfinite(x['nonmag_suppression'])
                and x['nonmag_suppression']>.9 and abs(x['magnetic_amplitude_change'])>.05 for x in primary),
            original_even_difference_negligible=pure,
            normalization_introduces_even_residual=bool(pure and all(x['residual_nonmag_norm']>1e-10 for x in primary)),
            warning='Scaling changes the magnetic normalization convention; this is not a calibrated magnetic-moment loss')
    return decisions


def run_postedge_robustness(source, output, *, base=PostedgeConfig(), cutoffs=(1.2,1.4),
        conditions=('near-2bc','symmetric-3bc'), grid_check=97, depth_check=128,
        metric_atol=.005, max_kernel_mib=512.):
    """Small matched basis series plus separate near-2BC grid/depth checks.

    Saved spectra permit staged extension without repeating expensive forward
    runs; source, physical settings and simulation files must match exactly.
    """
    cuts=np.asarray(cutoffs,float)
    if (len(cuts)<2 or not np.isfinite(cuts).all() or np.any(cuts<=0) or np.any(np.diff(cuts)<=0)
            or base.cutoff not in cutoffs):
        raise ValueError('Require >=2 increasing positive cutoffs including the base cutoff')
    if not conditions or len(set(conditions))!=len(conditions) or any(c not in ('near-2bc','symmetric-3bc') for c in conditions):
        raise ValueError('Select unique near-2bc/symmetric-3bc conditions')
    if base.integration_mode!='fractional' or metric_atol<0 or not np.isfinite(metric_atol):
        raise ValueError('Require fractional integration and finite nonnegative metric tolerance')
    if not np.isfinite(max_kernel_mib) or max_kernel_mib<=0:
        raise ValueError('Memory guard must be finite positive')
    for value,minimum in ((grid_check,base.grid),(depth_check,base.steps)):
        if value is not None and (not isinstance(value,int) or value<=minimum):
            raise ValueError('Refinement must be an integer larger than the baseline')
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    source_hash=load_wien2k_xmcd(source).source_sha256
    package=Path(__file__).resolve().parent
    fingerprints={name:hashlib.sha256((package/name).read_bytes()).hexdigest() for name in MODEL_FILES}
    jobs=[replace(base,condition=c,cutoff=float(cut)) for c in conditions for cut in cutoffs]
    representative='near-2bc' if 'near-2bc' in conditions else conditions[0]
    reference=replace(base,condition=representative)
    if grid_check is not None:jobs.append(replace(reference,grid=grid_check))
    if depth_check is not None:jobs.append(replace(reference,steps=depth_check))
    runs,cached={},{}
    for config in jobs:
        run_id=_run_id(config)
        print(f'{run_id}: checking saved run or calculating spectra',flush=True)
        result,used_cache=_load_or_run(source,config,output,source_hash,fingerprints,max_kernel_mib)
        runs[run_id]=result; cached[run_id]=used_cache
        print(f'{run_id}: complete ({"saved spectra reused" if used_cache else "forward calculation"})',flush=True)
    pairs=[]
    for condition in conditions:
        for lower,upper in zip(cutoffs[:-1],cutoffs[1:]):
            pair=[runs[_run_id(replace(base,condition=condition,cutoff=float(c)))] for c in (lower,upper)]
            pairs.append(compare_runs(*pair,'cutoff',metric_atol))
    for control,value in (('grid',grid_check),('steps',depth_check)):
        if value is not None:
            pairs.append(compare_runs(runs[_run_id(reference)],runs[_run_id(replace(reference,**{control:value}))],control,metric_atol))
    rows=[row for run_id,r in runs.items() for row in comparison_rows(run_id,r)]
    try:
        root=package.parents[1]
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,stderr=subprocess.DEVNULL).decode().strip()
        dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=root).strip())
    except (OSError,subprocess.CalledProcessError):commit,dirty=None,None
    metadata=dict(base_config=asdict(base),cutoffs=list(cutoffs),conditions=list(conditions),
        grid_check=grid_check,depth_check=depth_check,metric_atol=metric_atol,max_kernel_mib=max_kernel_mib,
        source_sha256=source_hash,simulation_file_sha256=fingerprints,software_commit=commit,
        software_worktree_dirty=dirty,python_version=platform.python_version(),comparisons=pairs,
        classifications=summarize_robustness(runs,pairs),
        runs={key:dict(config=r.metadata['config'],beam_count=r.metadata['beam_count'],beam_hkl=r.metadata['beam_hkl'],
            energy_bounds_ev=r.metadata['actual_energy_bounds_ev'],metadata_path=f'runs/{key}/metadata.json',
            reused_saved_spectra=cached[key]) for key,r in runs.items()},
        physical_potential='Same existing untruncated Ni independent-atom potential, B=0; no Fourier-potential cutoff',
        diagnostic_ratio='N_A/N_B only where N_B>1e-12*max(abs(N_B)); not used to fit or correct spectra',
        bias_identity='D_corrected-D_mag = oracle_even_mismatch + postedge_magnetic_bias_even + magnetic_scaling_change',
        classification_policy='Any valid full/L3/L2 observed/oracle metric absolute change > metric_atol, in any tested window; no near-zero relative test',
        qualitative_policy='Strong suppression >90%, substantial magnetic norm scaling >5%; diagnostic choices, not physical accuracy bounds',
        scope='Matched numerical settings only; spectral sampling and global convergence unverified',
        absolute_cross_section=False,outgoing_channeling=False,quantitative_Ni=False,convergence_established=False)
    return rows,metadata,runs


def save_robustness(rows, metadata, output):
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    with (output/'robustness_comparison.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    (output/'robustness_metadata.json').write_text(json.dumps(_json_safe(metadata),indent=2,allow_nan=False)+'\n',encoding='utf-8')


def plot_robustness(rows,metadata,runs,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(len(metadata['conditions']),3,figsize=(12,4*len(metadata['conditions'])),squeeze=False,constrained_layout=True)
    for i,condition in enumerate(metadata['conditions']):
        for kind in ('obs','oracle'):
            data=[r for r in rows if r['condition']==condition and r['scope']=='full' and r['window_index']==0
                  and r['normalization']==kind and r['grid']==metadata['base_config']['grid'] and r['steps']==metadata['base_config']['steps']]
            data.sort(key=lambda r:r['cutoff'])
            for ax,key,title in zip(axes[i],('nonmag_suppression','magnetic_amplitude_change','corrected_relative_error'),
                ('Even norm suppression','Processed magnetic norm change','Corrected/reference norm error')):
                y=np.asarray([r[key] for r in data],float)
                ax.plot([r['beam_count'] for r in data],y,'o-',label=kind)
                if kind=='obs' and not np.isfinite(y).any():ax.text(.5,.4,'Undefined: negligible even reference',transform=ax.transAxes,ha='center',fontsize=8)
                ax.set_title(condition+'\n'+title,fontsize=10)
                ax.set(xlabel='2D ZOLZ beam count',xlim=(min(r['beam_count'] for r in data)-1,max(r['beam_count'] for r in data)+1));ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.suptitle(LABEL+'\nPrimary post-edge window; finite-basis comparison, no convergence certificate')
    fig.savefig(Path(output)/'postedge_basis_comparison.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(len(metadata['conditions']),3,figsize=(14,4*len(metadata['conditions'])),squeeze=False,constrained_layout=True)
    intervals=list(next(iter(runs.values())).metadata['edge_windows_ev'].items())
    for i,condition in enumerate(metadata['conditions']):
        selected=[r for r in runs.values() if r.metadata['condition']==condition]
        for r in selected:
            s=r.spectra;c=r.metadata['config'];label=f'g={c["cutoff"]:g}, q={c["grid"]}, z={c["steps"]}'
            for j,(edge,interval) in enumerate(intervals):
                ax=axes[i,j]
                e=s['energy_ev'];lo,hi=interval
                nodes=np.concatenate(([lo],e[(e>lo)&(e<hi)],[hi]))
                line,=ax.plot(nodes,np.interp(nodes,e,s['D_mag']),label=label,lw=.8)
                ax.plot(nodes,np.interp(nodes,e,s['D_corrected'][0]),color=line.get_color(),ls='--',lw=.9)
                ax.plot(nodes,np.interp(nodes,e,s['D_nonmag_residual_obs'][0]),color=line.get_color(),ls=':',lw=1.)
                ax.set(xlim=interval,title=condition+' | '+edge,xlabel='Energy (eV)',ylabel='Relative intensity')
                ax.grid(alpha=.2)
            ax=axes[i,2]
            ax.plot(s['energy_ev'],s['R_nonmag'],label=label+' N_A/N_B')
            ax.axhline(s['alpha_nonmag'][0],color='grey',lw=.5,ls=':')
            ax.set(title=condition+' | oracle ratio (diagnostic only)',xlabel='Energy (eV)',ylabel='N_A/N_B')
        if all(np.nanmax(r.spectra['R_nonmag'])-np.nanmin(r.spectra['R_nonmag'])<1e-10 for r in selected):
            axes[i,2].set_ylim(.999,1.001);axes[i,2].ticklabel_format(useOffset=False,axis='y')
        for ax in axes[i]:ax.legend(fontsize=6,ncol=1)
    fig.suptitle(LABEL+'\nSolid: unscaled magnetic reference; dashed: observed corrected; dotted: even residual')
    fig.savefig(Path(output)/'postedge_recovery_regions.png',dpi=150);plt.close(fig)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--xmcd-file',type=Path,required=True)
    p.add_argument('--output',type=Path,default=Path('outputs/ni_postedge_robustness'))
    p.add_argument('--cutoffs',type=float,nargs='+',default=[1.2,1.4])
    p.add_argument('--conditions',nargs='+',choices=('near-2bc','symmetric-3bc'),default=['near-2bc','symmetric-3bc'])
    for key,default in [('grid',65),('steps',64),('energy-points',185),('grid-check',97),('depth-check',128)]:
        p.add_argument('--'+key,type=int,default=default)
    p.add_argument('--baseline-cutoff',type=float,default=1.4)
    p.add_argument('--metric-atol',type=float,default=.005)
    p.add_argument('--max-kernel-mib',type=float,default=512.)
    p.add_argument('--skip-sampling',action='store_true')
    args=p.parse_args(argv)
    base=PostedgeConfig(cutoff=args.baseline_cutoff,grid=args.grid,steps=args.steps,energy_points=args.energy_points)
    try:
        rows,meta,runs=run_postedge_robustness(args.xmcd_file,args.output,base=base,cutoffs=tuple(args.cutoffs),
            conditions=tuple(args.conditions),grid_check=None if args.skip_sampling else args.grid_check,
            depth_check=None if args.skip_sampling else args.depth_check,metric_atol=args.metric_atol,max_kernel_mib=args.max_kernel_mib)
    except ValueError as exc:p.error(str(exc))
    save_robustness(rows,meta,args.output);plot_robustness(rows,meta,runs,args.output)
    print(json.dumps(_json_safe(dict(output=str(args.output),classifications=meta['classifications'])),indent=2,allow_nan=False))


if __name__=='__main__':main()
