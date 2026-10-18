"""Focused checks of numerical controls; no changes to scattering physics."""
import sys
from pathlib import Path
import numpy as np
import pytest
from numpy.testing import assert_allclose
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import ni_double_channeling_cutoff_study as run


@pytest.mark.skipif(not Path('outputs/gui_stage_d/windows_20261016/reference_project/project.json').is_file(), reason='Requires the original local reference project; not distributed')
def test_context_preserves_geometry_tensor_and_detector():
    for zone in ('001','017'):
        old=run.base.context(zone)
        enlarged=run.context(zone,6.2,4.6)
        assert enlarged['hkl'][0]==(0,0,0)
        assert len(enlarged['hkl'])>len(old['hkl'])
        assert abs(enlarged['s'][enlarged['hkl'].index((2,0,0))])<1e-12
        assert_allclose(enlarged['centers'],old['centers'],atol=0,rtol=0)
        assert_allclose(enlarged['R'],old['R'],atol=0,rtol=0)
        for a,b in zip(enlarged['ts'],old['ts']):
            assert_allclose(a.tensor_angstrom2_per_ev,b.tensor_angstrom2_per_ev,atol=0,rtol=0)
        if zone=='017':assert all(h[1]+7*h[2]==0 for h in enlarged['hkl'])


@pytest.mark.skipif(not Path('outputs/gui_stage_d/windows_20261016/reference_project/project.json').is_file(), reason='Requires the original local reference project; not distributed')
def test_ladder_has_actual_fft_support_and_rejects_insufficient_mesh():
    c=run.context('017',6.2,4.6)
    grid=run.ProjectedNiFFT.build(c['model'].elastic,grid_points=48,potential_cutoff=6.2,projected_geometry=c['projected_geometry'])
    assert len(grid.indices(c['hkl']))==len(c['hkl'])
    with pytest.raises(ValueError,match='misses physical oriented harmonics'):
        run.ProjectedNiFFT.build(c['model'].elastic,grid_points=32,potential_cutoff=6.2,projected_geometry=c['projected_geometry'])


def test_signed_comparison_uses_integrated_raw_states():
    a=np.array([[[2.,1.,1.,2.],[3.,2.,2.,3.]],[[4.,3.,3.,4.],[5.,4.,4.,5.]]])
    b=a.copy();b[1,0,0]+=.1
    m=run.comparison(a,b)['double_L3']
    assert_allclose(m['prb_change_pp'],100*(4.1-3)/7.1-100/7)
    assert_allclose(m['raw_relative'],.1/4.1)
    assert_allclose(m['D_mag_change'],.05)
    assert run.TOLERANCES==dict(max_prb_change_pp=.01,max_raw_relative=.001)


def test_saved_study_precision_parity_populations_and_provenance():
    paths=list((run.ROOT/'checkpoints').glob('*.npz'))
    if not paths:pytest.skip('No local study data')
    for path in paths:
        with np.load(path,allow_pickle=False) as f:
            assert f['raw'].dtype==np.float64 and np.isfinite(f['raw']).all()
            assert f['raw'].min()>=0
            for raw in f['raw']:
                o=run.base.study.base.observables(raw)
                assert_allclose(o['D_raw'],o['D_mag']+o['D_even'],atol=1e-14)
            assert_allclose(f['outgoing_depth_mean'].sum(axis=-1),1,atol=1e-10)
            assert_allclose(f['outgoing_entrance'].sum(axis=-1),1,atol=1e-10)


def test_scheduler_only_change_reuses_completed_case_without_propagation(monkeypatch):
    path=run.ROOT/'checkpoints/001_bw_t008_p2.2_b3.8_o3.8_f48_d257_s0.04.npz'
    if not path.exists():pytest.skip('No local completed checkpoint')
    assert run.SCHEDULER_ONLY_EQUIVALENCE
    before=run.base.digest(path)
    def forbidden(*args,**kwargs):raise AssertionError('Completed propagation restarted')
    monkeypatch.setattr(run,'engine',forbidden)
    _,data,_=run.run_case('001',8.,cutoff=2.2,which='bw')
    assert data['raw'].shape==(2,2,4) and run.base.digest(path)==before
