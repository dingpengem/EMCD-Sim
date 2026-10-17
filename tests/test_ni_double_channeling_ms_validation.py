"""Focused checks of the local four-point FFT double-channel validation outputs."""
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
from numpy.testing import assert_allclose
import pytest

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/ni_double_channeling_ms_validation'
pytestmark=pytest.mark.skipif(not (OUT/'angular_maps.npz').exists(),reason='Local MS validation outputs not generated')


def records(name):return list(csv.DictReader((OUT/name).open()))


def test_saved_raw_intensities_and_reversal_components():
    rows=records('results.csv')
    assert len(rows)==32
    for r in rows:
        ap,bp,am,bm=[float(r[k]) for k in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus')]
        assert min(ap,bp,am,bm)>0
        assert_allclose(float(r['prb_relative_dichroism_percent']),100*(ap-bp)/(ap+bp),rtol=1e-12)
        assert_allclose(float(r['D_mag']),((ap-am)-(bp-bm))/2,atol=1e-16)
        assert_allclose(float(r['D_even']),((ap+am)-(bp+bm))/2,atol=1e-16)
        assert abs(float(r['nonmagnetic_imbalance_percent']))<1e-10
    assert max(float(x['max_raw_abs_error']) for x in records('legacy_reproduction.csv'))<1e-15


def test_matched_bw_ms_raw_and_magnetic_difference_agreement():
    data=records('discrepancies.csv')
    assert len(data)==16
    for d in data:
        assert float(d['max_raw_symmetric_relative'])<1e-4
        assert float(d['prb_relative_dichroism_percent_absolute'])<.001
        assert float(d['D_mag_relative'])<.001
        assert np.isnan(float(d['D_even_relative']))
    meta=json.loads((OUT/'configuration.json').read_text())
    assert meta['bw_reference']['verified'] and meta['bw_reference']['primary_bw_reused']
    assert not meta['postedge_normalized']
    assert meta['parameters']['eta']==meta['parameters']['beta']==1


def test_controlled_convergence_norms_and_memory():
    controls={r['control']:r for r in records('convergence.csv')}
    for name in ('slice_half','depth_double','fft48','basis13'):
        assert float(controls[name]['max_raw_symmetric_relative'])<1e-4
        assert float(controls[name]['max_prb_difference_pp'])<.001
    # Raising the physical potential cutoff adds actual Fourier harmonics.
    assert float(controls['potential_2p6']['max_prb_difference_pp'])>.01
    for point in json.loads((OUT/'performance.json').read_text()):
        for d in point['diagnostics']:
            assert max(d['incoming_norm_error'],d['outgoing_norm_error'])<1e-12
            assert max(d['incoming_max_excluded_population'],d['outgoing_max_excluded_population'])<1e-6
            assert d['memory_admission']['memory_budget_mib']==2048
            assert d['memory_admission']['estimated_process_peak_mib']<512
    basis=records('controlled_basis_comparison.csv')
    assert len(basis)==2
    assert all(float(r['max_raw_relative'])<1e-4 for r in basis)


def test_figures_source_and_previous_outputs_preserved():
    assert len(list(OUT.glob('figure_*.png')))==7
    assert len(list(OUT.glob('figure_*.svg')))==7
    meta=json.loads((OUT/'configuration.json').read_text())
    for path,digest in meta['implementation_sha256'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest
    preservation=json.loads((OUT/'preservation.json').read_text())
    assert preservation['source_unchanged'] and preservation['previous_outputs_unchanged']
    for mapping in preservation['reference_hashes'].values():
        for path,digest in mapping.items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest
