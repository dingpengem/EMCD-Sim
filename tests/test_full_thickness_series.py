"""Final data-only acceptance; no solver recomputation."""
from pathlib import Path
import hashlib,json,csv
import numpy as np
import pytest

ROOT=Path('outputs/ni_emcd_asymmetry_thickness_200kv')


@pytest.fixture
def series():
    progress=ROOT/'progress.json'
    if not progress.exists() or not json.loads(progress.read_text())['complete']:
        pytest.skip('Full checkpointed thickness calculation still incomplete')
    with np.load(ROOT/'thickness_series.npz',allow_pickle=False) as f:
        return json.loads(str(f['keys_json'])),f['raw'].copy(),f['energies_ev'].copy()


def test_all_204_joint_cases_and_zero_boundary(series):
    keys,raw,energies=series
    assert len(keys)==len(set(map(tuple,keys)))==204
    assert set(map(tuple,keys))=={(z,t,e) for z in ('001','017') for t in range(0,101,2) for e in ('bw','ms')}
    np.testing.assert_array_equal(energies,[831.4778,848.698]);assert raw.shape==(204,2,2,4) and raw.dtype==np.float64
    assert np.isfinite(raw).all()
    for key,value in zip(keys,raw):
        if key[1]==0:np.testing.assert_array_equal(value,0)


def test_full_precision_formulas_and_figures(series):
    keys,raw,energies=series
    with (ROOT/'thickness_series.csv').open(newline='') as f:rows=list(csv.DictReader(f))
    assert len(rows)==816
    for row in rows:
        ap,bp,am,bm=[float(row[k]) for k in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus')]
        value=float(row['emcd_asymmetry_percent'])
        if float(row['thickness_nm'])==0:assert np.isnan(value)
        else:np.testing.assert_allclose(value,100*(ap-bp)/(ap+bp),rtol=4e-15,atol=1e-14)
        np.testing.assert_allclose(float(row['D_mag']),((ap-am)-(bp-bm))/2,atol=1e-14)
        np.testing.assert_allclose(float(row['D_nonmag']),((ap+am)-(bp+bm))/2,atol=1e-14)
    assert len(list((ROOT/'figures').glob('*.png')))==12
    assert len(list((ROOT/'figures').glob('*.svg')))==12


def test_reused_files_unchanged_and_comparison_gate_not_relaxed(series):
    for path,digest in json.loads((ROOT/'reuse_manifest.json').read_text()).items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,path
    with (ROOT/'bw_ms_comparison.csv').open(newline='') as f:rows=list(csv.DictReader(f))
    assert len(rows)==400
    summary=json.loads((ROOT/'summary.json').read_text())
    expected=all(abs(float(r['prb_change_pp']))<=.01 and float(r['raw_relative'])<=.001 for r in rows)
    assert summary['numerical_gate_passed']==expected and not summary['global_convergence_certified']
