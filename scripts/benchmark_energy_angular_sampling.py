"""Small, resumable scheduling benchmark; never a thickness/convergence scan.

Run --probe first. --run compares three unchanged energy samples at the full
configured q grid. The baseline is the exact pre-scheduler GUI source in Git.
"""
import argparse,csv,hashlib,json,os,platform,subprocess,sys,threading,time,types
from contextlib import ExitStack
from dataclasses import asdict,replace
from pathlib import Path
from unittest.mock import patch
import numpy as np
from emcd_sim.gui import emcd_forward as f,channeling,propagation
from emcd_sim.gui.geometry import Structure,Settings,elastic_model,geometry
from emcd_sim.gui.memory_budget import memory_snapshot
from emcd_sim.gui.project_io import save_project,load_project
from emcd_sim.study_geometry import StudyGeometry
Ni017Geometry=lambda a_angstrom=3.524: StudyGeometry((0,1,7),(2,0,0),a_angstrom)
from emcd_sim.geometry import VirtualDetector
from emcd_sim.benchmark import nickel_physical_benchmark
from emcd_sim.double_channeling import prepare_incoming_bloch

BASE='619a1969055ac6d717c092dcf663c3d58062b7e0'
ROOT=Path('outputs/energy_angular_sampling/benchmark')


def configuration():
    # The GUI workspace has no saved physical inputs. Explicitly use its
    # starting [017] finite basis/grid/depth, with the requested 300 kV/8 nm.
    info=f.inspect_source(f.DEFAULT_SOURCE)
    selected=info['selected'];assert selected
    s=Settings(voltage=300,thickness=8,tilt=(Ni017Geometry().bragg_tilt(300),0.))
    c=replace(f.ForwardSettings(),axis_declared=True,source_sha256=info['sha256'],
        l3=selected['L3'],l2=selected['L2'],channeling_model='double',fft_grid=32,slice_step=.5)
    return Structure.nickel(),s,c,np.array([c.l3,(c.l3+c.l2)/2,c.l2])


def baseline():
    for name,file in (('_benchmark_old_channeling','channeling.py'),('_benchmark_old_forward','emcd_forward.py')):
        source=subprocess.check_output(['git','show',BASE+':src/emcd_sim/gui/'+file]).decode('utf-8-sig')
        source=source.replace('..multislice_emcd_reference import','..multislice_reference import')
        source=source.replace('..postedge_emcd_maps import paired_geometry, paired_maps','..emcd_angular_plots import paired_geometry, paired_maps')
        if file=='emcd_forward.py':source=source.replace('from .channeling import contract','from ._benchmark_old_channeling import contract')
        module=types.ModuleType('emcd_sim.gui.'+name);module.__package__='emcd_sim.gui';sys.modules[module.__name__]=module
        exec(compile(source,file,'exec'),module.__dict__)
    return module,sys.modules['emcd_sim.gui._benchmark_old_channeling']


def counts(a,s,c,e):
    elastic=elastic_model(a,s);model=replace(nickel_physical_benchmark(),elastic=elastic,
        detectors={k:VirtualDetector(p,c.radius) for k,p in zip(('A','B'),c.centers)})
    qx,qy,w,support,selected=channeling.angular_schedule(model,c,e)
    points=np.column_stack((qx.ravel(),qy.ravel()))
    unique=lambda p:len(np.unique(np.column_stack((p[:,0],abs(p[:,1]))),axis=0))
    n_full,n_det=qx.size,int(support.sum());u_full,u_det=unique(points),unique(points[support])
    n_energy=len(f.energy_grid(c));n_maps=2
    return model,dict(energy_samples_full=n_energy,energy_samples_benchmark=len(e),full_pixels=n_full,detector_union_pixels=n_det,
        full_unique_directions=u_full,detector_unique_directions=u_det,
        benchmark_old_pixels=len(e)*n_full,benchmark_new_pixels=n_maps*n_full+(len(e)-n_maps)*n_det,
        benchmark_old_outgoing_directions=len(e)*u_full,benchmark_new_outgoing_directions=n_maps*u_full+(len(e)-n_maps)*u_det,
        full_spectrum_old_pixels=n_energy*n_full,full_spectrum_new_pixels=n_maps*n_full+(n_energy-n_maps)*n_det,
        full_spectrum_old_outgoing_directions=n_energy*u_full,full_spectrum_new_outgoing_directions=n_maps*u_full+(n_energy-n_maps)*u_det)


def probe(a,s,c,e,model,work):
    result={}
    q=np.linspace(-c.halfwidth,c.halfwidth,c.grid);qx,qy=np.meshgrid(q,q,indexing='xy')
    query=np.unique(np.column_stack((qx.ravel(),abs(qy.ravel()))),axis=0)
    batch=query[len(query)//2:len(query)//2+32]
    for method in ('bloch','fft-multislice'):
        propagation.numerical_info(a,s,replace(c,propagation=method))
        start=time.perf_counter()
        if method=='bloch':incoming=prepare_incoming_bloch(model.elastic,s.thickness,c.depth)
        else:
            grid=channeling.fft_geometry(model.elastic,s,c)
            incoming=channeling.incident_fields(grid,s.thickness,depth_steps=c.depth,slice_step_nm=c.slice_step)
        incoming_time=time.perf_counter()-start;start=time.perf_counter()
        if method=='bloch':channeling.double_channeling_response(model.elastic,e[1],batch,s.thickness,method='numerical',depth_steps=c.depth,prepared_incoming=incoming)
        else:channeling.multislice_double_channeling_response(model.elastic,e[1],batch,s.thickness,fft_grid=c.fft_grid,
            potential_cutoff=s.potential_cutoff,projected_geometry=Ni017Geometry(),depth_steps=c.depth,slice_step_nm=c.slice_step,
            prepared_grid=grid,prepared_incoming=incoming)
        elapsed=time.perf_counter()-start
        result[method]=dict(probe_directions=len(batch),incoming_seconds=incoming_time,response_seconds=elapsed,
            serial_old_three_energy_response_estimate_seconds=elapsed*work['benchmark_old_outgoing_directions']/len(batch),
            note='Serial extrapolation from one direction batch; actual four-worker scaling and direction/energy costs may differ.')
        print(method,result[method],flush=True)
    return result


def union_seconds(intervals):
    end=-float('inf');total=0.
    for left,right in sorted(intervals):
        total+=max(0.,right-max(end,left));end=max(end,right)
    return total


def run_case(a,s,c,e,method,policy):
    c=replace(c,propagation=method)
    old,old_channel=baseline();forward,adapter=(old,old_channel) if policy=='original' else (f,channeling)
    path=ROOT/(method+'_'+policy)
    signature=dict(settings=asdict(s),config=asdict(c),energy=e.tolist(),baseline=BASE,
        adapter_hashes={p:hashlib.sha256(Path('src/emcd_sim/gui/'+p).read_bytes()).hexdigest() for p in ('channeling.py','emcd_forward.py')})
    signature=json.loads(json.dumps(signature))
    if (path/'benchmark.json').exists():
        meta=json.loads((path/'benchmark.json').read_text());assert meta['signature']==signature
        return load_project(path/'project'),meta
    timing={k:[] for k in ('incoming','outgoing','mdff')};directions=[];rss=[];stop=threading.Event()
    def sampler():
        while not stop.is_set():rss.append(memory_snapshot()['process_rss_mib']);stop.wait(.05)
    def wrapper(fn,category,count=False):
        def measured(*args,**kwargs):
            start=time.perf_counter()
            try:return fn(*args,**kwargs)
            finally:
                timing[category].append((start,time.perf_counter()))
                if count:directions.append(len(args[2]))
        return measured
    thread=threading.Thread(target=sampler,daemon=True);thread.start()
    try:
        with ExitStack() as stack:
            stack.enter_context(patch.object(propagation,'propagate',wrapper(propagation.propagate,'incoming')))
            stack.enter_context(patch.object(adapter,'prepare_incoming_bloch',wrapper(adapter.prepare_incoming_bloch,'incoming')))
            name='double_channeling_response' if method=='bloch' else 'multislice_double_channeling_response'
            stack.enter_context(patch.object(adapter,name,wrapper(getattr(adapter,name),'outgoing',True)))
            stack.enter_context(patch.object(adapter,'intensities_from_response',wrapper(adapter.intensities_from_response,'mdff')))
            start=time.perf_counter()
            result=forward.calculate(a,s,c,lambda stage:print(method,policy,stage,flush=True),energy_ev=e)
            elapsed=time.perf_counter()-start
    finally:stop.set();thread.join()
    meta=dict(signature=signature,wall_seconds=elapsed,incoming_seconds=union_seconds(timing['incoming']),
        outgoing_response_seconds=union_seconds(timing['outgoing']),mdff_contraction_seconds=union_seconds(timing['mdff']),
        outgoing_response_calls=len(directions),outgoing_directions=sum(directions),sampled_rss_max_mib=max(rss),rss_interval_seconds=.05,
        outgoing_note='Response wall intervals include event-kernel construction and depth integration; not isolated FFT/eigensolve time.')
    path.mkdir(parents=True,exist_ok=True);save_project(result,path/'project');(path/'benchmark.json').write_text(json.dumps(meta,indent=2))
    return result,meta


def compare(old,new):
    report={}
    for key,value in old['spectra'].items():
        np.testing.assert_allclose(new['spectra'][key],value,rtol=3e-12,atol=2e-14,equal_nan=True)
        valid=np.isfinite(value)&np.isfinite(new['spectra'][key]);diff=abs(new['spectra'][key][valid]-value[valid])
        report[key]=dict(max_absolute=float(diff.max(initial=0)),max_relative=float((diff/np.maximum(abs(value[valid]),1e-30)).max(initial=0)))
    max_map=0.
    for edge,fields in old['maps'].items():
        for key,value in fields.items():
            np.testing.assert_allclose(new['maps'][edge][key],value,rtol=3e-12,atol=2e-14,equal_nan=True)
            d=abs(new['maps'][edge][key]-value);max_map=max(max_map,float(d[np.isfinite(d)].max(initial=0)))
    return dict(spectra=report,max_map_absolute=max_map)


def write_summary(report):
    rows=[]
    for method,r in report.items():
        for policy in ('original','optimized'):
            t=r[policy]
            rows.append(dict(method=method,policy=policy,**{k:t[k] for k in ('wall_seconds','incoming_seconds',
                'outgoing_response_seconds','mdff_contraction_seconds','outgoing_response_calls','outgoing_directions','sampled_rss_max_mib')}))
    with (ROOT/'summary.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    np.savez_compressed(ROOT/'summary.npz',**{k:np.asarray([row[k] for row in rows]) for k in rows[0]})


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--probe',action='store_true');parser.add_argument('--run',action='store_true')
    parser.add_argument('--method',choices=['bloch','fft-multislice','both'],default='both');args=parser.parse_args()
    ROOT.mkdir(parents=True,exist_ok=True);a,s,c,e=configuration()
    for method in ('bloch','fft-multislice'):propagation.numerical_info(a,s,replace(c,propagation=method))
    model,work=counts(a,s,c,e)
    audit=dict(settings=asdict(s),config=asdict(c),energies=e.tolist(),counts=work,
        environment=dict(platform=platform.platform(),processor=platform.processor(),python=platform.python_version(),numpy=np.__version__,
            openblas_threads=os.environ.get('OPENBLAS_NUM_THREADS'),omp_threads=os.environ.get('OMP_NUM_THREADS')),
        input_note='No saved current physical inputs in the GUI index. Explicit starting [017] geometry/depth/angular settings; requested voltage/thickness/FFT/step applied.')
    (ROOT/'audit.json').write_text(json.dumps(audit,indent=2));print(json.dumps(audit,indent=2),flush=True)
    if args.probe:(ROOT/'probe.json').write_text(json.dumps(probe(a,s,c,e,model,work),indent=2))
    if args.run:
        report={}
        for method in ('bloch','fft-multislice') if args.method=='both' else (args.method,):
            old,old_time=run_case(a,s,c,e,method,'original');new,new_time=run_case(a,s,c,e,method,'optimized')
            report[method]=dict(original=old_time,optimized=new_time,speedup=old_time['wall_seconds']/new_time['wall_seconds'],differences=compare(old,new))
            (ROOT/'comparison.json').write_text(json.dumps(report,indent=2))
        write_summary(report)


if __name__=='__main__':main()
