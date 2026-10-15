"""Focused matched-basis physics checks; no convergence campaign."""
from dataclasses import replace
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from emcd_sim.benchmark import nickel_physical_benchmark
from emcd_sim.crystal import fcc_nickel
from emcd_sim.diffraction import select_diffraction_setup
from emcd_sim.elastic import BeamSet
from emcd_sim.geometry import electron_wavelength_angstrom
from emcd_sim.xmcd_basis_convergence import BasisConvergenceConfig, run_basis_convergence, selected_energy_grid


@pytest.fixture
def xmcd(tmp_path):
    p = tmp_path/'synthetic.xmcd'
    e = np.array([837., 852.7, 870., 882.])
    rp, lp = np.array([1.,3.,2.,1.]), np.array([1.,2.,3.,1.])
    np.savetxt(p, np.column_stack((e,rp,lp,rp-lp,rp+lp)))
    return p


@pytest.fixture
def config():
    return BasisConvergenceConfig(g_cutoffs=(.75,.85), grid=17, steps=3,
                                   thickness_nm=3., l2_energy_ev=870.)


def test_analytic_and_numerical_y_tilt():
    crystal = fcc_nickel()
    tx = select_diffraction_setup('near-2bc', crystal).tilt_mrad_xy[0]
    zolz = BeamSet.zolz(crystal, .85)
    assert any(h[1] != 0 for h in zolz.hkl)
    for beams in (BeamSet.systematic_row(3), zolz):
        models = [nickel_physical_benchmark(tilt_mrad_xy=(tx,ty), beams_override=beams)
                  for ty in (0.,25.)]
        delta = models[1].elastic.hamiltonian_nm_inv()-models[0].elastic.hamiltonian_nm_inv()
        gy = models[0].elastic.reciprocal_vectors_xy[:,1]
        dky = (models[1].elastic.microscope.incident_k_xy-models[0].elastic.microscope.incident_k_xy)[1]
        expected = np.diag(-20*np.pi*electron_wavelength_angstrom(200.)*dky*gy)
        np.testing.assert_allclose(delta, expected, rtol=1e-12, atol=1e-12)
        if np.all(gy == 0):
            np.testing.assert_allclose(delta, 0, atol=1e-12)
            np.testing.assert_allclose(models[0].elastic.amplitudes(np.array([3.,30.])),
                                       models[1].elastic.amplitudes(np.array([3.,30.])), atol=1e-11)
        else:
            assert np.max(abs(delta)) > .1
            a,b = [abs(m.elastic.amplitudes(np.array([30.]))[0])**2 for m in models]
            assert np.max(abs(a-b)) > 1e-4


def test_parity_and_matched_inputs(xmcd, config, monkeypatch):
    from emcd_sim import xmcd_basis_convergence as module
    original = module.run_xmcd_reversal
    captured = []
    def wrapped(model, source, energies, **kwargs):
        result = original(model, source, energies, **kwargs)
        captured.append((dict(model.detectors), model.chiral_groups, energies.copy(),
                         model.elastic.microscope.tilt_mrad_xy, result.tensor_sources))
        return result
    monkeypatch.setattr(module, 'run_xmcd_reversal', wrapped)
    plus, metadata = run_basis_convergence(xmcd, config)
    minus, _ = run_basis_convergence(xmcd, replace(config, eta=-1))
    zero, _ = run_basis_convergence(xmcd, replace(config, eta=0))
    assert metadata['source_peak_N'] == 2.5
    assert metadata['xmcd_sha256'] == hashlib.sha256(xmcd.read_bytes()).hexdigest()
    assert metadata['selected_energies_ev'] == {'L3':852.7, 'L2':870.}
    assert len(metadata['energy_grid_ev']) == 2
    for detectors, groups, energies, tilt, sources in captured:
        assert detectors == captured[0][0] and groups == captured[0][1]
        np.testing.assert_array_equal(energies, captured[0][2])
        assert tilt[0] == captured[0][3][0]
        assert all(metadata['xmcd_sha256'] in s for s in sources)
        assert all('beta=1.0' in s for s in sources)
    # Tensor normalization is source-only, so equality of source, energies,
    # eta/beta and detector inputs guarantees equality across beam bases.
    first_count = len(captured)//3
    assert all(c[4] == captured[0][4] for c in captured[:first_count])
    for p,m,z in zip(plus,minus,zero):
        assert p['valid'] and p['valid_raw_plus'] and p['valid_raw_minus']
        assert p['total_elastic'] == pytest.approx(1., abs=1e-12)
        assert min(p['elastic_intensity']) >= 0
        assert p['A_odd'] == pytest.approx(-m['A_odd'], abs=1e-12)
        assert p['A_even'] == pytest.approx(m['A_even'], abs=1e-12)
        assert z['A_odd'] == pytest.approx(0, abs=1e-14)
        assert z['delta_odd'] == pytest.approx(0, abs=1e-14)
        np.testing.assert_allclose(p['delta_plus'], p['delta_even']+p['delta_odd'], atol=1e-14)
        assert p['sigma_ref'] == pytest.approx((p['sigma_plus']+p['sigma_minus'])/2)
        if p['basis_kind'] == 'systematic-row':
            assert p['hamiltonian_change_vs_y0'] < 1e-12
        elif p['tilt_y_mrad'] == 25.:
            assert p['hamiltonian_change_vs_y0'] > .1
        if p['basis_index'] == 2:
            prev = next(r for r in plus if r['basis_index']==1 and r['edge']==p['edge']
                        and r['tilt_y_mrad']==p['tilt_y_mrad'])
            assert p['A_odd_abs_diff_previous'] == pytest.approx(abs(p['A_odd']-prev['A_odd']))
            assert p['A_odd_abs_diff_largest'] == 0.
            assert p['elastic_tv_largest'] == 0.
        else:
            assert np.isnan(p['A_odd_abs_diff_previous'])
    assert max(abs(r['A_odd']) for r in plus) > 1e-8


def test_energy_selection_and_clipping(xmcd, config):
    energies, selected = selected_energy_grid(np.array([850.,852.,870.]), {'L3':869.9})
    np.testing.assert_array_equal(energies, [852.,870.])
    assert selected == {'L3':870.}
    with pytest.raises(ValueError, match='cover'):
        selected_energy_grid(np.array([850.,870.]), {'L3':880.})
    # Even max_beams can clip a +/- pair while returning fewer than the cap.
    with pytest.raises(ValueError, match='truncates'):
        run_basis_convergence(xmcd, replace(config, max_beams=8))
    with pytest.raises(ValueError, match='same basis'):
        run_basis_convergence(xmcd, replace(config, g_cutoffs=(.70,.75)))


def test_small_cli_and_output_integrity(tmp_path):
    # One small real-source reference run: 8 geometries, only two energy samples.
    source = Path(__file__).resolve().parents[1]/'data/wien2k_ni/Ni_fm.xmcd'
    output = tmp_path/'Ni basis paths with spaces'
    result = subprocess.run([sys.executable, '-m', 'emcd_sim.xmcd_basis_convergence',
        '--xmcd-file', str(source), '--output', str(output)],
        capture_output=True, text=True, check=True, timeout=120)
    assert 'finite comparison' in result.stdout
    metadata = json.loads((output/'convergence_metadata.json').read_text(encoding='utf-8'))
    assert metadata['python_version'] == sys.version.split()[0]
    assert metadata['xmcd_sha256'] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert metadata['config']['y_tilts_mrad'] == [0.,25.]
    assert metadata['config']['thickness_nm'] == 30.
    assert metadata['config']['acceleration_kv'] == 200.
    assert metadata['absolute_cross_section'] is False
    assert metadata['outgoing_channeling'] is False and metadata['quantitative_Ni'] is False
    assert metadata['reference_is_finite_not_validated'] is True
    assert [b['beam_count'] for b in metadata['bases']] == [7,5,13,21]
    assert len(metadata['energy_grid_ev']) == 2
    with (output/'convergence_results.csv').open(encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 8
    with np.load(output/'convergence_results.npz', allow_pickle=False) as data:
        assert len(data['A_odd']) == 8
        for i,r in enumerate(rows):
            n = int(r['beam_count'])
            basis = metadata['bases'][int(r['basis_index'])]
            assert json.loads(r['beam_hkl_json']) == basis['beam_hkl']
            np.testing.assert_array_equal(data['beam_hkl'][i,:n], basis['beam_hkl'])
            np.testing.assert_allclose(data['elastic_intensity'][i,:n], json.loads(r['elastic_intensity_json']))
            assert data['beam_valid'][i].sum() == n
            assert np.isnan(data['elastic_intensity'][i,n:]).all()
            assert float(r['energy_ev']) == metadata['selected_energies_ev']['L3']
            assert float(r['A_odd']) == data['A_odd'][i]
            assert float(r['thickness_nm']) == data['thickness_nm'][i] == 30.
            assert float(r['tilt_x_mrad']) == data['tilt_x_mrad'][i] == metadata['tilt_x_mrad']
            assert int(r['grid']) == data['grid'][i] == 25
            assert int(r['steps']) == data['steps'][i] == 20
    assert (output/'basis_parity_comparison.png').stat().st_size > 1000
    print(f'Reference output: {output}')
