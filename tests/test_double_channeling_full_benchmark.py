"""Focused full-benchmark extensions, preserving validated channeling conventions."""
from dataclasses import replace
from pathlib import Path
import pytest
import numpy as np
from numpy.testing import assert_allclose
from emcd_sim.double_channeling import equivalent_site_phases,double_channeling_response
from emcd_sim.multislice_double_channeling import ProjectedNiFFT,incident_fields,multislice_double_channeling_response
from emcd_sim.ni_017_geometry import Ni017Geometry
from emcd_sim.multislice_reference import fft_multislice_ni


def test_equivalent_sites_preserve_general_complex_average():
    hi=np.array([[0,0,0],[2,0,0],[1,7,-1]])
    positions=np.array([[0,0,0],[0,.5,.5],[.5,0,.5],[.5,.5,0],[.13,.27,.39]])
    phases,weights=equivalent_site_phases(hi,hi,positions)
    delta=hi[None,:,:]-hi[:,None,:]
    original=np.exp(2j*np.pi*np.einsum('ghc,sc->sgh',delta,positions))
    rng=np.random.default_rng(19);k=rng.normal(size=(3,3))+1j*rng.normal(size=(3,3))
    expected=np.mean([abs(np.sum(k*p))**2 for p in original])
    assert_allclose(sum(w*abs(np.sum(k*p))**2 for p,w in zip(phases,weights)),expected,rtol=1e-13)
    assert_allclose(weights.sum(),1)
    fcc,_=equivalent_site_phases(hi,hi,positions[:4])
    assert len(fcc)==1


def test_017_fft_actual_oriented_potential_and_fields():
    geo=Ni017Geometry();model=geo.model()
    grid=ProjectedNiFFT.build(model.elastic,grid_points=32,potential_cutoff=2.2,projected_geometry=geo)
    fields,z,_,_,_=incident_fields(grid,2.,depth_steps=17)
    old=fft_multislice_ni(z,acceleration_kv=200,tilt_mrad_xy=model.elastic.microscope.tilt_mrad_xy,
        grid_points=32,slice_step_nm=.04,potential_cutoff_inv_angstrom=2.2,
        projected_geometry=geo,return_amplitudes=True)
    assert_allclose(fields,old.amplitudes,atol=3e-14)
    assert_allclose(grid.g,old.reciprocal_xy_inv_angstrom)
    assert np.all(grid.hkl[:,1]+7*grid.hkl[:,2]==0)


def test_017_reflected_response_not_reflected_magnetization():
    geo=Ni017Geometry();model=geo.model(beam_cutoff=2.3)
    q=np.array([[.28,.28],[.28,-.28]])
    bw=double_channeling_response(model.elastic,831.4778,q,2.)
    ms,_=multislice_double_channeling_response(model.elastic,831.4778,q,2.,
        fft_grid=32,potential_cutoff=2.2,depth_steps=33,projected_geometry=geo)
    sign=np.array([1,-1,1]);mirror=sign[:,None]*sign[None,:]
    assert_allclose(bw[1],bw[0]*mirror,atol=1e-13)
    assert_allclose(ms[1],ms[0]*mirror,atol=1e-13)
    assert_allclose(ms,bw,rtol=2e-3,atol=1e-7)


def test_017_numerical_bw_depth_against_analytic_at_long_thickness():
    model=Ni017Geometry().model();q=np.array([[.28376844495,.28376844495],[.28376844495,-.28376844495]])
    for t in (12.,100.):
        analytic=double_channeling_response(model.elastic,831.4778,q,t)
        numerical=double_channeling_response(model.elastic,831.4778,q,t,method='numerical',depth_steps=257)
        assert np.linalg.norm(numerical-analytic)/np.linalg.norm(analytic)<1e-3


def test_atomic_checkpoint_resume_rejects_mismatched_provenance(tmp_path):
    import sys,importlib.util
    from pathlib import Path
    import pytest
    scripts=Path(__file__).resolve().parents[1]/'scripts'
    sys.path.insert(0,str(scripts))
    try:
        import ni_double_channeling_full_benchmark as full
        calls=[]
        def produce():calls.append(1);return dict(raw=np.arange(8,dtype=np.float64),complex=np.array([1+2j]))
        path=tmp_path/'point.npz';params=dict(depth_steps=257,source='verified')
        first=full.cached(path,params,produce)
        second=full.cached(path,params,produce)
        assert len(calls)==1
        assert_allclose(first['raw'],second['raw'],atol=0,rtol=0)
        assert second['raw'].dtype==np.float64 and second['complex'].dtype==np.complex128
        with pytest.raises(ValueError,match='provenance mismatch'):
            full.cached(path,dict(params,depth_steps=513),produce)
    finally:sys.path.remove(str(scripts))


def test_detector_thread_batches_preserve_complex_response():
    import sys
    from pathlib import Path
    scripts=Path(__file__).resolve().parents[1]/'scripts';sys.path.insert(0,str(scripts))
    try:
        from ni_double_channeling_full_benchmark import detector_batches
        model=Ni017Geometry().model(beam_cutoff=2.3)
        q=np.array([[.2,.2],[.28,.28],[.3,.2],[.32,.3],[.23,.21],[.29,.27],[.31,.22],[.33,.31]])
        def evaluate(query):
            return multislice_double_channeling_response(model.elastic,831.4778,query,1.,
                fft_grid=32,potential_cutoff=2.2,depth_steps=9,projected_geometry=Ni017Geometry())
        serial,_=detector_batches(evaluate,q,1)
        parallel,info=detector_batches(evaluate,q,8)
        assert_allclose(serial,parallel,rtol=1e-13,atol=1e-14)
        assert info['detector_workers']==8
    finally:sys.path.remove(str(scripts))


@pytest.mark.skipif(not Path('outputs/gui_stage_d/windows_20261016/reference_project/project.json').is_file(), reason='Requires the original local reference project; not distributed')
def test_larger_systematic_row_is_not_limited_by_parent_gui_preview():
    import sys
    from pathlib import Path
    scripts=Path(__file__).resolve().parents[1]/'scripts';sys.path.insert(0,str(scripts))
    try:
        from ni_double_channeling_full_benchmark import context
        c=context('001',beam_cutoff=3.8)
        assert c['settings'].beam_cutoff==3.8
        assert len(c['hkl'])==13 and (12,0,0) in c['hkl'] and (-12,0,0) in c['hkl']
        assert all(h[1:]==(0,0) for h in c['hkl'])
        assert abs(c['s'][c['hkl'].index((2,0,0))])<1e-12
    finally:sys.path.remove(str(scripts))
