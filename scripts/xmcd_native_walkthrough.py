"""Visible source-GUI XMCD preview, switching and project-restoration walkthrough."""
import json
import os
from pathlib import Path
import sys
import time
import traceback
from unittest.mock import patch
from PySide6 import QtCore, QtTest, QtWidgets
from emcd_sim.gui.app import MainWindow
from emcd_sim.gui.emcd_forward import DEFAULT_SOURCE
from emcd_sim.gui.project_io import save_project

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/native-xmcd-preview';OUT.mkdir(parents=True,exist_ok=True)
app=QtWidgets.QApplication([]);assert app.platformName()=='windows'
w=MainWindow(OUT/'workspace');w.errors=[];w.error=w.errors.append
w.show();w.mdff_dialog.show();w.mdff_dialog.raise_();w.mdff_dialog.activateWindow()


def capture(name):
    QtTest.QTest.qWait(500)
    assert w.mdff_dialog.windowHandle().isExposed()
    image=w.mdff_dialog.screen().grabWindow(int(w.mdff_dialog.winId()))
    assert not image.isNull() and image.save(str(OUT/(name+'.png')))


def wait_worker():
    deadline=time.monotonic()+90
    while w.busy and time.monotonic()<deadline:app.processEvents();time.sleep(.01)
    assert not w.busy and not w.errors,w.errors
    assert w.run_outcome=='completed',w.run_outcome


def walkthrough():
    try:
        w.model_box.setCurrentIndex(0)
        # Source is explicitly selected for the Ni material already displayed.
        # Only the native text-file chooser result is supplied by the harness.
        with patch.object(QtWidgets.QFileDialog,'getOpenFileName',return_value=(str(DEFAULT_SOURCE),'')):
            w.browse_xmcd()
        w.declaration.setChecked(True);w.preview_mdff();p=w.xmcd_preview
        assert p.snapshot is not None and not p.is_stale,p.status.text()
        p.state.setCurrentIndex(4);p.part.setCurrentText('Imaginary')
        w.mdff_scroll.verticalScrollBar().setValue(0);capture('xmcd-source-and-tensor')
        p.state.setCurrentIndex(5);capture('xmcd-even-odd')
        eta=w.spin['eta'].value();w.spin['eta'].setValue(eta*.8)
        assert p.is_stale;capture('xmcd-stale')
        w.spin['eta'].setValue(eta);w.preview_mdff()
        selections=(p.state.currentIndex(),p.component.currentIndex(),p.part.currentIndex())
        for mode in (1,2,0):w.model_box.setCurrentIndex(mode);app.processEvents()
        assert selections==(p.state.currentIndex(),p.component.currentIndex(),p.part.currentIndex())
        assert not p.is_stale
        original=w.source_path.text();w.source_path.clear();w.preview_mdff()
        assert p.isVisible() and p.is_stale and 'main XMCD input' in p.status.text();capture('xmcd-missing-source')
        w.source_path.setText(original);w.validate_xmcd(show_error=False);w.declaration.setChecked(True);w.preview_mdff()
        w.zone.setText('0 0 1');w.target.setText('2 0 0');w.numerical_mode.setCurrentIndex(1)
        w.worker_mode.setCurrentIndex(1);w.worker_count.setValue(1)
        w.set_values(dict(beam=.7,potential=1.4,kv=200,thickness=.2,grid=9,depth=3,subpixels=4,energy=9,halfwidth=.7,radius=.12))
        w.propagation_box.setCurrentIndex(0);w.energy_scope.setCurrentIndex(1)
        w.start_emcd();wait_worker()
        project=OUT/('project-'+str(os.getpid()));save_project(w.emcd_result,project)
        w.model_box.setCurrentIndex(1);w.open_project_path(project);wait_worker();w.use_result_settings()
        assert w.model_box.currentIndex()==0 and w.mdff_stack.currentIndex()==0
        w.preview_mdff();assert not p.is_stale,p.status.text()
        p.state.setCurrentIndex(4);p.part.setCurrentText('Imaginary');w.mdff_scroll.verticalScrollBar().setValue(0)
        w.mdff_dialog.raise_();w.mdff_dialog.activateWindow();capture('xmcd-restored-final')
        report=dict(platform=app.platformName(),python=sys.executable,worktree=str(ROOT),pid=os.getpid(),
            source=str(DEFAULT_SOURCE),element='Ni',source_sha256=p.snapshot['config'].source_sha256,
            source_selection='five-column text file; no MDFF JSON selected',
            source_and_real_provider_tensor=True,even_odd_and_reversal=True,stale_and_missing_source=True,
            all_three_modes_switched=True,native_calculation='completed',project=str(project),project_reopened=True,
            device_pixel_ratio=w.screen().devicePixelRatio(),logical_dpi=w.screen().logicalDotsPerInch(),
            native_exposed=w.mdff_dialog.windowHandle().isExposed(),gui_left_open=True,
            screenshots=['xmcd-source-and-tensor.png','xmcd-even-odd.png','xmcd-stale.png','xmcd-missing-source.png','xmcd-restored-final.png'])
        (OUT/'walkthrough.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    except Exception:(OUT/'failure.txt').write_text(traceback.format_exc(),encoding='utf-8')


QtCore.QTimer.singleShot(1000,walkthrough)
sys.exit(app.exec())
