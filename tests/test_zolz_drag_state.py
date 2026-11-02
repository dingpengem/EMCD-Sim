"""Drag freshness and release-coordinate regression controls, without solvers."""
from dataclasses import asdict
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import pytest
from test_zolz_laue_overlay import window,mouse,assert_circle
from emcd_sim.gui.geometry import za_from_tilt


def seed_preview(w):
    """Synthetic cached display values, not a calculated scientific reference."""
    s=w.settings()
    w.last_result=dict(settings=asdict(s),systematic_row=w.row_projection.isChecked(),
        source=w.structure.source,source_sha256=w.structure.sha256,
        intensity=np.linspace(.1,.9,len(w.current[2])))
    w.refresh();w.canvas.draw()
    assert w.tabs.tabText(0)=='Diffraction (current)'
    return s,w.last_result,w.last_result['intensity'].copy()


def test_motion_invalidates_all_preview_indicators_and_restores_exact_cache(window):
    w=window;w.numerical_mode.setCurrentIndex(1);w.declaration.setChecked(True)
    s,cached,intensity=seed_preview(w)
    # Minimal result identity for testing status labels only; no maps fabricated.
    w.emcd_result=dict(settings=s,config=w.forward_settings(),methods={},
        metadata=dict(structure=w.structure.description(),settings=asdict(s)))
    w.emcd_stale();assert 'inputs match' in w.maps_view.label.text()
    q=za_from_tilt(s.tilt,s.voltage);w.mode.setCurrentIndex(1)
    w.clicked(mouse(w,'button_press_event',q))
    with patch.object(w,'emcd_stale',wraps=w.emcd_stale) as stale:
        w.drag_za(mouse(w,'motion_notify_event',q+[.03,.05]));w.canvas.draw()
        assert w.tabs.tabText(0)=='Diffraction (last preview)'
        assert w._diffraction_spots.get_array() is None
        assert len(w._diffraction_spots.get_facecolors())==0
        np.testing.assert_array_equal(w._diffraction_spots.get_sizes(),np.full(len(w.current[2]),28))
        assert 'not calculated for current inputs' in w.selection.text()
        assert 'Inputs differ from last preview' in w.info.toPlainText()
        assert 'last preview' in w.table.horizontalHeaderItem(4).text()
        for v in (w.maps_view,w.eels_view,w.diffraction_view,w.overview_view):
            assert 'STALE RESULT' in v.label.text()
        w.drag_za(mouse(w,'motion_notify_event',q+[.05,.08]))
        assert stale.call_count==1  # no repeated preflight for stale-to-stale motion
        w.drag_za(mouse(w,'motion_notify_event',q));w.canvas.draw()
        assert w.settings()==s and w.tabs.tabText(0)=='Diffraction (current)'
        np.testing.assert_array_equal(w._diffraction_spots.get_array(),intensity)
        assert len(w._diffraction_spots.get_facecolors())==len(intensity)
        assert 'inputs match' in w.maps_view.label.text()
        assert stale.call_count==2
    assert w.last_result is cached
    np.testing.assert_array_equal(cached['intensity'],intensity)
    w.release_za(mouse(w,'button_release_event',q));assert not w._za_drag


def test_release_commits_final_point_once_and_preserves_detectors(window):
    w=window;w.mode.setCurrentIndex(1);w.canvas.draw();detectors=w.detectors.copy()
    w.clicked(mouse(w,'button_press_event',[.1,.1]))
    w.drag_za(mouse(w,'motion_notify_event',[.2,.2]))
    event=mouse(w,'button_release_event',[.3,.25])
    with patch.object(w,'refresh',wraps=w.refresh) as refresh:
        w.release_za(event);w.release_za(event)
        assert refresh.call_count==1
    np.testing.assert_allclose(w._laue_circle.center,[.3,.25],atol=1e-10)
    assert w.settings()==w.drawn_settings;assert_circle(w)
    np.testing.assert_array_equal(w.detectors,detectors)
    assert w.worker is None and w.last_result is None


@pytest.mark.parametrize('bad', ['outside','missing','nan','inf','range'])
def test_invalid_motion_and_release_keep_last_valid_position(window,bad):
    w=window;w.mode.setCurrentIndex(1);w.canvas.draw()
    w.clicked(mouse(w,'button_press_event',[.1,.1]))
    w.drag_za(mouse(w,'motion_notify_event',[.2,.2]));s=w.settings()
    invalid=dict(outside=(None,0,0),missing=(w.ax,None,None),nan=(w.ax,np.nan,.1),
        inf=(w.ax,.1,np.inf),range=(w.ax,100,100))[bad]
    event=SimpleNamespace(inaxes=invalid[0],xdata=invalid[1],ydata=invalid[2],button=1)
    w.drag_za(event);assert w.settings()==s
    w.release_za(event);assert w.settings()==s and not w._za_drag
    np.testing.assert_allclose(w._laue_circle.center,[.2,.2],atol=1e-10)
    assert_circle(w)


def test_click_only_is_not_applied_twice_and_nonfinite_press_is_ignored(window):
    w=window;w.mode.setCurrentIndex(1);w.canvas.draw();s=w.settings()
    w.clicked(SimpleNamespace(inaxes=w.ax,xdata=np.nan,ydata=.1,button=1))
    assert w.settings()==s and not w._za_drag
    with patch.object(w,'refresh',wraps=w.refresh) as refresh:
        w.clicked(mouse(w,'button_press_event',[.13,-.19]))
        n=refresh.call_count
        w.release_za(mouse(w,'button_release_event',[.13,-.19]))
        assert refresh.call_count==n
    np.testing.assert_allclose(w._laue_circle.center,[.13,-.19],atol=1e-10)


def test_automatic_geometry_refresh_does_not_end_drag(window):
    w=window;w.mode.setCurrentIndex(1);w.canvas.draw()
    w.clicked(mouse(w,'button_press_event',[.1,.1]))
    original=w.emcd_stale
    # Exercise the existing Automatic-mode path that can refresh the plot once.
    def once():
        # Avoid recursion from the refresh's own final status update.
        with patch.object(w,'emcd_stale',side_effect=original):w.refresh()
    with patch.object(w,'emcd_stale',side_effect=once):
        w.drag_za(mouse(w,'motion_notify_event',[.2,.2]))
    assert w._za_drag;assert_circle(w)
    w.drag_za(mouse(w,'motion_notify_event',[.25,.2]))
    w.release_za(mouse(w,'button_release_event',[.3,.25]))
    np.testing.assert_allclose(w._laue_circle.center,[.3,.25],atol=1e-10)
