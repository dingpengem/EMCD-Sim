"""Resumable native-energy spectra using the production GUI/physics adapter."""
import argparse,csv,hashlib,json,time,subprocess
from dataclasses import asdict,replace
from pathlib import Path
import numpy as np
from emcd_sim.gui import emcd_forward as f
from emcd_sim.gui.geometry import Structure
from emcd_sim.gui.project_io import save_project
from emcd_sim.gui.memory_budget import memory_snapshot
from ni_double_channeling_gui_validation import configuration

ROOT=Path('outputs/ni_double_channeling_full_spectra')
PILOT=np.array([826.,831.4778,833.,848.698,850.])
RAW=('I_A_plus','I_B_plus','I_A_minus','I_B_minus')
IMPLEMENTATION=('src/emcd_sim/double_channeling.py','src/emcd_sim/multislice_double_channeling.py',
    'src/emcd_sim/gui/channeling.py','src/emcd_sim/gui/emcd_forward.py','src/emcd_sim/xmcd_effective_mdff.py')


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(zone,t,solver,model,energies,tag):
    s,cfg=configuration(zone,t,model);cfg=replace(cfg,propagation=solver,energy_scope='full')
    energies=f.energy_grid(cfg,energies)  # Source/hash checks also apply to completed-project reuse.
    profile=asdict(cfg)
    for k in ('energy_points','energy_scope','propagation'):profile.pop(k)
    provenance=dict(settings=asdict(s),config=profile,solver=solver,
        implementation={p:digest(p) for p in IMPLEMENTATION})
    identity=hashlib.sha256(json.dumps(provenance,sort_keys=True).encode()).hexdigest()
    folder=ROOT/f'{zone}_{int(t):03}_{model}_{solver}'/'prepared_v1'
    cache=folder/'energies';cache.mkdir(parents=True,exist_ok=True)
    manifest=folder/'profile.json'
    encoded=json.dumps(provenance,sort_keys=True,indent=2)
    if manifest.exists() and manifest.read_text()!=encoded:
        # Compatibility is limited to adding input validation on checkpoint
        # reads. Prove the rest of the adapter bytes and every other hash match.
        old=json.loads(manifest.read_text());candidate=json.loads(encoded)
        path='src/emcd_sim/gui/channeling.py';source=Path(path).read_bytes()
        source=source.replace(b"            raw=np.asarray(cached['raw'])\n",b'').replace(b"            if raw.shape!=(4,) or raw.dtype!=np.float64 or not np.isfinite(raw).all() or np.any(raw<0):raise ValueError('Invalid energy checkpoint detector intensities')\n",b'')
        candidate['implementation'][path]=hashlib.sha256(source).hexdigest()
        if candidate!=old:raise ValueError('Energy checkpoint provenance mismatch: '+str(folder))
        identity=hashlib.sha256(json.dumps(old,sort_keys=True).encode()).hexdigest()
    elif not manifest.exists():manifest.write_text(encoded)
    project=folder/tag
    if project.exists():
        from emcd_sim.gui.project_io import load_project,structures_match
        saved=load_project(project)
        if saved['settings']!=s or saved['config']!=cfg or not np.array_equal(saved['spectra']['energy_ev'],energies):
            raise ValueError('Completed spectrum configuration/energy mismatch: '+str(project))
        if not structures_match(saved['structure_snapshot'],Structure.nickel()):raise ValueError('Completed spectrum crystal mismatch')
        print('Reused completed spectrum:',project,flush=True)
        return saved
    def checkpoint(method,e,data):
        key=hashlib.sha256(float(e).hex().encode()).hexdigest()[:24];path=cache/(key+'.npz')
        if data is None:
            if not path.exists():return None
            with np.load(path,allow_pickle=False) as a:
                if str(a['identity'])!=identity or float(a['energy_ev'])!=e:raise ValueError('Invalid energy checkpoint')
                return dict(raw=a['raw'].copy())
        temp=path.with_suffix('.temporary.npz')
        np.savez_compressed(temp,identity=np.array(identity),energy_ev=np.array(e),raw=data['raw'])
        temp.replace(path)
    start=time.perf_counter();before=memory_snapshot()
    result=f.calculate(Structure.nickel(),s,cfg,lambda stage:print(f'{zone} {t:g} {model} {solver}: {stage}',flush=True),
        energy_ev=energies,energy_checkpoint=checkpoint)
    elapsed=time.perf_counter()-start
    for m in result['methods'].values():
        sp=m['spectra'];np.testing.assert_allclose(sp['D_raw'],sp['D_mag']+sp['D_nonmag'],rtol=1e-10,atol=1e-14)
        assert all(np.isfinite(sp[k]).all() and sp[k].min()>=0 for k in RAW)
    if not project.exists():save_project(result,project)
    spectra=result['spectra']
    with (folder/(tag+'.csv')).open('w',newline='',encoding='utf-8') as stream:
        writer=csv.writer(stream);writer.writerow(['solver','channeling_model']+list(spectra))
        writer.writerows((solver,model,*row) for row in zip(*spectra.values()))
    performance=dict(elapsed_seconds=elapsed,energy_samples=len(energies),ram_before=before,ram_after=memory_snapshot(),
        admission=result['metadata']['memory_admission'],numerics=result['metadata']['numerics'],
        commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),execution_implementation=provenance['implementation'])
    (folder/(tag+'_performance.json')).write_text(json.dumps(performance,indent=2))
    print('SPECTRUM SAVED',project,elapsed,flush=True)
    return result


def fixed_reference(result,zone,t,engine):
    path=Path('outputs/ni_double_channeling_final_200kv/results.npz')
    with np.load(path,allow_pickle=False) as a:
        records={tuple(k):v for k,v in zip(json.loads(str(a['keys_json'])),a['raw'])}
    reference=records[zone,float(t),engine][1]
    e=result['spectra']['energy_ev'];ix=[int(np.argmin(abs(e-v))) for v in (831.4778,848.698)]
    actual=np.column_stack([result['spectra'][k][ix] for k in RAW])
    relative=float(np.max(abs(actual-reference)/np.maximum(abs(actual),abs(reference))))
    assert relative<=.001
    return dict(max_raw_relative=relative,actual=actual.tolist(),reference=reference.tolist())


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=('pilot','bw','bw-pilot','ms','single','ms-full','refine'),required=True)
    parser.add_argument('--case',choices=('001_008','001_012','017_008'));args=parser.parse_args()
    ROOT.mkdir(parents=True,exist_ok=True)
    if args.stage=='pilot':
        results=[run('001',8.,engine,'double',PILOT,'pilot') for engine in ('bloch','fft-multislice')]
        fixed=[fixed_reference(r,'001',8.,engine) for r,engine in zip(results,('bw','ms'))]
        from emcd_sim.gui.prb_benchmark import benchmark_spectra
        a,b=[r['spectra'] for r in results];pa,pb=[benchmark_spectra(s)[0]['prb_relative_dichroism_percent'] for s in (a,b)]
        gap=float(np.nanmax(abs(pa-pb)));raw=float(max(np.max(abs(a[k]-b[k])/np.maximum(abs(a[k]),abs(b[k]))) for k in RAW))
        status=dict(passed=gap<=.01 and raw<=.001,fixed_reference=fixed,max_prb_pp=gap,max_raw_relative=raw,energies_ev=PILOT.tolist())
        (ROOT/'checkpoint_1_pilot.json').write_text(json.dumps(status,indent=2))
        if not status['passed']:raise RuntimeError('Pilot BW/MS gate failed')
    else:
        assert json.loads((ROOT/'checkpoint_1_pilot.json').read_text())['passed']
        for zone,t in (('001',8.),('001',12.),('017',8.)):
            if args.case and args.case!=f'{zone}_{int(t):03}':continue
            s,cfg=configuration(zone,t,'double');cfg=replace(cfg,energy_scope='full')
            energies=f.energy_grid(cfg)
            if args.stage=='refine':
                if not args.case and (zone!='001' or t!=8):continue
                from emcd_sim.wien2k_xmcd import load_wien2k_xmcd
                source=load_wien2k_xmcd(cfg.source);anchors=[]
                for e in (cfg.l3,cfg.l2):
                    ix=np.flatnonzero(abs(source.energy_ev-e)<3)
                    anchors.extend(source.energy_ev[ix[[np.argmax(source.nonmagnetic[ix]),np.argmax(abs(source.dichroic[ix]))]]])
                middle=(energies[1:]+energies[:-1])/2
                middle=middle[(abs(middle-cfg.l3)<1.5)|(abs(middle-cfg.l2)<1.5)]
                energies=np.unique(np.r_[energies,middle,anchors])
            if args.stage in ('ms','bw-pilot'):energies=PILOT
            if args.stage=='ms-full' and (zone!='001' or t!=8):continue
            solver='fft-multislice' if args.stage in ('ms','ms-full') else 'bloch'
            model='single' if args.stage=='single' else 'double'
            if model=='single' and zone=='017' and t==8:
                # Reuse the complete previous Single spectrum only after exact
                # snapshot/configuration/energy checks. Never relabel it Double.
                from emcd_sim.gui.project_io import load_project,structures_match
                old_path=Path('outputs/ni_double_channeling_final_200kv/gui_validation/native_eels_017_single_bw')
                old=load_project(old_path);expected=replace(cfg,propagation='bloch',channeling_model='single')
                if (old['settings']==s and old['config']==expected and np.array_equal(old['spectra']['energy_ev'],energies)
                    and structures_match(old['structure_snapshot'],Structure.nickel())):
                    dest=ROOT/f'{zone}_{int(t):03}_single_bloch'/'prepared_v1';dest.mkdir(parents=True,exist_ok=True)
                    if not (dest/'full').exists():save_project(old,dest/'full')
                    else:
                        saved=load_project(dest/'full')
                        if saved['settings']!=s or saved['config']!=expected:raise ValueError('Reused Single project configuration mismatch')
                        for key,value in old['spectra'].items():np.testing.assert_array_equal(saved['spectra'][key],value)
                    with (dest/'full.csv').open('w',newline='',encoding='utf-8') as stream:
                        writer=csv.writer(stream);writer.writerow(['solver','channeling_model']+list(old['spectra']))
                        writer.writerows(('bloch','single',*row) for row in zip(*old['spectra'].values()))
                    (dest/'reused.json').write_text(json.dumps(dict(source_project=str(old_path),source_sha256=expected.source_sha256,reason='Exact complete Single configuration and energy grid match'),indent=2))
                    print('Reused existing Single full spectrum:',old_path,flush=True);continue
            run(zone,t,solver,model,energies,'refined' if args.stage=='refine' else 'pilot' if args.stage in ('ms','bw-pilot') else 'full')


if __name__=='__main__':main()
