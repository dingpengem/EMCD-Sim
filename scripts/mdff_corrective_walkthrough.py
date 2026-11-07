"""Bounded corrective checks in a visible Windows Qt session; leave it open."""
import argparse
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import traceback
from unittest.mock import patch
import numpy as np
from PySide6 import QtCore, QtTest, QtWidgets
from emcd_sim.gui.app import MainWindow
from emcd_sim.gui.geometry import Structure, Settings
from emcd_sim.gui.forward_pipeline import calculate
from emcd_sim.gui.project_io import save_project, config_from_dict
from emcd_sim.gui.generalized_forward import source_for
from emcd_sim.mdff_providers import prepare_provider
from test_mdff_corrective import imported_document

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
OUT=parser.parse_args().output;OUT.mkdir(parents=True,exist_ok=True)
app=QtWidgets.QApplication([]);assert app.platformName()=='windows'
w=MainWindow(OUT/'workspace');w.errors=[];w.error=w.errors.append
w.show();w.mdff_dialog.show();w.mdff_dialog.raise_();w.mdff_dialog.activateWindow()
checks=[]


def capture(name):
    w.mdff_dialog.hide();app.processEvents();w.mdff_dialog.show()
    w.mdff_dialog.raise_();w.mdff_dialog.activateWindow();w.mdff_dialog.repaint();QtTest.QTest.qWait(500)
    assert w.mdff_dialog.windowHandle().isExposed()
    image=w.mdff_dialog.screen().grabWindow(int(w.mdff_dialog.winId()))
    assert not image.isNull() and image.save(str(OUT/(name+'.png')))


def wait_worker():
    deadline=time.monotonic()+120
    while w.busy and time.monotonic()<deadline:app.processEvents();time.sleep(.01)
    assert not w.busy and not w.errors,w.errors
    assert w.run_outcome=='completed',w.run_outcome


def submit(expected):
    w.numerical_mode.setCurrentIndex(1);w.worker_mode.setCurrentIndex(1);w.worker_count.setValue(1)
    w.set_values(dict(beam=.6,potential=1.2,kv=200,thickness=.2,grid=9,depth=3,subpixels=4,energy=9,halfwidth=.7,radius=.12,fft_grid=16,slice_step=.01))
    w.propagation_box.setCurrentIndex(0);w.energy_scope.setCurrentIndex(1)
    w.start_emcd();wait_worker();actual=w.emcd_result['config']
    if hasattr(expected,'source_sha256'):
        assert actual.source_sha256==expected.source_sha256 and actual.magnetization==expected.magnetization
    else:assert actual.atomic==expected.atomic and actual.l3==expected.l3 and actual.l2==expected.l2
    return actual


def walkthrough():
    try:
        with patch.object(QtWidgets.QFileDialog,'getOpenFileName',return_value=(str(ROOT/'tests/fixtures/alpha_Fe_bcc_Im-3m.cif'),'')):w.load_cif()
        w.zone.setText('0 0 1');w.target.setText('1 1 0');w.model_box.setCurrentIndex(1)
        e=w.atomic_editor;path=OUT/'same-path-atomic.json';path.write_text(json.dumps(e.document()),encoding='utf-8')
        w.atomic_parameter_path.setText(str(path));w.validate_atomic_parameters();e.preview();old=e.preview_dialog
        old.close();e.advanced_parameters.setChecked(True);capture('atomic-original')
        d=json.loads(path.read_bytes());d['parameters'].update(crystal_field_ev=1.75,edge_energies_ev=[709.2,722.3])
        path.write_text(json.dumps(d),encoding='utf-8');w.validate_atomic_parameters()
        assert old.is_stale and 'STALE' in e.preview_state.text()
        assert float(e.fields['cf'].text())==1.75 and float(e.fields['l3'].text())==709.2
        capture('atomic-revalidated-stale');e.preview();e.preview_dialog.close()
        cfg=w.forward_settings();assert cfg.source_sha256==hashlib.sha256(path.read_bytes()).hexdigest()
        submit(cfg);capture('atomic-current-submitted')
        checks.append(dict(case='same-path Atomic revalidation',splitting=1.75,energies=[709.2,722.3],sha256=cfg.source_sha256,old_preview_stale=True,submitted=True))
        w.model_box.setCurrentIndex(2);w.manual_model.setCurrentIndex(0);w.constant_input_mode.setCurrentIndex(0)
        w.manual_tensor.cells.item(0,0).setText('.8');w.axis.setText('0 0 1');constant=w.forward_settings()
        w.manual_model.setCurrentIndex(1);s=w.manual_spectral;s.direction.setText('1 2 3');s.fields['L2','width'].setText('2.3');spectral=w.forward_settings()
        w.manual_model.setCurrentIndex(0);w.constant_input_mode.setCurrentIndex(1)
        path=OUT/'imported-frame.json';path.write_text(json.dumps(imported_document(w)),encoding='utf-8')
        w.imported_path.setText(str(path));w.validate_imported_mdff();w.imported_declaration.setChecked(True);imported=w.forward_settings()
        for _ in range(2):
            w.constant_input_mode.setCurrentIndex(0);a=w.forward_settings();assert a.source_sha256==constant.source_sha256 and a.magnetization==constant.magnetization
            assert w.manual_tensor.cells.item(0,0).text()=='.8';w.preview_mdff();capture('constant-restored')
            w.manual_model.setCurrentIndex(1);a=w.forward_settings();assert a.source_sha256==spectral.source_sha256 and a.magnetization==spectral.magnetization
            w.preview_mdff();capture('spectral-restored')
            w.manual_model.setCurrentIndex(0);w.constant_input_mode.setCurrentIndex(1);a=w.forward_settings()
            assert a.source_sha256==imported.source_sha256 and a.magnetization==imported.magnetization
            w.preview_mdff();source=source_for(a)
            for actual,expected in zip(w.manual_preview_pair,source.tensors(source.energy_ev,np.eye(3),a.magnetization)):
                np.testing.assert_array_equal(actual,expected.tensor_angstrom2_per_ev)
        submit(imported);capture('imported-restored-submitted')
        checks.append(dict(case='three manual states',constant_sha256=constant.source_sha256,spectral_sha256=spectral.source_sha256,imported_sha256=imported.source_sha256,roundtrips=2,provider_preview_equal=True,submitted=True))
        cfg=config_from_dict(dict(model='atomic',atomic=dict(l3_ev=852.7,l2_ev=870.0,crystal_field_10dq_ev=.8)))
        cfg=replace(cfg,propagation='bloch',energy_scope='edges',grid=9,depth=3,subpixels=4,halfwidth=.7,radius=.12,centers=((.2,.2),(.2,-.2)),correction=False,worker_mode='manual',parallel_workers=1)
        settings=Settings(zone=(0,0,1),target=(2,0,0),voltage=200,thickness=.2,tilt=(-5,7),beam_cutoff=.7,potential_cutoff=1.4)
        result=calculate(Structure.nickel(),settings,cfg);folder=OUT/'historical-project';save_project(result,folder)
        w.open_project_path(folder);wait_worker();w.use_result_settings();app.processEvents()
        a=w.forward_settings();assert a.atomic==cfg.atomic and a.l3==852.7
        assert float(e.fields['cf'].text())==.8 and float(e.fields['l3'].text())==852.7 and e.fields['cf'].isReadOnly()
        w.preview_mdff();p=e.historical_preview
        for actual,expected in zip((p['plus'],p['minus']),prepare_provider(a).tensors(p['energy'],np.eye(3))):
            np.testing.assert_array_equal(actual,expected.tensor_angstrom2_per_ev)
        submit(a);e.advanced_parameters.setChecked(True);w.mdff_scroll.verticalScrollBar().setValue(0);capture('historical-restored-final')
        checks.append(dict(case='historical project restoration',l3_ev=852.7,splitting_ev=.8,read_only=True,provider_preview_equal=True,submitted=True,project=str(folder)))
        outcome=dict(exit_code=0,pid=os.getpid(),python=sys.executable,source_worktree=str(ROOT),platform=app.platformName(),checks=checks,gui_left_open=True,device_pixel_ratio=w.screen().devicePixelRatio(),screenshots=sorted(p.name for p in OUT.glob('*.png')))
    except Exception:
        outcome=dict(exit_code=1,pid=os.getpid(),checks=checks,error=traceback.format_exc(),gui_left_open=True)
    (OUT/'completed.json').write_text(json.dumps(outcome,indent=2),encoding='utf-8')


QtCore.QTimer.singleShot(1000,walkthrough)
sys.exit(app.exec())
