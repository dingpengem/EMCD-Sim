"""Sequential, resumable 200 kV double-channel benchmark and convergence gate.

No extra-voltage production or GUI activation is permitted by a failed gate.
All array precision and primary detector/beam/potential settings are explicit.
"""
import argparse,csv,hashlib,json,subprocess,time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace,asdict
from pathlib import Path
import numpy as np
import ni_prb2007_geometry_validation as study
from ni_double_channeling_bw import rows_for
from emcd_sim.multislice_double_channeling import ProjectedNiFFT,incident_fields,multislice_double_channeling_response
from emcd_sim.double_channeling import double_channeling_response,intensities_from_response
from emcd_sim.multislice_emcd_reference import coherence_from_amplitudes
from emcd_sim.ni_017_geometry import Ni017Geometry
from emcd_sim.diffraction import excitation_errors_angstrom_inv
from emcd_sim.geometry import Microscope
from emcd_sim.elastic import BeamSet
from emcd_sim.single_channeling_tensor import fcc_site_phase_matrix
from emcd_sim.gui.memory_budget import reserve_memory

ROOT=Path('outputs/ni_double_channeling_full_benchmark')
ENERGIES=study.base.ENERGIES
METHODS=('bw_entrance','bw_double','ms_entrance','ms_double')
THICKNESSES=tuple(np.arange(0.,101.,2.))
CORE=('src/emcd_sim/double_channeling.py','src/emcd_sim/multislice_double_channeling.py',
      'src/emcd_sim/physical_elastic.py','src/emcd_sim/single_channeling_tensor.py')


def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def context(zone,kv=200.,cutoff=2.2,beam_cutoff=3.2):
    saved=study.base.load_project('outputs/gui_stage_d/windows_20261016/reference_project')
    saved=dict(saved,settings=replace(saved['settings'],voltage=kv,potential_cutoff=cutoff,beam_cutoff=beam_cutoff))
    row=zone=='001'
    # Build the explicit row directly when its parent 2D GUI preview would
    # exceed the interactive beam limit. No requested row beams are dropped.
    initial=saved if not row or beam_cutoff<=3.2 else dict(saved,settings=replace(saved['settings'],beam_cutoff=3.2))
    c=study.make_context(initial,(0,0,1) if row else (0,1,7),2048,systematic_row=row)
    if row and beam_cutoff>3.2:
        elastic=c['model'].elastic
        bound=int(np.ceil(beam_cutoff*elastic.crystal.lattice_angstrom[0,0]))
        hkl=tuple(sorted(((h,0,0) for h in range(-bound,bound+1)
            if elastic.crystal.is_allowed((h,0,0)) and np.linalg.norm(elastic.crystal.g_vector((h,0,0)))<=beam_cutoff+1e-10),
            key=lambda h:(round(np.linalg.norm(elastic.crystal.g_vector(h)),12),h)))
        elastic=replace(elastic,beams=BeamSet(hkl))
        c.update(settings=replace(c['settings'],beam_cutoff=beam_cutoff),model=replace(c['model'],elastic=elastic),
            hkl=hkl,g=elastic.reciprocal_vectors_xy,s=excitation_errors_angstrom_inv(elastic))
        c['phase']=fcc_site_phase_matrix(c['model'])
    if not row:
        tilt=(Ni017Geometry().bragg_tilt(kv),0.)
        c['settings']=replace(c['settings'],tilt=tilt)
        elastic=replace(c['model'].elastic,microscope=Microscope(kv,tilt))
        c['model']=replace(c['model'],elastic=elastic)
        c['s']=excitation_errors_angstrom_inv(elastic)
    c['zone_label']=zone;c['projected_geometry']=None if row else Ni017Geometry()
    assert abs(c['s'][c['hkl'].index((2,0,0))])<1e-12
    assert c['cfg'].eta==c['cfg'].beta==1
    return c


def detector_grid(c,n=193):return study.DetectorGrid(c['centers'],(c['cfg'].radius,),n,.5,64)


def parameters(c,d,t,*,depth=257,step=.04,fft=32):
    return dict(zone=c['zone_label'],settings=asdict(c['settings']),thickness_nm=float(t),
        source_sha256=c['cfg'].source_sha256,hkl=c['hkl'],frame=c['R'],
        tensor=np.asarray([x.tensor_angstrom2_per_ev for x in c['ts']]).view(float),
        energies_ev=ENERGIES,depth_steps=depth,maximum_slice_step_nm=step,fft_grid=fft,
        detector_grid=d.grid,halfwidth=d.halfwidth,subpixels=d.subpixels,areas=d.areas,
        centers=c['centers'],radius=c['cfg'].radius,eta=1.,beta=1.,budget_mib=2048,
        bw_depth_method='analytic' if c['zone_label']=='001' else 'numerical',
        transverse_mirror_reuse=True,site_grouping=True,
        implementation_sha256={p:digest(p) for p in CORE})


def cached(path,params,producer):
    path.parent.mkdir(parents=True,exist_ok=True)
    encoded=json.dumps(study.base.clean(params),sort_keys=True)
    if path.exists():
        with np.load(path,allow_pickle=False) as f:
            if str(f['parameters_json'])!=encoded:raise ValueError(f'Checkpoint provenance mismatch: {path}')
            return {k:f[k].copy() for k in f.files if k!='parameters_json'}
    start=time.perf_counter();data=producer();data['elapsed_seconds']=np.array(time.perf_counter()-start)
    temporary=path.with_suffix('.temporary.npz')
    np.savez_compressed(temporary,parameters_json=np.array(encoded),**data)
    temporary.replace(path)
    return data


def folded_pixels(x,y):
    # Exact floating coordinates are retained; no map interpolation/quantization.
    unique,inverse=np.unique(np.column_stack((x,abs(y))),axis=0,return_inverse=True)
    sign=np.ones((len(x),3));sign[y<0,1]=-1
    return unique,inverse,sign


def unfold(response,inverse,sign):return response[inverse]*sign[:,:,None]*sign[:,None,:]


def integrate(c,d,response,ie):
    return np.concatenate([np.einsum('dp,p->d',d.w[0],
        intensities_from_response(response,c['ts'][rev].tensor_angstrom2_per_ev[ie]))*d.dq2 for rev in (0,1)])


def detector_batches(function,query,workers=4):
    """Independent detector directions in fixed ordered chunks, never thickness jobs.

    Each engine call keeps its own existing RAM reservation; active reservations
    are included when admitting further workers. No reduction crosses workers.
    """
    chunks=[q for q in np.array_split(query,min(workers,len(query))) if len(q)]
    with ThreadPoolExecutor(max_workers=len(chunks)) as pool:
        results=list(pool.map(function,chunks))
    if isinstance(results[0],tuple):
        responses,diagnostics=zip(*results)
        return np.concatenate(responses),dict(detector_workers=len(chunks),workers=diagnostics)
    return np.concatenate(results)


def calculate(c,d,t,*,depth=257,step=.04,fft=32,reuse_bw=None):
    n=len(c['hkl']);raw=np.zeros((4,2,4));elastic=c['model'].elastic
    if t==0:
        population=np.zeros(n);population[c['hkl'].index((0,0,0))]=1
        return dict(raw=raw,elastic_bw=population,elastic_ms=population.copy(),diagnostics_json=np.array('[]'))
    # Reserve the retained potential/incident arrays before preparing fields.
    samples=fft if c['systematic_row'] else fft**2
    with reserve_memory(8+64*depth*samples/2**20,2048):
        grid=ProjectedNiFFT.build(elastic,grid_points=fft,potential_cutoff=c['settings'].potential_cutoff,
            systematic_row=c['systematic_row'],row_reduction=c['systematic_row'],projected_geometry=c['projected_geometry'])
        incoming=incident_fields(grid,t,depth_steps=depth,slice_step_nm=step)
        psi=incoming[0][:,grid.indices(c['hkl'])]
        raw[2]=study.contract_detectors(c,coherence_from_amplitudes(incoming[1],psi),t,d)[0]
        raw[0]=study.contract_detectors(c,study.analytic_bw_coherence(elastic,t),t,d)[0] if reuse_bw is None else reuse_bw[0]
        query,inverse,sign=folded_pixels(d.x,d.y)
        diagnostics=[]
        for ie,e in enumerate(ENERGIES):
            workers=1 if c['zone_label']=='001' else 4
            if reuse_bw is None:
                bw=detector_batches(lambda q:double_channeling_response(elastic,float(e),q,t,
                    method='analytic' if c['zone_label']=='001' else 'numerical',depth_steps=depth),query,workers)
                raw[1,ie]=integrate(c,d,unfold(bw,inverse,sign),ie)
            else:raw[1,ie]=reuse_bw[1,ie]
            ms,info=detector_batches(lambda q:multislice_double_channeling_response(elastic,float(e),q,t,
                fft_grid=fft,potential_cutoff=c['settings'].potential_cutoff,
                systematic_row=c['systematic_row'],row_reduction=c['systematic_row'],depth_steps=depth,
                slice_step_nm=step,prepared_grid=grid,prepared_incoming=incoming,projected_geometry=c['projected_geometry']),query,1 if c['zone_label']=='001' else 8)
            raw[3,ie]=integrate(c,d,unfold(ms,inverse,sign),ie)
            diagnostics.append(info)
        assert raw.min()>=-1e-13
        return dict(raw=raw,cpu_detector_workers=np.array(1 if c['zone_label']=='001' else 8),cpu_bw_detector_workers=np.array(1 if c['zone_label']=='001' else 4),cpu_ms_detector_workers=np.array(1 if c['zone_label']=='001' else 8),elastic_bw=abs(elastic.amplitudes(np.array([t]))[0])**2,
            elastic_ms=abs(psi[-1])**2,diagnostics_json=np.array(json.dumps(study.base.clean(diagnostics))))


def output_rows(c,t,data):
    rows=[]
    for im,method in enumerate(METHODS):
        for row in rows_for(data['raw'][im],t,method):
            rows.append(dict(zone=c['zone_label'],voltage_kv=c['settings'].voltage,cpu_detector_workers=int(data.get('cpu_bw_detector_workers' if method.startswith('bw') else 'cpu_ms_detector_workers',data.get('cpu_detector_workers',1))),**row))
    return rows


def save_scan(c,d):
    folder=ROOT/c['zone_label'];rows=[];thickness=[];raw=[];bw=[];ms=[];times=[]
    for t in THICKNESSES:
        path=folder/'checkpoints'/f't{int(t):03d}.npz'
        if not path.exists():continue
        data=cached(path,parameters(c,d,t),lambda:None)
        rows.extend(output_rows(c,t,data));thickness.append(t);raw.append(data['raw'])
        bw.append(data['elastic_bw']);ms.append(data['elastic_ms']);times.append(float(data['elapsed_seconds']))
    if rows:
        study.base.write_csv(folder/'results.csv',rows)
        np.savez_compressed(folder/'results.npz',thickness_nm=thickness,raw=raw,elastic_bw=bw,elastic_ms=ms,
            hkl=c['hkl'],method_labels=METHODS,energy_ev=ENERGIES,elapsed_seconds=times,
            configuration_json=json.dumps(study.base.clean(parameters(c,d,0.))))
    return rows


def reproduce(c,d):
    # Re-execute, rather than merely read, the four recorded points at their settings.
    baseline=Path('outputs/ni_double_channeling_ms_validation')
    meta=json.loads((baseline/'configuration.json').read_text())
    assert meta['source_sha256']==c['cfg'].source_sha256
    assert meta['parameters']['hkl']==study.base.clean(c['hkl'])
    assert meta['parameters']['settings']==study.base.clean(asdict(c['settings']))
    assert meta['parameters']['energies_ev']==list(ENERGIES)
    np.testing.assert_array_equal(meta['detector_areas'],d.areas)
    checks=[]
    for t in (10.,12.,20.,30.):
        data=cached(ROOT/'reproduction'/f't{int(t)}.npz',parameters(c,d,t),lambda t=t:calculate(c,d,t))
        with np.load('outputs/ni_double_channeling_bw/t'+f'{int(t):02d}.npz') as old_bw:
            expected_bw=old_bw['double']
        with np.load(baseline/'checkpoints'/f'primary_t{int(t)}.npz') as old_ms:expected_ms=old_ms['raw']
        for method,actual,expected in (('bw',data['raw'][1],expected_bw),('ms',data['raw'][3],expected_ms)):
            np.testing.assert_allclose(actual,expected,rtol=2e-12,atol=1e-14)
            ap=study.base.observables(actual);ep=study.base.observables(expected)
            checks.append(dict(t_nm=t,solver=method,max_raw_absolute=float(abs(actual-expected).max()),
                max_prb_difference_pp=float(abs(ap['prb_relative_dichroism_percent']-ep['prb_relative_dichroism_percent']).max())))
        print('Reproduced four raw reversal states, both edges:',t,flush=True)
    study.base.write_csv(ROOT/'reference_reproduction.csv',checks)


def stage_a():
    primary=context('001');d=detector_grid(primary)
    reproduce(primary,d)
    rows=[]
    for zone in ('001','017'):
        c=context(zone);d=detector_grid(c);folder=ROOT/zone
        study.base.write_json(folder/'configuration.json',parameters(c,d,0.)) if folder.exists() else None
        for t in THICKNESSES:
            path=folder/'checkpoints'/f't{int(t):03d}.npz'
            reuse=ROOT/'reproduction'/f't{int(t)}.npz' if zone=='001' and t in (10.,12.,20.,30.) else None
            existed=path.exists()
            data=cached(path,parameters(c,d,t),lambda c=c,d=d,t=t,reuse=reuse:
                cached(reuse,parameters(c,d,t),lambda:None) if reuse is not None else calculate(c,d,t))
            save_scan(c,d)
            v=study.base.observables(data['raw'][3])['prb_relative_dichroism_percent']
            if not existed:print(f'A {zone} {t:5.1f} nm | MS double {v} | {float(data["elapsed_seconds"]):.2f}s',flush=True)
        study.base.write_json(folder/'configuration.json',parameters(c,d,0.))
        rows.extend(save_scan(c,d))
    study.base.write_csv(ROOT/'results_200kv.csv',rows)
    study.base.write_json(ROOT/'checkpoint_a.json',dict(complete=True,geometries=['001','017'],thickness_points=51,
        voltage_kv=200,primary_settings_fixed=True,methods=METHODS))


def stage_b():
    assert json.loads((ROOT/'checkpoint_a.json').read_text())['complete']
    controls=[];summaries=[]
    # Predeclared resolution for resolving sub-0.1 pp changes: 0.01 pp and 0.1% raw.
    tolerances=dict(max_prb_change_pp=.01,max_raw_relative=.001)
    for zone in ('001','017'):
        c=context(zone);d=detector_grid(c)
        with np.load(ROOT/zone/'results.npz') as f:raw=f['raw'];ts=f['thickness_nm']
        contrast=np.array([study.base.observables(x[1])['prb_relative_dichroism_percent'][0] for x in raw])
        peak=float(ts[np.nanargmax(abs(contrast))]);cross=np.flatnonzero(contrast[1:-1]*contrast[2:]<0)+1
        crossing_curve='bw_double'
        if not len(cross):
            entrance=np.array([study.base.observables(x[0])['prb_relative_dichroism_percent'][0] for x in raw])
            cross=np.flatnonzero(entrance[1:-1]*entrance[2:]<0)+1
            crossing_curve='bw_entrance'
        near=float(ts[cross[0]]) if len(cross) else float(ts[1:][np.nanargmin(abs(contrast[1:]))])
        if not len(cross):crossing_curve='weakest sampled double signal; no crossing'
        selected=sorted(set((peak,near,80.,100.)))
        for t in selected:
            base=cached(ROOT/zone/'checkpoints'/f't{int(t):03d}.npz',parameters(c,d,t),lambda:None)['raw']
            settings=[('depth513',c,d,dict(depth=513)),('step_half',c,d,dict(step=.02))]
            if t in (peak,near):
                settings.extend([('potential2p6',context(zone,cutoff=2.6),d,{}),
                    ('potential3p0',context(zone,cutoff=3.),d,{}),
                    ('basis3p8',context(zone,beam_cutoff=3.8),d,{}),
                    ('fft48',c,d,dict(fft=48)),('detector385',c,detector_grid(c,385),{})])
            for name,cc,dd,kwargs in settings:
                params=parameters(cc,dd,t,**kwargs)
                reusable_bw=base[:2] if name in ('step_half','fft48') or (name=='depth513' and zone=='001') else None
                if reusable_bw is not None:
                    params['BW_reused_from_checkpoint_sha256']=digest(ROOT/zone/'checkpoints'/f't{int(t):03d}.npz')
                data=cached(ROOT/zone/'controls'/f'{name}_t{int(t)}.npz',params,
                    lambda cc=cc,dd=dd,t=t,kwargs=kwargs,reusable_bw=reusable_bw:calculate(cc,dd,t,reuse_bw=reusable_bw,**kwargs))
                for im,method in enumerate(METHODS):
                    a=study.base.observables(base[im]);b=study.base.observables(data['raw'][im])
                    for ie,edge in enumerate(('L3','L2')):
                        reference=base[im,ie];actual=data['raw'][im,ie]
                        controls.append(dict(zone=zone,t_nm=t,control=name,solver=method,edge=edge,
                            raw_max_absolute=float(abs(actual-reference).max()),raw_max_relative=float(np.max(abs(actual-reference)/np.maximum(abs(actual),abs(reference)))),
                            prb_change_pp=float(b['prb_relative_dichroism_percent'][ie]-a['prb_relative_dichroism_percent'][ie]),
                            magnetic_difference_change=float(b['D_mag'][ie]-a['D_mag'][ie]),
                            even_difference_change=float(b['D_even'][ie]-a['D_even'][ie])))
                study.base.write_csv(ROOT/'convergence.csv',controls)
                print('B',zone,t,name,'max pp',max(abs(r['prb_change_pp']) for r in controls[-8:]),flush=True)
        summaries.append(dict(zone=zone,peak_thickness_nm=peak,first_crossing_left_nm=near,crossing_curve=crossing_curve,control_thicknesses_nm=selected))
    maximum_pp=max(abs(r['prb_change_pp']) for r in controls)
    maximum_raw=max(r['raw_max_relative'] for r in controls)
    passed=maximum_pp<=tolerances['max_prb_change_pp'] and maximum_raw<=tolerances['max_raw_relative']
    gate=dict(passed=passed,tolerances=tolerances,maximum_prb_change_pp=maximum_pp,maximum_raw_relative=maximum_raw,
        selected=summaries,additional_voltages='not run' if not passed else 'eligible',
        gui='not integrated' if not passed else 'eligible',reason='All numerical and physical-cutoff controls must pass; primary settings are not adjusted.')
    study.base.write_json(ROOT/'convergence_gate.json',gate)
    print('200 kV convergence gate:',gate,flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=('a','b','all'),default='all');args=parser.parse_args()
    ROOT.mkdir(exist_ok=True,parents=True)
    provenance=ROOT/'provenance.json'
    if not provenance.exists():
        study.base.write_json(provenance,dict(base_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            previous_hashes={str(p):study.base.file_hashes(p) for p in
                (Path('outputs/ni_double_channeling_bw'),Path('outputs/ni_double_channeling_ms_validation'),Path('outputs/ni_voltage_dependence_100_200_300kv'))},
            source_sha256=digest('data/wien2k_ni/Ni_fm.xmcd')))
    if args.stage in ('a','all'):stage_a()
    if args.stage in ('b','all'):stage_b()
    old=json.loads(provenance.read_text())
    for folder,mapping in old['previous_hashes'].items():assert study.base.file_hashes(Path(folder))==mapping
    assert digest('data/wien2k_ni/Ni_fm.xmcd')==old['source_sha256']


if __name__=='__main__':main()
