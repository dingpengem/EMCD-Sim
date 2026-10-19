"""Strict checkpoint reuse, runtime assessment and sequential two-energy scan.

Uses the accepted benchmark engine unchanged. Single and Double share each
case's incident preparation; reported historical elapsed times cover both.
"""
import argparse,ast,csv,hashlib,json,subprocess,time
from pathlib import Path
import numpy as np
import ni_double_channeling_cutoff_study as study

ROOT=Path('outputs/ni_emcd_asymmetry_thickness_200kv')
TIMES=tuple(range(0,101,2))
BASELINE='ef661444c9e68a1541fe8de213bb9cabcef3a288'


class WithoutOptionalCancellation(ast.NodeTransformer):
    """Audit the default execution path; never used to execute calculations."""
    def visit_ImportFrom(self,n):
        return None if n.module=='cancellation' else n
    def visit_ClassDef(self,n):
        return None if n.name=='PreparedBlochIncoming' else self.generic_visit(n)
    def visit_FunctionDef(self,n):
        if n.name=='prepare_incoming_bloch':return None
        pairs=[(a,d) for a,d in zip(n.args.kwonlyargs,n.args.kw_defaults) if a.arg not in ('cancelled','prepared_incoming')]
        # MS prepared_incoming predates the audit baseline and must be kept.
        if any(a.arg=='prepared_incoming' for a in n.args.kwonlyargs) and n.name!='double_channeling_response':
            pairs=[(a,d) for a,d in zip(n.args.kwonlyargs,n.args.kw_defaults) if a.arg!='cancelled']
        n.args.kwonlyargs=[a for a,d in pairs];n.args.kw_defaults=[d for a,d in pairs]
        self.generic_visit(n)
        if len(n.body)>1 and isinstance(n.body[-1],ast.Return) and isinstance(n.body[-1].value,ast.Name) and n.body[-1].value.id=='result':
            last=n.body[-2]
            if isinstance(last,ast.Assign) and len(last.targets)==1 and isinstance(last.targets[0],ast.Name) and last.targets[0].id=='result':
                n.body[-2:]=[ast.Return(value=last.value)]
        return n
    def visit_Expr(self,n):
        if isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='check_cancelled':return None
        return self.generic_visit(n)
    def visit_Call(self,n):
        n.keywords=[k for k in n.keywords if k.arg!='cancelled'];return self.generic_visit(n)
    def visit_If(self,n):
        if ast.unparse(n.test)=='prepared_incoming is not None' and n.orelse:
            return [self.visit(v) for v in n.orelse]
        return self.generic_visit(n)


def implementation_audit():
    aliases={};records={}
    for name in ('double_channeling.py','multislice_double_channeling.py'):
        path='src/emcd_sim/'+name
        old=subprocess.check_output(['git','show',BASELINE+':'+path])
        current=Path(path).read_bytes()
        a=WithoutOptionalCancellation().visit(ast.parse(old.decode()))
        b=WithoutOptionalCancellation().visit(ast.parse(current.decode()))
        assert ast.dump(a)==ast.dump(b),'Default numerical path changed: '+path
        aliases[path]={hashlib.sha256(old).hexdigest(),hashlib.sha256(old.replace(b'\n',b'\r\n')).hexdigest(),hashlib.sha256(current).hexdigest()}
        records[path]=dict(default_path_ast_equal=True,baseline=BASELINE,accepted_sha256=sorted(aliases[path]))
    return aliases,records


def encode(p):return json.dumps(study.base.study.base.clean(p),sort_keys=True)


def contexts():
    return {z:(c,study.base.detector_grid(c)) for z in ('001','017') for c in [study.context(z,6.2,4.6)]}


def parameters(c,d,t,engine):
    p=study.base.parameters(c,d,float(t),fft=48)
    p.update(engine=engine,outgoing_hkl=c['hkl'],study_script_sha256=study.PHYSICS_HASH,study='cutoff_convergence_v1')
    return study.base.study.base.clean(p)


def compatible(old,expected,aliases):
    old=json.loads(json.dumps(old));expected=json.loads(json.dumps(expected))
    # These two equivalences are source-audited, not a physical-parameter waiver.
    if study.SCHEDULER_ONLY_EQUIVALENCE and old.get('study_script_sha256')==study.ORIGINAL_PHYSICS_HASH:
        old['study_script_sha256']=study.PHYSICS_HASH
    for path,allowed in aliases.items():
        if old.get('implementation_sha256',{}).get(path) in allowed:
            old['implementation_sha256'][path]=expected['implementation_sha256'][path]
    if expected['thickness_nm']==0:
        old.pop('zero_thickness',None)
    return old==expected


def inventory(ctx,aliases):
    records={};rejected=[]
    roots=[p for p in Path('outputs').glob('ni_double_channeling*') if p.is_dir()]+[ROOT]
    for root in roots:
        for path in sorted(root.glob('checkpoints/*_p6.2_b4.6_o4.6_f48_d257_s0.04.npz')):
            with np.load(path,allow_pickle=False) as data:
                p=json.loads(str(data['parameters_json']));z=p['zone'];t=p['thickness_nm'];engine=p['engine']
                if z not in ctx or t not in TIMES or engine not in ('bw','ms'):continue
                c,d=ctx[z];expected=parameters(c,d,t,engine)
                if not compatible(p,expected,aliases):
                    rejected.append(str(path));continue
                raw=data['raw'].copy();assert raw.shape==(2,2,4) and np.isfinite(raw).all()
                key=(z,int(t),engine)
                if key in records:
                    np.testing.assert_array_equal(records[key]['raw'],raw)
                    continue
                records[key]=dict(path=str(path),raw=raw,elapsed=float(data['elapsed_seconds']),parameters=p)
    return records,rejected


def assessment(records):
    estimates={};remaining=[]
    for z in ('001','017'):
        measured=sorted((t,r['elapsed']) for (zone,t,e),r in records.items() if zone==z and e=='ms' and t>0)
        missing=[t for t in TIMES if t and (z,t,'ms') not in records]
        assert len(measured)>=3,'Representative timings missing; profile genuine missing cases first.'
        x,y=np.array(measured).T;slope,intercept=np.polyfit(x,y,1)
        predicted=np.maximum(min(y),intercept+np.maximum(0,slope)*np.asarray(missing))
        estimates[z]=dict(recorded_joint_single_double_timings=measured,missing_thicknesses_nm=missing,
            remaining_single_cases=len(missing),remaining_double_cases=len(missing),
            slope_seconds_per_nm=float(slope),intercept_seconds=float(intercept),estimated_seconds=float(predicted.sum()))
        remaining.extend((z,t,'ms') for t in missing)
    total=sum(r['estimated_seconds'] for r in estimates.values())
    return dict(zones=estimates,remaining_joint_ms_cases=len(remaining),remaining_ms_single_cases=len(remaining),
        remaining_ms_double_cases=len(remaining),estimated_hours=total/3600,
        uncertainty_hours=[.65*total/3600,1.6*total/3600],
        interpretation='Elapsed wall time for sequential geometry/thickness jobs; each produces both Single and Double at L3/L2. Historical timings do not separately time the models. No duplicate 50/100 nm profiling; existing 8/12 bracket 10 nm.',
        uncertainty='Conservative workload/thermal/load interval, not a statistical confidence interval.')


def save_case(path,p,raw,elapsed,provenance):
    path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix('.temporary.npz')
    np.savez_compressed(temp,parameters_json=np.array(encode(p)),raw=raw,elapsed_seconds=np.array(elapsed),provenance_json=np.array(json.dumps(provenance)))
    temp.replace(path)


def export(records):
    rows=[];keys=sorted(records)
    for z,t,e in keys:
        r=records[z,t,e];p=r['parameters']
        for im,model in enumerate(('single','double')):
            for ie,row in enumerate(study.base.rows_for(r['raw'][im],t,e)):
                rows.append(dict(zone=z,basis='systematic-row-restricted' if z=='001' else 'full finite ZOLZ',solver=e,channeling_model=model,
                    **row,
                    emcd_asymmetry_percent=row['prb_relative_dichroism_percent'],D_nonmag=row['D_even'],nonmagnetic_asymmetry_percent=row['nonmagnetic_imbalance_percent'],checkpoint=r['path'],
                    source_sha256=p['source_sha256'],numerical_configuration_json=encode(p)))
    ROOT.mkdir(parents=True,exist_ok=True)
    if rows:
        with (ROOT/'thickness_series.csv').open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        np.savez_compressed(ROOT/'thickness_series.npz',keys_json=np.array(json.dumps(keys)),raw=np.array([records[k]['raw'] for k in keys]),
            energies_ev=study.base.ENERGIES,rows_json=np.array(json.dumps(rows,allow_nan=True)))
    complete=all((z,t,e) in records for z in ('001','017') for t in TIMES for e in ('bw','ms'))
    (ROOT/'progress.json').write_text(json.dumps(dict(completed_joint_cases=len(keys),required_joint_cases=204,complete=complete,
        missing=[(z,t,e) for z in ('001','017') for t in TIMES for e in ('bw','ms') if (z,t,e) not in records]),indent=2),encoding='utf-8')
    if complete:figures_and_analysis(records)


def figures_and_analysis(records):
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    folder=ROOT/'figures';folder.mkdir(exist_ok=True);extrema=[];comparisons=[];crossings=[]
    for z in ('001','017'):
        for ie,edge in enumerate(('L3','L2')):
            for solvers,label in [(('bw',),'BW'),(('ms',),'MS'),(('bw','ms'),'BW_MS_all_models')]:
                fig=Figure(figsize=(8,5),layout='constrained');FigureCanvasAgg(fig);ax=fig.subplots()
                for e in solvers:
                    for im,model in enumerate(('single','double')):
                        values=np.array([study.base.study.base.observables(records[z,t,e]['raw'][im])['prb_relative_dichroism_percent'][ie] for t in TIMES])
                        ax.plot(TIMES,values,color=('C0','C1')[im],ls='-' if e=='bw' else '--',marker='o',ms=2.5,label=e.upper()+' '+model.title())
                        if len(solvers)==1:
                            index=int(np.nanargmax(abs(values)));extrema.append(dict(zone=z,solver=e,model=model,edge=edge,thickness_nm=TIMES[index],asymmetry_percent=float(values[index])))
                            for i in np.flatnonzero(values[:-1]*values[1:]<0):crossings.append(dict(zone=z,solver=e,model=model,edge=edge,bracket_nm=[TIMES[i],TIMES[i+1]]))
                ax.axhline(0,color='.4',lw=.7);ax.set(xlabel='Thickness (nm)',ylabel='EMCD Asymmetry (%)',xlim=(0,100),title=f'Ni [{z}] | 200 kV | {edge} {study.base.ENERGIES[ie]:.4f} eV\n'+('Systematic-row-restricted' if z=='001' else 'Full finite ZOLZ'));ax.legend();ax.grid(alpha=.2)
                name=f'ni{z}_{edge}_{label}'+('_single_double' if len(solvers)==1 else '')
                for extension in ('png','svg'):fig.savefig(folder/(name+'.'+extension),dpi=200)
        for t in TIMES[1:]:
            for channel,m in study.comparison(records[z,t,'bw']['raw'],records[z,t,'ms']['raw']).items():comparisons.append(dict(zone=z,thickness_nm=t,channel_edge=channel,**m))
    with (ROOT/'bw_ms_comparison.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(comparisons[0]));w.writeheader();w.writerows(comparisons)
    summary=dict(complete=True,extrema=extrema,zero_crossings=crossings,max_difference_pp=max(abs(r['prb_change_pp']) for r in comparisons),max_raw_relative=max(r['raw_relative'] for r in comparisons),
        numerical_gate_passed=all(abs(r['prb_change_pp'])<=.01 and r['raw_relative']<=.001 for r in comparisons),global_convergence_certified=False)
    (ROOT/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true');args=parser.parse_args()
    ROOT.mkdir(parents=True,exist_ok=True)
    aliases,audit=implementation_audit();ctx=contexts();records,rejected=inventory(ctx,aliases)
    assert not rejected,'Incompatible matching-name checkpoints: '+str(rejected)
    estimate=assessment(records)
    (ROOT/'runtime_assessment.json').write_text(json.dumps(estimate,indent=2),encoding='utf-8')
    (ROOT/'configuration.json').write_text(json.dumps({z:parameters(c,d,0,'ms') for z,(c,d) in ctx.items()},indent=2),encoding='utf-8')
    (ROOT/'provenance.json').write_text(json.dumps(dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),implementation_equivalence_audit=audit,checkpoint_reuse='Exact physical/tensor/grid metadata; explicitly audited scheduler/cancellation-only source equivalence.'),indent=2),encoding='utf-8')
    print(json.dumps(estimate,indent=2),flush=True);export(records)
    if not args.run:return
    for z,t,e in [(z,t,'ms') for t in TIMES for z in ('001','017')]:
        if (z,t,e) in records:continue
        c,d=ctx[z];p=parameters(c,d,t,e);path=ROOT/'checkpoints'/f'{z}_ms_t{t:03}_p6.2_b4.6_o4.6_f48_d257_s0.04.npz'
        start=time.perf_counter()
        if t:data=study.engine(c,d,t,e,fft=48,depth=257,step=.04);raw=data['raw'];del data
        else:raw=np.zeros((2,2,4))
        elapsed=time.perf_counter()-start
        save_case(path,p,raw,elapsed,dict(kind='new_calculation',commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()))
        records[z,t,e]=dict(path=str(path),raw=raw,elapsed=elapsed,parameters=p);export(records)
        print(f'Completed {z} {e} {t} nm, Single + Double, {elapsed:.2f} s; {len(records)}/204 joint cases',flush=True)


if __name__=='__main__':main()
