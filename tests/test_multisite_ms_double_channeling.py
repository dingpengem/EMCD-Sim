"""Synthetic multi-site MS checks at fixed, explicitly matched approximations."""
from dataclasses import replace
from pathlib import Path
import json

import numpy as np
import pytest

from emcd_sim import multislice_double_channeling as ms
from emcd_sim.cancellation import Cancelled
from emcd_sim.double_channeling import intensities_from_response
from emcd_sim.geometry import characteristic_qz_angstrom_inv
from emcd_sim.gui import channeling
from emcd_sim.gui.emcd_forward import calculate
from emcd_sim.gui.forward_pipeline import calculate_multisite
from emcd_sim.multisite import MultiSiteIonization
from emcd_sim.multisite_spectrum import ModeledEdgeWindow
from test_multisite_forward import configuration, system as simple_system, source, RAW_KEYS, PARITY_KEYS
from test_multisite_single_channeling import generic_atoms, model_for, source as framed_source
from test_multisite_spectrum import system as spectral_system, disjoint_windows


def direct_site_intensity(elastic,grid,incoming,loss,queries,position,tensor):
    """Forward-scatter each depth event to exit 000; no adjoint response API."""
    fields,z,w,n,dz=incoming
    indices=grid.indices(elastic.beams.hkl)
    hkl=np.asarray(elastic.beams.hkl)
    phase=np.exp(2j*np.pi*((hkl[:,None,:]-hkl[None,:,:])@position))
    result=[]
    for query in queries:
        transfer=np.empty((len(indices),len(indices),3))
        transfer[...,:2]=query+grid.g[indices][None,:,:]-grid.g[indices][:,None,:]
        transfer[...,2]=-characteristic_qz_angstrom_inv(loss,elastic.microscope.acceleration_kv)
        angular=2*np.pi*transfer
        kernel=angular/np.sum(angular**2,axis=-1)[...,None]*phase[...,None]
        outgoing=grid.plan(loss,query)
        total=0.
        for iz in range(len(z)):
            amplitudes=ms.forward_event_amplitudes(fields[iz,indices],kernel,tensor,outgoing,
                [(outgoing,dz)]*(n*(len(z)-1-iz)),indices)
            total+=w[iz]*np.sum(abs(amplitudes)**2)
        result.append(total)
    return np.asarray(result)


@pytest.mark.parametrize('row_reduction',[False,True])
def test_group_responses_against_forward_site_events_and_shared_fields(monkeypatch,row_reduction):
    atoms=generic_atoms()
    model=model_for(atoms)
    grid=ms.ProjectedFFT.build(model.elastic,grid_points=12,potential_cutoff=.6,
        systematic_row=row_reduction,row_reduction=row_reduction)
    incoming=ms.incident_fields(grid,.12,depth_steps=5,slice_step_nm=.01)
    positions=atoms.get_scaled_positions()
    queries=np.array([[.13,.17],[-.22,.19]])
    tensor=np.array([[1.,.12j,.07],[-.12j,1.2,0],[.07,0,.8]])
    assert np.linalg.eigvalsh(tensor).min()>0
    original=ms.FFTSplitStep.advance
    outgoing_steps=[]
    def advance(self,coefficients,steps,dz,**kwargs):
        if dz<0:outgoing_steps.append(1)
        return original(self,coefficients,steps,dz,**kwargs)
    monkeypatch.setattr(ms.FFTSplitStep,'advance',advance)
    completed_planes=[]
    responses,diagnostics=ms.multislice_double_channeling_group_responses(model.elastic,710.,queries,.12,
        {'one':positions[:1],'two':positions[1:]},fft_grid=12,potential_cutoff=.6,
        systematic_row=row_reduction,row_reduction=row_reduction,depth_steps=5,slice_step_nm=.01,
        prepared_grid=grid,prepared_incoming=incoming,batch_pixels=1,progress=lambda:completed_planes.append(1))
    assert len(completed_planes)==len(queries)*5
    assert len(outgoing_steps)==len(queries)*(5-1)
    for name,selected in [('one',positions[:1]),('two',positions[1:])]:
        expected=np.mean([direct_site_intensity(model.elastic,grid,incoming,710.,queries,p,tensor) for p in selected],axis=0)
        actual=intensities_from_response(responses[name],tensor)
        np.testing.assert_allclose(actual,expected,rtol=3e-12,atol=1e-17)
        assert actual.min()>=-1e-12*max(abs(actual).max(),1e-30)
    legacy,legacy_diagnostics=ms.multislice_double_channeling_response(model.elastic,710.,queries,.12,
        fft_grid=12,potential_cutoff=.6,systematic_row=row_reduction,row_reduction=row_reduction,
        depth_steps=5,slice_step_nm=.01,prepared_grid=grid,prepared_incoming=incoming,batch_pixels=1)
    np.testing.assert_allclose(legacy,(responses['one']+2*responses['two'])/3,rtol=3e-13,atol=1e-17)
    for key in ('incoming_norm_error','outgoing_norm_error','incoming_max_excluded_population',
                'outgoing_max_excluded_population','actual_slice_step_nm'):
        assert diagnostics[key]==legacy_diagnostics[key]


@pytest.mark.parametrize('systematic_row',[False,True])
def test_single_group_ni_equivalence_and_diagnostics(tmp_path,systematic_row):
    structure,settings,sites,refs=simple_system(tmp_path)
    cfg=configuration(propagation='fft-multislice',channeling_model='double',
        systematic_row=systematic_row,angular_maps=False)
    fields=('grid','depth','subpixels','fft_grid','slice_step','halfwidth','centers','radius',
        'worker_mode','parallel_workers','channeling_model','propagation','systematic_row','angular_maps')
    old_cfg=replace(refs[0],**{key:getattr(cfg,key) for key in fields})
    old=calculate(structure,settings,old_cfg,energy_ev=[710.,723.])
    result=calculate_multisite(structure,settings,sites,cfg,energy_ev=[710.,723.])
    for key in RAW_KEYS+PARITY_KEYS:
        np.testing.assert_allclose(result['spectra'][key],old['spectra'][key],rtol=3e-13,atol=1e-17)
    assert result['metadata']['multisite']['depth_integration']=='trapezoidal'
    np.testing.assert_array_equal(result['metadata']['outgoing_energy_ev'],[199290.,199277.])
    assert result['metadata']['fft']['renormalized'] is False
    assert len(result['metadata']['angular_evaluation'])==2
    for diagnostic in result['metadata']['angular_evaluation']:
        assert diagnostic['incoming_norm_error']<1e-12
        assert diagnostic['outgoing_norm_error']<1e-12
        assert diagnostic['actual_slice_step_nm']<=cfg.slice_step
        assert diagnostic['row_reduction']==systematic_row


@pytest.mark.parametrize('down_scale',[1.,2.])
def test_antiparallel_afm_ferrimagnetic_and_global_reversal(tmp_path,down_scale):
    structure,settings,sites,_=simple_system(tmp_path,'Cr')
    if down_scale!=1:
        stronger=source(tmp_path,'stronger','Cr',down=True,scale=down_scale)
        sites=MultiSiteIonization(structure,[sites.groups[0],replace(sites.groups[1],mdff_reference=stronger)])
    cfg=configuration(propagation='fft-multislice',channeling_model='double')
    positive=calculate_multisite(structure,settings,sites,cfg,energy_ev=[710.,723.])
    reverse=calculate_multisite(structure,settings,sites,cfg,energy_ev=[710.,723.],reverse_magnetization=True)
    for detector in ('A','B'):
        for name in ('up','down'):
            np.testing.assert_allclose(positive['groups'][name]['spectra'][f'I_{detector}_plus'],
                reverse['groups'][name]['spectra'][f'I_{detector}_minus'],rtol=3e-13)
        np.testing.assert_allclose(positive['spectra']['N_'+detector],reverse['spectra']['N_'+detector],rtol=3e-13)
        np.testing.assert_allclose(positive['spectra']['M_'+detector],-reverse['spectra']['M_'+detector],rtol=3e-13,atol=1e-17)
    if down_scale==1:np.testing.assert_allclose(positive['spectra']['M_A'],0,atol=1e-17)
    else:assert np.max(abs(positive['spectra']['M_A']))>0
    for key in RAW_KEYS:
        expected=(positive['groups']['up']['spectra'][key]+positive['groups']['down']['spectra'][key])/2
        np.testing.assert_allclose(positive['spectra'][key],expected,rtol=3e-13)
        assert positive['spectra'][key].min()>=-1e-17


def test_noncollinear_frames_against_independent_forward_events(tmp_path,monkeypatch):
    structure,settings,sites=spectral_system(tmp_path)
    settings=replace(settings,target=(0,1,0))
    frame=np.array([[0,0,1],[0,1,0],[-1,0,0]])
    reference=framed_source(tmp_path,'local_x',axis=(1,0,0),frame=frame,real_odd=True)
    sites=MultiSiteIonization(structure,[sites.groups[0],replace(sites.groups[1],
        mdff_reference=reference,magnetization=(1,0,0))])
    context={}
    original_grid=channeling.fft_geometry
    original_incoming=channeling.incident_fields
    def grid(*args,**kwargs):
        context['grid']=original_grid(*args,**kwargs)
        return context['grid']
    def incoming(*args,**kwargs):
        context['incoming']=original_incoming(*args,**kwargs)
        return context['incoming']
    monkeypatch.setattr(channeling,'fft_geometry',grid)
    monkeypatch.setattr(channeling,'incident_fields',incoming)
    cfg=configuration(propagation='fft-multislice',channeling_model='double',angular_maps=False)
    result=calculate_multisite(structure,settings,sites,cfg,energy_ev=[710.,723.])
    qx,qy=result['qx'],result['qy']
    support=np.logical_or.reduce([w.ravel()>0 for w in result['weights'].values()])
    queries=np.column_stack((qx.ravel()[support],qy.ravel()[support]))
    rotation=np.asarray(result['metadata']['frame'])
    document=json.loads(Path(reference.source).read_text(encoding='utf-8'))
    ie=document['energy_ev'].index(710.)
    for state in ('plus','minus'):
        local=np.asarray(document['T_'+state]['real'])[ie]+1j*np.asarray(document['T_'+state]['imag'])[ie]
        tensor=rotation@frame@local@frame.T@rotation.T
        expected=np.mean([direct_site_intensity(result['model'].elastic,context['grid'],context['incoming'],
            710.,queries,p,tensor) for p in structure.atoms.get_scaled_positions()[1:]],axis=0)
        for detector in ('A','B'):
            integrated=np.sum(expected*result['weights'][detector].ravel()[support])*(qx[0,1]-qx[0,0])**2
            np.testing.assert_allclose(result['groups']['B']['spectra'][f'I_{detector}_{state}'][0],integrated,rtol=3e-12)
    assert np.max(abs(result['groups']['B']['spectra']['M_A']))>0


@pytest.mark.parametrize('overlap',[False,True])
def test_windows_weighting_and_one_complete_crystal_context(tmp_path,monkeypatch,overlap):
    structure,settings,sites=spectral_system(tmp_path,same_element=overlap)
    windows=(dict(A=ModeledEdgeWindow((704.,720.),(710.,716.)),B=ModeledEdgeWindow((715.,735.),(716.,723.)))
        if overlap else disjoint_windows())
    incoming_calls=[];outgoing_plans=[]
    original_incoming=ms.incident_fields
    original_plan=ms.ProjectedFFT.plan
    def incoming(*args,**kwargs):
        incoming_calls.append(1)
        return original_incoming(*args,**kwargs)
    def plan(self,energy_loss_ev=0.,q_xy=None,**kwargs):
        if energy_loss_ev>0:outgoing_plans.append((float(energy_loss_ev),len(q_xy)))
        return original_plan(self,energy_loss_ev,q_xy,**kwargs)
    monkeypatch.setattr(ms,'incident_fields',incoming)
    monkeypatch.setattr(channeling,'incident_fields',incoming)
    monkeypatch.setattr(ms.ProjectedFFT,'plan',plan)
    cfg=configuration(propagation='fft-multislice',channeling_model='double',angular_maps=False,worker_mode='automatic')
    result=calculate_multisite(structure,settings,sites,cfg,energy_windows=windows,
        energy_ev=None if overlap else [800.])
    assert incoming_calls==[1]
    support=np.logical_or.reduce([w.ravel()>0 for w in result['weights'].values()])
    active=result['metadata']['multisite']['active_channels_by_energy']
    expected_batches=sum(d['response_batches'] for d in result['metadata']['angular_evaluation'])
    assert len(outgoing_plans)==expected_batches
    assert all(batch<=32 for _,batch in outgoing_plans)
    assert 1<=result['metadata']['execution']['effective_workers']['fft-multislice']<=4
    assert result['metadata']['multisite']['selected_atom_count']==3
    for key in RAW_KEYS:
        a,b=[result['groups'][name]['spectra'][key] for name in ('A','B')]
        np.testing.assert_allclose(result['spectra'][key],(a+2*b)/3,rtol=3e-13)
        np.testing.assert_allclose(result['weighted_sum']['spectra'][key],a+2*b,rtol=3e-13)
        assert result['spectra'][key].min()>=-1e-17
    if overlap:assert active==[['A'],['A','B'],['B']]
    else:
        gap=int(np.flatnonzero(result['spectra']['energy_ev']==800.)[0])
        assert result['metadata']['angular_evaluation'][gap]['response_batches']==0
        for key in RAW_KEYS:assert result['spectra'][key][gap]==0
        only=calculate_multisite(structure,settings,sites,cfg,energy_windows={'A':windows['A']})
        for key in RAW_KEYS:np.testing.assert_allclose(only['spectra'][key],result['spectra'][key][:3],rtol=3e-13)
        assert only['metadata']['multisite']['selected_atom_count']==3


@pytest.mark.parametrize('channel',['single','double'])
@pytest.mark.parametrize('reverse',[False,True])
def test_selected_ms_queries_match_full_evaluation(tmp_path,monkeypatch,channel,reverse):
    """Actual query coordinates, not retained-map count or the FFT mesh size."""
    structure,settings,sites,_=simple_system(tmp_path,element='Cr')
    energy=np.array([710.,713.,716.,719.,723.])
    cfg=configuration(propagation='fft-multislice',channeling_model=channel,angular_maps=True,
        selected_edges=(('first',710.),('same-energy-alias',710.),('last',723.)))
    queries={}
    def record(losses,x,y):
        points=set(zip(np.asarray(x).ravel(),np.asarray(y).ravel()))
        for loss in np.atleast_1d(losses):queries.setdefault(float(loss),set()).update(points)
    if channel=='double':
        original=ms.multislice_double_channeling_group_responses
        def response(*args,**kwargs):
            record(args[1],args[2][:,0],args[2][:,1])
            return original(*args,**kwargs)
        monkeypatch.setattr(ms,'multislice_double_channeling_group_responses',response)
    else:
        from emcd_sim import multisite_single_channeling as single
        original=single._group_intensity_pair
        def response(*args,**kwargs):
            record(args[3],args[5],args[6])
            return original(*args,**kwargs)
        monkeypatch.setattr(single,'_group_intensity_pair',response)
    selected=calculate_multisite(structure,settings,sites,cfg,energy_ev=energy,reverse_magnetization=reverse)
    support=np.logical_or.reduce([w>0 for w in selected['weights'].values()])
    qx,qy=selected['qx'],selected['qy']
    full_points=set(zip(qx.ravel(),qy.ravel()))
    aperture_points=set(zip(qx[support],qy[support]))
    assert 0<len(aperture_points)<len(full_points)
    assert set(queries)==set(energy)
    assert all(points==(full_points if loss in (710.,723.) else aperture_points) for loss,points in queries.items())
    expected=2*qx.size+3*int(support.sum())
    assert sum(map(len,queries.values()))==expected
    assert sum(d['evaluated_pixels'] for d in selected['metadata']['angular_evaluation'])==expected
    assert selected['metadata']['detector_evaluation']=='full_grid_selected_energies'
    queries.clear()
    full=calculate_multisite(structure,settings,sites,replace(cfg,angular_evaluation='all'),
                            energy_ev=energy,reverse_magnetization=reverse)
    assert all(points==full_points for points in queries.values())
    assert sum(map(len,queries.values()))==len(energy)*qx.size
    assert full['metadata']['detector_evaluation']=='full_grid_all_energies'
    entries=[(selected,full),(selected['weighted_sum'],full['weighted_sum'])]
    entries.extend((selected['groups'][g.group_id],full['groups'][g.group_id]) for g in sites.groups)
    for actual,reference in entries:
        for key in RAW_KEYS+PARITY_KEYS:
            np.testing.assert_allclose(actual['spectra'][key],reference['spectra'][key],rtol=3e-13,atol=1e-17)
        assert actual['maps'].keys()==reference['maps'].keys()
        for label in actual['maps']:
            for key in ('I_plus','I_minus','I_mag','I_nonmag'):
                np.testing.assert_allclose(actual['maps'][label][key],reference['maps'][label][key],rtol=3e-13,atol=1e-17)
    for detector in ('A','B'):
        np.testing.assert_array_equal(selected['weights'][detector],full['weights'][detector])
        np.testing.assert_array_equal(selected['weights'][detector]>0,full['weights'][detector]>0)
    for group in sites.groups:
        np.testing.assert_array_equal(selected['metadata']['multisite']['channels'][group.group_id]['active_energy_mask'],
                                      full['metadata']['multisite']['channels'][group.group_id]['active_energy_mask'])
    for key in RAW_KEYS:
        expected=sum(g.multiplicity*selected['groups'][g.group_id]['spectra'][key] for g in sites.groups)/2
        np.testing.assert_allclose(selected['spectra'][key],expected,rtol=3e-13,atol=1e-17)
    spectra=selected['spectra']
    np.testing.assert_allclose(spectra['D_mag'],spectra['M_A']-spectra['M_B'],rtol=3e-13,atol=1e-17)


def test_group_split_merge_invariance(tmp_path):
    structure,settings,sites,_=simple_system(tmp_path)
    whole=sites.groups[0]
    split=MultiSiteIonization(structure,[replace(whole,group_id='one',indices=(0,),multiplicity=1),
        replace(whole,group_id='three',indices=(1,2,3),multiplicity=3)])
    cfg=configuration(propagation='fft-multislice',channeling_model='double',angular_maps=False)
    merged=calculate_multisite(structure,settings,sites,cfg,energy_ev=[710.,723.])
    separate=calculate_multisite(structure,settings,split,cfg,energy_ev=[710.,723.])
    for key in RAW_KEYS+PARITY_KEYS:
        np.testing.assert_allclose(merged['spectra'][key],separate['spectra'][key],rtol=3e-13,atol=1e-17)


@pytest.mark.parametrize('failure',['quadrature','context'])
def test_prepared_context_validation_preserved(failure):
    model=model_for(generic_atoms())
    grid=ms.ProjectedFFT.build(model.elastic,grid_points=12,potential_cutoff=.6)
    incoming=ms.incident_fields(grid,.12,depth_steps=5,slice_step_nm=.01)
    if failure=='quadrature':incoming=(incoming[0],incoming[1],incoming[2]*2,incoming[3],incoming[4])
    else:grid=replace(grid,carrier=grid.carrier+np.array([.1,0]))
    with pytest.raises(ValueError):
        ms.multislice_double_channeling_group_responses(model.elastic,710.,[[.13,.17]],.12,
            {'one':model.elastic.crystal.fractional_positions[:1]},prepared_grid=grid,prepared_incoming=incoming,
            fft_grid=12,potential_cutoff=.6,depth_steps=5,slice_step_nm=.01)


def test_cancellation_during_shared_outgoing_propagation(tmp_path,monkeypatch):
    structure,settings,sites,_=simple_system(tmp_path,'Cr')
    stop=False
    original=ms.FFTSplitStep.advance
    outgoing=[]
    def advance(self,coefficients,steps,dz,**kwargs):
        nonlocal stop
        if dz<0:
            outgoing.append(1)
            stop=True
        return original(self,coefficients,steps,dz,**kwargs)
    monkeypatch.setattr(ms.FFTSplitStep,'advance',advance)
    with pytest.raises(Cancelled):
        calculate_multisite(structure,settings,sites,
            configuration(propagation='fft-multislice',channeling_model='double',angular_maps=False),
            energy_ev=[710.,723.],cancelled=lambda:stop)
    assert outgoing==[1]
