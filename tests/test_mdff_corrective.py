"""Narrow corrective regressions and retained contracts of superseded workflows."""
from dataclasses import replace
from pathlib import Path
import hashlib
import json
import numpy as np
import pytest
from emcd_sim.gui.atomic_editor import FIELDS
from emcd_sim.gui.atomic_editor_model import edge_references
from emcd_sim.gui.project_io import config_from_dict,save_project,load_project
from emcd_sim.gui.geometry import Structure,Settings
from emcd_sim.gui.forward_pipeline import calculate
from emcd_sim.gui.generalized_forward import source_for
from emcd_sim.mdff_providers import load_provider,prepare_provider
from emcd_sim.mdff_orientation import axis_rotation
from emcd_sim.manual_l23 import lorentzian,window_fraction
from emcd_sim.historical_ni import NiLocalConfig
from test_mdff_usability import window


def test_replacement_defaults_preserve_provenance_grid_and_help(window):
    w,_=window;e=w.atomic_editor
    assert e.parameter_origins['element']['origin']=='cif_derived'
    assert e.parameter_origins['l3']['origin']=='tabulated_reference'
    assert e.parameter_origins['sigma']['origin']=='numerical_starting'
    assert e.parameter_origins['frame']['origin']=='coordinate_starting'
    assert e.fields['samples'].text()=='201' and float(e.fields['emin'].text())==698.1
    for edge,field in (('L3','l3'),('L2','l2')):assert float(e.fields[field].text())==edge_references('Fe')[edge]['energy_ev']
    assert all(e.fields[k].text() for k in ('cf','exchange','radial'))
    assert e.document()['parameters']['status']=='synthetic'
    assert set(e.fields)<=set(e.info_buttons)
    e.info_buttons['exchange'].click();assert e.field_detail_dialog.isVisible();e.field_detail_dialog.close()


def test_replacement_physical_definitions_units_and_holes(window):
    e=window[0].atomic_editor
    assert set(e.sections)==set('ABCDEFGHI') and set(e.fields)<=set(FIELDS)
    assert all('Units:' in field.toolTip() and 'Provenance:' in field.toolTip() for field in e.fields.values())
    assert e.frame_mode.currentIndex()==1 and e.fields['sigma'].text()=='1.0'
    assert e.holes.rowCount()==5 and 'electron occupation' in e.holes.toolTip()
    assert np.isfinite(np.asarray(e.table_values(e.holes),float)).all()
    assert all(e.fields[k].text() for k in ('source','radial_source','assumptions','validity'))


def test_replacement_element_roundtrip_clears_executable_validation(window):
    w,_=window;e=w.atomic_editor;e.fields['cf'].setText('1.1');e.fields['radial'].setText('.04');e.generate()
    assert e.validated_path and w.atomic_provider_info
    e.element.setCurrentIndex(e.element.findData('Co'))
    assert float(e.fields['l3'].text())==778.6 and e.fields['cf'].text()=='0' and e.fields['radial'].text()=='1'
    assert not e.validated_path and not w.atomic_provider_info
    e.element.setCurrentIndex(e.element.findData('Fe'))
    assert e.fields['cf'].text()=='1.1' and e.fields['radial'].text()=='.04'
    assert not e.validated_path and not w.atomic_provider_info


def test_replacement_missing_reference_and_unsupported_rejection(window,monkeypatch):
    w,_=window;e=w.atomic_editor
    monkeypatch.setattr('emcd_sim.gui.atomic_editor.edge_references',lambda _: {})
    e.element.setCurrentIndex(e.element.findData('Cr'))
    e.document();assert 'Synthetic estimated' in e.reference_problem
    assert e.parameter_origins['l3']['origin']=='synthetic_demonstration'
    e.element.setCurrentIndex(e.element.findData('O'));assert not e.generate_button.isEnabled()
    e.generate();assert not e.validated_path and 'unavailable' in e.status.text()
    with pytest.raises(ValueError):w.forward_settings()


@pytest.mark.parametrize('explicit_zero',[False,True])
def test_replacement_historical_saved_zero_and_absence(window,tmp_path,explicit_zero):
    w,app=window
    saved=dict(model='atomic',atomic=dict(l3_ev=852.7,l2_ev=870.0))
    if explicit_zero:saved['atomic'].update(crystal_field_10dq_ev=0.,exchange_split_ev=0.)
    cfg=config_from_dict(saved)
    assert cfg.l3==852.7 and cfg.l2==870.0
    expected=0. if explicit_zero else NiLocalConfig().crystal_field_10dq_ev
    assert cfg.atomic.crystal_field_10dq_ev==expected
    cfg=replace(cfg,propagation='bloch',energy_scope='edges',grid=9,depth=3,subpixels=4,halfwidth=.7,radius=.12,
        centers=((.2,.2),(.2,-.2)),correction=False,worker_mode='manual',parallel_workers=1)
    settings=Settings(zone=(0,0,1),target=(2,0,0),voltage=200,thickness=.2,tilt=(-5,7),beam_cutoff=.7,potential_cutoff=1.4)
    result=calculate(Structure.nickel(),settings,cfg);folder=tmp_path/'saved';save_project(result,folder)
    w.emcd_result=load_project(folder);w.use_result_settings();app.processEvents()
    e=w.atomic_editor;actual=w.forward_settings()
    assert float(e.fields['l3'].text())==852.7 and float(e.fields['cf'].text())==expected
    assert actual.atomic==cfg.atomic and e.fields['cf'].isReadOnly() and not e.active
    assert not hasattr(actual,'provider_schema') and not w.errors
    w.preview_mdff();preview=e.historical_preview
    a,b=prepare_provider(actual).tensors(preview['energy'],np.eye(3))
    np.testing.assert_array_equal(preview['plus'],a.tensor_angstrom2_per_ev)
    np.testing.assert_array_equal(preview['minus'],b.tensor_angstrom2_per_ev)
    assert 'CURRENT' in e.preview_state.text()
    e.reset_defaults();assert e.active and e.historical_config is None and not e.fields['cf'].isReadOnly()


def test_atomic_revalidation_updates_energies_identity_and_stale_preview(window,tmp_path):
    w,_=window;e=w.atomic_editor;path=tmp_path/'same.json';path.write_text(json.dumps(e.document()),encoding='utf-8')
    w.atomic_parameter_path.setText(str(path));w.validate_atomic_parameters();e.preview();old=e.preview_dialog
    d=json.loads(path.read_bytes());d['parameters'].update(crystal_field_ev=1.75,edge_energies_ev=[709.2,722.3])
    path.write_text(json.dumps(d),encoding='utf-8');digest=hashlib.sha256(path.read_bytes()).hexdigest()
    w.validate_atomic_parameters();cfg=w.forward_settings();source=load_provider(cfg)
    assert e.validated_sha256==cfg.source_sha256==digest
    assert float(e.fields['cf'].text())==source.metadata['atomic_parameters']['crystal_field_ev']==1.75
    assert [float(e.fields[k].text()) for k in ('l3','l2')]==[709.2,722.3]
    assert old.is_stale and 'STALE' in e.preview_state.text()
    e.preview();assert e.preview_dialog.source.sha256==digest and 'CURRENT' in e.preview_state.text()
    path.write_text('{',encoding='utf-8');w.validate_atomic_parameters()
    assert not w.atomic_provider_info and not e.validated_path and 'STALE' in e.preview_state.text()
    with pytest.raises(ValueError):w.forward_settings()


def imported_document(w):
    d=w.manual_tensor.document('Fe','L2,3',(708.1,721.1),(0,0,1));d.pop('manual_constant_editor')
    r=axis_rotation((0,1,0));d.update(basis='declared_local',frame_to_crystal=r.tolist(),magnetization_crystal=r[:,2].tolist())
    for name in ('T_plus','T_minus','T_even'):
        for component in ('real','imag'):d[name][component]=(np.asarray(d[name][component])*np.arange(1,5)[:,None,None]).tolist()
    return d


def test_complete_three_manual_bindings_frames_and_edits(window,tmp_path):
    w,_=window;w.model_box.setCurrentIndex(2);w.manual_model.setCurrentIndex(0);w.constant_input_mode.setCurrentIndex(0)
    w.manual_tensor.cells.item(0,0).setText('.8');w.axis.setText('0 0 1');constant=w.forward_settings()
    w.manual_model.setCurrentIndex(1);e=w.manual_spectral;e.element.setCurrentText('Fe');e.direction.setText('1 2 3');e.fields['L2','width'].setText('2.3')
    spectral=w.forward_settings()
    w.manual_model.setCurrentIndex(0);w.constant_input_mode.setCurrentIndex(1)
    path=tmp_path/'external.json';path.write_text(json.dumps(imported_document(w)),encoding='utf-8')
    w.imported_path.setText(str(path));w.validate_imported_mdff();w.imported_declaration.setChecked(True);imported=w.forward_settings()
    assert w._manual_key=='imported'
    for _ in range(2):
        w.constant_input_mode.setCurrentIndex(0);a=w.forward_settings()
        assert a.source_sha256==constant.source_sha256 and a.magnetization==constant.magnetization
        assert w.manual_tensor.cells.item(0,0).text()=='.8'
        w.manual_model.setCurrentIndex(1);a=w.forward_settings()
        assert a.source_sha256==spectral.source_sha256 and a.magnetization==spectral.magnetization
        assert e.fields['L2','width'].text()=='2.3'
        w.manual_model.setCurrentIndex(0);w.constant_input_mode.setCurrentIndex(1);a=w.forward_settings()
        assert a.source==imported.source and a.source_sha256==imported.source_sha256 and a.magnetization==imported.magnetization
        w.preview_mdff();expected=source_for(a).tensors(source_for(a).energy_ev,np.eye(3),a.magnetization)
        for actual,tensor in zip(w.manual_preview_pair,expected):np.testing.assert_array_equal(actual,tensor.tensor_angstrom2_per_ev)


def test_invalid_constant_draft_and_pending_import_survive_switch(window,tmp_path):
    w,_=window;w.model_box.setCurrentIndex(2);w.manual_model.setCurrentIndex(0);w.constant_input_mode.setCurrentIndex(0)
    w.manual_tensor.cells.item(0,0).setText('nan')
    w.manual_model.setCurrentIndex(1);w.manual_model.setCurrentIndex(0)
    assert w.manual_tensor.cells.item(0,0).text()=='nan'
    with pytest.raises(ValueError):w.forward_settings()
    w.imported_path.setText(str(tmp_path/'missing.json'))
    assert w._manual_key=='imported'
    w.manual_model.setCurrentIndex(1);w.manual_model.setCurrentIndex(0)
    assert w.imported_path.text()==str(tmp_path/'missing.json')
    with pytest.raises(ValueError,match='Validate'):w.forward_settings()


@pytest.mark.parametrize('width',[1e-200,1.,1e308,1.5e308])
def test_stable_fwhm_peak_tails_and_full_area(width):
    peak=710.;expected=(2/np.pi)/width
    assert lorentzian([peak],peak,width)[0]/expected==pytest.approx(1.,rel=1e-14)
    assert window_fraction(-np.inf,np.inf,peak,width)==1
    if width==1e-200:assert lorentzian([peak+1],peak,width)[0]==pytest.approx(width/(2*np.pi),rel=1e-14,abs=0.)
    if width>=1e308:
        assert window_fraction(0.,1e308,peak,width)==pytest.approx(np.arctan2(1e308,width/2)/np.pi)


def test_unsupported_tiny_width_rejected_explicitly():
    with pytest.raises(ValueError,match='finite spectral-density range'):lorentzian([710.],710.,1e-320)
