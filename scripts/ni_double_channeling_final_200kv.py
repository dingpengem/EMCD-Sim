"""Final fixed-profile 200 kV series, sequential and strictly resumable."""
import argparse,json,subprocess
from pathlib import Path
import numpy as np
import ni_double_channeling_uniform_basis as uniform
from emcd_sim.ni_017_geometry import energy_audit

study=uniform.study
ROOT=Path('outputs/ni_double_channeling_final_200kv')
PRIOR=(uniform.PRIOR,uniform.ROOT)
MS_TIMES=(8.,12.,20.,30.,50.,80.,100.)


def case(zone,t,engine):
    tag=f'{zone}_{engine}_t{int(t):03}_p6.2_b4.6_o4.6_f48_d257_s0.04.npz'
    previous=study.ROOT
    try:
        study.ROOT=next((p for p in PRIOR if (p/'checkpoints'/tag).exists()),ROOT)
        if t:
            return study.run_case(zone,t,basis=4.6,which=engine)
        c=study.context(zone,6.2,4.6);d=study.base.detector_grid(c)
        p=study.base.parameters(c,d,0.,fft=48)
        p.update(engine=engine,outgoing_hkl=c['hkl'],study_script_sha256=study.PHYSICS_HASH,
            study='cutoff_convergence_v1',zero_thickness='exact_zero_inelastic_intensity')
        path=ROOT/'checkpoints'/tag
        return path,study.base.cached(path,p,lambda:dict(raw=np.zeros((2,2,4)))),p
    finally:study.ROOT=previous


def save(records):
    rows=[]
    for (zone,t,engine),(path,data,params) in records.items():
        for im,model in enumerate(('single','double')):
            for r in study.base.rows_for(data['raw'][im],t,engine):
                rows.append(dict(zone=zone,channeling_model=model,checkpoint=str(path),**r))
    study.base.study.base.write_csv(ROOT/'observables.csv',rows)
    temporary=ROOT/'results.temporary.npz'
    np.savez_compressed(temporary,keys_json=np.array(json.dumps(list(records))),
        raw=np.array([v[1]['raw'] for v in records.values()]),energies_ev=study.base.ENERGIES)
    temporary.replace(ROOT/'results.npz')
    study.base.study.base.write_json(ROOT/'checkpoint_manifest.json',[
        dict(key=k,path=str(v[0]),sha256=study.base.digest(v[0]),reused=v[0].parent.parent in PRIOR)
        for k,v in records.items()])


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true');args=parser.parse_args()
    ROOT.mkdir(parents=True,exist_ok=True)
    provenance=ROOT/'provenance.json'
    if not provenance.exists():
        audit=energy_audit('data/wien2k_ni/Ni_fm.xmcd')
        validated=json.loads((uniform.ROOT/'provenance.json').read_text())
        assert study.base.digest('data/wien2k_ni/Ni_fm.xmcd')==validated['source_sha256']
        lo,hi=audit['native_bounds_ev']
        assert all(lo<=e<=hi for e in study.base.ENERGIES)
        audit['fixed_benchmark_energies_ev']=study.base.ENERGIES
        audit['energy_selection_note']='Retain validated fixed evaluation energies, not the automatic audit extrema; no shift or thickness-dependent optimization.'
        study.base.study.base.write_json(provenance,dict(start_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            source_sha256=study.base.digest('data/wien2k_ni/Ni_fm.xmcd'),energy_audit=audit,
            prior_output_hashes={str(p):study.base.study.base.file_hashes(p) for p in PRIOR},
            numerical_profile=dict(potential_cutoff=6.2,beam_cutoff=4.6,fft=48,depth_nodes=257,max_step_nm=.04),
            thresholds=study.TOLERANCES,ms_thicknesses_nm=MS_TIMES))
    original=json.loads(provenance.read_text())
    assert study.base.digest('data/wien2k_ni/Ni_fm.xmcd')==original['source_sha256']
    records={}
    for engine,times in (('bw',np.arange(0.,101.,2.)),('ms',(0.,)+MS_TIMES)):
        for t in times:
            for zone in ('001','017'):
                tag=f'{zone}_{engine}_t{int(t):03}_p6.2_b4.6_o4.6_f48_d257_s0.04.npz'
                if not args.run and not any((p/'checkpoints'/tag).exists() for p in PRIOR+(ROOT,)):continue
                records[zone,float(t),engine]=case(zone,float(t),engine)
                save(records)
                print(f'Completed {zone} {engine} {t:g} nm; {len(records)}/118 cases',flush=True)
    for p in PRIOR:assert study.base.study.base.file_hashes(p)==original['prior_output_hashes'][str(p)]
    print('Final benchmark cases:',len(records),flush=True)


if __name__=='__main__':main()
