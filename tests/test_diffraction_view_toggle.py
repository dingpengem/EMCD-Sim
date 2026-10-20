"""Diffraction viewport regression tests; no physical calculations."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from contextlib import ExitStack
from dataclasses import asdict
from unittest.mock import patch
import numpy as np
import pytest
from PySide6 import QtWidgets
from emcd_sim.gui.app import MainWindow


@pytest.fixture
def window(tmp_path):
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    with ExitStack() as guards:
        for name in ('emcd_sim.gui.app.preview','emcd_sim.gui.app.PreviewWorker.start',
                     'emcd_sim.gui.stage_b.calculate','emcd_sim.gui.stage_b.EMCDWorker.start',
                     'emcd_sim.gui.propagation.propagate','emcd_sim.gui.emcd_forward.calculate',
                     'numpy.linalg.eigh'):
            guards.enter_context(patch(name,side_effect=AssertionError('Viewport must not run solvers')))
        w=MainWindow(workspace=tmp_path/'workspace')
        w.numerical_mode.setCurrentIndex(1);w.model_box.setCurrentIndex(1)
        yield w
        w.close();app.processEvents()


def limits(w):return w.ax.get_xlim(),w.ax.get_ylim()


def zoom(w):
    # Deliberately unequal spans and inverted Y: restore the exact user view.
    w.ax.set(xlim=(-.31,.73),ylim=(.82,-.19))
    return limits(w)


def annotations(w):
    return ([text.get_text() for text in w.ax.texts],
            [(line.get_label(),line.get_marker()) for line in w.ax.lines],
            [(patch.get_label(),tuple(patch.center),patch.radius) for patch in w.ax.patches])


def test_expand_restore_repeated_and_preserve_all_inputs(window):
    w=window;original=zoom(w);before=annotations(w)
    settings=asdict(w.settings());cfg=asdict(w.forward_settings());detectors=w.detectors.copy()
    saved_result=object();w.emcd_result=saved_result
    for _ in range(3):
        assert w.basis_view_button.text()=='Show full basis'
        w.basis_view_button.click()
        bound=w.settings().beam_cutoff+.2
        assert limits(w)==((-bound,bound),(-bound,bound))
        assert w.basis_view_button.text()=='Restore previous view'
        assert annotations(w)==before and w.ax.get_aspect()==1
        w.basis_view_button.click()
        assert limits(w)==original and w.ax.get_aspect()==1
        assert annotations(w)==before
    assert asdict(w.settings())==settings and asdict(w.forward_settings())==cfg
    np.testing.assert_array_equal(w.detectors,detectors)
    assert w.emcd_result is saved_result and w.last_result is None
    w.emcd_result=None


def test_refresh_and_intensity_only_changes_preserve_saved_view(window):
    w=window;original=zoom(w);before=annotations(w)
    w.basis_view_button.click();full=limits(w)
    w.refresh();w.refresh()
    assert w._basis_view_limits==original and limits(w)==full
    assert annotations(w)==before
    w.spin['thickness'].setValue(35)
    assert w._basis_view_limits==original
    w.basis_view_button.click();assert limits(w)==original


@pytest.mark.parametrize('change',['beam','zone','target','tilt','voltage','cell'])
def test_geometry_changes_invalidate_previous_view(window,change):
    w=window;old=zoom(w);w.basis_view_button.click()
    w.toolbar.push_current()
    if change=='beam':w.spin['beam'].setValue(2.8)
    elif change=='zone':w.zone.setText('7 1 0');w.refresh()
    elif change=='target':w.target.setText('4 0 0');w.refresh()
    elif change=='tilt':w.spin['tx'].setValue(-6)
    elif change=='voltage':w.spin['kv'].setValue(300)
    else:w.structure.atoms.set_cell(w.structure.atoms.cell.array*1.01,scale_atoms=True);w.refresh()
    assert w._basis_view_limits is None
    assert w.basis_view_button.text()=='Show full basis'
    # New toggle saves the current viewport, never the old incompatible one.
    new=limits(w);assert new!=old
    w.basis_view_button.click();w.basis_view_button.click();assert limits(w)==new
    assert w.toolbar._nav_stack()==None


def test_invalid_geometry_clears_state(window):
    w=window;zoom(w);w.basis_view_button.click()
    w.zone.setText('0');w.refresh()
    assert w._basis_view_limits is None and w._basis_view_geometry is None
    assert not w.basis_view_button.isEnabled()
    w.zone.setText('0 1 7');w.refresh()
    assert w.basis_view_button.isEnabled() and w.basis_view_button.text()=='Show full basis'


def test_pan_zoom_and_navigation_remain_available(window):
    w=window;original=zoom(w)
    w.toolbar.push_current();w.basis_view_button.click();w.toolbar.push_current()
    w.toolbar.back();assert limits(w)==original
    w.toolbar.forward()
    # User pan/zoom while expanded does not overwrite the pre-toggle snapshot.
    w.ax.set(xlim=(-1.5,1.9),ylim=(-.5,1.7))
    panned=limits(w);w.refresh();assert limits(w)==panned
    w.toolbar.pan();mode=w.toolbar.mode
    w.basis_view_button.click()
    assert limits(w)==original and w.toolbar.mode==mode
    w.toolbar.pan()
