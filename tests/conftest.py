"""Test-owned GUI lifecycle; never alter production memory admission.

QWidget.close() hides a window; it does not destroy its Qt object or signal
connections. Delete only MainWindows created by this test, after its own
fixtures have closed them. Preserve pre-existing module/class-owned windows.
"""
import gc
import json
import os
from pathlib import Path
import sys

import pytest


def pytest_collection_modifyitems(config, items):
    # Exact reviewed replacements execute both historical and current contracts.
    from mdff_workflow_registration import install
    install(config, items)


@pytest.fixture(autouse=True)
def release_test_owned_gui_resources(request, monkeypatch):
    qt = sys.modules.get('PySide6.QtWidgets')
    app = qt.QApplication.instance() if qt else None
    # Keep wrappers alive: otherwise Python can reuse an ID for a new test
    # window and incorrectly classify it as a pre-existing/shared window.
    before_windows = tuple(app.topLevelWidgets()) if app else ()
    before = {id(w) for w in before_windows}
    if qt:
        warning, execute = qt.QMessageBox.warning, qt.QMessageBox.exec
        def owned(window):
            return type(window).__name__ == 'MainWindow' and id(window) not in before
        def project_warning(parent, title, *args, **kwargs):
            # Stage 4D added confirmations to legacy New/Close workflows.
            # Explicitly discard temporary test inputs by default. Tests of
            # Save/Cancel install their own responses after this fixture.
            if owned(parent) and title == 'Unsaved Changes':
                return qt.QMessageBox.StandardButton.Discard
            return warning(parent, title, *args, **kwargs)
        def retain_calculation(dialog, *args, **kwargs):
            if owned(dialog.parent()) and dialog.windowTitle() == 'Retain Calculation':
                dialog.defaultButton().click()  # keep as a new test calculation
                return qt.QDialog.DialogCode.Accepted
            return execute(dialog, *args, **kwargs)
        monkeypatch.setattr(qt.QMessageBox, 'warning', project_warning)
        monkeypatch.setattr(qt.QMessageBox, 'exec', retain_calculation)
    pyplot = sys.modules.get('matplotlib.pyplot')
    figures = set(pyplot.get_fignums()) if pyplot else set()
    yield
    qt = sys.modules.get('PySide6.QtWidgets')
    app = qt.QApplication.instance() if qt else None
    destroyed = 0
    if app:
        from PySide6 import QtCore
        window = None
        for window in list(app.topLevelWidgets()):
            if id(window) in before or type(window).__name__ != 'MainWindow':
                continue
            # Tests must terminate their own calculations. A remaining active
            # worker is a real cleanup failure, not permission to destroy it.
            assert not getattr(window, 'busy', False), 'Test left a running GUI calculation'
            window.close()
            window.deleteLater()
            destroyed += 1
        del window  # release this fixture's temporary wrapper reference
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        app.processEvents()
    pyplot = sys.modules.get('matplotlib.pyplot')
    if pyplot:
        for number in set(pyplot.get_fignums()) - figures:
            pyplot.close(number)
    gc.collect()
    gc.collect()
    if app:
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        app.processEvents()
        log = os.environ.get('EMCD_TEST_LIFECYCLE_LOG')
        if log:
            from emcd_sim.gui.memory_budget import memory_snapshot
            data = dict(test=request.node.nodeid, destroyed_windows=destroyed,
                        remaining_mainwindows=sum(type(w).__name__ == 'MainWindow' for w in app.topLevelWidgets()),
                        **memory_snapshot())
            with Path(log).open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(data)+'\n')
