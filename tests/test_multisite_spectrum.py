"""Synthetic partial core-edge spectra; no absolute cross-element calibration."""
from dataclasses import replace
import json

import numpy as np
import pytest
from ase import Atoms

from emcd_sim.gui import forward_pipeline, propagation
from emcd_sim.gui.forward_pipeline import calculate_multisite
from emcd_sim.gui.generalized_forward import settings_for_source
from emcd_sim.gui.geometry import Structure, Settings
from emcd_sim.multisite import IonizationSiteGroup, MultiSiteIonization
from emcd_sim.multisite_single_channeling import run_multisite_with_coherence
from emcd_sim.multisite_spectrum import ModeledEdgeWindow, prepare_multisite_spectrum
from single_element_helpers import document
from test_multisite_forward import configuration, RAW_KEYS, PARITY_KEYS


FE_GRID=(710.,716.,723.)
NI_GRID=(840.,846.,853.)


def source(tmp_path, name, element, offset=0., scale=1., edge='L2,3', down=False):
    d=document(element)
    d['energy_ev']=(np.asarray(d['energy_ev'])+offset).tolist()
    d['selected_ev']={label:value+offset for label,value in d['selected_ev'].items()}
    if edge=='K':d.update(edge='K',selected_ev={'K':710.+offset})
    if down:
        d['magnetization_crystal']=[0,0,-1]
        d['T_plus'],d['T_minus']=d['T_minus'],d['T_plus']
    for key in ('T_plus','T_minus','T_even'):
        for part in ('real','imag'):d[key][part]=(scale*np.asarray(d[key][part])).tolist()
    path=tmp_path/(name+'.json')
    path.write_text(json.dumps(d),encoding='utf-8')
    return settings_for_source(path)


def system(tmp_path, same_element=False, fe_edge='L2,3'):
    structure=Structure(Atoms('Ni3' if same_element else 'FeNi2',
        scaled_positions=[(0,0,0),(.25,.2,.1),(.63,.54,.4)],cell=[4,4,4],pbc=True))
    settings=Settings(zone=(0,0,1),target=(1,0,0),tilt=(-5,7),voltage=200,
        thickness=.1,beam_cutoff=.31,potential_cutoff=.7)
    first=source(tmp_path,'first','Ni' if same_element else 'Fe',
        offset=0 if fe_edge=='L2,3' else 6400,edge=fe_edge)
    second=source(tmp_path,'second','Ni',offset=5 if same_element else 130,scale=3.,down=True)
    groups=[IonizationSiteGroup('A',first.ionizing_element,(0,),first,first.magnetization,1),
            IonizationSiteGroup('B','Ni',(1,2),second,second.magnetization,2)]
    return structure,settings,MultiSiteIonization(structure,groups)


def disjoint_windows(fe_offset=0.):
    return dict(A=ModeledEdgeWindow((704.+fe_offset,730.+fe_offset),tuple(e+fe_offset for e in FE_GRID)),
                B=ModeledEdgeWindow((834.,860.),NI_GRID))


def independently_accumulated(method,structure,settings,sites):
    """Compare each active channel against Patch 2A on its own covered grid."""
    energy=method['spectra']['energy_ev']
    sums={key:np.zeros(len(energy)) for key in RAW_KEYS}
    for group in sites.groups:
        entry=method['groups'][group.group_id]
        mask=np.asarray(entry['metadata']['coverage']['active_energy_mask'])
        if not mask.any():continue
        raw=run_multisite_with_coherence(method['model'],MultiSiteIonization(structure,[group]),
            method['coherence'],energy[mask],method['qx'],method['qy'],
            crystal_to_microscope=np.asarray(method['metadata']['frame']),thickness_nm=settings.thickness)
        for state in ('plus','minus'):
            for detector in ('A','B'):
                key=f'I_{detector}_{state}'
                expected=np.zeros(len(energy))
                expected[mask]=np.sum(raw['total'][state]*method['weights'][detector],axis=(1,2))*(method['qx'][0,1]-method['qx'][0,0])**2
                np.testing.assert_allclose(entry['spectra'][key],expected,rtol=3e-13,atol=1e-18)
                sums[key]+=group.multiplicity*expected
    for key in RAW_KEYS:
        np.testing.assert_allclose(method['weighted_sum']['spectra'][key],sums[key],rtol=3e-13,atol=1e-18)
        np.testing.assert_allclose(method['spectra'][key],sums[key]/3,rtol=3e-13,atol=1e-18)


@pytest.mark.parametrize('fe_edge,offset',[('L2,3',0.),('K',6400.)])
def test_disjoint_elements_and_edges_both_solvers(tmp_path,monkeypatch,fe_edge,offset):
    structure,settings,sites=system(tmp_path,fe_edge=fe_edge)
    calls=[]
    original=propagation.propagate
    def counted(*args,**kwargs):
        calls.append(args[2].propagation)
        return original(*args,**kwargs)
    monkeypatch.setattr(propagation,'propagate',counted)
    result=calculate_multisite(structure,settings,sites,configuration(propagation='both'),energy_windows=disjoint_windows(offset))
    assert calls==['bloch','fft-multislice']
    expected_energy=np.sort(np.r_[np.asarray(FE_GRID)+offset,NI_GRID])
    np.testing.assert_array_equal(result['spectra']['energy_ev'],expected_energy)
    for method in result['methods'].values():
        independently_accumulated(method,structure,settings,sites)
        coverage=method['metadata']['multisite']
        assert coverage['spectrum_kind']=='modeled_partial_core_edge_spectrum'
        assert coverage['selected_atom_count']==3
        assert coverage['channels']['A']['edge']==fe_edge
        assert coverage['channels']['B']['edge']=='L2,3'
        assert coverage['channels']['A']['amplitude_multiplier']==1.
        assert coverage['channels']['A']['units']=='angstrom^2/eV'
        assert set(method['maps'])==({'A:K','B:L3','B:L2'} if fe_edge=='K' else {'A:L3','A:L2','B:L3','B:L2'})
    assert result['comparison']['spectra']['I_A_plus']['l2_relative']<.015


def test_window_selection_keeps_denominator_and_provider_amplitude(tmp_path):
    structure,settings,sites=system(tmp_path)
    cfg=configuration(angular_maps=False)
    full=calculate_multisite(structure,settings,sites,cfg,energy_windows=disjoint_windows())
    fe_only=calculate_multisite(structure,settings,sites,cfg,energy_windows={'A':disjoint_windows()['A']})
    for key in RAW_KEYS:
        np.testing.assert_allclose(fe_only['spectra'][key],full['spectra'][key][:3],rtol=3e-13)
        np.testing.assert_allclose(fe_only['spectra'][key],fe_only['groups']['A']['spectra'][key]/3,rtol=3e-13)
        np.testing.assert_array_equal(fe_only['groups']['B']['spectra'][key],0.)
    assert fe_only['metadata']['multisite']['selected_atom_count']==3
    assert fe_only['metadata']['multisite']['omitted_site_groups']==['B']
    assert set(fe_only['groups']['B']['metadata']['coverage']['status_at_energy'])=={'omitted_by_request'}
    stronger=source(tmp_path,'stronger','Ni',offset=130,scale=15.,down=True)
    scaled_sites=MultiSiteIonization(structure,[sites.groups[0],replace(sites.groups[1],mdff_reference=stronger)])
    scaled=calculate_multisite(structure,settings,scaled_sites,cfg,energy_windows=disjoint_windows())
    for key in RAW_KEYS:
        np.testing.assert_allclose(scaled['spectra'][key][:3],full['spectra'][key][:3],rtol=3e-13)
        np.testing.assert_allclose(scaled['spectra'][key][3:],5*full['spectra'][key][3:],rtol=3e-13)


@pytest.mark.parametrize('partial_overlap',[False,True])
def test_same_element_overlapping_grids_and_common_grid_compatibility(tmp_path,monkeypatch,partial_overlap):
    import emcd_sim.multisite_spectrum as spectrum

    structure,settings,sites=system(tmp_path,same_element=True)
    windows=dict(A=ModeledEdgeWindow((704.,720.) if partial_overlap else (704.,730.),(710.,716.)),
                 B=ModeledEdgeWindow((715.,735.) if partial_overlap else (709.,735.),(716.,723.)))
    calls=[]
    original=spectrum.run_multisite_with_coherence
    def counted(*args,**kwargs):
        calls.append((tuple(g.group_id for g in args[1].groups),args[3].copy()))
        return original(*args,**kwargs)
    monkeypatch.setattr(spectrum,'run_multisite_with_coherence',counted)
    cfg=configuration(angular_maps=False)
    result=calculate_multisite(structure,settings,sites,cfg,energy_windows=windows)
    independently_accumulated(result,structure,settings,sites)
    if not partial_overlap:
        assert len(calls)==1 and calls[0][0]==('A','B')
        np.testing.assert_array_equal(calls[0][1],[710.,716.,723.])
        common=calculate_multisite(structure,settings,sites,cfg,energy_ev=[710.,716.,723.])
        for key in RAW_KEYS+PARITY_KEYS:
            np.testing.assert_allclose(result['spectra'][key],common['spectra'][key],rtol=3e-13,atol=1e-18)
    else:
        assert result['metadata']['multisite']['active_channels_by_energy']==[['A'],['A','B'],['B']]
        assert result['metadata']['multisite']['selected_atom_count']==3


def test_explicit_exclusions_are_not_physical_zeros_and_reversal_is_global(tmp_path):
    structure,settings,sites=system(tmp_path)
    windows=dict(A=ModeledEdgeWindow((710.,720.)),B=ModeledEdgeWindow((840.,850.)))
    energy=[709.,710.,716.,720.,721.,800.,839.,840.,846.,850.,851.]
    cfg=configuration(angular_maps=False)
    plus=calculate_multisite(structure,settings,sites,cfg,energy_ev=energy,energy_windows=windows)
    minus=calculate_multisite(structure,settings,sites,cfg,energy_ev=energy,energy_windows=windows,reverse_magnetization=True)
    outside=[0,4,5,6,10]
    for key in RAW_KEYS:
        np.testing.assert_array_equal(plus['spectra'][key][outside],0.)
    metadata=plus['metadata']['multisite']
    assert metadata['channels']['A']['active_energy_mask']==[False,True,True,True,False,False,False,False,False,False,False]
    assert metadata['channels']['B']['status_at_energy'][5]=='outside_modeled_window'
    assert metadata['active_channels_by_energy'][5]==[]
    assert 'not a physical zero' in metadata['inactive_value_meaning']
    assert metadata['omitted_excitation_channels']
    for detector in ('A','B'):
        np.testing.assert_allclose(plus['spectra'][f'I_{detector}_plus'],minus['spectra'][f'I_{detector}_minus'],rtol=3e-13)
        np.testing.assert_allclose(plus['spectra']['N_'+detector],minus['spectra']['N_'+detector],rtol=3e-13)
        np.testing.assert_allclose(plus['spectra']['M_'+detector],-minus['spectra']['M_'+detector],rtol=3e-13,atol=1e-18)
    assert np.max(abs(plus['spectra']['M_A']))>0


def test_single_element_window_matches_existing_forward(tmp_path):
    from test_multisite_forward import system as ni_system
    from emcd_sim.gui.emcd_forward import calculate

    structure,settings,sites,refs=ni_system(tmp_path)
    cfg=configuration(angular_maps=False)
    old_cfg=replace(refs[0],**{key:getattr(cfg,key) for key in (
        'grid','depth','subpixels','halfwidth','centers','radius','angular_maps','worker_mode','parallel_workers')})
    old=calculate(structure,settings,old_cfg,energy_ev=FE_GRID)
    result=calculate_multisite(structure,settings,sites,cfg,energy_windows={'Ni':ModeledEdgeWindow((704.,730.),FE_GRID)})
    for key in RAW_KEYS+PARITY_KEYS:
        np.testing.assert_allclose(result['spectra'][key],old['spectra'][key],rtol=3e-13,atol=1e-18)


@pytest.mark.parametrize('failure',['lower_coverage','upper_coverage','unknown_group','no_samples','uncovered_common','unordered_common'])
def test_missing_required_data_rejected_before_geometry(tmp_path,monkeypatch,failure):
    structure,settings,sites=system(tmp_path)
    windows=disjoint_windows()
    energy=None
    if failure=='lower_coverage':windows['A']=ModeledEdgeWindow((703.,730.),FE_GRID)
    elif failure=='upper_coverage':windows['B']=ModeledEdgeWindow((834.,861.),NI_GRID)
    elif failure=='unknown_group':windows['unknown']=windows['A']
    elif failure=='no_samples':windows={'A':ModeledEdgeWindow((704.,730.))}
    elif failure=='uncovered_common':windows=None;energy=[710.,840.]
    elif failure=='unordered_common':energy=[840.,710.]
    def forbidden(*args,**kwargs):pytest.fail('Invalid spectral coverage reached geometry or propagation')
    monkeypatch.setattr(forward_pipeline,'geometry',forbidden)
    monkeypatch.setattr(forward_pipeline,'elastic_model',forbidden)
    monkeypatch.setattr(propagation,'numerical_info',forbidden)
    monkeypatch.setattr(propagation,'propagate',forbidden)
    with pytest.raises(ValueError):
        calculate_multisite(structure,settings,sites,configuration(),energy_ev=energy,energy_windows=windows)


@pytest.mark.parametrize('bounds,samples',[((0.,730.),FE_GRID),((730.,704.),FE_GRID),
    ((704.,np.inf),FE_GRID),((704.,730.),(710.,np.nan)),((704.,730.),(710.,709.)),
    ((704.,730.),(703.,710.))])
def test_invalid_modeled_window(bounds,samples):
    with pytest.raises(ValueError):ModeledEdgeWindow(bounds,samples)


def test_native_coverage_does_not_implicitly_declare_a_modeled_window(tmp_path):
    _,_,sites=system(tmp_path)
    with pytest.raises(ValueError,match='Missing MDFF coverage'):
        prepare_multisite_spectrum(sites,[710.,840.])
    plan=prepare_multisite_spectrum(sites,energy_windows=disjoint_windows())
    assert plan['metadata']['coverage_mode']=='explicit_modeled_edge_windows'
