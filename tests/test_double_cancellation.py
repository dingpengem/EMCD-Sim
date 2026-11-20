"""Kernel cancellation, exact callback neutrality and historical equivalence."""
from emcd_sim.study_presets import nickel_geometry_settings
import subprocess,types,sys,threading,time
from dataclasses import replace
from unittest.mock import patch
import numpy as np
import pytest
from emcd_sim.cancellation import Cancelled
from legacy_geometry import Ni017Geometry
from emcd_sim import double_channeling as bw, multislice_double_channeling as ms
from emcd_sim.structure_geometry import Structure, Settings, elastic_model
from emcd_sim.forward_settings import NiForwardSettings
from emcd_sim.forward_pipeline import calculate
from numerical_roundoff import assert_bloch_observables, assert_roundoff, bloch_roundoff


def reference_module(path,name):
    source=subprocess.check_output(['git','show','7bebdce:'+path],text=True)
    module=types.ModuleType(name);module.__package__='emcd_sim';sys.modules[name]=module
    exec(compile(source,path,'exec'),module.__dict__)
    return module


@pytest.fixture
def elastic():
    return elastic_model(Structure.nickel(),nickel_geometry_settings(thickness=2,beam_cutoff=.9,potential_cutoff=1.8))


@pytest.mark.parametrize('method',['analytic','numerical'])
def test_bw_unchanged_and_depth_cancel(elastic,method):
    old=reference_module('src/emcd_sim/double_channeling.py','emcd_sim._baseline_bw')
    q=np.array([[.15,.2],[.15,-.2]])
    args=dict(method=method,depth_steps=9)
    expected=old.double_channeling_response(elastic,831.4778,q,2,**args)
    actual=bw.double_channeling_response(elastic,831.4778,q,2,cancelled=lambda:False,**args)
    np.testing.assert_array_equal(actual,
        bw.double_channeling_response(elastic,831.4778,q,2,**args))
    if method=='numerical':
        budget=bloch_roundoff(len(elastic.beams.hkl),args['depth_steps'])
        scale=np.max(abs(expected),axis=(-2,-1),keepdims=True)
        assert_roundoff(actual,expected,budget*scale,label='historical Bloch response')
    else:
        np.testing.assert_array_equal(actual,expected)
    hook='_numerical_site_responses' if method=='numerical' else 'depth_response'
    event=threading.Event();original=getattr(bw,hook)
    def depth(*a,**kw):
        event.set();return original(*a,**kw)
    with patch.object(bw,hook,side_effect=depth),pytest.raises(Cancelled):
        bw.double_channeling_response(elastic,831.4778,q,2,cancelled=event.is_set,**args)


def test_ms_unchanged_and_outgoing_cancel(elastic):
    old=reference_module('src/emcd_sim/multislice_double_channeling.py','emcd_sim._baseline_ms')
    q=np.array([[.15,.2],[.15,-.2]])
    args=dict(projected_geometry=Ni017Geometry(),fft_grid=24,potential_cutoff=1.8,depth_steps=9,slice_step_nm=.04)
    args['prepared_grid']=old.ProjectedNiFFT.build(elastic,grid_points=24,potential_cutoff=1.8,projected_geometry=Ni017Geometry())
    expected,_=old.multislice_double_channeling_response(elastic,831.4778,q,2,**args)
    g=args['prepared_grid']
    args['prepared_grid']=ms.ProjectedFFT(g.potential,g.hkl,g.g,g.acceleration_kv,g.carrier,g.reduction)
    actual,_=ms.multislice_double_channeling_response(elastic,831.4778,q,2,cancelled=lambda:False,**args)
    np.testing.assert_array_equal(actual,expected)
    event=threading.Event();original=ms.FFTSplitStep.advance
    def advance(self,c,steps,dz,**kw):
        if dz<0:event.set()
        return original(self,c,steps,dz,**kw)
    with patch.object(ms.FFTSplitStep,'advance',advance),pytest.raises(Cancelled):
        ms.multislice_double_channeling_response(elastic,831.4778,q,2,cancelled=event.is_set,**args)


def test_incoming_slice_cancel(elastic):
    grid=ms.ProjectedFFT.build(elastic,grid_points=24,potential_cutoff=1.8,projected_geometry=Ni017Geometry())
    calls=0
    def cancelled():
        nonlocal calls
        calls+=1
        return calls==12
    with pytest.raises(Cancelled):ms.incident_fields(grid,30,depth_steps=9,cancelled=cancelled)
    assert calls==12


def test_both_cancellation_prevents_incoming_ms():
    from emcd_sim import channeling as channeling
    event=threading.Event();original=channeling.calculate_detector_signals
    def signals(*a,**kw):
        value=original(*a,**kw);event.set();return value
    cfg=NiForwardSettings(axis_declared=True,channeling_model='double',propagation='both',
        energy_scope='edges',angular_maps=False,grid=9,depth=9,fft_grid=24,subpixels=16,correction=False)
    with patch.object(channeling,'calculate_detector_signals',signals),patch.object(channeling,'fft_geometry') as fft:
        with pytest.raises(Cancelled):calculate(Structure.nickel(),nickel_geometry_settings(thickness=2,beam_cutoff=.9,potential_cutoff=1.8),cfg,cancelled=event.is_set)
    fft.assert_not_called()


@pytest.mark.parametrize('solver',['bloch','fft-multislice','both'])
def test_full_spectrum_unchanged(solver):
    oldbw=reference_module('src/emcd_sim/double_channeling.py','emcd_sim._baseline_bw')
    oldms=reference_module('src/emcd_sim/multislice_double_channeling.py','emcd_sim._baseline_ms')
    oldbw.PreparedBlochIncoming=bw.PreparedBlochIncoming
    from emcd_sim import channeling as channeling
    cfg=NiForwardSettings(axis_declared=True,channeling_model='double',propagation=solver,
        energy_points=9,angular_maps=True,grid=9,depth=9,fft_grid=24,subpixels=16,correction=False)
    structure=Structure.nickel();settings=nickel_geometry_settings(thickness=2,beam_cutoff=.9,potential_cutoff=1.8)
    def historical_arguments(elastic,kw):
        from emcd_sim.historical_ni import HistoricalNiSites
        kw.pop('cancelled',None)
        kw.pop('prepared_outgoing',None)  # The archived reference prepares its own outgoing basis.
        sites=kw.pop('ionization_sites')
        assert isinstance(sites,HistoricalNiSites)
        # The archived API predates explicit sites. Certify the adapter supplies
        # exactly its original positions before removing only this new argument.
        np.testing.assert_array_equal(sites.positions_for(elastic.crystal),elastic.crystal.fractional_positions)
        return kw
    def original_bw(*a,**kw):return oldbw.double_channeling_response(*a,**historical_arguments(a[0],kw))
    def original_ms(*a,**kw):return oldms.multislice_double_channeling_response(*a,**historical_arguments(a[0],kw))
    with patch.object(channeling,'double_channeling_response',original_bw),patch.object(channeling,'multislice_double_channeling_response',original_ms):
        before=calculate(structure,settings,cfg)
    after=calculate(structure,settings,cfg)
    for method in before['methods']:
        if method=='bloch':
            assert_bloch_observables(after['methods'][method],before['methods'][method],cfg)
            continue
        for key,value in before['methods'][method]['spectra'].items():
            np.testing.assert_array_equal(value,after['methods'][method]['spectra'][key])
        for edge,fields in before['methods'][method]['maps'].items():
            for key,value in fields.items():np.testing.assert_array_equal(value,after['methods'][method]['maps'][edge][key])
