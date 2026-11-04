from dataclasses import replace
import numpy as np
import pytest
from ase.build import bulk
from emcd_sim.gui.geometry import Structure,Settings
from emcd_sim.gui.generalized_forward import calculate,settings_for_source
from emcd_sim.gui.project_io import save_project,load_project,source_status,rerun_reason
from single_element_helpers import write_source


@pytest.mark.parametrize('channel',['single','double'])
def test_fe_both_solvers_maps_and_project(tmp_path,channel):
    s=Structure(bulk('Fe','bcc',a=2.866,cubic=True),'Synthetic Fe geometry')
    settings=Settings(zone=(0,0,1),target=(1,1,0),tilt=(-5,7),voltage=200,thickness=.2,beam_cutoff=.6,potential_cutoff=1.2)
    source=write_source(tmp_path/'tensor.json')
    cfg=settings_for_source(source,energy_scope='edges',grid=9,depth=9,subpixels=8,fft_grid=16,slice_step=.01,
        halfwidth=.7,centers=((.2,.2),(.2,-.2)),radius=.12,propagation='both',channeling_model=channel,worker_mode='manual',parallel_workers=1)
    r=calculate(s,settings,cfg)
    assert set(r['methods'])=={'bloch','fft-multislice'}
    for method,v in r['methods'].items():
        sp=v['spectra'];assert v['metadata']['scientific_status']=='SYNTHETIC TEST ONLY'
        assert set(v['maps'])=={'L3','L2'}
        assert v['metadata']['ionization_sites']['normalization']=='mean_per_selected_atom'
        assert 'atomic' in v['metadata']['unused_legacy_config_fields']
        if channel=='double':
            np.testing.assert_array_equal(v['metadata']['outgoing_energy_ev'],200000-np.array([710,723]))
        for k in ('I_A_plus','I_A_minus','I_B_plus','I_B_minus'):
            assert np.isfinite(sp[k]).all() and sp[k].min()>=0
        np.testing.assert_allclose(sp['D_raw'],sp['D_mag']+sp['D_nonmag'],atol=1e-14)
        np.testing.assert_allclose(sp['I_A_plus']-sp['I_A_minus'],2*sp['M_A'],atol=1e-15)
    assert r['comparison']['spectra']['I_A_plus']['l2_relative']<.015
    save_project(r,tmp_path/'project');opened=load_project(tmp_path/'project')
    assert opened['config'].model=='imported' and opened['config'].ionizing_element=='Fe'
    assert source_status(opened)['mdff']['verified'] and not rerun_reason(opened)
    np.testing.assert_array_equal(opened['spectra']['D_mag'],r['spectra']['D_mag'])
    source.unlink();opened2=load_project(tmp_path/'project')
    assert not source_status(opened2)['mdff']['available']
    assert 'mdff source unavailable' in rerun_reason(opened2)
    np.testing.assert_array_equal(opened2['spectra']['I_A_plus'],r['spectra']['I_A_plus'])
    with pytest.raises(ValueError,match='Missing/unreadable'):calculate(s,settings,opened2['config'])


def test_nonmagnetic_and_unsupported_material(tmp_path):
    s=Structure(bulk('Fe','bcc',a=2.866,cubic=True))
    s.atoms.set_initial_magnetic_moments([0,0])
    settings=Settings(zone=(0,0,1),target=(1,1,0),tilt=(0,0),thickness=.1,beam_cutoff=.6,potential_cutoff=1.2)
    cfg=settings_for_source(write_source(tmp_path/'nonmag.json',nonmagnetic=True),energy_scope='edges',grid=9,depth=9,subpixels=8)
    r=calculate(s,settings,cfg)
    np.testing.assert_array_equal(r['spectra']['M_A'],0)
    np.testing.assert_array_equal(r['spectra']['M_B'],0)
    with pytest.raises(ValueError,match='single-element'):calculate(Structure.nickel(),settings,cfg)


def test_changed_external_source_during_calculation_discards_result(tmp_path):
    s=Structure(bulk('Fe','bcc',a=2.866,cubic=True))
    settings=Settings(zone=(0,0,1),target=(1,1,0),tilt=(0,0),thickness=.1,beam_cutoff=.6,potential_cutoff=1.2)
    p=write_source(tmp_path/'mutable.json');original=p.read_bytes()
    cfg=settings_for_source(p,energy_scope='edges',grid=9,depth=9,subpixels=8,angular_maps=False)
    def replace_source(stage):
        if stage=='Validating imported tensor and equivalent localized events':p.write_bytes(original+b' ')
    with pytest.raises(ValueError,match='checksum changed'):calculate(s,settings,cfg,progress=replace_source)
    assert p.read_bytes()!=original


@pytest.mark.parametrize('channel',['single','double'])
@pytest.mark.parametrize('voltage',[.5,.723])
def test_imported_loss_must_be_below_incident_energy(tmp_path,channel,voltage):
    s=Structure(bulk('Fe','bcc',a=2.866,cubic=True))
    settings=Settings(zone=(0,0,1),target=(1,1,0),tilt=(0,0),voltage=voltage,thickness=.1,beam_cutoff=.6,potential_cutoff=1.2)
    cfg=settings_for_source(write_source(tmp_path/'loss.json'),channeling_model=channel,energy_scope='edges',grid=9,depth=9,subpixels=8)
    with pytest.raises(ValueError,match='below incident'):calculate(s,settings,cfg)
