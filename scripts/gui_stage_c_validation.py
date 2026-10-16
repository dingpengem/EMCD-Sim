"""Six default Stage C native Windows runs and matched standalone validation.

Uses genuine Qt workers, saves actual screenshots/exports, no mistilt sweep.
"""
import argparse,json,datetime
from pathlib import Path
from dataclasses import replace
import numpy as np
from PySide6 import QtCore,QtWidgets
from emcd_sim.gui.app import MainWindow
from emcd_sim.gui.emcd_forward import export_result,metrics
from emcd_sim.ni_017_geometry import Ni017Geometry,rotated_tensor
from emcd_sim.ni_local_mdff import ni_local_transitions
from emcd_sim.mdff_tensor import DipoleTensor,dipole_tensor_from_transitions
from emcd_sim.multislice_reference import fft_multislice_ni
from emcd_sim.multislice_emcd_reference import project_fft_amplitudes,coherence_from_amplitudes
from emcd_sim.single_channeling_tensor import run_tensor_with_coherence


def standalone_check(result):
    cfg=result['config'];settings=result['settings'];geo=Ni017Geometry();z=result['depth_nm'];e=result['spectra']['energy_ev']
    fft=fft_multislice_ni(z,acceleration_kv=settings.voltage,tilt_mrad_xy=settings.tilt,grid_points=cfg.fft_grid,slice_step_nm=cfg.slice_step,
        potential_cutoff_inv_angstrom=settings.potential_cutoff,b_factor_angstrom2=settings.b_factor,return_amplitudes=True,projected_geometry=geo)
    psi,out=project_fft_amplitudes(fft,result['model'].elastic.beams.hkl)
    np.testing.assert_array_equal(psi,result['methods']['fft-multislice']['amplitudes'])
    np.testing.assert_array_equal(out,result['fft']['excluded_intensity']);differences={}
    if cfg.model=='xmcd':ts=[rotated_tensor(cfg.source,e,eta=sign*cfg.eta,beta=cfg.beta) for sign in (1,-1)]
    else:
        ts=[]
        for sign in (1,-1):
            t=dipole_tensor_from_transitions(ni_local_transitions(cfg.atomic,magnetization_sign=sign),e,cfg.sigma)
            ts.append(DipoleTensor(e,np.einsum('ia,eab,jb->eij',geo.frame,t.tensor_angstrom2_per_ev,geo.frame),t.source))
    cli_model=geo.model(kv=settings.voltage,beam_cutoff=settings.beam_cutoff,potential_cutoff=settings.potential_cutoff)
    cli_model=replace(cli_model,elastic=replace(cli_model.elastic,microscope=result['model'].elastic.microscope),detectors=result['model'].detectors)
    for name,amplitudes in (('bloch',cli_model.elastic.amplitudes(z)),('fft-multislice',psi)):
        C=coherence_from_amplitudes(z,amplitudes);np.testing.assert_array_equal(C,result['methods'][name]['coherence'])
        for sign,t in zip(('plus','minus'),ts):
            ref=run_tensor_with_coherence(cli_model,t,C,thickness_nm=settings.thickness,grid_size=cfg.grid,map_halfwidth_q=cfg.halfwidth,
                reference_energy_ev=cfg.l3,integration_mode='fractional',aperture_subpixels=cfg.subpixels)
            for d in ('A','B'):
                key='I_'+d+'_'+sign;expected=ref.chiral_spectrum(d);actual=result['methods'][name]['spectra'][key]
                np.testing.assert_allclose(actual,expected,rtol=1e-12,atol=1e-15);differences[name+'__'+key]=float(abs(actual-expected).max())
    return differences


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=Path('outputs/gui_stage_c')/datetime.datetime.now().strftime('windows_%Y%m%d_%H%M%S'))
    parser.add_argument('--screenshot',type=Path,default=Path('docs/images/gui/stage_c_windows.png'));args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([]);w=MainWindow();w.show();cases=[(model,method) for model in range(2) for method in range(3)];results={};failures=[]
    def failed(message):failures.append(message);print('FAIL: '+message,flush=True)
    w.error=failed
    def start():
        if not cases:w.close();app.quit();return
        model,method=cases.pop(0);w.model_box.setCurrentIndex(model);w.propagation_box.setCurrentIndex(method)
        print('Native GUI: '+('XMCD' if model==0 else 'atomic')+' / '+w.propagation_box.currentText(),flush=True)
        w.start_emcd()
        if not w.busy:failed('Run was not started');app.exit(2);return
        w.worker.finished.connect(lambda:QtCore.QTimer.singleShot(150,complete))
    def complete():
        if w.busy:QtCore.QTimer.singleShot(100,complete);return
        if failures or w.run_outcome!='completed':app.exit(2);return
        r=w.emcd_result;key=r['config'].model+'_'+r['config'].propagation;results[key]=r
        if r['config'].propagation=='both':
            w.tabs.setCurrentIndex(6);w.overview_view.maximize()
            QtCore.QTimer.singleShot(700,lambda:capture_and_next(key))
        else:QtCore.QTimer.singleShot(100,start)
    def capture_and_next(key):
        target=args.screenshot if key.startswith('xmcd') else args.output/'atomic_windows.png'
        target.parent.mkdir(parents=True,exist_ok=True);w.grab().save(str(target));w.overview_view.maximize();QtCore.QTimer.singleShot(100,start)
    QtCore.QTimer.singleShot(300,start)
    code=app.exec()
    if code or failures:raise RuntimeError('Native GUI acceptance failed: '+repr(failures))
    report={}
    for key,r in results.items():
        print('Exporting '+key,flush=True);export_result(r,args.output/key)
        report[key]=dict(metrics={name:metrics(m) for name,m in r['methods'].items()},comparison=r['comparison'])
        if r['config'].propagation=='both':
            report[key]['standalone_max_abs']=standalone_check(r)
            for name,mode in (('bloch','bloch'),('fft-multislice','fft-multislice')):
                other=results[r['config'].model+'_'+mode]
                for k,v in r['methods'][name]['spectra'].items():np.testing.assert_array_equal(v,other['spectra'][k])
            report[key]['single_vs_both']='bitwise-identical all spectra per method'
    (args.output/'validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print('Six native Windows calculations and independent standalone checks PASS: '+str(args.output),flush=True)


if __name__=='__main__':main()
