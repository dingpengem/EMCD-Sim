"""Fresh manageable GUI-worker spectra and read-only production presentation."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import json,time
from pathlib import Path
from uuid import uuid4
from dataclasses import replace
from unittest.mock import patch
import numpy as np
from PySide6 import QtCore,QtGui,QtWidgets
from matplotlib import get_data_path
from emcd_sim.gui.stage_b import EMCDWorker
from emcd_sim.gui.geometry import Structure,Settings
from emcd_sim.gui.emcd_forward import ForwardSettings,export_result
from emcd_sim.gui.project_io import save_project,load_project
from emcd_sim.gui.app import MainWindow

ROOT=Path('outputs/ni_double_channeling_full_spectra/gui_validation')


def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    font=QtGui.QFontDatabase.addApplicationFont(str(Path(get_data_path())/'fonts/ttf/DejaVuSans.ttf'))
    app.setFont(QtGui.QFont(QtGui.QFontDatabase.applicationFontFamilies(font)[0],9))
    records=[]
    for channel in ('single','double'):
        target=ROOT/f'fresh_{channel}'
        if target.exists():result=load_project(target)
        else:
            cfg=ForwardSettings(axis_declared=True,channeling_model=channel,propagation='both',energy_scope='full',
                energy_points=17,angular_maps=False,grid=9,depth=9,fft_grid=24,subpixels=16,correction=False)
            worker=EMCDWorker(Structure.nickel(),Settings(thickness=8,beam_cutoff=.9,potential_cutoff=1.8),cfg)
            received=[];errors=[];loop=QtCore.QEventLoop();start=time.perf_counter()
            worker.result.connect(received.append);worker.failed.connect(errors.append);worker.finished.connect(loop.quit)
            worker.start();loop.exec();worker.wait()
            if errors or not received:raise RuntimeError(str(errors) or 'GUI worker produced no result')
            result=received[0];save_project(result,target)
            (ROOT/f'{channel}_runtime.json').write_text(json.dumps(dict(elapsed_seconds=time.perf_counter()-start)))
        assert set(result['methods'])=={'bloch','fft-multislice'}
        assert len(result['spectra']['energy_ev'])>=17
        for method,r in result['methods'].items():
            s=r['spectra'];np.testing.assert_allclose(s['D_raw'],s['D_mag']+s['D_nonmag'],atol=1e-14)
            records.append(dict(channeling_model=channel,solver=method,energy_samples=len(s['energy_ev']),raw_min=float(min(s[k].min() for k in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus')))))
    production=load_project(ROOT.parent/'001_008_double_bloch/prepared_v1/full')
    bwms=load_project(ROOT.parent/'001_008_double_fft-multislice/prepared_v1/full')
    production=dict(production,methods={'bloch':production,'fft-multislice':bwms})
    original={method:{k:v.copy() for k,v in r['spectra'].items()} for method,r in production['methods'].items()}
    window=MainWindow(workspace=ROOT/('workspace_'+uuid4().hex))
    try:
        with patch('emcd_sim.gui.emcd_forward.calculate',side_effect=AssertionError('Saved display must not calculate')):
            window.display_saved_result(production);window.resize(1500,1050);window.show();window.tabs.setCurrentWidget(window.eels_view)
            for dock in window.findChildren(QtWidgets.QDockWidget):dock.hide()
            view=window.eels_view;view.maximize();app.processEvents()
            for mode in ('raw','relative'):
                view.component_mode.setCurrentIndex(view.component_mode.findData(mode))
                for zoom in ('Full spectrum','L3 zoom','L2 zoom'):
                    view.choice.setCurrentText(zoom);app.processEvents()
                    assert len(view.figure.axes)==2 and view.figure._emcd_display_metadata['component_mode']==mode
                    view.figure.savefig(ROOT/f'production_{mode}_{zoom.replace(" ","_")}.png',dpi=140)
                view.choice.setCurrentText('Full spectrum');app.processEvents();window.grab().save(str(ROOT/f'desktop_{mode}.png'))
                if not (ROOT/('export_'+mode)).exists():export_result(production,ROOT/('export_'+mode),component_mode=mode)
            for method,r in production['methods'].items():
                for key,v in original[method].items():np.testing.assert_array_equal(v,r['spectra'][key])
            for filename in ('virtual_detector_eels.npz','angular_maps.npz','diffraction_pattern.npz'):
                with np.load(ROOT/'export_raw'/filename,allow_pickle=False) as a,np.load(ROOT/'export_relative'/filename,allow_pickle=False) as b:
                    assert a.files==b.files
                    for key in a.files:np.testing.assert_array_equal(a[key],b[key])
    finally:window.close();app.processEvents()
    status=dict(passed=True,fresh_actual_gui_worker=records,production_saved_display_energy_samples=242,
        raw_relative_exports_identical=True,display_does_not_recalculate=True,
        limitation='Fresh GUI-worker profile is deliberately small; production numerical validation is reported separately.')
    (ROOT/'checkpoint_2.json').write_text(json.dumps(status,indent=2));print(json.dumps(status),flush=True)


if __name__=='__main__':main()
