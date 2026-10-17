"""Focused raw-detector PRB readout tests; no simulations or fitted factors."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from contextlib import ExitStack
import csv
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest

from emcd_sim.gui.prb_benchmark import relative_dichroism_percent, benchmark_readout, benchmark_spectra


def result():
    e = np.arange(101., 131.)
    a, b = np.full(30, .55), np.full(30, .45)
    a[7], b[7] = .9, .1       # Largest dichroism, NOT the white-line maximum.
    a[8], b[8] = 1.1, .9     # Maximum original +M sum at 109 eV.
    am, bm = a.copy(), b.copy()
    am[7], bm[7] = 3., 3.    # Reversal-even maximum differs from +M maximum.
    config = SimpleNamespace(l3=108., l2=122., centers=((.25, .25), (.25, -.25)), radius=.08,
                             model='xmcd', source_sha256='source', magnetization=(0, 0, 1), eta=1., beta=1.)
    settings = SimpleNamespace(zone=(0, 1, 7), target=(2, 0, 0), tilt=(-7., 0.), voltage=200., thickness=30.)
    return dict(spectra=dict(energy_ev=e, I_A_plus=a, I_B_plus=b, I_A_minus=am, I_B_minus=bm),
                config=config, settings=settings, method='bloch', metadata=dict(beam_hkl=[[2, 0, 0]], g=[[.5, 0]]))


@pytest.mark.parametrize('a,b,expected', [(.55, .45, 10), (.45, .55, -10), (5.5, 4.5, 10), (.5, .5, 0)])
def test_definition_sign_scaling_equal(a, b, expected):
    value, metadata = relative_dichroism_percent(a, b)
    assert float(value) == pytest.approx(expected)
    assert 'no factor 2' in metadata['definition']


def test_invalid_and_near_zero_are_undefined():
    value, _ = relative_dichroism_percent([0, np.nan, -1, 1e-20, .55], [0, 1, -2, 1e-20, .45])
    assert np.isnan(value[:4]).all()
    assert value[4] == pytest.approx(10)
    overflow, _ = relative_dichroism_percent(1e308, 1e308)
    assert np.isnan(overflow)


def test_peak_is_original_plus_sum_not_even_peak_or_largest_ratio():
    r = result()
    b = benchmark_readout(r)
    assert b['evaluation_energy_ev'] == 109
    assert b['prb_relative_dichroism_percent'] == pytest.approx(10)
    r['spectra'].update(D_raw=np.full(30, 99.), Sigma_ref=np.full(30, 123.), D_corrected=np.full(30, -456.))
    assert benchmark_readout(r)['prb_relative_dichroism_percent'] == b['prb_relative_dichroism_percent']


def test_selected_nearest_sample_and_reported_energy_no_maximization():
    r = result()
    b = benchmark_readout(r, selection='selected', energy_ev=108.5)
    assert b['evaluation_energy_ev'] == 108
    assert b['requested_energy_ev'] == 108.5
    assert b['prb_relative_dichroism_percent'] == pytest.approx(80)
    with pytest.raises(ValueError, match='range'):
        benchmark_readout(r, selection='selected', energy_ev=99.)
    with pytest.raises(ValueError, match='L3 window'):
        benchmark_readout(r, windows={'L3': (100., 110.)})


def test_reversal_diagnostics_are_algebraically_distinct():
    r = result()
    for k, value in [('I_A_plus', .65), ('I_B_plus', .38), ('I_A_minus', .55), ('I_B_minus', .42)]:
        r['spectra'][k] = np.full(30, value)
    b = benchmark_readout(r, selection='selected')
    assert b['magnetic_only_percent'] == pytest.approx(7)
    assert b['nonmagnetic_imbalance_percent'] == pytest.approx(20)
    assert b['prb_relative_dichroism_percent'] == pytest.approx(100*.27/1.03)
    assert b['prb_relative_dichroism_percent'] != pytest.approx(27)
    assert '[0, 1, 7]' in b['geometry_mismatches'][0]


def test_zero_peak_and_missing_reversal_do_not_invent_values():
    r = result()
    r['spectra'].pop('I_A_minus')
    r['spectra'].pop('I_B_minus')
    b = benchmark_readout(r)
    assert b['magnetic_only_percent'] is None
    assert 'diagnostic_unavailable_reason' in b
    r['spectra']['I_A_plus'][:] = 0
    r['spectra']['I_B_plus'][:] = 0
    b = benchmark_readout(r)
    assert b['prb_relative_dichroism_percent'] is None
    assert b['undefined_reason']


def test_raw_arrays_unchanged():
    r = result()
    before = {k: v.tobytes() for k, v in r['spectra'].items()}
    for selection in ('l3-peak', 'selected'):
        benchmark_readout(r, selection=selection)
    assert before == {k: v.tobytes() for k, v in r['spectra'].items()}


@pytest.fixture
def app():
    pytest.importorskip('PySide6')
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_fixed_energy_across_loaded_conditions(app):
    from emcd_sim.gui.prb_controls import PRBBenchmarkControls
    w = PRBBenchmarkControls()
    first = result()
    w.set_context(first, 'bloch', None, 108.)
    assert w.records[0]['evaluation_energy_ev'] == 109
    w.fixed.setChecked(True)
    second = result()
    second['settings'].thickness = 10.
    second['spectra']['I_A_plus'][9] = 10.
    w.set_context(second, 'bloch', None, 108.)
    assert w.records[0]['evaluation_energy_ev'] == 109
    assert w.records[0]['thickness_nm'] == 10
    w.fixed.setChecked(False)
    w.selection.setCurrentIndex(0)
    assert w.records[0]['evaluation_energy_ev'] == 110
    w.close()


SAVED = Path(__file__).resolve().parents[1]/'outputs/gui_stage_d/windows_20261016/reference_project'


@pytest.mark.skipif(not SAVED.is_dir(), reason='Optional real saved Ni project unavailable')
def test_saved_gui_modes_export_and_no_forward_calls(app, tmp_path):
    from emcd_sim.gui.app import MainWindow
    from emcd_sim.gui.project_io import load_project
    from emcd_sim.gui.stage_f_acceptance import FORWARD_PATHS, fingerprints
    from emcd_sim.gui.normalization_export import export_derived, save_figure
    with ExitStack() as guards:
        mocks = [guards.enter_context(patch(name, side_effect=AssertionError('Readout invoked forward calculation'))) for name in FORWARD_PATHS]
        r = load_project(SAVED)
        original = fingerprints(r)
        w = MainWindow(workspace=tmp_path/'workspace')
        w.display_saved_result(r)
        view = w.eels_view
        assert view.prb_benchmark.records[0]['prb_relative_dichroism_percent'] == pytest.approx(-.36256677804412213)
        assert view.prb_benchmark.records[0]['data_origin'] == 'saved project'
        for mode in range(3):
            view.normalization.mode.setCurrentIndex(mode)
            view.redraw()
            before = [line.get_xydata().tobytes() for ax in view.figure.axes for line in ax.lines]
            view.prb_benchmark.selection.setCurrentIndex(1)
            view.prb_benchmark.energy.setValue(831.271)
            assert before == [line.get_xydata().tobytes() for ax in view.figure.axes for line in ax.lines]
            assert view.prb_benchmark.records[0]['prb_relative_dichroism_percent'] == pytest.approx(-.3795858419227595)
        entries = [(name, m, name) for name, m in r['methods'].items()]
        export_derived(entries, tmp_path/'derived', view.normalization.settings(), prb_options=view.prb_benchmark.options())
        meta = json.loads((tmp_path/'derived/normalization_metadata.json').read_text())
        assert meta['records'][0]['prb_2007_benchmark']['data_origin'] == 'saved project'
        with (tmp_path/'derived/prb_2007_benchmark.csv').open(newline='') as f:
            rows = list(csv.DictReader(f))
        assert float(rows[0]['prb_relative_dichroism_percent']) == pytest.approx(-.3795858419227595)
        with np.load(tmp_path/'derived/derived_and_raw.npz', allow_pickle=False) as arrays:
            assert arrays['run0__raw__I_A_plus'].tobytes() == r['spectra']['I_A_plus'].tobytes()
        save_figure(view.figure, tmp_path/'benchmark.svg')
        exported = json.loads((tmp_path/'benchmark.svg.json').read_text())
        assert exported['prb_2007_benchmark']['values'][0]['evaluation_energy_ev'] == 831.271
        assert fingerprints(r) == original
        assert sum(m.call_count for m in mocks) == 0
        w.close()
