"""Checkpointed, matched L3-only 30/8 nm buffer benchmark. No scans."""
import argparse,csv,hashlib,importlib.util,json,subprocess,sys
from dataclasses import asdict,replace
from pathlib import Path
import numpy as np
from emcd_sim import multislice_double_channeling as current
from emcd_sim.double_channeling import intensities_from_response
from emcd_sim.gui.prb_benchmark import relative_dichroism_percent
from emcd_sim.gui.signal_normalization import divide_percent,MAP_FLOOR
from emcd_sim.study_geometry import StudyGeometry
Ni017Geometry=lambda a_angstrom=3.524: StudyGeometry((0,1,7),(2,0,0),a_angstrom)
import profile_ms_double as profile

BASE='39aafb6701f7cf84643c10366afac59401e8d91e'
ROOT=Path('outputs/ms_double_buffer_optimization')


def baseline():
    source=subprocess.check_output(['git','show',BASE+':src/emcd_sim/multislice_double_channeling.py'])
    path=ROOT/'baseline_multislice.py';path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():assert path.read_bytes()==source
    else:path.write_bytes(source)
    name='emcd_sim._baseline_buffer_ms';spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module


def arrays(case,response):
    c=case['cfg'];r=response[case['inverse']]*case['sign'][:,:,None]*case['sign'][:,None,:]
    plus,minus=[intensities_from_response(r,t.tensor_angstrom2_per_ev[0]).reshape(c.grid,c.grid) for t in case['tensors']]
    n,m=(plus+minus)/2,(plus-minus)/2
    weight=np.stack([case['weights'][d].ravel() for d in ('A','B')]);dq2=(case['qx'][0,1]-case['qx'][0,0])**2
    ap,bp=weight@plus.ravel()*dq2;am,bm=weight@minus.ravel()*dq2
    return dict(R=response,I_plus=plus,I_minus=minus,I_mag=m,I_nonmag=n,D_mag=m-m[::-1],D_nonmag=n-n[::-1],
        detector_states=np.array([ap,bp,am,bm]),detector_D_mag=np.array([(ap-am-bp+bm)/2]),
        detector_D_nonmag=np.array([(ap+am-bp-bm)/2]),detector_asymmetry=relative_dichroism_percent(ap,bp)[0],
        angular_asymmetry=divide_percent(plus-plus[::-1],plus+plus[::-1],MAP_FLOOR)[0])


def run(policy,thickness):
    implementation=baseline() if policy=='baseline' else current
    case=profile.setup();case['settings']=replace(case['settings'],thickness=thickness)
    s=case['settings'];c=case['cfg'];stem=ROOT/f'{policy}_t{int(thickness):03}'
    signature=json.loads(json.dumps(dict(settings=asdict(s),config=asdict(c),baseline=BASE,
        implementation_sha256=hashlib.sha256(Path(implementation.__file__).read_bytes()).hexdigest())))
    if stem.with_suffix('.json').exists():
        data=json.loads(stem.with_suffix('.json').read_text());assert data['signature']==signature
        assert hashlib.sha256(stem.with_suffix('.npz').read_bytes()).hexdigest()==data['array_sha256']
        print('REUSED',policy,thickness,flush=True);return
    timings=profile.Timings()
    with profile.SampleRAM() as ram,profile.fft_hooks(timings,implementation):
        with timings.region('fft_geometry_potential'):
            grid=implementation.ProjectedNiFFT.build(case['elastic'],grid_points=c.fft_grid,potential_cutoff=s.potential_cutoff,
                systematic_row=c.systematic_row,row_reduction=c.systematic_row,projected_geometry=Ni017Geometry())
        with timings.region('incoming_fields'):
            incoming=implementation.incident_fields(grid,s.thickness,depth_steps=c.depth,slice_step_nm=c.slice_step)
        response,run_info,_=profile.evaluate_batches(case,case['query'],grid,incoming,4,timings=timings,implementation=implementation)
        with timings.region('result_assembly'):result=arrays(case,response)
    np.savez_compressed(stem.with_suffix('.npz'),**result)
    meta=dict(signature=signature,run=run_info,timings=timings.report(),sampled_rss_max_mib=max(ram.samples),
        rss_interval_seconds=.05,substeps_per_interval=incoming[3],actual_slice_step_nm=incoming[4],
        array_sha256=hashlib.sha256(stem.with_suffix('.npz').read_bytes()).hexdigest())
    stem.with_suffix('.json').write_text(json.dumps(meta,indent=2))
    print('SAVED',policy,thickness,run_info['wall_seconds'],flush=True)


def compare():
    report={}
    for t in (30,8):
        a=ROOT/f'baseline_t{t:03}';b=ROOT/f'optimized_t{t:03}'
        if not b.with_suffix('.json').exists():continue
        before=json.loads(a.with_suffix('.json').read_text());after=json.loads(b.with_suffix('.json').read_text())
        assert before['signature']['settings']==after['signature']['settings'] and before['signature']['config']==after['signature']['config']
        differences={}
        with np.load(a.with_suffix('.npz')) as x,np.load(b.with_suffix('.npz')) as y:
            for name in x.files:
                np.testing.assert_allclose(y[name],x[name],rtol=2e-14,atol=1e-30,equal_nan=True,err_msg=name)
                finite=np.isfinite(x[name])&np.isfinite(y[name]);d=abs(y[name][finite]-x[name][finite])
                differences[name]=dict(bitwise_equal=np.array_equal(x[name],y[name],equal_nan=True),max_absolute=float(d.max(initial=0)),
                    max_relative=float((d/np.maximum(abs(x[name][finite]),1e-300)).max(initial=0)))
        diagnostic_keys=('incoming_norm_error','outgoing_norm_error','incoming_max_excluded_population','outgoing_max_excluded_population')
        diagnostics={}
        for name in diagnostic_keys:
            # Worker completion order varies. Compare every batch's diagnostic
            # distribution, as well as the final maximum; do not hide smaller
            # changes by checking only the global maximum.
            old_values=np.sort([e['diagnostics'][name] for e in before['run']['events']])
            new_values=np.sort([e['diagnostics'][name] for e in after['run']['events']])
            np.testing.assert_array_equal(old_values,new_values)
            old=old_values[-1];new=new_values[-1]
            np.testing.assert_allclose(new,old,rtol=0,atol=2e-14)
            diagnostics[name]=dict(baseline=old,optimized=new,absolute_difference=abs(new-old),all_batches_bitwise_equal=True)
        old=before['run']['wall_seconds'];new=after['run']['wall_seconds']
        report[str(t)]=dict(baseline_seconds=old,optimized_seconds=new,speedup=old/new,saved_seconds=old-new,
            differences=differences,diagnostics=diagnostics,baseline_sampled_rss_mib=before['sampled_rss_max_mib'],optimized_sampled_rss_mib=after['sampled_rss_max_mib'])
    (ROOT/'comparison.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
    rows=[]
    for t in report:
        for policy in ('baseline','optimized'):
            d=json.loads((ROOT/f'{policy}_t{int(t):03}.json').read_text());r=d['timings']['regions']
            total=d['run']['wall_seconds']+sum(r[k]['wall_inclusive'] for k in ('fft_geometry_potential','incoming_fields','result_assembly'))
            rows.append(dict(thickness_nm=int(t),policy=policy,response_wall_seconds=d['run']['wall_seconds'],
                serial_stage_wall_seconds=total,process_cpu_seconds=d['run']['process_cpu_seconds'],
                outgoing_advance_worker_seconds=r['outgoing_advance']['wall_inclusive'],
                contraction_body_worker_seconds=r['depth_cartesian_contraction']['wall_inclusive'],
                diagnostics_worker_seconds=r['norm_leakage_diagnostics']['wall_inclusive'],
                response_other_worker_seconds=r['response']['wall_exclusive'],sampled_rss_mib=d['sampled_rss_max_mib']))
    if rows:
        with (ROOT/'summary.csv').open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
        np.savez_compressed(ROOT/'summary.npz',**{k:np.asarray([row[k] for row in rows]) for k in rows[0]})


def microbench():
    """Uninstrumented fixed batch repeats; no additional full-field baseline."""
    old=baseline();records=[]
    for thickness in (30,8):
        case=profile.setup();case['settings']=replace(case['settings'],thickness=thickness)
        s=case['settings'];c=case['cfg'];prepared={};expected=None
        query=case['query'][np.linspace(0,len(case['query'])-1,256,dtype=int)]
        for policy,impl in (('baseline',old),('optimized',current)):
            grid=impl.ProjectedNiFFT.build(case['elastic'],grid_points=c.fft_grid,potential_cutoff=s.potential_cutoff,projected_geometry=Ni017Geometry())
            incoming=impl.incident_fields(grid,thickness,depth_steps=c.depth,slice_step_nm=c.slice_step)
            prepared[policy]=(impl,grid,incoming)
        for repeat in range(3):
            for policy in (('baseline','optimized') if repeat%2==0 else ('optimized','baseline')):
                impl,grid,incoming=prepared[policy]
                value,info,_=profile.evaluate_batches(case,query,grid,incoming,4,implementation=impl)
                if expected is None:expected=value.copy()
                else:np.testing.assert_array_equal(value,expected)
                records.append(dict(thickness_nm=thickness,policy=policy,repeat=repeat+1,wall_seconds=info['wall_seconds'],
                    process_cpu_seconds=info['process_cpu_seconds'],directions=len(query),batches=info['batches'],workers=4))
                (ROOT/'uninstrumented_batches.json').write_text(json.dumps(records,indent=2))
                print('BATCH',thickness,policy,info['wall_seconds'],flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--policy',choices=['baseline','optimized']);parser.add_argument('--compare',action='store_true')
    parser.add_argument('--microbench',action='store_true');args=parser.parse_args()
    ROOT.mkdir(parents=True,exist_ok=True)
    if args.policy:
        for thickness in (30,8):run(args.policy,thickness)
    if args.compare:compare()
    if args.microbench:microbench()
