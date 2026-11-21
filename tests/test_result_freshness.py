"""Saved-input comparisons only; stored synthetic arrays, never propagation."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from test_project_workflow import app,window,result_fixture,io,restore_configuration
from test_multisite_configuration import tensor_source
from emcd_sim.gui.multisite_run import applied_inputs,configuration_equal,saved_inputs_match
from emcd_sim.gui.project_configuration import _encode_config,_decode_config


def effective_result(w,tmp_path):
    r=result_fixture(tmp_path)
    # The IO fixture has three explicitly saved samples, below the GUI's
    # minimum uniform-point count. Preserve them through its native-grid mode.
    r['configuration']['config']=replace(r['config'],fft_generators=None,energy_sampling='native')
    restore_configuration(w,r['configuration'])
    cfg,sites,windows,reverse,signature=applied_inputs(w,w.forward_settings(prepare=False))
    state=dict(r['configuration'],config=cfg,site_groups=sites,energy_windows=windows)
    # Give the stored-array fixture the GUI's actual, resolved edge aliases.
    for entry in (r,*r.get('methods',{}).values()):
        entry['config']=cfg;entry['configuration']=state
        for part in (entry,*entry['groups'].values(),entry['weighted_sum']):
            part['maps']={cfg.selected_edges[0][0]:next(iter(part['maps'].values()))}
    r['gui_multisite_input']=signature
    return r,signature


@pytest.mark.parametrize('runtime_signature',[False,True])
def test_unchanged_roundtrip_and_real_gui_edits(window,tmp_path,runtime_signature):
    w=window;r,_=effective_result(w,tmp_path)
    r=io.load_project(io.save_project(r,tmp_path/'roundtrip'))
    restore_configuration(w,r['configuration']);cfg,_,_,_,sig=applied_inputs(w,w.forward_settings(prepare=False))
    if runtime_signature:r['gui_multisite_input']=sig
    a,b=_encode_config(cfg),_encode_config(r['config'])
    assert configuration_equal(cfg,r['config']),{k:(a[k],b[k]) for k in a if a[k]!=b[k]}
    assert saved_inputs_match(r,sig)
    w.emcd_result=r;w.emcd_stale()
    assert 'inputs match' in w.maps_view.label.text()
    before=w.spin['thickness'].value();w.spin['thickness'].setValue(before+1)
    assert 'STALE RESULT' in w.maps_view.label.text()
    w.spin['thickness'].setValue(before)
    assert 'inputs match' in w.maps_view.label.text()
    w.channeling_box.setCurrentIndex(1)
    assert 'STALE RESULT' in w.maps_view.label.text()
    w.channeling_box.setCurrentIndex(0)
    assert 'inputs match' in w.maps_view.label.text()


def test_unset_values_and_missing_evidence(window,tmp_path):
    r,sig=effective_result(window,tmp_path);cfg=r['config']
    assert configuration_equal(cfg,_decode_config(_encode_config(cfg)))
    assert not configuration_equal(cfg,replace(cfg,l3=710.))
    r.pop('configuration');r['gui_multisite_input']=sig[:4]
    assert saved_inputs_match(r,sig)  # older runtime tuple, full saved metadata
    r.pop('gui_multisite_input');assert saved_inputs_match(r,sig) is None
    window.emcd_result=r;window.emcd_stale()
    assert 'comparison unavailable' in window.maps_view.label.text(),window.memory_label.text()
    assert 'STALE RESULT' not in window.maps_view.label.text()


@pytest.mark.parametrize('change',['energy','window','reversal','membership','provider','frame'])
def test_real_local_changes_remain_detectable(window,tmp_path,change):
    r,sig=effective_result(window,tmp_path)
    groups,windows,reverse,excluded,energy=deepcopy(sig)
    if change=='energy':energy=(energy[0],energy[1]+.01,*energy[2:])
    elif change=='window':
        gid,w=windows[0];windows=((gid,replace(w,bounds_ev=(w.bounds_ev[0]-.1,w.bounds_ev[1]))),*windows[1:])
    elif change=='reversal':reverse=not reverse
    elif change=='membership':
        a,b=groups;groups=((*a[:2],(2,),*a[3:]),(*b[:2],(0,1),*b[3:]))
    else:
        a=groups[0]
        if change=='provider':ref=replace(a[5],eta=a[5].eta+.1)
        else:ref=tensor_source(tmp_path,'rotated',axis=a[3],frame=[[0,-1,0],[1,0,0],[0,0,1]])
        groups=((*a[:5],ref),*groups[1:])
    assert saved_inputs_match(r,(groups,windows,reverse,excluded,energy)) is False


def test_changed_source_is_not_hidden_by_saved_identity(window,tmp_path):
    r,_=effective_result(window,tmp_path);window.emcd_result=r
    source=Path(window.structure_viewer.editor.validated_site_groups.groups[0].mdff_reference.source)
    assert tmp_path in source.parents
    source.write_bytes(source.read_bytes()+b'\n')
    window.emcd_stale()
    assert 'STALE RESULT' in window.maps_view.label.text()
    assert not window.emcd_button.isEnabled()
