"""Scheduling equivalence against the exact pre-optimization GUI adapters."""
import json,subprocess,sys,types
from dataclasses import replace,asdict
from unittest.mock import patch
import numpy as np
import pytest
from emcd_sim.gui import emcd_forward as f,channeling
from emcd_sim.gui.geometry import Structure,Settings

BASE='619a1969055ac6d717c092dcf663c3d58062b7e0'


def reference():
    for name,filename in (('_sampling_baseline_channeling','channeling.py'),('_sampling_baseline_forward','emcd_forward.py')):
        source=subprocess.check_output(['git','show',BASE+':src/emcd_sim/gui/'+filename]).decode('utf-8-sig')
        # Only relocate dependencies in the archived adapter; its numerical
        # statements remain the exact pre-optimization reference.
        source=source.replace('from ..ni_017_geometry import','from legacy_geometry import')
        source=source.replace('..multislice_emcd_reference import','..multislice_reference import')
        source=source.replace('..postedge_emcd_maps import paired_geometry, paired_maps','..emcd_angular_plots import paired_geometry, paired_maps')
        if filename=='emcd_forward.py':source=source.replace('from .channeling import contract','from ._sampling_baseline_channeling import contract')
        module=types.ModuleType('emcd_sim.gui.'+name);module.__package__='emcd_sim.gui';sys.modules[module.__name__]=module
        exec(compile(source,filename,'exec'),module.__dict__)
    return module


@pytest.fixture
def small():
    s=Settings(thickness=2,beam_cutoff=.9,potential_cutoff=1.8)
    c=f.ForwardSettings(axis_declared=True,grid=9,depth=5,fft_grid=24,subpixels=16,
        correction=False,energy_points=9,l3=831.4778,l2=848.698)
    energy=np.array([826.,c.l3,840.,c.l2,850.])
    return Structure.nickel(),s,c,energy


def equivalent(old,new):
    assert replace(new['config'],fft_generators=None)==replace(old['config'],fft_generators=None) and old['settings']==new['settings']
    for method,a in old['methods'].items():
        b=new['methods'][method]
        for name,value in a['spectra'].items():np.testing.assert_allclose(b['spectra'][name],value,rtol=3e-12,atol=2e-14,equal_nan=True,err_msg=method+' '+name)
        assert set(a['maps'])==set(b['maps'])
        for edge,fields in a['maps'].items():
            for name,value in fields.items():np.testing.assert_allclose(b['maps'][edge][name],value,rtol=3e-12,atol=2e-14,equal_nan=True,err_msg=method+' '+edge+' '+name)
        for name,value in a['weights'].items():np.testing.assert_array_equal(b['weights'][name],value)
        for name in ('qx','qy','depth_nm'):np.testing.assert_array_equal(a[name],b[name])
        for name in ('amplitudes','coherence'):np.testing.assert_allclose(a[name],b[name],rtol=0,atol=2e-13)
        np.testing.assert_allclose(b['spectra']['D_raw'],b['spectra']['D_mag']+b['spectra']['D_nonmag'],rtol=1e-12,atol=1e-14)


@pytest.mark.parametrize('method',['bloch','fft-multislice','both'])
@pytest.mark.parametrize('channel',['single','double'])
def test_actual_kernels_match_original_full_grid(small,method,channel):
    a,s,c,e=small;c=replace(c,propagation=method,channeling_model=channel)
    before=reference().calculate(a,s,c,energy_ev=e)
    after=f.calculate(a,s,c,energy_ev=e)
    equivalent(before,after)
    for result in after['methods'].values():
        diag=result['metadata']['angular_evaluation'];count=int(np.count_nonzero((result['weights']['A']>0)|(result['weights']['B']>0)))
        assert [d['evaluated_pixels'] for d in diag]==[count,81,count,81,count]
        assert sum(d['full_field'] for d in diag)==2 and len(diag)==len(e)
        assert result['metadata']['angular_evaluation_policy']==channeling.EVALUATION_POLICY


@pytest.mark.parametrize('channel',['single','double'])
@pytest.mark.parametrize('maps',[False,True])
def test_selected_edges_and_maps_switch(small,channel,maps):
    a,s,c,_=small;c=replace(c,channeling_model=channel,angular_maps=maps,energy_scope='edges')
    old=reference().calculate(a,s,c);new=f.calculate(a,s,c);equivalent(old,new)
    assert set(new['maps'])==({'L3','L2'} if maps else set())
    assert all(d['full_field']==maps for d in new['metadata']['angular_evaluation'])


@pytest.mark.parametrize('tilt_y',[0.,.3])
def test_asymmetric_apertures_do_not_control_field_symmetry(small,tilt_y):
    a,s,c,e=small;s=replace(s,tilt=(s.tilt[0],tilt_y))
    c=replace(c,channeling_model='double',propagation='both',centers=((.25,.25),(-.25,-.5)))
    equivalent(reference().calculate(a,s,c,energy_ev=e),f.calculate(a,s,c,energy_ev=e))
    result=f.calculate(a,s,c,energy_ev=e)
    for m in result['methods'].values():
        assert not any(d['mirror_reuse'] for d in m['metadata']['angular_evaluation'])
        assert all(d['query_pixels']==d['evaluated_pixels'] for d in m['metadata']['angular_evaluation']) if tilt_y else True
        assert m['maps']['L3']['I_plus'].shape==(9,9)


def test_single_atomic_reversal_uses_both_original_tensors(small):
    a,s,c,_=small;c=replace(c,model='atomic',l3=c.atomic.l3_ev,l2=c.atomic.l2_ev,propagation='both')
    e=np.array([c.l3-2,c.l3,(c.l3+c.l2)/2,c.l2,c.l2+2])
    equivalent(reference().calculate(a,s,c,energy_ev=e),f.calculate(a,s,c,energy_ev=e))


@pytest.mark.parametrize('channel',['single','double'])
def test_no_duplicate_response_and_exact_detector_union(small,channel):
    a,s,c,e=small;c=replace(c,channeling_model=channel)
    original=channeling._tensor_angular_maps if channel=='single' else channeling.double_channeling_response
    calls={float(v):[] for v in e}
    def capture(*args,**kwargs):
        if channel=='single':energy=float(args[2]);points=np.column_stack((args[5],args[6]))
        else:energy=float(args[1]);points=args[2]
        calls[energy].append(points.copy());return original(*args,**kwargs)
    name='_tensor_angular_maps' if channel=='single' else 'double_channeling_response'
    with patch.object(channeling,name,side_effect=capture):r=f.calculate(a,s,c,energy_ev=e)
    for ie,energy in enumerate(e):
        actual=np.concatenate(calls[float(energy)])
        support=np.ones((9,9),bool) if ie in (1,3) else (r['weights']['A']>0)|(r['weights']['B']>0)
        points=np.column_stack((r['qx'][support],r['qy'][support]))
        if channel=='single':points=np.repeat(points,2,axis=0)
        assert sorted(map(tuple,actual))==sorted(map(tuple,points))


@pytest.mark.parametrize('channel',['single','double'])
def test_checkpoint_missing_maps_only_recomputes_edges(small,channel):
    a,s,c,e=small;c=replace(c,channeling_model=channel);cache={};writes=[]
    def checkpoint(method,energy,data):
        if data is None:return cache.get((method,energy))
        cache[method,energy]=data;writes.append(energy)
    first=f.calculate(a,s,c,energy_ev=e,energy_checkpoint=checkpoint)
    # Full old callbacks may return raw-only entries; preserve all non-edge work.
    for data in cache.values():data.pop('maps',None)
    writes.clear();again=f.calculate(a,s,c,energy_ev=e,energy_checkpoint=checkpoint)
    assert writes==[c.l3,c.l2];equivalent(first,again)
    with patch.object(channeling,'_tensor_angular_maps',side_effect=AssertionError('Repeated completed energy')),patch.object(channeling,'double_channeling_response',side_effect=AssertionError('Repeated completed energy')):
        resumed=f.calculate(a,s,c,energy_ev=e,energy_checkpoint=checkpoint)
    equivalent(first,resumed)
    assert all(d['checkpoint_reused'] and d['evaluated_pixels']==0 for d in resumed['metadata']['angular_evaluation'])


def test_reject_partial_checkpoint_maps(small):
    a,s,c,e=small
    def checkpoint(method,energy,data):
        if data is None:return dict(raw=np.ones(4),maps=np.zeros((2,3,3)))
    with pytest.raises(ValueError,match='checkpoint angular maps'):f.calculate(a,s,c,energy_ev=e,energy_checkpoint=checkpoint)


@pytest.mark.parametrize('channel',['single','double'])
def test_cancel_resume_keeps_completed_energies(small,channel):
    a,s,c,e=small;c=replace(c,channeling_model=channel,propagation='both');cache={};stop=[False]
    def checkpoint(method,energy,data):
        if data is None:return cache.get((method,energy))
        cache[method,energy]=data;stop[0]=len(cache)==2
    with pytest.raises(f.Cancelled):f.calculate(a,s,c,energy_ev=e,energy_checkpoint=checkpoint,cancelled=lambda:stop[0])
    assert len(cache)==2
    stop[0]=False
    resumed=f.calculate(a,s,c,energy_ev=e,energy_checkpoint=checkpoint)
    equivalent(f.calculate(a,s,c,energy_ev=e),resumed)


def test_saved_output_and_nan_masks_unchanged(small,tmp_path):
    from emcd_sim.gui.project_io import save_project,load_project
    a,s,c,e=small;c=replace(c,eta=0.,channeling_model='double')
    before=reference().calculate(a,s,c,energy_ev=e);after=f.calculate(a,s,c,energy_ev=e)
    equivalent(before,after);save_project(after,tmp_path/'project');loaded=load_project(tmp_path/'project')
    equivalent(after,loaded)
    for edge,m in before['maps'].items():
        for k,v in m.items():np.testing.assert_array_equal(np.isnan(v),np.isnan(after['maps'][edge][k]))
    assert loaded['metadata']['angular_evaluation']==json.loads(json.dumps(after['metadata']['angular_evaluation']))


@pytest.mark.parametrize('channel',['single','double'])
def test_full_spectrum_maps_off_uses_union_at_every_energy(small,channel):
    a,s,c,e=small;c=replace(c,channeling_model=channel,angular_maps=False,propagation='both')
    old=reference().calculate(a,s,c,energy_ev=e);new=f.calculate(a,s,c,energy_ev=e);equivalent(old,new)
    for m in new['methods'].values():
        count=int(np.count_nonzero((m['weights']['A']>0)|(m['weights']['B']>0)))
        assert not m['maps']
        assert all(not d['full_field'] and d['evaluated_pixels']==count for d in m['metadata']['angular_evaluation'])


def test_full_spectrum_postedge_diagnostics_preserved(small):
    a,s,c,_=small;c=replace(c,correction=True)
    e=np.array([c.l3,c.l2,878.,880.,882.])
    old=reference().calculate(a,s,c,energy_ev=e);new=f.calculate(a,s,c,energy_ev=e)
    equivalent(old,new);assert new['metadata']['alpha']==pytest.approx(old['metadata']['alpha'],rel=3e-13)


def test_zero_signal_preserves_nan_denominator_masks(small):
    from emcd_sim.mdff_tensor import DipoleTensor
    a,s,c,e=small;old=reference()
    def zero(cfg,energy,R):
        tensor=DipoleTensor(energy,np.zeros((len(energy),3,3),complex),'synthetic zero-signal test')
        return [tensor,tensor]
    with patch.object(old,'tensors',zero),patch.object(f,'tensors',zero):
        before=old.calculate(a,s,c,energy_ev=e);after=f.calculate(a,s,c,energy_ev=e)
    equivalent(before,after)
    assert np.isnan(after['spectra']['prb_relative_dichroism_percent']).all()
    assert any(np.isnan(v).any() for v in after['maps']['L3'].values())


@pytest.mark.parametrize('channel',['single','double'])
def test_cancelled_partial_energy_never_writes_checkpoint(small,channel):
    a,s,c,e=small;c=replace(c,channeling_model=channel);stop=[False];writes=[]
    name='_tensor_angular_maps' if channel=='single' else 'double_channeling_response'
    original=getattr(channeling,name)
    def interrupt(*args,**kwargs):
        stop[0]=True;return original(*args,**kwargs)
    def checkpoint(method,energy,data):
        if data is not None:writes.append(energy)
    with patch.object(channeling,name,side_effect=interrupt),pytest.raises(f.Cancelled):
        f.calculate(a,s,c,energy_ev=e,energy_checkpoint=checkpoint,cancelled=lambda:stop[0])
    assert not writes
