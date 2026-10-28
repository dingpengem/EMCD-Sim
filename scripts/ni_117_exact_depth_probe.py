"""Independent exact-depth BW check on cached circle directions, same physics."""
import argparse,json,time
import numpy as np
from emcd_sim.gui.geometry import Structure,elastic_model
from emcd_sim.gui.project_io import settings_from_dict
from emcd_sim.double_channeling import double_channeling_response,intensities_from_response
from ni_117_magnetization import OUT as CACHE,ROOT,write_json,write_npz,sha


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--thickness',type=int,default=30);parser.add_argument('--stride',type=int,default=15);args=parser.parse_args()
    out=ROOT/'outputs/ni_117_final_symmetry_validation';out.mkdir(parents=True,exist_ok=True)
    label=f'refined_full_double_t{args.thickness}_bloch'
    meta=next((CACHE/'cases').glob(label+'_*/complete.json'));d=json.loads(meta.read_text(encoding='utf-8'))
    target=out/f'exact_depth_t{args.thickness}_stride{args.stride}.npz'
    if target.exists():print('REUSE',target);raise SystemExit(0)
    start=time.perf_counter();elastic=elastic_model(Structure.nickel(),settings_from_dict(d['identity']['settings']))
    with np.load(meta.with_name('arrays.npz')) as a:
        ii=a['circle_index'][::args.stride];q=a['q'][ii];arrays=dict(q=q);rows=[]
        for ie,energy in enumerate(d['identity']['energies_ev']):
            response=double_channeling_response(elastic,energy,q,args.thickness,method='analytic',depth_steps=d['identity']['profile']['depth'])
            T=a['crystal001__tensor_plus'][ie];plus=intensities_from_response(response,T);minus=intensities_from_response(response,T.conj())
            M=(plus-minus)/2;N=(plus+minus)/2;numeric=a['crystal001__M'][ie,ii];nn=a['crystal001__N'][ie,ii]
            scale=max(float(np.linalg.norm(M)),1e-30)
            rows.append(dict(energy_ev=energy,magnetic_relative_l2=float(np.linalg.norm(M-numeric)/scale),
                magnetic_relative_max=float(np.max(abs(M-numeric))/np.max(abs(M))),nonmagnetic_relative_l2=float(np.linalg.norm(N-nn)/np.linalg.norm(N))))
            arrays[f'{energy}__response']=response;arrays[f'{energy}__M_exact']=M;arrays[f'{energy}__M_numerical']=numeric;arrays[f'{energy}__N_exact']=N;arrays[f'{energy}__N_numerical']=nn
    write_npz(target,**arrays)
    write_json(target.with_suffix('.json'),dict(check='Analytic continuous-depth integral versus cached trapezoidal integral at identical physical directions',
        scope='Pointwise circle probe, not a new potential/basis study or a new MDFF',source_case=str(meta),source_case_sha256=sha(meta),
        identity=d['identity'],stride=args.stride,directions=len(q),elapsed_seconds=time.perf_counter()-start,comparisons=rows,arrays_sha256=sha(target)))
    print(rows,flush=True)
