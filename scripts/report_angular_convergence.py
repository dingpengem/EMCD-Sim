"""Report actual nested numerical maps; no propagation or interpolation."""
import csv,json
from pathlib import Path
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

ROOT=Path('outputs/angular_resolution_convergence')
FIELDS=('I_plus','I_minus','D_mag','D_nonmag','asymmetry')


def write_document(report):
    complete=report['complete']
    lines=['# Ni [017] angular-map convergence and historical source audit','',
        '**Status: '+('all six requested numerical maps completed.' if complete else '193-grid calculations in progress; this is an interim report.')+'**','',
        'Branch feat/full-field-emcd-thickness, task-start HEAD 737e3f9. Existing prepared work is preserved. No version change, Windows rebuild, broad release acceptance, push, merge or tag.','',
        '## Profile and actual samples','',
        'FCC Ni [017], full finite 2D ZOLZ, exact (200) Bragg; 200 kV, 8 nm, native L3 831.4778 eV, Double channeling. Both incoming/outgoing bases contain 59 beams at 4.6 inverse Angstrom; potential cutoff 6.2; FFT48, 257 depth nodes, maximum MS step 0.04 nm; float64/complex128; eta=beta=1. Crystal [001] magnetization is rotated into the original [017] local frame. Detector centers/radius, fractional weights and 64 subpixels are unchanged from the validated study. Only this one energy/thickness is propagated. The 4096 MiB resource budget does not alter physics.','',
        'The actual centered axis is (integer index minus 96)/192 cycles/Angstrom, from -0.5 to +0.5. The 33 and 97 grids are exact subsets of 193, with spacing 1/32, 1/96 and 1/192. This differs from linspace by at most floating-point roundoff, not by a physical geometry change. Actual common response samples are reused; no high-resolution values are interpolated from coarse data. Therefore common-point equality is expected by construction and is not an independent convergence test. Added sample extrema and detector quadrature provide the sampling test.','',
        'Each positive/zero qy direction is genuinely propagated. Negative qy Cartesian responses use the same exact crystal-mirror tensor transformation as the production reference, before contraction with each rotated magnetization tensor. This does not force symmetry of magnetized intensities or assume general nonmagnetic diffraction symmetry.','',
        'The saved-output inventory found 193-grid coordinate arrays in several older jobs, but the matching full-field intensity arrays were absent (angular_maps=false), or the job geometry/model differed. Those arrays cannot substitute for the requested full-field Double maps. The prior small Single 33/97 assessment is not this validated profile.','',
        '## Detector integration','',
        'For every state, sum fractional weight times raw intensity times dq squared before any ratio. A_raw uses the +M A+B denominator; A_mag and A_nonmag use the common reversal-even N_A+N_B denominator. These percentages need not add to A_raw. No pixelwise percentage averaging or post-edge normalization is used.','',
        '| Method | N | A_raw (%) | A_mag (%) | A_nonmag (%) | D_mag (a.u.) | D_nonmag (a.u.) | A area |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in report['detector_rows']:
        lines.append(f"| {r['method']} | {r['grid']} | {r['A_raw']:.11g} | {r['A_mag']:.11g} | {r['A_nonmag']:.6g} | {r['D_mag']:.11g} | {r['D_nonmag']:.6g} | {r['area_A']:.11g} |")
    lines+=['','| Method | Grid increment | Change A_raw (pp) | Change A_mag (pp) | Max relative raw-state change (%) |','|---|---|---:|---:|---:|']
    for r in report['successive_grid_changes']:
        lines.append(f"| {r['method']} | {r['low']} to {r['high']} | {r['detector_changes']['A_raw']:.10g} | {r['detector_changes']['A_mag']:.10g} | {100*max(r['raw_relative'].values()):.10g} |")
    lines+=['','These increments quantify grid sensitivity; the thickness-study BW/MS 0.01 pp agreement threshold is not applied as a grid-convergence gate. Effective circle areas and intensity-field quadrature are distinct convergence questions. All raw states and signed differences remain in detector_convergence.csv.','',
        '## Map extrema, features and solver comparison','',
        '| Method/grid | Observable | Minimum | Maximum | Maximum qx,qy | Valid/NaN |','|---|---|---:|---:|---|---|']
    for key,r in report['map_summaries'].items():
        for field in FIELDS:
            v=r[field];lines.append(f"| {key} | {field} | {v['minimum']:.10g} | {v['maximum']:.10g} | {v['maximum_q']} | {v['valid_count']}/{v['nan_count']} |")
    lines+=['','Intensity-supported diagnostics use pair denominator greater than 1% of its map maximum, separately from the unchanged primary map floor (1e-6 times positive finite 95th percentile). BW/MS comparisons include unweighted and supported maximum absolute error, relative L2 and intensity-weighted RMS. Relative errors of roundoff-level nonmagnetic components are explicitly undefined, not interpreted as physical discrepancies. Full diagnostics and actual sampled sign-change brackets, including exactly sampled zero axes, are in comparison.json. Fixed-domain trapezoid integrals are sampling diagnostics, never detector asymmetries.','',
        'The raw magnetic maximum lies on the qx=+0.5 boundary for the coarse/standard maps. It is a domain-limited extremum, not proof of a global angular optimum outside the displayed field. A_raw percentage extrema are also checked on signal support; percentages near tiny denominators are not the sole criterion. The reversal-even paired residual is near floating-point roundoff for this symmetric geometry, so its bright rescaled image colors must not be read as a large contamination signal.','',
        '| Grid | BW/MS maximum angular asymmetry difference (pp) | Supported maximum (pp) | Intensity-weighted RMS (pp) |','|---:|---:|---:|---:|']
    for r in report['bw_ms']:
        v=r['fields']['asymmetry'];lines.append(f"| {r['grid']} | {v['max_absolute']:.10g} | {v['supported_max_absolute']:.10g} | {v['intensity_weighted_rms']:.10g} |")
    lines+=['','## Runtime, memory and outputs','',
        'Initial profile chunks were retained, not rerun. Compatible coincident samples are reused across grids. Stage wall times below cover additional samples at each level; summed per-chunk times count concurrent workers and are not wall time. Methods ran concurrently, so stage times must not be summed as total elapsed wall time. Peak RSS is measured by 0.25-second sampling and can miss brief spikes; admission estimates are separate conservative bounds. Four MS workers and one BW worker retain the original numerical settings and active memory checks.','',
        '| Method | N | Additional stage wall seconds | Sampled process peak RSS (MiB) |','|---|---:|---:|---:|']
    for r in report['detector_rows']:lines.append(f"| {r['method']} | {r['grid']} | {r['stage_wall_seconds']:.3f} | {r['peak_sampled_rss_mib']:.3f} |")
    lines+=['','outputs/angular_resolution_convergence/ contains immutable response chunks, all six numerical NPZ maps when complete, comparison.npz/json, detector CSV, exact settings/provenance and runtime estimates. figures/ contains common-scale BW/MS maps, real sampling-point plots, solver differences and detector-convergence PNG/SVG. Source snapshot and the complete production metadata/hash audit are retained separately. Original 204 checkpoints are never overwritten.','',
        '## Recommendations and limitations','']
    if complete:
        last=[r for r in report['successive_grid_changes'] if r['high']==193]
        largest=max(abs(r['detector_changes']['A_raw']) for r in last)
        lines += [f'The tested 97-to-193 detector increment is at most {largest:.7g} pp. Standard 97 is a reasonable routine starting point for this measured geometry/thickness/energy at that observed sensitivity, not a universal accuracy guarantee. Preview 33 is useful for broad feature placement. Use 193 and an explicit convergence comparison for publication claims sensitive to fine extrema, boundaries or detector quadrature; a high preset alone does not certify publication-quality physics.']
        for r in last:
            field=r['extrema_changes'];s=report['map_summaries'][f"{r['method']}_193"]
            fraction=100*field['D_mag']['maximum']/s['D_mag']['maximum']
            lines += [f"For {r['method'].upper()}, 97-to-193 changes the angular asymmetry maximum by {field['asymmetry']['maximum']:.8g} pp and raw magnetic maximum by {fraction:.6g}%. Peak location shifts are {field['asymmetry']['maximum_location_shift']} cycles/Angstrom for asymmetry and {field['D_mag']['maximum_location_shift']} for the magnetic difference. I_plus/I_minus extrema are unchanged. These are actual added-node effects, not common-point interpolation errors."]
    else:lines+=['Keep the current Standard 97 default provisionally; do not claim its sampling convergence until the 193 comparison finishes.']
    lines+=['','The test covers one thickness and edge only. Basis/potential/FFT/depth convergence is inherited from limited representative studies, not re-established here. Approximate XMCD-constrained MDFF, no complete DFT transition tensor, projected IAM, existing longitudinal transfer and uncalibrated intensities remain. No experimental SNR or global optimum is inferred.','',
        '## Historical MS fingerprint','',
        'The exact historical SHA256 625fdc503711f06f3eeaad37893d9464fc108e4b47b8fa3dc9354d65a798d3df is recoverable from commit be8c3c34477f2a197646bf07f01a64d38fde1b33 by restoring two PowerShell CRLF boundaries with the UTF-8 BOM. The recovered source AST equals that committed historical source. Current MS hash is 1d6e84a7b3b0e27a0ebc88f5329f60cebd1a75c2a28f670e897845ee2750dba1.','',
        'Exact test: tests/test_ni_double_channeling_ms_validation.py::test_figures_source_and_previous_outputs_preserved. The recorded fingerprints are separate SHA256 values for scripts/ni_double_channeling_ms_validation.py, src/emcd_sim/multislice_double_channeling.py, src/emcd_sim/double_channeling.py and src/emcd_sim/multislice_reference.py. They are not a single combined hash. The old BW companion fingerprint also reconstructs exactly from its original committed source with CRLF. Every recorded fingerprint is preserved in historical_source_audit.json and the original output metadata.','',
        'Classification is mixed A/B: nonphysical encoding, optional signatures and cancellation changes; numerical multiplicity-weighted equivalent-site grouping and redundant default FCC selection. Oriented-potential support is an explicit extension outside the old cubic baseline. Existing four-thickness old/current raw reproduction differs by at most 5.56e-17 a.u.; an independent two-direction execution of exact recovered versus current MS differs by 2.45e-15 or less in Cartesian response. The current default AST must still match the pinned later validated baseline. These checks justify narrow compatibility, not a blanket claim that any hash change is harmless.','',
        'The historical test remains enabled, preserves its original expected hashes and now calls the narrow audit only for identified old MS/BW fingerprints. A deliberate qz sign mutation is rejected. Initial focused suite: 30 passed; three additional preparation/site/reflection equivalence tests passed; final completed-data/source checks: six passed. These selections overlap and must not be added as unique tests. The older broad release run is not repeated and release acceptance is not declared complete.','',
        'All changes remain uncommitted under the existing approval restriction. No attempt is made to bypass it; an explicit approval resolving that gate is still required for the pending commit.']
    Path('docs/ANGULAR_MAP_CONVERGENCE.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def read(method,n):
    with np.load(ROOT/f'{method}_{n}.npz',allow_pickle=False) as f:return {k:f[k].copy() for k in f.files}


def relative(a,b,scale):
    if np.linalg.norm(b)<=64*np.finfo(float).eps*scale:return float('nan')
    return float(np.linalg.norm(a-b)/np.linalg.norm(b))


def summarize(a):
    den=a['denominator'];signal=den>.01*np.max(den)
    result={}
    for name in FIELDS:
        v=a[name];valid=np.isfinite(v);support=valid&signal
        i=np.unravel_index(np.nanargmax(v),v.shape);j=np.unravel_index(np.nanargmin(v),v.shape)
        result[name]=dict(minimum=float(v[j]),minimum_q=[float(a['qx'][j]),float(a['qy'][j])],
            maximum=float(v[i]),maximum_q=[float(a['qx'][i]),float(a['qy'][i])],valid_count=int(valid.sum()),
            nan_count=int(np.isnan(v).sum()),signal_supported_min=float(v[support].min()),signal_supported_max=float(v[support].max()),
            fixed_domain_trapezoid_integral=float(np.trapezoid(np.trapezoid(v,a['qx'][0],axis=1),a['qy'][:,0],axis=0)))
    supported_mag=abs(a['D_mag'][signal]);nonmag=abs(a['D_nonmag'][signal])
    result['supported_nonmag_to_mag_L2']=float(np.linalg.norm(nonmag)/np.linalg.norm(supported_mag))
    result['mirror_asymmetry_error']=float(np.nanmax(abs(a['asymmetry']+a['asymmetry'][::-1])))
    result['sign_boundaries']={}
    for name in ('D_mag','asymmetry'):
        v=a[name];cuts={}
        for x in (0.,.25):
            ix=int(np.argmin(abs(a['qx'][0]-x)));values=v[:,ix];q=a['qy'][:,ix]
            cuts[str(x)]=[[float(q[i]),float(q[i+1])] for i in np.flatnonzero(values[:-1]*values[1:]<0)]
            cuts[str(x)]+=[[float(q[i]),float(q[i])] for i in range(1,len(q)-1) if values[i]==0 and values[i-1]*values[i+1]<0]
        result['sign_boundaries'][name]=cuts
    return result


def main():
    complete=all((ROOT/f'{m}_{n}.npz').exists() for m in ('bw','ms') for n in (33,97,193))
    records=[];grid_changes=[];solver=[];maps={};summaries={}
    for method in ('bw','ms'):
        ns=[n for n in (33,97,193) if (ROOT/f'{method}_{n}.npz').exists()]
        for n in ns:
            a=read(method,n);maps[method,n]=a;summaries[f'{method}_{n}']=summarize(a)
            record=dict(method=method,grid=n,**json.loads(str(a['detector_json'])),
                summed_chunk_elapsed_seconds=float(a['cumulative_cpu_chunk_seconds']),
                stage_wall_seconds=float(a['stage_wall_seconds']),peak_sampled_rss_mib=float(a['peak_sampled_rss_mib']))
            records.append(record)
        for low,high in zip(ns[:-1],ns[1:]):
            a,b=maps[method,low],maps[method,high];step=(high-1)//(low-1)
            np.testing.assert_array_equal(a['qx'],b['qx'][::step,::step]);np.testing.assert_array_equal(a['qy'],b['qy'][::step,::step])
            for name in FIELDS:
                np.testing.assert_array_equal(a[name],b[name][::step,::step])
            lo=next(r for r in records if r['method']==method and r['grid']==low);hi=next(r for r in records if r['method']==method and r['grid']==high)
            grid_changes.append(dict(method=method,low=low,high=high,
                extrema_changes={field:{'maximum':summaries[f'{method}_{high}'][field]['maximum']-summaries[f'{method}_{low}'][field]['maximum'],
                    'minimum':summaries[f'{method}_{high}'][field]['minimum']-summaries[f'{method}_{low}'][field]['minimum'],
                    'maximum_location_shift':(np.asarray(summaries[f'{method}_{high}'][field]['maximum_q'])-summaries[f'{method}_{low}'][field]['maximum_q']).tolist()}
                    for field in FIELDS},
                detector_changes={k:hi[k]-lo[k] for k in ('A_raw','A_mag','A_nonmag','D_mag','D_nonmag')},
                raw_relative={k:abs(hi[k]-lo[k])/max(abs(hi[k]),1e-300) for k in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus')},
                common_point_policy='Identical because actual point responses were reused, not evidence of independent propagation convergence. Extrema and detector quadrature test added samples.'))
    for n in (33,97,193):
        if ('bw',n) not in maps or ('ms',n) not in maps:continue
        b,m=maps['bw',n],maps['ms',n];den=b['denominator'];signal=den>.01*den.max();values={}
        for field in FIELDS:
            x,y=b[field],m[field];valid=np.isfinite(x)&np.isfinite(y);support=valid&signal
            delta=x-y
            values[field]=dict(relative_L2=relative(x[valid],y[valid],np.linalg.norm(m['I_plus'][valid])),max_absolute=float(abs(delta[valid]).max()),
                supported_max_absolute=float(abs(delta[support]).max()),
                intensity_weighted_rms=float(np.sqrt(np.sum(den[support]*delta[support]**2)/np.sum(den[support]))))
        solver.append(dict(grid=n,fields=values))
    if records:
        with (ROOT/'detector_convergence.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
        np.savez_compressed(ROOT/'comparison.npz',**{f'{method}_{n}__{field}':a[field] for (method,n),a in maps.items() for field in ('qx','qy')+FIELDS})
    figures=ROOT/'figures';figures.mkdir(exist_ok=True)
    reference_checks=[]
    if complete:
        from dataclasses import replace
        import ni_emcd_complete_thickness as baseline
        from emcd_sim.emcd_angular_plots import decorate_reciprocal_map
        from emcd_sim.geometry import VirtualDetector
        c=baseline.study.context('017',6.2,4.6)
        aliases,_=baseline.implementation_audit();production,rejected=baseline.inventory(baseline.contexts(),aliases)
        assert len(production)==204 and not rejected
        for method in ('bw','ms'):
            row=next(r for r in records if r['method']==method and r['grid']==193)
            actual=np.array([row[k] for k in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus')])
            expected=production['017',8,method]['raw'][1,0]
            np.testing.assert_allclose(actual,expected,rtol=2e-12,atol=1e-14)
            reference_checks.append(dict(method=method,max_absolute=float(abs(actual-expected).max()),
                reference=production['017',8,method]['path']))
        model=replace(c['model'],detectors={name:VirtualDetector(tuple(p),c['cfg'].radius) for name,p in zip(('A','B'),c['centers'])})
        def overlays(ax):
            decorate_reciprocal_map(ax,model,(-.5,.5,-.5,.5),target_hkl=(2,0,0),zone_axis=(0,1,7))
            g=model.elastic.crystal.g_vector((2,0,0))[:2]
            if np.any(abs(g)>.5):
                ax.text(.02,.02,f'(200) q=({g[0]:.3f},{g[1]:.3f}) outside view',transform=ax.transAxes,
                    fontsize=6,bbox=dict(facecolor='white',alpha=.8,edgecolor='none'))
        for method in ('bw','ms'):
            fig=Figure(figsize=(14,17),layout='constrained');FigureCanvasAgg(fig);axes=fig.subplots(5,3)
            for row,field in enumerate(FIELDS):
                pool=np.concatenate([maps[m,n][field].ravel() for m in ('bw','ms') for n in (33,97,193)]);limit=max(float(np.nanmax(abs(pool))),1e-30)
                for col,n in enumerate((33,97,193)):
                    ax=axes[row,col];a=maps[method,n];dq=a['qx'][0,1]-a['qx'][0,0]
                    im=ax.imshow(a[field],origin='lower',extent=(-.5-dq/2,.5+dq/2,-.5-dq/2,.5+dq/2),interpolation='nearest',
                        vmin=-limit if row>=2 else 0,vmax=limit,cmap='RdBu_r' if row>=2 else 'viridis')
                    im.cmap=im.cmap.with_extremes(bad='#aaa');ax.set(xlim=(-.5,.5),ylim=(-.5,.5),title=f'{field} | {n} x {n}',xlabel='qx (cycles/Angstrom)',ylabel='qy (cycles/Angstrom)')
                    overlays(ax)
                    fig.colorbar(im,ax=ax,shrink=.65).set_label('%' if field=='asymmetry' else 'a.u.')
            fig.suptitle(f'Ni [017] 8 nm Double L3 831.4778 eV | {method.upper()} | common scales per observable')
            for ext in ('png','svg'):fig.savefig(figures/f'{method}_maps.{ext}',dpi=130)
        fig=Figure(figsize=(13,4),layout='constrained');FigureCanvasAgg(fig);axes=fig.subplots(1,3)
        for ax,n in zip(axes,(33,97,193)):
            a=maps['bw',n];ax.scatter(a['qx'],a['qy'],s=.3);ax.set(title=f'{n} x {n}: {n*n} actual samples',xlabel='qx (cycles/Angstrom)',ylabel='qy (cycles/Angstrom)',aspect='equal')
        for ext in ('png','svg'):fig.savefig(figures/f'sampling_points.{ext}',dpi=130)
        fig=Figure(figsize=(12,8),layout='constrained');FigureCanvasAgg(fig);axes=fig.subplots(2,3).ravel()
        for ax,name in zip(axes,('A_raw','A_mag','D_mag','D_nonmag','I_A_plus','I_B_plus')):
            for method in ('bw','ms'):
                r=[r for r in records if r['method']==method];ax.plot([x['grid'] for x in r],[x[name] for x in r],marker='o',ls='-' if method=='bw' else '--',label=method.upper())
            ax.set(xlabel='Actual grid N',ylabel=name+(' (%)' if name.startswith('A_') else ' (a.u.)'));ax.ticklabel_format(axis='y',useOffset=False);ax.legend();ax.grid(alpha=.2)
        for ext in ('png','svg'):fig.savefig(figures/f'detector_convergence.{ext}',dpi=130)
        fig=Figure(figsize=(13,4),layout='constrained');FigureCanvasAgg(fig);axes=fig.subplots(1,3)
        for ax,n in zip(axes,(33,97,193)):
            a=maps['bw',n];b=maps['ms',n];v=a['asymmetry']-b['asymmetry'];limit=max(abs(r['fields']['asymmetry']['max_absolute']) for r in solver)
            dq=a['qx'][0,1]-a['qx'][0,0]
            im=ax.imshow(v,origin='lower',extent=(-.5-dq/2,.5+dq/2,-.5-dq/2,.5+dq/2),interpolation='nearest',vmin=-limit,vmax=limit,cmap='RdBu_r');ax.set_title(f'{n}: BW-MS asymmetry (pp)');fig.colorbar(im,ax=ax).set_label('pp')
            overlays(ax)
        for ext in ('png','svg'):fig.savefig(figures/f'bw_ms_difference.{ext}',dpi=130)
    report=dict(complete=complete,map_summaries=summaries,detector_rows=records,successive_grid_changes=grid_changes,bw_ms=solver,
        independent_production_integral_checks=reference_checks,
        signal_support_definition='Pair denominator >1% of map maximum, separate diagnostic from the existing primary 1e-6 percentile floor. No intensity renormalization.',
        scope='Single thickness/energy/geometry. No universal convergence threshold; no interpolation. Common-point equality is by compatible reuse.')
    (ROOT/'comparison.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(complete=complete,detectors=records,changes=grid_changes)),flush=True)
    write_document(report)


if __name__=='__main__':main()
