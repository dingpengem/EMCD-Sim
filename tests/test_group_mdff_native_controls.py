"""Native MDFF editing paths; no user-authored tensor/configuration JSON."""
import numpy as np
import pytest
from PySide6 import QtCore

from emcd_sim.mdff_providers import load_provider
from test_group_mdff import app,viewer,create


def matrix(editor, scale=1.):
    value = np.eye(3,dtype=complex)*scale
    value[0,1] = .1j*scale;value[1,0] = -.1j*scale
    with QtCore.QSignalBlocker(editor.cells):
        for i in range(3):
            for j in range(3):editor.cells.item(i,j).setText(str(value[i,j]).strip('()').replace('j','i'))
    editor.edited();return value


def native_xmcd(dialog, path, shift=0.):
    dialog.model.setCurrentIndex(0)
    energy = np.linspace(704+shift,730+shift,9)
    right = 1.1+np.exp(-((energy-710-shift)/2)**2);left = .9+np.exp(-((energy-710-shift)/2)**2)
    np.savetxt(path,np.column_stack((energy,right,left,right-left,right+left)))
    dialog.source_path.setText(str(path));dialog.spin['xl3'].setValue(710+shift);dialog.spin['xl2'].setValue(723+shift)
    dialog.xmcd_provenance.setText('Explicit synthetic RP/LP fixture');dialog.xmcd_validity.setText('Synthetic axisymmetric preview only')
    dialog.xmcd_scale.setText('3');dialog.eta.setValue(1);dialog.beta.setValue(0)
    dialog.xmcd_status.setCurrentText('synthetic');dialog.validate_xmcd_source()
    dialog.declaration.setChecked(True);dialog.xmcd_preview.update_preview()


def test_default_constant_nine_cells_and_independent_fe_groups(viewer):
    editor = viewer.editor;create(editor,'Fe(A)',[0]);create(editor,'Fe(B)',[1])
    dialogs = []
    for row,scale in enumerate((1.,4.)):
        editor.groups.setCurrentItem(editor.groups.topLevelItem(row));dialog = editor.configure_mdff()
        dialog.model.setCurrentIndex(2)
        assert dialog.manual_mode.currentIndex() == 0
        assert not dialog.import_path.isVisibleTo(dialog.pages)
        assert dialog.manual_tensor.cells.rowCount() == dialog.manual_tensor.cells.columnCount() == 3
        expected = matrix(dialog.manual_tensor,scale)
        dialog.declaration.setChecked(True)
        assert dialog.apply_configuration() is not None,dialog.status.text()
        source = load_provider(editor.rows()[row][4])
        np.testing.assert_allclose(source.plus.tensor_angstrom2_per_ev,np.broadcast_to(expected,source.plus.tensor_angstrom2_per_ev.shape))
        np.testing.assert_allclose(source.minus.tensor_angstrom2_per_ev,source.plus.tensor_angstrom2_per_ev.conj())
        dialogs.append(dialog)
    assert editor.validated_site_groups is not None
    editor.groups.setCurrentItem(editor.groups.topLevelItem(0));assert editor.configure_mdff() is dialogs[0]
    np.testing.assert_allclose(dialogs[0].manual_tensor.matrix(),matrix_value(1.))
    np.testing.assert_allclose(dialogs[1].manual_tensor.matrix(),matrix_value(4.))
    # Invalid visible coefficients cannot bind an older valid tensor.
    reference = editor.rows()[0][4]
    dialogs[0].manual_tensor.cells.item(0,1).setText('0.9i');dialogs[0].declaration.setChecked(True)
    assert dialogs[0].apply_configuration() is None and 'Hermitian' in dialogs[0].status.text()
    assert editor.rows()[0][4] is reference
    dialogs[0].reject();np.testing.assert_allclose(dialogs[0].manual_tensor.matrix(),matrix_value(1.))


def matrix_value(scale):
    value = np.eye(3,dtype=complex)*scale;value[0,1] = .1j*scale;value[1,0] = -.1j*scale
    return value


def test_l23_existing_simple_full_controls_and_actual_preview(viewer):
    editor = viewer.editor;create(editor,'Fe',[0]);dialog = editor.configure_mdff()
    dialog.model.setCurrentIndex(2);dialog.manual_mode.setCurrentIndex(1)
    spectral = dialog.manual_spectral
    assert spectral.view.currentIndex() == 0 and spectral.frame_mode.currentIndex() == 1
    spectral.samples.setValue(31)
    for edge,energy,width,amplitude in [('L3',710.,1.5,2.),('L2',723.,2.5,3.)]:
        spectral.fields[edge,'energy'].setText(str(energy));spectral.fields[edge,'width'].setText(str(width))
        spectral.fields[edge,'A'].setText(str(amplitude));spectral.fields[edge,'r'].setText('1.4')
    dialog.preview_tensor()
    assert not spectral.is_stale and spectral.numeric_curves
    source = spectral.snapshot['source']
    assert source.metadata['manual_l23_model']['edges']['L3']['fwhm_ev'] == 1.5
    assert source.metadata['manual_l23_model']['edges']['L2']['fwhm_ev'] == 2.5
    spectral.view.setCurrentIndex(1)
    general = np.array([[2,.2,0],[.2,1,.1],[0,.1,3]],complex)
    spectral.set_matrix('L3',general)
    spectral.view.setCurrentIndex(0)
    assert spectral.view.currentIndex() == 1  # No projection into the simple ansatz.
    np.testing.assert_array_equal(spectral.matrices['L3'].matrix(),general)
    dialog.preview_tensor();assert not spectral.is_stale
    dialog.declaration.setChecked(True);assert dialog.apply_configuration() is not None
    model = load_provider(editor.rows()[0][4]).metadata['manual_l23_model']
    np.testing.assert_allclose(model['edges']['L3']['real'],general.real)
    editor.apply();dialog.manual_mode.setCurrentIndex(0);editor.cancel()
    assert dialog.manual_mode.currentIndex() == 1 and spectral.view.currentIndex() == 1
    # Reopening an applied source restores the established numerical editor.
    from emcd_sim.gui.group_mdff import GroupMDFFDialog
    restored = GroupMDFFDialog(editor.rows()[0],editor.mdff_workspace,editor)
    try:
        assert restored.manual_mode.currentIndex() == 1
        np.testing.assert_array_equal(restored.manual_spectral.matrices['L3'].matrix(),general)
    finally:restored.close();restored.deleteLater()


def test_fe_manual_ni_xmcd_preview_and_independent_drafts(viewer,tmp_path):
    editor = viewer.editor;create(editor,'Fe',[0]);create(editor,'Ni',[2])
    editor.groups.setCurrentItem(editor.groups.topLevelItem(0));fe = editor.configure_mdff()
    fe.model.setCurrentIndex(2);matrix(fe.manual_tensor)
    fe.declaration.setChecked(True);assert fe.apply_configuration() is not None
    fe.preview_tensor();assert fe.preview_states
    editor.groups.setCurrentItem(editor.groups.topLevelItem(1));ni = editor.configure_mdff()
    native_xmcd(ni,tmp_path/'Ni.xmcd',140.)
    assert not ni.xmcd_preview.is_stale,ni.xmcd_preview.status.text()
    assert ni.apply_configuration() is not None,ni.status.text()
    assert [r[4].model for r in editor.rows()] == ['imported','xmcd']
    assert editor.energy_windows['Ni'].bounds_ev == (844.,870.)
    preview = ni.xmcd_preview.snapshot['states']['+M']
    provider = load_provider(editor.rows()[1][4]);actual = provider.tensors(provider.energy_ev,np.eye(3),(0,0,1))[0].tensor_angstrom2_per_ev
    np.testing.assert_allclose(preview,actual)
    assert ni.axis.text() == '0.0 0.0 1.0'
    editor.groups.setCurrentItem(editor.groups.topLevelItem(0));editor.configure_mdff()
    np.testing.assert_array_equal(fe.manual_tensor.matrix(),matrix_value(1.))
    assert ni.source_path.text().endswith('Ni.xmcd')


def test_native_frame_and_sampling_validation_without_json(viewer):
    editor = viewer.editor;create(editor,'noncollinear',[0],'1 0 0');dialog = editor.configure_mdff()
    dialog.model.setCurrentIndex(2);dialog.manual_mode.setCurrentIndex(1)
    dialog.declaration.setChecked(True);assert dialog.apply_configuration() is None
    assert 'axis' in dialog.status.text()
    spectral = dialog.manual_spectral
    frame = [[0,0,1],[0,1,0],[-1,0,0]]
    for i in range(3):
        for j in range(3):spectral.frame_table.item(i,j).setText(str(frame[i][j]))
    dialog.declaration.setChecked(True);assert dialog.apply_configuration() is not None,dialog.status.text()
    reference = editor.rows()[0][4]
    np.testing.assert_allclose(load_provider(reference).metadata['frame_to_crystal'],frame)
    spectral.reset_defaults();assert spectral.frame_mode.currentIndex() == 1
    assert editor.rows()[0][3] == (1.,0.,0.)  # Group M remains independent of a frame reset.
    dialog.reject()
    np.testing.assert_allclose(spectral.frame_value(),frame)
    dialog.energy_window.source_bounds.setChecked(False)
    dialog.energy_window.low.setValue(710);dialog.energy_window.high.setValue(720)
    dialog.energy_window.kind.setCurrentText('Selected energies')
    dialog.energy_window.add_energy(715);dialog.energy_window.add_energy(712)
    dialog.declaration.setChecked(True);assert dialog.apply_configuration() is None
    assert 'ascending' in dialog.status.text() and editor.rows()[0][4] is reference


def test_expert_export_preserves_the_applied_original_source(viewer,tmp_path):
    editor = viewer.editor;create(editor,'Fe',[0]);dialog = editor.configure_mdff()
    dialog.model.setCurrentIndex(2);matrix(dialog.manual_tensor)
    dialog.declaration.setChecked(True);assert dialog.apply_configuration() is not None
    destination = tmp_path/'exported-tensor.json'
    assert dialog.export_applied_source(destination) == destination
    from pathlib import Path
    assert destination.read_bytes() == Path(dialog.reference.source).read_bytes()
    assert dialog.export_applied_source(destination) is None  # Existing research files remain intact.
