"""Figures and tables from completed uniform-basis validation only."""
import csv,json
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
import ni_double_channeling_uniform_basis as run


def main():
    root=run.ROOT
    status=json.loads((root/'status.json').read_text())
    with (root/'comparisons.csv').open(newline='') as f:rows=list(csv.DictReader(f))
    with (root/'observables.csv').open(newline='') as f:obs=list(csv.DictReader(f))
    fig=Figure(figsize=(10,7),layout='constrained');FigureCanvasAgg(fig)
    axes=fig.subplots(2,2)
    summary=[]
    for iz,zone in enumerate(('001','017')):
        for category,label,style in (('BW-MS','4.6','o-'),('independent_basis','bw','s--'),('independent_basis','ms','^:')):
            selected=[r for r in rows if r['zone']==zone and r['category']==category and r['label']==label]
            times=sorted(set(float(r['thickness_nm']) for r in selected))
            pp=[max(abs(float(r['prb_change_pp'])) for r in selected if float(r['thickness_nm'])==t) for t in times]
            raw=[100*max(float(r['raw_relative']) for r in selected if float(r['thickness_nm'])==t) for t in times]
            legend='BW–MS at 4.6' if category=='BW-MS' else label.upper()+' basis 3.8 → 4.6'
            axes[0,iz].plot(times,pp,style,label=legend)
            axes[1,iz].plot(times,raw,style,label=legend)
            worst=max(selected,key=lambda r:abs(float(r['prb_change_pp'])))
            summary.append(dict(zone=zone,category=category,label=label,max_prb_pp=max(pp),max_raw_percent=max(raw),
                worst_prb_thickness_nm=float(worst['thickness_nm']),worst_prb_channel=worst['channel'],worst_prb_edge=worst['edge']))
        axes[0,iz].axhline(.01,color='k',lw=.8);axes[1,iz].axhline(.1,color='k',lw=.8)
        axes[0,iz].set(title=f'Ni [{zone}]',ylabel='Maximum |PRB change| (pp)')
        axes[1,iz].set(xlabel='Thickness (nm)',ylabel='Maximum raw-state change (%)')
        for ax in axes[:,iz]:ax.grid(alpha=.2);ax.legend(fontsize=7)
    fig.savefig(root/'uniform_basis.png',dpi=180);fig.savefig(root/'uniform_basis.svg')
    run.study.base.study.base.write_csv(root/'summary.csv',summary)
    populations=[]
    for entry in json.loads((root/'checkpoint_manifest.json').read_text()):
        zone,t,basis,engine=entry['key']
        with np.load(entry['path'],allow_pickle=False) as f:
            incoming=f['incoming_exit'];outgoing=f['outgoing_depth_mean']
            explicit={tuple(h) for h in f['outgoing_hkl']}
            mask=np.array([tuple(h) in explicit for h in f['outgoing_population_hkl']])
            populations.append(dict(zone=zone,thickness_nm=t,basis=basis,engine=engine,
                incoming_exit_sum=float(incoming.sum()),incoming_depth_mean_sum=float(f['incoming_depth_mean'].sum()),
                incoming_exit_outside_basis=float(1-incoming.sum()) if engine=='ms' else 0.,
                incoming_depth_mean_outside_basis=float(1-f['incoming_depth_mean'].sum()) if engine=='ms' else 0.,
                outgoing_depth_population_sum_min=float(outgoing.sum(axis=-1).min()),
                outgoing_depth_population_outside_basis_max=float(outgoing[...,~mask].sum(axis=-1).max())))
    run.study.base.study.base.write_csv(root/'populations.csv',populations)
    lines=['# Uniform enlarged-basis validation','',
        f"Tested thicknesses: {status['thicknesses_nm']} nm. Uniform gate: **{'PASS' if status['uniform_gate_passed'] else 'FAIL'}**.",'',
        'Both edges, both reversal states, entrance and double channeling are included. Thresholds remain 0.01 percentage points in PRB dichroism and 0.1% in each raw detector state. Independent basis changes and BW/MS differences are separate tests.','',
        '|Geometry|Comparison|Maximum PRB change (pp)|Maximum raw change (%)|Worst PRB point|','|---|---|---:|---:|---|']
    for r in summary:lines.append(f"|[{r['zone']}]|{r['category']} {r['label']}|{r['max_prb_pp']:.8f}|{r['max_raw_percent']:.7f}|{r['worst_prb_thickness_nm']:g} nm, {r['worst_prb_channel']}, {r['worst_prb_edge']}|")
    lines+=['','## Sampled L3 ordering at beam cutoff 4.6','',
        '|Geometry|Engine|Thickness (nm)|Entrance PRB (%)|Double PRB (%)|','|---|---|---:|---:|---:|']
    for zone in ('001','017'):
        for engine in ('bw','ms'):
            for t in status['thicknesses_nm']:
                chosen=[r for r in obs if r['zone']==zone and r['method']==engine and r['edge']=='L3' and float(r['basis'])==4.6 and float(r['thickness_nm'])==t]
                values={r['channel']:float(r['prb_relative_dichroism_percent']) for r in chosen}
                lines.append(f"|[{zone}]|{engine.upper()}|{t:g}|{values['entrance']:.8f}|{values['double']:.8f}|")
    lines+=['','The entrance signal is strongest at 12 nm and the double-channeling signal at 8 nm among these sampled points, in both methods and geometries. The 8 nm double-channeling L3 magnitude remains about 13.06–13.23%. Outgoing channeling therefore preserves the observed redistribution of thickness dependence; these are not globally established maxima.','',
        'Recommended tested profile, conditional on the gate passing: potential cutoff 6.2, incoming/outgoing beam cutoff 4.6 cycles/angstrom, FFT 48, depth 257 and maximum split step 0.04 nm. This supports subsequent controlled validation using this profile, rather than certification of an existing full thickness or voltage series.','',
        '![Uniform basis convergence](uniform_basis.png)','',
        'Markers show the four tested thicknesses; joining lines guide the eye. Each ordinate is the maximum over both edges and both channeling treatments. Black lines mark the unchanged acceptance limits.','',
        'Raw states, magnetic differences, magnetic-only asymmetries and reversal-even imbalances are retained in observables.csv; signed changes are in comparisons.csv. No post-edge normalization or amplitude fitting is applied. The raw-state relative error is the maximum of abs(B-A)/max(abs(A),abs(B)) over A+/B+/A-/B-.','',
        'FFT support is checked by exact hkl lookup and reciprocal-coordinate equality for both incoming and outgoing event bases. MS propagation retains its full FFT modes; it is not artificially projected to the BW basis. populations.csv reports the populations outside the event basis without renormalization; incoming MS tails are inferred from unit norm minus the selected-basis populations, while outgoing tails are summed directly over the full FFT.','',
        'Settings: potential 6.2 cycles/angstrom, beam cutoffs 3.8 and 4.6, FFT 48 (the [001] invariant row uses its verified 1D reduction), 257 depth nodes, maximum split step 0.04 nm, 200 kV, original detectors and native 831.4778/848.698 eV energies. All tensors, phases, normalization and solver files are unchanged. Prior cutoff/FFT/slice/depth checks are inherited; they were not repeated at the enlarged basis.','',
        'This is a representative-point validation, not certification of the full 0–100 nm curve or global extrema. The 12 nm entrance and 8 nm double maxima are sampled observations. Absolute energy calibration, XMCD-effective rather than complete complex DFT MDFF, and the projected potential approximation remain unchanged limitations.','',
        'The 5.4 profile has 81 beams for [017]: the existing BW dense-memory estimate alone is 3284.2 MiB, before RSS, allocation margin and worker reserve, exceeding the unchanged 2048 MiB budget. No numerical settings or guards were reduced. No 5.4 calculation is needed if the requested 3.8-to-4.6 increment passes.','',
        'provenance.json records source SHA256, starting software commit, preserved prior-output hashes and thresholds; checkpoint_manifest.json identifies every reused/new checkpoint and its SHA256. comparison.npz retains full float64 raw states.']
    (root/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


if __name__=='__main__':main()
