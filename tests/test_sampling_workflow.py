"""Independent energy/map choices and the shared bounded Local scheduler."""
from dataclasses import replace
import numpy as np
from PySide6 import QtCore

from emcd_sim.gui.multisite_run import applied_inputs
from emcd_sim.gui.project_session import capture_configuration,restore_configuration
from emcd_sim.gui.project_configuration import save_configuration,load_configuration
from emcd_sim.gui.project_io import config_from_dict
from emcd_sim.gui import forward_pipeline as forward
from test_multisite_gui_run import app,window
from test_local_mdff_workflow import local_draft
from test_multisite_forward import system,configuration,RAW_KEYS,PARITY_KEYS
from emcd_sim.multisite_spectrum import prepare_multisite_spectrum,contract_multisite_spectrum


def test_uniform_native_selected_counts_and_roundtrip(window,tmp_path):
    w=window
    assert w.energy_scope.currentData()=='uniform' and w.spin['energy'].value()==241
    v,e,d=local_draft(w,'xmcd');assert d.apply_configuration() is not None
    v.apply_groups()
    w.energy_scope.setCurrentIndex(w.energy_scope.findData('uniform'))
    cfg,sites,windows,_,_=applied_inputs(w,w.forward_settings())
    energy=np.asarray(windows['Ni'].energy_ev)
    expected=np.unique(np.r_[np.linspace(823.625,882.521,241),831.271,848.698])
    np.testing.assert_array_equal(energy,expected)
    assert cfg.energy_points==243 and w.spin['energy'].value()==241 and w.spin['energy'].isEnabled()
    assert cfg.angular_evaluation=='selected' and cfg.angular_maps
    state=capture_configuration(w);assert state['config'].energy_points==241
    save_configuration(state,tmp_path/'uniform')
    restored=load_configuration(tmp_path/'uniform');restore_configuration(w,restored)
    again=applied_inputs(w,w.forward_settings())
    np.testing.assert_array_equal(again[2]['Ni'].energy_ev,expected)
    assert w.energy_scope.currentData()=='uniform' and w.spin['energy'].value()==241
    w.angular_maps.setChecked(False)
    assert len(applied_inputs(w,w.forward_settings())[2]['Ni'].energy_ev)==243
    w.energy_scope.setCurrentIndex(w.energy_scope.findData('native'))
    cfg,_,windows,_,_=applied_inputs(w,w.forward_settings())
    assert cfg.energy_points==4329 and len(windows['Ni'].energy_ev)==4329
    assert w.spin['energy'].isHidden() and not w.uniform_points_label.isVisible()
    save_configuration(capture_configuration(w),tmp_path/'native')
    restore_configuration(w,load_configuration(tmp_path/'native'))
    assert w.energy_scope.currentData()=='native' and applied_inputs(w,w.forward_settings())[0].energy_points==4329
    w.energy_scope.setCurrentIndex(w.energy_scope.findData('edges'))
    assert applied_inputs(w,w.forward_settings())[0].energy_points==2
    w.confirm_project_changes=lambda continuation=None:True
    w.new_project()
    assert w.energy_scope.currentData()=='uniform' and w.angular_maps.isChecked()
    assert not w.full_angular_field.isChecked() and w.spin['energy'].value()==241


def test_old_explicit_native_and_broad_field_choices_are_preserved():
    old=config_from_dict(dict(model='multisite',energy_scope='full',angular_maps=True))
    assert old.energy_sampling=='native' and old.angular_evaluation=='all'
    absent=config_from_dict(dict(model='multisite'))
    assert absent.energy_sampling=='uniform' and absent.angular_evaluation=='selected'
    legacy=config_from_dict(dict(model='xmcd',energy_scope='full',angular_maps=True))
    assert legacy.energy_sampling=='uniform' and legacy.angular_evaluation=='selected'
    from emcd_sim.gui.generalized_forward import energy_grid
    from emcd_sim.gui.emcd_forward import ForwardSettings
    assert len(energy_grid(ForwardSettings(energy_sampling='native')))==4329
    assert len(energy_grid(ForwardSettings()))==243


def test_selected_fields_match_full_grid_at_identical_energies(tmp_path,monkeypatch):
    structure,settings,sites,_=system(tmp_path)
    energy=np.unique(np.r_[np.linspace(710.,723.,35),716.])
    cfg=configuration(grid=97,subpixels=64,selected_edges=(('L3',710.),('L2',723.)))
    result=forward.calculate_multisite(structure,settings,sites,cfg,energy_ev=energy)
    diagnostics=result['metadata']['angular_evaluation']
    full=[d for d in diagnostics if d['full_field']]
    detector=[d for d in diagnostics if not d['full_field']]
    assert sum(d['energy_count'] for d in full)==2
    assert all(d['required_pixels']==97**2 for d in full)
    assert sum(d['energy_count'] for d in detector)==len(energy)-2
    support=np.logical_or.reduce([result['weights'][k]>0 for k in ('A','B')])
    assert all(d['required_pixels']==int(support.sum())<97**2 for d in detector)
    raw=contract_multisite_spectrum(result['model'],structure,sites,result['coherence'],
        prepare_multisite_spectrum(sites,energy),result['qx'].ravel(),result['qy'].ravel(),
        crystal_to_microscope=result['metadata']['frame'],thickness_nm=settings.thickness)
    expected=forward._multisite_detector_data(raw['total'],cfg,energy,result['qx'],result['qy'],
        result['weights'],np.ones(97**2,bool))
    for key in RAW_KEYS+PARITY_KEYS:
        np.testing.assert_allclose(result['spectra'][key],expected['spectra'][key],rtol=2e-13,atol=1e-17)
    for label,maps in expected['maps'].items():
        for key,value in maps.items():np.testing.assert_allclose(result['maps'][label][key],value,rtol=2e-13,atol=1e-17)
    broad=forward.calculate_multisite(structure,settings,sites,replace(cfg,angular_evaluation='all'),energy_ev=energy)
    assert all(d['full_field'] for d in broad['metadata']['angular_evaluation'])
    for key in RAW_KEYS:np.testing.assert_allclose(broad['spectra'][key],result['spectra'][key],rtol=2e-13,atol=1e-17)
