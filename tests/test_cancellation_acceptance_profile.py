"""A misconfigured acceptance profile must fail before launching any worker."""
import json

import pytest
from PySide6 import QtWidgets

from emcd_sim.gui import cancellation_acceptance, geometry
from emcd_sim.gui.app import MainWindow
from emcd_sim.gui.runtime import reference_source


@pytest.mark.parametrize('mismatch', ['grid', 'beam_basis'])
def test_mismatched_acceptance_profile_never_starts_worker(tmp_path, monkeypatch, mismatch):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    starts = []

    def forbidden_start(self):
        starts.append(True)
        raise AssertionError('Worker must not start with a mismatched profile')

    monkeypatch.setattr(MainWindow, 'start_emcd', forbidden_start)
    if mismatch == 'grid':
        snapshot = MainWindow.numerical_snapshot

        def wrong_grid(self):
            value = snapshot(self)
            if self.numerical_mode.currentIndex() == 1:
                value['grid'] = 10
            return value

        monkeypatch.setattr(MainWindow, 'numerical_snapshot', wrong_grid)
        message = 'Bounded cancellation profile preserved'
    else:
        original = geometry.geometry

        def wrong_basis(*args, **kwargs):
            values = list(original(*args, **kwargs))
            values[2] = values[2][:2]
            return tuple(values)

        monkeypatch.setattr(geometry, 'geometry', wrong_basis)
        message = 'Bounded cancellation profile has three retained beams'

    output = tmp_path / 'acceptance'
    assert cancellation_acceptance.run(output, reference_source()) == 1
    report = json.loads((output / 'acceptance.json').read_text())
    assert report['outcome'] == 'FAIL' and message in report['traceback']
    assert not starts and not report['cases']
    app.processEvents()
