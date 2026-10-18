"""Calculated-data-only summaries of independent cutoff/basis/FFT/depth tests."""
import csv,json
from functools import lru_cache
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
import ni_double_channeling_cutoff_study as run
ROOT=run.ROOT


@lru_cache(None)
def beam_count(zone,basis):return len(run.context(zone,6.2,basis)['hkl'])


@lru_cache(None)
def key(zone,t,p=6.2,b=3.8,o=None,f=48,d=257,s=.04):
    n=beam_count(zone,b if o is None else o)
    return (zone,t,p,b,n,f,d,s)


def comparisons(records):
    rows=[];missing=[]
    def append(category,label,ka,kb,engine):
        aa=records.get(ka+(engine,));bb=records.get(kb+(engine,))
        if aa is None or bb is None:
            missing.append((category,label,ka,kb,engine));return
        for name,m in run.comparison(aa[0],bb[0]).items():
            channel,edge=name.split('_')
            rows.append(dict(category=category,label=label,zone=ka[0],thickness_nm=ka[1],engine=engine,channel=channel,edge=edge,
                reference=str(aa[1]),control=str(bb[1]),**m))
    for z in ('001','017'):
        for t in run.TIMES:
            for a,b in zip(run.CUTOFFS[:-1],run.CUTOFFS[1:]):
                for engine in ('bw','ms'):
                    available=key(z,t,p=a)+(engine,) in records and key(z,t,p=b)+(engine,) in records
                    if engine=='bw' or available or (t in run.ms_times(a) and t in run.ms_times(b)):
                        append('cutoff',f'{a:g}->{b:g}',key(z,t,p=a),key(z,t,p=b),engine)
            for cutoff in run.CUTOFFS:
                kb=key(z,t,p=cutoff)
                aa=records.get(kb+('bw',));bb=records.get(kb+('ms',))
                if aa and bb:
                    for name,m in run.comparison(aa[0],bb[0]).items():
                        channel,edge=name.split('_')
                        rows.append(dict(category='BW-MS',label=f'matched {cutoff:g}',zone=z,thickness_nm=t,engine='ms-bw',channel=channel,edge=edge,
                            reference=str(aa[1]),control=str(bb[1]),**m))
                elif t in run.ms_times(cutoff):missing.append(('BW-MS',z,t,cutoff))
        for zone,t,engine,label,args in run.controls():
            if zone!=z:continue
            translated={dict(basis='b',out_basis='o',fft='f',depth='d',step='s')[k]:v for k,v in args.items()}
            append('control',label,key(z,t),key(z,t,**translated),engine)
        for t in (8.,12.):
            k=key(z,t,b=4.6,o=4.6)
            aa=records.get(k+('bw',));bb=records.get(k+('ms',))
            if aa and bb:
                for name,m in run.comparison(aa[0],bb[0]).items():
                    channel,edge=name.split('_')
                    rows.append(dict(category='BW-MS enlarged',label='matched b4.6 (8/12)',zone=z,thickness_nm=t,
                        engine='ms-bw',channel=channel,edge=edge,reference=str(aa[1]),control=str(bb[1]),**m))
            else:missing.append(('enlarged matched',z,t))
    return rows,missing


def summarize(rows):
    result=[]
    for category,label,z in dict.fromkeys((r['category'],r['label'],r['zone']) for r in rows):
        a=[r for r in rows if (r['category'],r['label'],r['zone'])==(category,label,z)]
        result.append(dict(category=category,label=label,zone=z,
            max_prb_change_pp=max(abs(r['prb_change_pp']) for r in a),
            max_raw_relative=max(r['raw_relative'] for r in a),
            max_magnetic_asymmetry_change_pp=max(abs(r['magnetic_asymmetry_change_pp']) for r in a),
            max_D_mag_change=max(abs(r['D_mag_change']) for r in a)))
    return result


def figures(rows,summary):
    for metric,ylabel,name in (('prb_relative_dichroism_percent','L3 PRB (%)','cutoff_L3'),
        ('magnetic_only_percent','L3 magnetic-only (%)','cutoff_magnetic')):
        f=Figure(figsize=(11,7));FigureCanvasAgg(f)
        for iz,z in enumerate(('001','017')):
            for im,method in enumerate(('bw_double','ms_double')):
                ax=f.add_subplot(2,2,iz*2+im+1)
                for t in run.TIMES:
                    a=[r for r in rows if r['zone']==z and r['method']==method and r['edge']=='L3' and r['thickness_nm']==t
                        and r['beam_cutoff']==3.8 and r['outgoing_beams']==beam_count(z,3.8) and r['fft']==48 and r['depth']==257 and r['step']==.04]
                    a.sort(key=lambda r:r['potential_cutoff'])
                    ax.plot([r['potential_cutoff'] for r in a],[r[metric] for r in a],'.-',label=f'{t:g} nm')
                ax.set(xlabel='Potential cutoff (cycles/A)',ylabel=ylabel,title=f'[{z}] {method}');ax.legend(fontsize=7,ncol=2)
        save(f,name)
    f=Figure(figsize=(12,7));FigureCanvasAgg(f)
    for iz,z in enumerate(('001','017')):
        a=[r for r in summary if r['zone']==z]
        for col,(metric,ylabel,limit) in enumerate((('max_prb_change_pp','Max contrast change (pp)',.01),('max_raw_relative','Max relative raw change',.001))):
            ax=f.add_subplot(2,2,iz*2+col+1);values=[max(r[metric],1e-15) for r in a]
            ax.bar(np.arange(len(a)),values);ax.set_yscale('log');ax.set_xticks(np.arange(len(a)),[r['label'] for r in a],rotation=65,ha='right',fontsize=7)
            ax.axhline(limit,color='red',ls=':');ax.set(ylabel=ylabel,title=f'[{z}] all checked methods/edges/thicknesses')
    save(f,'independent_controls')


def save(fig,name):
    fig.tight_layout()
    for ext in ('png','svg'):fig.savefig(ROOT/(name+'.'+ext),dpi=170)


def populations():
    rows=[]
    for path in sorted((ROOT/'checkpoints').glob('*.npz')):
        with np.load(path) as f:
            p=json.loads(str(f['parameters_json']));hi=list(map(tuple,p['hkl']))
            ho=list(map(tuple,f['outgoing_population_hkl']));selected=set(map(tuple,p['outgoing_hkl']))
            outside=np.array([h not in selected for h in ho]);cfg=p['settings']
            for ie,edge in enumerate(('L3','L2')):
                for iq,detector in enumerate(('A','B')):
                    rows.append(dict(checkpoint=str(path),zone=p['zone'],engine=p['engine'],thickness_nm=p['thickness_nm'],potential_cutoff=cfg['potential_cutoff'],
                        incoming_beams=len(hi),outgoing_beams=len(selected),fft=p['fft_grid'],depth=p['depth_steps'],step=p['maximum_slice_step_nm'],edge=edge,detector=detector,
                        incoming_000_mean=float(f['incoming_depth_mean'][hi.index((0,0,0))]),incoming_200_mean=float(f['incoming_depth_mean'][hi.index((2,0,0))]),
                        incoming_excluded_mean=float(1-f['incoming_depth_mean'].sum()),
                        outgoing_000_mean=float(f['outgoing_depth_mean'][ie,iq,ho.index((0,0,0))]),
                        outgoing_200_mean=float(f['outgoing_depth_mean'][ie,iq,ho.index((2,0,0))]),
                        outgoing_excluded_mean=float(f['outgoing_depth_mean'][ie,iq,outside].sum())))
    run.base.study.base.write_csv(ROOT/'beam_populations.csv',rows)
    f=Figure(figsize=(11,7));FigureCanvasAgg(f)
    for iz,z in enumerate(('001','017')):
        for col,metric in enumerate(('incoming_200_mean','outgoing_200_mean')):
            ax=f.add_subplot(2,2,iz*2+col+1)
            for engine in ('bw','ms'):
                a=[r for r in rows if r['zone']==z and r['engine']==engine and r['thickness_nm']==100 and r['edge']=='L3' and r['detector']=='A'
                    and r['incoming_beams']==beam_count(z,3.8) and r['outgoing_beams']==r['incoming_beams'] and r['fft']==48 and r['depth']==257 and r['step']==.04]
                a.sort(key=lambda r:r['potential_cutoff'])
                ax.plot([r['potential_cutoff'] for r in a],[r[metric] for r in a],'.-',label=engine)
            ax.set(title=f'[{z}] 100 nm | L3 | A center',xlabel='Potential cutoff (cycles/A)',ylabel=metric);ax.legend()
    save(f,'beam_populations')


def locations(rows):
    summaries=[]
    f=Figure(figsize=(11,7));FigureCanvasAgg(f)
    for iz,z in enumerate(('001','017')):
        original=list(csv.DictReader((run.OLD/z/'results.csv').open()))
        for im,engine in enumerate(('bw','ms')):
            ax=f.add_subplot(2,2,iz*2+im+1)
            for channel in ('entrance','double'):
                method=engine+'_'+channel
                old=[r for r in original if r['method']==method and r['edge']=='L3' and float(r['thickness_nm'])<=36]
                ax.plot([float(r['thickness_nm']) for r in old],[float(r['prb_relative_dichroism_percent']) for r in old],alpha=.4,label=channel+' old 2.2')
                a=[r for r in rows if r['zone']==z and r['method']==method and r['edge']=='L3' and r['potential_cutoff']==6.2 and r['beam_cutoff']==3.8
                    and r['outgoing_beams']==beam_count(z,3.8) and r['fft']==48 and r['depth']==257 and r['step']==.04]
                a.sort(key=lambda r:r['thickness_nm'])
                ax.plot([r['thickness_nm'] for r in a if r['thickness_nm']<=36],[r['prb_relative_dichroism_percent'] for r in a if r['thickness_nm']<=36],'o',ms=4,label=channel+' new 6.2')
                if a:
                    peak=max(a,key=lambda r:abs(r['prb_relative_dichroism_percent']))
                    brackets=[(x['thickness_nm'],y['thickness_nm']) for x,y in zip(a[:-1],a[1:]) if x['prb_relative_dichroism_percent']*y['prb_relative_dichroism_percent']<0]
                    summaries.append(dict(zone=z,method=method,sampled_peak_nm=peak['thickness_nm'],sampled_peak_L3_percent=peak['prb_relative_dichroism_percent'],
                        sign_change_brackets_nm=brackets,thicknesses_tested=[r['thickness_nm'] for r in a]))
            ax.set(title=f'[{z}] {engine} | native L3',xlabel='Thickness (nm)',ylabel='Signed raw PRB (%)');ax.legend(fontsize=7);ax.axhline(0,color='.5',lw=.5)
    save(f,'peak_and_crossing_locations')
    run.base.study.base.write_json(ROOT/'locations.json',summaries)


def audit_original():
    original=list(csv.DictReader((run.OLD/'convergence.csv').open()))
    failed=[r for r in original if abs(float(r['prb_change_pp']))>.01 or float(r['raw_max_relative'])>.001]
    run.base.study.base.write_csv(ROOT/'original_failed_controls.csv',failed)
    states=[];shells=[]
    for z in ('001','017'):
        for t in (8,30):
            with np.load(run.OLD/z/'checkpoints'/f't{t:03}.npz') as f:reference=f['raw'].copy()
            for label in ('potential2p6','potential3p0'):
                with np.load(run.OLD/z/'controls'/f'{label}_t{t}.npz') as f:actual=f['raw'].copy()
                for im,method in enumerate(run.base.METHODS):
                    for ie,edge in enumerate(('L3','L2')):
                        for ip,state in enumerate(('A_plus','B_plus','A_minus','B_minus')):
                            a,b=reference[im,ie,ip],actual[im,ie,ip]
                            states.append(dict(zone=z,t_nm=t,control=label,method=method,edge=edge,state=state,
                                reference=float(a),actual=float(b),relative_change=float((b-a)/max(abs(a),abs(b)))))
        c=run.context(z,6.2,3.8)
        grid=run.ProjectedNiFFT.build(c['model'].elastic,grid_points=48,potential_cutoff=6.2,
            systematic_row=c['systematic_row'],row_reduction=c['systematic_row'],projected_geometry=c['projected_geometry'])
        coefficients=np.fft.fftn(grid.potential)/grid.potential.size
        for h,g,v in zip(grid.hkl,grid.g,coefficients.ravel()):
            length=float(np.linalg.norm(g))
            if length<1e-10 or length>6.2+1e-10 or abs(v)<1e-12:continue
            shells.append(dict(zone=z,h=int(h[0]),k=int(h[1]),l=int(h[2]),g=length,coefficient_nm_inv=float(v.real),
                first_included_cutoff=next(x for x in run.CUTOFFS if x>=length)))
    run.base.study.base.write_csv(ROOT/'original_failed_states.csv',states)
    run.base.study.base.write_csv(ROOT/'fourier_shells.csv',shells)
    run.base.study.base.write_json(ROOT/'original_failure_audit.json',dict(failed_rows=len(failed),
        largest=max(failed,key=lambda x:abs(float(x['prb_change_pp']))),thresholds=run.TOLERANCES))


def main():
    audit_original()
    rows,records=run.rows_and_pairs();delta,missing=comparisons(records);summary=summarize(delta)
    if delta:run.base.study.base.write_csv(ROOT/'differences.csv',delta)
    if summary:run.base.study.base.write_csv(ROOT/'convergence_summary.csv',summary)
    tails=[r for r in summary if r['category']=='control' or (r['category']=='BW-MS' and r['label']=='matched 6.2') or (r['category']=='cutoff' and r['label'] in ('4.6->5.4','5.4->6.2'))]
    for z in ('001','017'):
        for t in (6.,10.,14.,32.,34.,36.):
            if key(z,t)+('bw',) not in records:missing.append(('location',z,t,'bw'))
    numerical_pass=bool(tails) and all(r['max_prb_change_pp']<=.01 and r['max_raw_relative']<=.001 for r in tails)
    gate=dict(complete=not missing,passed=not missing and numerical_pass,thresholds=run.TOLERANCES,
        numerical_controls_pass=numerical_pass,missing_comparisons=missing,
        scope='Representative thicknesses, independent controls; original 2.2 scan is not retroactively converged',
        tested_uniform_profile=dict(potential_cutoff=6.2,beam_cutoff=3.8,fft=48,depth=257,step_nm=.04))
    run.base.study.base.write_json(ROOT/'convergence_gate.json',gate)
    statuses={}
    groups=dict(potential_cutoff=[r for r in summary if r['category']=='cutoff' and r['label'] in ('4.6->5.4','5.4->6.2')],
        adjacent_basis=[r for r in summary if r['category']=='control' and r['label'] in ('incoming basis','outgoing basis','both bases')],
        fft_slice_depth=[r for r in summary if r['category']=='control' and r['label'] not in ('incoming basis','outgoing basis','both bases')],
        fixed_b3p8_method_agreement=[r for r in summary if r['category']=='BW-MS' and r['label']=='matched 6.2'],
        enlarged_b4p6_agreement_8_12=[r for r in summary if r['category']=='BW-MS enlarged'])
    for name,a in groups.items():
        pp=max(r['max_prb_change_pp'] for r in a);raw=max(r['max_raw_relative'] for r in a)
        statuses[name]=dict(passed=not missing and pp<=.01 and raw<=.001,max_prb_change_pp=pp,max_raw_relative=raw)
    peak_rows=[]
    for z in ('001','017'):
        for engine in ('bw','ms'):
            values=[]
            for t in (8.,12.):
                raw=records[key(z,t,b=4.6,o=4.6)+(engine,)][0]
                values.append([float(run.base.study.base.observables(raw[im])['prb_relative_dichroism_percent'][0]) for im in (0,1)])
            peak_rows.append(dict(zone=z,engine=engine,beam_cutoff=4.6,entrance_8=values[0][0],entrance_12=values[1][0],
                double_8=values[0][1],double_12=values[1][1],entrance_12_stronger=abs(values[1][0])>abs(values[0][0]),
                double_8_stronger=abs(values[0][1])>abs(values[1][1])))
    run.base.study.base.write_csv(ROOT/'peak_ordering.csv',peak_rows)
    statuses.update(main_peak_ordering_stable=all(r['entrance_12_stronger'] and r['double_8_stronger'] for r in peak_rows),
        uniform_profile_gate_passed=gate['passed'],full_0_100_curve_convergence_established=False,
        production_candidate_for_further_validation=dict(potential_cutoff=6.2,beam_cutoff=4.6,fft=48,depth=257,step_nm=.04),
        recommendation='Do not treat the original or uniform b3.8 series as converged. Validate the uniform enlarged profile before full voltage/GUI expansion.')
    run.base.study.base.write_json(ROOT/'factor_status.json',statuses)
    enlarged=[r for r in delta if r['category']=='BW-MS enlarged']
    run.base.study.base.write_csv(ROOT/'enlarged_basis_matched_methods.csv',enlarged)
    keys=list(records);np.savez_compressed(ROOT/'compact_results.npz',raw=np.array([records[k][0] for k in keys]),
        keys_json=np.array(json.dumps(keys)),comparison_rows_json=np.array(json.dumps(delta)))
    figures(rows,summary);populations();locations(rows)
    print('Complete:',not missing,'gate:',gate['passed'],'missing:',len(missing),flush=True)


if __name__=='__main__':main()
