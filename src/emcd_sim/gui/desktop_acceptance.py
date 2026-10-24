"""Opt-in portable-build acceptance using real Qt widgets and small BW/MS jobs."""
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sys
import time

import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets


def run(output):
    from .app import MainWindow, add_about_menu
    from .runtime import build_info
    from .project_io import fingerprints, load_project, save_project
    from .emcd_forward import export_result
    from .normalization_export import save_figure
    from .parallel_resources import native_backend_info

    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    if not QtGui.QFontDatabase.families():
        from matplotlib import get_data_path
        font = QtGui.QFontDatabase.addApplicationFont(str(Path(get_data_path())/'fonts/ttf/DejaVuSans.ttf'))
        app.setFont(QtGui.QFont(QtGui.QFontDatabase.applicationFontFamilies(font)[0], 9))
    w = MainWindow(output/'workspace')
    info = build_info()
    w.setWindowTitle(info['label'])
    about = add_about_menu(w)
    report = dict(build=info, frozen=bool(getattr(sys, 'frozen', False)), executable=sys.executable,
                  started_utc=datetime.now(timezone.utc).isoformat(), platform=platform.platform(),
                  qt_platform=app.platformName(), native=native_backend_info(), errors=[], cases=[],
                  layout_checks=[], heartbeats=0, clean_machine_tested=False)
    start = time.perf_counter()
    state = dict(stage='boot')

    def write():
        (output/'acceptance.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')

    def fail(message):
        if report.get('complete') or state.get('failed'):
            return
        state['failed'] = True
        report['errors'].append(str(message)); report['complete'] = False
        write()
        if w.busy:
            w.cancel()
        else:
            w.close(); app.exit(2)

    w.error = fail
    previous_hook = sys.excepthook
    sys.excepthook = lambda kind, value, tb: fail(str(value))

    def boot():
        try:
            s = w.settings()
            assert (s.voltage, s.beam_cutoff, s.potential_cutoff) == (300, 3.2, 2.5)
            assert w.spin['grid'].value() == 97 and w.memory_budget.currentData() == 2048
            assert w.worker_mode.currentIndex() == 0
            report['defaults'] = dict(settings=asdict(s), grid=97, memory_budget_mib=2048,
                                      worker_mode='automatic')
            report['screen'] = dict(available=w.screen().availableGeometry().getRect(),
                                    logical_dpi=w.screen().logicalDotsPerInch(),
                                    device_pixel_ratio=w.devicePixelRatioF())
            def dismiss_about():
                box = app.activeModalWidget()
                if not isinstance(box, QtWidgets.QMessageBox):
                    fail('About dialog did not open'); return
                assert info['application_version'] in box.text()
                assert info['display_version'] in box.text()
                report['about_verified'] = True
                box.accept()
            QtCore.QTimer.singleShot(150, dismiss_about)
            about.trigger()
            w.resize(1280, 720)
            QtCore.QTimer.singleShot(250, layout_check)
        except Exception as exc:
            fail(exc)

    def layout_check():
        try:
            assert w.splitter.count() == 3 and not hasattr(w.responsive, 'pages')
            assert all(p.isVisible() for p in w.responsive.panels)
            before = asdict(w.settings())
            tilt = w.spin['tx'].value()
            w.spin['tx'].setValue(tilt + .1)
            assert abs(w.settings().tilt[0] - tilt - .1) < 1e-8
            w.spin['tx'].setValue(tilt)
            step = w.step.currentText(); w.step.setCurrentText('0.01')
            assert w.spin['tx'].singleStep() == .01
            w.step.setCurrentText(step)
            assert asdict(w.settings()) == before
            limits = w.ax.get_xlim(), w.ax.get_ylim()
            w.basis_view_button.click(); w.basis_view_button.click()
            assert (w.ax.get_xlim(), w.ax.get_ylim()) == limits
            body = w.geometry_options.body
            w.geometry_options.header.click(); w.geometry_options.header.click()
            assert w.geometry_options.body is body
            w.splitter.moveSplitter(w.width()//3, 1)
            report['layout_checks'].append(dict(size=w.size().toTuple(), sizes=w.splitter.sizes(),
                                                settings_diffraction_visible=True))
            w.resize(1092, 600)
            QtCore.QTimer.singleShot(250, small_layout)
        except Exception as exc:
            fail(exc)

    def small_layout():
        try:
            assert all(p.isVisible() for p in w.responsive.panels)
            assert w.responsive.panels[0].width() >= 280 and w.responsive.panels[1].width() >= 300
            w.responsive.browser_section.setChecked(True)
            w.responsive.browser_section.setChecked(False)
            assert w.responsive.browser_section.header.isVisible()
            report['layout_checks'].append(dict(size=w.size().toTuple(), sizes=w.splitter.sizes(),
                                                settings_diffraction_visible=True, simulated_geometry=True))
            # Explicit, bounded acceptance settings; never change production defaults.
            w.numerical_mode.setCurrentIndex(1)
            w.set_values(dict(thickness=1, beam=.9, potential=1.8, grid=9, depth=5,
                              energy=9, subpixels=4, fft_grid=24, slice_step=.25))
            w.propagation_box.setCurrentIndex(2); w.energy_scope.setCurrentIndex(1)
            w.declaration.setChecked(True)
            w.refresh()
            report['smoke_profile'] = dict(settings=asdict(w.settings()), config=asdict(w.forward_settings()),
                                           scope='Tiny selected-energy smoke, not a convergence benchmark')
            state['stage'] = 'preview'
            w.start_preview()
            assert w.busy
        except Exception as exc:
            fail(exc)

    def launch_case(channeling):
        w.channeling_box.setCurrentIndex(channeling)
        state.update(stage='calculation', channeling=channeling)
        w.start_emcd()
        assert w.busy, 'Small EMCD worker did not start'

    def tick():
        report['heartbeats'] += 1
        if state.get('failed'):
            if not w.busy and (w.worker is None or not w.worker.isRunning()):
                w.close(); app.exit(2)
            return
        if time.perf_counter() - start > 180:
            fail('Desktop acceptance timeout'); return
        if w.busy or (w.worker is not None and w.worker.isRunning()):
            return
        try:
            if state['stage'] == 'preview':
                assert w.last_result is not None and np.isfinite(w.last_result['intensity']).all()
                report['elastic_preview'] = True
                launch_case(0)
            elif state['stage'] == 'calculation':
                assert w.run_outcome == 'completed', w.run_outcome
                r = w.emcd_result
                assert set(r['methods']) == {'bloch', 'fft-multislice'}
                for method in r['methods'].values():
                    assert np.isfinite(method['spectra']['I_A_plus']).all()
                execution = r['metadata']['execution']
                assert execution['effective_workers']['bloch'] == 1
                before = fingerprints(r)
                folder = output/('single' if state['channeling'] == 0 else 'double')
                save_project(r, folder)
                opened = load_project(folder)
                assert fingerprints(opened) == before
                w.display_saved_result(opened)
                for view in (w.maps_view, w.eels_view):
                    view.component_mode.setCurrentIndex(1); view.component_mode.setCurrentIndex(0)
                assert fingerprints(opened) == before
                save_figure(w.maps_view.figure, output/(folder.name+'_maps.png'))
                save_figure(w.eels_view.figure, output/(folder.name+'_eels.svg'))
                export_result(opened, output/(folder.name+'_exports'))
                report['cases'].append(dict(channeling=folder.name, methods=list(r['methods']),
                                            execution=execution, save_reopen=True, exports=True,
                                            displayed_arrays_unchanged=True, fingerprints=before))
                w.grab().save(str(output/(folder.name+'_completed.png')))
                if state['channeling'] == 0:
                    state['stage'] = 'between'
                    QtCore.QTimer.singleShot(200, lambda: launch_case(1))
                else:
                    state['stage'] = 'done'
                    w.store_ui_preferences(); w.close()
                    report.update(complete=True, closed_cleanly=not w.isVisible(),
                                  elapsed_seconds=time.perf_counter()-start)
                    write(); app.quit()
        except Exception as exc:
            fail(exc)

    w.show()
    timer = QtCore.QTimer(w); timer.timeout.connect(tick); timer.start(25)
    QtCore.QTimer.singleShot(300, boot)
    try:
        code = app.exec()
        return code if report.get('complete') else 2
    finally:
        sys.excepthook = previous_hook
