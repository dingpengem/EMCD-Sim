"""Focused Stage B default BW/CLI comparison; no multislice or orientation sweep."""
import argparse,json
from dataclasses import replace
from pathlib import Path
import numpy as np
from emcd_sim.gui.emcd_forward import ForwardSettings,inspect_source,DEFAULT_SOURCE,calculate,metrics,export_result
from emcd_sim.gui.geometry import Structure,Settings
from emcd_sim.study_geometry import StudyGeometry,rotated_tensor
Ni017Geometry=lambda a_angstrom=3.524: StudyGeometry((0,1,7),(2,0,0),a_angstrom)
from emcd_sim.elastic import depth_coherence
from emcd_sim.single_channeling_tensor import run_tensor_with_coherence
from emcd_sim.xmcd_postedge_normalization import analyze_postedge_spectra
from emcd_sim.geometry import Microscope,VirtualDetector


def compare_gui_export(root):
    """Match the actual Qt spinbox snapshot, including its decimal precision."""
    meta=json.loads((root/'metadata.json').read_text(encoding='utf-8'));s=meta['settings'];cfg=meta['mdff']
    if cfg['model']!='xmcd':raise ValueError('CLI XMCD comparison requires an XMCD GUI export')
    if s['zone']!=[0,1,7] or s['b_factor']!=0 or cfg['magnetization']!=[0.,0.,1.]:
        raise ValueError('This focused CLI validation supports default [017], B=0, cubic [001] M only')
    if inspect_source(cfg['source'])['sha256']!=cfg['source_sha256']:
        raise ValueError('Source changed since native GUI calculation')
    model=Ni017Geometry().model(kv=s['voltage'],beam_cutoff=s['beam_cutoff'],potential_cutoff=s['potential_cutoff'])
    model=replace(model,elastic=replace(model.elastic,microscope=Microscope(s['voltage'],tuple(s['tilt']))),
        detectors={k:VirtualDetector(tuple(p),cfg['radius']) for k,p in zip(('A','B'),cfg['centers'])})
    C=depth_coherence(model.elastic,s['thickness'],cfg['depth']);differences={}
    with np.load(root/'virtual_detector_eels.npz',allow_pickle=False) as data:
        e=data['energy_ev']
        for sign,state in ((1,'plus'),(-1,'minus')):
            r=run_tensor_with_coherence(model,rotated_tensor(cfg['source'],e,frame=Ni017Geometry().frame,eta=sign*cfg['eta'],beta=cfg['beta']),C,
                thickness_nm=s['thickness'],grid_size=cfg['grid'],map_halfwidth_q=cfg['halfwidth'],reference_energy_ev=cfg['l3'],
                integration_mode='fractional',aperture_subpixels=cfg['subpixels'])
            for d in ('A','B'):
                key='I_'+d+'_'+state;np.testing.assert_allclose(data[key],r.chiral_spectrum(d),rtol=1e-12,atol=1e-14)
                differences[key]=float(abs(data[key]-r.chiral_spectrum(d)).max())
    with np.load(root/'angular_maps.npz',allow_pickle=False) as data:coherence_error=float(abs(C-data['coherence']).max())
    report=dict(comparison='Native Qt export versus established CLI with actual saved tilt, apertures, source, energy grid and numerical sampling',
        max_abs_full_spectrum_difference=differences,coherence_max_abs=coherence_error,source_sha256=cfg['source_sha256'])
    (root/'native_cli_comparison.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=Path('outputs/gui_stage_b/default_cli_validation'))
    parser.add_argument('--gui-export',type=Path,help='Compare an actual native default [017] XMCD GUI export with CLI using its saved controls');args=parser.parse_args()
    if args.gui_export:compare_gui_export(args.gui_export);return
    info=inspect_source(DEFAULT_SOURCE);cfg=ForwardSettings(source_sha256=info['sha256'],axis_declared=True)
    result=calculate(Structure.nickel(),Settings(),cfg,lambda s:print(s,flush=True))
    # Independently use the established [017] CLI model, rotation and coherence.
    model=Ni017Geometry().model();C=depth_coherence(model.elastic,30,64);e=result['spectra']['energy_ev']
    comparisons={};opts=dict(thickness_nm=30,grid_size=33,integration_mode='fractional',aperture_subpixels=64)
    refs=[]
    for sign,state in ((1,'plus'),(-1,'minus')):
        print('Established CLI contraction: '+state,flush=True)
        r=run_tensor_with_coherence(model,rotated_tensor(DEFAULT_SOURCE,e,frame=Ni017Geometry().frame,eta=sign),C,reference_energy_ev=cfg.l3,**opts);refs.append(r)
        for d in ('A','B'):
            key='I_'+d+'_'+state;x=result['spectra'][key];y=r.chiral_spectrum(d)
            np.testing.assert_allclose(x,y,rtol=1e-11,atol=1e-14)
            comparisons[key]=float(np.max(abs(x-y)))
    post=analyze_postedge_spectra(e,refs[0].chiral_spectrum('A'),refs[0].chiral_spectrum('B'),refs[1].chiral_spectrum('A'),refs[1].chiral_spectrum('B'),windows=(cfg.window,),edge_windows={})
    np.testing.assert_allclose(result['metadata']['alpha'],post.spectra['alpha_obs'][0],rtol=1e-12)
    export_result(result,args.output)
    report=dict(source_sha256=info['sha256'],energy_points=len(e),grid=33,depth=64,beams=len(model.elastic.beams.hkl),
                max_abs_full_spectrum_difference=comparisons,coherence_max_abs=float(abs(C-result['coherence']).max()),
                alpha_cli=float(post.spectra['alpha_obs'][0]),alpha_gui=result['metadata']['alpha'],edge_metrics=metrics(result),
                comparison='Established Ni017Geometry CLI model, rotated_tensor and depth_coherence; identical source, energies, detector apertures and numerical controls.')
    (args.output/'cli_comparison.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
