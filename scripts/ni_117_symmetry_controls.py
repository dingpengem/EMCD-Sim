"""Bounded aperture/mistilt controls, reusing compatible Cartesian responses.

Only missing physical q directions are calculated. The source [001] tensor
and the allowed incident-aligned control are contracted; no [110] case is used.
"""
import argparse,json,time
import numpy as np
import ni_117_magnetization as base


def compatible(old,new):
    keys=('settings','method','channeling','energies_ev','source_sha256','physics_sha256','response_algorithm')
    if any(json.dumps(old.get(k),sort_keys=True)!=json.dumps(new.get(k),sort_keys=True) for k in keys):return False
    return all(old['profile'][k]==new['profile'][k] for k in ('beam','potential','fft','depth','step'))


def run(p,t,offset,method):
    s=base.Settings(zone=(1,1,7),target=(2,-2,0),tilt=(base.Ni117Geometry().bragg_tilt()+offset[0],offset[1]),
        voltage=200,thickness=t,beam_cutoff=p.beam,potential_cutoff=p.potential,basis_mode='full')
    identity=base.identities(p,s,method,'double');identity.pop('analysis_sha256');identity['response_algorithm']='cartesian_response_v1'
    import hashlib
    digest=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()[:12]
    label=f'{p.name}_full_double_t{t}_{method}';folder=base.OUT/'cases'/(label+'_'+digest);folder.mkdir(parents=True,exist_ok=True)
    if (folder/'complete.json').exists():
        d=json.loads((folder/'complete.json').read_text(encoding='utf-8'))
        if base.sha(folder/'arrays.npz')==d['arrays_sha256']:print('REUSE',label,flush=True);return
    cached={};candidates=[];diagnostics=[]
    for meta in (base.OUT/'cases').glob('*/complete.json'):
        d=json.loads(meta.read_text(encoding='utf-8'))
        if not compatible(d['identity'],identity):continue
        path=meta.with_name('arrays.npz')
        if base.sha(path)!=d['arrays_sha256']:raise ValueError('Invalid reusable response')
        with np.load(path) as a:
            for i,q in enumerate(a['q']):cached[tuple(q)]=a['response'][:,i].copy()
        candidates.append(str(meta));diagnostics.extend(d.get('diagnostics',[]))
    start=time.perf_counter();support=base.supports(p);q=support['q'];elastic=base.elastic_model(base.Structure.nickel(),s)
    z=np.linspace(0,t,p.depth);grid=incoming=prepared=None
    if method=='bloch':waves=elastic.amplitudes(z);prepared=base.prepare_incoming_bloch(elastic,t,p.depth)
    else:
        grid=base.ProjectedNiFFT.build(elastic,grid_points=p.fft,potential_cutoff=p.potential,projected_geometry=base.Ni117Geometry())
        incoming=base.incident_fields(grid,t,depth_steps=p.depth,slice_step_nm=p.step);waves=incoming[0][:,grid.indices(elastic.beams.hkl)]
    responses=[];reused=0;calculated=0
    for ie,energy in enumerate(base.ENERGIES):
        chunks=[]
        for i in range(0,len(q),32):
            qb=q[i:i+32];path=folder/f'response_{energy}_{i:05d}.npz'
            if path.exists():
                with np.load(path) as a:np.testing.assert_array_equal(a['q'],qb);r=a['response'].copy()
                chunks.append(r);continue
            known=np.array([tuple(v) in cached for v in qb]);r=np.empty((len(qb),3,3),complex)
            for j in np.flatnonzero(known):r[j]=cached[tuple(qb[j])][ie]
            reused+=int(known.sum());calculated+=int((~known).sum())
            if not known.all():
                if method=='bloch':new=base.double_channeling_response(elastic,energy,qb[~known],t,method='numerical',depth_steps=p.depth,prepared_incoming=prepared)
                else:
                    new,diag=base.multislice_double_channeling_response(elastic,energy,qb[~known],t,fft_grid=p.fft,potential_cutoff=p.potential,
                        depth_steps=p.depth,slice_step_nm=p.step,prepared_grid=grid,prepared_incoming=incoming,projected_geometry=base.Ni117Geometry())
                    diagnostics.append(diag)
                r[~known]=new
            base.write_npz(path,q=qb,response=r);chunks.append(r)
        responses.append(np.concatenate(chunks));print('EDGE',label,energy,'seconds',round(time.perf_counter()-start,1),flush=True)
    arrays=dict(**support,response=np.array(responses),depth_nm=z,waves=waves,coherence=base.coherence_from_amplitudes(z,waves),hkl=np.array(elastic.beams.hkl),g=elastic.reciprocal_vectors_xy)
    axes={k:v for k,v in base.axes(s.tilt).items() if k in ('crystal001','incident')};R=base.Ni117Geometry().frame
    for name,axis in axes.items():
        ts=base.tensors(base.ForwardSettings(axis_declared=True,source=str(base.SOURCE),magnetization=tuple(axis['crystal'])),np.array(base.ENERGIES),R)
        values=np.array([[base.intensities_from_response(r,tensor.tensor_angstrom2_per_ev[e]) for e,r in enumerate(responses)] for tensor in ts])
        if values.min()<-1e-12:raise ValueError('Negative raw intensity')
        arrays[name+'__plus']=values[0];arrays[name+'__minus']=values[1];arrays[name+'__M']=(values[0]-values[1])/2;arrays[name+'__N']=(values[0]+values[1])/2;arrays[name+'__tensor_plus']=ts[0].tensor_angstrom2_per_ev
    base.write_npz(folder/'arrays.npz',**arrays)
    base.write_json(folder/'complete.json',dict(label=label,identity=identity,magnetizations=axes,elapsed_seconds=time.perf_counter()-start,points=len(q),beam_count=len(elastic.beams.hkl),frame=R,
        s_target=float(base.excitation(elastic.crystal.g_vector(s.target)[:2],s.tilt,200)),qz_cycles_angstrom=[-base.characteristic_qz_angstrom_inv(e,200) for e in base.ENERGIES],
        diagnostics=diagnostics,diagnostics_scope='Conservative maxima include any reused compatible supports',reused_response_directions=reused,new_response_directions=calculated,
        reused_cases=candidates,script_sha256=base.sha(__file__),arrays_sha256=base.sha(folder/'arrays.npz')))
    print('DONE',label,'reused',reused,'new',calculated,'seconds',round(time.perf_counter()-start,1),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--only',default='');parser.add_argument('--method',choices=('bloch','fft-multislice'));args=parser.parse_args()
    for p,t,offset in ((base.Profile('aperture129',detector_grid=129),30,(0,0)),
                       (base.Profile('mistilt_dx0.2',map_grid=9),8,(.2,0)),(base.Profile('mistilt_dy0.2',map_grid=9),8,(0,.2))):
        if args.only and args.only not in p.name:continue
        for method in ('bloch','fft-multislice'):
            if args.method and method!=args.method:continue
            run(p,t,offset,method)
