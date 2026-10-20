"""The packaged acceptance controls also run without scientific solvers."""
from contextlib import ExitStack
from unittest.mock import patch
from PySide6 import QtWidgets
from emcd_sim.gui.app import MainWindow
from emcd_sim.gui.stage_f_acceptance import FORWARD_PATHS, release_controls


def test_development_acceptance_controls(tmp_path):
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    with ExitStack() as guards:
        mocks=[guards.enter_context(patch(name,side_effect=AssertionError('No solver permitted')))
               for name in FORWARD_PATHS]
        window=MainWindow(workspace=tmp_path/'workspace')
        try:
            checks=release_controls(window,app)
            assert checks['automatic_manual_roundtrip'] and checks['reversible_basis_view']
            assert not any(mock.call_count for mock in mocks)
        finally:
            window.close();app.processEvents()
