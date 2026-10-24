"""Logical-screen layout checks with saved data; no forward calculations."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from contextlib import ExitStack
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
from PySide6 import QtCore, QtGui, QtTest, QtWidgets
from emcd_sim.gui.app import MainWindow
from emcd_sim.gui.responsive import FlowLayout, ResponsiveCanvas, CollapsibleSection


@pytest.fixture(scope='module')
def app():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    if not QtGui.QFontDatabase.families():
        from matplotlib import get_data_path
        font = QtGui.QFontDatabase.addApplicationFont(str(Path(get_data_path())/'fonts/ttf/DejaVuSans.ttf'))
        app.setFont(QtGui.QFont(QtGui.QFontDatabase.applicationFontFamilies(font)[0], 9))
    return app


@pytest.fixture
def window(app, tmp_path):
    with ExitStack() as guards:
        for target in ('emcd_sim.gui.app.preview', 'emcd_sim.gui.app.PreviewWorker.start',
                       'emcd_sim.gui.stage_b.calculate', 'emcd_sim.gui.stage_b.EMCDWorker.start'):
            guards.enter_context(patch(target, side_effect=AssertionError('Layout must not calculate')))
        w = MainWindow(tmp_path/'workspace')
        w.show()
        QtTest.QTest.qWait(250)
        yield w
        w.close()
        app.processEvents()


def resize(w, width, height):
    # Let Qt negotiate the logical geometry and debounce resize renders.
    w.resize(width, max(height, w.height()))
    QtTest.QTest.qWait(160)
    w.resize(width, height)
    QtTest.QTest.qWait(160)


@pytest.mark.parametrize('physical,scale', [
    ((2560,1440),1),((2560,1440),1.25),((2560,1440),1.5),
    ((1920,1080),1),((1920,1080),1.25),((1920,1080),1.5),
    ((1600,900),1),((1600,900),1.25),
    ((1366,768),1),((1366,768),1.25),((1280,720),1)])
def test_logical_screen_sizes(window, physical, scale):
    w = window
    width, height = (int(n/scale) for n in physical)
    # Reserve logical space for taskbar and window frame.
    height -= 60
    resize(w, width, height)
    assert w.size() == QtCore.QSize(width, height)
    assert w.minimumSizeHint().width() <= width
    assert w.minimumSizeHint().height() <= height
    assert w.splitter.count() == 3
    assert not hasattr(w.responsive, 'pages')
    assert all(panel.isVisible() for panel in w.responsive.panels)
    assert w.results_section.isChecked()
    assert w.canvas.width() >= 280
    assert w.canvas.height() >= 160
    assert w.spin['tx'].isVisible() and w.spin['ty'].isVisible() and w.step.isVisible()
    assert w.responsive.panels[0].geometry().right() < w.responsive.panels[1].geometry().left()
    assert w.responsive.panels[0].horizontalScrollBar().maximum()==0


def test_collapsing_preserves_state_without_replot(window):
    w = window
    settings, cfg = asdict(w.settings()), asdict(w.forward_settings())
    detectors = w.detectors.copy()
    w.ax.set(xlim=(-.4,.8), ylim=(-.2,.7))
    limits = w.ax.get_xlim(), w.ax.get_ylim()
    artists = list(w.ax.lines), list(w.ax.patches), list(w.ax.texts)
    widgets = [*w.responsive.panels, w.browser, w.canvas, w.eels_view.canvas]
    with patch.object(w, 'refresh', side_effect=AssertionError('Resize replot')), \
         patch.object(w.eels_view, 'redraw', side_effect=AssertionError('Resize results replot')):
        for width in (1920, 1093, 1920, 1280):
            resize(w, width, 800 if width >= 1500 else 600)
    assert widgets == [*w.responsive.panels, w.browser, w.canvas, w.eels_view.canvas]
    assert (w.ax.get_xlim(), w.ax.get_ylim()) == limits
    assert (list(w.ax.lines), list(w.ax.patches), list(w.ax.texts)) == artists
    assert w.ax.get_aspect() == 1
    assert asdict(w.settings()) == settings and asdict(w.forward_settings()) == cfg
    np.testing.assert_array_equal(w.detectors, detectors)
    w.store_ui_preferences()
    assert len(w.ui_settings.value('splitter')) == 3
    w.restore_layout()
    assert not w.responsive.browser_section.isChecked()
    w.responsive.show_panel(3)
    assert w.responsive.browser_section.isChecked() and not w.browser_dock.isHidden()


def test_screen_fit_and_flow(window):
    w = window
    class Screen:
        def availableGeometry(self):
            return QtCore.QRect(1920, 0, 1093, 574)
    resize(w, 1920, 1000)
    w.responsive.fit_screen(Screen())
    QtTest.QTest.qWait(180)
    w.responsive.fit_screen(Screen())
    assert Screen().availableGeometry().contains(w.frameGeometry())
    layout = FlowLayout()
    host = QtWidgets.QWidget()
    host.setLayout(layout)
    buttons = [QtWidgets.QPushButton('Button '+str(i)) for i in range(3)]
    for button in buttons:layout.addWidget(button)
    host.show()
    assert layout.heightForWidth(100) > layout.heightForWidth(400)
    host.close()


def test_compact_maximize_restores_controls(window):
    w=window
    resize(w,1093,600)
    w.tabs.setTabEnabled(2,True);w.tabs.setCurrentIndex(2);w.responsive.show_panel(2)
    QtTest.QTest.qWait(160)
    view=w.eels_view
    before=view.canvas.height()
    view.maximize();QtTest.QTest.qWait(160)
    assert view.canvas.height()>before
    assert view.benchmark_section.isHidden()
    view.maximize();QtTest.QTest.qWait(160)
    assert not view.benchmark_section.isHidden()
    assert not view.details_toggle.isChecked()


def test_narrow_fallback_keeps_settings_and_diffraction(window):
    resize(window,950,620)
    assert window.splitter.count()==3
    assert not window.results_section.isChecked()
    assert all(p.isVisible() for p in window.responsive.panels)
    assert window.responsive.panels[0].width()>=280
    assert window.responsive.panels[1].width()>=300
    window.results_section.header.click()
    QtTest.QTest.qWait(160)
    assert window.results_section.isChecked() and window.tabs.isVisible()
    resize(window,1600,900)
    assert window.results_section.isChecked()
    window.results_section.header.click()
    resize(window,1920,1020)
    assert not window.results_section.isChecked()  # Explicit user choice wins.


def test_sections_release_space_without_rebuilding(window):
    w=window
    resize(w,1366,708)
    controller=w.responsive
    controller.browser_section.setChecked(True)
    QtTest.QTest.qWait(160)
    before=w.canvas.height()
    controller.browser_section.header.click()
    QtTest.QTest.qWait(160)
    assert w.canvas.height()>before
    assert controller.browser_section.header.isVisible()
    assert w.browser.isHidden()
    controller.browser_section.header.click()
    QtTest.QTest.qWait(160)
    assert w.browser.isVisible()
    w.tabs.setTabEnabled(2,True);w.tabs.setCurrentIndex(2)
    view=w.eels_view
    view.details_section.setChecked(True)
    QtTest.QTest.qWait(160)
    before=view.canvas.height()
    view.details_section.header.click()
    QtTest.QTest.qWait(160)
    assert view.canvas.height()>before
    for section in w.findChildren(CollapsibleSection):
        body=section.body
        state=section.isChecked()
        section.setChecked(not state)
        assert section.body is body
        assert body.isHidden()==state
        assert section.header.arrowType()==(QtCore.Qt.ArrowType.RightArrow if state else QtCore.Qt.ArrowType.DownArrow)
        section.setChecked(state)


def test_splitter_and_section_preferences_persist(window,app):
    w=window
    resize(w,1920,1020)
    w.splitter.moveSplitter(620,1)
    QtTest.QTest.qWait(160)
    proportions=w.responsive.proportions.copy()
    resize(w,1366,708)
    np.testing.assert_allclose(w.responsive.proportions,proportions)
    w.geometry_options.setChecked(True)
    w.responsive.browser_section.setChecked(False)
    w.maps_view.details_section.setChecked(True)
    w.eels_view.prb_benchmark.options_section.setChecked(True)
    w.results_section.setChecked(False)
    w.store_ui_preferences()
    reopened=MainWindow(w.workspace)
    try:
        reopened.show();QtTest.QTest.qWait(250)
        np.testing.assert_allclose(reopened.responsive.proportions,proportions)
        assert reopened.geometry_options.isChecked()
        assert not reopened.responsive.browser_section.isChecked()
        assert reopened.maps_view.details_section.isChecked()
        assert reopened.eels_view.prb_benchmark.options_section.isChecked()
        assert not reopened.results_section.isChecked()
        assert all(p.isVisible() for p in reopened.responsive.panels)
        assert asdict(reopened.settings())==asdict(w.settings())
        reopened.responsive.reset();reopened.store_ui_preferences()
        assert not reopened.ui_settings.contains('layout/results_expanded')
    finally:
        reopened.close();app.processEvents()


def test_invalid_preferences_fall_back(window,app,tmp_path):
    root=tmp_path/'bad_preferences';root.mkdir()
    q=QtCore.QSettings(str(root/'ui.ini'),QtCore.QSettings.Format.IniFormat)
    for key,value in [('geometry','invalid'),('state',42),('splitter',['bad']),
                      ('layout/proportions',['nan',-1,0]),('layout/results_expanded','invalid'),
                      ('layout/sections/geometry_options','maybe')]:
        q.setValue(key,value)
    q.sync()
    other=MainWindow(root)
    try:
        other.show();QtTest.QTest.qWait(250)
        assert other.splitter.count()==3
        np.testing.assert_allclose(other.responsive.proportions,[.30,.35,.35])
        assert all(p.isVisible() for p in other.responsive.panels)
        assert not other.geometry_options.isChecked()
    finally:
        other.close();app.processEvents()


def test_resize_renders_are_coalesced(app):
    from matplotlib.figure import Figure
    canvas=ResponsiveCanvas(Figure())
    canvas.show();QtTest.QTest.qWait(200)
    with patch.object(canvas,'draw',wraps=canvas.draw) as draw:
        for width in range(700,750,5):
            canvas.resize(width,400)
            app.processEvents()
        assert draw.call_count==0
        QtTest.QTest.qWait(180)
        assert draw.call_count==1
        canvas.draw_idle();app.processEvents()
        assert draw.call_count==2  # Explicit content updates are not delayed.
    canvas.close()


def test_saved_results_resize_and_project_roundtrip(window, tmp_path):
    from emcd_sim.gui.project_io import load_project, save_project
    saved = Path('outputs/windows_beta_acceptance/source_native/double_both_project')
    if not (saved/'project.json').exists():
        pytest.skip('Saved BW/MS fixture not available; never run a fallback simulation')
    result = load_project(saved)
    before = {method:{key:value.copy() for key,value in data['spectra'].items()}
              for method,data in result['methods'].items()}
    w = window
    w.display_saved_result(result)
    maps=w.maps_view
    w.tabs.setCurrentIndex(1)
    resize(w,1092,660)
    images=[ax for ax in maps.figure.axes if ax.images]
    assert len(images)==2
    assert [ax.get_subplotspec().rowspan.start for ax in images]==[0,1]
    arrays=[np.array(ax.images[0].get_array(),copy=True) for ax in images]
    original_title=maps.presentation.full_title
    compact_title=maps.figure._suptitle.get_text()
    assert compact_title!=original_title and maps.full_caption.text()==original_title
    size=maps.figure.get_size_inches().copy()
    limits=[(ax.get_xlim(),ax.get_ylim()) for ax in images]
    with patch.object(maps,'redraw',side_effect=AssertionError('Export must not rebuild')):
        maps.figure.savefig(tmp_path/'compact_export.png')
    assert (tmp_path/'compact_export.png').is_file()
    assert maps.figure._suptitle.get_text()==compact_title
    np.testing.assert_allclose(maps.figure.get_size_inches(),size)
    assert [ax for ax in maps.figure.axes if ax.images]==images
    assert [(ax.get_xlim(),ax.get_ylim()) for ax in images]==limits
    for ax,value in zip(images,arrays):np.testing.assert_array_equal(ax.images[0].get_array(),value)
    axes = list(w.eels_view.figure.axes)
    with patch.object(w.eels_view, 'redraw', side_effect=AssertionError('Resize replot')):
        for width in (1093, 1920, 1280):
            resize(w, width, 900 if width >= 1500 else 600)
        assert list(w.eels_view.figure.axes) == axes
        assert w.emcd_result is result and w.eels_view.result is result
    save_project(result, tmp_path/'roundtrip')
    restored = load_project(tmp_path/'roundtrip')
    for method, fields in before.items():
        for key, value in fields.items():
            np.testing.assert_array_equal(result['methods'][method]['spectra'][key], value)
            np.testing.assert_array_equal(restored['methods'][method]['spectra'][key], value)
