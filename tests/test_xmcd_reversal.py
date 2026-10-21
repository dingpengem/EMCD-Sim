from dataclasses import replace
import json
import subprocess
import sys

import numpy as np
import pytest

from emcd_sim.benchmark import nickel_physical_benchmark
from emcd_sim.geometry import VirtualDetector
from emcd_sim.xmcd_effective_mdff import effective_tensor_from_xmcd
from runtime_fixtures import run_xmcd_reversal, normalized_signal, parity_spectra


@pytest.fixture
def xmcd(tmp_path):
    path = tmp_path/'synthetic.xmcd'
    e = np.array([837., 852.7, 870., 882.])
    rp, lp = np.array([1., 3., 2., 1.]), np.array([1., 2., 3., 1.])
    np.savetxt(path, np.column_stack((e, rp, lp, rp-lp, rp+lp)))
    return path


def test_tensor_reversal_and_validity(xmcd):
    plus = effective_tensor_from_xmcd(xmcd).tensor_angstrom2_per_ev
    minus = effective_tensor_from_xmcd(xmcd, eta=-1).tensor_angstrom2_per_ev
    np.testing.assert_array_equal(plus.real, minus.real)
    np.testing.assert_array_equal(plus.imag, -minus.imag)
    for t in (plus, minus):
        np.testing.assert_allclose(t, t.conj().swapaxes(1, 2))
        assert np.linalg.eigvalsh(t).min() >= -1e-12
    for kwargs in ({'eta':10}, {'beta':-1}, {'eta':float('nan')}):
        with pytest.raises(ValueError):
            effective_tensor_from_xmcd(xmcd, **kwargs)


@pytest.mark.parametrize('condition', ['near-2bc', 'symmetric-3bc'])
def test_parity_and_geometry(xmcd, condition):
    model = nickel_physical_benchmark(beam_order=1, tilt_mrad_xy=(-5., 25.),
                                       diffraction_condition=condition)
    basis = np.array(model.elastic.beams.hkl)
    detectors = dict(model.detectors)
    amplitudes = model.elastic.amplitudes(np.array([0., 3.])).copy()
    kw = dict(grid_size=17, depth_steps=3, thickness_nm=3.)
    result = run_xmcd_reversal(model, xmcd, **kw)
    reverse = run_xmcd_reversal(model, xmcd, eta=-1, **kw)
    s, r = result.spectra, reverse.spectra
    np.testing.assert_allclose(s['delta_odd'], -r['delta_odd'], atol=1e-15)
    np.testing.assert_allclose(s['delta_even'], r['delta_even'], atol=1e-15)
    np.testing.assert_allclose(s['delta_plus'], s['delta_even']+s['delta_odd'], atol=1e-15)
    np.testing.assert_allclose(s['delta_minus'], s['delta_even']-s['delta_odd'], atol=1e-15)
    for edge, m in result.maps.items():
        assert np.min(m['I_plus']) >= -1e-8
        assert np.min(m['I_minus']) >= -1e-8
        np.testing.assert_allclose(m['I_odd'], -reverse.maps[edge]['I_odd'], atol=1e-15)
        np.testing.assert_allclose(m['I_even'], reverse.maps[edge]['I_even'], atol=1e-15)
        assert m['energy_ev'] == (852.7 if edge == 'L3' else 870.)
    np.testing.assert_array_equal(basis, model.elastic.beams.hkl)
    assert detectors == model.detectors
    np.testing.assert_array_equal(amplitudes, model.elastic.amplitudes(np.array([0., 3.])))
    if condition == 'symmetric-3bc':
        assert model.chiral_groups == {'A': ('RU', 'LD'), 'B': ('RD', 'LU')}
    # Check grouping against the existing forward solver, independently of parity.
    from emcd_sim.single_channeling_tensor import run_tensor_single_channeling
    forward = run_tensor_single_channeling(model, effective_tensor_from_xmcd(xmcd), **kw)
    names = model.chiral_groups['A'] if model.chiral_groups else ('A',)
    np.testing.assert_allclose(s['I_A_plus'], sum(forward.detector_spectra[n] for n in names))


def test_zero_magnetic_asymmetric_detectors(xmcd):
    model = nickel_physical_benchmark(beam_order=1, tilt_mrad_xy=(-5., 25.))
    model = replace(model, detectors={'A':VirtualDetector((.25,.25), .15),
                                      'B':VirtualDetector((.5,-.25), .15)})
    result = run_xmcd_reversal(model, xmcd, eta=0, grid_size=17, depth_steps=3)
    np.testing.assert_array_equal(result.spectra['delta_odd'], 0)
    assert np.max(abs(result.spectra['delta_even'])) > 1e-10
    for m in result.maps.values():
        np.testing.assert_array_equal(m['I_odd'], 0)


def test_normalization_and_distinct_denominators():
    value, valid = normalized_signal(np.ones(3), np.array([0., 1e-15, 1.]))
    np.testing.assert_array_equal(valid, [False, False, True])
    assert np.isnan(value[:2]).all()
    # Raw asymmetries have different denominators: their odd part is not A_odd.
    class Result:
        energy_ev = np.array([850., 851.])
        def __init__(self, a, b): self.a, self.b = np.array(a), np.array(b)
        def chiral_spectrum(self, label): return self.a if label == 'A' else self.b
    s = parity_spectra(Result([4.,0.], [2.,0.]), Result([2.,0.], [1.,0.]))
    assert s['A_odd'][0] != (s['A_raw_plus'][0]-s['A_raw_minus'][0])/2
    assert not s['valid'][1] and np.isnan(s['A_odd'][1])
