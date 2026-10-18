"""Energy streaming, prepared incoming fields and unchanged per-energy physics."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from dataclasses import replace
from unittest.mock import patch
import numpy as np
import pytest
from emcd_sim.gui import emcd_forward as f
from emcd_sim.gui.geometry import Structure,Settings,elastic_model
from emcd_sim.double_channeling import prepare_incoming_bloch,double_channeling_response,outgoing_elastic


@pytest.fixture
def small():
    return Structure.nickel(),Settings(thickness=8,beam_cutoff=.9,potential_cutoff=1.8),f.ForwardSettings(
        axis_declared=True,channeling_model='double',energy_scope='full',energy_points=9,grid=9,depth=9,
        fft_grid=24,angular_maps=False,correction=False,l3=831.4778,l2=848.698)


def test_prepared_bloch_is_equivalent_and_bound_to_geometry(small):
    a,s,c=small;e=elastic_model(a,s);q=np.array([[.2,.3],[.2,-.3]])
    prepared=prepare_incoming_bloch(e,s.thickness,c.depth)
    assert not prepared.fields.flags.writeable
    for method in ('analytic','numerical'):
        for loss in (831.4778,848.698):
            plain=double_channeling_response(e,loss,q,s.thickness,method=method,depth_steps=c.depth)
            cached=double_channeling_response(e,loss,q,s.thickness,method=method,depth_steps=c.depth,prepared_incoming=prepared)
            np.testing.assert_allclose(cached,plain,rtol=2e-13,atol=1e-15)
    with pytest.raises(ValueError,match='do not match'):
        double_channeling_response(e,831.4778,q,12,prepared_incoming=prepared,depth_steps=c.depth)
    with pytest.raises(ValueError,match='do not match'):
        double_channeling_response(replace(e),831.4778,q,8,prepared_incoming=prepared,depth_steps=c.depth)


@pytest.mark.parametrize('solver',['bloch','fft-multislice','both'])
def test_longer_energy_grid_preserves_actual_locked_four_state_results(small,solver):
    a,s,c=small;c=replace(c,propagation=solver)
    fixed=np.array([c.l3,c.l2]);long=np.sort(np.r_[826.,c.l3,833.,c.l2,850.])
    p=f.calculate(a,s,c,energy_ev=fixed);r=f.calculate(a,s,c,energy_ev=long)
    for key,m in p['methods'].items():
        sp=r['methods'][key]['spectra'];ix=np.searchsorted(long,fixed)
        for name in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus','D_mag','D_nonmag','prb_relative_dichroism_percent'):
            np.testing.assert_allclose(sp[name][ix],m['spectra'][name],rtol=3e-13,atol=1e-14)
        assert min(sp[k].min() for k in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus'))>=0
        np.testing.assert_allclose(sp['D_raw'],sp['D_mag']+sp['D_nonmag'],atol=1e-14)
        np.testing.assert_allclose(sp['magnetic_only_percent'],100*sp['D_mag']/sp['Sigma_ref'])
        np.testing.assert_allclose(sp['nonmagnetic_imbalance_percent'],100*sp['D_nonmag']/sp['Sigma_ref'])


def test_energy_checkpoint_reuses_only_completed_points(small):
    a,s,c=small;cache={};writes=[]
    def checkpoint(method,e,data):
        if data is None:return cache.get((method,e))
        cache[method,e]=data;writes.append(e)
    first=f.calculate(a,s,c,energy_ev=np.array([c.l3,c.l2]),energy_checkpoint=checkpoint)
    with patch('emcd_sim.gui.channeling.double_channeling_response',side_effect=AssertionError('Completed point restarted')):
        again=f.calculate(a,s,c,energy_ev=np.array([c.l3,c.l2]),energy_checkpoint=checkpoint)
    assert len(writes)==2
    for k in first['spectra']:np.testing.assert_array_equal(first['spectra'][k],again['spectra'][k])


def test_invalid_energy_grid_and_no_extrapolation(small):
    c=small[2];native=f.energy_grid(c)
    for energy in ([native[0]-1,c.l3,c.l2],[c.l3,c.l2,native[-1]+1],[c.l2,c.l3],[c.l3,np.nan,c.l2]):
        with pytest.raises(ValueError):f.energy_grid(c,energy)
    with pytest.raises(ValueError,match='include'):f.energy_grid(c,[826,833,850])


def test_outgoing_energy_and_frozen_branch_convention(small):
    a,s,c=small;e=elastic_model(a,s)
    losses=[826.,831.4778,848.698,850.]
    for loss in losses:
        out=outgoing_elastic(e,(.2,.3),loss)
        assert out.microscope.acceleration_kv==pytest.approx(200-loss/1000)
        np.testing.assert_allclose(out.microscope.incident_k_xy,e.microscope.incident_k_xy+[.2,.3])
    r=f.calculate(a,s,c)
    np.testing.assert_allclose(r['metadata']['outgoing_energy_ev'],200000-r['spectra']['energy_ev'])
    assert 'frozen across branches' in r['metadata']['longitudinal_transfer']


def test_reversal_and_single_unchanged(small):
    a,s,c=small
    p=f.calculate(a,s,c);m=f.calculate(a,s,replace(c,eta=-1))
    np.testing.assert_allclose(p['spectra']['D_mag'],-m['spectra']['D_mag'],atol=1e-14)
    np.testing.assert_allclose(p['spectra']['D_nonmag'],m['spectra']['D_nonmag'],atol=1e-14)
    with patch('emcd_sim.gui.channeling.prepare_incoming_bloch',side_effect=AssertionError('Single uses legacy propagation')):
        r=f.calculate(a,s,replace(c,channeling_model='single'))
    assert r['config'].channeling_model=='single'


def test_cancelled_spectrum_resumes_without_repeating_completed_energy(small):
    from emcd_sim.gui import channeling,memory_budget
    a,s,c=small;energy=np.array([c.l3,c.l2]);cache={};stop=[False]
    def checkpoint(method,e,data):
        if data is None:return cache.get(e)
        cache[e]=data;stop[0]=True
    with pytest.raises(f.Cancelled):
        f.calculate(a,s,c,energy_ev=energy,energy_checkpoint=checkpoint,cancelled=lambda:stop[0])
    assert set(cache)=={c.l3}
    assert memory_budget.assess_memory(0)['concurrent_calculations']==0
    stop[0]=False;original=channeling.double_channeling_response
    def missing_only(elastic,e,*args,**kwargs):
        assert e!=c.l3,'Completed loss energy must not be recalculated'
        return original(elastic,e,*args,**kwargs)
    with patch.object(channeling,'double_channeling_response',side_effect=missing_only):
        result=f.calculate(a,s,c,energy_ev=energy,energy_checkpoint=checkpoint)
    assert set(cache)==set(energy)
    np.testing.assert_array_equal([result['spectra'][k][0] for k in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus')],cache[c.l3]['raw'])
