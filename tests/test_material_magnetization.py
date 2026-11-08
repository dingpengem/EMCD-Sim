"""Material-owned target M: GUI/provider data flow, without propagation."""
from dataclasses import replace
from pathlib import Path
import numpy as np
import pytest
from ase.build import bulk
from PySide6 import QtWidgets

from emcd_sim.gui.geometry import Structure
from emcd_sim.gui.generalized_forward import source_for
from emcd_sim.gui.emcd_forward import tensors
from emcd_sim.gui.project_session import capture_configuration,restore_configuration
from emcd_sim.gui.project_io import save_configuration,load_configuration
from test_multisite_gui_run import app,window,controls,sites_for,bind
from test_group_mdff import source


def click_apply(viewer):
    viewer.dialog_buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Apply).click()


def test_global_material_apply_cancel_and_model_switch(window):
    w=window;controls(w,Structure.nickel());w.show_structure_viewer();v=w.structure_viewer
    assert w.axis.isReadOnly() and w.atomic_editor.direction.isReadOnly() and w.manual_spectral.direction.isReadOnly()
    v.global_direction.setText('0 1 0')
    assert w.material_magnetization==(0,0,1)
    with pytest.raises(ValueError,match='Apply or Cancel pending Global Material M'):w.forward_settings()
    with pytest.raises(ValueError,match='Apply or Cancel pending Global Material M'):capture_configuration(w)
    v.reject();w.show_structure_viewer()
    assert v.global_direction.text()=='0 0 1'
    v.global_direction.setText('0 1 0');click_apply(v)
    assert w.material_magnetization==(0,1,0)
    w._manual_bindings['imported']['fields']['axis']='1 0 0'  # Historical per-model draft.
    for index in (1,2,0):w.model_box.setCurrentIndex(index);assert w.material_magnetization==(0,1,0)
    assert w.axis.text()=='0 1 0'
    v.global_direction.setText('nan 0 0');click_apply(v)
    assert 'finite' in v.editor.status.text() and w.material_magnetization==(0,1,0)
    v.reject();w.show_structure_viewer();assert v.global_direction.text()=='0 1 0'


def test_directional_xmcd_and_manual_use_material_in_generation_and_preview(window):
    w=window;controls(w,Structure.nickel());w.set_material_magnetization((1,0,0))
    w.model_box.setCurrentIndex(0);w.validate_xmcd(show_error=False);w.declaration.setChecked(True)
    cfg=w.forward_settings()
    assert cfg.magnetization==(1,0,0)
    a,b=tensors(cfg,np.array([cfg.l3,cfg.l2]),np.eye(3))
    assert np.isfinite(a.tensor_angstrom2_per_ev).all() and np.isfinite(b.tensor_angstrom2_per_ev).all()
    w.model_box.setCurrentIndex(2);w.manual_model.setCurrentIndex(1)
    w.manual_spectral.direction.setText('0 0 1')  # Stale presentation cannot change the actual target.
    cfg=w.forward_settings();provider=source_for(cfg)
    np.testing.assert_allclose(provider.metadata['magnetization_crystal'],[1,0,0],atol=1e-12)
    w.draw_manual_preview(cfg)
    assert w.manual_spectral.snapshot['source'].metadata==provider.metadata
    w.set_material_magnetization((0,1,0))
    assert 'STALE' in w.manual_preview_state.text()
    cfg=w.forward_settings();np.testing.assert_allclose(source_for(cfg).metadata['magnetization_crystal'],[0,1,0],atol=1e-12)


def test_atomic_frame_is_not_overwritten_by_target_and_preview_uses_pair(window):
    w=window;controls(w,Structure(bulk('Fe','bcc',a=2.88,cubic=True)))
    w.set_material_magnetization((0,0,-1));w.model_box.setCurrentIndex(1)
    e=w.atomic_editor;e.load_document(Path(__file__).resolve().parents[1]/'docs/examples/synthetic_fe_atomic_parameters.json')
    frame=e.table_values(e.frame);e.generate()
    assert e.validated_path,e.status.text()
    assert w.material_magnetization==(0,0,-1) and e.table_values(e.frame)==frame
    cfg=w.forward_settings();assert cfg.pair_reversed and cfg.magnetization==(0,0,-1)
    e.preview();assert getattr(e,'preview_dialog',None) is not None,e.status.text()
    assert e.preview_dialog.source.provenance()['direction_binding']['pair_state']=='minus'
    w.set_material_magnetization((1,0,0))
    with pytest.raises(ValueError,match='source axis.*frame_to_crystal'):w.forward_settings()
    assert e.table_values(e.frame)==frame


def test_imported_source_cannot_set_target_and_configuration_roundtrip(window,tmp_path):
    w=window;controls(w,Structure.nickel());path=source(tmp_path,element='Ni')
    w.set_material_magnetization((1,0,0));w.model_box.setCurrentIndex(2)
    w.constant_input_mode.setCurrentIndex(1);w.manual_model.setCurrentIndex(0)
    w.imported_path.setText(str(path));w.validate_imported_mdff();w.imported_declaration.setChecked(True)
    assert w.material_magnetization==(1,0,0)
    with pytest.raises(ValueError,match='source axis.*frame_to_crystal'):w.forward_settings()
    w.set_material_magnetization((0,0,-1));cfg=w.forward_settings();assert cfg.pair_reversed
    w.draw_manual_preview(cfg)
    native=source_for(replace(cfg,magnetization=(0,0,1),pair_reversed=False))
    np.testing.assert_array_equal(w.manual_preview_pair[0],native.minus.tensor_angstrom2_per_ev)
    state=load_configuration(save_configuration(capture_configuration(w),tmp_path/'project'))
    w.set_material_magnetization((1,0,0));restore_configuration(w,state)
    assert w.material_magnetization==(0,0,-1) and w.structure_viewer.global_direction.text()=='0 0 -1'
    restored=w.forward_settings();assert restored.pair_reversed and restored.source_sha256==cfg.source_sha256
    assert source_for(restored).metadata['frame_to_crystal']==native.metadata['frame_to_crystal']


def test_group_mdff_uses_parent_draft_and_cancel_keeps_other_group(window,tmp_path):
    w=window;structure,sites=sites_for(tmp_path);controls(w,structure);e=bind(w,sites)
    accepted=e.accepted_site_groups;other=e.rows()[1]
    e.groups.setCurrentItem(e.groups.topLevelItem(0));e.direction.setText('0 0 -1');e.update_direction()
    d=e.configure_mdff()
    assert d.axis.isReadOnly() and d.atomic.direction.isReadOnly() and d.manual_spectral.direction.isReadOnly()
    assert 'group draft M' in d.context.text() and d.material_direction()==(0,0,-1)
    d.preview_tensor();assert d.preview_states is not None,d.status.text()
    cfg=d.apply_configuration();assert cfg.pair_reversed,d.status.text()
    assert e.accepted_site_groups is accepted and e.rows()[1]==other
    w.structure_viewer.reject();assert e.rows()[0][3]==(0,0,1) and e.rows()[1]==other
    assert not w.structure_viewer.global_direction.isEnabled()
