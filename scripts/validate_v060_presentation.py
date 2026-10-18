"""Opt-in native presentation acceptance using saved calculations only.

Run from the repository root. No numerical workers or packaging are invoked.
"""
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
import json
import sys

from PySide6 import QtWidgets
from emcd_sim.gui.app import MainWindow
from emcd_sim.gui.project_io import load_project
from emcd_sim.gui.rc_acceptance import fingerprints
from emcd_sim.gui.runtime import build_info


def main():
    output = Path(sys.argv[1] if len(sys.argv)>1 else 'outputs/v060_validation/native_presentation')
    output.mkdir(parents=True, exist_ok=False)
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = MainWindow(workspace=output/'workspace')
    window.resize(1600, 1000)
    window.showMaximized()
    window.browser_dock.hide()
    window.eels_view.maximize()
    report = dict(build=build_info(), qt_platform=app.platformName(),
                  screen_dpr=app.primaryScreen().devicePixelRatio(), cases={})
    try:
        with ExitStack() as guards:
            calls = [guards.enter_context(patch(path, side_effect=AssertionError('Display invoked calculation')))
                     for path in ('emcd_sim.gui.stage_b.calculate', 'emcd_sim.gui.emcd_forward.calculate')]
            for model in ('single', 'double'):
                for method in ('bloch', 'fft-multislice', 'both'):
                    name = model+'_'+method
                    result = load_project(Path('outputs/windows_beta_acceptance/source_native')/(name+'_project'))
                    before = fingerprints(result)
                    window.display_saved_result(result)
                    window.eels_view.choice.setCurrentIndex(0)
                    window.eels_view.prb_benchmark.fixed.setChecked(False)
                    window.eels_view.prb_benchmark.selection.setCurrentIndex(1)
                    window.eels_view.prb_benchmark.energy.setValue(result['config'].l3)
                    for view, tab in ((window.eels_view, 2), (window.maps_view, 1)):
                        window.tabs.setCurrentIndex(tab)
                        view.advanced.setChecked(False)
                        for mode in (0, 1):
                            view.component_mode.setCurrentIndex(mode)
                            app.processEvents()
                            if model == 'double' and method == 'both':
                                stem = ('eels' if tab == 2 else 'angular')+'_'+view.component_mode.currentData()
                                view.figure.set_size_inches(12, 7)
                                for ext in ('png', 'svg'):
                                    view.figure.savefig(output/(stem+'.'+ext), dpi=160)
                                window.grab().save(str(output/(stem+'_native.png')))
                    assert fingerprints(result) == before
                    report['cases'][name] = dict(outcome='PASS', fingerprints=before)
            assert sum(c.call_count for c in calls) == 0
            report['forward_calls'] = 0
        report['outcome'] = 'PASS'
    finally:
        (output/'acceptance.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
        window.close()
        app.processEvents()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
