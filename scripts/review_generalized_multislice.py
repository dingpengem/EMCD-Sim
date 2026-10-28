"""Minimal detector-only review controls; historical fields stay immutable."""
from dataclasses import asdict,replace
from pathlib import Path
import argparse,hashlib,json,subprocess,time
from emcd_sim.gui.emcd_forward import calculate
from emcd_sim.gui.geometry import Structure
from emcd_sim.gui.project_io import load_project,save_project,fingerprints

ROOT=Path(__file__).resolve().parents[1]
PREVIOUS=ROOT/'outputs/generalized_multislice_emcd_validation/cases'
OUT=ROOT/'outputs/generalized_multislice_merge_review'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def requests():
    base=load_project(PREVIOUS/'111_grid65/project');joint=load_project(PREVIOUS/'111_joint/project')
    s=base['settings'];c=replace(base['config'],angular_maps=False,subpixels=128)
    yield 'beam_only',replace(s,beam_cutoff=3.2),c
    yield 'potential_only',replace(s,potential_cutoff=3.8),c
    yield 'support_only',replace(s,beam_cutoff=3.2,potential_cutoff=3.8),c
    yield 'higher_basis_ms',replace(joint['settings'],beam_cutoff=3.8),replace(joint['config'],angular_maps=False,propagation='fft-multislice')
    yield 'higher_potential_ms',replace(joint['settings'],beam_cutoff=3.8,potential_cutoff=4.6),replace(joint['config'],angular_maps=False,propagation='fft-multislice')

def run(label,s,c):
    folder=OUT/'cases'/label;folder.mkdir(parents=True,exist_ok=True)
    identity=json.loads(json.dumps(dict(settings=asdict(s),config=asdict(c),source_sha256=sha(Path(c.source)),
        code_sha256={str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'src/emcd_sim').rglob('*.py'))})))
    meta=folder/'case.json'
    if meta.exists():
        saved=json.loads(meta.read_text(encoding='utf-8'))
        if saved['identity']!=identity:raise ValueError('Changed case identity; select a new explicit label')
        if fingerprints(load_project(folder/'project'))!=saved['fingerprints']:raise ValueError('Changed saved arrays')
        print('REUSE',label,flush=True);return
    print('RUN',label,flush=True);start=time.perf_counter()
    result=calculate(Structure.nickel(),s,c);save_project(result,folder/'project')
    record=dict(complete=True,identity=identity,fingerprints=fingerprints(result),seconds=time.perf_counter()-start,
        commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True,cwd=ROOT).strip(),comparison=result['comparison'])
    partial=folder/'case.partial.json';partial.write_text(json.dumps(record,indent=2,allow_nan=False),encoding='utf-8');partial.replace(meta)
    print('DONE',label,round(record['seconds'],2),'s',flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--only',action='append',default=[]);args=p.parse_args()
    for label,s,c in requests():
        if not args.only or label in args.only:run(label,s,c)

if __name__=='__main__':main()
