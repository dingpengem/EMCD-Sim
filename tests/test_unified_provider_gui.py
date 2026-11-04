"""End-to-end provider presentation, source validation, worker and exports."""
import json,time
from pathlib import Path
import numpy as np
import pytest
from ase import Atoms
from ase.build import bulk
from PySide6 import QtWidgets,QtCore
from emcd_sim.gui.app import MainWindow
from emcd_sim.gui.geometry import Structure
from emcd_sim.gui.project_io import save_project,load_project
from emcd_sim.gui.emcd_forward import export_result
from test_unified_mdff_providers import oxygen_source,xmcd_source
from test_atomic_ionization import parameter_file

MODELS=['XMCD-constrained MDFF','Atomic Ionization MDFF','Imported Complex MDFF Tensor']


def app():return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def configure(w,channel='single'):
    w.numerical_mode.setCurrentIndex(1)
    w.zone.setText('0 0 1');w.target.setText('1 0 0')
    w.set_values(dict(kv=200,tx=-5,ty=7,thickness=.2,beam=.6,potential=1.2,grid=9,depth=9,
        subpixels=8,fft_grid=16,slice_step=.01,halfwidth=.7,radius=.12))
    w.propagation_box.setCurrentIndex(2);w.channeling_box.setCurrentIndex(channel=='double')
    w.worker_mode.setCurrentIndex(1);w.worker_count.setValue(1)
    w.detectors=np.array([[.2,.2],[.2,-.2]]);w.sync_detectors();w.correction.setChecked(False)


def wait(w,application):
    deadline=time.monotonic()+90
    while w.busy and time.monotonic()<deadline:application.processEvents();time.sleep(.01)
    assert not w.busy


@pytest.mark.parametrize('model',['xmcd','imported'])
@pytest.mark.parametrize('channel',['single','double'])
def test_non_3d_k_edge_actual_gui_export_reopen(tmp_path,monkeypatch,model,channel):
    monkeypatch.setenv('EMCD_GUI_WORKSPACE',str(tmp_path/'workspace'))
    application=app();w=MainWindow();errors=[];w.error=errors.append
    try:
        w.structure=Structure(Atoms('O',cell=np.eye(3)*4,scaled_positions=[[0,0,0]],pbc=True),'Synthetic O K software test only')
        configure(w,channel)
        if model=='imported':
            p=oxygen_source(tmp_path/'synthetic.json');w.model_box.setCurrentIndex(2)
            w.imported_path.setText(str(p));w.validate_imported_mdff();w.imported_declaration.setChecked(True)
        else:
            p,d=xmcd_source(tmp_path);w.model_box.setCurrentIndex(0);w.explicit_xmcd.setChecked(True)
            w.source_path.setText(str(p));w.xmcd_element.setText('O');w.xmcd_edge.setText('K')
            w.xmcd_selected.setText(json.dumps(d['selected_ev']));w.xmcd_provenance.setText(d['source'])
            w.xmcd_validity.setText(d['validity']);w.xmcd_scale.setText('1');w.xmcd_status.setCurrentText('synthetic')
            w.validate_xmcd();w.declaration.setChecked(True)
        w.energy_scope.setCurrentIndex(1);w.refresh();w.emcd_stale()
        assert w.emcd_button.isEnabled(),w.emcd_button.toolTip()
        w.start_emcd();wait(w,application)
        assert not errors,errors
        r=w.emcd_result
        assert set(r['maps'])=={'K'} and r['spectra']['energy_ev'].shape==(1,)
        assert [w.maps_view.choice.itemText(i) for i in range(w.maps_view.choice.count())]==['K']
        assert w.eels_view.choice.count()==1
        w.preview_mdff();assert not errors,errors
        combos=w.dialogs[-1].findChildren(QtWidgets.QComboBox)
        assert any([box.itemText(i) for i in range(box.count())]==['Full spectrum'] for box in combos)
        for view in (w.eels_view,w.maps_view,w.overview_view):
            view.redraw()
            assert view.figure._suptitle is not None,[(t.get_text()) for ax in view.figure.axes for t in ax.texts]
            assert 'L3' not in view.figure._suptitle.get_text()
        export_result(r,tmp_path/'exports')
        assert (tmp_path/'exports/K_angular_maps.png').is_file()
        assert (tmp_path/'exports/virtual_detector_eels.svg').is_file()
        assert not (tmp_path/'exports/L3_angular_maps.png').exists()
        opened=load_project(tmp_path/'exports')
        np.testing.assert_array_equal(opened['spectra']['D_mag'],r['spectra']['D_mag'])
        w.emcd_result=opened;w.use_result_settings();w.emcd_stale()
        assert w.emcd_button.isEnabled(),w.emcd_button.toolTip()
        p.write_bytes(p.read_bytes()+b' ');w.emcd_stale()
        assert not w.emcd_button.isEnabled()
        checkbox=w.declaration if model=='xmcd' else w.imported_declaration
        assert not checkbox.isChecked()
        assert w.emcd_result is not None
    finally:
        if w.busy:w.cancel();w.worker.wait(15000)
        for dialog in w.dialogs:dialog.close()
        w.close();application.processEvents()


def test_same_three_choices_and_no_default_transfer(tmp_path,monkeypatch):
    monkeypatch.setenv('EMCD_GUI_WORKSPACE',str(tmp_path/'workspace'))
    application=app();w=MainWindow()
    try:
        w.numerical_mode.setCurrentIndex(1)
        for element,lattice in (('Ni','fcc'),('Fe','bcc'),('Co','hcp'),('Cr','bcc')):
            w.structure=Structure(bulk(element,lattice),'Provider menu test')
            assert [w.model_box.itemText(i) for i in range(w.model_box.count())]==MODELS
            if element!='Ni':
                for index in range(3):
                    w.model_box.setCurrentIndex(index);w.emcd_stale()
                    assert not w.emcd_button.isEnabled()
    finally:w.close();application.processEvents()


def test_atomic_input_route_and_failed_generation_clears_stale_state(tmp_path,monkeypatch):
    monkeypatch.setenv('EMCD_GUI_WORKSPACE',str(tmp_path/'workspace'))
    application=app();w=MainWindow();errors=[];w.error=errors.append
    try:
        w.structure=Structure(bulk('Fe','bcc',a=2.866,cubic=True),'Synthetic Fe')
        configure(w);w.target.setText('1 1 0');w.model_box.setCurrentIndex(1)
        path=parameter_file(tmp_path/'atomic.json');w.atomic_parameter_path.setText(str(path));w.validate_atomic_parameters()
        w.atomic_declaration.setChecked(True);w.energy_scope.setCurrentIndex(1);w.refresh();w.emcd_stale()
        assert w.emcd_button.isEnabled(),w.emcd_button.toolTip()
        assert w.forward_settings().model=='atomic'
        w.start_emcd();wait(w,application);assert not errors,errors
        save_project(w.emcd_result,tmp_path/'project');w.emcd_result=load_project(tmp_path/'project');w.use_result_settings()
        assert w.model_box.currentIndex()==1 and w.forward_settings().ionizing_element=='Fe'
        path.write_text('{}');w.validate_atomic_parameters()
        assert w.atomic_provider_info is None and not w.atomic_declaration.isChecked()
        assert not w.emcd_button.isEnabled() and w.emcd_result is not None
    finally:
        if w.busy:w.cancel();w.worker.wait(15000)
        w.close();application.processEvents()


def test_imported_reopen_and_revalidation_clear_acknowledgement(tmp_path,monkeypatch):
    from emcd_sim.gui.generalized_forward import settings_for_source
    from single_element_helpers import write_source
    monkeypatch.setenv('EMCD_GUI_WORKSPACE',str(tmp_path/'workspace'))
    application=app();w=MainWindow()
    try:
        w.numerical_mode.setCurrentIndex(1);w.model_box.setCurrentIndex(2)
        p=write_source(tmp_path/'imported.json');cfg=settings_for_source(p)
        w.restore_imported_settings(cfg)
        assert w.imported_info is not None and w.imported_declaration.isChecked()
        p.write_bytes(p.read_bytes()+b' ')
        w.validate_imported_mdff()
        assert w.imported_info is not None and not w.imported_declaration.isChecked()
        w.restore_imported_settings(cfg)
        assert w.imported_info is None and not w.imported_declaration.isChecked()
        p.unlink();w.restore_imported_settings(cfg)
        assert w.imported_info is None and not w.imported_declaration.isChecked()
    finally:w.close();application.processEvents()


def test_ambiguous_xmcd_requires_explicit_selections_no_ni_default(tmp_path,monkeypatch):
    monkeypatch.setenv('EMCD_GUI_WORKSPACE',str(tmp_path/'workspace'))
    application=app();w=MainWindow()
    try:
        w.structure=Structure(bulk('Fe','bcc',a=2.866,cubic=True),'Synthetic ambiguity test')
        configure(w);w.target.setText('1 1 0');w.model_box.setCurrentIndex(0);w.explicit_xmcd.setChecked(True)
        e=np.linspace(500,1000,51);n=.3+np.exp(-((e-700)/20)**2);m=.04*np.exp(-((e-700)/20)**2)
        p=tmp_path/'ambiguous.xmcd';np.savetxt(p,np.column_stack((e,n+m,n-m,2*m,2*n)))
        w.source_path.setText(str(p));w.xmcd_element.setText('Fe');w.xmcd_provenance.setText('Original synthetic single-feature fixture')
        w.xmcd_validity.setText('Not physical Fe spectroscopy');w.xmcd_scale.setText('1');w.xmcd_status.setCurrentText('synthetic')
        w.validate_xmcd();w.declaration.setChecked(True)
        assert w.source_info['selected'] is None
        with pytest.raises(ValueError,match='Explicit native edge selections'):w.forward_settings()
        w.xmcd_selected.setText('{"L3":710,"L2":723}');w.declaration.setChecked(True)
        cfg=w.forward_settings();assert (cfg.l3,cfg.l2)==(710,723)
    finally:w.close();application.processEvents()


def test_run_detects_source_change_without_prior_gui_event(tmp_path,monkeypatch):
    from single_element_helpers import write_source
    monkeypatch.setenv('EMCD_GUI_WORKSPACE',str(tmp_path/'workspace'))
    application=app();w=MainWindow();errors=[];w.error=errors.append
    try:
        w.structure=Structure(bulk('Fe','bcc',a=2.866,cubic=True),'Synthetic source-integrity test')
        configure(w);w.target.setText('1 1 0');w.model_box.setCurrentIndex(2)
        p=write_source(tmp_path/'imported.json');w.imported_path.setText(str(p));w.validate_imported_mdff()
        w.imported_declaration.setChecked(True)
        p.write_bytes(p.read_bytes()+b' ')
        w.start_emcd()
        assert errors and not w.busy and w.imported_info is None
        assert not w.imported_declaration.isChecked() and not w.emcd_button.isEnabled()
    finally:w.close();application.processEvents()


def test_historical_ni_missing_xmcd_clears_acknowledgement(tmp_path,monkeypatch):
    from emcd_sim.gui.emcd_forward import DEFAULT_SOURCE
    monkeypatch.setenv('EMCD_GUI_WORKSPACE',str(tmp_path/'workspace'))
    application=app();w=MainWindow();errors=[];w.error=errors.append
    try:
        w.numerical_mode.setCurrentIndex(1)
        p=tmp_path/'ni.xmcd';p.write_bytes(DEFAULT_SOURCE.read_bytes())
        w.source_path.setText(str(p));w.validate_xmcd();w.declaration.setChecked(True)
        p.unlink();w.start_emcd()
        assert errors and not w.busy and not w.declaration.isChecked()
        assert w.source_info is None and not w.emcd_button.isEnabled()
    finally:w.close();application.processEvents()
