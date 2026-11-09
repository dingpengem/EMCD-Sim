"""Selection identities over stored arrays only; no scientific calculations."""
from copy import deepcopy
from dataclasses import replace
import numpy as np
import pytest
from PySide6 import QtCore,QtWidgets

from test_multisite_result_selection import app,view,stored_result,spectra
from emcd_sim.gui.results import ResultsView
from emcd_sim.gui.generalized_forward import ImportedSettings
from emcd_sim.gui.multisite_results import angular_choices,total_energy_samples,SPECTRAL_KEYS


CASES=[
    [('one','Cu',{'K':8980.})],
    [('alpha','Zn',{'K':9659.}),('beta','Zn',{'K':9659.}),('gamma','Zn',{'K':9659.})],
    [('first','Cu',{'K':8980.}),('second','Cu',{'K':8981.})],
    [('close-a','Cu',{'K':8980.000001}),('close-b','Cu',{'K':8980.000002})],
    [('iron','Fe',{'L3':708.1}),('nickel','Ni',{'L3':852.7}),('oxygen','O',{'K':532.})],
    [('equal-a','Co',{'K':7709.}),('equal-b','Co',{'K':7709.})],
]


def stored_maps(specs):
    result=stored_result();selected=tuple((gid+':'+edge,float(e)) for gid,_,samples in specs for edge,e in samples.items())
    energy=np.unique([e for _,e in selected]);result['config']=replace(result['config'],selected_edges=selected,angular_maps=True)
    qx,qy=np.meshgrid([-1.,0.,1.],[-1.,0.,1.]);result.update(qx=qx,qy=qy,weights=dict(A=(qy>0).astype(float),B=(qy<0).astype(float)))
    result['model'].elastic.crystal.g_vector=lambda hkl:np.array([1.,0.,0.])
    result['model'].elastic.crystal.species=tuple(element for _,element,_ in specs)
    result['groups']={};channels={};n=len(specs)
    for gid,element,samples in specs:
        lo,hi=min(samples.values()),max(samples.values());mask=(energy>=lo)&(energy<=hi)
        # Deliberately equal group responses: equality must never define identity.
        base=10+qx*qx;odd=.2*qy
        maps={key:dict(I_plus=(base+odd)*active,I_minus=(base-odd)*active,I_mag=odd*active,I_nonmag=base*active)
              for key,e in selected for active in [lo<=e<=hi]}
        result['groups'][gid]=dict(maps=maps,spectra=spectra(energy,mask=mask),metadata=dict(element=element,
            multiplicity=1,indices=(len(result['groups']),),magnetization_crystal=(0,0,1),normalization='mean_per_selected_atom',
            contribution_weight=1/n,source=dict(element=element,edge='/'.join(samples),selected_ev=samples,
            path=gid+'.json',source='Stored selection fixture',status='synthetic',units='relative',normalization='per_atom_relative',frame_to_crystal=np.eye(3).tolist())))
        channels[gid]=dict(modeled_window_ev=[lo,hi],active_energy_mask=mask.tolist(),omitted_by_request=False)
    result['metadata']['multisite'].update(channels=channels,selected_atom_count=n)
    result['maps']={key:{field:sum(g['maps'][key][field]/n for g in result['groups'].values())
                        for field in ('I_plus','I_minus','I_mag','I_nonmag')} for key,_ in selected}
    result['spectra']=dict(energy_ev=energy,**{key:sum(g['spectra'][key]/n for g in result['groups'].values()) for key in SPECTRAL_KEYS})
    return result


@pytest.mark.parametrize('specs',CASES)
def test_general_total_energy_rule_and_independent_groups(specs):
    result=stored_maps(specs);original=deepcopy(result['maps']);choices=angular_choices(result)
    assert len(choices)==len(result['spectra']['energy_ev'])
    assert len({label for label,_ in choices})==len(choices)
    assert all(gid not in label for label,_ in choices for gid,_,_ in specs)
    assert len(angular_choices(result,True))==sum(len(samples) for _,_,samples in specs)
    records=total_energy_samples(result)
    assert {r['energy_ev'] for r in records}==set(result['spectra']['energy_ev'])
    if len({element for _,element,_ in specs})>1:
        assert all(r['partial'] and 'modeled channels' in r['label'] for r in records)
    for key,fields in original.items():
        for field,value in fields.items():np.testing.assert_array_equal(result['maps'][key][field],value)


def test_alias_restore_switching_context_and_export(view,monkeypatch,tmp_path):
    specs=[('origin-a','Cu',{'K':8980.,'nearby':8981.}),('origin-b','Cu',{'K':8980.,'nearby':8981.})]
    result=stored_maps(specs);other=deepcopy(result)
    for fields in other['maps'].values():
        for key in fields:fields[key]*=2
        fields['I_plus'],fields['I_minus']=fields['I_minus'],fields['I_plus']
        fields['I_mag']=-fields['I_mag']
    other['metadata']['multisite']['global_reversal']=True
    result=dict(result,methods={'bloch':result,'fft-multislice':other})
    monkeypatch.setattr('emcd_sim.gui.results.decorate_reciprocal_map',lambda *a,**k:None)
    widget=ResultsView(view.owner,'maps');widget.set_result(result)
    assert widget.choice.count()==2
    # An older duplicate key restores the same energy through the canonical alias.
    widget.restore_map_options(dict(scope='total',group_id=None,edge='origin-b:nearby'))
    assert widget.map_options()['energy_ev']==8981. and widget.map_options()['edge']=='origin-a:nearby'
    before=np.array(widget.figure.axes[0].images[0].get_array())
    widget.map_scope.setCurrentIndex(1);assert widget.map_options()['energy_ev']==8981.
    widget.map_scope.setCurrentIndex(2);assert widget.map_options()['energy_ev']==8981.
    widget.restore_map_options(dict(scope='mean',group_id='origin-a',edge='origin-b:nearby'))
    assert widget.map_options()['group_id']=='origin-a' and widget.map_options()['energy_ev']==8981.
    widget.map_scope.setCurrentIndex(0);np.testing.assert_array_equal(widget.figure.axes[0].images[0].get_array(),before)
    widget.method.setCurrentIndex(1)
    assert widget.map_options()['method']=='fft-multislice' and widget.map_options()['energy_ev']==8981.
    np.testing.assert_array_equal(widget.figure.axes[0].images[0].get_array(),-2*before)
    assert widget.figure._emcd_display_metadata['global_reversal'] is True
    saved=[];monkeypatch.setattr(QtWidgets.QFileDialog,'getExistingDirectory',lambda *a:str(tmp_path))
    monkeypatch.setattr('emcd_sim.gui.project_io.save_project',lambda r,p:saved.append(r))
    widget.export_derived();assert saved[0]['display_state']['angular_selection']==widget.map_options()
    assert saved[0]['maps'] is result['maps']
    widget.restore_map_options(dict(scope='total',edge='no-longer-present',energy_ev=99999.,method='bloch'))
    assert widget.choice.currentIndex()==-1 and 'unavailable' in widget.display_note.text()
    widget.deleteLater()


def test_global_metadata_and_spectral_zoom_aliases(view,monkeypatch):
    result=stored_maps([('first','Cu',{'K':8980.}),('second','Cu',{'K':8981.})])
    monkeypatch.setattr('emcd_sim.gui.results.decorate_reciprocal_map',lambda *a,**k:None)
    view.set_result(result);assert view.choice.count()==3
    assert not view.restore_zoom('second:K zoom') and view.choice.currentData()==8981.
    view.redraw();assert view.figure.axes[-1].get_xlim()==(8976.,8986.)
    assert 'Ni' not in view.figure._suptitle.get_text()
    result=deepcopy(result);result['config']=ImportedSettings(selected_edges=(('K',8980.),),core_edge='K',energy_scope='full',ionizing_element='Cu')
    result.pop('groups');result['metadata'].pop('multisite');result['maps']={'K':result['maps']['first:K']}
    widget=ResultsView(view.owner,'maps');widget.set_result(result)
    assert widget.choice.count()==1 and widget.map_scope.isHidden()
    assert widget.choice.itemText(0)=='K · 8980.0000 eV'
    widget.deleteLater()
