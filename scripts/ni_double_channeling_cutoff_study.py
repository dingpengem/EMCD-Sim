"""Potential-support convergence without changes to either channeling solver.

Run BW screening first, then matched MS, then independent numerical controls.
All detector pixels, tensors, raw-state conventions and precision are inherited
unchanged from the completed benchmark. Each engine/case is atomic/resumable.
"""
import argparse,json,subprocess,time
from dataclasses import replace
from pathlib import Path
import numpy as np
import ni_double_channeling_full_benchmark as base
from emcd_sim.elastic import BeamSet
from emcd_sim.single_channeling_tensor import fcc_site_phase_matrix
from emcd_sim.diffraction import excitation_errors_angstrom_inv
from emcd_sim.double_channeling import (double_channeling_response,outgoing_elastic,BlochStates)
from emcd_sim.multislice_double_channeling import (ProjectedNiFFT,incident_fields,
    multislice_double_channeling_response)
from emcd_sim.multislice_emcd_reference import coherence_from_amplitudes
from emcd_sim.gui.memory_budget import reserve_memory

ROOT=Path('outputs/ni_double_channeling_cutoff_convergence')
OLD=base.ROOT
TIMES=(8.,12.,20.,30.,50.,80.,100.)
CUTOFFS=(2.2,3.,3.8,4.6,5.4,6.2)
TOLERANCES=dict(max_prb_change_pp=.01,max_raw_relative=.001)


def ms_times(cutoff):
    """User-narrowed MS scope; retain completed broader calculations unchanged."""
    return (8.,12.,30.,100.) if cutoff==6.2 else (8.,30.,100.) if cutoff==5.4 else (8.,30.) if cutoff==4.6 else ()


def controls():
    for z in ('001','017'):
        for which in ('bw','ms'):
            yield z,8.,which,'both bases',dict(basis=4.6,out_basis=4.6)
            for label,kwargs in (('incoming basis',dict(basis=4.6,out_basis=3.8)),
                ('outgoing basis',dict(out_basis=4.6)),('both bases',dict(basis=4.6,out_basis=4.6)),('depth513',dict(depth=513))):
                if which=='bw':yield z,30.,which,label,kwargs
                elif label in ('incoming basis','outgoing basis'):yield z,8.,which,label,kwargs
            yield z,100.,which,'depth513',dict(depth=513)
            if which=='ms':
                yield z,8.,which,'fft64',dict(fft=64)
                yield z,8.,which,'step_half',dict(step=.02)
            else:
                yield z,8.,which,'depth513',dict(depth=513)
                yield z,100.,which,'both bases',dict(basis=4.6,out_basis=4.6)
            yield z,12.,which,'both bases',dict(basis=4.6,out_basis=4.6)


def context(zone,cutoff,basis):
    c=base.context(zone,cutoff=cutoff)
    e=c['model'].elastic
    lattice=e.crystal.lattice_angstrom[0,0]
    candidate=tuple((h,0,0) for h in range(-int(np.ceil(basis*lattice)),int(np.ceil(basis*lattice))+1)
        if h%2==0 and abs(h)/lattice<=basis+1e-10) if zone=='001' else c['projected_geometry'].beams(basis).hkl
    hkl=tuple(sorted(candidate,key=lambda h:(round(np.linalg.norm(e.crystal.g_vector(h)),12),h)))
    e=replace(e,beams=BeamSet(hkl))
    c.update(model=replace(c['model'],elastic=e),settings=replace(c['settings'],beam_cutoff=basis),
        hkl=hkl,g=e.reciprocal_vectors_xy,s=excitation_errors_angstrom_inv(e))
    c['phase']=fcc_site_phase_matrix(c['model'])
    return c


def engine(c,d,t,which,*,fft=48,depth=257,step=.04,outgoing=None):
    e=c['model'].elastic;ob=e.beams if outgoing is None else outgoing
    ni=len(e.beams.hkl);no=len(ob.hkl)
    dense=80*(ni*no)**2/2**20
    # Existing BW admission includes its worst-case analytic temporary even for
    # numerical depth. Reserve enough headroom; never override engine admission.
    workers=min(4,max(1,int(1200/(dense+40)))) if which=='bw' else 4
    query,inverse,sign=base.folded_pixels(d.x,d.y)
    raw=np.empty((2,2,4));info=[];out_population=[]
    z=np.linspace(0,t,depth)
    if which=='bw':
        raw[0]=base.study.contract_detectors(c,base.study.analytic_bw_coherence(e,t),t,d)[0]
        psi=e.amplitudes(z);grid=None
    else:
        grid=ProjectedNiFFT.build(e,grid_points=fft,potential_cutoff=c['settings'].potential_cutoff,
            systematic_row=c['systematic_row'],row_reduction=c['systematic_row'],projected_geometry=c['projected_geometry'])
        incoming=incident_fields(grid,t,depth_steps=depth,slice_step_nm=step)
        psi=incoming[0][:,grid.indices(c['hkl'])]
        raw[0]=base.study.contract_detectors(c,coherence_from_amplitudes(incoming[1],psi),t,d)[0]
    samples=1 if grid is None else grid.potential.size
    with reserve_memory(8+64*depth*samples/2**20,2048):
        for ie,energy in enumerate(base.ENERGIES):
            if which=='bw':
                response=base.detector_batches(lambda q:double_channeling_response(e,float(energy),q,t,
                    outgoing_beams=ob,method='analytic' if c['zone_label']=='001' else 'numerical',depth_steps=depth),query,workers)
                diagnostic=dict(detector_workers=workers,conservative_dense_mib=dense)
            else:
                response,diagnostic=base.detector_batches(lambda q:multislice_double_channeling_response(e,float(energy),q,t,
                    outgoing_beams=ob,fft_grid=fft,potential_cutoff=c['settings'].potential_cutoff,
                    systematic_row=c['systematic_row'],row_reduction=c['systematic_row'],projected_geometry=c['projected_geometry'],
                    depth_steps=depth,slice_step_nm=step,prepared_grid=grid,prepared_incoming=incoming),query,workers)
            raw[1,ie]=base.integrate(c,d,base.unfold(response,inverse,sign),ie)
            info.append(diagnostic)
            centers=[]
            for q in c['centers']:
                if which=='bw':
                    eo=outgoing_elastic(e,q,float(energy),ob)
                    reciprocal=BlochStates.solve(eo.hamiltonian_nm_inv(),ob.hkl.index((0,0,0))).ket(z-t)
                else:
                    plan=grid.plan(float(energy),q[None,:]);wave=np.zeros((1,plan.size),complex);wave[:,0]=1
                    reciprocal=np.empty((depth,plan.size),complex);reciprocal[-1]=wave[0]
                    for iz in range(depth-2,-1,-1):
                        wave=plan.advance(wave,incoming[3],-incoming[4]);reciprocal[iz]=wave[0]
                centers.append(np.abs(reciprocal)**2)
            out_population.append(centers)
    incoming_population=np.abs(psi)**2
    return dict(raw=raw,incoming_exit=incoming_population[-1],
        incoming_depth_mean=np.trapezoid(incoming_population,z,axis=0)/t,
        outgoing_depth_mean=np.trapezoid(np.asarray(out_population),z,axis=2)/t,
        outgoing_entrance=np.asarray(out_population)[:,:,0],outgoing_hkl=np.asarray(ob.hkl),
        outgoing_population_hkl=np.asarray(ob.hkl if which=='bw' else grid.hkl),
        diagnostics_json=np.array(json.dumps(base.study.base.clean(info))))


def run_case(zone,t,cutoff=6.2,basis=3.8,which='bw',fft=48,depth=257,step=.04,out_basis=None):
    c=context(zone,cutoff,basis);d=base.detector_grid(c)
    ob=None if out_basis is None else context(zone,cutoff,out_basis)['model'].elastic.beams
    params=base.parameters(c,d,t,fft=fft,depth=depth,step=step)
    params.update(engine=which,outgoing_hkl=c['hkl'] if ob is None else ob.hkl,
        study_script_sha256=PHYSICS_HASH,study='cutoff_convergence_v1')
    tag=f'{zone}_{which}_t{int(t):03}_p{cutoff:g}_b{basis:g}_o{out_basis or basis:g}_f{fft}_d{depth}_s{step:g}'
    path=ROOT/'checkpoints'/(tag+'.npz');existed=path.exists()
    if existed and SCHEDULER_ONLY_EQUIVALENCE:
        with np.load(path,allow_pickle=False) as f:previous=json.loads(str(f['parameters_json']))
        if previous.get('study_script_sha256')==ORIGINAL_PHYSICS_HASH:
            # Only the verified worker-admission formula changed. All other
            # physical/core/tensor/grid parameters still require exact equality.
            params['study_script_sha256']=ORIGINAL_PHYSICS_HASH
    data=base.cached(path,params,lambda:engine(c,d,t,which,fft=fft,depth=depth,step=step,outgoing=ob))
    if not existed:print(tag,f'{float(data["elapsed_seconds"]):.1f}s',base.study.base.observables(data['raw'][1])['prb_relative_dichroism_percent'],flush=True)
    return path,data,params


def rows_and_pairs():
    rows=[];records={}
    for path in sorted((ROOT/'checkpoints').glob('*.npz')):
        with np.load(path) as f:
            p=json.loads(str(f['parameters_json']));raw=f['raw'];cfg=p['settings']
            key=(p['zone'],p['thickness_nm'],cfg['potential_cutoff'],cfg['beam_cutoff'],len(p['outgoing_hkl']),p['fft_grid'],p['depth_steps'],p['maximum_slice_step_nm'])
            records[key+(p['engine'],)]=(raw.copy(),path)
            for im,channel in enumerate(('entrance','double')):
                for r in base.rows_for(raw[im],p['thickness_nm'],p['engine']+'_'+channel):
                    rows.append(dict(zone=p['zone'],potential_cutoff=cfg['potential_cutoff'],beam_cutoff=cfg['beam_cutoff'],
                        incoming_beams=len(p['hkl']),outgoing_beams=len(p['outgoing_hkl']),fft=p['fft_grid'],depth=p['depth_steps'],step=p['maximum_slice_step_nm'],checkpoint=str(path),**r))
    base.study.base.write_csv(ROOT/'observables.csv',rows)
    return rows,records


def comparison(a,b):
    metrics={}
    for im,channel in enumerate(('entrance','double')):
        oa=base.study.base.observables(a[im]);ob=base.study.base.observables(b[im])
        for ie,edge in enumerate(('L3','L2')):
            ra=a[im,ie];rb=b[im,ie]
            metrics[channel+'_'+edge]=dict(prb_change_pp=float(ob['prb_relative_dichroism_percent'][ie]-oa['prb_relative_dichroism_percent'][ie]),
                magnetic_asymmetry_change_pp=float(ob['magnetic_only_percent'][ie]-oa['magnetic_only_percent'][ie]),
                raw_relative=float(np.max(abs(rb-ra)/np.maximum(abs(ra),abs(rb)))),
                raw_absolute=float(np.max(abs(rb-ra))),D_mag_change=float(ob['D_mag'][ie]-oa['D_mag'][ie]))
    return metrics


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=('bw','ms','controls','locations'),required=True);args=parser.parse_args()
    ROOT.mkdir(parents=True,exist_ok=True)
    provenance=ROOT/'provenance.json'
    if not provenance.exists():
        base.study.base.write_json(provenance,dict(base_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            original_benchmark_hashes=base.study.base.file_hashes(OLD),source_sha256=base.digest('data/wien2k_ni/Ni_fm.xmcd'),
            thresholds=TOLERANCES,cutoffs=CUTOFFS,thicknesses=TIMES,basis=3.8,fft=48))
    if args.stage in ('bw','ms'):
        for zone in ('001','017'):
            for cutoff in CUTOFFS:
                for t in TIMES if args.stage=='bw' else ms_times(cutoff):
                    run_case(zone,t,cutoff=cutoff,which=args.stage)
                rows_and_pairs()
    elif args.stage=='controls':
        for zone,t,which,label,kwargs in controls():
            run_case(zone,t,which=which,**kwargs)
            rows_and_pairs()
    else:
        # Local peak competitors and the first entrance-only crossing brackets.
        for zone in ('001','017'):
            for t in (6.,10.,14.,32.,34.,36.):
                run_case(zone,t,which='bw')
                rows_and_pairs()
    rows_and_pairs()
    old=json.loads(provenance.read_text())
    assert base.study.base.file_hashes(OLD)==old['original_benchmark_hashes']
    assert base.digest('data/wien2k_ni/Ni_fm.xmcd')==old['source_sha256']


# Hash only the calculation functions, keeping analysis/report edits resumable.
import inspect,hashlib
ORIGINAL_PHYSICS_HASH='c6669288f4dfdf638416dcf3beccb334990f9f31904814c84654213178938912'
_source=inspect.getsource(context)+inspect.getsource(engine)
PHYSICS_HASH=hashlib.sha256(_source.encode()).hexdigest()
SCHEDULER_ONLY_EQUIVALENCE=hashlib.sha256(_source.replace(
    'workers=min(4,max(1,int(1200/(dense+40))))',
    'workers=min(4,max(1,int(1800/(dense+20))))').encode()).hexdigest()==ORIGINAL_PHYSICS_HASH
if __name__=='__main__':main()
