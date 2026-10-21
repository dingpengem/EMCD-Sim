"""Focused geometric weights and shared tensor-integration checks."""
from dataclasses import replace
import numpy as np
import pytest

from emcd_sim.benchmark import nickel_apertures, nickel_physical_benchmark
from emcd_sim.elastic import depth_coherence
from emcd_sim.geometry import VirtualDetector, _circle_pixel_weights
from emcd_sim.single_channeling_tensor import run_tensor_with_coherence
from emcd_sim.xmcd_effective_mdff import effective_tensor_from_xmcd
from runtime_fixtures import parity_spectra, run_xmcd_reversal


@pytest.fixture
def xmcd(tmp_path):
    p=tmp_path/'synthetic.xmcd'
    e=np.array([837.,852.7,870.,882.]); rp=np.array([1.,3.,2.,1.]); lp=np.array([1.,2.,3.,1.])
    np.savetxt(p,np.column_stack((e,rp,lp,rp-lp,rp+lp)))
    return p


def grid(n):
    return np.meshgrid(np.linspace(-1.,1.,n),np.linspace(-1.,1.,n),indexing='xy')


@pytest.mark.parametrize('n',[33,65,97])
def test_circle_area_bounds_and_symmetry(n):
    qx,qy=grid(n); dets,_=nickel_apertures('near-2bc')
    a,b=[d.integration_weights(qx,qy,mode='fractional') for d in dets.values()]
    assert np.all((a>=0)&(a<=1))
    np.testing.assert_array_equal(a,b[::-1])
    assert a is dets['A'].integration_weights(qx,qy,mode='fractional')
    assert not a.flags.writeable
    info=dets['A'].integration_info(qx,qy,mode='fractional')
    assert abs(info['relative_area_error'])<1e-3
    assert abs(info['area_error'])<abs(dets['A'].integration_info(qx,qy)['area_error'])
    assert np.sum(a*np.ones_like(a))*(qx[0,1]-qx[0,0])**2==pytest.approx(info['effective_area'])
    positive=np.random.default_rng(4).random(qx.shape)
    assert np.sum(a*positive)>=0
    hx=(qx[0,1]-qx[0,0])/2
    x,y=abs(qx-dets['A'].center_q_xy[0]),abs(qy-dets['A'].center_q_xy[1])
    inside=(x+hx)**2+(y+hx)**2<=dets['A'].radius_q**2
    outside=np.maximum(x-hx,0)**2+np.maximum(y-hx,0)**2>=dets['A'].radius_q**2
    assert np.all(a[inside]==1) and np.all(a[outside]==0)


def test_grid_clipping_and_input_validation():
    qx,qy=grid(33)
    det=VirtualDetector((1.,0.),.2)
    info=det.integration_info(qx,qy,mode='fractional')
    assert not info['aperture_fully_covered']
    assert 0<info['effective_area']<info['analytical_area']
    for kwargs in ({'mode':'unknown'},{'subpixels':0},{'subpixels':2.5}):
        with pytest.raises(ValueError):
            det.integration_weights(qx,qy,**kwargs)
    with pytest.raises(ValueError,match='uniform'):
        det.integration_weights(qx.T,qy.T,mode='fractional')


@pytest.mark.parametrize('condition',['near-2bc','symmetric-3bc'])
def test_tensor_binary_unchanged_fractional_grouping_and_parity(xmcd,condition):
    model=nickel_physical_benchmark(beam_order=1,diffraction_condition=condition)
    c=depth_coherence(model.elastic,3.,4)
    t=effective_tensor_from_xmcd(xmcd)
    options=dict(thickness_nm=3.,grid_size=17)
    legacy=run_tensor_with_coherence(model,t,c,**options)
    binary=run_tensor_with_coherence(model,t,c,integration_mode='binary',**options)
    fractional=run_tensor_with_coherence(model,t,c,integration_mode='fractional',**options)
    i=int(np.argmin(abs(t.energy_ev-852.7)))
    for name,mask in legacy.detector_masks.items():
        assert mask.dtype==bool
        np.testing.assert_array_equal(mask,fractional.detector_masks[name])
        np.testing.assert_array_equal(binary.detector_spectra[name],legacy.detector_spectra[name])
        np.testing.assert_array_equal(binary.detector_weights[name],mask.astype(float))
        total=legacy.nonmag_map_at_l3+legacy.magnetic_map_at_l3
        dq2=(legacy.qx_angstrom_inv[0,1]-legacy.qx_angstrom_inv[0,0])**2
        assert legacy.detector_spectra[name][i]==float(total[mask].sum()*dq2)
        assert fractional.detector_spectra[name][i]==pytest.approx(
            np.sum(total*fractional.detector_weights[name])*dq2,abs=1e-14)
    if condition=='symmetric-3bc':
        assert fractional.chiral_groups=={'A':('RU','LD'),'B':('RD','LU')}
        np.testing.assert_array_equal(fractional.chiral_spectrum('A'),
            fractional.detector_spectra['RU']+fractional.detector_spectra['LD'])
    # Reverse tensors on exactly the same coherence; confirm cached weight identity.
    tr=effective_tensor_from_xmcd(xmcd,eta=-1)
    reverse=run_tensor_with_coherence(model,tr,c,integration_mode='fractional',**options)
    for name in model.detectors:
        assert reverse.detector_weights[name] is fractional.detector_weights[name]
    s=parity_spectra(fractional,reverse); r=parity_spectra(reverse,fractional)
    np.testing.assert_allclose(s['delta_odd'],-r['delta_odd'],atol=1e-14)
    np.testing.assert_allclose(s['delta_even'],r['delta_even'],atol=1e-14)
    np.testing.assert_allclose(s['delta_plus'],s['delta_odd']+s['delta_even'],atol=1e-14)
    np.testing.assert_array_equal(fractional.nonmag_map_at_l3,legacy.nonmag_map_at_l3)
    np.testing.assert_array_equal(fractional.magnetic_map_at_l3,legacy.magnetic_map_at_l3)


def test_reversal_caches_weights_once_per_detector_grid(xmcd):
    model=nickel_physical_benchmark(beam_order=1,diffraction_condition='near-2bc')
    _circle_pixel_weights.cache_clear()
    run_xmcd_reversal(model,xmcd,grid_size=17,depth_steps=3,integration_mode='fractional')
    info=_circle_pixel_weights.cache_info()
    assert info.misses==2 and info.hits>=6
    zero=run_xmcd_reversal(model,xmcd,grid_size=17,depth_steps=3,eta=0,integration_mode='fractional')
    np.testing.assert_array_equal(zero.spectra['delta_odd'],0)
    assert _circle_pixel_weights.cache_info().misses==2
