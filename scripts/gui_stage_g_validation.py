"""Focused native source acceptance: one default BW run and saved baselines.

Run in the GUI Python environment, without QT_QPA_PLATFORM=offscreen.
All outputs go into a new directory; existing projects are only read.
"""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback

import numpy as np
from PySide6 import QtCore, QtWidgets

from emcd_sim.gui.app import MainWindow
from emcd_sim.gui.emcd_forward import export_result
from emcd_sim.gui.project_io import load_project, save_project, rerun_reason
from emcd_sim.gui.rc_acceptance import fingerprints
from emcd_sim.gui.runtime import build_info


def compare_arrays(reference, candidate):
    count = 0
    for name in ('angular_maps.npz', 'virtual_detector_eels.npz', 'diffraction_pattern.npz'):
        with np.load(reference/name, allow_pickle=False) as a, np.load(candidate/name, allow_pickle=False) as b:
            assert set(a.files) == set(b.files), name
            for key in a.files:
                np.testing.assert_array_equal(a[key], b[key], err_msg=name+': '+key)
                count += 1
    return count


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--baseline', type=Path, required=True, help='Stage C six-case export folder')
    p.add_argument('--saved-root', type=Path, required=True, help='Stage E folder with *_project and case exports')
    p.add_argument('--resume-project', type=Path, help='Recheck a previously generated reference project without recalculation')
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    protected = {str(f): hashlib.sha256(f.read_bytes()).hexdigest()
                 for f in a.saved_root.rglob('*') if f.is_file()}
    app = QtWidgets.QApplication([])
    w = MainWindow(workspace=a.output/'workspace')
    w.resize(1700, 1050)
    w.show()
    report = dict(build=build_info(), timings={}, cases={}, source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest())
    state = {}

    def fail(message):
        report['error'] = message
        (a.output/'failure.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        app.exit(2)
    w.error = fail
    sys.excepthook = lambda typ, exc, tb: fail(''.join(traceback.format_exception(typ, exc, tb)))

    def idle(callback):
        if w.busy:
            QtCore.QTimer.singleShot(100, lambda: idle(callback))
        else:
            callback()

    def reopened():
        assert fingerprints(w.emcd_result) == state['fingerprints']
        assert not w.busy
        report['save_open_without_forward_rerun'] = True
        r = w.emcd_result
        unavailable = str((a.output/'unavailable/Ni_fm.xmcd').resolve())
        def with_missing_source(m):
            return dict(m, config=replace(m['config'], source=unavailable),
                        metadata=dict(m['metadata'], mdff=dict(m['metadata']['mdff'], source=unavailable)))
        missing = with_missing_source(r)
        missing['methods'] = {name: with_missing_source(m) for name, m in r['methods'].items()}
        save_project(missing, a.output/'missing_source_project')
        missing = load_project(a.output/'missing_source_project')
        assert rerun_reason(missing)
        w.display_saved_result(missing)
        w.use_result_settings()
        assert not w.emcd_button.isEnabled()
        w.eels_view.normalization.mode.setCurrentIndex(2)
        w.eels_view.redraw()
        report['missing_source_view_percentages_rerun_blocked'] = True
        report['missing_source_reason'] = rerun_reason(missing)
        for model in ('xmcd', 'atomic'):
            for method in ('bloch', 'fft-multislice', 'both'):
                case = model+'_'+method
                count = compare_arrays(a.baseline/case, a.saved_root/case)
                saved = load_project(a.saved_root/(case+'_project'))
                w.display_saved_result(saved)
                assert not w.busy
                report['cases'][case] = dict(stage_c_arrays_equal=count, reopened=True)
        assert all(hashlib.sha256(Path(f).read_bytes()).hexdigest() == h for f, h in protected.items())
        report['saved_baselines_unchanged'] = True
        (a.output/'acceptance.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        w.close()
        app.quit()

    def saved():
        w.project_ready.disconnect()
        w.clear_selected()
        w.project_ready.connect(lambda: idle(reopened))
        w.open_project_path(a.output/'reference_saved_project')

    def calculated():
        report['timings']['default_bw_worker_s'] = time.perf_counter()-state['bw_start']
        assert w.run_outcome == 'completed'
        r = w.emcd_result
        export_result(r, a.output/'reference_export')
        report['new_bw_arrays_equal_stage_c'] = compare_arrays(a.baseline/'xmcd_bloch', a.output/'reference_export')
        state['fingerprints'] = fingerprints(r)
        # Use the actual Save Project As action; only dialog selections are supplied.
        from unittest.mock import patch
        with patch.object(QtWidgets.QFileDialog, 'getExistingDirectory', return_value=str(a.output)), \
             patch.object(QtWidgets.QInputDialog, 'getText', return_value=('reference_saved_project', True)):
            w.save_project_action(save_as=True)
        w.project_ready.connect(lambda: idle(saved))

    def previewed():
        report['timings']['preview_worker_s'] = time.perf_counter()-state['preview_start']
        w.preview_mdff()
        assert w.dialogs
        w.dialogs[-1].show()
        app.processEvents()
        w.dialogs[-1].grab().save(str(a.output/'stage_g_xmcd_source.png'))
        w.dialogs[-1].close()
        state['bw_start'] = time.perf_counter()
        w.start_emcd()
        assert w.busy, w.emcd_button.toolTip()

    def begin():
        if a.resume_project:
            r = load_project(a.resume_project)
            state['fingerprints'] = fingerprints(r)
            report['resume_project'] = str(a.resume_project)
            report['new_bw_arrays_equal_stage_c'] = compare_arrays(a.baseline/'xmcd_bloch', a.resume_project.parent/'reference_export')
            report['reference_tilt_mrad'] = list(r['settings'].tilt)
            from emcd_sim.gui.geometry import excitation
            report['s200_inv_angstrom'] = float(excitation(np.asarray(r['metadata']['g'])[r['metadata']['beam_hkl'].index([2, 0, 0])], r['settings'].tilt, 200))
            w.project_ready.connect(lambda: idle(reopened))
            w.open_project_path(a.resume_project)
            return
        w.restore_layout()
        w.reset_reference()
        w.source_path.setText(str(a.source.resolve()))
        w.validate_xmcd()
        w.declaration.setChecked(True)
        w.correction.setChecked(True)
        w.propagation_box.setCurrentIndex(0)
        from emcd_sim.gui.geometry import excitation
        g = w.current[3][w.current[2].index((2, 0, 0))]
        assert abs(excitation(g, w.settings().tilt, 200)) < 1e-12
        assert w.settings().zone == (0, 1, 7)
        report['reference_tilt_mrad'] = list(w.settings().tilt)
        report['s200_inv_angstrom'] = float(excitation(g, w.settings().tilt, 200))
        state['preview_start'] = time.perf_counter()
        w.start_preview()

    w.preview_ready.connect(lambda: idle(previewed))
    w.emcd_ready.connect(lambda: idle(calculated))
    QtCore.QTimer.singleShot(300, begin)
    QtCore.QTimer.singleShot(600000, lambda: fail('Source acceptance timed out'))
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
