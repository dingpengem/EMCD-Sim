"""Raw-signal decomposition of the targeted [111] merge-review controls."""
from pathlib import Path
import csv,hashlib,json
import numpy as np
from matplotlib.figure import Figure
from emcd_sim.geometry import VirtualDetector
from emcd_sim.gui.project_io import load_project

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/generalized_multislice_merge_review'
OLD=ROOT/'outputs/generalized_multislice_emcd_validation/cases'
RAW=('I_A_plus','I_B_plus','I_A_minus','I_B_minus')

def records(r,label):
    cfg=r['config'];rows=[]
    for method,m in r['methods'].items():
        for edge,energy in [('L3',cfg.l3),('L2',cfg.l2)]:
            if m['maps']:
                dq2=float(r['qx'][0,1]-r['qx'][0,0])**2
                weights=[VirtualDetector(p,cfg.radius).integration_weights(r['qx'],r['qy'],mode='fractional',subpixels=128) for p in cfg.centers]
                fields=m['maps'][edge]
                ap,bp,am,bm=[float(np.sum(fields['I_'+sign]*w)*dq2) for sign in ('plus','minus') for w in weights]
            else:
                i=int(np.argmin(abs(m['spectra']['energy_ev']-energy)))
                ap,bp,am,bm=[float(m['spectra'][k][i]) for k in RAW]
            na,nb=(ap+am)/2,(bp+bm)/2;ma,mb=(ap-am)/2,(bp-bm)/2
            rows.append(dict(case=label,method=method,edge=edge,I_A_plus=ap,I_B_plus=bp,I_A_minus=am,I_B_minus=bm,
                N_A=na,N_B=nb,M_A=ma,M_B=mb,D_mag=ma-mb,D_nonmag=na-nb,Sigma_ref=na+nb,
                prb_pp=100*(ap-bp)/(ap+bp),magnetic_pp=100*(ma-mb)/(na+nb)))
    return {(r['method'],r['edge']):r for r in rows}

def compare(a,b):
    common=sorted(a.keys()&b.keys());worst=max((abs(a[k][field]-b[k][field])/max(abs(a[k][field]),abs(b[k][field])),k,field) for k in common for field in RAW)
    v=dict(prb_pp=max(abs(a[k]['prb_pp']-b[k]['prb_pp']) for k in common),
        magnetic_pp=max(abs(a[k]['magnetic_pp']-b[k]['magnetic_pp']) for k in common),relative_raw=worst[0],
        worst_raw=dict(method=worst[1][0],edge=worst[1][1],field=worst[2]),methods=sorted({k[0] for k in common}))
    v['pass']=bool(max(v['prb_pp'],v['magnetic_pp'])<=.01 and v['relative_raw']<=.001)
    return v

def main():
    cases=dict(base=OLD/'111_grid65/project',joint=OLD/'111_joint/project')
    for n in ('beam_only','potential_only','support_only','higher_basis_ms','higher_potential_ms'):cases[n]=OUT/'cases'/n/'project'
    data={k:records(load_project(p),k) for k,p in cases.items()}
    rows=[row for case in data.values() for row in case.values()]
    with (OUT/'comparison.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    np.savez_compressed(OUT/'comparison.npz',**{k:np.array([r[k] for r in rows]) for k in rows[0]})
    pairs=[('base','joint'),('base','beam_only'),('base','potential_only'),('base','support_only'),('support_only','joint'),
        ('joint','higher_basis_ms'),('higher_basis_ms','higher_potential_ms'),('joint','higher_potential_ms')]
    checks={a+'__'+b:compare(data[a],data[b]) for a,b in pairs}
    bw_ms={}
    for name,values in data.items():
        if {k[0] for k in values}=={'bloch','fft-multislice'}:
            a={('BW/MS',e):v for (m,e),v in values.items() if m=='bloch'}
            b={('BW/MS',e):v for (m,e),v in values.items() if m=='fft-multislice'}
            bw_ms[name]=compare(a,b)
    k=('fft-multislice','L2');field='I_A_plus';base=data['base'][k][field]
    value=lambda name:data[name][k][field]
    contributions=dict(beam=100*(value('beam_only')-base)/base,potential=100*(value('potential_only')-base)/base,
        support_interaction=100*(value('support_only')-value('beam_only')-value('potential_only')+base)/base,
        sampling=100*(value('joint')-value('support_only'))/base)
    summary=dict(checks=checks,bw_ms=bw_ms,worst_channel_signed_percent_contributions=contributions,
        support_fraction_of_original_change=(value('support_only')-base)/(value('joint')-base),
        thresholds=dict(relative_raw=.001,dichroism_pp=.01),scope='Ni [111], 200 kV, 2 nm, native L3/L2, fixed grid65/sub128 detectors',
        conclusion='Potential bandwidth and its interaction with finite beam support dominate. Final enlarged-MS increments pass; old lower-support joint comparison still fails. No universal or enlarged-BW certification.')
    (OUT/'analysis.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    table=['| Change | PRB (pp) | Magnetic (pp) | Raw change (%) | Gate |','|---|---:|---:|---:|---|']
    for name,v in checks.items():table.append(f"| {name.replace('__',' → ')} | {v['prb_pp']:.7g} | {v['magnetic_pp']:.7g} | {100*v['relative_raw']:.7g} | {'PASS' if v['pass'] else 'FAIL'} |")
    (OUT/'tables.md').write_text('\n'.join(table)+'\n',encoding='utf-8')
    fig=Figure(figsize=(11,4),layout='constrained');a,b=fig.subplots(1,2)
    names=list(contributions);a.bar(range(4),list(contributions.values()));a.set(xticks=range(4),xticklabels=['Beam','Potential','Support\ninteraction','FFT/depth/\nslice'],ylabel='Signed change (% of original intensity)',title='Worst channel: MS L2 A, +M')
    labels=['base__joint','joint__higher_basis_ms','higher_basis_ms__higher_potential_ms','joint__higher_potential_ms']
    b.bar(range(4),[100*checks[n]['relative_raw'] for n in labels]);b.axhline(.1,color='red',ls='--',label='0.1% gate')
    b.set(xticks=range(4),xticklabels=['Original\njoint','Larger\nMS basis','Higher\nMS potential','Final combined\nMS increment'],ylabel='Maximum raw-intensity change (%)',title='Unchanged acceptance threshold');b.legend(fontsize=8)
    fig.savefig(OUT/'sensitivity.png',dpi=160);fig.savefig(OUT/'sensitivity.svg')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
