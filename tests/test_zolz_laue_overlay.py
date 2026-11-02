"""Geometry and interaction controls for the display-only zero-excitation circle."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from dataclasses import replace
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest
pytest.importorskip('PySide6')
pytest.importorskip('ase')
from PySide6 import QtWidgets
from matplotlib.backend_bases import MouseEvent
from matplotlib.colors import to_rgba
from emcd_sim.gui.app import MainWindow
from emcd_sim.gui.geometry import Settings, Structure, geometry, excitation, align_bragg, za_from_tilt


@pytest.mark.parametrize('voltage',[200,300])
def test_bragg_circle_and_sampled_excitation(voltage):
    s=replace(Settings(),voltage=voltage)
    _,_,hkl,g,_=geometry(Structure.nickel(),s)
    target=g[hkl.index((2,0,0))]
    tilt=align_bragg(target,[0,15],voltage,'Y')
    center=za_from_tilt(tilt,voltage);radius=np.linalg.norm(center)
    assert abs(np.linalg.norm(target-center)-radius)<1e-13
    assert abs(np.linalg.norm(center)-radius)<1e-13  # transmitted beam
    a=np.linspace(0,2*np.pi,101)
    points=center+radius*np.column_stack((np.cos(a),np.sin(a)))
    np.testing.assert_allclose(excitation(points,tilt,voltage),0,atol=1e-13)


@pytest.fixture
def window(tmp_path):
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    # Any inadvertent scientific execution fails rather than doing expensive work.
    with ExitStack() as guards:
        for name in ('emcd_sim.gui.app.preview','emcd_sim.gui.app.PreviewWorker.start',
                     'emcd_sim.gui.stage_b.calculate','emcd_sim.gui.stage_b.EMCDWorker.start',
                     'emcd_sim.gui.propagation.propagate','emcd_sim.gui.emcd_forward.calculate',
                     'numpy.linalg.eigh'):
            guards.enter_context(patch(name,side_effect=AssertionError('Unexpected solver')))
        w=MainWindow(workspace=tmp_path/'project');w.show();app.processEvents()
        yield w
        w.close();app.processEvents()


def assert_circle(w):
    q=za_from_tilt(w.settings().tilt,w.settings().voltage)
    np.testing.assert_allclose(w._laue_circle.center,q,atol=1e-12)
    assert w._laue_circle.radius==pytest.approx(np.linalg.norm(q))
    np.testing.assert_allclose(np.array(w._za_artist.get_data()).ravel(),q)


def test_zero_tilt_and_checkbox(window):
    w=window;w.set_tilt((0,0));assert_circle(w)
    assert w._laue_circle.radius==0 and not w._laue_circle.get_visible()
    assert 'On zone axis' in w.selection.text()
    w.set_tilt((3,-7));assert_circle(w)
    detectors=w.detectors.copy();hkl=w.current[2];g=w.current[3].copy()
    w.show_laue.setChecked(False)
    assert not w._laue_circle.get_visible() and w._za_artist.get_visible()
    assert w.current[2]==hkl
    np.testing.assert_array_equal(w.current[3],g)
    np.testing.assert_array_equal(w.detectors,detectors)
    w.show_laue.setChecked(True);assert w._laue_circle.get_visible()
    assert w.worker is None and w.last_result is None and not w.history


def test_live_controls_voltage_alignment_and_orientation(window):
    w=window;w.spin['tx'].setValue(5);w.spin['ty'].setValue(-9);assert_circle(w)
    before=np.array(w._laue_circle.center);w.spin['kv'].setValue(200);assert_circle(w)
    assert not np.allclose(before,w._laue_circle.center)
    w.spin['qx'].setValue(.2);w.spin['qy'].setValue(-.3);assert_circle(w)
    np.testing.assert_allclose(w._laue_circle.center,[.2,-.3],atol=1e-10)
    for zone,target in [('0 1 7','2 0 0'),('1 1 7','2 -2 0')]:
        w.zone.setText(zone);w.target.setText(target);w.apply_orientation();w.align();assert_circle(w)
        gg=w.current[3][w.current[2].index(w.settings().target)]
        assert np.linalg.norm(gg-w._laue_circle.center)==pytest.approx(w._laue_circle.radius,abs=1e-10)
    w.reset_reference();assert_circle(w)
    assert w.worker is None


def test_styles_layering_and_viewport(window):
    w=window;w.set_tilt((-6,15));w.ax.set(xlim=(-.5,.9),ylim=(-.7,.7));w.refresh()
    laue=w._laue_circle
    thales=next(p for p in w.ax.patches if p.get_label()=='Thales circle (000–target)')
    assert laue.get_edgecolor()==to_rgba('darkorange',.95)
    assert (laue.get_linestyle(),laue.get_linewidth(),laue.get_alpha())==('--',1.8,.95)
    assert thales.get_edgecolor()==to_rgba('teal',.75)
    assert (thales.get_linestyle(),thales.get_linewidth(),thales.get_alpha())==(':',1.2,.75)
    assert thales.get_zorder()<laue.get_zorder()<min(c.get_zorder() for c in w.ax.collections)
    assert laue.get_zorder()<w._za_artist.get_zorder()
    assert all(p.get_zorder()>laue.get_zorder() for p in w.ax.patches if p not in (thales,laue))
    np.testing.assert_allclose(w.ax.get_xlim(),[-.5,.9]);np.testing.assert_allclose(w.ax.get_ylim(),[-.7,.7])
    w.toggle_basis_view();w.toggle_basis_view()
    np.testing.assert_allclose(w.ax.get_xlim(),[-.5,.9]);assert w.ax.get_aspect()==1
    w.basis_mode.setCurrentIndex(1);assert_circle(w)
    assert len(w.current[2])==2
    assert any(str(w.settings().target)==t.get_text() for t in w.ax.texts)


def mouse(w,name,point,button=1):
    x,y=w.ax.transData.transform(point)
    return MouseEvent(name,w.canvas,x,y,button=button)


def test_click_drag_release_without_rebuild_or_detector_move(window):
    w=window;w.mode.setCurrentIndex(1);w.canvas.draw()
    detectors=w.detectors.copy();w.clicked(mouse(w,'button_press_event',[.12,-.24]))
    np.testing.assert_allclose(w._laue_circle.center,[.12,-.24],atol=1e-10)
    circle=w._laue_circle;marker=w._za_artist;limits=(w.ax.get_xlim(),w.ax.get_ylim())
    with patch.object(w,'refresh',wraps=w.refresh) as refresh:
        w.drag_za(mouse(w,'motion_notify_event',[.21,.18]))
        assert refresh.call_count==0 and w._laue_circle is circle and w._za_artist is marker
        assert_circle(w)
        np.testing.assert_allclose(w._laue_circle.center,[.21,.18],atol=1e-10)
        w.release_za(mouse(w,'button_release_event',[.21,.18]))
        assert refresh.call_count==1
    assert w.drawn_settings==w.settings() and not w._za_drag
    np.testing.assert_allclose((w.ax.get_xlim(),w.ax.get_ylim()),limits)
    np.testing.assert_array_equal(w.detectors,detectors)
    assert w.worker is None and not w.busy


def test_navigation_and_detector_clicks(window):
    w=window;w.mode.setCurrentIndex(1);w.canvas.draw();before=w.settings()
    w.toolbar.pan();w.clicked(mouse(w,'button_press_event',[.2,.1]));assert w.settings()==before
    assert not w._za_drag
    w.toolbar.pan();w.mode.setCurrentIndex(2);w.clicked(mouse(w,'button_press_event',[.2,.1]))
    np.testing.assert_allclose(w.detectors[0],[.2,.1],atol=1e-10);assert_circle(w)
    # A release outside the axes still finalizes the last valid position.
    w.mode.setCurrentIndex(1);w.clicked(mouse(w,'button_press_event',[.1,.1]))
    w.release_za(SimpleNamespace(inaxes=None));assert not w._za_drag


def test_export_visible_styles_and_hidden_overlay(window,tmp_path):
    w=window;w.set_tilt((-6,15));settings=w.settings();detectors=w.detectors.copy()
    for suffix in ('png','svg'):
        path=tmp_path/('diffraction.'+suffix)
        with patch.object(QtWidgets.QFileDialog,'getSaveFileName',return_value=(str(path),'')):
            w.export_plot()
        assert path.stat().st_size>1000
    svg=(tmp_path/'diffraction.svg').read_text(encoding='utf-8')
    assert 'ZOLZ Laue circle (s_g = 0)' in svg and 'Thales circle (000–target)' in svg
    assert '#ff8c00' in svg and '#008080' in svg and 'stroke-dasharray' in svg
    w.show_laue.setChecked(False);path=tmp_path/'hidden.svg'
    with patch.object(QtWidgets.QFileDialog,'getSaveFileName',return_value=(str(path),'')):w.export_plot()
    assert 'ZOLZ Laue circle' not in path.read_text(encoding='utf-8')
    assert w.settings()==settings;np.testing.assert_array_equal(w.detectors,detectors)
