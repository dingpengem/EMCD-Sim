"""Bounded synthetic BCC Fe acceptance; never a quantitative Fe prediction."""
from dataclasses import replace,asdict
from pathlib import Path
import argparse,hashlib,json,sys
import numpy as np
from ase.build import bulk
from ase.io import write
from emcd_sim.gui.geometry import Structure,Settings
from emcd_sim.gui.generalized_forward import calculate,settings_for_source
from emcd_sim.gui.emcd_forward import export_result
from emcd_sim.gui.runtime import build_info


def run(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    # Use the same original synthetic software fixture as the regression tests.
    # No downloaded/experimental Fe table is represented by this validation.
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tests'))
    from single_element_helpers import document
    doc=document();source=output/'SYNTHETIC_Fe_L23.json';source.write_text(json.dumps(doc,indent=2),encoding='utf-8')
    cif=output/'bcc_fe.cif';write(cif,bulk('Fe','bcc',a=2.866,cubic=True),format='cif')
    structure=Structure.from_cif(cif)
    settings=Settings(zone=(0,0,1),target=(1,1,0),tilt=(-5,7),voltage=200,thickness=.4,beam_cutoff=.6,potential_cutoff=1.2)
    cfg=settings_for_source(source,energy_points=9,grid=17,depth=17,subpixels=16,fft_grid=24,slice_step=.005,
        halfwidth=.7,centers=((.2,.2),(.2,-.2)),radius=.12,propagation='both',worker_mode='manual',parallel_workers=1)
    report=dict(status='SYNTHETIC TEST ONLY',build=build_info(),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        settings=asdict(settings),source='Original software fixture, not a physical Fe MDFF',channels={},bounded_checks=[])
    baselines={}
    for channel in ('single','double'):
        config=replace(cfg,channeling_model=channel)
        result=calculate(structure,settings,config,energy_ev=np.asarray(doc['energy_ev']))
        export_result(result,output/channel)
        report['channels'][channel]=dict(energy_ev=result['spectra']['energy_ev'].tolist(),comparison=result['comparison'],
            raw={k:result['spectra'][k].tolist() for k in ('I_A_plus','I_A_minus','I_B_plus','I_B_minus','D_raw','D_mag','D_nonmag')},
            flip_M_A=(result['spectra']['I_A_plus']-result['spectra']['I_A_minus']).tolist())
        for name,method in result['methods'].items():
            sp=method['spectra']
            assert all(np.isfinite(sp[k]).all() and np.min(sp[k])>=0 for k in ('I_A_plus','I_A_minus','I_B_plus','I_B_minus'))
            np.testing.assert_allclose(sp['D_raw'],sp['D_mag']+sp['D_nonmag'],rtol=1e-12,atol=1e-14)
        baselines[channel]=calculate(structure,settings,replace(config,energy_scope='edges',angular_maps=False))
    variations=[('beam_cutoff',replace(settings,beam_cutoff=.85),cfg),
        ('potential_cutoff',replace(settings,potential_cutoff=1.5),cfg),
        ('thickness_thin',replace(settings,thickness=.2),cfg),('thickness_thicker',replace(settings,thickness=.8),cfg),
        ('depth_coarser',settings,replace(cfg,depth=9)),('depth_finer',settings,replace(cfg,depth=33)),
        ('detector_coarser',settings,replace(cfg,grid=9,subpixels=8)),('detector_finer',settings,replace(cfg,grid=25,subpixels=32)),
        ('fft_coarser',settings,replace(cfg,fft_grid=16)),('fft_finer',settings,replace(cfg,fft_grid=32)),
        ('slice_coarser',settings,replace(cfg,slice_step=.02)),('slice_finer',settings,replace(cfg,slice_step=.0025))]
    for channel in ('single','double'):
        baseline=baselines[channel]
        for label,s,c in variations:
            r=calculate(structure,s,replace(c,channeling_model=channel,energy_scope='edges',angular_maps=False))
            checks={}
            for method in r['methods']:
                p=r['methods'][method]['spectra'];b=baseline['methods'][method]['spectra']
                checks[method]={k:float(np.linalg.norm(p[k]-b[k])/max(np.linalg.norm(b[k]),1e-30)) for k in ('I_A_plus','I_B_plus','D_mag','D_nonmag')}
            report['bounded_checks'].append(dict(channel=channel,variation=label,settings=asdict(s),depth=c.depth,grid=c.grid,
                fft_grid=c.fft_grid,slice_step=c.slice_step,relative_to_baseline=checks,bw_ms=r['comparison']))
            print(channel,label,'done',flush=True)
    report['limits']='Only selected thin BCC Fe synthetic cases; detector/basis/thickness sensitivities are reported, not certified converged. No experimental/DFT comparison or absolute cross-section validation.'
    (output/'validation.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    files={p.relative_to(output).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in output.rglob('*') if p.is_file()}
    (output/'SHA256_manifest.json').write_text(json.dumps(files,indent=2),encoding='utf-8')
    print(json.dumps(dict(output=str(output),source=report['build']['commit'],bounded_checks=len(report['bounded_checks']),
        channels={k:v['comparison']['spectra']['I_A_plus'] for k,v in report['channels'].items()}),indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args().output)
