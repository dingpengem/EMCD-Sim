"""Done returns to Material; only the outer action accepts its draft."""
import pytest
from PySide6 import QtCore, QtWidgets, QtTest
from test_multisite_gui_run import app, window
from test_material_mdff_workflow import xmcd_draft
from test_mdff_workspace_participation import grouped
from test_group_mdff_native_controls import native_xmcd


def click(app,button):
    QtTest.QTest.mouseClick(button,QtCore.Qt.MouseButton.LeftButton)
    app.processEvents();QtTest.QTest.qWait(100)


def returned(app,w,v,d):
    assert w.isVisible() and v.isVisible() and not d.isVisible()
    if app.platformName()=='cocoa':assert v.isActiveWindow()


def test_global_done_returns_without_material_acceptance(window,app):
    w=window;w.show();v=xmcd_draft(w);d=w.open_mdff_context()
    app.processEvents();QtTest.QTest.qWait(100)
    click(app,d.buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Apply))
    returned(app,w,v,d)
    assert d.draft_ready() and w._accepted_global_mdff is None
    click(app,v.dialog_buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Apply))
    assert not v.isVisible() and w._accepted_global_mdff is not None
    accepted=w._accepted_global_mdff
    w.show_structure_viewer();assert w._accepted_global_mdff==accepted
    assert v.draft_global_direction()==accepted.magnetization


def test_two_local_groups_done_cancel_and_outer_acceptance(window,app,tmp_path):
    w=window;w.show();editor=grouped(w);v=w.structure_viewer;v.show()
    rows=tuple(r[:3]+((1.,0.,0.) if r[1]=='Fe' else None,r[4]) for r in editor.rows())
    editor.replace_rows(rows)
    editor.excluded_groups={r[0] for r in rows if r[1]=='O'}
    fe=[r for r in rows if r[1]=='Fe']
    for i,row in enumerate(fe):
        d=w.open_mdff_context(row[0]);native_xmcd(d,tmp_path/f'fe-{i}.dat')
        app.processEvents();QtTest.QTest.qWait(100)
        click(app,d.buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Apply))
        returned(app,w,v,d)
        assert editor.rows()[editor.current_row()][4] is not None
    assert all(r[4] is None for r in editor._accepted_rows)
    before=editor.rows();d=w.open_mdff_context(fe[0][0]);old=d.xmcd_scale.text()
    d.xmcd_scale.setText('7')
    click(app,d.buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Cancel))
    assert v.isVisible() and editor.rows()==before and d.xmcd_scale.text()==old
    click(app,v.dialog_buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Apply))
    assert not v.isVisible(),editor.status.text()
    w.show_structure_viewer();assert editor.rows()==before
    assert all(r[3]==(1.,0.,0.) and r[4] is not None for r in editor.rows() if r[1]=='Fe')


def test_deferred_screen_fit_stops_with_its_window(app,tmp_path,monkeypatch):
    import sys
    from emcd_sim.gui.app import MainWindow
    errors=[];monkeypatch.setattr(sys,'excepthook',lambda *exc:errors.append(exc))
    w=MainWindow(tmp_path/'disposed-workspace');w.store_ui_preferences=lambda:None;w.show()
    app.processEvents();w.responsive.screen_changed()
    w.project_dirty=False;w.close();w.deleteLater()
    app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete);QtTest.QTest.qWait(250)
    assert not errors
