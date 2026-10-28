"""Focused kernel cancellation and exact pre-fix numerical equivalence."""
import subprocess,types,sys,threading,time
from dataclasses import replace
from unittest.mock import patch
import numpy as np
import pytest
from emcd_sim.cancellation import Cancelled
from legacy_geometry import Ni017Geometry
from emcd_sim import double_channeling as bw, multislice_double_channeling as ms
from emcd_sim.gui.geometry import Structure,Settings,elastic_model
from emcd_sim.gui.emcd_forward import ForwardSettings,calculate


def reference_module(path,name):
    source=subprocess.check_output(['git','show','7bebdce:'+path],text=True)
    module=types.ModuleType(name);module.__package__='emcd_sim';sys.modules[name]=module
    exec(compile(source,path,'exec'),module.__dict__)
    return module


@pytest.fixture
def elastic():
    return elastic_model(Structure.nickel(),Settings(thickness=2,beam_cutoff=.9,potential_cutoff=1.8))


@pytest.mark.parametrize('method',['analytic','numerical'])
def test_bw_unchanged_and_depth_cancel(elastic,method):
    old=reference_module('src/emcd_sim/double_channeling.py','emcd_sim._baseline_bw')
    q=np.array([[.15,.2],[.15,-.2]])
    args=dict(method=method,depth_steps=9)
    expected=old.double_channeling_response(elastic,831.4778,q,2,**args)
    actual=bw.double_channeling_response(elastic,831.4778,q,2,cancelled=lambda:False,**args)
    np.testing.assert_array_equal(actual,expected)
    event=threading.Event();original=bw.depth_response
    def depth(*a,**kw):
        event.set();return original(*a,**kw)
    with patch.object(bw,'depth_response',side_effect=depth),pytest.raises(Cancelled):
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
    grid=ms.ProjectedNiFFT.build(elastic,grid_points=24,potential_cutoff=1.8,projected_geometry=Ni017Geometry())
    calls=0
    def cancelled():
        nonlocal calls
        calls+=1
        return calls==12
    with pytest.raises(Cancelled):ms.incident_fields(grid,30,depth_steps=9,cancelled=cancelled)
    assert calls==12


def test_both_cancellation_prevents_incoming_ms():
    from emcd_sim.gui import channeling
    event=threading.Event();original=bw.depth_response
    def depth(*a,**kw):event.set();return original(*a,**kw)
    cfg=ForwardSettings(axis_declared=True,channeling_model='double',propagation='both',
        energy_scope='edges',angular_maps=False,grid=9,depth=9,fft_grid=24,subpixels=16,correction=False)
    with patch.object(bw,'depth_response',depth),patch.object(channeling,'fft_geometry') as fft:
        with pytest.raises(Cancelled):calculate(Structure.nickel(),Settings(thickness=2,beam_cutoff=.9,potential_cutoff=1.8),cfg,cancelled=event.is_set)
    fft.assert_not_called()


@pytest.mark.parametrize('solver',['bloch','fft-multislice','both'])
def test_full_spectrum_unchanged(solver):
    oldbw=reference_module('src/emcd_sim/double_channeling.py','emcd_sim._baseline_bw')
    oldms=reference_module('src/emcd_sim/multislice_double_channeling.py','emcd_sim._baseline_ms')
    oldbw.PreparedBlochIncoming=bw.PreparedBlochIncoming
    from emcd_sim.gui import channeling
    cfg=ForwardSettings(axis_declared=True,channeling_model='double',propagation=solver,
        energy_points=9,angular_maps=True,grid=9,depth=9,fft_grid=24,subpixels=16,correction=False)
    structure=Structure.nickel();settings=Settings(thickness=2,beam_cutoff=.9,potential_cutoff=1.8)
    def original_bw(*a,**kw):kw.pop('cancelled',None);return oldbw.double_channeling_response(*a,**kw)
    def original_ms(*a,**kw):kw.pop('cancelled',None);return oldms.multislice_double_channeling_response(*a,**kw)
    with patch.object(channeling,'double_channeling_response',original_bw),patch.object(channeling,'multislice_double_channeling_response',original_ms):
        before=calculate(structure,settings,cfg)
    after=calculate(structure,settings,cfg)
    for method in before['methods']:
        for key,value in before['methods'][method]['spectra'].items():
            np.testing.assert_array_equal(value,after['methods'][method]['spectra'][key])
        for edge,fields in before['methods'][method]['maps'].items():
            for key,value in fields.items():np.testing.assert_array_equal(value,after['methods'][method]['maps'][edge][key])
