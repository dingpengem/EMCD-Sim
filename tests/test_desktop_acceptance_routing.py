"""The frozen QA entry point forwards its explicit orientation unchanged."""
import sys
import pytest


@pytest.mark.parametrize('orientation', ['001', '017', '117', '111', '710'])
def test_desktop_orientation_dispatch(monkeypatch, tmp_path, orientation):
    from emcd_sim.gui import app, desktop_acceptance
    from emcd_sim.gui import runtime
    monkeypatch.setattr(runtime, 'configure_logging', lambda: None)
    calls = []
    monkeypatch.setattr(desktop_acceptance, 'run', lambda *args: calls.append(args) or 0)
    monkeypatch.setattr(sys, 'argv', ['EMCD-Sim', '--desktop-acceptance', str(tmp_path),
                                    '--desktop-orientation', orientation])
    assert app.main() == 0
    assert calls == [(tmp_path, orientation)]
