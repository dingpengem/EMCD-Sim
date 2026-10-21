"""Paired-map identities and one small matched real-source calculation."""
from dataclasses import replace
from pathlib import Path
import numpy as np
import pytest
from emcd_sim.benchmark import nickel_physical_benchmark
from emcd_sim.geometry import VirtualDetector
from emcd_sim.emcd_angular_plots import paired_geometry, paired_maps, integrate_paired
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
