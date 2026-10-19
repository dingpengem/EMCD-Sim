"""One fixed Ni [017] Double L3 case, nested real samples, resumable chunks.

No interpolation, production writes, energy scan or solver modifications.
"""
import argparse,csv,hashlib,json,subprocess,threading,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
import ni_emcd_complete_thickness as baseline
from emcd_sim.double_channeling import double_channeling_response,intensities_from_response,prepare_incoming_bloch
from emcd_sim.multislice_double_channeling import ProjectedNiFFT,incident_fields,multislice_double_channeling_response
from emcd_sim.gui.memory_budget import memory_snapshot,assess_memory,reserve_memory
from emcd_sim.geometry import VirtualDetector

ROOT=Path('outputs/angular_resolution_convergence')
ENERGY=831.4778
BUDGET=4096


def atomic_npz(path,**data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.temporary.npz');np.savez_compressed(temporary,**data);temporary.replace(path)


def fields(plus,minus):
    m=(plus-minus)/2;n=(plus+minus)/2;den=plus+plus[::-1]
    floor=1e-6*np.percentile(den[den>0],95) if np.any(den>0) else 0
    ratio=np.divide(100*(plus-plus[::-1]),den,out=np.full_like(plus,np.nan),where=np.isfinite(den)&(den>floor))
    return dict(I_plus=plus,I_minus=minus,D_mag=m-m[::-1],D_nonmag=n-n[::-1],asymmetry=ratio,denominator=den)


def detector_values(qx,qy,plus,minus,c):
    weights=np.array([VirtualDetector(tuple(p),c['cfg'].radius).integration_weights(qx,qy,mode='fractional',subpixels=64) for p in c['centers']])
    dq2=(qx[0,1]-qx[0,0])**2
    ap,bp=np.einsum('dij,ij->d',weights,plus)*dq2
    am,bm=np.einsum('dij,ij->d',weights,minus)*dq2
    na,nb=(ap+am)/2,(bp+bm)/2;ma,mb=(ap-am)/2,(bp-bm)/2
    return dict(I_A_plus=ap,I_B_plus=bp,I_A_minus=am,I_B_minus=bm,D_mag=ma-mb,D_nonmag=na-nb,
        A_raw=100*(ap-bp)/(ap+bp),A_mag=100*(ma-mb)/(na+nb),A_nonmag=100*(na-nb)/(na+nb),
        area_A=weights[0].sum()*dq2,area_B=weights[1].sum()*dq2)


def cache_read(folder,signature):
    cache={};elapsed=0
    for path in sorted(folder.glob('chunk_*.npz')):
        if path.name.endswith('.temporary.npz'):continue
        with np.load(path,allow_pickle=False) as f:
            assert str(f['signature'])==signature,str(path)
            for i,response in zip(f['indices'],f['response']):
                if int(i) in cache:np.testing.assert_array_equal(cache[int(i)],response)
                cache[int(i)]=response.copy()
            elapsed+=float(f['seconds'])
    return cache,elapsed


def produce(c,method,run):
    q=(np.arange(193,dtype=float)-96)/192
    # Exact reflection of the actual coordinates; same allowed symmetry used by production.
    signature=baseline.encode(dict(parameters=baseline.parameters(c,baseline.study.base.detector_grid(c),8,method),
        energy_ev=ENERGY,budget_mib=BUDGET,coordinate_axis=q.tolist(),kind='full_field_double_L3_v1'))
    folder=ROOT/'chunks'/method;folder.mkdir(parents=True,exist_ok=True)
    cache,total_time=cache_read(folder,signature);counter=sum(not p.name.endswith('.temporary.npz') for p in folder.glob('chunk_*.npz'))
    elastic=c['model'].elastic;peak=[memory_snapshot()['process_rss_mib']];stop=threading.Event()
    def monitor():
        while not stop.wait(.25):peak[0]=max(peak[0],memory_snapshot()['process_rss_mib'])
    monitor_thread=threading.Thread(target=monitor,daemon=True);monitor_thread.start()
    incoming=None;grid=None
    if method=='bw':
        estimate=80*len(c['hkl'])**4/2**20+48
        workers=1
    else:
        estimate=4*(96*32*len(c['hkl'])**2/2**20+(64*257*48**2+192*32*48**2)/2**20+16)
        workers=4
    admission=assess_memory(estimate,BUDGET)
    def response(indices):
        xy=np.array([(q[int(i)%193],q[int(i)//193]) for i in indices]);start=time.perf_counter()
        if method=='bw':
            value=double_channeling_response(elastic,ENERGY,xy,8,method='numerical',depth_steps=257,
                memory_budget_mib=BUDGET,prepared_incoming=incoming)
        else:
            value,_=multislice_double_channeling_response(elastic,ENERGY,xy,8,fft_grid=48,potential_cutoff=6.2,
                depth_steps=257,slice_step_nm=.04,projected_geometry=c['projected_geometry'],
                prepared_grid=grid,prepared_incoming=incoming,memory_budget_mib=BUDGET)
        return indices,value,time.perf_counter()-start
    try:
        for n in (33,97,193):
            step=192//(n-1);axis=np.arange(0,193,step)
            required=[int(y*193+x) for y in axis if y>=96 for x in axis]
            missing=[i for i in required if i not in cache]
            if missing and incoming is None:
                if method=='bw':incoming=prepare_incoming_bloch(elastic,8,257)
                else:
                    grid=ProjectedNiFFT.build(elastic,grid_points=48,potential_cutoff=6.2,projected_geometry=c['projected_geometry'])
                    incoming=incident_fields(grid,8,depth_steps=257,slice_step_nm=.04)
            batches=[np.array(missing[i:i+32],dtype=int) for i in range(0,len(missing),32)]
            # The first chunk is the retained runtime profile, not a duplicate job.
            if batches:
                start=time.perf_counter();ids,value,seconds=response(batches.pop(0))
                atomic_npz(folder/f'chunk_{counter:04}.npz',indices=ids,response=value,seconds=seconds,signature=np.array(signature));counter+=1
                cache.update(zip(map(int,ids),value));total_time+=seconds
                remaining=sum(map(len,batches));estimate_seconds=seconds/len(ids)*remaining/workers
                (ROOT/f'{method}_runtime_estimate.json').write_text(json.dumps(dict(grid=n,measured_chunk_seconds=seconds,
                    measured_pixels=len(ids),remaining_pixels=remaining,workers=workers,estimated_remaining_seconds=estimate_seconds,
                    uncertainty_seconds=[.5*estimate_seconds,2*estimate_seconds],admission=admission),indent=2))
                print(f'{method} {n}: profile {len(ids)} actual points {seconds:.2f}s; remaining estimate {estimate_seconds/60:.1f} min',flush=True)
                if not run:return
                with ThreadPoolExecutor(max_workers=workers) as pool:
                    for ids,value,seconds in pool.map(response,batches):
                        atomic_npz(folder/f'chunk_{counter:04}.npz',indices=ids,response=value,seconds=seconds,signature=np.array(signature));counter+=1
                        cache.update(zip(map(int,ids),value));total_time+=seconds
                        (ROOT/f'{method}_progress.json').write_text(json.dumps(dict(method=method,grid=n,completed=len(set(required)&cache.keys()),required=len(required),peak_sampled_rss_mib=peak[0])))
                wall=time.perf_counter()-start
            else:wall=0
            x,y=np.meshgrid(q[axis],q[axis]);response_array=np.array([cache[int(max(iy,192-iy)*193+ix)] for iy in axis for ix in axis])
            sign=np.ones((n*n,3));sign[y.ravel()<0,1]=-1
            response_array=response_array*sign[:,:,None]*sign[:,None,:]
            plus,minus=[intensities_from_response(response_array,t.tensor_angstrom2_per_ev[0]).reshape(n,n) for t in c['ts']]
            assert np.isfinite(plus).all() and plus.min()>=0 and minus.min()>=0
            atomic_npz(ROOT/f'{method}_{n}.npz',qx=x,qy=y,**fields(plus,minus),
                detector_json=np.array(json.dumps(detector_values(x,y,plus,minus,c))),signature=np.array(signature),
                cumulative_cpu_chunk_seconds=total_time,stage_wall_seconds=wall,peak_sampled_rss_mib=peak[0])
            print(f'{method} {n}: saved full {n*n} real samples; peak sampled RSS {peak[0]:.1f} MiB',flush=True)
    finally:stop.set();monitor_thread.join()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true');parser.add_argument('--method',choices=('bw','ms'));args=parser.parse_args()
    ROOT.mkdir(exist_ok=True)
    hashes=json.loads(Path('outputs/ni_emcd_thickness_scientific_audit/production_hashes.json').read_text())
    assert len(hashes)==204 and all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==v for p,v in hashes.items())
    aliases,audit=baseline.implementation_audit();c=baseline.study.context('017',6.2,4.6)
    records,rejected=baseline.inventory(baseline.contexts(),aliases)
    assert len(records)==204 and not rejected
    expected=baseline.parameters(c,baseline.study.base.detector_grid(c),8,'bw')
    assert baseline.compatible(records['017',8,'bw']['parameters'],expected,aliases)
    provenance=dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        setup=baseline.parameters(c,baseline.study.base.detector_grid(c),8,'bw'),source_audit=audit,
        numerical_policy='Nested exactly symmetric rational grids; common samples reused without interpolation. Cartesian response symmetry, not forced symmetry of magnetized intensities.',
        memory_budget_mib=BUDGET,energy_ev=ENERGY)
    (ROOT/'provenance.json').write_text(json.dumps(provenance,indent=2))
    for method in ([args.method] if args.method else ('bw','ms')):produce(c,method,args.run)
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==v for p,v in hashes.items())


if __name__=='__main__':main()
