"""Focused final-series provenance and sampled-analysis checks."""
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import ni_double_channeling_final_200kv as run
import ni_double_channeling_final_report as report


def test_zero_thickness_has_zero_raw_and_undefined_percentages():
    path=run.ROOT/'checkpoints/017_bw_t000_p6.2_b4.6_o4.6_f48_d257_s0.04.npz'
    if not path.exists():pytest.skip('No local zero-thickness checkpoint')
    with np.load(path,allow_pickle=False) as f:
        assert f['raw'].dtype==np.float64 and not f['raw'].any()
        for raw in f['raw']:
            obs=run.study.base.study.base.observables(raw)
            for key in ('prb_relative_dichroism_percent','magnetic_only_percent','nonmagnetic_imbalance_percent'):
                assert np.isnan(obs[key]).all()


@pytest.mark.skipif(not Path('outputs/gui_stage_d/windows_20261016/reference_project/project.json').is_file(), reason='Requires the original local reference project; not distributed')
def test_exact_existing_case_never_restarted(monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('Completed engine restarted')
    monkeypatch.setattr(run.study,'engine',forbidden)
    import json
    import ni_emcd_complete_thickness as scan
    original=run.study.base.cached;params={}
    def capture(path,expected,calculate):
        params.update(expected)
        return original(path,expected,calculate)
    monkeypatch.setattr(run.study.base,'cached',capture)
    with pytest.raises(ValueError,match='Checkpoint provenance mismatch'):
        run.case('017',30.,'ms')
    path=run.uniform.ROOT/'checkpoints/017_ms_t030_p6.2_b4.6_o4.6_f48_d257_s0.04.npz'
    with np.load(path,allow_pickle=False) as data:
        aliases,_=scan.implementation_audit()
        assert scan.compatible(json.loads(str(data['parameters_json'])),json.loads(scan.encode(params)),aliases)
        assert data['raw'].shape==(2,2,4)
    assert path.parent.parent==run.uniform.ROOT
    assert params['settings']['potential_cutoff']==6.2
    assert params['settings']['beam_cutoff']==4.6
    assert params['hkl']==params['outgoing_hkl']


def test_sampled_maxima_are_computed_not_hard_coded():
    records={}
    for zone in ('001','017'):
        for engine,times in (('bw',np.arange(2.,101.,2.)),('ms',run.MS_TIMES)):
            for t in times:
                raw=np.empty((2,2,4))
                for im,maximum in enumerate((14.,10.)):
                    signal=np.exp(-((t-maximum)/3)**2)
                    for ie,sign in enumerate((1.,-1.)):
                        m=sign*signal
                        raw[im,ie]=[10+m,10-m,10-m,10+m]
                records[zone,float(t),engine]=raw
    rows,peaks,crossings=report.analyze(records)
    assert all(r['thickness_nm']==(14 if r['channeling_model']=='single' else 10) for r in peaks)
    assert max(abs(r['prb_change_pp']) for r in rows)==0
    assert not crossings


def test_final_raw_and_relative_exports_share_one_denominator():
    path=run.ROOT/'results.npz'
    if not path.exists():pytest.skip('No local final result')
    with np.load(path,allow_pickle=False) as f:
        if 'magnetic_only_percent' not in f:pytest.skip('Final report not yet generated')
        ap,bp,am,bm=np.moveaxis(f['raw'],-1,0)
        denominator=(ap+am+bp+bm)/2
        np.testing.assert_allclose(f['Sigma_ref'],denominator,rtol=3*np.finfo(float).eps)
        np.testing.assert_allclose(f['D_mag'],((ap-am)-(bp-bm))/2,atol=1e-16)
        np.testing.assert_allclose(f['D_nonmag'],((ap+am)-(bp+bm))/2,atol=1e-16)
        valid=denominator>0
        np.testing.assert_allclose(f['magnetic_only_percent'][valid],100*f['D_mag'][valid]/denominator[valid])
        np.testing.assert_allclose(f['nonmagnetic_imbalance_percent'][valid],100*f['D_nonmag'][valid]/denominator[valid])
        assert np.isnan(f['magnetic_only_percent'][~valid]).all()
