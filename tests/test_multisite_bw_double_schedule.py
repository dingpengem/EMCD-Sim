"""Shared BW/MS DC query scheduling; the response solver is not executed."""
from types import SimpleNamespace
import weakref
import numpy as np
import pytest

from emcd_sim.gui import forward_pipeline as forward
from emcd_sim.multisite_spectrum import _empty_group_intensities,_spectrum_result


@pytest.mark.parametrize('maps,reverse',[(True,False),(False,True)])
@pytest.mark.parametrize('propagation',['bloch','fft-multislice'])
def test_selected_double_support_and_reduction(monkeypatch,maps,reverse,propagation):
    energy=np.unique(np.r_[np.linspace(831.271,848.698,35),840.])
    group=SimpleNamespace(group_id='site',element='Ni',indices=(0,1,2,3),multiplicity=4,
                          magnetization=(0,0,1),normalization='mean_per_selected_atom')
    sites=SimpleNamespace(groups=(group,));incoming=object();fft=object();fields=object();calls=[];previous=[]
    plan=dict(energy_ev=energy,sources={'site':{}},active={'site':np.ones(len(energy),bool)},
              metadata=dict(channels={'site':{}},coverage_mode='common'))
    model=SimpleNamespace(elastic=SimpleNamespace(microscope=SimpleNamespace(acceleration_kv=300.)))
    cfg=forward.MultiSiteForwardSettings(grid=9,depth=64,subpixels=64,angular_maps=maps,
        angular_evaluation='selected',selected_edges=(('low',energy[0]),('high',energy[-1])),
        worker_mode='manual',parallel_workers=1)
    qx,qy=np.meshgrid(np.linspace(-1,1,9),np.linspace(-1,1,9))
    weights=dict(A=np.where((qx>0)&(qy>0),.7,0.),B=np.where((qx>0)&(qy<0),.7,0.))
    support=(weights['A']+weights['B']).ravel()>0
    def raw_values(block,x,y):
        base=(3+.001*block[:,None])*(1+x[None,:]**2+y[None,:]**2)
        odd=.1*y[None,:]*(-1 if reverse else 1)
        return base+odd,base-odd
    def solver(actual_model,actual_sites,block,x,y,**kwargs):
        assert actual_model is model and actual_sites is sites
        assert kwargs['execution_workers']==1 and kwargs['depth_steps']==64
        if propagation=='bloch':
            assert kwargs['prepared_incoming'] is incoming and kwargs['method']=='numerical'
        else:
            assert kwargs['prepared_incoming'] is fields and kwargs['prepared_grid'] is fft
            assert kwargs['potential_cutoff']==.6 and kwargs['slice_step_nm']==cfg.slice_step
        assert kwargs['reverse_magnetization'] is reverse
        assert all(ref() is None for ref in previous), 'Previous response block retained'
        assert len(block['energy_ev'])<=16
        calls.append((block['energy_ev'].copy(),len(x)))
        groups,weighted=_empty_group_intensities(sites,block,x.shape)
        plus,minus=raw_values(block['energy_ev'],x,y)
        groups['site'].update(plus=plus,minus=minus);weighted[:]=4*np.stack([plus,minus])
        result=_spectrum_result(sites,block,groups,weighted,np.eye(3),9.,reverse)
        result['diagnostics']=[dict(energy_ev=float(e),evaluated_pixels=len(x),required_pixels=len(x)) for e in block['energy_ev']]
        previous[:]=[weakref.ref(result['total']['plus']),weakref.ref(groups['site']['plus'])]
        return result
    name='contract_multisite_bloch_double' if propagation=='bloch' else 'contract_multisite_ms_double'
    monkeypatch.setattr('emcd_sim.multisite_double_channeling.'+name,solver)
    result=forward._multisite_double_detector_data(model,sites,plan,cfg,qx,qy,weights,support,
        np.eye(3),9.,incoming,1,reverse,lambda s:None,lambda:False,
        propagation=propagation,prepared_fft=(fft,fields),potential_cutoff=.6)
    counts={float(e):pixels for block,pixels in calls for e in block}
    assert len(counts)==len(energy)==sum(len(block) for block,_ in calls)
    assert all(pixels==(qx.size if maps and e in energy[[0,-1]] else support.sum()) for e,pixels in counts.items())
    expected=forward._multisite_detector_data(dict(zip(('plus','minus'),raw_values(energy,qx.ravel(),qy.ravel()))),
        cfg,energy,qx,qy,weights,np.ones(qx.size,bool))
    for key,value in expected['spectra'].items():np.testing.assert_allclose(result['total']['spectra'][key],value,rtol=2e-13,atol=1e-14)
    for label,fields in expected['maps'].items():
        for key,value in fields.items():np.testing.assert_array_equal(result['total']['maps'][label][key],value)
    assert [d['energy_index'] for d in result['diagnostics']]==list(range(len(energy)))
    np.testing.assert_array_equal(result['metadata']['outgoing_energy_ev'],300000-energy)
    assert all(ref() is None for ref in previous)
