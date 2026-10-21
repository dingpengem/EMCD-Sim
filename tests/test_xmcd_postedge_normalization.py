"""Focused post-edge algebra, oracle separation and one small real-source run."""
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from emcd_sim.xmcd_postedge_normalization import (
    normalize_postedge, analyze_postedge_spectra, recovery_diagnostics,
)

E=np.linspace(0.,10.,101)
EDGE_WINDOWS={'L3':(1.,3.),'L2':(4.,6.)}


def test_constant_nonmagnetic_imbalance_removed_exactly():
    b=1.+np.exp(-(E-2.)**2)
    a=2.3*b
    original=a.copy()
    fit=normalize_postedge(E,a,b,(8.,10.))
    assert fit['alpha']==pytest.approx(2.3)
    np.testing.assert_allclose(fit['difference'],0.,atol=2e-15)
    np.testing.assert_array_equal(a,original)
    result=analyze_postedge_spectra(E,a,b,a,b,windows=((8.,10.),),edge_windows=EDGE_WINDOWS)
    np.testing.assert_array_equal(result.spectra['D_mag'],0)
    np.testing.assert_allclose(result.spectra['D_corrected'],0,atol=2e-15)
    row=next(r for r in result.comparisons if r['scope']=='full' and r['normalization']=='obs')
    assert row['nonmag_suppression']==pytest.approx(1.)
    assert np.isnan(row['magnetic_amplitude_change'])
    assert 'magnetic_amplitude_change' in json.loads(row['undefined_reasons_json'])


def test_observed_uses_plus_only_oracle_uses_even_only_and_exact_residuals():
    n=1.+np.exp(-(E-2.)**2)
    ma=.1*np.exp(-(E-2.)**2)+.01
    mb=-.04*np.exp(-(E-2.)**2)+.02
    ap,bp,am,bm=2*n+ma,n+mb,2*n-ma,n-mb
    base=analyze_postedge_spectra(E,ap,bp,am,bm,windows=((8.,10.),),edge_windows=EDGE_WINDOWS)
    modified=analyze_postedge_spectra(E,ap,bp,am+.2,bm,windows=((8.,10.),),edge_windows=EDGE_WINDOWS)
    assert base.spectra['alpha_obs'][0]==modified.spectra['alpha_obs'][0]
    assert base.spectra['alpha_nonmag'][0]!=modified.spectra['alpha_nonmag'][0]
    # Changing magnetic terms with fixed N changes observed alpha but not oracle alpha.
    changed=analyze_postedge_spectra(E,2*n+2*ma,n+2*mb,2*n-2*ma,n-2*mb,
        windows=((8.,10.),),edge_windows=EDGE_WINDOWS)
    assert base.spectra['alpha_nonmag'][0]==pytest.approx(changed.spectra['alpha_nonmag'][0])
    assert base.spectra['alpha_obs'][0]!=changed.spectra['alpha_obs'][0]
    assert base.spectra['alpha_nonmag'][0]==pytest.approx(2.)
    assert abs(base.spectra['alpha_obs'][0]-2.)>1e-3
    assert base.spectra['alpha_obs_minus'][0]!=base.spectra['alpha_obs'][0]
    s=base.spectra
    for kind,name in [('obs','D_corrected'),('oracle','D_oracle')]:
        alpha=s['alpha_obs' if kind=='obs' else 'alpha_nonmag'][0]
        np.testing.assert_allclose(s[name][0],s['D_nonmag_residual_'+kind][0]+s['D_mag_processed_'+kind][0],atol=1e-14)
        np.testing.assert_allclose(s['D_mag_processed_'+kind][0],s['D_mag']-(alpha-1)*s['M_B'],atol=1e-14)
        assert not np.allclose(s['D_mag_processed_'+kind][0],s['D_mag'])
    nodes=normalize_postedge(E,ap,bp,(8.,10.))['integration_nodes_ev']
    integrate=np.trapezoid if hasattr(np,'trapezoid') else np.trapz
    assert integrate(np.interp(nodes,E,s['D_corrected'][0]),x=nodes)==pytest.approx(0.,abs=1e-13)
    assert integrate(np.interp(nodes,E,s['D_nonmag_residual_oracle'][0]),x=nodes)==pytest.approx(0.,abs=1e-13)
    np.testing.assert_array_equal(s['I_A_plus'],ap)
    np.testing.assert_array_equal(s['I_B_plus'],bp)


@pytest.mark.parametrize('window',[(-1.,2.),(9.,11.),(5.,5.),(8.01,8.09),(8.,7.)])
def test_bad_windows_rejected(window):
    with pytest.raises(ValueError):normalize_postedge(E,np.ones_like(E),np.ones_like(E),window)


def test_negligible_postedge_and_nonfinite_data_rejected():
    b=np.ones_like(E); b[E>=8]=1e-20
    with pytest.raises(ValueError,match='nonnegligible'):normalize_postedge(E,np.ones_like(E),b,(8.,10.))
    with pytest.raises(ValueError):normalize_postedge(E,np.zeros_like(E),np.zeros_like(E),(8.,10.))
    b[0]=np.nan
    with pytest.raises(ValueError,match='finite'):normalize_postedge(E,np.ones_like(E),b,(8.,10.))


def test_exact_window_endpoints_and_undefined_signed_integral():
    fit=normalize_postedge(E,2+E,1+E,(8.03,9.97))
    expected=((2*9.97+9.97**2/2)-(2*8.03+8.03**2/2))/((9.97+9.97**2/2)-(8.03+8.03**2/2))
    assert fit['alpha']==pytest.approx(expected)
    assert fit['integration_nodes_ev'][0]==8.03 and fit['integration_nodes_ev'][-1]==9.97
    mag=np.sin(2*np.pi*E/10)
    metrics,reasons=recovery_diagnostics(E,mag,np.zeros_like(E),mag,np.zeros_like(E),mag,np.ones_like(E))
    assert metrics['magnetic_shape_correlation']==pytest.approx(1.)
    assert metrics['magnetic_amplitude_ratio']==pytest.approx(1.)
    assert np.isnan(metrics['magnetic_integral_change'])
    assert 'cancels' in reasons['magnetic_integral_change']
    assert np.isnan(metrics['nonmag_suppression'])
