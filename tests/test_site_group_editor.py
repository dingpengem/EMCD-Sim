"""Focused interaction checks for transient site assignments and directions."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import sys
import json

import numpy as np
import pytest
from ase import Atoms
from ase.build import bulk
from PySide6 import QtCore, QtWidgets, QtTest

from emcd_sim.multisite import IonizationSiteGroup, MultiSiteIonization
from emcd_sim.gui.structure_viewer import CrystalStructureDialog
from emcd_sim.gui.generalized_forward import settings_for_source, source_for
from single_element_helpers import document


def declared_reference(tmp_path, name, element, direction=(0,0,1), frame=None):
    data = document(element)
    data['magnetization_crystal'] = list(direction)
    if frame is not None:
        data.update(basis='declared_local',frame_to_crystal=frame.tolist())
    path = tmp_path/(name+'.json')
    path.write_text(json.dumps(data),encoding='utf-8')
    return settings_for_source(path)


@pytest.fixture(scope='module')
def app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def dialog(app):
    viewer = CrystalStructureDialog()
    yield viewer
    viewer.close();app.processEvents()


def create(editor, name, indices, direction='0 0 1'):
    editor.mode.setCurrentIndex(1)
    editor.select_indices(indices)
    editor.name.setText(name);editor.direction.setText(direction)
    editor.create_group()


def test_afm_drafts_apply_cancel_and_real_reference_handoff(dialog,app,tmp_path):
    atoms = bulk('Cr','bcc',a=2.88,cubic=True); original = atoms.copy()
    dialog.set_structure(atoms); editor = dialog.editor
    create(editor,'Cr-up',[0]);create(editor,'Cr-down',[1],'0 0 -2')
    assert dialog.view.scene.site_groups is None
    assert np.array_equal(dialog.view.scene.group_indices,[0,1])
    np.testing.assert_allclose(dialog.view.scene.directions,[[0,0,1],[0,0,-1]])
    assert 'unconfigured' in editor.status.text() and 'not executable' in editor.status.text()
    assert editor.apply() is None and dialog.accepted_site_groups is None
    assert not editor.dirty
    # Applied drafts survive close/reopen and an explicit refresh of the same structure.
    dialog.close();dialog.set_structure(atoms,force=True);dialog.show();app.processEvents()
    assert len(editor.rows()) == 2
    editor.name.setText('changed');editor.rename_group()
    editor.direction.setText('1 2 3');editor.update_direction()
    assert editor.dirty
    dialog.reject();app.processEvents()
    assert [r[0] for r in editor.rows()] == ['Cr-up','Cr-down']
    np.testing.assert_allclose(editor.rows()[1][3],[0,0,-1])
    # No provider is invented: supply declared source references through the handoff API.
    references = [declared_reference(tmp_path,'up','Cr'),
                  declared_reference(tmp_path,'down','Cr',(0,0,-1))]
    for name,reference in zip(('Cr-up','Cr-down'),references):
        editor.set_mdff_reference(name,reference)
    model = editor.apply()
    assert isinstance(model,MultiSiteIonization)
    assert model is dialog.accepted_site_groups
    assert [g.multiplicity for g in model.groups] == [1,1]
    assert [g.mdff_reference for g in model.groups] == references
    assert atoms == original


def test_fe3o4_assign_remove_delete_and_filters(dialog):
    atoms = Atoms('Fe3O4',scaled_positions=[(i/7,(i*.23)%1,(i*.37)%1) for i in range(7)],cell=[8]*3,pbc=True)
    dialog.set_structure(atoms);editor = dialog.editor
    create(editor,'Fe(A)',[0],'0 0 -1');create(editor,'Fe(B)',[1])
    editor.select_indices([2]);editor.assign_selected()
    assert editor.rows()[1][2] == (1,2)
    create(editor,'O',[3,4,5,6],'1 1 0')
    assert [r[1] for r in editor.rows()] == ['Fe','Fe','O']
    editor.filter.setCurrentIndex(2);assert editor.atom_list.count() == 0
    editor.groups.setCurrentItem(editor.groups.topLevelItem(2));editor.delete_group()
    assert editor.atom_list.count() == 4
    editor.filter.setCurrentIndex(1);assert editor.atom_list.count() == 3
    editor.filter.setCurrentIndex(0)
    editor.groups.setCurrentItem(editor.groups.topLevelItem(1))
    editor.select_indices([2]);editor.remove_selected()
    assert editor.rows()[1][2] == (1,)
    assert 'Unassigned' in editor.atom_list.item(2).text()
    editor.select_indices([1])
    with pytest.raises(ValueError,match='at least one'):editor.remove_selected()
    editor.delete_group();assert len(editor.rows()) == 1


def test_invalid_assignment_and_direction_edits_are_atomic(dialog):
    atoms = Atoms('FeFeO',scaled_positions=[[0,0,0],[.3,.3,.3],[.6,.6,.6]],cell=[5]*3,pbc=True)
    dialog.set_structure(atoms);editor = dialog.editor
    create(editor,'first',[0]);snapshot = editor.rows()
    editor.select_indices([0]);editor.name.setText('duplicate')
    with pytest.raises(ValueError,match='Duplicate'):editor.create_group()
    assert editor.rows() == snapshot
    editor.select_indices([1]);editor.name.setText('first')
    with pytest.raises(ValueError,match='unique'):editor.create_group()
    editor.name.setText('mixed');editor.select_indices([1,2])
    with pytest.raises(ValueError,match='one element'):editor.create_group()
    for bad in ('0 0 0','nan 0 1','1 2','inf 2 3','wrong'):
        editor.direction.setText(bad)
        with pytest.raises(ValueError,match='finite'):editor.update_direction()
    assert editor.rows() == snapshot
    with pytest.raises(ValueError,match='reference'):editor.set_mdff_reference('first','')
    assert editor.rows() == snapshot
    # Empty/deleted configurations are legal ordinary viewing, without an empty Stage 1 model.
    editor.delete_group();assert editor.apply() is None
    assert not editor.rows() and dialog.view.scene.site_groups is None


def test_noncollinear_selection_and_supercell_replicas(dialog,app):
    atoms = Atoms('Fe3',scaled_positions=[[.1,.1,.1],[.4,.4,.4],[.7,.7,.7]],
                  cell=[[5,0,0],[1,6,0],[.5,.7,7]],pbc=True)
    dialog.set_structure(atoms);editor = dialog.editor
    create(editor,'x',[0],'1 0 0');create(editor,'y',[1],'0 1 0');create(editor,'diag',[2],'1 -2 3')
    dialog.set_repetitions((2,2,2));dialog.color_mode.setCurrentIndex(1)
    dialog.magnetic_arrows.setChecked(True)
    dialog.show();app.processEvents()
    # The real mouse release path maps a picked replica to its original index.
    xy,_,_ = dialog.view.projected_atoms()
    candidates = [i for i in range(3,len(xy)) if dialog.view.pick_atom(xy[i]) == i]
    assert candidates
    i = candidates[0]; original_index = int(dialog.view.scene.indices[i])
    QtTest.QTest.mouseClick(dialog.view,QtCore.Qt.MouseButton.LeftButton,
                          QtCore.Qt.KeyboardModifier.NoModifier,QtCore.QPoint(*map(int,xy[i])))
    assert editor.selected_indices() == (original_index,)
    assert dialog.view.selected_indices == {original_index}
    assert np.count_nonzero(dialog.view.scene.indices == original_index) == 8
    other = (original_index+1)%3
    editor.pick_atom(other,True)
    assert set(editor.selected_indices()) == {original_index,other}
    editor.pick_atom(original_index,True);assert editor.selected_indices() == (other,)
    # Updating a direction refreshes every replica while preserving the camera.
    editor.groups.setCurrentItem(editor.groups.topLevelItem(0))
    before = dialog.view.orientation.copy()
    editor.direction.setText('-1 2 0');editor.update_direction()
    expected = np.array([-1,2,0])/np.sqrt(5)
    np.testing.assert_allclose(dialog.view.scene.directions[dialog.view.scene.indices==0],np.tile(expected,(8,1)))
    np.testing.assert_array_equal(dialog.view.orientation,before)


def test_configured_model_cancel_and_incompatible_structure(dialog,tmp_path):
    atoms = bulk('Ni','fcc',a=3.52,cubic=True)
    reference = declared_reference(tmp_path,'Ni','Ni')
    original = MultiSiteIonization(atoms,[IonizationSiteGroup('Ni','Ni',(0,1,2,3),reference,(0,0,1),4)])
    dialog.set_structure(atoms);dialog.set_site_groups(original);editor = dialog.editor
    editor.groups.setCurrentItem(editor.groups.topLevelItem(0))
    editor.name.setText('Ni-renamed');editor.rename_group()
    dialog.close()
    assert dialog.accepted_site_groups is original and editor.rows()[0][0] == 'Ni'
    editor.groups.setCurrentItem(editor.groups.topLevelItem(0))
    editor.name.setText('Ni-applied');editor.rename_group();dialog.apply_groups()
    assert dialog.accepted_site_groups.groups[0].group_id == 'Ni-applied'
    dialog.set_structure(bulk('Fe','bcc',a=2.88,cubic=True))
    assert not editor.rows() and dialog.accepted_site_groups is None
    create(editor,'Fe',[0]);editor.apply()
    dialog.set_structure(bulk('Cr','bcc',a=2.88,cubic=True))
    assert not editor.rows() and 'drafts cleared' in dialog.notice.text()


def test_ordinary_and_partial_occupancy_structure_stays_viewable(dialog):
    atoms = Atoms('Fe',positions=[[0,0,0]],cell=[4]*3,pbc=True)
    atoms.info['occupancy'] = {'0':{'Fe':.5}}
    dialog.set_structure(atoms)
    assert dialog.view.scene is not None and not dialog.editor.rows()
    dialog.editor.select_indices([0]);dialog.editor.name.setText('partial')
    with pytest.raises(ValueError,match='occupancies'):dialog.editor.create_group()
    assert dialog.view.scene is not None and not dialog.editor.rows()


@pytest.mark.skipif(sys.platform!='win32' or os.environ.get('QT_QPA_PLATFORM')!='windows',reason='Explicit native Windows check')
def test_native_windows_site_editor(app):
    assert app.platformName() == 'windows'
    viewer = CrystalStructureDialog()
    try:
        viewer.set_structure(bulk('Cr','bcc',a=2.88,cubic=True))
        viewer.show();viewer.tabs.setCurrentWidget(viewer.editor);app.processEvents()
        assert QtTest.QTest.qWaitForWindowExposed(viewer.windowHandle(),3000)
        editor = viewer.editor
        editor.mode.setCurrentIndex(1)
        for index,name,direction in [(0,'Cr-up','0 0 1'),(1,'Cr-down','0 0 -1')]:
            editor.select_indices([index]);editor.name.setText(name);editor.direction.setText(direction)
            QtTest.QTest.mouseClick(editor.buttons['Create from selection'],QtCore.Qt.MouseButton.LeftButton)
        assert len(editor.rows()) == 2
        QtTest.QTest.mouseClick(viewer.dialog_buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Apply),QtCore.Qt.MouseButton.LeftButton)
        assert not editor.dirty and viewer.accepted_site_groups is None
        viewer.color_mode.setCurrentIndex(1);viewer.magnetic_arrows.setChecked(True)
        editor.name.setText('temporary');QtTest.QTest.mouseClick(editor.buttons['Rename'],QtCore.Qt.MouseButton.LeftButton)
        QtTest.QTest.mouseClick(viewer.dialog_buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Cancel),QtCore.Qt.MouseButton.LeftButton)
        assert not viewer.isVisible() and editor.rows()[1][0] == 'Cr-down'
        viewer.show();app.processEvents()
        if os.environ.get('EMCD_VIEWER_CHECK_IMAGE'):viewer.grab().save(os.environ['EMCD_VIEWER_CHECK_IMAGE'])
    finally:viewer.close();app.processEvents()


def test_global_local_lock_legacy_settings_reopen_and_no_fallback(tmp_path,app,monkeypatch):
    from emcd_sim.gui.app import MainWindow
    from emcd_sim.gui.geometry import Structure
    window = MainWindow(workspace=tmp_path/'workspace')
    errors = [];monkeypatch.setattr(window,'error',errors.append)
    monkeypatch.setattr(window,'store_ui_preferences',lambda:None)
    try:
        assert window.magnetization_mode == 'global' and window.axis.isEnabled()
        window.numerical_mode.setCurrentIndex(1)
        window.correction.setChecked(False)
        # Preserve exactly the legacy interpretation/settings rather than deriving local M.
        global_text = window.axis.text()
        with pytest.raises(ValueError,match='Atomic draft ready') as legacy_state:
            window.forward_settings(prepare=False)
        window.show_structure_viewer();viewer = window.structure_viewer;editor = viewer.editor
        assert editor.magnetization_mode == 'global'
        editor.mode.setCurrentIndex(1)
        assert not window.axis.isEnabled() and window.axis.text() == global_text
        assert not window.atomic_editor.direction.isEnabled() and not window.atomic_editor.apply_direction.isEnabled()
        assert 'Global magnetization is locked while site-specific magnetization is enabled.' in window.magnetization_mode_note.text()
        assert not window.emcd_button.isEnabled()
        from emcd_sim.gui.multisite_run import applied_inputs
        local_cfg = window.forward_settings(prepare=False)
        assert local_cfg.model == 'multisite'
        with pytest.raises(ValueError,match='Apply'):applied_inputs(window,local_cfg)
        window.start_emcd()
        assert errors and 'Apply' in errors[-1] and window.worker is None
        create(editor,'Ni-up',[0],'1 0 0');create(editor,'Ni-down',[1],'-1 0 0')
        np.testing.assert_allclose(viewer.view.scene.directions[:2],[[1,0,0],[-1,0,0]])
        viewer.apply_groups()
        rows = editor.rows()
        viewer.close();window.show_structure_viewer();app.processEvents()
        assert editor.magnetization_mode == 'local' and not window.axis.isEnabled()
        assert editor.rows() == rows
        editor.mode.setCurrentIndex(0)
        assert window.axis.isEnabled() and window.axis.text() == global_text
        assert window.atomic_editor.direction.isEnabled() and window.atomic_editor.apply_direction.isEnabled()
        assert not editor.direction.isEnabled() and not viewer.view.show_magnetization
        assert editor.rows() == rows
        with pytest.raises(ValueError) as restored_state:window.forward_settings(prepare=False)
        assert str(restored_state.value) == str(legacy_state.value)
        editor.mode.setCurrentIndex(1)
        editor.groups.setCurrentItem(editor.groups.topLevelItem(1))
        editor.direction.setText('0 1 2');editor.update_direction()
        before = [r[3] for r in editor.rows()]
        editor.flip_all()
        np.testing.assert_allclose([r[3] for r in editor.rows()],-np.asarray(before))
        assert window.axis.text() == global_text
        # Cancel restores all directions and the previously applied Local mode.
        viewer.reject();assert editor.rows() == rows and window.magnetization_mode == 'local'
        window.structure = Structure(bulk('Cr','bcc',a=2.88,cubic=True));window.refresh()
        assert not editor.rows() and not window.axis.isEnabled()
        assert 'No local groups configured' in editor.status.text()
        # A cancelled mode switch must restore the lock consistently too.
        window.show_structure_viewer();editor.mode.setCurrentIndex(0)
        assert window.axis.isEnabled()
        viewer.reject();assert window.magnetization_mode == 'local' and not window.axis.isEnabled()
    finally:
        for child in window.findChildren(QtWidgets.QDialog):child.close()
        window.close();window.deleteLater();app.processEvents()


def test_global_flip_preserves_explicit_references_and_full_frames(dialog,tmp_path):
    atoms = bulk('Cr','bcc',a=2.88,cubic=True)
    frames = [np.eye(3),np.array([[0,-1,0],[1,0,0],[0,0,1]])]
    references = [declared_reference(tmp_path,'up','Cr',frame=frames[0]),
                  declared_reference(tmp_path,'down','Cr',(0,0,-1),frames[1])]
    groups = MultiSiteIonization(atoms,[IonizationSiteGroup(str(i),'Cr',(i,),references[i],(0,0,1 if i==0 else -1),1) for i in range(2)])
    dialog.set_structure(atoms);dialog.set_site_groups(groups)
    editor = dialog.editor
    with pytest.raises(ValueError,match='Local'):editor.flip_all()
    editor.mode.setCurrentIndex(1);editor.flip_all()
    model = editor.apply()
    # Configured providers keep their declared axes; global reversal selects
    # every physical pair's other state, rather than rewriting source frames.
    assert editor.reverse_magnetization
    np.testing.assert_allclose([g.magnetization for g in model.groups],[[0,0,1],[0,0,-1]])
    for group,reference,frame in zip(model.groups,references,frames):
        assert group.mdff_reference is reference
        np.testing.assert_array_equal(source_for(group.mdff_reference).metadata['frame_to_crystal'],frame)
