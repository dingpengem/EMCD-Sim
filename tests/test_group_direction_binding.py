"""Physical-pair binding and restored GUI execution; bounded synthetic inputs."""
from dataclasses import replace
from pathlib import Path
import json
import numpy as np
import pytest

from emcd_sim.gui.generalized_forward import source_for, settings_for_source, settings_for_provider
from emcd_sim.gui.group_mdff import bind_group_direction
from emcd_sim.gui.project_session import capture_configuration, restore_configuration
from emcd_sim.gui.project_io import save_configuration, load_configuration
from emcd_sim.gui.site_group_editor import validate_site_rows
from test_multisite_gui_run import app, window, controls, sites_for, bind, finish, RAW
from test_group_mdff import source


ENERGY=np.array([710.,723.])


def direction(editor,index,text):
    editor.groups.setCurrentItem(editor.groups.topLevelItem(index))
    editor.direction.setText(text);editor.update_direction()


def test_complete_physical_pair_apply_cancel_and_editor_refresh(window,tmp_path):
    structure,sites=sites_for(tmp_path);controls(window,structure);e=bind(window,sites)
    original=e.accepted_site_groups;other=e.rows()[1]
    ref=e.rows()[0][4];raw=source_for(ref);before=raw.tensors(ENERGY,np.eye(3),(0,0,1))
    source_bytes=Path(ref.source).read_bytes()
    dialog=e.configure_mdff()
    direction(e,0,'0 0 -1')
    assert not dialog.has_unapplied_edits()  # A group direction is not an MDFF parameter edit.
    accepted=e.apply();cfg=accepted.groups[0].mdff_reference
    assert cfg.pair_reversed and cfg.magnetization==(0.,0.,-1.)
    assert e.rows()[1]==other and accepted.groups[1].mdff_reference is original.groups[1].mdff_reference
    selected=source_for(cfg);after=selected.tensors(ENERGY,np.eye(3),(0,0,-1))
    for actual,expected in zip(after,before[::-1]):
        np.testing.assert_array_equal(actual.tensor_angstrom2_per_ev,expected.tensor_angstrom2_per_ev)
    assert not np.allclose(before[0].tensor_angstrom2_per_ev.conj(),before[1].tensor_angstrom2_per_ev)
    assert selected.metadata==raw.metadata and selected.sha256==raw.sha256
    assert Path(ref.source).read_bytes()==source_bytes
    assert selected.provenance()['direction_binding']['pair_state']=='minus'
    fresh=e.configure_mdff();assert fresh.reference==cfg
    assert fresh.validate_configuration()[0]==cfg
    fresh.close()
    direction(e,0,'0 0 1');e.cancel()
    assert e.rows()[0][4]==cfg and e.rows()[0][3]==(0,0,-1)
    direction(e,0,'0 0 1');e.apply()
    assert not e.rows()[0][4].pair_reversed and e.rows()[1]==other


def test_failed_multi_group_apply_is_atomic_and_draft_is_not_saved(window,tmp_path):
    structure,sites=sites_for(tmp_path);controls(window,structure);e=bind(window,sites)
    accepted=e.accepted_site_groups;rows=e._accepted_rows;status=dict(e._mdff_status)
    direction(e,0,'0 0 -1');direction(e,1,'1 0 0')
    with pytest.raises(ValueError,match=r'Group Cr-down: requested.*source axis.*frame_to_crystal.*MDFF Editor'):
        e.apply()
    assert e.accepted_site_groups is accepted and e._accepted_rows==rows and e._mdff_status==status
    assert e.rows()[1][3]==(1,0,0)
    with pytest.raises(ValueError,match='Apply or Cancel'):capture_configuration(window)
    e.cancel();assert e.rows()==rows
    assert [r['magnetization'] for r in capture_configuration(window)['group_records']]==[r[3] for r in rows]
    e.flip_all()
    with pytest.raises(ValueError,match='Apply or Cancel'):capture_configuration(window)
    e.cancel();assert not e.reverse_magnetization


def test_restored_accepted_selection_is_used_by_small_recalculation(window,tmp_path,app):
    structure,sites=sites_for(tmp_path);controls(window,structure);e=bind(window,sites)
    direction(e,0,'0 0 -1');e.apply()
    e.requested_energy_ev=ENERGY.copy()
    before=e.rows();frame=source_for(before[0][4]).metadata['frame_to_crystal']
    state=load_configuration(save_configuration(capture_configuration(window),tmp_path/'project'))
    assert state['ready_for_calculation'],state['issues']
    restore_configuration(window,state);e=window.structure_viewer.editor
    assert e.rows()==before and e.rows()[0][4].pair_reversed
    assert source_for(e.rows()[0][4]).metadata['frame_to_crystal']==frame
    window.start_emcd();result=finish(window,app)
    assert np.isfinite(result['spectra']['I_A_plus']).all()
    for key in RAW:
        reconstructed=sum(g['metadata']['multiplicity']*g['spectra'][key] for g in result['groups'].values())/2
        np.testing.assert_allclose(reconstructed,result['spectra'][key],rtol=2e-12,atol=1e-15)
    assert result['groups']['Cr-up']['metadata']['source']['direction_binding']['pair_state']=='minus'
    assert 'direction_binding' not in result['groups']['Cr-down']['metadata']['source']


def test_reversal_requires_declared_pair_and_keeps_native_validation(tmp_path):
    cfg=settings_for_source(source(tmp_path,'Fe'))
    reversed_cfg=bind_group_direction(('Fe','Fe',(0,),(0,0,-1),cfg))
    with pytest.raises(ValueError):source_for(replace(reversed_cfg,pair_reversed=False))
    with pytest.raises(ValueError):source_for(replace(reversed_cfg,magnetization=(1,0,0)))
    with pytest.raises(ValueError):source_for(replace(reversed_cfg,pair_reversed='yes'))
    with pytest.raises(ValueError):settings_for_source(source(tmp_path,'missing',defect='missing'))
    assert validate_site_rows(__import__('ase').Atoms('Fe',cell=[3]*3,pbc=True),[('Fe','Fe',(0,),None,None)]) is None


def test_declared_xmcd_pair_uses_original_axis_declaration(tmp_path):
    from emcd_sim.imported_mdff import CONVENTION
    p=tmp_path/'Fe.xmcd';energy=np.linspace(704,730,9)
    right=np.full(9,1.1);left=np.full(9,.9)
    np.savetxt(p,np.column_stack((energy,right,left,right-left,right+left)))
    import hashlib
    declaration=dict(element='Fe',edge='L2,3',selected_ev={'L3':710.,'L2':723.},
        magnetization_crystal=[0,0,1],handedness='RP_minus_LP_in_declared_axis',eta=1.,beta=0.,
        normalization='source_max_nonmagnetic',convention=CONVENTION,source='Explicit synthetic RP/LP',
        validity='Synthetic axisymmetric proxy only',status='synthetic',source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
        reference_tensor_scale_angstrom2_per_ev=3.,magnetic_state='uniform_fm',reversal_assumption='axisymmetric_XMCD_odd_shared_XAS')
    cfg=settings_for_provider(p,'xmcd',declaration)
    selected=bind_group_direction(('Fe','Fe',(0,),(0,0,-1),cfg))
    assert selected.pair_reversed and selected.provider_declaration==declaration
    plus=source_for(cfg).tensors(ENERGY,np.eye(3),(0,0,1))
    minus=source_for(selected).tensors(ENERGY,np.eye(3),(0,0,-1))
    np.testing.assert_array_equal(minus[0].tensor_angstrom2_per_ev,plus[1].tensor_angstrom2_per_ev)


def test_manual_editor_refreshes_selected_pair_after_direction_binding(window,tmp_path):
    from emcd_sim.multisite import MultiSiteIonization
    structure,sites=sites_for(tmp_path);a,b=sites.groups
    path=Path(a.mdff_reference.source);d=json.loads(path.read_text())
    d['manual_constant_pair_editor']=1
    for key in ('T_plus','T_minus','T_even'):
        for part in ('real','imag'):d[key][part]=[d[key][part][2]]*len(d['energy_ev'])
    path.write_text(json.dumps(d),encoding='utf-8')
    a=replace(a,mdff_reference=settings_for_source(path))
    controls(window,structure);e=bind(window,MultiSiteIonization(structure,[a,b]))
    dialog=e.configure_mdff();assert dialog.manual_mode.currentIndex()==2
    native=source_for(a.mdff_reference)
    direction(e,0,'0 0 -1')
    cfg=dialog.apply_configuration();assert cfg is not None,dialog.status.text()
    assert cfg.pair_reversed and dialog.reference==cfg
    np.testing.assert_array_equal(dialog.pair[0].matrix(),native.minus.tensor_angstrom2_per_ev[0])
    np.testing.assert_array_equal(dialog.pair[1].matrix(),native.plus.tensor_angstrom2_per_ev[0])
    e.apply();assert e.rows()[1][4] is b.mdff_reference


def test_changed_source_still_requires_explicit_review_for_reversed_binding(window,tmp_path):
    structure,sites=sites_for(tmp_path);controls(window,structure);e=bind(window,sites)
    direction(e,0,'0 0 -1');e.apply();dialog=e.configure_mdff()
    old=dialog.reference;path=Path(old.source);d=json.loads(path.read_text())
    for key in ('T_plus','T_minus','T_even'):
        for part in ('real','imag'):d[key][part]=(2*np.asarray(d[key][part])).tolist()
    path.write_text(json.dumps(d),encoding='utf-8')
    assert dialog.apply_configuration() is None
    assert 'Source identity changed' in dialog.status.text() and not dialog.declaration.isChecked()
    assert e.accepted_site_groups.groups[0].mdff_reference==old
    dialog.declaration.setChecked(True);new=dialog.apply_configuration()
    assert new is not None,dialog.status.text()
    assert new.pair_reversed and new.source_sha256!=old.source_sha256
