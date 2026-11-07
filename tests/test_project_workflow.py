"""Representative project/history workflows using stored arrays, no solver runs."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import sys
import time
from copy import deepcopy
from dataclasses import replace, asdict
from pathlib import Path

import numpy as np
import pytest
from PySide6 import QtCore, QtWidgets, QtTest

from emcd_sim.gui.app import MainWindow
from emcd_sim.gui.project_session import restore_configuration, capture_configuration
from emcd_sim.gui.project_collection import load_collection
from emcd_sim.gui import project_io as io
from test_multisite_result_persistence import stored_project


@pytest.fixture(scope='module')
def app():return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def window(app,tmp_path,monkeypatch):
    def forbidden(*a,**k):pytest.fail('Project workflow started a numerical calculation')
    monkeypatch.setattr('emcd_sim.gui.stage_b.calculate',forbidden)
    monkeypatch.setattr('emcd_sim.gui.stage_b.calculate_multisite',forbidden)
    w=MainWindow(tmp_path/'workspace');w.errors=[];w.error=w.errors.append
    b=QtWidgets.QMessageBox.StandardButton
    monkeypatch.setattr(QtWidgets.QMessageBox,'warning',lambda *a,**k:b.Discard)
    monkeypatch.setattr(QtWidgets.QMessageBox,'question',lambda *a,**k:b.Yes)
    monkeypatch.setattr(QtWidgets.QMessageBox,'exec',lambda dialog:dialog.defaultButton().click())
    yield w
    if w.busy:w.cancel();w.worker.wait(5000)
    for dialog in w.dialogs:dialog.close()
    w.project_dirty=False;w.close();app.processEvents()


def result_fixture(tmp_path,manual=True):
    r=stored_project(tmp_path,manual=manual)
    r['config']=replace(r['config'],grid=9,depth=3,subpixels=4,fft_grid=16,slice_step=.2)
    r['settings']=replace(r['settings'],thickness=2.,beam_cutoff=.5,potential_cutoff=.8)
    r['metadata']['settings']=asdict(r['settings'])
    r['configuration'].update(config=r['config'],settings=r['settings'])
    return io.load_project(io.save_project(r,tmp_path/'fixture'))


def wait(w,app):
    deadline=time.monotonic()+25
    while w.busy and time.monotonic()<deadline:app.processEvents();QtTest.QTest.qWait(10)
    assert not w.busy,'Owned project IO did not finish'
    app.processEvents()


def retain(w,r):
    w.register_completed(r);row=w.selected_record
    w.display_saved_result(w.browser.cache[row['id']],row)
    return row['id']


def test_save_history_restore_compare_delete_and_save_as(window,app,tmp_path,monkeypatch):
    w=window;r=result_fixture(tmp_path);original=r['spectra']['I_A_plus'].copy()
    restore_configuration(w,r['configuration'])
    assert w.magnetization_mode=='local' and not w.axis.isEnabled()
    assert [row[0] for row in w.structure_viewer.editor.rows()]==['Fe(A)','Fe(B)']
    first=retain(w,r);second_result=deepcopy(r)
    second_result['settings']=replace(r['settings'],thickness=3.)
    second_result['metadata']['settings']=asdict(second_result['settings'])
    second_result['methods']['bloch']['settings']=second_result['settings']
    second_result['methods']['bloch']['metadata']['settings']=asdict(second_result['settings'])
    second_result['configuration']['settings']=second_result['settings']
    second=retain(w,second_result);assert first!=second and len(w.browser.registry.records)==2
    assert w.project_dirty
    root=tmp_path/'Project';w.save_to_path(root);wait(w,app)
    assert not w.errors and w.project_save_status=='Saved' and w.active_project_path==str(root)
    assert len(load_collection(root)['runs'])==2
    w.spin['thickness'].setValue(4.)
    assert w.project_save_status=='Unsaved Changes'
    w.save_project_action();wait(w,app);assert w.project_save_status=='Saved'
    assert load_collection(root)['state']['settings'].thickness==4.
    w.browser.select_id(first);w.browser.view();assert w.project_save_status=='Saved'
    w.use_result_settings()
    assert w.settings().thickness==2. and w.magnetization_mode=='local'
    np.testing.assert_array_equal(w.browser.cache[first]['spectra']['I_A_plus'],original)
    w.compare_selected();comparison=w.dialogs[-1]
    assert comparison.first.currentData()!=comparison.second.currentData() and comparison.rows
    comparison.second.setCurrentIndex(comparison.first.currentIndex())
    assert not comparison.rows and 'two distinct' in comparison.note.text()
    comparison.second.setCurrentIndex(1);assert comparison.rows
    export=tmp_path/'comparison.csv'
    monkeypatch.setattr(QtWidgets.QFileDialog,'getSaveFileName',lambda *a,**k:(str(export),'CSV'))
    comparison.export_data();assert export.is_file() and 'run_id' in export.read_text()
    w.browser.select_id(first);w.delete_selected_calculation()
    assert [row['id'] for row in w.browser.registry.records]==[second]
    assert len(load_collection(root)['runs'])==2  # Disk is unchanged before Save.
    # Preserve unrelated attachments, including a note inside the removed run.
    note=root/'calculations'/first/'user-notes.txt';note.write_text('Keep this user file')
    w.save_project_action();wait(w,app)
    assert [row['id'] for row,_ in load_collection(root)['runs']]==[second]
    assert note.read_text()=='Keep this user file'
    assert not (note.parent/'virtual_detector_eels.npz').exists()
    new=tmp_path/'Separate Project';w.save_to_path(new);wait(w,app)
    assert w.active_project_path==str(new) and (root/'project.json').exists()
    w.open_project_path(new);wait(w,app)
    assert not w.errors and len(w.browser.registry.records)==1 and w.browser.registry.records[0]['id']==second
    assert w.magnetization_mode=='local' and not w.axis.isEnabled()
    assert w.project_save_status=='Saved'
    w.show_structure_viewer();w.structure_viewer.view.update();assert w.project_save_status=='Saved'
    # A failed save must retain both current edits and the previous saved project.
    w.spin['thickness'].setValue(5.)
    def failed(*a,**k):raise OSError('Intentional focused save failure')
    monkeypatch.setattr('emcd_sim.gui.project_session.save_collection',failed)
    w.save_project_action();wait(w,app)
    assert w.project_save_status=='Save Failed' and w.project_dirty
    assert load_collection(new)['state']['settings'].thickness!=5.


def test_close_cancel_discard_and_explicit_replace(window,app,tmp_path,monkeypatch):
    w=window;r=result_fixture(tmp_path);restore_configuration(w,r['configuration'])
    first=retain(w,r)
    monkeypatch.setattr(QtWidgets.QMessageBox,'exec',lambda dialog:next(b for b in dialog.buttons() if b.text()=='Replace Selected Calculation').click())
    replacement=deepcopy(r);replacement['settings']=replace(r['settings'],thickness=7.)
    retain(w,replacement);assert len(w.browser.registry.records)==1 and w.selected_record['id']==first
    assert w.selected_record['thickness']==7. and w.selected_record['pending']
    b=QtWidgets.QMessageBox.StandardButton
    monkeypatch.setattr(QtWidgets.QMessageBox,'warning',lambda *a,**k:b.Cancel)
    w.close_project();assert w.browser.registry.records and w.project_dirty
    monkeypatch.setattr(QtWidgets.QMessageBox,'warning',lambda *a,**k:b.Discard)
    w.close_project();assert not w.browser.registry.records and w.active_project_path is None
    assert w.magnetization_mode=='global' and w.axis.isEnabled()


def test_missing_sources_and_legacy_ni_open_without_recalculation(window,app,tmp_path):
    from ase import Atoms
    from emcd_sim.gui.geometry import Structure
    from emcd_sim.gui.emcd_forward import ForwardSettings
    w=window;r=result_fixture(tmp_path,manual=False);restore_configuration(w,r['configuration']);retain(w,r)
    root=tmp_path/'External Project';w.save_to_path(root);wait(w,app);assert not w.errors
    for entry in r['groups'].values():Path(entry['metadata']['source']['path']).unlink()
    w.open_project_path(root);wait(w,app)
    assert not w.errors and w.magnetization_mode=='local' and not w.axis.isEnabled()
    np.testing.assert_array_equal(w.emcd_result['spectra']['I_A_plus'],r['spectra']['I_A_plus'])
    assert not w.emcd_button.isEnabled() and w.project_save_status=='Saved'
    w.start_emcd();assert not w.busy and w.errors  # Preflight rejects, no worker/solver.
    w.errors.clear()
    legacy=deepcopy(r);legacy.pop('groups');legacy.pop('weighted_sum');legacy.pop('configuration');legacy.pop('methods')
    legacy['config']=ForwardSettings(model='atomic',magnetization=(1.,0.,0.),l3=710.,l2=723.,grid=9,depth=3,subpixels=4)
    legacy['metadata'].pop('multisite');legacy['metadata'].pop('mdff_provider');legacy['metadata']['mdff']=asdict(legacy['config'])
    atoms=Atoms('Ni4',scaled_positions=[[0,0,0],[0,.5,.5],[.5,0,.5],[.5,.5,0]],cell=[3.52]*3,pbc=True)
    legacy['structure_snapshot']=io.structure_snapshot(Structure(atoms));m=legacy['maps']['Fe__L3'];legacy['maps']={'L3':m,'L2':m}
    folder=io.save_project(legacy,tmp_path/'Legacy Ni');w.open_project_path(folder);wait(w,app)
    assert not w.errors and w.magnetization_mode=='global' and w.axis.isEnabled()
    np.testing.assert_allclose([float(v) for v in w.axis.text().split()],[1,0,0])
    assert w.emcd_result['config'].model=='atomic'
    np.testing.assert_array_equal(w.emcd_result['spectra']['I_A_plus'],legacy['spectra']['I_A_plus'])
    identity=w.browser.registry.records[0]['id'];w.open_project_path(folder);wait(w,app)
    assert w.browser.registry.records[0]['id']==identity


def test_save_before_close_and_failed_save_never_discards(window,app,tmp_path,monkeypatch):
    w=window;w.spin['thickness'].setValue(3.)
    root=tmp_path/'Configuration Only'
    monkeypatch.setattr(QtWidgets.QFileDialog,'getSaveFileName',lambda *a,**k:(str(root),''))
    b=QtWidgets.QMessageBox.StandardButton
    monkeypatch.setattr(QtWidgets.QMessageBox,'warning',lambda *a,**k:b.Save)
    w.close_project();wait(w,app);app.processEvents()
    assert (root/'project.json').is_file() and not w.errors
    assert w.active_project_path is None and not w.project_dirty
    w.spin['thickness'].setValue(6.)
    def failed(*a,**k):raise OSError('Intentional save failure before closing')
    monkeypatch.setattr('emcd_sim.gui.project_session.save_collection',failed)
    w.close_project();wait(w,app)
    assert w.project_dirty and w.spin['thickness'].value()==6. and w.project_save_status=='Save Failed'


def test_group_editor_drafts_survive_configuration_only_save(window,app,tmp_path):
    w=window;r=result_fixture(tmp_path);restore_configuration(w,r['configuration'])
    editor=w.structure_viewer.editor;editor.groups.setCurrentItem(editor.groups.topLevelItem(0))
    dialog=editor.configure_mdff();dialog.declaration.setChecked(True)
    assert dialog.apply_configuration() is not None,dialog.status.text()
    editor.apply();dialog.manual_source.setText('Pending draft citation retained verbatim')
    w.structure_viewer.color_mode.setCurrentIndex(1);w.structure_viewer.magnetic_arrows.setChecked(True)
    snapshot=dialog.snapshot();assert dialog.has_unapplied_edits()
    root=tmp_path/'Draft Project';w.save_to_path(root);wait(w,app);assert not w.errors
    w.open_project_path(root);wait(w,app)
    assert not w.errors and w.magnetization_mode=='local'
    restored=w.structure_viewer.editor.mdff_dialogs['Fe(A)']
    assert restored.snapshot()['fields']==snapshot['fields'] and restored.has_unapplied_edits()
    assert w.structure_viewer.color_mode.currentIndex()==1 and w.structure_viewer.magnetic_arrows.isChecked()
    np.testing.assert_array_equal(w.structure_viewer.view.scene.group_indices[:3],[0,1,1])
    assert not w.emcd_button.isEnabled() and not w.browser.registry.records


def test_failed_collection_stage_keeps_previous_run_files(tmp_path,monkeypatch):
    from emcd_sim.gui.project_collection import save_collection
    r=result_fixture(tmp_path);state=r['configuration']
    rows=[(dict(id=name,name=name),r) for name in ('a','b','c')]
    root=save_collection(state,rows,tmp_path/'Staged Project')
    before=(root/'project.json').read_bytes();original=io.save_project;calls=[]
    def interrupted(*args,**kwargs):
        calls.append(1)
        if len(calls)==2:raise OSError('Controlled failure after one retained run was written')
        return original(*args,**kwargs)
    monkeypatch.setattr(io,'save_project',interrupted)
    with pytest.raises(OSError,match='Controlled failure'):save_collection(state,rows[1:],root,replace_existing=True)
    assert (root/'project.json').read_bytes()==before
    assert [row['id'] for row,_ in load_collection(root)['runs']]==['a','b','c']


def test_unavailable_global_atomic_provider_is_not_saved_as_legacy_ni(window,app,tmp_path):
    from ase.build import bulk
    from emcd_sim.gui.geometry import Structure,Settings
    from emcd_sim.gui.generalized_forward import ProviderSettings
    w=window;source=tmp_path/'missing-atomic.json'
    raw=(Path(__file__).resolve().parents[1]/'docs/examples/synthetic_fe_atomic_parameters.json').read_bytes()
    source.write_bytes(raw);digest=io.sha256(source);source.unlink()
    cfg=ProviderSettings(model='atomic',source=str(source),source_sha256=digest,ionizing_element='Fe',
        magnetic_state='uniform_fm',magnetization=(0.,0.,1.),axis_declared=True,l3=710.,l2=723.)
    state=dict(structure=Structure(bulk('Fe','bcc',a=2.87,cubic=True)),settings=Settings(zone=(0,0,1),target=(2,0,0),beam_cutoff=.9),
        config=cfg,magnetization_mode='global')
    root=io.save_configuration(state,tmp_path/'Missing Provider');w.open_project_path(root);wait(w,app)
    assert w.active_project_path==str(root) and w.magnetization_mode=='global'
    captured=capture_configuration(w)
    assert isinstance(captured['config'],ProviderSettings)
    assert captured['config'].source_sha256==digest and captured['config'].ionizing_element=='Fe'
    assert w.restored_source_reason() and not w.busy
    copy=tmp_path/'Unavailable Copy';w.save_to_path(copy);wait(w,app)
    restored=load_collection(copy)['state'];assert isinstance(restored['config'],ProviderSettings)
    assert restored['config'].source_sha256==digest and not restored['ready_for_calculation']


def test_restored_numerical_settings_and_requested_grid_are_not_replaced(window,tmp_path):
    from emcd_sim.gui.multisite_run import applied_inputs
    w=window;r=result_fixture(tmp_path);restore_configuration(w,r['configuration'])
    c=w.forward_settings(prepare=False)
    assert (c.grid,c.depth,c.fft_grid,c.subpixels,c.slice_step)==(9,3,16,4,.2)
    np.testing.assert_array_equal(w.detectors,r['config'].centers)
    cfg,sites,windows,reverse,signature=applied_inputs(w,c)
    assert cfg.energy_points==len(r['spectra']['energy_ev'])
    for edge in windows.values():np.testing.assert_array_equal(edge.energy_ev,r['spectra']['energy_ev'])
    state=capture_configuration(w)
    assert state['metadata']['numerical_selection']['mode']=='manual'


@pytest.mark.skipif(sys.platform!='win32' or os.environ.get('QT_QPA_PLATFORM')!='windows',reason='Explicit native Windows project workflow')
def test_native_windows_project_history_and_menus(window,app,tmp_path,monkeypatch):
    w=window;assert app.platformName()=='windows'
    r=result_fixture(tmp_path);restore_configuration(w,r['configuration'])
    retain(w,r);retain(w,deepcopy(r));w.show();app.processEvents()
    assert QtTest.QTest.qWaitForWindowExposed(w.windowHandle(),3000)
    menus={a.text():[b.text() for b in a.menu().actions()] for a in w.menuBar().actions() if a.menu()}
    assert set(menus)=={'File','Results'}
    assert menus['File']==['New Project','Open Project…','Save','Save As…','Close Project']
    assert menus['Results']==['Compare Calculations…','Export Results…']
    assert not w.findChildren(QtWidgets.QToolBar,'projectsToolbar')
    w.save_to_path(tmp_path/'Native Project');wait(w,app);assert w.project_save_status=='Saved'
    w.responsive.browser_section.setChecked(True);app.processEvents()
    item=w.browser.table.item(0,0);rect=w.browser.table.visualItemRect(item)
    QtTest.QTest.mouseClick(w.browser.table.viewport(),QtCore.Qt.MouseButton.LeftButton,pos=rect.center())
    button=next(b for b in w.browser.action_buttons if b.text()=='View Results')
    QtTest.QTest.mouseClick(button,QtCore.Qt.MouseButton.LeftButton);app.processEvents()
    w.eels_view.multisite_controls.quantity.setCurrentIndex(6)
    w.compare_selected();comparison=w.dialogs[-1];app.processEvents()
    assert comparison.isVisible() and comparison.first.count()==2 and comparison.second.count()==2
    comparison.canvas.draw()
    image=os.environ.get('EMCD_VIEWER_CHECK_IMAGE')
    if image:comparison.grab().save(str(Path(image).with_name('project_comparison_after.png')))
    comparison.close()
    if image:w.grab().save(image)
    figure=tmp_path/'visible-spectrum.svg'
    monkeypatch.setattr(QtWidgets.QFileDialog,'getSaveFileName',lambda *a,**k:(str(figure),'SVG'))
    action=next(a for a in w.eels_view.navigation.actions() if a.text()=='Export Figure…');action.trigger()
    assert figure.is_file() and not w.errors
