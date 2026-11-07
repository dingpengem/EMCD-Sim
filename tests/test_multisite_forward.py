"""Small production-pipeline integrations with synthetic, declared sources."""
from dataclasses import replace
import hashlib
import json

import numpy as np
import pytest
from ase.build import bulk

from emcd_sim.cancellation import Cancelled
from emcd_sim.gui import forward_pipeline, propagation
from emcd_sim.gui.emcd_forward import calculate
from emcd_sim.gui.forward_pipeline import calculate_multisite, MultiSiteForwardSettings
from emcd_sim.gui.generalized_forward import settings_for_source
from emcd_sim.gui.geometry import Structure, Settings
from emcd_sim.multisite import IonizationSiteGroup, MultiSiteIonization
from emcd_sim.multisite_single_channeling import run_multisite_with_coherence
from single_element_helpers import document


ENERGY=np.array([710.,716.,723.])
RAW_KEYS=('I_A_plus','I_B_plus','I_A_minus','I_B_minus')
PARITY_KEYS=('N_A','N_B','M_A','M_B','D_mag','D_nonmag','D_raw','Sigma_ref')


def source(tmp_path,name,element='Ni',down=False,scale=1.):
    d=document(element)
    if down:
        d['magnetization_crystal']=[0,0,-1]
        d['T_plus'],d['T_minus']=d['T_minus'],d['T_plus']
    for key in ('T_plus','T_minus','T_even'):
        for part in ('real','imag'):d[key][part]=(scale*np.asarray(d[key][part])).tolist()
    path=tmp_path/(name+'.json')
    path.write_text(json.dumps(d),encoding='utf-8')
    return settings_for_source(path)


def configuration(**kwargs):
    fields=dict(grid=9,depth=9,subpixels=8,fft_grid=16,slice_step=.01,
                halfwidth=.7,centers=((.2,.2),(.2,-.2)),radius=.12,
                worker_mode='manual',parallel_workers=1)
    fields.update(kwargs)
    return MultiSiteForwardSettings(**fields)


def system(tmp_path,element='Ni'):
    structure=Structure(bulk(element,'fcc' if element=='Ni' else 'bcc',a=3.524 if element=='Ni' else 2.88,cubic=True))
    settings=Settings(zone=(0,0,1),target=(2,0,0) if element=='Ni' else (1,1,0),
                      tilt=(-5,7),voltage=200,thickness=.15,beam_cutoff=.6,potential_cutoff=1.2)
    if element=='Ni':
        refs=[source(tmp_path,'Ni')]
        groups=[IonizationSiteGroup('Ni','Ni',(0,1,2,3),refs[0],(0,0,1),4)]
    else:
        refs=[source(tmp_path,'up','Cr'),source(tmp_path,'down','Cr',down=True)]
        groups=[IonizationSiteGroup('up','Cr',(0,),refs[0],(0,0,1),1),
                IonizationSiteGroup('down','Cr',(1,),refs[1],(0,0,-1),1)]
        structure.atoms.set_initial_magnetic_moments([1,-1])
    return structure,settings,MultiSiteIonization(structure,groups),refs


@pytest.mark.parametrize('method',['bloch','fft-multislice'])
def test_single_group_ni_matches_existing_pipeline(tmp_path,method):
    structure,settings,sites,refs=system(tmp_path)
    cfg=configuration(propagation=method)
    old_cfg=replace(refs[0],**{key:getattr(cfg,key) for key in (
        'grid','depth','subpixels','fft_grid','slice_step','halfwidth','centers','radius',
        'worker_mode','parallel_workers','propagation')})
    before=calculate(structure,settings,old_cfg,energy_ev=ENERGY)
    result=calculate_multisite(structure,settings,sites,cfg,energy_ev=ENERGY)
    for key in RAW_KEYS+PARITY_KEYS:
        np.testing.assert_allclose(result['spectra'][key],before['spectra'][key],rtol=2e-13,atol=1e-16)
    for edge in ('L3','L2'):
        for key in ('I_plus','I_minus','I_mag','I_nonmag'):
            np.testing.assert_allclose(result['maps']['Ni:'+edge][key],before['maps'][edge][key],rtol=2e-13,atol=1e-16)
    assert result['metadata']['multisite']['normalization']=='mean_per_selected_ionizing_atom'
    assert result['metadata']['multisite']['selected_atom_count']==4
    assert result['metadata']['integration']=='fractional'


def test_afm_both_solvers_reuse_one_propagation_and_match_patch2a(tmp_path,monkeypatch):
    structure,settings,sites,_=system(tmp_path,'Cr')
    calls=[]
    original=propagation.propagate
    def counted(*args,**kwargs):
        calls.append(args[2].propagation)
        return original(*args,**kwargs)
    monkeypatch.setattr(propagation,'propagate',counted)
    result=calculate_multisite(structure,settings,sites,configuration(propagation='both'),energy_ev=ENERGY)
    assert calls==['bloch','fft-multislice']
    for method,method_result in result['methods'].items():
        qx,qy=method_result['qx'],method_result['qy']
        dq2=(qx[0,1]-qx[0,0])**2
        rotation=np.asarray(method_result['metadata']['frame'])
        sums={key:np.zeros(len(ENERGY)) for key in RAW_KEYS}
        for group in sites.groups:
            independent=run_multisite_with_coherence(method_result['model'],MultiSiteIonization(structure,[group]),
                method_result['coherence'],ENERGY,qx,qy,crystal_to_microscope=rotation,thickness_nm=settings.thickness)
            entry=method_result['groups'][group.group_id]
            assert entry['metadata']['indices']==group.indices
            assert entry['metadata']['normalization']=='mean_per_selected_atom'
            assert entry['metadata']['source']['sha256']==group.mdff_reference.source_sha256
            for state in ('plus','minus'):
                for detector in ('A','B'):
                    key=f'I_{detector}_{state}'
                    expected=np.sum(independent['total'][state]*method_result['weights'][detector],axis=(1,2))*dq2
                    np.testing.assert_allclose(entry['spectra'][key],expected,rtol=2e-13)
                    sums[key]+=group.multiplicity*expected
        for key in RAW_KEYS:
            np.testing.assert_allclose(method_result['spectra'][key],sums[key]/2,rtol=2e-13)
            np.testing.assert_allclose(method_result['weighted_sum']['spectra'][key],sums[key],rtol=2e-13)
        # Equal event phases on BCC elastic support, opposite explicit states.
        np.testing.assert_allclose(method_result['spectra']['M_A'],0,atol=1e-16)
        assert set(method_result['maps'])=={'up:L3','up:L2','down:L3','down:L2'}
        assert method_result['metadata']['multisite']['selected_atom_count']==2
    assert result['methods']['fft-multislice']['metadata']['fft']['renormalized'] is False
    assert result['comparison']['spectra']['I_A_plus']['l2_relative']<.015


def test_global_reversal_of_unequal_sublattices(tmp_path):
    structure,settings,sites,_=system(tmp_path,'Cr')
    stronger=source(tmp_path,'stronger','Cr',down=True,scale=2.)
    sites=MultiSiteIonization(structure,[sites.groups[0],replace(sites.groups[1],mdff_reference=stronger)])
    cfg=configuration(angular_maps=False)
    plus=calculate_multisite(structure,settings,sites,cfg,energy_ev=ENERGY)
    minus=calculate_multisite(structure,settings,sites,cfg,energy_ev=ENERGY,reverse_magnetization=True)
    assert np.linalg.norm(plus['spectra']['M_A'])>1e-8*np.linalg.norm(plus['spectra']['N_A'])
    assert plus['metadata']['scientific_status']=='SYNTHETIC TEST ONLY'
    for detector in ('A','B'):
        np.testing.assert_allclose(plus['spectra'][f'I_{detector}_plus'],minus['spectra'][f'I_{detector}_minus'])
        np.testing.assert_allclose(plus['spectra']['N_'+detector],minus['spectra']['N_'+detector])
        np.testing.assert_allclose(plus['spectra']['M_'+detector],-minus['spectra']['M_'+detector])
    for name in ('up','down'):
        np.testing.assert_allclose(plus['groups'][name]['spectra']['I_A_plus'],minus['groups'][name]['spectra']['I_A_minus'])


def test_detector_only_reduction_matches_full_grid(tmp_path):
    structure,settings,sites,_=system(tmp_path,'Cr')
    full=calculate_multisite(structure,settings,sites,configuration(),energy_ev=ENERGY)
    sparse=calculate_multisite(structure,settings,sites,configuration(angular_maps=False),energy_ev=ENERGY)
    assert sparse['maps']=={}
    for key in RAW_KEYS:
        np.testing.assert_allclose(full['spectra'][key],sparse['spectra'][key],rtol=2e-13)
        for name in ('up','down'):
            np.testing.assert_allclose(full['groups'][name]['spectra'][key],sparse['groups'][name]['spectra'][key],rtol=2e-13)


@pytest.mark.parametrize('failure',['uncovered','nan','unordered','zero','incident','species','axis','frame',
                                    'identity','assignment','occupancy','ms_double','map_energy'])
def test_invalid_inputs_fail_before_geometry_or_propagation(tmp_path,monkeypatch,failure):
    structure,settings,sites,refs=system(tmp_path)
    cfg=configuration()
    energy=ENERGY
    if failure=='uncovered':energy=[703.,710.]
    elif failure=='nan':energy=[710.,np.nan]
    elif failure=='unordered':energy=[723.,710.]
    elif failure=='zero':energy=[0.,710.]
    elif failure=='incident':energy=[710.,200000.]
    elif failure=='species':
        different=source(tmp_path,'Fe','Fe')
        sites=MultiSiteIonization(structure,[replace(sites.groups[0],mdff_reference=different)])
    elif failure=='axis':
        sites=MultiSiteIonization(structure,[replace(sites.groups[0],magnetization=(1,0,0))])
    elif failure in ('frame','identity'):
        path=tmp_path/'Ni.json'
        if failure=='frame':
            d=json.loads(path.read_text())
            d.update(basis='declared_local',frame_to_crystal=np.diag([1,1,-1]).tolist())
            path.write_text(json.dumps(d))
            cfg_source=replace(refs[0],source_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            sites=MultiSiteIonization(structure,[replace(sites.groups[0],mdff_reference=cfg_source)])
        else:path.write_text(path.read_text()+' ')
    elif failure=='assignment':structure.atoms.positions[0,0]+=.1
    elif failure=='occupancy':structure.atoms.info['occupancy']={'0':{'Ni':.5}}
    elif failure=='ms_double':cfg=replace(cfg,channeling_model='double',propagation='fft-multislice')
    elif failure=='map_energy':cfg=replace(cfg,selected_edges=(('outside',711.),))
    def forbidden(*args,**kwargs):
        pytest.fail('Invalid input reached expensive calculation/preflight')
    monkeypatch.setattr(forward_pipeline,'geometry',forbidden)
    monkeypatch.setattr(forward_pipeline,'elastic_model',forbidden)
    monkeypatch.setattr(propagation,'numerical_info',forbidden)
    monkeypatch.setattr(propagation,'propagate',forbidden)
    with pytest.raises(ValueError):
        calculate_multisite(structure,settings,sites,cfg,energy_ev=energy)


def test_cancellation_inside_bounded_contraction_prevents_second_solver(tmp_path,monkeypatch):
    import emcd_sim.multisite_single_channeling as contraction

    structure,settings,sites,_=system(tmp_path,'Cr')
    stop=False
    calls=[]
    original_propagate=propagation.propagate
    original_kernel=contraction._tensor_angular_maps
    def counted(*args,**kwargs):
        calls.append(args[2].propagation)
        return original_propagate(*args,**kwargs)
    def kernel(*args):
        nonlocal stop
        assert len(args[-1])<=64
        value=original_kernel(*args)
        stop=True
        return value
    monkeypatch.setattr(propagation,'propagate',counted)
    monkeypatch.setattr(contraction,'_tensor_angular_maps',kernel)
    with pytest.raises(Cancelled):
        calculate_multisite(structure,settings,sites,configuration(propagation='both'),energy_ev=ENERGY,cancelled=lambda:stop)
    assert calls==['bloch']
