"""Small, checkpointed Milestone-A comparisons; never touches old studies."""
from dataclasses import asdict,replace
from pathlib import Path
import csv,hashlib,json,subprocess,time
import numpy as np
from emcd_sim.crystal import fcc_nickel
from emcd_sim.projected_geometry import ProjectedGeometry
from emcd_sim.gui.geometry import Structure,Settings
from emcd_sim.gui.emcd_forward import ForwardSettings,calculate,DEFAULT_SOURCE
from emcd_sim.gui.prb_benchmark import benchmark_spectra

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/general_zolz_multislice_validation'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def cases():
    for name,zone,target,beam,potential in [
        ('001',(0,0,1),(2,0,0),1.8,2.2),('017',(0,1,7),(2,0,0),3.2,2.2),
        ('117',(1,1,7),(2,-2,0),3.2,3.8),('111',(1,1,1),(2,-2,0),2.6,3.0),
        ('710',(7,1,0),(0,0,2),3.2,2.2)]:
        geo=ProjectedGeometry.from_crystal(fcc_nickel(),zone,target);g=geo.crystal.g_vector(target)[0]
        s=Settings(zone=zone,target=target,voltage=200,thickness=2,tilt=(geo.bragg_tilt(),0),beam_cutoff=beam,potential_cutoff=potential)
        c=ForwardSettings(axis_declared=True,propagation='both',energy_scope='edges',grid=17,depth=33,subpixels=32,
            fft_grid=32,slice_step=.02,correction=False,centers=((g/2,g/2),(g/2,-g/2)),radius=.16*g,worker_mode='manual',parallel_workers=1)
        for channel in ('single','double'):yield name+'_'+channel,s,replace(c,channeling_model=channel)
        if name=='001':
            for channel in ('single','double'):
                yield name+'_basis22_'+channel,replace(s,beam_cutoff=2.2),replace(c,channeling_model=channel)
                yield name+'_fine_slice_'+channel,replace(s,beam_cutoff=2.2),replace(c,channeling_model=channel,slice_step=.005)
            yield name+'_wide_single',replace(s,beam_cutoff=3.2),replace(c,channeling_model='single',slice_step=.005)
            yield name+'_wide_double',replace(s,beam_cutoff=2.6),replace(c,channeling_model='double',slice_step=.005,memory_budget_mib=4096)
        if name=='111':
            c=replace(c,channeling_model='double')
            for label,ss,cc in [
                ('beam_low',replace(s,beam_cutoff=1.8),c),('beam_high',replace(s,beam_cutoff=3.2),c),
                ('potential_low',replace(s,potential_cutoff=2.2),c),('potential_high',replace(s,potential_cutoff=3.8),c),
                ('fft',s,replace(c,fft_grid=48)),('depth',s,replace(c,depth=65)),
                ('slice',s,replace(c,slice_step=.01)),('angular',s,replace(c,grid=33,subpixels=64))]:
                yield name+'_'+label,ss,cc

def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--only',action='append',default=[])
    args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    files=sorted((ROOT/'src/emcd_sim').glob('*.py'))+sorted((ROOT/'src/emcd_sim/gui').glob('*.py'))
    provenance=dict(source_sha256=sha(DEFAULT_SOURCE),commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        code_sha256={str(p.relative_to(ROOT)):sha(p) for p in files},physical_model='depth-averaged projected IAM ZOLZ; XMCD-effective Hermitian Ni tensor; crystal M=[001]')
    rows=[]
    for label,s,c in cases():
        if args.only and not any(label.startswith(prefix) for prefix in args.only):continue
        identity=dict(settings=asdict(s),config=asdict(c),provenance=provenance)
        key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()[:12]
        folder=OUT/(label+'_'+key);folder.mkdir(exist_ok=True)
        meta=folder/'case.json';npz=folder/'arrays.npz'
        if meta.exists() and npz.exists():
            data=json.loads(meta.read_text(encoding='utf-8'))
            if data.get('complete') and data.get('arrays_sha256')==sha(npz):
                print('REUSE',label,flush=True);rows.extend(data['rows']);continue
        print('RUN',label,flush=True);start=time.perf_counter()
        result=calculate(Structure.nickel(),s,c)
        arrays={};case_rows=[]
        for method,r in result['methods'].items():
            arrays.update({method+'__'+k:v for k,v in r['spectra'].items()})
            arrays.update({method+'__'+edge+'__'+k:v for edge,m in r['maps'].items() for k,v in m.items()})
            arrays[method+'__amplitudes']=r['amplitudes'];arrays[method+'__coherence']=r['coherence']
            curves,_=benchmark_spectra(r['spectra'])
            for edge,energy in [('L3',c.l3),('L2',c.l2)]:
                i=int(np.argmin(abs(r['spectra']['energy_ev']-energy)))
                row=dict(case=label,method=method,edge=edge,beams=len(r['metadata']['beam_hkl']),
                    prb_pp=float(curves['prb_relative_dichroism_percent'][i]),magnetic_pp=float(curves['magnetic_only_percent'][i]))
                row.update({k:float(r['spectra'][k][i]) for k in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus','D_mag','D_nonmag','Sigma_ref')})
                case_rows.append(row)
        arrays.update(qx=result['qx'],qy=result['qy'],depth_nm=result['depth_nm'],hkl=np.array(result['metadata']['beam_hkl']),frame=np.array(result['metadata']['frame']))
        temp=folder/'arrays.partial.npz';np.savez_compressed(temp,**arrays);temp.replace(npz)
        data=dict(identity=identity,resolved_config=asdict(result['config']),complete=True,seconds=time.perf_counter()-start,arrays_sha256=sha(npz),rows=case_rows,comparison=result['comparison'])
        temp=folder/'case.partial.json';temp.write_text(json.dumps(data,indent=2,allow_nan=False),encoding='utf-8');temp.replace(meta)
        rows.extend(case_rows);print('DONE',label,round(data['seconds'],2),'s',flush=True)
    with (OUT/'comparison.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print('Completed',len(rows)//4,'cases',flush=True)

if __name__=='__main__':main()
