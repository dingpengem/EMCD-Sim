"""Focused actual-kernel dispatch, parity, memory and compatibility checks."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from dataclasses import replace,asdict
from unittest.mock import patch
import numpy as np
import pytest
from emcd_sim.gui import emcd_forward as forward
from emcd_sim.gui.geometry import Structure,Settings,geometry
from emcd_sim.gui.project_io import config_from_dict,save_project,load_project
from emcd_sim.gui.propagation import numerical_info


@pytest.fixture
def small():
    return Structure.nickel(),Settings(thickness=8,beam_cutoff=.9,potential_cutoff=1.8),forward.ForwardSettings(
        axis_declared=True,energy_scope='edges',angular_maps=False,grid=17,depth=17,subpixels=16,fft_grid=24,correction=False)


@pytest.mark.parametrize('propagation',['bloch','fft-multislice','both'])
@pytest.mark.parametrize('channel',['single','double'])
def test_six_routes_use_actual_kernels(small,propagation,channel):
    s,settings,cfg=small
    from emcd_sim.gui import channeling
    with patch.object(channeling,'double_channeling_response',wraps=channeling.double_channeling_response) as bw,patch.object(channeling,'multislice_double_channeling_response',wraps=channeling.multislice_double_channeling_response) as ms:
        r=forward.calculate(s,settings,replace(cfg,propagation=propagation,channeling_model=channel))
    assert set(r['methods'])==({'bloch','fft-multislice'} if propagation=='both' else {propagation})
    assert bool(bw.call_count)==(channel=='double' and propagation in ('bloch','both'))
    assert bool(ms.call_count)==(channel=='double' and propagation in ('fft-multislice','both'))
    for method,m in r['methods'].items():
        sp=m['spectra']
        assert m['metadata']['channeling_model']==channel and m['metadata']['solver'].startswith(method)
        assert not m['maps']
        assert min(sp[k].min() for k in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus'))>=0
        np.testing.assert_allclose(sp['D_raw'],sp['D_mag']+sp['D_nonmag'],atol=1e-15)
        np.testing.assert_allclose(sp['magnetic_only_percent'],100*sp['D_mag']/sp['Sigma_ref'])


def test_legacy_default_and_double_roundtrip(small):
    from pathlib import Path
    from uuid import uuid4
    tmp_path=Path('outputs')/('gui_double_roundtrip_'+uuid4().hex)
    old=asdict(small[2])
    for k in ('channeling_model','energy_scope','angular_maps','systematic_row'):old.pop(k)
    assert config_from_dict(old).channeling_model=='single'
    r=forward.calculate(*small[:2],replace(small[2],channeling_model='double'))
    save_project(r,tmp_path/'project');loaded=load_project(tmp_path/'project')
    assert loaded['config'].channeling_model=='double' and not loaded['maps']
    for k,v in r['spectra'].items():np.testing.assert_array_equal(v,loaded['spectra'][k])


def test_detector_only_matches_legacy_full_maps(small):
    s,settings,cfg=small
    a=forward.calculate(s,settings,cfg);b=forward.calculate(s,settings,replace(cfg,angular_maps=True))
    for key in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus'):
        np.testing.assert_allclose(a['spectra'][key],b['spectra'][key],rtol=2e-13,atol=1e-16)


def test_enlarged_basis_support_and_concurrent_memory(small):
    s,settings,cfg=small
    for zone,row,n in (((0,0,1),True,17),((0,1,7),False,59)):
        settings=replace(settings,zone=zone,beam_cutoff=4.6,potential_cutoff=6.2)
        cfg=replace(cfg,systematic_row=row,channeling_model='double',propagation='both',fft_grid=48,depth=257,grid=193)
        assert len(geometry(s,settings,systematic_row=row)[2])==n
        info=numerical_info(s,settings,cfg,check_memory=False)
        assert info['estimated_working_mib']>info['dense_working_estimate_mib']
        assert info['detector_workers']['fft-multislice']==4
    with pytest.raises(ValueError,match='Nyquist|support|harmonics'):
        numerical_info(s,settings,replace(cfg,fft_grid=12),check_memory=False)


def test_nonmagnetic_and_reversal_parity(small):
    s,settings,cfg=small
    a=forward.calculate(s,settings,replace(cfg,channeling_model='double',eta=0))
    np.testing.assert_allclose(a['spectra']['D_mag'],0,atol=1e-15)
    p=forward.calculate(s,settings,replace(cfg,channeling_model='double'))
    m=forward.calculate(s,settings,replace(cfg,channeling_model='double',eta=-1))
    np.testing.assert_allclose(p['spectra']['D_mag'],-m['spectra']['D_mag'],atol=1e-15)
    np.testing.assert_allclose(p['spectra']['D_nonmag'],m['spectra']['D_nonmag'],atol=1e-15)


def test_double_maps_are_actual_integrands(small):
    s,settings,cfg=small
    r=forward.calculate(s,settings,replace(cfg,channeling_model='double',angular_maps=True,grid=9,propagation='both'))
    for m in r['methods'].values():
        dq2=(m['qx'][0,1]-m['qx'][0,0])**2
        for ie,edge in enumerate(('L3','L2')):
            for d in ('A','B'):
                for sign in ('plus','minus'):
                    actual=np.sum(m['maps'][edge]['I_'+sign]*m['weights'][d])*dq2
                    assert actual==pytest.approx(m['spectra']['I_'+d+'_'+sign][ie],rel=3e-13)


def test_original_project_is_read_only_and_defaults_single():
    import json,hashlib
    from pathlib import Path
    root=Path('outputs/gui_stage_d/windows_20261016/reference_project')
    if not root.exists():pytest.skip('Local legacy reference project unavailable')
    before={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
    with patch.object(forward,'calculate',side_effect=AssertionError('Loading must not run physics')):
        r=load_project(root)
    assert r['config'].channeling_model=='single'
    assert before=={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
    for method in r['methods'].values():
        assert method['config'].channeling_model=='single'


def test_double_full_energy_coverage_is_actually_evaluated(small):
    s,settings,cfg=small
    cfg=replace(cfg,channeling_model='double',propagation='both',energy_scope='full',energy_points=9,grid=9,depth=5)
    r=forward.calculate(s,settings,cfg)
    assert len(r['spectra']['energy_ev'])>=9
    assert cfg.l3 in r['spectra']['energy_ev'] and cfg.l2 in r['spectra']['energy_ev']
    assert r['metadata']['spectral_coverage']=='full'
    for m in r['methods'].values():assert np.isfinite(m['spectra']['I_A_plus']).all()


def test_cancelled_double_job_releases_reservation(small):
    from emcd_sim.gui import memory_budget
    with pytest.raises(forward.Cancelled):
        forward.calculate(*small[:2],replace(small[2],channeling_model='double'),cancelled=lambda:True)
    assert memory_budget.assess_memory(0)['concurrent_calculations']==0


def test_saved_model_label_and_restored_controls(small):
    from pathlib import Path
    from uuid import uuid4
    from PySide6 import QtWidgets
    from emcd_sim.gui.app import MainWindow
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    r=forward.calculate(*small[:2],replace(small[2],channeling_model='double',l3=831.4778))
    w=MainWindow(workspace=Path('outputs')/('gui_dc_controls_'+uuid4().hex))
    try:
        record=w.browser.register(r)
        assert record['channeling_model']=='double'
        w.emcd_result=r;w.use_result_settings()
        assert w.forward_settings().channeling_model=='double'
        assert w.forward_settings().energy_scope=='edges' and not w.forward_settings().angular_maps
        assert w.forward_settings().l3==831.4778
    finally:w.close();app.processEvents()
