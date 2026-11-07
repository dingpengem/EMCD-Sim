"""Small synthetic multi-site BW Double Channeling checks, not physical spectra."""
from contextlib import contextmanager
from dataclasses import replace
import json

import numpy as np
import pytest

from emcd_sim import double_channeling as bw
from emcd_sim.cancellation import Cancelled
from emcd_sim.geometry import characteristic_qz_angstrom_inv
from emcd_sim.gui import channeling
from emcd_sim.gui.emcd_forward import calculate
from emcd_sim.gui.forward_pipeline import calculate_multisite
from emcd_sim.mdff_providers import load_site_group_provider
from emcd_sim.multisite import MultiSiteIonization
from emcd_sim.multisite_spectrum import ModeledEdgeWindow
from test_multisite_forward import configuration, system as simple_system, RAW_KEYS, PARITY_KEYS
from test_multisite_single_channeling import generic_atoms, model_for, source as framed_source
from test_multisite_spectrum import system as spectral_system, disjoint_windows


def direct_site_intensity(elastic,loss,queries,position,tensor,thickness,method,steps):
    """Explicit event amplitudes using full outgoing Hamiltonians, no response API."""
    if method=='analytic':
        nodes,weights=np.polynomial.legendre.leggauss(40)
        z=(nodes+1)*thickness/2
        weights=weights*thickness/2
    else:
        z=np.linspace(0,thickness,steps)
        weights=np.full(steps,thickness/(steps-1));weights[[0,-1]]*=.5
    def ket(hamiltonian,distance):
        e,v=np.linalg.eigh(hamiltonian)
        return (np.exp(1j*distance[:,None]*e)*v[0].conj())@v.T
    incoming=ket(elastic.hamiltonian_nm_inv(),z)
    gi=elastic.reciprocal_vectors_xy
    hkl=np.asarray(elastic.beams.hkl)
    phase=np.exp(2j*np.pi*((hkl[:,None,:]-hkl[None,:,:])@position))
    result=[]
    for query in queries:
        outgoing=bw.outgoing_elastic(elastic,query,loss)
        bra=ket(outgoing.hamiltonian_nm_inv(),z-thickness).conj()
        q=np.empty((len(hkl),len(hkl),3))
        q[...,:2]=query+outgoing.reciprocal_vectors_xy[None,:,:]-gi[:,None,:]
        q[...,2]=-characteristic_qz_angstrom_inv(loss,elastic.microscope.acceleration_kv)
        angular=2*np.pi*q
        kernel=angular/np.sum(angular**2,axis=-1)[...,None]*phase[...,None]
        amplitudes=np.einsum('zg,zh,gha->za',incoming,bra,kernel)
        intensity=np.einsum('za,ba,zb->z',amplitudes,tensor,amplitudes.conj()).real
        result.append(np.sum(weights*intensity))
    return np.asarray(result)


@pytest.mark.parametrize('method',['analytic','numerical'])
def test_group_responses_match_explicit_site_events_and_share_outgoing(monkeypatch,method):
    atoms=generic_atoms()
    model=model_for(atoms)
    queries=np.array([[.13,.17],[-.22,.19]])
    positions=atoms.get_scaled_positions()
    tensor=np.array([[1.,.12j,.07],[-.12j,1.2,0],[.07,0,.8]])
    assert np.linalg.eigvalsh(tensor).min()>0
    original=bw.BlochStates.solve
    solves=[]
    def counted(cls,h,boundary_index=0):
        solves.append(len(h))
        return original(h,boundary_index)
    monkeypatch.setattr(bw.BlochStates,'solve',classmethod(counted))
    incoming=bw.prepare_incoming_bloch(model.elastic,.7,9)
    responses=bw.double_channeling_group_responses(model.elastic,710.,queries,.7,
        {'one':positions[:1],'two':positions[1:]},method=method,depth_steps=9,prepared_incoming=incoming)
    assert len(solves)==1+len(queries)
    for name,selected in [('one',positions[:1]),('two',positions[1:])]:
        expected=np.mean([direct_site_intensity(model.elastic,710.,queries,p,tensor,.7,method,9) for p in selected],axis=0)
        actual=bw.intensities_from_response(responses[name],tensor)
        np.testing.assert_allclose(actual,expected,rtol=3e-13,atol=1e-17)
        assert actual.min()>=-1e-12*max(abs(actual).max(),1e-30)
    merged=bw.double_channeling_group_responses(model.elastic,710.,queries,.7,{'all':positions},
        method=method,depth_steps=9,prepared_incoming=incoming)['all']
    np.testing.assert_allclose(merged,(responses['one']+2*responses['two'])/3,rtol=3e-13,atol=1e-17)


@pytest.mark.parametrize('systematic_row',[False,True])
def test_single_group_ni_matches_existing_bw_double_pipeline(tmp_path,systematic_row):
    structure,settings,sites,refs=simple_system(tmp_path)
    cfg=configuration(channeling_model='double',systematic_row=systematic_row,angular_maps=False)
    fields=('grid','depth','subpixels','halfwidth','centers','radius','worker_mode','parallel_workers',
            'channeling_model','systematic_row','angular_maps')
    old_cfg=replace(refs[0],**{key:getattr(cfg,key) for key in fields})
    energy=[710.,723.]
    old=calculate(structure,settings,old_cfg,energy_ev=energy)
    result=calculate_multisite(structure,settings,sites,cfg,energy_ev=energy)
    for key in RAW_KEYS+PARITY_KEYS:
        np.testing.assert_allclose(result['spectra'][key],old['spectra'][key],rtol=3e-13,atol=1e-17)
    np.testing.assert_array_equal(result['metadata']['outgoing_energy_ev'],[199290.,199277.])
    assert result['metadata']['multisite']['depth_integration']==('analytic' if systematic_row else 'numerical')


def test_afm_cr_and_global_reversal(tmp_path):
    structure,settings,sites,_=simple_system(tmp_path,'Cr')
    cfg=configuration(channeling_model='double',angular_maps=True)
    positive=calculate_multisite(structure,settings,sites,cfg,energy_ev=[710.,723.])
    reversed_result=calculate_multisite(structure,settings,sites,cfg,energy_ev=[710.,723.],reverse_magnetization=True)
    for detector in ('A','B'):
        np.testing.assert_allclose(positive['spectra']['M_'+detector],0,atol=1e-16)
        for group in ('up','down'):
            np.testing.assert_allclose(positive['groups'][group]['spectra'][f'I_{detector}_plus'],
                reversed_result['groups'][group]['spectra'][f'I_{detector}_minus'],rtol=3e-13)
    # Explicit group states carry a signal; cancellation is from antiparallel sublattices.
    assert np.max(abs(positive['groups']['up']['spectra']['M_A']))>0
    for key in RAW_KEYS:
        expected=(positive['groups']['up']['spectra'][key]+positive['groups']['down']['spectra'][key])/2
        np.testing.assert_allclose(positive['spectra'][key],expected,rtol=3e-13)
    for group in positive['groups'].values():
        for key in RAW_KEYS:assert group['spectra'][key].min()>=-1e-16


def test_noncollinear_local_frames_and_real_reversal_odd(tmp_path):
    structure,settings,sites=spectral_system(tmp_path)
    settings=replace(settings,target=(0,1,0))
    frame=np.array([[0,0,1],[0,1,0],[-1,0,0]])
    reference=framed_source(tmp_path,'local_x',axis=(1,0,0),frame=frame,real_odd=True)
    sites=MultiSiteIonization(structure,[sites.groups[0],replace(sites.groups[1],
        mdff_reference=reference,magnetization=(1,0,0))])
    cfg=configuration(channeling_model='double',angular_maps=False)
    result=calculate_multisite(structure,settings,sites,cfg,energy_ev=[710.,723.])
    reverse=calculate_multisite(structure,settings,sites,cfg,energy_ev=[710.,723.],reverse_magnetization=True)
    qx,qy=result['qx'],result['qy']
    queries=np.column_stack((qx.ravel(),qy.ravel()))
    rotation=np.asarray(result['metadata']['frame'])
    d=json.loads(open(reference.source,encoding='utf-8').read())
    ie=d['energy_ev'].index(710.)
    for state in ('plus','minus'):
        local=np.asarray(d['T_'+state]['real'])[ie]+1j*np.asarray(d['T_'+state]['imag'])[ie]
        tensor=rotation@frame@local@frame.T@rotation.T
        expected=np.mean([direct_site_intensity(result['model'].elastic,710.,queries,p,tensor,settings.thickness,'numerical',cfg.depth)
            for p in structure.atoms.get_scaled_positions()[1:]],axis=0).reshape(qx.shape)
        for detector in ('A','B'):
            integrated=np.sum(expected*result['weights'][detector])*(qx[0,1]-qx[0,0])**2
            np.testing.assert_allclose(result['groups']['B']['spectra'][f'I_{detector}_{state}'][0],integrated,rtol=3e-13)
    assert np.max(abs(result['groups']['B']['spectra']['M_A']))>0
    for detector in ('A','B'):
        np.testing.assert_allclose(result['spectra']['N_'+detector],reverse['spectra']['N_'+detector],rtol=3e-13)
        np.testing.assert_allclose(result['spectra']['M_'+detector],-reverse['spectra']['M_'+detector],rtol=3e-13,atol=1e-18)


@pytest.mark.parametrize('overlap',[False,True])
def test_windows_weighting_fixed_denominator_and_shared_solves(tmp_path,monkeypatch,overlap):
    structure,settings,sites=spectral_system(tmp_path,same_element=overlap)
    windows=(dict(A=ModeledEdgeWindow((704.,720.),(710.,716.)),B=ModeledEdgeWindow((715.,735.),(716.,723.)))
             if overlap else disjoint_windows())
    incoming_calls=[];solves=[];guard_calls=[]
    original_incoming=bw.prepare_incoming_bloch
    original_solve=bw.BlochStates.solve
    original_guard=channeling.bw_executor_guard
    def incoming(*args,**kwargs):
        incoming_calls.append(args[0].crystal.species)
        return original_incoming(*args,**kwargs)
    def solve(cls,h,boundary_index=0):
        solves.append(1)
        return original_solve(h,boundary_index)
    @contextmanager
    def guard(*args):
        guard_calls.append(1)
        with original_guard(*args):yield
    monkeypatch.setattr(bw,'prepare_incoming_bloch',incoming)
    monkeypatch.setattr(bw.BlochStates,'solve',classmethod(solve))
    monkeypatch.setattr(channeling,'bw_executor_guard',guard)
    cfg=configuration(channeling_model='double',angular_maps=False,worker_mode='automatic')
    result=calculate_multisite(structure,settings,sites,cfg,energy_windows=windows)
    assert len(incoming_calls)==1 and incoming_calls[0]==sites.species
    assert guard_calls==[1]
    support=np.logical_or.reduce([w.ravel()>0 for w in result['weights'].values()])
    energy=result['spectra']['energy_ev']
    assert len(solves)==1+int(support.sum())*len(energy)
    assert result['metadata']['execution']['effective_workers']=={'bloch':1}
    count=result['metadata']['multisite']['selected_atom_count']
    assert count==3
    for key in RAW_KEYS:
        a,b=[result['groups'][name]['spectra'][key] for name in ('A','B')]
        np.testing.assert_allclose(result['spectra'][key],(a+2*b)/3,rtol=3e-13)
        np.testing.assert_allclose(result['weighted_sum']['spectra'][key],a+2*b,rtol=3e-13)
        assert result['spectra'][key].min()>=-1e-16
    if overlap:
        assert result['metadata']['multisite']['active_channels_by_energy']==[['A'],['A','B'],['B']]
    else:
        only=calculate_multisite(structure,settings,sites,cfg,energy_windows={'A':windows['A']})
        for key in RAW_KEYS:
            np.testing.assert_allclose(only['spectra'][key],result['spectra'][key][:3],rtol=3e-13)
        assert only['metadata']['multisite']['selected_atom_count']==3


def test_equivalent_site_split_merge_pipeline(tmp_path):
    structure,settings,sites,_=simple_system(tmp_path)
    whole=sites.groups[0]
    split=MultiSiteIonization(structure,[replace(whole,group_id='one',indices=(0,),multiplicity=1),
        replace(whole,group_id='three',indices=(1,2,3),multiplicity=3)])
    cfg=configuration(channeling_model='double',angular_maps=False)
    merged=calculate_multisite(structure,settings,sites,cfg,energy_ev=[710.,723.])
    separate=calculate_multisite(structure,settings,split,cfg,energy_ev=[710.,723.])
    for key in RAW_KEYS+PARITY_KEYS:
        np.testing.assert_allclose(merged['spectra'][key],separate['spectra'][key],rtol=3e-13,atol=1e-17)


@pytest.mark.parametrize('failure',['ms','both','workers','coverage'])
def test_unsupported_or_uncovered_double_rejected_before_propagation(tmp_path,monkeypatch,failure):
    structure,settings,sites=spectral_system(tmp_path)
    cfg=configuration(channeling_model='double',angular_maps=False)
    windows=disjoint_windows()
    if failure in ('ms','both'):cfg=replace(cfg,propagation='fft-multislice' if failure=='ms' else 'both')
    elif failure=='workers':cfg=replace(cfg,parallel_workers=2)
    else:windows['A']=ModeledEdgeWindow((703.,730.),(710.,))
    def forbidden(*args,**kwargs):pytest.fail('Invalid multi-site double request started propagation')
    monkeypatch.setattr(bw,'prepare_incoming_bloch',forbidden)
    monkeypatch.setattr(channeling,'fft_geometry',forbidden)
    with pytest.raises(ValueError):calculate_multisite(structure,settings,sites,cfg,energy_windows=windows)


def test_cancellation_between_site_events(tmp_path,monkeypatch):
    structure,settings,sites,_=simple_system(tmp_path,'Cr')
    stopped=False
    original=bw.depth_response
    def depth(*args,**kwargs):
        nonlocal stopped
        value=original(*args,**kwargs)
        stopped=True
        return value
    monkeypatch.setattr(bw,'depth_response',depth)
    with pytest.raises(Cancelled):
        calculate_multisite(structure,settings,sites,configuration(channeling_model='double',angular_maps=False),
            energy_ev=[710.,723.],cancelled=lambda:stopped)
