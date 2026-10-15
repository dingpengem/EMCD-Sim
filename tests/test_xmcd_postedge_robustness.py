"""Focused diagnostic identities and matched-control guards (no parameter sweep)."""
from dataclasses import asdict, replace
import numpy as np
import pytest
from emcd_sim.xmcd_postedge_normalization import PostedgeConfig, analyze_postedge_spectra
from emcd_sim.xmcd_postedge_robustness import normalization_bias_diagnostics, compare_runs


def synthetic(config=PostedgeConfig()):
    e=np.linspace(837.,883.,185)
    n=1.+np.exp(-((e-850.)/3.)**2)
    na=(1.2+.001*(e-837.))*n
    ma=.05*np.exp(-((e-851.)/2.)**2)+.003
    mb=-.03*np.exp(-((e-851.)/2.)**2)+.002
    r=analyze_postedge_spectra(e,na+ma,n+mb,na-ma,n-mb,
        windows=config.postedge_windows,edge_windows={'L3':config.l3_window,'L2':config.l2_window})
    r.metadata.update(config=asdict(config),source_sha256='synthetic',tilt_mrad_xy=[0.,25.])
    return r


def test_three_bias_terms_reconstruct_and_ratio_is_diagnostic_only():
    r=synthetic(); before={k:v.copy() for k,v in r.spectra.items() if isinstance(v,np.ndarray)}
    d=normalization_bias_diagnostics(r)
    np.testing.assert_allclose(r.spectra['D_corrected']-r.spectra['D_mag'],
        d['oracle_even_mismatch']+d['postedge_magnetic_bias_even']+d['magnetic_scaling_change'],atol=1e-14)
    np.testing.assert_allclose(d['R_nonmag'],r.spectra['N_A']/r.spectra['N_B'])
    assert np.ptp(d['R_nonmag'])>.01
    for k,v in before.items():np.testing.assert_array_equal(r.spectra[k],v)
    # Reverse-state data change the oracle but cannot affect experimentally observed alpha.
    s=r.spectra
    changed=analyze_postedge_spectra(s['energy_ev'],s['I_A_plus'],s['I_B_plus'],
        s['I_A_minus']+.1,s['I_B_minus'],windows=r.metadata['config']['postedge_windows'],
        edge_windows={'L3':(844.,862.),'L2':(864.,874.)})
    np.testing.assert_array_equal(changed.spectra['alpha_obs'],s['alpha_obs'])
    assert not np.allclose(changed.spectra['alpha_nonmag'],s['alpha_nonmag'])


def test_ratio_masks_nonpositive_denominator():
    r=synthetic();s=r.spectra
    bp=s['I_B_plus'].copy();bm=s['I_B_minus'].copy()
    bp[:3]=bm[:3]=[0.,-1.,1e-20]
    r=analyze_postedge_spectra(s['energy_ev'],s['I_A_plus'],bp,s['I_A_minus'],bm,
        windows=((878.,882.),),edge_windows={'L3':(844.,862.),'L2':(864.,874.)})
    d=normalization_bias_diagnostics(r)
    assert not d['valid_R_nonmag'][:3].any()
    assert np.isnan(d['R_nonmag'][:3]).all()
    assert ((d['R_nonmag']*0)[3:]==0).all()


def test_comparison_rejects_confounded_controls_and_source():
    left=synthetic();right=synthetic(replace(PostedgeConfig(),cutoff=1.8))
    pair=compare_runs(left,right,'cutoff')
    assert not pair['sensitive']
    assert all(v==0 for v in pair['signal_norm_absolute_differences'].values())
    right.metadata['config']['grid']=97
    with pytest.raises(ValueError,match='only cutoff'):compare_runs(left,right,'cutoff')
    right.metadata['config']['grid']=65;right.metadata['source_sha256']='other'
    with pytest.raises(ValueError,match='identical source'):compare_runs(left,right,'cutoff')
