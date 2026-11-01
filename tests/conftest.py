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


@pytest.fixture(autouse=True)
def release_test_owned_gui_resources(request):
    qt = sys.modules.get('PySide6.QtWidgets')
    app = qt.QApplication.instance() if qt else None
    before = {id(w) for w in app.topLevelWidgets()} if app else set()
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
