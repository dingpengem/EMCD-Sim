"""Focused study-contract checks; no full series is calculated by tests."""
import importlib.util
import json
from pathlib import Path
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ni_017_thickness_scan', ROOT/'scripts/ni_017_thickness_scan.py')
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)


def test_sequence_and_fixed_energies():
    t = study.thickness_sequence()
    assert len(t) == 51 and t[0] == 0 and t[-1] == 100
    np.testing.assert_array_equal(np.diff(t), np.full(50, 2.))
    np.testing.assert_array_equal(study.ENERGIES, [831.4778, 848.698])


def test_original_state_definitions_and_reversal():
    raw = np.array([[.65, .38, .55, .42], [.55, .45, .55, .45]])
    before = raw.tobytes()
    v = study.observables(raw)
    assert v['prb_relative_dichroism_percent'][0] == pytest.approx(100*.27/1.03)
    assert v['magnetic_only_percent'][0] == pytest.approx(7.)
    assert v['nonmagnetic_imbalance_percent'][0] == pytest.approx(20.)
    reverse = study.observables(raw[:, [2, 3, 0, 1]])
    np.testing.assert_allclose(reverse['D_mag'], -v['D_mag'])
    np.testing.assert_allclose(reverse['D_even'], v['D_even'])
    assert raw.tobytes() == before


def test_zero_thickness_intensities_and_undefined_percentages():
    values = study.observables(np.zeros((2, 4)))
    for key in study.METRICS:
        assert np.isnan(values[key]).all()
    for key in ('I_A_plus', 'I_B_plus', 'I_A_minus', 'I_B_minus', 'raw_denominator', 'diagnostic_denominator'):
        assert (values[key] == 0).all()


OUTPUT = ROOT/'outputs/ni_017_thickness_0_100nm'


@pytest.mark.skipif(not (OUTPUT/'thickness_series.npz').exists(), reason='Completed study output unavailable')
def test_actual_study_arrays_metadata_and_saved_reference():
    with np.load(OUTPUT/'thickness_series.npz', allow_pickle=False) as data:
        np.testing.assert_array_equal(data['requested_thickness_nm'], study.thickness_sequence())
        np.testing.assert_array_equal(data['fixed_energies_ev'], study.ENERGIES)
        cfg = json.loads(str(data['configuration_json']))
        assert cfg['configuration']['eta'] == cfg['configuration']['beta'] == 1
        assert cfg['source_unchanged'] and cfg['original_project_files_unchanged']
        assert not cfg['post_edge_correction_applied']
        assert cfg['integration'] == 'fractional'
        np.testing.assert_allclose(data['detector_centers'], [[.283768445, .283768445], [.283768445, -.283768445]], atol=1e-9, rtol=0)
        np.testing.assert_allclose(data['weights'][0], data['weights'][1, ::-1, :], atol=0, rtol=0)
        hkl = data['beam_hkl']
        assert len(hkl) == 27
        assert np.all(hkl[:, 1]+7*hkl[:, 2] == 0)
        assert abs(data['excitation_errors_inv_angstrom'][np.all(hkl == [2, 0, 0], axis=1)][0]) < 1e-10
        for method, expected in zip(study.METHODS, [-.36256677804412213, -.3626967649009784]):
            np.testing.assert_array_equal(data[method+'__actual_thickness_nm'], data['requested_thickness_nm'])
            y = data[method+'__prb_relative_dichroism_percent']
            assert np.isnan(y[0]).all()
            assert np.isfinite(y[1:]).all()
            assert y[15, 0] == pytest.approx(expected, abs=1e-9)
            raw = np.stack([data[method+'__'+k] for k in ('I_A_plus', 'I_B_plus', 'I_A_minus', 'I_B_minus')], axis=-1)
            assert (raw[0] == 0).all() and (raw[1:] >= 0).all()
            np.testing.assert_allclose(y[1:], 100*(raw[1:, :, 0]-raw[1:, :, 1])/(raw[1:, :, 0]+raw[1:, :, 1]))
            np.testing.assert_allclose(data[method+'__D_raw'], data[method+'__D_mag']+data[method+'__D_even'], atol=1e-14)
