"""Mouse-driven MDFF/Material transactions; Cocoa also verifies activation."""
from PySide6 import QtCore, QtWidgets, QtTest
from shiboken6 import isValid

from test_multisite_gui_run import app, window
from test_material_mdff_workflow import xmcd_draft
from test_group_mdff import create, imported, source
from emcd_sim.gui.mdff_workspace import MDFFWorkspace


def settle():
    QtWidgets.QApplication.processEvents()
    QtTest.QTest.qWait(60)
    QtWidgets.QApplication.processEvents()


def click(button):
    assert button.isVisible() and button.isEnabled()
    QtTest.QTest.mouseClick(button, QtCore.Qt.MouseButton.LeftButton)
    settle()


def mdff_button(dialog, kind):
    return dialog.buttons.button(kind)


def outer_button(viewer, kind):
    return viewer.dialog_buttons.button(kind)


APPLY = QtWidgets.QDialogButtonBox.StandardButton.Apply
CANCEL = QtWidgets.QDialogButtonBox.StandardButton.Cancel


def returned(viewer, dialog):
    assert not dialog.isVisible()
    assert isValid(viewer) and viewer.isVisible()
    if QtWidgets.QApplication.platformName() == 'cocoa':
        assert viewer.isActiveWindow(), 'Done/Cancel must activate the original Cocoa Viewer'


def watch(viewer, monkeypatch):
    calls = []
    # A connected bound slot may predate this spy; Close and signals cover it too.
    original = viewer.closeEvent
    monkeypatch.setattr(viewer, 'closeEvent', lambda event: (calls.append('close'), original(event))[-1])
    for name in ('accepted', 'rejected', 'finished', 'destroyed'):
        getattr(viewer, name).connect(lambda *_, name=name: calls.append(name))
    viewer.globalDirectionApplied.connect(lambda *_: calls.append('direction committed'))
    viewer.siteGroupsApplied.connect(lambda *_: calls.append('groups committed'))
    return calls


def configure(viewer):
    viewer.tabs.setCurrentWidget(viewer.editor)
    settle()
    button = next(b for b in viewer.editor.findChildren(QtWidgets.QPushButton)
                  if b.text().startswith('Configure MDFF'))
    viewer.editor.ensureWidgetVisible(button)
    click(button)
    return next(d for d in viewer.parent().findChildren(MDFFWorkspace) if d.isVisible())


def test_global_done_cancel_and_outer_transaction(window, monkeypatch):
    w = window; w.show(); v = xmcd_draft(w); settle()
    calls = watch(v, monkeypatch)
    v.global_direction.setText('0 1 0')
    selected = v.editor.groups.currentItem()
    dialog = configure(v)
    click(mdff_button(dialog, APPLY))
    returned(v, dialog)
    assert not calls and w._accepted_global_mdff is None
    assert v.global_direction.text() == '0 1 0'
    assert v.editor.groups.currentItem() is selected
    prepared = dialog._draft_configuration
    assert dialog.draft_ready()
    assert configure(v) is dialog and dialog._draft_configuration is prepared
    # Failed Done does not hide the editor or accept a previous valid draft.
    w.xmcd_scale.clear()
    click(mdff_button(dialog, APPLY))
    assert dialog.isVisible() and 'positive finite' in dialog.status.text()
    assert not calls and w._accepted_global_mdff is None
    click(mdff_button(dialog, CANCEL)); returned(v, dialog)
    assert w.xmcd_scale.text() == '1' and not dialog.has_unapplied_edits()
    assert not calls and v.global_direction.text() == '0 1 0'
    assert configure(v) is dialog
    w.model_box.setCurrentIndex(0); w.validate_xmcd(show_error=False); w.declaration.setChecked(True)
    click(mdff_button(dialog, APPLY)); returned(v, dialog)
    click(outer_button(v, APPLY))
    assert not v.isVisible() and w._accepted_global_mdff is not None
    assert w._accepted_global_mdff.magnetization == (0., 1., 0.)
    accepted = w._accepted_global_mdff
    calls.clear(); w.show_structure_viewer(); settle()
    v.global_direction.setText('1 0 0'); dialog = configure(v)
    w.xmcd_scale.setText('2'); click(mdff_button(dialog, APPLY)); returned(v, dialog)
    assert w._accepted_global_mdff is accepted and not calls
    click(outer_button(v, CANCEL)); settle()
    assert not v.isVisible() and w._accepted_global_mdff is accepted
    assert w.xmcd_scale.text() == '1' and v.global_direction.text() == '0 1 0'
    assert not dialog.has_unapplied_edits()


def test_local_done_repeated_groups_and_outer_transaction(window, tmp_path, monkeypatch):
    w = window; w.show(); v = xmcd_draft(w); e = v.editor
    create(e, 'Ni(A)', [0, 1]); create(e, 'Ni(B)', [2, 3], '0 0 -1')
    calls = watch(v, monkeypatch)
    rows = e.rows(); dialogs = {}
    for i in (0, 1, 0, 1, 0, 1):
        e.groups.setCurrentItem(e.groups.topLevelItem(i)); row = e.rows()[i]
        d = configure(v)
        if row[0] not in dialogs:
            imported(d, source(tmp_path, row[0], element='Ni', axis=row[3], scale=i+1))
            dialogs[row[0]] = d
        else:
            assert dialogs[row[0]] is d
        selected = e.groups.currentItem().text(0)
        click(mdff_button(d, APPLY)); returned(v, d)
        assert not calls and e.accepted_site_groups is None
        assert e.groups.currentItem().text(0) == selected
        assert tuple(r[:4] for r in e.rows()) == tuple(r[:4] for r in rows)
        assert e.rows()[i][4] is not None
    assert len(e.mdff_dialogs) == 2
    assert sum(isinstance(d, MDFFWorkspace) for d in w.findChildren(QtWidgets.QDialog)) == 3
    staged = e.rows(); d = configure(v)
    d.import_path.setText(str(tmp_path/'missing-source.json'))
    click(mdff_button(d, APPLY))
    assert d.isVisible() and 'Invalid' in d.status.text() and not calls
    click(mdff_button(d, CANCEL)); returned(v, d)
    assert e.rows() == staged and not d.has_unapplied_edits()
    assert configure(v) is d
    click(mdff_button(d, APPLY)); returned(v, d)
    click(outer_button(v, APPLY))
    assert not v.isVisible() and e.accepted_site_groups is not None
    accepted = e.rows(); accepted_model = e.accepted_site_groups
    calls.clear(); w.show_structure_viewer(); settle()
    e.groups.setCurrentItem(e.groups.topLevelItem(0)); d = configure(v)
    imported(d, source(tmp_path, 'changed', element='Ni', scale=9))
    click(mdff_button(d, APPLY)); returned(v, d)
    assert not calls and e.accepted_site_groups is accepted_model and e.rows() != accepted
    click(outer_button(v, CANCEL)); settle()
    assert not v.isVisible() and e.rows() == accepted
    assert not any(d.isVisible() for d in dialogs.values())
    assert not w.test_errors


def test_queued_return_does_not_reopen_cancelled_viewer_or_cover_other_editor(window, monkeypatch):
    w = window; w.show(); v = xmcd_draft(w)
    create(v.editor, 'Ni(A)', [0, 1]); create(v.editor, 'Ni(B)', [2, 3])
    w.set_magnetization_mode('global'); d = configure(v)
    # Process both button events but deliberately postpone the queued handoff.
    button = mdff_button(d, APPLY)
    QtTest.QTest.mouseClick(button, QtCore.Qt.MouseButton.LeftButton)
    v.reject(); settle()
    assert not v.isVisible() and w._accepted_global_mdff is None
    w.show_structure_viewer()
    create(v.editor, 'Ni(A)', [0, 1]); create(v.editor, 'Ni(B)', [2, 3])
    w.set_magnetization_mode('global'); w.model_box.setCurrentIndex(0)
    w.validate_xmcd(show_error=False); w.declaration.setChecked(True); d = configure(v)
    QtTest.QTest.mouseClick(mdff_button(d, APPLY), QtCore.Qt.MouseButton.LeftButton)
    assert not d.isVisible() and d.draft_ready()
    other = w.open_mdff_context('Ni(A)'); settle()
    assert other.isVisible() and not d.isVisible()
    if QtWidgets.QApplication.platformName() == 'cocoa': assert other.isActiveWindow()
    other.reject(); settle()
    returned(v, other)
