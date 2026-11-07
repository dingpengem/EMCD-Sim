"""Synthetic MDFF configuration checks only; no elastic propagation."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import json
import sys

import numpy as np
import pytest
from ase import Atoms
from PySide6 import QtCore,QtWidgets,QtTest

from emcd_sim.gui.group_mdff import GroupMDFFDialog,validate_group_reference
from emcd_sim.gui.generalized_forward import settings_for_source
from emcd_sim.gui.structure_viewer import CrystalStructureDialog
from emcd_sim.mdff_providers import load_provider
from emcd_sim.multisite_spectrum import ModeledEdgeWindow,prepare_multisite_spectrum
from single_element_helpers import document


@pytest.fixture(scope='module')
def app():return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def source(tmp_path,name='Fe',element='Fe',axis=(0,0,1),scale=1.,shift=0.,defect=None):
    d = document(element);d['magnetization_crystal'] = list(axis)
    d['energy_ev'] = (np.asarray(d['energy_ev'])+shift).tolist()
    d['selected_ev'] = {key:value+shift for key,value in d['selected_ev'].items()}
    for key in ('T_plus','T_minus','T_even'):
        for part in ('real','imag'):d[key][part] = (np.asarray(d[key][part])*scale).tolist()
    if defect == 'missing':del d['T_minus']
    if defect == 'frame':d.update(basis='declared_local',frame_to_crystal=[[1,0,0],[0,1,0],[0,0,2]])
    if defect == 'psd':
        for key in ('T_plus','T_minus','T_even'):d[key]['real'][0][0][0] = -1
    if defect == 'hermitian':d['T_plus']['real'][0][0][1] = 2
    path = tmp_path/(name+'.json');path.write_text(json.dumps(d),encoding='utf-8')
    return path


def create(editor,name,indices,direction='0 0 1'):
    editor.mode.setCurrentIndex(1);editor.select_indices(indices)
    editor.name.setText(name);editor.direction.setText(direction);editor.create_group()


def imported(dialog,path):
    dialog.model.setCurrentIndex(2);dialog.manual_mode.setCurrentIndex(3)
    dialog.import_path.setText(str(path));dialog.declaration.setChecked(True)


@pytest.fixture
def viewer(tmp_path,app):
    dialog = CrystalStructureDialog();dialog.editor.mdff_workspace = tmp_path/'managed'
    atoms = Atoms('FeFeNi',scaled_positions=[[.1,.1,.1],[.4,.4,.4],[.7,.7,.7]],cell=[5]*3,pbc=True)
    dialog.set_structure(atoms)
    yield dialog
    dialog.close();app.processEvents()


def test_same_element_independent_sources_switching_rename_cancel_and_delete(viewer,tmp_path):
    editor = viewer.editor
    create(editor,'Fe(A)',[0]);create(editor,'Fe(B)',[1],'0 0 -1')
    editor.groups.setCurrentItem(editor.groups.topLevelItem(0));a = editor.configure_mdff()
    imported(a,source(tmp_path,'A'));assert a.apply_configuration() is not None
    editor.groups.setCurrentItem(editor.groups.topLevelItem(1));b = editor.configure_mdff()
    assert b.source_path.text() == '' and b.import_path.text() == ''
    imported(b,source(tmp_path,'B',axis=(0,0,-1),scale=7));assert b.apply_configuration() is not None
    assert editor.mdff_status(editor.rows()[0]) == 'Configured and valid'
    assert editor.mdff_status(editor.rows()[1]) == 'Configured and valid'
    model = editor.validated_site_groups
    assert [g.indices for g in model.groups] == [(0,),(1,)]
    assert [g.multiplicity for g in model.groups] == [1,1]
    assert model.groups[0].mdff_reference.source != model.groups[1].mdff_reference.source
    editor.apply()
    # Each dialog retains incomplete changes when switching, without applying them.
    a.open_draft(editor.rows()[0]);a.import_path.setText('unfinished source');a.close()
    editor.groups.setCurrentItem(editor.groups.topLevelItem(1));assert editor.configure_mdff() is b
    editor.groups.setCurrentItem(editor.groups.topLevelItem(0));assert editor.configure_mdff() is a
    assert a.import_path.text() == 'unfinished source'
    editor.name.setText('Fe(A)-renamed');editor.rename_group()
    assert editor.mdff_dialogs['Fe(A)-renamed'] is a and a.row[0] == 'Fe(A)-renamed'
    editor.cancel()
    assert editor.mdff_dialogs['Fe(A)'] is a and a.import_path.text() != 'unfinished source'
    assert editor.rows()[0][0] == 'Fe(A)'
    editor.groups.setCurrentItem(editor.groups.topLevelItem(1));editor.delete_group()
    editor.apply();assert 'Fe(B)' not in editor.mdff_dialogs and 'Fe(B)' not in editor.energy_windows


def test_disjoint_fe_ni_windows_and_source_amplitudes(viewer,tmp_path):
    editor = viewer.editor;create(editor,'Fe',[0]);create(editor,'Ni',[2])
    for number,(element,shift,scale) in enumerate([('Fe',0.,1.),('Ni',140.,23.)]):
        editor.groups.setCurrentItem(editor.groups.topLevelItem(number));dialog = editor.configure_mdff()
        imported(dialog,source(tmp_path,element,element=element,shift=shift,scale=scale))
        assert dialog.apply_configuration() is not None
    plan = prepare_multisite_spectrum(editor.validated_site_groups,energy_windows=editor.energy_windows)
    assert len(plan['energy_ev']) > 0
    fe,ni = [load_provider(row[4]) for row in editor.rows()]
    np.testing.assert_allclose(ni.plus.tensor_angstrom2_per_ev,23*fe.plus.tensor_angstrom2_per_ev)
    assert editor.energy_windows['Fe'].bounds_ev == (704.,730.)
    assert editor.energy_windows['Ni'].bounds_ev == (844.,870.)


@pytest.mark.parametrize('defect',['missing','frame','psd','hermitian'])
def test_invalid_sources_do_not_bind(viewer,tmp_path,defect):
    editor = viewer.editor;create(editor,'Fe',[0]);dialog = editor.configure_mdff()
    imported(dialog,source(tmp_path,defect=defect))
    assert dialog.apply_configuration() is None
    assert editor.rows()[0][4] is None and 'Invalid' in dialog.status.text()


def test_species_axis_coverage_identity_and_explicit_revalidation(viewer,tmp_path):
    editor = viewer.editor;create(editor,'Fe',[0]);dialog = editor.configure_mdff()
    for path in [source(tmp_path,'Ni',element='Ni'),source(tmp_path,'wrong-axis',axis=(1,0,0))]:
        imported(dialog,path);assert dialog.apply_configuration() is None
    path = source(tmp_path);imported(dialog,path)
    dialog.energy_window.source_bounds.setChecked(False)
    dialog.energy_window.low.setValue(700);dialog.energy_window.high.setValue(730)
    dialog.declaration.setChecked(True);assert dialog.apply_configuration() is None
    assert 'coverage' in dialog.status.text()
    dialog.energy_window.low.setValue(707);dialog.energy_window.high.setValue(726)
    dialog.energy_window.kind.setCurrentText('Selected energies')
    dialog.energy_window.add_energy(710);dialog.energy_window.add_energy(723)
    dialog.declaration.setChecked(True)
    assert dialog.apply_configuration() is not None
    editor.apply();original = editor.rows()[0][4]
    path.write_text(path.read_text(encoding='utf-8')+'\n',encoding='utf-8')
    editor.recheck_mdff_sources()
    assert editor.mdff_status(editor.rows()[0]) == 'Invalid / stale'
    with pytest.raises(ValueError,match='checksum'):editor.apply()
    assert editor.accepted_site_groups.groups[0].mdff_reference is original
    dialog.declaration.setChecked(True);assert dialog.apply_configuration() is None
    assert not dialog.declaration.isChecked() and 'identity changed' in dialog.status.text()
    dialog.declaration.setChecked(True);assert dialog.apply_configuration() is not None
    assert editor.rows()[0][4].source_sha256 != original.source_sha256
    # Editing local M invalidates the binding; no frame or physical state is manufactured.
    editor.direction.setText('1 0 0');editor.update_direction()
    assert not dialog.declaration.isChecked()
    assert editor.mdff_status(editor.rows()[0]) == 'Needs validation'
    with pytest.raises(ValueError,match='axis'):editor.validated_site_groups


def test_explicit_manual_pair_has_real_odd_component_and_full_frame(viewer):
    editor = viewer.editor;create(editor,'Fe',[0],'1 0 0');dialog = editor.configure_mdff()
    dialog.model.setCurrentIndex(2);dialog.manual_mode.setCurrentIndex(2)
    dialog.constant_energy.low.setValue(704);dialog.constant_energy.high.setValue(730)
    dialog.manual_edges.set_rows([('L3',710),('L2',723)])
    frame = [[0,0,1],[0,1,0],[-1,0,0]]
    for i in range(3):
        for j in range(3):dialog.manual_frame.item(i,j).setText(str(frame[i][j]))
    dialog.manual_source.setText('Explicit synthetic pair')
    dialog.manual_validity.setText('Synthetic software test only')
    for tensor,scale in zip(dialog.pair,(2.,1.)):
        with QtCore.QSignalBlocker(tensor.cells):
            for i in range(3):
                for j in range(3):tensor.cells.item(i,j).setText(str(scale if i==j else 0.))
        tensor.edited()
    dialog.declaration.setChecked(True);assert dialog.apply_configuration() is not None
    provider = load_provider(editor.rows()[0][4])
    np.testing.assert_allclose(provider.plus.tensor_angstrom2_per_ev,2*provider.minus.tensor_angstrom2_per_ev)
    np.testing.assert_array_equal(provider.metadata['frame_to_crystal'],frame)
    assert provider.provenance()['normalization'] == 'per_atom_relative'


def test_existing_atomic_and_xmcd_editors_bind_independently(viewer,tmp_path):
    editor = viewer.editor;create(editor,'atomic',[0],'0 0 -1');create(editor,'xmcd',[1])
    editor.groups.setCurrentItem(editor.groups.topLevelItem(0));atomic = editor.configure_mdff()
    atomic.model.setCurrentIndex(1)
    for key,value in dict(l3='710',l2='723',emin='704',emax='730',samples='9',source='Explicit synthetic atomic parameters').items():
        atomic.atomic.fields[key].setText(value)
    atomic.atomic.frame_mode.setCurrentIndex(2)
    for i in range(3):
        for j in range(3):atomic.atomic.frame.cellWidget(i,j).setText(str([1,-1,-1][i] if i==j else 0))
    atomic.declaration.setChecked(True)
    assert atomic.apply_configuration() is not None,atomic.status.text()
    original_atomic = editor.rows()[0][4]
    atomic.atomic_mode.setCurrentIndex(0);atomic.atomic_path.setText(original_atomic.source)
    atomic.load_atomic()  # Editing is explicit, never silently ignored in favor of a file.
    assert atomic.atomic_mode.currentIndex() == 1
    atomic.atomic.fields['radial'].setText('2');atomic.declaration.setChecked(True)
    assert atomic.apply_configuration() is not None
    assert editor.rows()[0][4].source_sha256 != original_atomic.source_sha256
    editor.groups.setCurrentItem(editor.groups.topLevelItem(1));xmcd = editor.configure_mdff()
    xmcd.model.setCurrentIndex(0)
    energy = np.linspace(704,730,9);right=np.ones(9)*1.1;left=np.ones(9)*.9
    path = tmp_path/'Fe.xmcd';np.savetxt(path,np.column_stack((energy,right,left,right-left,right+left)))
    xmcd.source_path.setText(str(path));xmcd.spin['xl3'].setValue(710);xmcd.spin['xl2'].setValue(723)
    xmcd.xmcd_provenance.setText('Explicit synthetic RP/LP source');xmcd.xmcd_validity.setText('Axisymmetric proxy test only')
    xmcd.xmcd_scale.setText('3');xmcd.eta.setValue(1);xmcd.beta.setValue(0)
    xmcd.xmcd_status.setCurrentText('synthetic');xmcd.declaration.setChecked(True)
    assert xmcd.apply_configuration() is not None,xmcd.status.text()
    assert [r[4].model for r in editor.rows()] == ['atomic','xmcd']
    assert editor.validated_site_groups is not None
    assert atomic.atomic.fields['source'].text() != xmcd.xmcd_provenance.text()


def test_mdff_cancel_and_parent_cancel_restore_configuration(viewer,tmp_path):
    editor = viewer.editor;create(editor,'Fe',[0]);dialog = editor.configure_mdff()
    path = source(tmp_path);imported(dialog,path)
    assert dialog.apply_configuration() is not None
    original = editor.rows()[0][4];editor.apply()
    dialog.open_draft(editor.rows()[0]);dialog.import_path.setText('unfinished');dialog.reject()
    assert dialog.import_path.text() == str(path) and editor.rows()[0][4] is original
    dialog.open_draft(editor.rows()[0]);imported(dialog,source(tmp_path,'new',scale=2))
    assert dialog.apply_configuration() is not None and editor.rows()[0][4] is not original
    editor.cancel()
    assert editor.rows()[0][4] is original and dialog.import_path.text() == str(path)


@pytest.mark.skipif(sys.platform!='win32' or os.environ.get('QT_QPA_PLATFORM')!='windows',reason='Explicit native Windows check')
def test_native_group_mdff(tmp_path,app,monkeypatch):
    from emcd_sim.gui.app import MainWindow
    from emcd_sim.gui.geometry import Structure
    assert app.platformName() == 'windows'
    window = MainWindow(workspace=tmp_path/'workspace')
    monkeypatch.setattr(window,'store_ui_preferences',lambda:None)
    try:
        window.axis.setText('0 1 0');original_axis = window.axis.text()
        window.structure = Structure(Atoms('Fe2',scaled_positions=[[.1,.1,.1],[.5,.5,.5]],cell=[5]*3,pbc=True))
        window.show_structure_viewer();viewer = window.structure_viewer
        viewer.tabs.setCurrentWidget(viewer.editor);app.processEvents()
        editor = viewer.editor;create(editor,'Fe(A)',[0]);dialog = editor.configure_mdff()
        from test_group_mdff_native_controls import matrix,native_xmcd
        dialog.model.setCurrentIndex(2);matrix(dialog.manual_tensor)
        assert dialog.manual_mode.currentIndex() == 0
        dialog.declaration.setChecked(True);app.processEvents()
        assert not window.axis.isEnabled() and window.axis.text() == original_axis
        assert QtTest.QTest.qWaitForWindowExposed(dialog.windowHandle(),3000)
        QtTest.QTest.mouseClick(dialog.buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Apply),QtCore.Qt.MouseButton.LeftButton)
        assert editor.mdff_status(editor.rows()[0]) == 'Configured and valid'
        assert dialog.reference is editor.rows()[0][4]
        if os.environ.get('EMCD_VIEWER_CHECK_IMAGE'):dialog.grab().save(os.environ['EMCD_VIEWER_CHECK_IMAGE'])
        native_xmcd(dialog,tmp_path/'native-Fe.xmcd');app.processEvents()
        assert not dialog.xmcd_preview.is_stale,dialog.xmcd_preview.status.text()
        QtTest.QTest.mouseClick(dialog.buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Apply),QtCore.Qt.MouseButton.LeftButton)
        assert editor.rows()[0][4].model == 'xmcd'
        assert not window.axis.isEnabled() and window.axis.text() == original_axis
        if os.environ.get('EMCD_VIEWER_CHECK_IMAGE'):
            from pathlib import Path
            image_path = Path(os.environ['EMCD_VIEWER_CHECK_IMAGE'])
            dialog.grab().save(str(image_path.with_stem(image_path.stem+'_xmcd')))
        dialog.close();editor.apply();viewer.close();window.show_structure_viewer();app.processEvents()
        assert editor.validated_site_groups is not None
        assert not window.axis.isEnabled() and window.axis.text() == original_axis
    finally:
        for child in window.findChildren(QtWidgets.QDialog):child.close()
        window.close();window.deleteLater();app.processEvents()
