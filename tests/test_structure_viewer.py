"""General crystal visualization is independent of EMCD material eligibility."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from copy import deepcopy
from dataclasses import asdict
import sys

import numpy as np
import pytest
from ase import Atoms
from ase.build import bulk
from ase.cell import Cell
from ase.io import write
from ase.data.colors import jmol_colors
from PySide6 import QtCore, QtGui, QtWidgets, QtTest

from emcd_sim.gui.geometry import Structure
from emcd_sim.gui.structure_scene import build_scene, cell_segments, MAX_ATOMS
from emcd_sim.gui.structure_viewer import CrystalStructureDialog


@pytest.fixture(scope='module')
def app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def examples():
    yield bulk('Ni','fcc',a=3.524,cubic=True)
    yield bulk('Fe','bcc',a=2.88,cubic=True)
    yield Atoms('Fe3O4',scaled_positions=[(i/7,(i*.23)%1,(i*.37)%1) for i in range(7)],cell=[8]*3,pbc=True)
    for parameters in ([4,4,6,90,90,90],[4,5,6,90,90,90],[4,4,6,90,90,120],
                       [4,5,6,90,105,90],[4,5,6,78,101,112]):
        yield Atoms('FeNiO',scaled_positions=[[.1,.2,.3],[.4,.5,.6],[.7,.8,.9]],
                    cell=Cell.fromcellpar(parameters),pbc=True)


@pytest.mark.parametrize('atoms',list(examples()))
def test_general_cells_and_stable_replica_identity(atoms):
    original=atoms.copy(); original_info=deepcopy(atoms.info)
    scene=build_scene(atoms,(2,2,2))
    assert len(scene.positions)==len(atoms)*8
    np.testing.assert_array_equal(scene.indices,np.tile(np.arange(len(atoms)),8))
    np.testing.assert_allclose(scene.positions,atoms.positions[scene.indices]+scene.offsets@atoms.cell.array)
    np.testing.assert_allclose(scene.fractional,atoms.get_scaled_positions(wrap=False)[scene.indices])
    edges=cell_segments(atoms.cell.array)
    assert edges.shape==(12,2,3)
    for vector in edges[:,1]-edges[:,0]:
        assert any(np.allclose(vector,cell) or np.allclose(vector,-cell) for cell in atoms.cell.array)
    for i,index in enumerate(scene.indices):
        np.testing.assert_array_equal(scene.colors[i],jmol_colors[atoms.numbers[index]])
    assert np.all(scene.ball_radii>0) and np.all(scene.space_radii>0)
    assert atoms==original and atoms.info==original_info


def test_rendering_limits_and_unknown_radius_fallback():
    atoms=Atoms('He'*(MAX_ATOMS+1),positions=np.column_stack((np.arange(MAX_ATOMS+1)*3.,
        np.zeros(MAX_ATOMS+1),np.zeros(MAX_ATOMS+1))),cell=[10000,5,5],pbc=True)
    scene=build_scene(atoms)
    assert len(scene.positions)==MAX_ATOMS
    assert scene.requested_count==MAX_ATOMS+1 and len(scene.bonds)==0
    assert 'first' in ' '.join(scene.notices) and 'Bonds are hidden' in ' '.join(scene.notices)
    rare=build_scene(Atoms('Og',positions=[[0,0,0]],cell=[5]*3,pbc=True))
    assert rare.space_radii[0]>0 and rare.colors.shape==(1,3)


def test_contacts_are_geometric_and_display_only():
    atoms=Atoms('CC',positions=[[0,0,0],[1.4,0,0]],cell=[3,4,4],pbc=True)
    scene=build_scene(atoms,(2,1,1))
    assert (0,1) in map(tuple,scene.bonds)
    assert (1,2) in map(tuple,scene.bonds)  # Across two displayed unit cells.
    assert len(atoms)==2


def test_mixed_occupancy_cif_is_viewable(tmp_path,app):
    path=tmp_path/'mixed.cif'
    path.write_text('''data_mixed
_cell_length_a 4
_cell_length_b 5
_cell_length_c 6
_cell_angle_alpha 78
_cell_angle_beta 101
_cell_angle_gamma 112
_space_group_IT_number 1
loop_
_space_group_symop_operation_xyz
'x,y,z'
loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
_atom_site_occupancy
Fe1 Fe 0 0 0 0.6
Ni1 Ni 0 0 0 0.4
O1 O 0.5 0.5 0.5 1
''',encoding='utf-8')
    structure=Structure.from_cif(path)
    assert structure.elastic_reason  # Calculation-ineligible, still viewable.
    original=structure.atoms.copy(); info=deepcopy(structure.atoms.info)
    dialog=CrystalStructureDialog()
    try:
        dialog.set_structure(structure);dialog.show();app.processEvents()
        scene=dialog.view.scene
        assert len(scene.positions)==len(structure.atoms)
        assert scene.occupancies[0]['CIF occupancy']=={'Fe':.6,'Ni':.4}
        dialog.inspect_atom(0)
        assert '0.6' in dialog.atom_info.toPlainText() and '0.4' in dialog.atom_info.toPlainText()
        assert 'representative elements' in dialog.notice.text()
        assert structure.atoms==original and structure.atoms.info==info
    finally:dialog.close()


def drag(widget,button,start,end):
    QtTest.QTest.mousePress(widget,button,pos=QtCore.QPoint(*start))
    point=QtCore.QPointF(*end)
    event=QtGui.QMouseEvent(QtCore.QEvent.Type.MouseMove,point,QtCore.QPointF(widget.mapToGlobal(QtCore.QPoint(*end))),
        QtCore.Qt.MouseButton.NoButton,button,QtCore.Qt.KeyboardModifier.NoModifier)
    QtWidgets.QApplication.sendEvent(widget,event)
    QtTest.QTest.mouseRelease(widget,button,pos=QtCore.QPoint(*end))


def exercise_dialog(dialog,app):
    dialog.show();app.processEvents()
    dialog.set_repetitions((2,2,2));app.processEvents()
    view=dialog.view;scene=view.scene
    positions=scene.positions.copy();indices=scene.indices.copy()
    xy,_,_=view.projected_atoms()
    target=next(i for i,point in enumerate(xy) if np.any(scene.offsets[i]) and view.pick_atom(point)==i)
    QtTest.QTest.mouseClick(view,QtCore.Qt.MouseButton.LeftButton,pos=QtCore.QPoint(*np.rint(xy[target]).astype(int)))
    text=dialog.atom_info.toPlainText()
    assert f'zero-based): {scene.indices[target]}' in text
    assert str(tuple(int(n) for n in scene.offsets[target])) in text
    before=view.orientation.copy()
    drag(view,QtCore.Qt.MouseButton.LeftButton,(100,100),(145,125))
    assert not np.allclose(view.orientation,before)
    drag(view,QtCore.Qt.MouseButton.RightButton,(120,120),(145,135))
    np.testing.assert_array_equal(view.pan,[25.,15.])
    zoom=view.zoom
    event=QtGui.QWheelEvent(QtCore.QPointF(150,150),QtCore.QPointF(view.mapToGlobal(QtCore.QPoint(150,150))),
        QtCore.QPoint(),QtCore.QPoint(0,120),QtCore.Qt.MouseButton.NoButton,
        QtCore.Qt.KeyboardModifier.NoModifier,QtCore.Qt.ScrollPhase.NoScrollPhase,False)
    QtWidgets.QApplication.sendEvent(view,event)
    assert view.zoom>zoom
    dialog.style.setCurrentIndex(1)
    assert view.space_filling
    dialog.showMaximized();app.processEvents()
    assert dialog.isMaximized()
    dialog.showNormal();view.reset_camera();app.processEvents()
    assert view.zoom==1 and np.all(view.pan==0)
    np.testing.assert_array_equal(scene.positions,positions)
    np.testing.assert_array_equal(scene.indices,indices)


def test_camera_picking_replica_and_read_only_snapshot(app):
    structure=Structure.nickel();original=structure.atoms.copy()
    dialog=CrystalStructureDialog()
    try:
        dialog.set_structure(structure)
        exercise_dialog(dialog,app)
        assert structure.atoms==original
        dialog.close();dialog.show();app.processEvents()
        assert dialog.view.scene is not None
    finally:dialog.close()


def test_main_window_menu_reopen_cif_replacement_and_state(tmp_path,app,monkeypatch):
    from emcd_sim.gui.app import MainWindow
    window=MainWindow(workspace=tmp_path/'workspace')
    errors=[];monkeypatch.setattr(window,'error',errors.append)
    monkeypatch.setattr(window,'store_ui_preferences',lambda:None)
    monkeypatch.setattr(window,'start_preview',lambda:pytest.fail('Viewer invoked numerical preview'))
    try:
        original=window.structure;atoms=original.atoms.copy()
        settings=asdict(window.settings())
        mdff=(window.model_box.currentIndex(),window.axis.text(),window.source_path.text(),
              {k:box.value() for k,box in window.spin.items()})
        state=(window.last_result,window.emcd_result,window.worker,window.busy)
        assert window.structure_view_action.text()=='View 3D Crystal Structure…'
        window.structure_view_action.trigger();app.processEvents()
        viewer=window.structure_viewer
        assert viewer.isVisible()
        exercise_dialog(viewer,app)
        viewer.close();app.processEvents()
        assert window.structure is original and window.structure.atoms==atoms
        assert asdict(window.settings())==settings
        assert mdff==(window.model_box.currentIndex(),window.axis.text(),window.source_path.text(),
                      {k:box.value() for k,box in window.spin.items()})
        assert state==(window.last_result,window.emcd_result,window.worker,window.busy)
        window.structure_view_action.trigger();app.processEvents()
        assert window.structure_viewer is viewer and viewer.isVisible()
        path=tmp_path/'nonorthogonal.cif'
        write(path,list(examples())[-1])
        monkeypatch.setattr(QtWidgets.QFileDialog,'getOpenFileName',lambda *a,**kw:(str(path),'CIF'))
        monkeypatch.setattr(window,'inspect_structure',lambda:None)
        window.load_cif();app.processEvents()
        assert not errors
        assert viewer._source is window.structure
        np.testing.assert_allclose(viewer.view.scene.cell,window.structure.atoms.cell.array)
        assert set(viewer.view.scene.symbols)=={'Fe','Ni','O'}
        # Viewer also updates when diffraction geometry itself is invalid.
        window.zone.setText('0 0 0');window.refresh();app.processEvents()
        assert viewer.view.scene is not None
        viewer.close();window.show_structure_viewer();app.processEvents()
        np.testing.assert_allclose(viewer.view.scene.cell,window.structure.atoms.cell.array)
    finally:
        for dialog in window.findChildren(QtWidgets.QDialog):dialog.close()
        window.close();window.deleteLater();app.processEvents()


@pytest.mark.skipif(sys.platform!='win32' or os.environ.get('QT_QPA_PLATFORM')!='windows',reason='Explicit native Windows GUI check')
def test_native_windows_interaction(app):
    assert app.platformName()=='windows'
    atoms=list(examples())[-1]
    dialog=CrystalStructureDialog()
    try:
        dialog.set_structure(Structure(atoms))
        exercise_dialog(dialog,app)
        assert QtTest.QTest.qWaitForWindowExposed(dialog.windowHandle(),3000)
        assert all(box.width()>=box.sizeHint().width() for box in dialog.repeats)
        assert dialog.isVisible()
        if os.environ.get('EMCD_VIEWER_CHECK_IMAGE'):dialog.grab().save(os.environ['EMCD_VIEWER_CHECK_IMAGE'])
    finally:dialog.close();app.processEvents()
