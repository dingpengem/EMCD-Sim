"""Read-only analysis of completed Milestone-A checkpoints."""
from pathlib import Path
import csv,hashlib,json
import numpy as np
from matplotlib.figure import Figure

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/general_zolz_multislice_validation'

def main():
    from emcd_sim.crystal import fcc_nickel
    from emcd_sim.projected_geometry import ProjectedGeometry
    cases={};rows=[];sampling={}
    for p in sorted(OUT.glob('*/case.json')):
        d=json.loads(p.read_text(encoding='utf-8'));arrays=p.with_name('arrays.npz')
        if not d.get('complete') or hashlib.sha256(arrays.read_bytes()).hexdigest()!=d['arrays_sha256']:raise ValueError('Incomplete or changed checkpoint: '+str(p))
        label=d['rows'][0]['case']
        if label in cases:raise ValueError('Multiple versions need explicit selection: '+label)
        cases[label]=d;rows.extend(d['rows'])
        settings=d['identity']['settings'];cfg=d['identity']['config']
        cell=ProjectedGeometry.from_crystal(fcc_nickel(),settings['zone'],settings['target'],generators=cfg['fft_generators'])
        sampling[label]=dict(status='Reconstructed geometry only from saved structure/settings; original case provenance untouched',
            fft_generators=cell.generators.tolist(),frame=cell.frame.tolist(),real_cell_xy_angstrom=cell.real_cell_xy.tolist(),
            area_angstrom2=cell.area_angstrom2,case_arrays_sha256=d['arrays_sha256'])
    keys=list(rows[0])
    with (OUT/'comparison.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
    np.savez_compressed(OUT/'comparison.npz',**{k:np.array([r[k] for r in rows]) for k in keys})
    comparisons={}
    raw_keys=('I_A_plus','I_B_plus','I_A_minus','I_B_minus')
    for name,d in cases.items():
        a,b=d['rows'][:2],d['rows'][2:]
        comparisons[name]=dict(prb_pp=max(abs(x['prb_pp']-y['prb_pp']) for x,y in zip(a,b)),
            magnetic_pp=max(abs(x['magnetic_pp']-y['magnetic_pp']) for x,y in zip(a,b)),
            relative_raw=max(abs(x[k]-y[k])/max(abs(x[k]),abs(y[k])) for x,y in zip(a,b) for k in raw_keys))
        v=comparisons[name];v['pass']=max(v['prb_pp'],v['magnetic_pp'])<=.01 and v['relative_raw']<=.001
    controls={};base=cases['111_double']['rows']
    for name in ('beam_low','beam_high','potential_low','potential_high','fft','slice','depth','angular'):
        other=cases['111_'+name]['rows']
        controls[name]=dict(prb_pp=max(abs(x['prb_pp']-y['prb_pp']) for x,y in zip(base,other)),
            magnetic_pp=max(abs(x['magnetic_pp']-y['magnetic_pp']) for x,y in zip(base,other)),
            relative_raw=max(abs(x[k]-y[k])/max(abs(x[k]),abs(y[k])) for x,y in zip(base,other) for k in raw_keys))
        v=controls[name];v['pass']=max(v['prb_pp'],v['magnetic_pp'])<=.01 and v['relative_raw']<=.001
    selected=['001_wide_single','001_wide_double']+[z+'_'+c for z in ('017','117','111','710') for c in ('single','double')]
    summary=dict(cases=len(cases),matched_comparisons=comparisons,independent_111_controls=controls,
        selected=selected,selected_bw_ms_pass=all(comparisons[n]['pass'] for n in selected),
        quantitative_convergence_claim=False,thresholds=dict(dichroism_pp=.01,relative_raw=.001),
        scope='2 nm, 200 kV, selected native edges; geometry/backend acceptance, not production numerical convergence')
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    (OUT/'sampling_metadata.json').write_text(json.dumps(sampling,indent=2),encoding='utf-8')
    fig=Figure(figsize=(12,6),layout='constrained');ax,other=fig.subplots(1,2)
    labels=[s.replace('_','\n') for s in selected];x=np.arange(len(selected))
    ax.bar(x,[comparisons[n]['prb_pp'] for n in selected]);ax.axhline(.01,color='red',ls='--',label='0.01 pp acceptance')
    ax.set(xticks=x,xticklabels=labels,ylabel='Maximum L3/L2 BW–MS PRB difference (pp)',title='Matched geometry and beam support; 2 nm')
    ax.tick_params(axis='x',labelsize=8);ax.legend(fontsize=8)
    names=list(controls);other.bar(np.arange(len(names)),[controls[n]['prb_pp'] for n in names])
    other.axhline(.01,color='red',ls='--');other.set(xticks=np.arange(len(names)),xticklabels=[n.replace('_','\n') for n in names],ylabel='Maximum PRB change from [111] baseline (pp)',title='Independent controls: failures retained')
    other.tick_params(axis='x',labelsize=8)
    fig.savefig(OUT/'validation.png',dpi=160);fig.savefig(OUT/'validation.svg')
    table=['| Case | BW/MS PRB (pp) | Magnetic (pp) | Raw relative | Gate |','|---|---:|---:|---:|---|']
    for n in selected:
        v=comparisons[n];table.append(f"| {n} | {v['prb_pp']:.6g} | {v['magnetic_pp']:.6g} | {v['relative_raw']:.6g} | {'PASS' if v['pass'] else 'FAIL'} |")
    table+=['','| [111] control vs baseline | PRB change (pp) | Raw relative | Gate |','|---|---:|---:|---|']
    for n,v in controls.items():table.append(f"| {n} | {v['prb_pp']:.6g} | {v['relative_raw']:.6g} | {'PASS' if v['pass'] else 'FAIL'} |")
    (OUT/'tables.md').write_text('\n'.join(table)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
