"""Numerical comparison allowances must reject changes to scientific signals."""
from copy import deepcopy
from types import SimpleNamespace

import numpy as np
import pytest

from numerical_roundoff import assert_bloch_observables, assert_roundoff


def observables():
    # Dyadic raw inputs make these linear forms and percentages exact. The
    # magnetic signal is weak relative to its positive parent intensities.
    odd = 2.**-26
    values = dict(energy_ev=1., I_A_plus=1+odd, I_B_plus=1-odd,
        I_A_minus=1-odd, I_B_minus=1+odd, N_A=1., N_B=1., M_A=odd,
        M_B=-odd, D_mag=2*odd, D_nonmag=0., D_raw=2*odd, Sigma_ref=2.,
        prb_relative_dichroism_percent=100*odd, magnetic_only_percent=100*odd,
        nonmagnetic_imbalance_percent=0.)
    p,m=np.array([[1+odd],[1-odd]]),np.array([[1-odd],[1+odd]])
    maps=dict(I_plus=p,I_minus=m,I_mag=np.array([[odd],[-odd]]),I_nonmag=np.ones((2,1)),
        I_A_plus=np.array([[1+odd],[np.nan]]),I_B_plus_paired=np.array([[1-odd],[np.nan]]),
        I_A_minus=np.array([[1-odd],[np.nan]]),I_B_minus_paired=np.array([[1+odd],[np.nan]]),
        D_raw=np.array([[2*odd],[np.nan]]),D_mag=np.array([[2*odd],[np.nan]]),
        D_nonmag=np.array([[0.],[np.nan]]))
    return dict(amplitudes=np.zeros((9,3),complex), maps={'L3':maps},
                spectra={k:np.array([v]) for k,v in values.items()})


@pytest.mark.parametrize('change', ['raw_scale','odd_zero','odd_reverse','odd_percent',
                                   'even_percent','paired_odd_zero','paired_mask'])
def test_historical_roundoff_rejects_scientific_changes(change):
    expected = observables()
    actual = deepcopy(expected)
    s = actual['spectra']
    if change == 'raw_scale':
        s['I_A_plus'] *= 1.01
    elif change == 'odd_zero':
        s['M_A'] *= 0
    elif change == 'odd_reverse':
        s['M_A'] *= -1
    elif change == 'odd_percent':
        s['magnetic_only_percent'] *= 1.01
    elif change == 'even_percent':
        s['nonmagnetic_imbalance_percent'] += 1e-8
    elif change == 'paired_odd_zero':
        actual['maps']['L3']['D_mag'][0,0] = 0.
    else:
        actual['maps']['L3']['D_raw'][1,0] = 0.
    with pytest.raises(AssertionError):
        assert_bloch_observables(actual,expected,SimpleNamespace(depth=9,grid=9))


def test_roundoff_retains_undefined_values_shape_and_dtype():
    expected = np.array([1.,np.nan])
    assert_roundoff(expected.copy(),expected,1e-14)
    for actual in (np.array([1.,0.]), expected.astype(np.float32), expected.reshape(1,2)):
        with pytest.raises(AssertionError):
            assert_roundoff(actual,expected,1e-14)
