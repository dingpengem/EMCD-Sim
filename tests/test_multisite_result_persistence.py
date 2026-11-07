"""Lossless project IO of stored synthetic arrays; no new EMCD calculations."""
from copy import deepcopy
from dataclasses import asdict, replace
import json
from pathlib import Path

import numpy as np
import pytest
from ase import Atoms

from emcd_sim.multisite import IonizationSiteGroup, MultiSiteIonization
from emcd_sim.multisite_spectrum import ModeledEdgeWindow
from emcd_sim.mdff_providers import load_provider
from emcd_sim.gui import project_io as io
from emcd_sim.gui.geometry import Structure
from emcd_sim.gui.emcd_forward import ForwardSettings
from emcd_sim.gui.multisite_results import SPECTRAL_KEYS, spectral_series, covered_segments, draw_totals
from emcd_sim.gui.runtime import PHYSICS_CONVENTION
from test_multisite_result_selection import stored_result
from test_multisite_configuration import tensor_source


def stored_project(tmp_path,kind='Fe3O4',channeling='single',both=False,manual=False,omit=False):
    r=stored_result('FeNi' if kind=='FeNi' else 'Fe3O4',omit=omit)
    if kind=='Cr':
        r['model'].elastic.crystal.species=('Cr','Cr')
        r['groups']={name:entry for name,entry in zip(('Cr__up','Cr/down'),r['groups'].values())}
        old_channels=list(r['metadata']['multisite']['channels'].values())
        r['metadata']['multisite']['channels']=dict(zip(r['groups'],old_channels))
        for entry in r['groups'].values():entry['metadata'].update(element='Cr',multiplicity=1,contribution_weight=.5)
        r['metadata']['multisite']['selected_atom_count']=2
        for key in SPECTRAL_KEYS:r['spectra'][key]=sum(.5*g['spectra'][key] for g in r['groups'].values())
    species=r['model'].elastic.crystal.species
    atoms=Atoms(species,scaled_positions=np.arange(len(species)*3).reshape(-1,3)/24,cell=[8,8,8],pbc=True)
    structure=Structure(atoms,source='Synthetic stored arrays; not predicted spectra')
    r['structure_snapshot']=io.structure_snapshot(structure);r['config']=replace(r['config'],channeling_model=channeling,
        angular_maps=True,selected_edges=(('Fe__L3',710.),),fft_generators=((2,0,0),(0,2,0)),propagation='both' if both else 'bloch')
    axis=np.array([-.2,0.,.2]);r['qx'],r['qy']=np.meshgrid(axis,axis)
    r['weights']={'A':np.full((3,3),.5),'B':np.full((3,3),.25)}
    r['coherence']=np.array([[.8,.03j],[-.03j,.2]])
    r['amplitudes']=np.array([[1,0],[.8,.2j]],complex);r['depth_nm']=np.array([0.,1.])
    r['metadata'].update(mdff_provider='multisite',beam_hkl=[[0,0,0],[2,0,0]],g=[[0.,0.],[.25,0.]],frame=np.eye(3).tolist(),
        za_q=[0.,0.],transmitted_q=[0.,0.],angular_maps_calculated=True,physics_convention=PHYSICS_CONVENTION,
        software_version='stored-test-version',software_commit='stored-test-commit',numerics={'note':'Stored fixture; no propagation'})
    groups=[];offset=0
    for i,(gid,entry) in enumerate(r['groups'].items()):
        meta=entry['metadata'];n=meta['multiplicity'];indices=tuple(range(offset,offset+n));offset+=n
        shift=140. if meta['element']=='Ni' else 0.
        cfg=tensor_source(tmp_path,'source'+str(i),element=meta['element'],axis=meta['magnetization_crystal'],shift=shift,scale=i+1,manual=manual)
        meta.update(indices=indices,source=load_provider(cfg).provenance())
        entry.update(qx=r['qx'],qy=r['qy'],weights=r['weights'])
        groups.append(IonizationSiteGroup(gid,meta['element'],indices,cfg,meta['magnetization_crystal'],n))
    def maps(entry):
        s=entry['spectra']
        return {'Fe__L3':{key:np.full((3,3),s[field][0]) for key,field in
            [('I_plus','I_A_plus'),('I_minus','I_A_minus'),('I_mag','M_A'),('I_nonmag','N_A')]}}
    r['maps']=maps(r)
    for entry in r['groups'].values():entry['maps']=maps(entry)
    n=r['metadata']['multisite']['selected_atom_count']
    r['weighted_sum']=dict(spectra={key:value.copy() if key=='energy_ev' else value*n for key,value in r['spectra'].items()},
        maps={edge:{key:value*n for key,value in fields.items()} for edge,fields in r['maps'].items()},
        metadata={'normalization':'sum_over_selected_atoms'})
    # Retain even a last-bit difference in the independently accumulated sum.
    r['weighted_sum']['spectra']['I_A_plus'][0]=np.nextafter(r['weighted_sum']['spectra']['I_A_plus'][0],np.inf)
    r['metadata']['mdff']={gid:entry['metadata'] for gid,entry in r['groups'].items()}
    r['configuration']=dict(structure=structure,settings=r['settings'],config=r['config'],site_groups=MultiSiteIonization(atoms,groups),
        magnetization_mode='local',reverse_magnetization=False,energy_ev=r['spectra']['energy_ev'],
        energy_windows={gid:ModeledEdgeWindow(tuple(c['modeled_window_ev'])) for gid,c in r['metadata']['multisite']['channels'].items() if c['modeled_window_ev'] is not None})
    if kind=='Cr':
        r['metadata']['multisite']['global_reversal']=True;r['configuration']['reverse_magnetization']=True
        for entry in [r,*r['groups'].values(),r['weighted_sum']]:
            s=entry['spectra']
            for detector in ('A','B'):
                a,b='I_'+detector+'_plus','I_'+detector+'_minus';s[a],s[b]=s[b],s[a]
                s['M_'+detector]=-s['M_'+detector]
            s['D_mag']=-s['D_mag'];s['D_raw']=s['I_A_plus']-s['I_B_plus']
            for fields in entry['maps'].values():
                fields['I_plus'],fields['I_minus']=fields['I_minus'],fields['I_plus'];fields['I_mag']=-fields['I_mag']
    if both:
        other=deepcopy(r);other['method']='fft-multislice'
        for entry in [other,*other['groups'].values(),other['weighted_sum']]:
            for key in SPECTRAL_KEYS:entry['spectra'][key]*=2
            for fields in entry['maps'].values():
                for key in fields:fields[key]*=2
        r=dict(r,methods={'bloch':r,'fft-multislice':other},comparison={'note':'Synthetic distinct stored solver arrays'})
    return r


@pytest.fixture(autouse=True)
def no_simulation(monkeypatch):
    def forbidden(*a,**k):pytest.fail('Project IO invoked a simulation')
    monkeypatch.setattr('emcd_sim.gui.geometry.elastic_model',forbidden)
    monkeypatch.setattr('emcd_sim.gui.forward_pipeline.calculate_multisite',forbidden)
    monkeypatch.setattr('emcd_sim.gui.emcd_forward.calculate',forbidden)


def load_without_mdff(root,monkeypatch):
    def forbidden(*a,**k):pytest.fail('Saved-result loading read/rebuilt MDFF tensors')
    with monkeypatch.context() as patch:
        patch.setattr('emcd_sim.imported_mdff.ImportedMDFF.load',forbidden)
        patch.setattr('emcd_sim.mdff_providers.load_provider',forbidden)
        return io.load_project(root)


@pytest.mark.parametrize('kind,channeling',[('Cr','single'),('Fe3O4','double'),('FeNi','double')])
def test_multisite_lossless_roundtrip_all_signals_maps_and_selections(tmp_path,monkeypatch,kind,channeling):
    original=stored_project(tmp_path,kind,channeling,both=True)
    root=io.save_project(original,tmp_path/'project');loaded=load_without_mdff(root,monkeypatch)
    assert loaded['metadata']==json.loads(json.dumps(original['metadata']))
    assert loaded['config'].channeling_model==channeling and loaded['project_convention_status']['status']=='recorded-corrected'
    assert set(loaded['methods'])=={'bloch','fft-multislice'}
    for method,r in loaded['methods'].items():
        before=original['methods'][method]
        for key in ('qx','qy','coherence','depth_nm','amplitudes'):np.testing.assert_array_equal(r[key],before[key])
        for gid,entry in [('',r),*r['groups'].items(),('weighted_sum',r['weighted_sum'])]:
            reference=before if gid=='' else before['weighted_sum'] if gid=='weighted_sum' else before['groups'][gid]
            for key,value in reference['spectra'].items():
                np.testing.assert_array_equal(entry['spectra'][key],value)
                assert not entry['spectra'][key].flags.writeable
            for edge,fields in reference['maps'].items():
                for key,value in fields.items():np.testing.assert_array_equal(entry['maps'][edge][key],value)
        parts=spectral_series(r,('compare',None),compared=tuple(r['groups']))
        for key in SPECTRAL_KEYS:np.testing.assert_allclose(sum(p['spectra'][key] for p in parts),r['spectra'][key],rtol=1e-14,atol=1e-14)
        for element in {g['metadata']['element'] for g in r['groups'].values()}:
            assert spectral_series(r,('element',element))[0]['groups']
        for s in [r['spectra'],*(g['spectra'] for g in r['groups'].values())]:
            np.testing.assert_allclose(s['M_A'],(s['I_A_plus']-s['I_A_minus'])/2,atol=1e-14)
            np.testing.assert_allclose(s['N_A'],(s['I_A_plus']+s['I_A_minus'])/2,atol=1e-14)
            np.testing.assert_allclose(s['D_raw'],s['D_mag']+s['D_nonmag'],atol=1e-14)
        assert r['metadata']['multisite']['selected_atom_count']==before['metadata']['multisite']['selected_atom_count']
    assert [row['group_id'] for row in loaded['configuration']['group_records']]==list(original['groups'])
    assert loaded['configuration']['reverse_magnetization']==(kind=='Cr')
    # Restored method results can be saved again without changing arrays.
    again=load_without_mdff(io.save_project(loaded,tmp_path/'again'),monkeypatch)
    np.testing.assert_array_equal(again['groups'][next(iter(again['groups']))]['spectra']['I_A_plus'],loaded['groups'][next(iter(loaded['groups']))]['spectra']['I_A_plus'])


@pytest.mark.parametrize('defect',['missing','changed'])
def test_external_source_unavailable_keeps_views_but_blocks_rerun(tmp_path,monkeypatch,defect):
    from matplotlib.figure import Figure
    r=stored_project(tmp_path,'FeNi');root=io.save_project(r,tmp_path/'saved')
    path=Path(next(iter(r['groups'].values()))['metadata']['source']['path'])
    if defect=='missing':path.unlink()
    else:path.write_bytes(b'changed')
    loaded=load_without_mdff(root,monkeypatch)
    assert not io.source_status(loaded)['group:Fe']['verified']
    assert 'group:Fe source unavailable' in io.rerun_reason(loaded)
    fig=Figure();draw_totals(fig,loaded,'bloch','eels','',selection=('compare',None),compared=('Fe','Ni'),include_total=True,quantity=6)
    assert len(fig.axes[0].lines)==4  # Fe, Ni, and the two disconnected total windows.
    np.testing.assert_array_equal(loaded['spectra']['I_A_plus'],r['spectra']['I_A_plus'])


def test_energy_exclusions_and_portable_manual_sources(tmp_path,monkeypatch):
    r=stored_project(tmp_path,'FeNi',manual=True,omit=True);root=io.save_project(r,tmp_path/'portable')
    for group in r['groups'].values():Path(group['metadata']['source']['path']).unlink()
    loaded=load_without_mdff(root,monkeypatch)
    assert all(status['verified'] for status in io.source_status(loaded).values())
    assert loaded['configuration']['source_overrides']==loaded['source_overrides']
    assert io.rerun_reason(loaded)==''
    channels=loaded['metadata']['multisite']['channels']
    assert channels['Ni']['omitted_by_request'] and channels['Ni']['modeled_window_ev'] is None
    assert len(covered_segments(loaded,loaded['spectra']['energy_ev']))==1
    assert not np.any(covered_segments(loaded,loaded['spectra']['energy_ev'])[0][3:])
    assert loaded['metadata']['multisite']['selected_atom_count']==2


def test_embedded_atomic_evidence_uses_existing_portable_source_fallback(tmp_path,monkeypatch):
    from PySide6 import QtWidgets
    from emcd_sim.gui.atomic_editor import AtomicParameterEditor
    from emcd_sim.gui.generalized_forward import ProviderSettings
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    editor=AtomicParameterEditor(lambda:tmp_path)
    try:
        editor.load_document(Path(__file__).resolve().parents[1]/'docs/examples/synthetic_fe_atomic_parameters.json')
        doc=editor.document()  # Parameters only; do not generate MDFF tensors.
        source=tmp_path/'accepted-atomic.json';io._json(source,doc);raw=source.read_bytes();digest=io.sha256(source)
        cfg=ProviderSettings(model='atomic',source=str(source),source_sha256=digest,ionizing_element='Fe',
            core_edge='L2,3',magnetic_state='uniform_fm',magnetization=(0,0,1),axis_declared=True,l3=710.,l2=723.)
        r=stored_project(tmp_path);groups=list(r['configuration']['site_groups'].groups)
        groups[1]=replace(groups[1],mdff_reference=cfg)
        r['configuration']['site_groups']=MultiSiteIonization(r['configuration']['structure'],groups)
        r['groups']['Fe(B)']['metadata']['source'].update(path=str(source),sha256=digest,provider_identity='atomic',
            atomic_parameter_source_utf8=raw.decode('utf-8'))
        source.unlink()
        root=io.save_project(r,tmp_path/'atomic-evidence');loaded=load_without_mdff(root,monkeypatch)
        effective=Path(loaded['source_overrides']['group:Fe(B)'])
        assert effective.read_bytes()==raw and io.source_status(loaded)['group:Fe(B)']['verified']
    finally:editor.close();editor.deleteLater();app.processEvents()


def test_legacy_single_element_project_uses_original_layout_and_loader(tmp_path,monkeypatch):
    r=stored_project(tmp_path)
    r['config']=ForwardSettings(model='atomic',l3=710,l2=723,energy_scope='full')
    r['metadata'].pop('multisite');r['metadata'].pop('mdff_provider');r['metadata']['mdff']=asdict(r['config'])
    r.pop('groups');r.pop('weighted_sum');r.pop('configuration')
    atoms=Atoms('Ni4',scaled_positions=[[0,0,0],[0,.5,.5],[.5,0,.5],[.5,.5,0]],cell=[3.52]*3,pbc=True)
    r['structure_snapshot']=io.structure_snapshot(Structure(atoms))
    r['maps']={'L3':r['maps']['Fe__L3'],'L2':r['maps']['Fe__L3']}
    root=io.save_project(r,tmp_path/'legacy-ni');loaded=load_without_mdff(root,monkeypatch)
    assert loaded['config']==r['config'] and 'groups' not in loaded
    assert loaded['model'].elastic.crystal.species==('Ni',)*4
    for key,value in r['spectra'].items():np.testing.assert_array_equal(loaded['spectra'][key],value)


def test_older_in_memory_multisite_arrays_do_not_invent_provider_configs(tmp_path,monkeypatch):
    r=stored_project(tmp_path);r.pop('configuration')
    loaded=load_without_mdff(io.save_project(r,tmp_path/'arrays-only'),monkeypatch)
    np.testing.assert_array_equal(loaded['groups']['Fe(A)']['spectra']['I_A_plus'],r['groups']['Fe(A)']['spectra']['I_A_plus'])
    assert 'configuration' not in loaded
    assert 'provider configuration declarations are unavailable' in io.rerun_reason(loaded)


def test_stale_reversal_configuration_is_not_saved_as_the_calculated_state(tmp_path):
    r=stored_project(tmp_path);r['configuration']['reverse_magnetization']=True
    with pytest.raises(ValueError,match='reversal differs'):io.save_project(r,tmp_path/'stale')
    assert not (tmp_path/'stale').exists()
