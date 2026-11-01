"""Bounded old/corrected Ni [017] controls; separate resumable output only.

Runs each source tree in its own process. No historical output is written.
Source kernels, settings and common spectrum identities are checkpoint keys.
"""
import argparse
from pathlib import Path
import os
import sys
import json
import hashlib
from dataclasses import replace, asdict
from time import perf_counter

os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source-root',type=Path,required=True)
    parser.add_argument('--historical-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--label',choices=['original','corrected'],required=True)
    args=parser.parse_args()
    root=args.source_root.resolve();old=args.historical_root.resolve();out=args.output.resolve()/args.label
    out.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(root/'src'))
    import numpy as np
    import emcd_sim.double_channeling as kernel
    from emcd_sim.gui.geometry import Structure,geometry,align_bragg
    from emcd_sim.gui.project_io import settings_from_dict,config_from_dict
    from emcd_sim.gui.emcd_forward import calculate
    from emcd_sim.gui.propagation import numerical_info
    assert Path(kernel.__file__).resolve().is_relative_to(root)
    def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
    def savejson(p,value):
        temporary=p.with_suffix('.pending.json');temporary.write_text(json.dumps(value,indent=2),encoding='utf-8');temporary.replace(p)
    metadata=json.loads((old/'build/emcd-017-y-mistilt-reversal-comparison/cases/double_final_y0_p62/metadata.json').read_text())
    base_settings=settings_from_dict(metadata['settings']);base_cfg=config_from_dict(metadata['config'])
    base_cfg=replace(base_cfg,energy_scope='edges',energy_points=241,angular_maps=False,
                     propagation='both',worker_mode='manual',parallel_workers=1)
    structure=Structure.nickel();energy=np.array([831.271,848.698])
    _,frame,hkl,g,_=geometry(structure,base_settings)
    bragg=align_bragg(g[hkl.index((2,0,0))],(0.,0.),300,lock='Y')
    assert len(hkl)==71
    assert np.allclose(bragg,[-5.586688140406263,0.],rtol=0,atol=1e-12)
    source_hashes={name:sha(root/'src/emcd_sim'/name) for name in
        ['single_channeling_tensor.py','double_channeling.py','multislice_double_channeling.py']}
    records=[]
    for thickness in [10.,30.]:
        for y in [0.,15.]:
            for channel in ['single','double']:
                name=f't{thickness:g}_y{y:g}_{channel}';folder=out/name;folder.mkdir(parents=True,exist_ok=True)
                settings=replace(base_settings,thickness=thickness,tilt=(float(bragg[0]),y))
                cfg=replace(base_cfg,channeling_model=channel)
                identity=dict(settings=asdict(settings),config=asdict(cfg),energy_ev=energy.tolist(),
                    source_sha256=sha(Path(cfg.source)),kernel_sha256=source_hashes,
                    convention=args.label,study_script_sha256=sha(Path(__file__)))
                fingerprint=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
                if (folder/'complete.json').exists():
                    saved=json.loads((folder/'complete.json').read_text());assert saved['fingerprint']==fingerprint
                    records.append(saved);print('REUSE',args.label,name,flush=True);continue
                savejson(folder/'configuration.json',dict(identity,fingerprint=fingerprint,frame=frame.tolist(),hkl=hkl))
                info=numerical_info(structure,settings,cfg)
                assert info['execution']['effective_workers']=={'bloch':1,'fft-multislice':1}
                def checkpoint(method,e,data):
                    p=folder/f'{method}_{e:.6f}.npz'
                    if data is None:
                        if not p.exists():return None
                        with np.load(p,allow_pickle=False) as f:
                            assert str(f['fingerprint'])==fingerprint
                            return {'raw':f['raw'].copy()}
                    tmp=p.with_suffix('.pending.npz');np.savez_compressed(tmp,raw=data['raw'],fingerprint=fingerprint);tmp.replace(p)
                    print('SAVED',args.label,name,method,e,flush=True)
                start=perf_counter()
                result=calculate(structure,settings,cfg,energy_ev=energy,energy_checkpoint=checkpoint)
                arrays={};method_metadata={}
                for method,value in result['methods'].items():
                    arrays.update({method+'__'+k:v for k,v in value['spectra'].items() if isinstance(v,np.ndarray)})
                    method_metadata[method]=value['metadata']
                tmp=folder/'results.pending.npz';np.savez_compressed(tmp,**arrays);tmp.replace(folder/'results.npz')
                savejson(folder/'method_metadata.json',method_metadata)
                record=dict(name=name,thickness_nm=thickness,y_mrad=y,channel=channel,
                    fingerprint=fingerprint,elapsed_seconds=perf_counter()-start,
                    results_sha256=sha(folder/'results.npz'),source_root=str(root),kernel_sha256=source_hashes)
                savejson(folder/'complete.json',record);records.append(record)
                print('DONE',args.label,name,round(record['elapsed_seconds'],3),'seconds',flush=True)
    savejson(out/'complete.json',dict(cases=records,methods=['bloch','fft-multislice'],completed_method_cases=16,
                                    physics_label=args.label))


if __name__=='__main__':main()
