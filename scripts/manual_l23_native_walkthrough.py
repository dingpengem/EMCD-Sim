"""Visible source-GUI spectral manual model, BW/MS and portable restoration."""
import json
import os
from pathlib import Path
import sys
import time
import traceback
from unittest.mock import patch
from PySide6 import QtCore, QtTest, QtWidgets
from emcd_sim.gui.app import MainWindow
from emcd_sim.gui.project_io import save_project

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/native-manual-l23';OUT.mkdir(parents=True,exist_ok=True)
app=QtWidgets.QApplication([]);assert app.platformName()=='windows'
w=MainWindow(OUT/'workspace');w.errors=[];w.error=w.errors.append
w.show();w.mdff_dialog.show();w.mdff_dialog.raise_();w.mdff_dialog.activateWindow()


def capture(name):
    w.mdff_dialog.repaint()
    QtTest.QTest.qWait(500)
    assert w.mdff_dialog.windowHandle().isExposed()
    image=w.mdff_dialog.screen().grabWindow(int(w.mdff_dialog.winId()))
    assert not image.isNull() and image.save(str(OUT/(name+'.png')))


def wait_worker():
    deadline=time.monotonic()+120
    while w.busy and time.monotonic()<deadline:app.processEvents();time.sleep(.01)
    assert not w.busy and not w.errors,w.errors
    assert w.run_outcome=='completed',w.run_outcome


def walkthrough():
    try:
        with patch.object(QtWidgets.QFileDialog,'getOpenFileName',return_value=(str(ROOT/'tests/fixtures/alpha_Fe_bcc_Im-3m.cif'),'')):
            w.load_cif()
        w.zone.setText('0 0 1');w.target.setText('1 1 0')
        w.model_box.setCurrentIndex(2);w.manual_model.setCurrentIndex(1);e=w.manual_spectral;e.element.setCurrentText('Fe')
        e.fields['L2','width'].setText('1.8');e.fields['L2','p'].setText('-.18');e.direction.setText('1 0 1')
        w.preview_mdff();assert e.snapshot and not e.is_stale
        w.mdff_scroll.verticalScrollBar().setValue(0);capture('spectral-basic')
        e.state.setCurrentIndex(4);capture('spectral-reversal')
        e.view.setCurrentIndex(1);QtTest.QTest.qWait(300);w.mdff_scroll.ensureWidgetVisible(e.matrices['L3']);capture('spectral-expanded-matrices')
        e.matrices['L3'].cells.item(0,2).setText('0.04+0.02i');e.matrices['L3'].cells.item(2,0).setText('0.04-0.02j')
        e.view.setCurrentIndex(0);assert e.view.currentIndex()==1 and 'no projection' in e.error.text();capture('spectral-general-matrix-retained')
        w.preview_mdff();e.heat_energy.setValue(714.3);e.state.setCurrentIndex(3)
        w.mdff_scroll.ensureWidgetVisible(e.heat_canvas);capture('spectral-heatmaps')
        w.numerical_mode.setCurrentIndex(1);w.worker_mode.setCurrentIndex(1);w.worker_count.setValue(1)
        w.set_values(dict(beam=.6,potential=1.2,kv=200,thickness=.2,grid=9,depth=3,subpixels=4,energy=9,halfwidth=.7,radius=.12,fft_grid=16,slice_step=.01))
        w.propagation_box.setCurrentIndex(2);w.energy_scope.setCurrentIndex(1)
        outcomes=[]
        for channel in (0,1):
            w.channeling_box.setCurrentIndex(channel);w.start_emcd();wait_worker()
            outcomes.append(dict(channel=w.emcd_result['config'].channeling_model,methods=list(w.emcd_result['methods'])))
        original=OUT/('project-'+str(os.getpid()));save_project(w.emcd_result,original)
        relocated=OUT/('relocated-project-'+str(os.getpid()));original.rename(relocated)
        Path(w.emcd_result['config'].source).unlink()
        w.model_box.setCurrentIndex(1);w.open_project_path(relocated);wait_worker();w.use_result_settings()
        assert w.manual_model.currentIndex()==1 and e.view.currentIndex()==1
        w.preview_mdff();assert not e.is_stale
        e.advanced.setChecked(False);w.mdff_scroll.verticalScrollBar().setValue(0)
        debug=[]
        for widget in (w.mdff_material,*[b for b in w.mdff_dialog.findChildren(QtWidgets.QPushButton) if b.text().startswith('Open CIF')]):
            rect=widget.geometry()
            debug.append(dict(text=widget.text(),visible=widget.isVisible(),hidden=widget.isHidden(),geometry=[rect.x(),rect.y(),rect.width(),rect.height()]))
        (OUT/'header-debug.json').write_text(json.dumps(debug,indent=2),encoding='utf-8')
        w.mdff_dialog.hide();app.processEvents();w.mdff_dialog.show()
        w.mdff_dialog.raise_();w.mdff_dialog.activateWindow();capture('spectral-restored-final')
        report=dict(platform=app.platformName(),python=sys.executable,source_worktree=str(ROOT),pid=os.getpid(),
            device_pixel_ratio=w.screen().devicePixelRatio(),logical_dpi=w.screen().logicalDotsPerInch(),
            native_exposed=w.mdff_dialog.windowHandle().isExposed(),native_calculations=outcomes,
            general_matrix_retained=True,portable_project_restored_without_original_source=True,project=str(relocated),
            gui_left_open=True,screenshots=['spectral-basic.png','spectral-reversal.png','spectral-expanded-matrices.png','spectral-general-matrix-retained.png','spectral-heatmaps.png','spectral-restored-final.png'])
        (OUT/'walkthrough.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    except Exception:(OUT/'failure.txt').write_text(traceback.format_exc(),encoding='utf-8')


QtCore.QTimer.singleShot(1000,walkthrough)
sys.exit(app.exec())
