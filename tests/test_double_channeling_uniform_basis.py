"""Focused admission, reuse and scientific-gate checks."""
import json,sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import ni_double_channeling_uniform_basis as run


def test_unchanged_thresholds_and_independent_basis_gate():
    assert run.study.TOLERANCES==dict(max_prb_change_pp=.01,max_raw_relative=.001)
    agreement=[dict(prb_change_pp=.005,raw_relative=.0001)]
    unstable_basis=[dict(prb_change_pp=.011,raw_relative=.0001)]
    assert run.passed(agreement)
    assert not run.passed(unstable_basis)
    assert not (run.passed(agreement) and run.passed(unstable_basis))
    assert not run.passed([])
    assert not run.passed([dict(prb_change_pp=0.,raw_relative=.0011)])


def test_completed_case_reused_without_solver_or_modification(monkeypatch):
    path=run.PRIOR/'checkpoints/017_ms_t008_p6.2_b4.6_o4.6_f48_d257_s0.04.npz'
    if not path.exists():pytest.skip('Local completed calculation unavailable')
    before=run.study.base.digest(path)
    def forbidden(*args,**kwargs):raise AssertionError('Completed solver restarted')
    monkeypatch.setattr(run.study,'engine',forbidden)
    actual,data,params=run.case('017',8.,4.6,'ms')
    assert actual==path and run.study.base.digest(path)==before
    assert params['hkl']==params['outgoing_hkl']
    assert data['raw'].dtype==np.float64


def test_exact_fft_beam_support_and_larger_basis_memory():
    rows=run.support()
    assert all(r['matched_support'] for r in rows)
    assert [r['incoming_beams'] for r in rows if r['zone']=='017']==[37,59,81]
    large=next(r for r in rows if r['zone']=='017' and r['basis']==5.4)
    assert not large['dense_alone_within_2048_mib']


def test_saved_states_parity_precision_and_prior_preservation():
    manifest=run.ROOT/'checkpoint_manifest.json'
    if not manifest.exists():pytest.skip('Validation not completed')
    entries=json.loads(manifest.read_text())
    with np.load(run.ROOT/'comparison.npz',allow_pickle=False) as packed:
        assert packed['raw'].dtype==np.float64
        assert len(packed['raw'])==len(entries)
        for index,entry in enumerate(entries):
            assert run.study.base.digest(entry['path'])==entry['sha256']
            with np.load(entry['path'],allow_pickle=False) as f:
                np.testing.assert_array_equal(f['raw'],packed['raw'][index])
                assert np.isfinite(f['raw']).all() and f['raw'].min()>=0
                for raw in f['raw']:
                    o=run.study.base.study.base.observables(raw)
                    np.testing.assert_allclose(o['D_raw'],o['D_mag']+o['D_even'],atol=1e-14)
                np.testing.assert_allclose(f['outgoing_depth_mean'].sum(axis=-1),1,atol=1e-10)
    provenance=json.loads((run.ROOT/'provenance.json').read_text())
    assert run.study.base.study.base.file_hashes(run.PRIOR)==provenance['prior_output_hashes']
    assert run.study.base.digest('data/wien2k_ni/Ni_fm.xmcd')==provenance['source_sha256']
