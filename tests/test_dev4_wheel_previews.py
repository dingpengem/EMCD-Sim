"""Focused control/preview checks; existing model generators, no propagation."""
from dataclasses import replace

import numpy as np
from PySide6 import QtCore,QtGui,QtWidgets,QtTest

from test_multisite_gui_run import app,window
from emcd_sim.gui.parameter_wheel import protect_parameter_wheels
from emcd_sim.gui.group_mdff import GroupMDFFDialog
from emcd_sim.gui.emcd_forward import DEFAULT_SOURCE,inspect_source


def wheel(widget,delta=-120):
    point=widget.rect().center()
    event=QtGui.QWheelEvent(QtCore.QPointF(point),QtCore.QPointF(widget.mapToGlobal(point)),
        QtCore.QPoint(),QtCore.QPoint(0,delta),QtCore.Qt.MouseButton.NoButton,
        QtCore.Qt.KeyboardModifier.NoModifier,QtCore.Qt.ScrollPhase.NoScrollPhase,False)
    QtWidgets.QApplication.sendEvent(widget,event)


def xmcd(d):
    d.model.setCurrentIndex(0);d.source_path.setText(str(DEFAULT_SOURCE));d.validate_xmcd_source()
    info=inspect_source(DEFAULT_SOURCE)
    d.spin['xl3'].setValue(info['selected']['L3']);d.spin['xl2'].setValue(info['selected']['L2'])
    d.xmcd_provenance.setText(info['provenance'])
    d.xmcd_validity.setText('Existing native Ni XAS/XMCD example; effective axisymmetric model, not full ab-initio MDFF')
    d.xmcd_scale.setText('1');d.declaration.setChecked(True)


def test_focused_controls_forward_wheel_to_page(app):
    scroll=QtWidgets.QScrollArea();scroll.resize(240,180);body=QtWidgets.QWidget()
    layout=QtWidgets.QVBoxLayout(body);body.setMinimumHeight(1200)
    spin=QtWidgets.QDoubleSpinBox();spin.setValue(2.5);layout.addWidget(spin)
    integer=QtWidgets.QSpinBox();integer.setValue(7);layout.addWidget(integer)
    combo=QtWidgets.QComboBox();combo.addItems(['first','second']);layout.addWidget(combo)
    layout.addStretch();scroll.setWidget(body);scroll.setWidgetResizable(True)
    protect_parameter_wheels(scroll);scroll.show();app.processEvents()
    try:
        for control,value in ((spin,2.5),(integer,7),(combo,0)):
            scroll.verticalScrollBar().setValue(0);control.setFocus();app.processEvents()
            assert control.hasFocus()
            wheel(control)
            assert (control.currentIndex() if control is combo else control.value())==value
            assert scroll.verticalScrollBar().value()>0
        integer.setFocus();QtTest.QTest.keyClick(integer,QtCore.Qt.Key.Key_Up)
        assert integer.value()==8
        spin.stepUp();assert spin.value()>2.5
    finally:scroll.close();scroll.deleteLater()


def test_wheel_does_not_edit_working_drafts_or_dirty_state(window,app):
    window.numerical_mode.setCurrentIndex(1);window.show();app.processEvents()
    window.project_dirty=False
    before=(window.settings(),window.mdff_dialog.snapshot(),window._accepted_global_mdff)
    for control in (window.spin['beam'],window.numerical_mode):
        control.setFocus();app.processEvents();assert control.hasFocus();wheel(control)
    assert (window.settings(),window.mdff_dialog.snapshot(),window._accepted_global_mdff)==before
    assert not window.project_dirty
    window.show_structure_viewer();viewer=window.structure_viewer;app.processEvents()
    zoom=viewer.view.zoom;wheel(viewer.view)
    assert viewer.view.zoom!=zoom  # Intentional 3D navigation stays active.


def test_xmcd_source_guidance_reversed_group_and_global_context(window,tmp_path,app):
    window.show_structure_viewer(show=False)
    d=GroupMDFFDialog(('Ni','Ni',(0,1,2,3),(0.,0.,1.),None),tmp_path,window.structure_viewer.editor)
    d.model.setCurrentIndex(0);d.source_path.setText(str(DEFAULT_SOURCE));d.validate_xmcd_source()
    assert d.xmcd_preview.snapshot is None
    assert len(d.xmcd_preview.figure.axes[0].lines)==4  # Authenticated input, no invented tensor.
    d.declaration.setChecked(True);d.xmcd_preview.update_preview()
    assert 'Source / provenance' in d.xmcd_preview.status.text()
    xmcd(d);d.xmcd_preview.update_preview();p=d.xmcd_preview
    assert p.snapshot is not None and not p.is_stale
    baseline={k:v.copy() for k,v in p.snapshot['states'].items()}
    accepted=replace(p.snapshot['config'],magnetization=(0.,0.,-1.),pair_reversed=True)
    d.reference=accepted;d.set_context(d.row[:3]+((0.,0.,-1.),accepted));d.restore_reference(accepted)
    d.declaration.setChecked(True);p.update_preview()
    assert p.snapshot['config'].magnetization==(0.,0.,-1.) and p.snapshot['config'].pair_reversed
    np.testing.assert_allclose(p.snapshot['states']['+M'],baseline['−M'],rtol=1e-13,atol=1e-14)
    assert d.reference is accepted  # Preview never confirms the draft.
    for _,values in p.curves:assert np.isfinite(values).all()
    d.eta.setValue(d.eta.value()+.1);p.invalidate_if_changed();assert p.is_stale
    window.model_box.setCurrentIndex(0);window.declaration.setChecked(True);window.xmcd_preview.update_preview()
    assert window.xmcd_preview.snapshot is not None,window.xmcd_preview.status.text()
    assert window.xmcd_preview.snapshot['config'].magnetization==window.material_magnetization
    assert window._accepted_global_mdff is None
    assert p.snapshot['config'].magnetization==(0.,0.,-1.)
    d.close()


def test_atomic_and_manual_valid_previews_remain_unapplied(window,tmp_path,app):
    window.show_structure_viewer(show=False)
    d=GroupMDFFDialog(('Ni','Ni',(0,1,2,3),(0.,0.,1.),None),tmp_path,window.structure_viewer.editor)
    d.model.setCurrentIndex(1)
    for key,value in dict(samples='9',emin='800',emax='900').items():d.atomic.fields[key].setText(value)
    d.preview_current_model()
    assert hasattr(d.atomic,'preview_dialog'),d.atomic.status.text()
    assert d.atomic.preview_dialog.isVisible()
    assert len(d.atomic.spectrum_figure.axes[0].lines)==3
    for line in d.atomic.spectrum_figure.axes[0].lines:assert np.isfinite(line.get_ydata()).all()
    d.model.setCurrentIndex(2);d.manual_mode.setCurrentIndex(1);d.manual_spectral.samples.setValue(9)
    d.preview_current_model()
    assert d.manual_spectral.snapshot is not None,d.status.text()
    assert d.manual_spectral.numeric_curves
    for _,values in d.manual_spectral.numeric_curves:assert np.isfinite(values).all()
    assert d.reference is None and window._accepted_global_mdff is None
    d.atomic.preview_dialog.close();d.close()
