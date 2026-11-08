"""UI configuration boundaries only; no elastic or inelastic propagation."""
import json
from pathlib import Path

import numpy as np
import pytest
from PySide6 import QtCore, QtWidgets

from test_multisite_gui_run import app, window, controls
from test_group_mdff import source, imported
from single_element_helpers import document
from emcd_sim.gui.geometry import Structure
from emcd_sim.gui.generalized_forward import settings_for_source
from emcd_sim.gui.multisite_run import applied_inputs
from emcd_sim.gui.project_session import capture_configuration, restore_configuration
from emcd_sim.gui.project_configuration import save_configuration, load_configuration
from emcd_sim.gui.mdff_workspace import MDFFWorkspace
from emcd_sim.multisite_spectrum import ModeledEdgeWindow


def grouped(window):
    structure=Structure.from_cif(Path(__file__).parent/'fixtures/Fe3O4_inverse_spinel.cif')
    controls(window,structure)
    window.target.setText('2 2 0');window.set_values(dict(beam=.45,potential=.8))
    window.show_structure_viewer(show=False)
    editor=window.structure_viewer.editor
    window.set_magnetization_mode('local')
    assert sorted(len(r[2]) for r in editor.rows())==[8,16,32]
    return editor


def configure_fe(window,tmp_path):
    editor=grouped(window);rows=[]
    cfg=settings_for_source(source(tmp_path))
    for row in editor.rows():
        if row[1]=='O':editor.excluded_groups.add(row[0]);rows.append(row)
        else:
            rows.append(row[:3]+((0.,0.,1.),cfg))
            editor.energy_windows[row[0]]=ModeledEdgeWindow((704.,730.))
    editor.replace_rows(rows);editor.apply();window.emcd_stale()
    return editor


def test_preview_independent_of_unconfigured_m_and_mdff(window):
    editor=grouped(window)
    assert all(r[3] is None and r[4] is None for r in editor.rows())
    window.refresh()
    assert window.run_button.isEnabled(),window.run_button.toolTip()
    assert len(window.structure.atoms)==56
    window.basis_mode.setCurrentIndex(0);window.zone.setText('0 1 7');window.target.setText('2 0 0')
    window.set_values(dict(beam=3.2));window.refresh()
    assert not window.run_button.isEnabled()
    assert '121' in window.run_button.toolTip() or 'beams' in window.run_button.toolTip()


def test_selected_fe_preflight_and_persistence(window,tmp_path):
    editor=configure_fe(window,tmp_path)
    _,sites,_,_,signature=applied_inputs(window,window.forward_settings())
    assert sum(g.multiplicity for g in sites.groups)==24
    assert len(window.structure.atoms)==56 and len(signature[3])==1
    state=capture_configuration(window);path=tmp_path/'project'
    save_configuration(state,path);loaded=load_configuration(path)
    assert loaded['ready_for_calculation'],loaded.get('issues')
    restore_configuration(window,loaded)
    _,restored,_,_,_=applied_inputs(window,window.forward_settings())
    assert sum(g.multiplicity for g in restored.groups)==24
    assert window.structure_viewer.editor.excluded_groups==editor.excluded_groups
    assert len(window.structure_viewer.editor.rows())==3
    np.testing.assert_array_equal(loaded['structure'].atoms.positions,state['structure'].atoms.positions)


def test_enabled_missing_provider_is_named_and_cancel_restores(window,tmp_path):
    editor=configure_fe(window,tmp_path)
    accepted=editor.rows();excluded=set(editor.excluded_groups)
    fe=next(r for r in accepted if r[1]=='Fe')
    editor.replace_rows(tuple(r[:4]+(None,) if r[0]==fe[0] else r for r in accepted))
    editor.apply()
    with pytest.raises(ValueError,match=fe[0].replace('(','\\(').replace(')','\\)')):
        applied_inputs(window,window.forward_settings())
    editor._accepted_rows=accepted;editor._accepted_excluded=excluded;editor.cancel()
    assert editor.rows()==accepted and editor.excluded_groups==excluded


def test_nonmagnetic_participant_keeps_material_direction_unset(window,tmp_path):
    editor=grouped(window)
    data=document('Fe',nonmagnetic=True);path=tmp_path/'nonmagnetic.json'
    path.write_text(json.dumps(data),encoding='utf-8');cfg=settings_for_source(path)
    rows=[]
    for row in editor.rows():
        if row[1]=='O':editor.excluded_groups.add(row[0]);rows.append(row)
        else:rows.append(row[:3]+(None,cfg))
    editor.replace_rows(rows);editor.apply()
    assert all(r[3] is None for r in editor.rows())
    _,sites,_,_,_=applied_inputs(window,window.forward_settings())
    assert sum(g.multiplicity for g in sites.groups)==24


def test_shared_context_isolation_and_outer_cancel(window,tmp_path,monkeypatch):
    editor=configure_fe(window,tmp_path);accepted=editor.rows()
    group=next(r for r in accepted if r[1]=='Fe')
    local=window.open_mdff_context(group[0]);global_editor=window.open_mdff_context(None)
    assert isinstance(local,MDFFWorkspace) and isinstance(global_editor,MDFFWorkspace)
    assert local.model.count()==window.model_box.count()==3
    assert window.magnetization_mode=='local'
    previous=window.spin['eta'].value();window.spin['eta'].setValue(previous+.1)
    assert global_editor.has_unapplied_edits()
    monkeypatch.setattr(QtWidgets.QMessageBox,'question',lambda *a,**k:QtWidgets.QMessageBox.StandardButton.Cancel)
    global_editor.context_selector.setCurrentIndex(1)
    assert global_editor.context_selector.currentData() is None
    global_editor.reject()
    assert window.spin['eta'].value()==previous
    assert editor.rows()==accepted and window.magnetization_mode=='local'
    local=window.open_mdff_context(group[0])
    imported(local,source(tmp_path,name='new',scale=2.))
    assert local.apply_configuration() is not None
    assert editor.rows()!=accepted
    editor.cancel();assert editor.rows()==accepted
    assert window._accepted_global_mdff is None
    assert sum(c.objectName().startswith('settings_') for c in window.findChildren(QtWidgets.QWidget))==7


def test_accepted_global_configuration_restores_without_hidden_draft_override(window,tmp_path):
    controls(window,window.structure)
    cfg=settings_for_source(source(tmp_path,element='Ni'))
    window._accepted_global_mdff=cfg;window._saved_global_config=cfg
    state=capture_configuration(window);path=tmp_path/'global-project'
    save_configuration(state,path);loaded=load_configuration(path)
    restore_configuration(window,loaded)
    assert not window.mdff_dialog.has_unapplied_edits()
    restored=window.forward_settings()
    assert restored.source_sha256==cfg.source_sha256
    assert restored.magnetization==cfg.magnetization
    window.spin['eta'].setValue(window.spin['eta'].value()+.1)
    with pytest.raises(ValueError,match='draft'):
        window.forward_settings()
    assert window._accepted_global_mdff.source_sha256==cfg.source_sha256
