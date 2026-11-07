"""Analytical manual tensor semantics, source authentication and GUI workflows."""
from dataclasses import replace
from pathlib import Path
import copy
import json
import numpy as np
import pytest
from emcd_sim.manual_l23 import (lorentzian,window_fraction,simple_strength,simple_parameters,evaluate,AnalyticalL23MDFF)
from emcd_sim.imported_mdff import ImportedMDFF
from emcd_sim.mdff_orientation import axis_rotation
from emcd_sim.gui.generalized_forward import source_for,settings_for_source
from emcd_sim.gui.geometry import Settings
from emcd_sim.gui.forward_pipeline import calculate
from emcd_sim.gui.project_io import save_project,load_project,source_status
from test_mdff_usability import window


def spectral(w):
    w.model_box.setCurrentIndex(2);w.manual_model.setCurrentIndex(1);e=w.manual_spectral;e.element.setCurrentText('Fe');return e


@pytest.mark.parametrize('peak,width',[(710,1),(723,3.4),(1,.001)])
def test_lorentzian_area_fwhm_and_no_window_renormalization(peak,width):
    assert window_fraction(-np.inf,np.inf,peak,width)==1
    center=lorentzian([peak],peak,width)[0]
    # Input subtraction at a narrow width loses a few ulps relative to the peak.
    np.testing.assert_allclose(lorentzian([peak-width/2,peak+width/2],peak,width),center/2,rtol=2e-12)
    assert window_fraction(peak-width/2,peak+width/2,peak,width)==pytest.approx(.5)
    theta=np.linspace(-np.pi/2+1e-6,np.pi/2-1e-6,20001)
    x=peak+width/2*np.tan(theta)
    transformed=lorentzian(x,peak,width)*width/2/np.cos(theta)**2
    area=np.sum((transformed[1:]+transformed[:-1])*.5*np.diff(theta))
    assert area==pytest.approx(1-2e-6/np.pi,abs=1e-11)


@pytest.mark.parametrize('a,r,p',[(0,1,0),(2,0,-1),(1.3,2.4,.7)])
def test_strength_mapping_and_sign(a,r,p):
    t=simple_strength(a,r,p)
    assert t[0,0]==a and t[2,2]==a*r and t[0,1]==1j*a*p
    assert np.trace(t).real==pytest.approx(a*(2+r))
    assert np.linalg.eigvalsh(t).min()>=-1e-14


@pytest.mark.parametrize('values',[(-1,1,0),(1,-1,0),(1,1,1.01),(np.inf,1,0)])
def test_invalid_simple_strength(values):
    with pytest.raises(ValueError):simple_strength(*values)


def test_independent_profiles_and_exact_provider_off_grid(window):
    w,_=window;e=spectral(w)
    for (edge,key),value in {( 'L3','width'):'1.2',('L2','width'):'3',('L3','A'):'2',('L2','A'):'3',('L3','p'):'.6',('L2','p'):'.4',('L2','r'):'2'}.items():e.fields[edge,key].setText(value)
    cfg=w.forward_settings();source=source_for(cfg);assert isinstance(source,AnalyticalL23MDFF)
    model=source.metadata['manual_l23_model'];energy=np.array([708.12345,712.34567,720.87654])
    expected=lorentzian(energy,708.1,1.2)[:,None,None]*simple_strength(2,1,.6)+lorentzian(energy,721.1,3)[:,None,None]*simple_strength(3,2,.4)
    a,b=source.tensors(energy,np.eye(3),cfg.magnetization)
    np.testing.assert_allclose(a.tensor_angstrom2_per_ev,expected,rtol=1e-14,atol=1e-16)
    np.testing.assert_array_equal(b.tensor_angstrom2_per_ev,a.tensor_angstrom2_per_ev.conj())
    assert np.linalg.eigvalsh(a.tensor_angstrom2_per_ev).min()>0
    before=source.tensors(energy,np.eye(3),cfg.magnetization)[0].tensor_angstrom2_per_ev
    e.low.setText('707');e.high.setText('725');cfg2=w.forward_settings()
    np.testing.assert_array_equal(source_for(cfg2).tensors(energy,np.eye(3),cfg2.magnetization)[0].tensor_angstrom2_per_ev,before)
    assert model['edges']['L3']['fwhm_ev']!=model['edges']['L2']['fwhm_ev']


def test_general_complex_matrices_preserved_between_views(window):
    w,_=window;e=spectral(w);e.view.setCurrentIndex(1)
    a=np.array([[2,.2+.1j,.3-.1j],[.2-.1j,3,.1+.2j],[.3+.1j,.1-.2j,4]])
    e.loading=True;e.set_matrix('L3',a);e.loading=False;e.matrix_changed()
    assert simple_parameters(a) is None
    e.view.setCurrentIndex(0)
    assert e.view.currentIndex()==1 and 'no projection' in e.error.text()
    assert 'General matrix retained' in e.representation.text()
    assert e.fields['L3','A'].text()=='N/A'
    np.testing.assert_array_equal(e.matrices['L3'].matrix(),a)
    source=source_for(w.forward_settings());edge=source.metadata['manual_l23_model']['edges']['L3']
    np.testing.assert_array_equal(np.array(edge['real'])+1j*np.array(edge['imag']),a)
    e.loading=True;e.set_matrix('L3',simple_strength(2,.5,.3));e.loading=False
    e.view.setCurrentIndex(0);assert e.view.currentIndex()==0
    assert float(e.fields['L3','A'].text())==2


@pytest.mark.parametrize('text',['nan','1e999','bad','-1','1+2ii'])
def test_invalid_full_matrix_keeps_previous_source(window,text):
    w,_=window;e=spectral(w);cfg=w.forward_settings();raw=Path(cfg.source).read_bytes()
    e.view.setCurrentIndex(1);e.matrices['L3'].cells.item(0,0).setText(text)
    with pytest.raises(ValueError):w.forward_settings()
    assert Path(cfg.source).read_bytes()==raw


def test_frame_rotation_reversal_and_heatmaps_use_provider(window):
    w,_=window;e=spectral(w);e.direction.setText('1 2 3');cfg=w.forward_settings();source=source_for(cfg)
    rotation=axis_rotation((1,2,3));energy=np.array([708.1,714.123,721.1]);local=evaluate(source.metadata['manual_l23_model'],energy)
    a,b=source.tensors(energy,np.eye(3),cfg.magnetization)
    np.testing.assert_allclose(a.tensor_angstrom2_per_ev,np.einsum('ia,eab,jb->eij',rotation,local,rotation),atol=1e-15)
    np.testing.assert_allclose(b.tensor_angstrom2_per_ev,a.tensor_angstrom2_per_ev.conj(),atol=1e-15)
    w.preview_mdff();e.heat_energy.setValue(714.123);e.state.setCurrentIndex(3)
    pair=source.tensors(np.array([714.123]),np.eye(3),cfg.magnetization)
    np.testing.assert_allclose(e.heatmap_values,(pair[0].tensor_angstrom2_per_ev[0]-pair[1].tensor_angstrom2_per_ev[0])/2,atol=1e-15)
    assert 'CURRENT' in e.status.text()
    e.fields['L2','width'].setText('2');assert e.is_stale and 'STALE' in e.status.text()


def test_per_element_reset_constant_and_full_state(window):
    w,_=window;e=spectral(w);e.fields['L3','A'].setText('3');e.fields['L2','p'].setText('.6')
    e.element.setCurrentText('Co');e.fields['L3','width'].setText('2.4')
    e.element.setCurrentText('Fe');assert e.fields['L3','A'].text()=='3' and e.fields['L2','p'].text()=='.6'
    w.manual_model.setCurrentIndex(0);w.manual_tensor.cells.item(0,0).setText('.8');constant=w.forward_settings()
    assert not isinstance(source_for(constant),AnalyticalL23MDFF)
    w.manual_model.setCurrentIndex(1);assert e.fields['L3','A'].text()=='3'
    w.manual_model.setCurrentIndex(0);assert w.manual_tensor.cells.item(0,0).text()=='.8'
    w.restore_imported_settings(constant);assert w.manual_model.currentIndex()==0
    np.testing.assert_array_equal(source_for(w.forward_settings()).plus.tensor_angstrom2_per_ev,source_for(constant).plus.tensor_angstrom2_per_ev)
    w.manual_model.setCurrentIndex(1);e.reset_defaults();assert e.fields['L3','A'].text()=='1.0'


@pytest.mark.parametrize('channel',['single','double'])
def test_solver_agreement_and_portable_complete_restoration(window,tmp_path,channel):
    w,app=window;e=spectral(w);e.fields['L2','p'].setText('.3');e.direction.setText('1 0 0')
    e.element.setCurrentText('Co');e.fields['L3','A'].setText('1.8');e.element.setCurrentText('Fe')
    cfg=replace(w.forward_settings(),propagation='both',channeling_model=channel,energy_scope='edges',grid=9,depth=3,subpixels=4,
        halfwidth=.7,radius=.12,centers=((.2,.2),(.2,-.2)),fft_grid=16,slice_step=.01,correction=False,worker_mode='manual',parallel_workers=1)
    settings=Settings(zone=(0,0,1),target=(1,1,0),voltage=200,thickness=.2,tilt=(-5,7),beam_cutoff=.6,potential_cutoff=1.2)
    source=source_for(cfg);result=calculate(w.structure,settings,cfg)
    # Independent sampled input at the exact solver energies proves that the
    # density is delivered once with the unchanged imported tensor contraction.
    bare=copy.deepcopy(source.metadata);bare.pop('manual_l23_model');bare.pop('manual_l23_editor')
    path=tmp_path/'independent-sampled.json';path.write_text(json.dumps(bare),encoding='utf-8')
    reference=calculate(w.structure,settings,replace(cfg,source=str(path),source_sha256=ImportedMDFF.load(path).sha256))
    for method in result['methods']:
        for key,value in result['methods'][method]['spectra'].items():np.testing.assert_allclose(value,reference['methods'][method]['spectra'][key],rtol=1e-13,atol=1e-16)
    folder=tmp_path/'original';save_project(result,folder);relocated=tmp_path/'relocated';folder.rename(relocated);Path(cfg.source).unlink()
    reopened=load_project(relocated);entry=source_status(reopened)['mdff'];assert entry['verified']
    w.model_box.setCurrentIndex(1);w.emcd_result=reopened;w.use_result_settings();app.processEvents()
    assert w.manual_model.currentIndex()==1 and not w.errors
    w.preview_mdff();assert not e.is_stale
    rerun=calculate(w.structure,settings,w.forward_settings())
    for method in result['methods']:
        for key,value in result['methods'][method]['spectra'].items():np.testing.assert_array_equal(value,rerun['methods'][method]['spectra'][key])
    e.element.setCurrentText('Co');assert e.fields['L3','A'].text()=='1.8'
    attached=Path(entry['path']);data=json.loads(attached.read_bytes());data['manual_l23_model']['edges']['L3']['fwhm_ev']*=2
    tampered=tmp_path/'inconsistent.json';tampered.write_text(json.dumps(data),encoding='utf-8')
    with pytest.raises(ValueError,match='differ'):ImportedMDFF.load(tampered)


@pytest.mark.parametrize('field',['manual_l23_model','manual_l23_editor'])
def test_partial_spectral_provenance_rejected(window,tmp_path,field):
    w,_=window;e=spectral(w);data=e.document();data.pop(field)
    path=tmp_path/'stripped.json';path.write_text(json.dumps(data),encoding='utf-8')
    with pytest.raises(ValueError,match='Incomplete manual'):ImportedMDFF.load(path)


def test_restored_proper_frame_direction_is_derived(window):
    w,_=window;e=spectral(w);e.direction.setText('1 2 3');source=source_for(w.forward_settings())
    e.load_source(source)
    assert not e.direction.isReadOnly() and e.frame_mode.currentIndex()==0
    e.loading=True
    for i in range(3):
        for j in range(3):e.frame_table.item(i,j).setText(str(source.metadata['frame_to_crystal'][i][j]))
    e.frame_mode.setCurrentIndex(1);e.loading=False;e.edited()
    source=source_for(w.forward_settings());e.load_source(source)
    assert e.direction.isReadOnly() and e.frame_mode.currentIndex()==1
    np.testing.assert_array_equal(e.frame_value(),source.metadata['frame_to_crystal'])
    e.frame_mode.setCurrentIndex(0);assert not e.direction.isReadOnly()


def test_zero_edge_keeps_its_inactive_simple_choices(window):
    w,_=window;e=spectral(w)
    for key,value in (('r','2.5'),('p','-.4'),('A','0')):e.fields['L3',key].setText(value)
    e.view.setCurrentIndex(1);e.view.setCurrentIndex(0)
    assert e.fields['L3','r'].text()=='2.5' and e.fields['L3','p'].text()=='-.4'
    e.load_source(source_for(w.forward_settings()))
    assert e.fields['L3','r'].text()=='2.5' and e.fields['L3','p'].text()=='-.4'


def test_invalid_preview_reports_inline_without_dialog(window):
    w,_=window;e=spectral(w);w.preview_mdff();assert not e.is_stale
    e.fields['L3','width'].setText('0');w.preview_mdff()
    assert e.is_stale and 'Preview blocked' in e.status.text() and not w.errors
    assert np.isfinite(lorentzian([710],710,1e308)).all()
