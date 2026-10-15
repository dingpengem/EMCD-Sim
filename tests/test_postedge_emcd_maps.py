"""Paired-map identities and one small matched real-source calculation."""
from dataclasses import replace
from pathlib import Path
import numpy as np
import pytest
from emcd_sim.benchmark import nickel_physical_benchmark
from emcd_sim.geometry import VirtualDetector
from emcd_sim.postedge_emcd_maps import (MapConfig, paired_geometry, paired_maps, integrate_paired,
    run_map_comparison, save_comparison, load_comparison, map_error)
from emcd_sim.xmcd_postedge_normalization import normalize_postedge
from emcd_sim.xmcd_effective_mdff import effective_tensor_from_xmcd


def geometry(condition='near-2bc',mode='fractional'):
    model=nickel_physical_benchmark(diffraction_condition=condition)
    q=np.linspace(-1.,1.,33);x,y=np.meshgrid(q,q)
    return model,x,y,paired_geometry(model,x,y,mode=mode)


@pytest.mark.parametrize('condition',['near-2bc','symmetric-3bc'])
def test_physical_pairing_weights_integrals_and_pointwise_parity(condition):
    model,x,y,g=geometry(condition)
    assert g['mapping']==({'A':'B'} if condition=='near-2bc' else {'RU':'RD','LD':'LU'})
    np.testing.assert_array_equal(g['weights_A'],g['weights_B'][::-1])
    n=2.+x+.2*y;m=.05*x*y
    p=n+m;minus=n-m;r=paired_maps(p,minus,.93,g);v=g['valid']
    np.testing.assert_allclose(r['D_raw'][v],(r['D_mag']+r['D_nonmag'])[v],atol=1e-15)
    np.testing.assert_allclose(r['D_corrected'][v],(r['D_mag_processed']+r['D_nonmag_residual'])[v],atol=1e-15)
    assert np.isnan(r['D_raw'][~v]).all()
    np.testing.assert_array_equal(r['I_mag'],(p-minus)/2)
    for key,field,w in [('I_A_plus',p,g['weights_A']),('I_B_plus_paired',p,g['weights_B'])]:
        assert integrate_paired(r[key],g)==pytest.approx(np.sum(field*w)*g['dq2'],abs=1e-15)
    assert integrate_paired(r['D_raw'],g)==pytest.approx(np.sum(p*(g['weights_A']-g['weights_B']))*g['dq2'],abs=1e-15)
    reverse=paired_maps(minus,p,.93,g)
    np.testing.assert_allclose(reverse['D_mag'][v],-r['D_mag'][v],atol=1e-15)
    np.testing.assert_allclose(reverse['D_mag_processed'][v],-r['D_mag_processed'][v],atol=1e-15)
    np.testing.assert_allclose(reverse['D_nonmag'][v],r['D_nonmag'][v],atol=1e-15)
    np.testing.assert_array_equal(paired_maps(n,n,1.,g)['I_mag'],0)


def test_reject_mismatched_geometry_and_grid():
    model,x,y,g=geometry()
    bad=replace(model,detectors={'A':model.detectors['A'],'B':VirtualDetector((.3,-.2),.08)})
    with pytest.raises(ValueError,match='reflected'):paired_geometry(bad,x,y)
    with pytest.raises(ValueError,match='symmetric'):paired_geometry(model,x,y+.01)
    with pytest.raises(ValueError,match='grouping'):paired_geometry(replace(model,detectors={'X':model.detectors['A'],'Y':model.detectors['B']},chiral_groups={'A':('X',),'B':('Y',)}),x,y)


def test_reflected_weight_mismatch_rejected(monkeypatch):
    model,x,y,_=geometry()
    original=VirtualDetector.integration_weights
    def inconsistent(det,*args,**kwargs):
        weights=original(det,*args,**kwargs)
        return weights*.99 if det.center_q_xy[1]<0 else weights
    monkeypatch.setattr(VirtualDetector,'integration_weights',inconsistent)
    with pytest.raises(ValueError,match='weights do not match'):
        paired_geometry(model,x,y)


def test_binary_weights_preserve_center_masks_and_observed_scale_uses_plus_only():
    model,x,y,g=geometry(mode='binary')
    for name,w in g['physical_weights'].items():np.testing.assert_array_equal(w,model.detectors[name].mask(x,y))
    e=np.linspace(837.,883.,185);a=2.+.01*(e-837);b=1.+.01*(e-837)
    alpha=normalize_postedge(e,a,b,(878.,882.))['alpha']
    n=2.+x+y*.1;m=.01*y
    first=paired_maps(n+m,n-m,alpha,g);second=paired_maps(n+m,n-5*m,alpha,g)
    np.testing.assert_array_equal(first['D_corrected'],second['D_corrected'])
    assert not np.allclose(first['I_mag'],second['I_mag'])
    err=map_error(first['D_nonmag']*0,first['D_nonmag']*0,g,1.)
    assert not err['relative_valid'] and np.isnan(err['l2_relative']) and err['l2_abs']==0


def test_small_real_source_matched_conventions_and_pickle_free_export(tmp_path):
    source=Path(__file__).resolve().parents[1]/'data/wien2k_ni/Ni_fm.xmcd'
    cfg=MapConfig(conditions=('near-2bc',),thickness_nm=(.5,),potential_cutoff=.6,
        beam_cutoff=1.2,fft_grid=16,depth_steps=4,detector_grid=17,energy_points=65)
    r=run_map_comparison(source,cfg)
    assert r['metadata']['propagation']['config']['integration_mode']=='fractional'
    assert r['metadata']['source_sha256']==r['metadata']['propagation']['xmcd_sha256']
    c=r['cases'][0]
    for row in r['rows']:
        if 'paired_detector_reconstruction_max_abs' in row:assert row['paired_detector_reconstruction_max_abs']<1e-14
    assert c['map_errors'][0]['D_raw']['l2_relative']<.01
    assert c['map_errors'][0]['D_corrected']['l2_relative']<.01
    for m in c['methods']:
        s=m['spectra'];assert s['alpha_obs'][0]==pytest.approx(normalize_postedge(s['energy_ev'],s['I_A_plus'],s['I_B_plus'],(878.,882.))['alpha'])
    # Effective eta=0 is reversal invariant, without hard-coded Ni signals.
    zero=effective_tensor_from_xmcd(source,np.array([852.7,870.]),eta=0.)
    np.testing.assert_array_equal(zero.tensor_angstrom2_per_ev.imag,0)
    zero_result=run_map_comparison(source,replace(cfg,eta=0.))
    for method in zero_result['cases'][0]['methods']:
        for fields in method['maps']:
            np.testing.assert_array_equal(fields['I_mag'],0)
            np.testing.assert_array_equal(fields['D_mag'][zero_result['cases'][0]['geometry']['valid']],0)
    save_comparison(r,tmp_path)
    loaded=load_comparison(tmp_path)
    np.testing.assert_array_equal(loaded['cases'][0]['methods'][0]['maps'][0]['D_corrected'],c['methods'][0]['maps'][0]['D_corrected'])
    with np.load(tmp_path/'map_comparison.npz',allow_pickle=False) as data:
        for k in data.files:assert data[k].dtype.kind!='O'
        assert data['I_plus'].shape==(1,2,2,17,17)
        assert data['spectra__energy_ev'].shape==(1,2,65)
