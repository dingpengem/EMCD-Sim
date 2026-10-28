"""Independent general row selection, reduced-energy propagation and export."""
from pathlib import Path
from dataclasses import replace
import json
import numpy as np
import pytest
from emcd_sim.crystal import fcc_nickel
from emcd_sim.projected_geometry import ProjectedGeometry
from emcd_sim.gui.geometry import Structure,Settings,elastic_model
from emcd_sim.multislice_double_channeling import ProjectedFFT

@pytest.mark.parametrize('zone,target',[
    ((0,0,1),(2,0,0)),((0,1,7),(2,0,0)),((1,1,7),(2,-2,0)),
    ((1,1,1),(2,-2,0)),((7,1,0),(0,0,2))])
def test_row_uses_actual_target_or_actual_local_x_support(zone,target):
    geo=ProjectedGeometry.from_crystal(fcc_nickel(),zone,target)
    s=Settings(zone=zone,target=target,thickness=2,voltage=200,beam_cutoff=3.2,potential_cutoff=3.8)
    elastic=elastic_model(Structure.nickel(),s,systematic_row=True)
    results=[]
    for descriptor in (geo,None):
        grid=ProjectedFFT.build(elastic,grid_points=32,potential_cutoff=3.8,
            systematic_row=True,row_reduction=True,projected_geometry=descriptor)
        assert all(np.all(np.cross(h,target)==0) for h in grid.hkl)
        grid.indices(elastic.beams.hkl)
        results.append(grid)
    np.testing.assert_allclose(results[0].potential,results[1].potential,atol=1e-15)
    np.testing.assert_array_equal(results[0].hkl,results[1].hkl)


def test_outgoing_energy_carrier_and_adjoint_without_elastic_eigenmodes():
    from emcd_sim.geometry import electron_wavelength_angstrom
    geo=ProjectedGeometry.from_crystal(fcc_nickel(),(1,1,1),(2,-2,0))
    s=Settings(zone=(1,1,1),target=(2,-2,0),voltage=200,tilt=(-10,.2),beam_cutoff=1.8,potential_cutoff=2.2)
    elastic=elastic_model(Structure.nickel(),s)
    grid=ProjectedFFT.build(elastic,grid_points=24,potential_cutoff=2.2,projected_geometry=geo)
    q=np.array([.4,-.3]);loss=831.271;out=grid.plan(loss,q)
    lam=electron_wavelength_angstrom(200-loss/1000)
    expected=-10*np.pi*lam*(np.sum(grid.g**2,axis=-1)+2*grid.g@(elastic.microscope.incident_k_xy+q))
    np.testing.assert_allclose(out.d.ravel(),expected,atol=1e-12)
    ratio=(1+(200000-loss)/510998.95)*lam/((1+200000/510998.95)*electron_wavelength_angstrom(200))
    np.testing.assert_allclose(out.u,grid.potential*ratio,atol=1e-15)
    c=np.zeros(grid.potential.size,complex);c[0]=1
    np.testing.assert_allclose(out.advance(out.advance(c,3,.01),3,-.01),c,atol=2e-14)
    assert not np.array_equal(grid.plan().d,out.d)


def test_generalized_117_saved_gui_export_retains_raw_relative_data(tmp_path):
    from emcd_sim.gui.project_io import load_project,fingerprints
    from emcd_sim.gui.emcd_forward import export_result
    root=Path('outputs/generalized_multislice_emcd_validation/gui')
    paths=[p for p in root.glob('117_double_*/project') if (p.parent/'acceptance.json').exists()]
    if not paths:pytest.skip('Real GUI acceptance artifact not yet available')
    r=load_project(sorted(paths)[-1]);before=fingerprints(r)
    out=tmp_path/'export';export_result(r,out,component_mode='raw')
    assert fingerprints(r)==before
    with np.load(out/'signal_display.npz',allow_pickle=False) as f:
        assert any('raw' in k for k in f.files) and any('percent' in k for k in f.files)
    for method in ('bloch','fft-multislice'):
        assert (out/(method+'_spectra.csv')).exists()
    assert (out/'L3_angular_maps.png').exists()


@pytest.mark.parametrize('zone,target,cutoff',[
    ((1,1,7),(2,-2,0),3.2),((1,1,1),(2,-2,0),1.8),((7,1,0),(0,0,2),2.2)])
@pytest.mark.parametrize('channel',['single','double'])
def test_general_ms_only_never_uses_bw_wavefields(zone,target,cutoff,channel):
    from unittest.mock import patch
    from emcd_sim.gui.emcd_forward import ForwardSettings,calculate
    geo=ProjectedGeometry.from_crystal(fcc_nickel(),zone,target);g=geo.crystal.g_vector(target)[0]
    s=Settings(zone=zone,target=target,voltage=200,thickness=.5,tilt=(geo.bragg_tilt(),0),beam_cutoff=cutoff,potential_cutoff=3.8)
    c=ForwardSettings(axis_declared=True,propagation='fft-multislice',channeling_model=channel,energy_scope='edges',grid=9,depth=5,
        fft_grid=24,subpixels=16,centers=((g/2,g/2),(g/2,-g/2)),radius=.16*g,correction=False,worker_mode='manual')
    with patch('emcd_sim.physical_elastic.PhysicalElasticModel.amplitudes',side_effect=AssertionError('BW wavefield used by MS-only')):
        r=calculate(Structure.nickel(),s,c)
    assert list(r['methods'])==['fft-multislice']
    assert r['fft']['summary']['norm_error']<1e-12
    assert np.isfinite(r['maps']['L3']['I_mag']).all()


def test_validation_driver_resumes_json_checkpoint_without_solver(tmp_path,monkeypatch):
    import importlib.util
    from emcd_sim.gui.emcd_forward import ForwardSettings
    path=Path(__file__).parents[1]/'scripts/validate_generalized_emcd.py'
    spec=importlib.util.spec_from_file_location('generalized_resume_test',path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    monkeypatch.setattr(m,'OUT',tmp_path/'results')
    source=tmp_path/'source.txt';source.write_text('source identity only',encoding='utf-8')
    s=Settings();c=ForwardSettings(source=str(source))
    folder=m.OUT/'cases'/'finished';folder.mkdir(parents=True)
    record=dict(identity=m.case_identity(s,c),fingerprints={'array':'unchanged'})
    checkpoint=folder/'case.json';checkpoint.write_text(json.dumps(record),encoding='utf-8');before=checkpoint.read_bytes()
    monkeypatch.setattr(m,'load_project',lambda path: {'saved':True})
    monkeypatch.setattr(m,'fingerprints',lambda r: {'array':'unchanged'})
    def forbidden(*a,**k):raise AssertionError('Completed checkpoint must not recalculate')
    monkeypatch.setattr(m,'calculate',forbidden)
    m.run_case('finished',s,c)
    assert checkpoint.read_bytes()==before
    # A real source change must still block reuse.
    source.write_text('changed',encoding='utf-8')
    with pytest.raises(ValueError,match='Changed case identity'):m.run_case('finished',s,c)
