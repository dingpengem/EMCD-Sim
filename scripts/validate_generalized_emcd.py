"""Follow-up projected EMCD study: only new cases, immediately checkpointed.

Milestone-A cases are read as immutable references, never relaunched here.
"""
from dataclasses import asdict,replace
from pathlib import Path
import argparse,hashlib,json,subprocess,time
from emcd_sim.gui.emcd_forward import calculate
from emcd_sim.gui.geometry import Structure
from emcd_sim.gui.project_io import config_from_dict,settings_from_dict,save_project,load_project,fingerprints

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/generalized_multislice_emcd_validation'
PREVIOUS=ROOT/'outputs/general_zolz_multislice_validation'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def baseline(label):
    paths=[p for p in PREVIOUS.glob('*/case.json') if json.loads(p.read_text(encoding='utf-8'))['rows'][0]['case']==label]
    if len(paths)!=1:raise ValueError('Ambiguous/missing immutable reference '+label)
    p=paths[0];d=json.loads(p.read_text(encoding='utf-8'))
    if sha(p.with_name('arrays.npz'))!=d['arrays_sha256']:raise ValueError('Changed baseline '+label)
    return settings_from_dict(d['identity']['settings']),config_from_dict(d['identity']['config'])

def cases():
    s,c=baseline('111_double')
    for n in (65,97):yield '111_grid'+str(n),s,replace(c,grid=n,subpixels=32)
    yield '111_joint',replace(s,beam_cutoff=3.2,potential_cutoff=3.8),replace(c,grid=65,subpixels=128,fft_grid=48,depth=65,slice_step=.01)
    # Exact recorded 8 nm [117] configuration: one explicit equivalence control,
    # not a restart of the historical driver's completed cases.
    p=next((ROOT/'outputs/ni_117_emcd_validation/cases').glob('baseline_full_double_t8_*/case.json'))
    d=json.loads(p.read_text(encoding='utf-8'))
    if sha(p.with_name('arrays.npz'))!=d['arrays_sha256']:raise ValueError('Changed protected [117] reference')
    yield '117_legacy_t8',settings_from_dict(d['identity']['settings']),config_from_dict(d['identity']['config'])
    # Selected native spectrum across the complete source range is exercised
    # through the normal GUI workers in test_generalized_emcd_gui.py.

def case_identity(s,c):
    identity=dict(settings=asdict(s),config=asdict(c),source_sha256=sha(Path(c.source)),
        code_sha256={str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'src/emcd_sim').rglob('*.py'))})
    # JSON stores tuple-valued configuration fields as lists. Compare the same
    # canonical representation on resume, without weakening provenance checks.
    return json.loads(json.dumps(identity))

def run_case(label,s,c):
    folder=OUT/'cases'/label;folder.mkdir(parents=True,exist_ok=True)
    identity=case_identity(s,c)
    done=folder/'case.json'
    if done.exists():
        d=json.loads(done.read_text(encoding='utf-8'))
        if d['identity']!=identity:raise ValueError('Changed case identity; preserve completed case and choose an explicit new label: '+label)
        saved=load_project(folder/'project')
        if fingerprints(saved)!=d['fingerprints']:raise ValueError('Changed checkpoint '+label)
        print('REUSE',label,flush=True);return
    print('RUN',label,flush=True);start=time.perf_counter()
    r=calculate(Structure.nickel(),s,c)
    save_project(r,folder/'project')
    d=dict(identity=identity,complete=True,seconds=time.perf_counter()-start,fingerprints=fingerprints(r),
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),comparison=r['comparison'])
    temp=folder/'case.partial.json';temp.write_text(json.dumps(d,indent=2,allow_nan=False),encoding='utf-8');temp.replace(done)
    print('DONE',label,round(d['seconds'],2),'s',flush=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--only',action='append',default=[]);args=parser.parse_args()
    for label,s,c in cases():
        if not args.only or label in args.only:run_case(label,s,c)

if __name__=='__main__':main()
