"""Saved-data before/after analysis only; no scattering calculations."""
from pathlib import Path
import csv
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/physics_convention_correction_acceptance'


def metrics(raw):
    ap,bp,am,bm=raw
    na,nb=(ap+am)/2,(bp+bm)/2;ma,mb=(ap-am)/2,(bp-bm)/2
    v=dict(I_A_plus=ap,I_B_plus=bp,I_A_minus=am,I_B_minus=bm,N_A=na,N_B=nb,
        M_A=ma,M_B=mb,D_mag=ma-mb,D_nonmag=na-nb,D_flip_A=ap-am,D_flip_B=bp-bm,
        D_AB=ap-bp,Sigma_ref=na+nb)
    v.update(P_mag=100*(ma-mb)/(na+nb),P_nonmag=100*(na-nb)/(na+nb),
             P_flip_A=100*(ap-am)/(ap+am),P_AB=100*(ap-bp)/(ap+bp))
    return v


def writecsv(path,rows):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def run():
    cases=[];differences=[];checks=[];raw_arrays=[[],[]]
    for thickness in [10.,30.]:
        for y in [0.,15.]:
            for channel in ['single','double']:
                name=f't{thickness:g}_y{y:g}_{channel}'
                loaded=[]
                for label in ['original','corrected']:
                    folder=OUT/'ni017'/label/name
                    assert (folder/'complete.json').exists(),folder
                    with np.load(folder/'results.npz',allow_pickle=False) as f:loaded.append({k:f[k].copy() for k in f.files})
                for method in ['bloch','fft-multislice']:
                    for edge,ie in [('L3',0),('L2',1)]:
                        key=dict(thickness_nm=thickness,y_mrad=y,channel=channel,method=method,
                                 edge=edge,energy_ev=[831.271,848.698][ie])
                        raw=[np.array([v[method+'__'+k][ie] for k in
                             ['I_A_plus','I_B_plus','I_A_minus','I_B_minus']]) for v in loaded]
                        before,after=map(metrics,raw)
                        row=dict(key)
                        for label,m in [('old',before),('new',after)]:row.update({label+'_'+k:float(v) for k,v in m.items()})
                        cases.append(row)
                        for iv,v in enumerate(raw):raw_arrays[iv].append(v)
                        for metric in before:
                            a,b=before[metric],after[metric];delta=b-a
                            floor=1e-12*max(abs(raw[0]))
                            valid=abs(a)>floor if not metric.startswith('P_') else abs(a)>1e-10
                            differences.append(dict(key,observable=metric,before=float(a),after=float(b),
                                signed_difference=float(delta),absolute_difference=float(abs(delta)),
                                absolute_relative_change_percent=float(100*abs(delta)/abs(a)) if valid else float('nan'),
                                relative_change_valid=bool(valid),change_pp=float(delta) if metric.startswith('P_') else float('nan')))
                        expectation=raw[0][[2,3,0,1]]
                        error=float(max(abs(raw[1]-expectation)))
                        passed=bool(np.allclose(raw[1],expectation,rtol=1e-12,atol=1e-14))
                        checks.append(dict(key,state_exchange_max_absolute=error,passed=passed,
                            even_max_absolute=float(max(abs(after[k]-before[k]) for k in ['N_A','N_B','D_nonmag'])),
                            odd_sign_residual=float(max(abs(after[k]+before[k]) for k in ['M_A','M_B','D_mag','D_flip_A','D_flip_B']))))
    writecsv(OUT/'scientific_cases.csv',cases);writecsv(OUT/'scientific_differences.csv',differences)
    writecsv(OUT/'predicted_state_exchange_checks.csv',checks)
    np.savez_compressed(OUT/'before_after.npz',raw=np.array(raw_arrays),
        keys_json=json.dumps([{k:r[k] for k in ['thickness_nm','y_mrad','channel','method','edge','energy_ev']} for r in cases]),
        version_labels=np.array(['original','corrected']),raw_order=np.array(['I_A_plus','I_B_plus','I_A_minus','I_B_minus']))
    # Preserve the previous numerical gates without interpreting method agreement
    # as an independent proof of physical or cutoff convergence.
    comparisons=[]
    for r in cases:
        if r['method']!='bloch':continue
        other=next(v for v in cases if v['method']=='fft-multislice' and
                   all(v[k]==r[k] for k in ['thickness_nm','y_mrad','channel','edge']))
        for label in ['old','new']:
            rawkeys=['I_A_plus','I_B_plus','I_A_minus','I_B_minus']
            relative=max(abs(other[label+'_'+k]-r[label+'_'+k])/abs(r[label+'_'+k]) for k in rawkeys)
            pp=abs(other[label+'_P_AB']-r[label+'_P_AB'])
            comparisons.append(dict(thickness_nm=r['thickness_nm'],y_mrad=r['y_mrad'],channel=r['channel'],
                edge=r['edge'],version=label,raw_max_relative=float(relative),prb_discrepancy_pp=float(pp),
                magnetic_asymmetry_discrepancy_pp=float(abs(other[label+'_P_mag']-r[label+'_P_mag'])),
                passed=bool(relative<=.001 and pp<=.01)))
    writecsv(OUT/'bw_ms_comparison.csv',comparisons)
    # Confirm that re-executed original BW Double points reproduce historical
    # saved data rather than substituting an uncontrolled equivalent.
    baseline=json.loads((OUT/'pre_correction_baseline.json').read_text())
    old=Path(baseline['original_worktree']);historic=list(csv.DictReader((old/'build/emcd-017-extended-absolute-2d-mistilt/absolute_tilt_2d_raw.csv').open()))
    reproduction=[]
    for r in cases:
        if r['channel']!='double' or r['method']!='bloch':continue
        frozen=next(v for v in historic if v['grid_kind']=='matched_coarse' and float(v['delta_x_mrad'])==0 and
                    float(v['thickness_nm'])==r['thickness_nm'] and float(v['absolute_y_mrad'])==r['y_mrad'] and v['edge']==r['edge'])
        a=np.array([float(frozen[k]) for k in ['I_A_plus','I_B_plus','I_A_minus','I_B_minus']])
        b=np.array([r['old_'+k] for k in ['I_A_plus','I_B_plus','I_A_minus','I_B_minus']])
        reproduction.append(dict(thickness_nm=r['thickness_nm'],y_mrad=r['y_mrad'],edge=r['edge'],
            max_absolute=float(max(abs(a-b))),passed=bool(np.allclose(a,b,rtol=1e-12,atol=1e-14))))
    writecsv(OUT/'historical_reproduction.csv',reproduction)
    # Algebraic reanalysis of old full-map detector samples; explicitly not a
    # newly simulated or newly convergence-certified complete tilt scan.
    regional=[]
    for t in [10.,30.]:
        for edge in ['L3','L2']:
            selected=[v for v in historic if v['grid_kind']=='matched_coarse' and float(v['thickness_nm'])==t and v['edge']==edge]
            old_false=new_false=valid=changed_locations=0
            for v in selected:
                old_mag=float(v['D_mag']);even=float(v['D_nonmag']);floor=float(v['magnetic_floor_au'])
                if abs(old_mag)<=floor:continue
                old_flag=(even+old_mag)*old_mag<0;new_flag=(even-old_mag)*(-old_mag)<0
                valid+=1;old_false+=int(old_flag);new_false+=int(new_flag)
                changed_locations+=int(old_flag!=new_flag)
            regional.append(dict(thickness_nm=t,edge=edge,grid_points=len(selected),resolved_magnetic_points=valid,
                old_false_sign_count=old_false,algebraic_corrected_false_sign_count=new_false,
                changed_spatial_classifications=changed_locations,
                inherited_failed_control_points=sum('FAILED' in v.get('numerical_status','') for v in selected),
                scope='algebraic state swap of frozen Stage4.2 detector data; not a recomputed full scan'))
    writecsv(OUT/'stage42_algebraic_sign_impact.csv',regional)
    fig,axes=plt.subplots(2,2,figsize=(11,7),constrained_layout=True)
    for ie,edge in enumerate(['L3','L2']):
        rows=[r for r in cases if r['channel']=='double' and r['method']=='bloch' and r['edge']==edge]
        x=np.arange(len(rows));labels=[f"{r['thickness_nm']:g} nm\nY={r['y_mrad']:+g} mrad" for r in rows]
        for ax,metric,title in [(axes[ie,0],'D_mag','Magnetic-odd A/B difference'),(axes[ie,1],'D_AB','Conventional +M A/B difference')]:
            ax.plot(x,[r['old_'+metric] for r in rows],'o--',label='Original')
            ax.plot(x,[r['new_'+metric] for r in rows],'s-',label='Corrected')
            ax.axhline(0,color='.6',lw=.7);ax.set_xticks(x,labels);ax.set_title(edge+': '+title)
            ax.set_ylabel('Signed intensity difference (a.u.)');ax.legend(fontsize=8)
    fig.suptitle('Ni [017], 300 kV, exact (200) Bragg X; Double BW\nIdentical source, basis, potential, detector and depth settings')
    for ext in ['png','svg']:fig.savefig(OUT/('scientific_impact.'+ext),dpi=160)
    plt.close(fig)
    summary=dict(paired_method_edge_conditions=len(cases),state_exchange_passed=all(v['passed'] for v in checks),
        max_state_exchange_absolute=max(v['state_exchange_max_absolute'] for v in checks),
        max_even_absolute=max(v['even_max_absolute'] for v in checks),max_odd_sign_residual=max(v['odd_sign_residual'] for v in checks),
        historical_reproduction_passed=all(v['passed'] for v in reproduction),
        historical_reproduction_max_absolute=max(v['max_absolute'] for v in reproduction),
        bw_ms_passed=sum(v['passed'] for v in comparisons),bw_ms_comparisons=len(comparisons),
        bw_ms_max_raw_relative=max(v['raw_max_relative'] for v in comparisons),
        bw_ms_max_prb_pp=max(v['prb_discrepancy_pp'] for v in comparisons),
        regional_algebraic_impact=regional)
    (OUT/'scientific_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':run()
