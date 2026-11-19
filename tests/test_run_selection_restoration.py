"""Run selection is a lossless input/results operation, never a calculation."""
from copy import deepcopy
from dataclasses import asdict, replace
import json
from pathlib import Path

import numpy as np
from ase import Atoms
from PySide6 import QtCore, QtWidgets, QtTest

from emcd_sim.gui import project_io as io
from emcd_sim.gui.geometry import Structure, orientation
from emcd_sim.gui.generalized_forward import settings_for_provider
from emcd_sim.gui.project_session import capture_configuration, restore_configuration
from emcd_sim.gui.emcd_forward import ForwardSettings
from test_project_workflow import app, window, result_fixture, retain, wait
from test_multisite_configuration import tensor_source
import pytest


def global_atomic(tmp_path):
    """Reuse saved-array fixtures and declared Atomic parameters, no propagation."""
    r=result_fixture(tmp_path)
    source=json.loads((Path(__file__).parents[1]/'docs/examples/synthetic_fe_atomic_parameters.json').read_text())
    source['parameters']['spin_resolved_holes']=[[.11,.71],[.22,.62],[.33,.53],[.24,.84],[.45,.65]]
    source['parameters']['crystal_field_ev']=1.23
    source['parameters']['exchange_ev']=.47
    source['parameters']['radial_integral_angstrom']=.073
    path=tmp_path/'atomic.json';path.write_text(json.dumps(source))
    cfg=replace(settings_for_provider(path,'atomic'),grid=9,depth=7,subpixels=8,
        halfwidth=.7,radius=.11,centers=((.23,.19),(.23,-.19)),fft_grid=32,slice_step=.13,
        worker_mode='manual',parallel_workers=2,memory_mode='manual',memory_budget_mib=2048)
    r=deepcopy(r)
    for key in ('groups','weighted_sum','configuration','methods'):r.pop(key,None)
    r['config']=cfg
    r['settings']=replace(r['settings'],zone=(0,0,1),target=(1,1,0),thickness=13.,voltage=200.,tilt=(-3.251234567891234,2.75123456789),
        beam_cutoff=1.2,potential_cutoff=8.)
    structure=Structure(Atoms('Fe2',scaled_positions=[[0,0,0],[.5,.5,.5]],cell=[2.884]*3,pbc=True),
        source=str(tmp_path/'missing-original.cif'),sha256='recorded-cif-identity')
    r['structure_snapshot']=io.structure_snapshot(structure)
    frame=orientation(structure.atoms.cell.array,r['settings'].zone,r['settings'].target)
    r['metadata'].update(settings=asdict(r['settings']),mdff=asdict(cfg),frame=frame.tolist(),
        beam_hkl=[[0,0,0],[1,1,0]],g=[[0,0],[np.sqrt(2)/2.884,0]],magnetization_crystal=list(cfg.magnetization))
    r['metadata'].pop('multisite');r['metadata'].pop('mdff_provider')
    fields=next(iter(r['maps'].values()));r['maps']={'L3':fields,'L2':deepcopy(fields)}
    return io.load_project(io.save_project(r,tmp_path/'global-fixture')),source


def add(w,result):
    row=w.browser.register(result)
    # Exercise the same automatic path as a single history selection.
    w.browser.auto_view()
    return row['id']


def local_fixture(path):
    path.mkdir(parents=True,exist_ok=True)
    return result_fixture(path)


def assert_raw_unchanged(w,copies):
    for identity,arrays in copies.items():
        for key,value in arrays.items():np.testing.assert_array_equal(w.browser.cache[identity]['spectra'][key],value)


def test_global_local_a_b_a_restores_complete_inputs(window,app,tmp_path,monkeypatch):
    w=window;a,document=global_atomic(tmp_path);b=local_fixture(tmp_path/'b')
    # Change both crystallography and diffraction, without constructing spectra.
    b['settings']=replace(b['settings'],voltage=300.,thickness=29.,tilt=(-5.1,7.2))
    b['configuration']['settings']=b['settings'];b['metadata']['settings']=asdict(b['settings'])
    def forbidden(*args,**kwargs):raise AssertionError('Selection invoked a calculation or numerical preview')
    monkeypatch.setattr(w,'preview_mdff',forbidden)
    monkeypatch.setattr(w,'start_preview',forbidden)
    monkeypatch.setattr(w.atomic_editor,'generate',forbidden)
    a_id=add(w,a)
    assert not w._run_restore_error,w.run_settings_notice.text()
    a['input_configuration']=capture_configuration(w)
    w.browser.cache[a_id]['input_configuration']=deepcopy(a['input_configuration'])
    assert w.magnetization_mode=='global' and w.axis.isEnabled()
    assert w.settings().zone==(0,0,1) and w.settings().target==(1,1,0)
    np.testing.assert_allclose(np.asarray(w.atomic_editor.draft()['holes'],float),document['parameters']['spin_resolved_holes'])
    b_id=add(w,b)
    assert w.magnetization_mode=='local' and not w.axis.isEnabled()
    assert w.settings().thickness==29. and w.settings().voltage==300.
    np.testing.assert_allclose(w.settings().tilt,(-5.1,7.2))
    assert w.structure.atoms.get_chemical_symbols()!=['Fe','Fe']
    assert w.structure_viewer.editor.rows()[0][4].model=='imported'
    copies={i:{k:v.copy() for k,v in w.browser.cache[i]['spectra'].items()} for i in (a_id,b_id)}
    w.project_dirty=False
    confirmations=[]
    monkeypatch.setattr(w,'confirm_project_changes',lambda *a:confirmations.append(a) or True)
    for identity in (a_id,b_id,a_id):
        w.browser.select_id(identity);w.browser.auto_view()
        assert w.selected_record['id']==identity and not w.project_dirty
    QtTest.QTest.qWait(200);app.processEvents()
    assert w.selected_record['id']==a_id and not w.project_dirty
    assert not confirmations
    assert w.settings()==a['settings']
    assert w.magnetization_mode=='global' and w.model_box.currentIndex()==1
    np.testing.assert_allclose(w.structure.atoms.cell.array,np.eye(3)*2.884)
    np.testing.assert_allclose(w.material_magnetization,a['config'].magnetization)
    d=w.atomic_editor.draft()
    np.testing.assert_array_equal(d['holes'],a['input_configuration']['metadata']['gui_drafts']['atomic']['holes'])
    expected=a['input_configuration']['metadata']['gui_drafts']['atomic']
    assert d['fields']==expected['fields'] and d['energy']==expected['energy']
    np.testing.assert_array_equal(d['frame'],expected['frame'])
    assert float(d['fields']['cf'])==1.23 and float(d['fields']['exchange'])==.47 and float(d['fields']['radial'])==.073
    assert w.compute_resources.settings()['resource_allocation'] is None
    assert w.compute_resources.settings()['parallel_workers']==2
    assert w.structure.source.endswith('missing-original.cif')
    assert_raw_unchanged(w,copies)
    # A comparison selection must never arbitrarily restore its first row.
    flags=QtCore.QItemSelectionModel.SelectionFlag.Select|QtCore.QItemSelectionModel.SelectionFlag.Rows
    index=next(i for i in range(w.browser.table.rowCount()) if w.browser.table.item(i,0).data(QtCore.Qt.ItemDataRole.UserRole)==b_id)
    w.browser.table.selectionModel().select(w.browser.table.model().index(index,0),flags)
    w.browser.auto_view();w.browser.view()
    assert w.settings()==a['settings'] and w.selected_record['id']==a_id


@pytest.mark.parametrize('source_state',['missing','changed'])
def test_snapshot_save_open_missing_source_and_latest_selected_run(window,app,tmp_path,source_state):
    w=window;a,document=global_atomic(tmp_path);a_id=add(w,a)
    a['input_configuration']=capture_configuration(w)
    # register() keeps a shallow result dictionary, so bind the frozen snapshot
    # explicitly, just as worker completion does.
    w.browser.cache[a_id]['input_configuration']=deepcopy(a['input_configuration'])
    b=local_fixture(tmp_path/'b');b_id=add(w,b)
    editor=w.structure_viewer.editor
    oxygen=tuple(i for i,a in enumerate(w.structure.atoms) if a.symbol=='O')
    editor.excluded_groups.add('O (elastic only)')
    editor.restore_rows(list(editor.rows())+[('O (elastic only)','O',oxygen,None,None)])
    editor.apply()
    b['input_configuration']=capture_configuration(w)
    w.browser.cache[b_id]['input_configuration']=deepcopy(b['input_configuration'])
    w.browser.select_id(a_id);w.browser.view()
    root=tmp_path/'Run snapshots';w.save_to_path(root);wait(w,app)
    assert not w.errors
    assert (root/'calculations'/a_id/'run_inputs/project.json').is_file()
    # Project-level editable inputs are A, but the automatically selected last
    # history entry B must restore B's own snapshot, not those project inputs.
    w.open_project_path(root);wait(w,app)
    assert w.selected_record['id']==b_id and w.magnetization_mode=='local'
    assert w.settings()==b['settings']
    assert 'O (elastic only)' in w.structure_viewer.editor.excluded_groups
    assert w.structure_viewer.editor.rows()[-1][2]==oxygen
    w.browser.select_id(a_id);w.browser.view()
    assert w.settings()==a['settings'] and w.magnetization_mode=='global'
    if source_state=='missing':Path(a['config'].source).unlink()
    else:Path(a['config'].source).write_text('{}')
    saved=root/'calculations'/a_id
    reread=io.load_project(saved)
    before={k:v.copy() for k,v in reread['spectra'].items()}
    w.display_saved_result(reread,w.selected_record)
    assert not w._run_restore_error
    assert not w.emcd_button.isEnabled()
    assert 'missing' in w.run_settings_notice.text().lower() or 'unavailable' in w.run_settings_notice.text().lower()
    np.testing.assert_allclose(np.asarray(w.atomic_editor.draft()['holes'],float),document['parameters']['spin_resolved_holes'])
    for key,value in before.items():np.testing.assert_array_equal(w.emcd_result['spectra'][key],value)


def test_xmcd_and_explicit_imported_pair_restore_independently(window,tmp_path):
    w=window;r,_=global_atomic(tmp_path)
    imported=tensor_source(tmp_path,'explicit-pair',element='Fe',axis=(0,0,1),manual=True,
        frame=[[0,-1,0],[1,0,0],[0,0,1]])
    imported=replace(imported,pair_reversed=True,magnetization=(0.,0.,-1.),grid=9,depth=7)
    r['config']=imported;r['metadata']['mdff']=asdict(imported)
    r['metadata']['magnetization_crystal']=list(imported.magnetization)
    r['methods']={'bloch':dict(r)};r['methods']['bloch'].pop('methods',None)
    pair_id=add(w,r)
    assert not w._run_restore_error,w.run_settings_notice.text()
    assert w._accepted_global_mdff.pair_reversed
    np.testing.assert_array_equal(w.material_magnetization,[0,0,-1])
    source_bytes=Path(imported.source).read_bytes()
    source=w.imported_info
    assert source is not None and source.sha256==imported.source_sha256
    np.testing.assert_allclose(source.plus.tensor_angstrom2_per_ev[0,0,1],.1j)
    x=deepcopy(r);x.pop('input_configuration',None)
    source_path=Path(__file__).parents[1]/'data/wien2k_ni/Ni_fm.xmcd'
    cfg=ForwardSettings(model='xmcd',source=str(source_path),source_sha256=io.sha256(source_path),axis_declared=True,
        magnetization=(1.,0.,0.),eta=.7345678912345,beta=.61357913579,l3=831.271,l2=848.698,grid=9,depth=11,correction=False)
    x['config']=cfg;x['metadata']['mdff']=asdict(cfg)
    x['spectra']['energy_ev']=np.linspace(cfg.l3,cfg.l2,len(x['spectra']['energy_ev']))
    x['metadata']['energy_ev']=x['spectra']['energy_ev'].tolist()
    structure=Structure(Atoms('Ni4',scaled_positions=[[0,0,0],[0,.5,.5],[.5,0,.5],[.5,.5,0]],cell=[3.524]*3,pbc=True))
    x['structure_snapshot']=io.structure_snapshot(structure)
    x['settings']=replace(x['settings'],zone=(0,1,7),target=(2,0,0),voltage=250.,thickness=8.,tilt=(-7.25,1.13))
    x['metadata'].update(settings=asdict(x['settings']),frame=orientation(structure.atoms.cell.array,(0,1,7),(2,0,0)).tolist(),
        beam_hkl=[[0,0,0],[2,0,0]],g=[[0,0],[2/3.524,0]])
    x['methods']={'bloch':dict(x)};x['methods']['bloch'].pop('methods',None)
    x_id=add(w,x)
    assert not w._run_restore_error,w.run_settings_notice.text()
    assert w.model_box.currentIndex()==0 and w.spin['eta'].value()==cfg.eta and w.spin['beta'].value()==cfg.beta
    assert w.source_path.text()==str(source_path) and w.validated_path==str(source_path)
    for identity in (pair_id,x_id,pair_id):w.browser.select_id(identity);w.browser.view()
    assert w._accepted_global_mdff.pair_reversed and w.settings()==r['settings']
    assert Path(imported.source).read_bytes()==source_bytes


def test_late_result_load_does_not_replace_latest_selection(window,tmp_path,monkeypatch):
    w=window;a=local_fixture(tmp_path/'a');b=local_fixture(tmp_path/'b')
    b['settings']=replace(b['settings'],thickness=19.);b['configuration']['settings']=b['settings']
    a_id=add(w,a);b_id=add(w,b)
    a_record=next(row for row in w.browser.registry.records if row['id']==a_id)
    a_record['path']=str(tmp_path/'a/fixture')
    w.browser.cache.pop(a_id)
    pending=[]
    def defer(operation,completed):w.busy=True;pending.append(completed)
    monkeypatch.setattr(w,'io_operation',defer)
    w.browser.select_id(a_id);w.browser.view()
    assert pending
    w.browser.select_id(b_id);w.browser.auto_view()
    pending[0](a)  # older I/O completion arrives after B was selected
    w.busy=False;w.browser.auto_view()
    assert w.selected_record['id']==b_id and w.settings().thickness==19.


def test_clicking_current_run_and_returning_from_multiselection_restore_inputs(window,app,tmp_path):
    w=window;a=local_fixture(tmp_path/'a');b=local_fixture(tmp_path/'b')
    a_id=add(w,a);b_id=add(w,b)
    w.browser.select_id(a_id);w.browser.auto_view()
    w.spin['thickness'].setValue(99.)
    w.show();w.browser_dock.show();app.processEvents()
    item=next(w.browser.table.item(i,0) for i in range(w.browser.table.rowCount())
        if w.browser.table.item(i,0).data(QtCore.Qt.ItemDataRole.UserRole)==a_id)
    w.browser.table.scrollToItem(item)
    QtTest.QTest.mouseClick(w.browser.table.viewport(),QtCore.Qt.MouseButton.LeftButton,
        pos=w.browser.table.visualItemRect(item).center())
    app.processEvents()
    assert w.settings().thickness==a['settings'].thickness
    w.browser.table.selectAll();w.browser.auto_view()
    w.spin['thickness'].setValue(98.)
    w.browser.select_id(a_id);w.browser.auto_view()
    assert w.settings().thickness==a['settings'].thickness and w.selected_record['id']==a_id


def test_incomplete_legacy_does_not_show_previous_inputs(window,tmp_path):
    w=window;a,_=global_atomic(tmp_path);add(w,a)
    incomplete=deepcopy(a);incomplete.pop('input_configuration',None);incomplete['structure_snapshot']=None
    w.display_saved_result(incomplete)
    assert w._run_restore_error and not w.emcd_button.isEnabled()
    assert 'incomplete' in w.run_settings_notice.text().lower()
    assert all(widget.isHidden() for widget,_ in w._unavailable_input_widgets)
    assert w.emcd_result is incomplete
    w.display_saved_result(a)
    assert not w._run_restore_error and w.settings()==a['settings']


def test_legacy_atomic_model_is_not_replaced_by_a_generalized_provider(window,tmp_path):
    w=window
    r,_=global_atomic(tmp_path)
    cfg=ForwardSettings(model='atomic',l3=710.,l2=723.,grid=9,depth=7,correction=False)
    cfg=replace(cfg,atomic=replace(cfg.atomic,l3_ev=710.,l2_ev=723.))
    r['config']=cfg;r['metadata']['mdff']=asdict(cfg)
    crystal=Structure(Atoms('Ni4',scaled_positions=[[0,0,0],[0,.5,.5],[.5,0,.5],[.5,.5,0]],cell=[3.524]*3,pbc=True))
    r['structure_snapshot']=io.structure_snapshot(crystal)
    r['methods']={'bloch':dict(r)};r['methods']['bloch'].pop('methods',None)
    add(w,r)
    assert not w._run_restore_error,w.run_settings_notice.text()
    restored=w.forward_settings(prepare=False)
    assert not hasattr(restored,'provider_schema') and restored.atomic==cfg.atomic
    assert w.atomic_editor.historical_config==cfg


def test_older_local_without_providers_restores_available_inputs(window,tmp_path):
    w=window;r=local_fixture(tmp_path/'older')
    r.pop('configuration');r.pop('input_configuration',None)
    add(w,r)
    assert w.magnetization_mode=='local' and w.settings()==r['settings']
    np.testing.assert_array_equal(w.structure.atoms.cell.array,r['structure_snapshot']['lattice_angstrom'])
    assert all(row[4] is None for row in w.structure_viewer.editor.rows())
    assert not w.emcd_button.isEnabled() and 'unavailable' in w.run_settings_notice.text()


def test_retired_setting_is_identified_without_reinterpreting_saved_arrays(window,tmp_path):
    w=window;r,_=global_atomic(tmp_path)
    r['config']=replace(r['config'],correction=True)
    before={k:v.copy() for k,v in r['spectra'].items()}
    add(w,r)
    assert 'retired' in w.run_settings_notice.text() and not w.emcd_button.isEnabled()
    assert r['config'].correction  # saved scientific inputs remain unchanged
    for key,value in before.items():np.testing.assert_array_equal(w.emcd_result['spectra'][key],value)


def test_worker_completion_retains_inputs_captured_at_start(window,tmp_path,monkeypatch):
    w=window;r=result_fixture(tmp_path)
    restore_configuration(w,r['configuration'])
    monkeypatch.setattr('emcd_sim.gui.propagation.numerical_info',lambda *a,**k:dict(bw_beams=2,execution={}))
    monkeypatch.setattr('emcd_sim.gui.parallel_resources.require_supported',lambda *a:None)
    monkeypatch.setattr('emcd_sim.gui.parallel_resources.bind_allocation',lambda cfg,*a:cfg)
    monkeypatch.setattr(w.compute_resources,'show_estimate',lambda *a:None)
    started=[]
    monkeypatch.setattr('emcd_sim.gui.calculation_worker.EMCDWorker.start',lambda worker:started.append(worker))
    w.start_emcd()
    assert started and w.busy,w.errors
    frozen=deepcopy(w._run_configuration)
    w.spin['thickness'].setValue(99.)
    w.emcd_completed(r)
    assert r['input_configuration']['settings']==frozen['settings']
    assert r['input_configuration']['settings'].thickness!=99.
    assert w.settings().thickness==frozen['settings'].thickness
    assert r['input_configuration']['group_records']==frozen['group_records']
    w._emcd_elapsed_timer.stop();w.busy=False
