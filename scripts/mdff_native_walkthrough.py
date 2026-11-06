"""Visible Windows source walkthrough; leaves the real application running."""
import json
import os
from pathlib import Path
import sys
import traceback
import time
from unittest.mock import patch
from PySide6 import QtCore, QtWidgets, QtTest
from emcd_sim.gui.app import MainWindow

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/native-usability';OUT.mkdir(parents=True,exist_ok=True)
app=QtWidgets.QApplication([])
assert app.platformName()=='windows', 'Native Windows platform required'
w=MainWindow(OUT/'workspace')
w.show()
w.model_box.setCurrentIndex(1)
w.mdff_dialog.show();w.mdff_dialog.raise_();w.mdff_dialog.activateWindow()


def capture(name):
    QtTest.QTest.qWait(600)
    assert w.mdff_dialog.windowHandle().isExposed()
    pixmap=w.mdff_dialog.screen().grabWindow(int(w.mdff_dialog.winId()))
    assert not pixmap.isNull()
    assert pixmap.save(str(OUT/(name+'.png')))


def walkthrough():
    try:
        with patch.object(QtWidgets.QFileDialog,'getOpenFileName',return_value=(str(ROOT/'tests/fixtures/alpha_Fe_bcc_Im-3m.cif'),'')):
            w.load_cif()
        w.zone.setText('0 0 1');w.target.setText('1 1 0');w.sync_atomic_editor_structure()
        e=w.atomic_editor;e.preview()
        if hasattr(e,'preview_dialog'):e.preview_dialog.hide()
        w.mdff_dialog.raise_();w.mdff_dialog.activateWindow();w.mdff_scroll.verticalScrollBar().setValue(0)
        capture('atomic-basic')
        QtTest.QTest.mouseClick(e.advanced_parameters.header,QtCore.Qt.MouseButton.LeftButton)
        e.sections['D'].setChecked(True);e.sections['C'].setChecked(False)
        w.mdff_scroll.ensureWidgetVisible(e.hole_canvas)
        capture('atomic-advanced')
        e.holes.cellWidget(0,0).setFocus();QtTest.QTest.qWait(100)
        w.mdff_scroll.ensureWidgetVisible(e.hole_canvas)
        capture('atomic-occupations')
        e.advanced_parameters.setChecked(False)
        w.model_box.setCurrentIndex(2);w.ionizing_element.setText('Fe')
        w.manual_model.setCurrentIndex(0)
        w.manual_tensor.cells.item(0,1).setText('0.02-0.01i')
        w.manual_tensor.cells.item(1,0).setText('0.02+0.01j')
        w.preview_mdff()
        for dialog in w.dialogs:dialog.hide()
        w.mdff_dialog.raise_();w.mdff_scroll.verticalScrollBar().setValue(0)
        capture('manual-tensor')
        w.mdff_scroll.ensureWidgetVisible(w.manual_tensor.focus)
        capture('manual-heatmaps')
        w.mdff_scroll.verticalScrollBar().setValue(0)
        w.manual_tensor.cells.item(0,0).setText('-1')
        capture('manual-inline-error')
        w.manual_tensor.cells.item(0,0).setText('0.3333333333333333')
        w.errors=[];w.error=w.errors.append
        w.numerical_mode.setCurrentIndex(1)
        w.worker_mode.setCurrentIndex(1);w.worker_count.setValue(1)
        w.set_values(dict(beam=.6,potential=1.2,kv=200,thickness=.2,grid=9,depth=3,subpixels=4,energy=9,halfwidth=.7,radius=.12))
        w.propagation_box.setCurrentIndex(0);w.energy_scope.setCurrentIndex(1)
        calculated=[]
        for index in (2,1):
            w.model_box.setCurrentIndex(index);w.start_emcd()
            deadline=time.monotonic()+90
            while w.busy and time.monotonic()<deadline:app.processEvents();time.sleep(.01)
            assert not w.busy and not w.errors, w.errors
            assert w.run_outcome=='completed', w.run_outcome
            calculated.append(w.emcd_result['config'].model)
        w.model_box.setCurrentIndex(1);w.mdff_scroll.verticalScrollBar().setValue(0)
        e.preview();e.preview_dialog.hide()
        capture('final-atomic')
        report=dict(platform=app.platformName(),python=sys.executable,source=str(ROOT),pid=os.getpid(),
            screen_geometry=[w.screen().geometry().width(),w.screen().geometry().height()],
            device_pixel_ratio=w.screen().devicePixelRatio(),logical_dpi=w.screen().logicalDotsPerInch(),
            dialog_size=[w.mdff_dialog.width(),w.mdff_dialog.height()],
            native_exposed=w.mdff_dialog.windowHandle().isExposed(),
            screenshots=['atomic-basic.png','atomic-advanced.png','atomic-occupations.png','manual-tensor.png','manual-heatmaps.png','manual-inline-error.png','final-atomic.png'],
            atomic_default_valid=bool(e.document()),inline_error_exercised=True,native_calculations=calculated,gui_left_open=True)
        (OUT/'walkthrough.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    except Exception:
        (OUT/'failure.txt').write_text(traceback.format_exc(),encoding='utf-8')


QtCore.QTimer.singleShot(1200,walkthrough)
sys.exit(app.exec())
