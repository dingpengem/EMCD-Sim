"""Patch 5A: matched historical Ni and independent, synthetic BCC Cr events.

The Ni input is the pinned historical XMCD effective model, not a new MDFF
model. Its two evaluated tensor pairs are tabulated without rescaling. Cr is
an idealized ordered BCC software benchmark, NOT bulk Cr spin-density-wave
order. Opposite unit directions do not declare calibrated magnetic moments.
These bounded finite-ZOLZ tests establish algebra/compatibility, not general
beam, angular, depth or physical-model convergence.
"""
from dataclasses import replace
import json
from unittest.mock import patch

import numpy as np
import pytest

from emcd_sim.geometry import VirtualDetector, characteristic_qz_angstrom_inv
from emcd_sim.gui import channeling
from emcd_sim.gui.emcd_forward import ForwardSettings, calculate, tensors
from emcd_sim.gui.forward_pipeline import calculate_multisite
from emcd_sim.gui.generalized_forward import settings_for_source
from emcd_sim.gui.geometry import Structure, Settings, elastic_model, geometry
from emcd_sim.multisite import IonizationSiteGroup, MultiSiteIonization
from historical_xmcd_test_support import historical_xmcd_source, HISTORICAL_XMCD_SHA256
from single_element_helpers import document
from test_multisite_forward import configuration, system, RAW_KEYS, PARITY_KEYS
from test_multisite_double_channeling import direct_site_intensity as bw_site_event
from test_multisite_ms_double_channeling import direct_site_intensity as ms_site_event
from test_single_element_ni_compatibility import old_contract  # existing archived reference fixture


def encoded(value):
    return dict(real=value.real.tolist(), imag=value.imag.tolist())


def discrepancy(actual, expected, keys):
    a = np.concatenate([actual[k] for k in keys])
    b = np.concatenate([expected[k] for k in keys])
    return dict(max_abs=float(np.max(abs(a-b))),
                relative_norm=float(np.linalg.norm(a-b)/max(np.linalg.norm(b), 1e-30)))


def check_signals(entry):
    s = entry['spectra']
    for d in ('A', 'B'):
        p, m = s[f'I_{d}_plus'], s[f'I_{d}_minus']
        scale = max(float(np.max(abs(p))), float(np.max(abs(m))), 1e-30)
        assert min(p.min(), m.min()) >= -1e-12*scale
        np.testing.assert_allclose(s['N_'+d], (p+m)/2, rtol=3e-13, atol=1e-18)
        np.testing.assert_allclose(s['M_'+d], (p-m)/2, rtol=3e-13, atol=1e-18)
    for key, expected in (
        ('D_raw', s['I_A_plus']-s['I_B_plus']),
        ('D_mag', s['M_A']-s['M_B']),
        ('D_nonmag', s['N_A']-s['N_B']),
        ('D_raw', s['D_mag']+s['D_nonmag']),
    ):
        np.testing.assert_allclose(s[key], expected, rtol=3e-13, atol=1e-18)


@pytest.mark.parametrize('method', ['bloch', 'fft-multislice'])
@pytest.mark.parametrize('channel', ['single', 'double'])
@pytest.mark.parametrize('thickness', [2., 10.])
def test_historical_ni_matched_thicknesses(tmp_path, old_contract, method, channel, thickness):
    cfg = configuration(propagation=method, channeling_model=channel,
                        systematic_row=True, depth=33, slice_step=.04)
    fields = {k: getattr(cfg, k) for k in (
        'grid', 'depth', 'subpixels', 'fft_grid', 'slice_step', 'halfwidth',
        'centers', 'radius', 'worker_mode', 'parallel_workers', 'propagation',
        'channeling_model', 'systematic_row', 'angular_maps')}
    historical = ForwardSettings(**fields, source=str(historical_xmcd_source(tmp_path)),
        source_sha256=HISTORICAL_XMCD_SHA256, axis_declared=True, correction=False,
        energy_scope='edges')
    energy = np.array([historical.l3, historical.l2])
    pair = [t.tensor_angstrom2_per_ev for t in tensors(historical, energy, np.eye(3))]
    # Evaluate exactly the same model at exactly the requested samples. No
    # imported interpolation, new source model or peak normalization intervenes.
    data = document('Ni')
    data.update(energy_ev=energy.tolist(), selected_ev=dict(L3=energy[0], L2=energy[1]),
        T_plus=encoded(pair[0]), T_minus=encoded(pair[1]), T_even=encoded((pair[0]+pair[1])/2),
        source='Exact sampled historical Ni XMCD effective tensor pair; '+HISTORICAL_XMCD_SHA256,
        validity='Relative historical effective model; not an absolute cross section',
        status='physical_source_unvalidated')
    path = tmp_path/'ni-pair.json'
    path.write_text(json.dumps(data), encoding='utf-8')
    structure = Structure.nickel()
    settings = Settings(thickness=thickness, beam_cutoff=.9, potential_cutoff=1.8,
                        elastic_provider='nickel-lobato-2014')
    sites = MultiSiteIonization(structure, [IonizationSiteGroup(
        'Ni', 'Ni', (0, 1, 2, 3), settings_for_source(path), (0, 0, 1), 4)])
    # Reuse the established pre-feature numerical reference, not only today's
    # shared kernels. The fixture adapts historical names, not equations.
    with patch.object(channeling, 'contract', old_contract):
        legacy = calculate(structure, settings, historical, energy_ev=energy)
    result = calculate_multisite(structure, settings, sites, cfg, energy_ev=energy)
    # Reversal/detector differences can be exactly zero in the reference.
    # Subtraction roundoff is set by the raw intensity, not that zero signal.
    raw_scale = max(np.max(abs(legacy['spectra'][k])) for k in RAW_KEYS)
    roundoff = max(1e-17, 8*np.finfo(float).eps*raw_scale)
    for key in RAW_KEYS+PARITY_KEYS:
        np.testing.assert_allclose(result['spectra'][key], legacy['spectra'][key],
                                   rtol=3e-13, atol=roundoff)
    for edge in ('L3', 'L2'):
        map_scale = max(np.max(abs(legacy['maps'][edge][k])) for k in ('I_plus', 'I_minus'))
        for key in ('I_plus', 'I_minus', 'I_mag', 'I_nonmag'):
            np.testing.assert_allclose(result['maps']['Ni:'+edge][key], legacy['maps'][edge][key],
                                       rtol=3e-13, atol=max(1e-17, 8*np.finfo(float).eps*map_scale))
    assert result['metadata']['multisite']['selected_atom_count'] == 4
    check_signals(result)
    print('Ni', method, channel, thickness, 'nm',
          'beams', len(result['metadata']['beam_hkl']),
          'raw', discrepancy(result['spectra'], legacy['spectra'], RAW_KEYS),
          'odd', discrepancy(result['spectra'], legacy['spectra'], ('M_A', 'M_B')))


def cr_case(tmp_path, unequal):
    structure, settings, original, _ = system(tmp_path, 'Cr')
    settings = replace(settings, thickness=.5, beam_cutoff=.55, potential_cutoff=.8)
    groups, declared = [], {}
    for group in original.groups:
        data = document('Cr')
        decode = lambda k: np.asarray(data[k]['real'])+1j*np.asarray(data[k]['imag'])
        even = decode('T_even')
        odd = (decode('T_plus')-decode('T_minus'))/2
        sign = 1 if group.group_id == 'up' else -1
        # Deliberately inequivalent synthetic spectroscopy in the second case;
        # the magnetic directions still sum to zero. Both complete tensors PSD.
        amplitude = .6 if unequal and sign < 0 else 1.
        pair = (even+sign*amplitude*odd, even-sign*amplitude*odd)
        for tensor in pair:
            np.testing.assert_allclose(tensor, tensor.swapaxes(-1, -2).conj(), atol=0)
            assert np.linalg.eigvalsh(tensor).min() > 0
        data.update(magnetization_crystal=list(group.magnetization),
                    T_plus=encoded(pair[0]), T_minus=encoded(pair[1]))
        path = tmp_path/(group.group_id+'-declared.json')
        path.write_text(json.dumps(data), encoding='utf-8')
        groups.append(replace(group, mdff_reference=settings_for_source(path)))
        declared[group.group_id] = pair
    return structure, settings, MultiSiteIonization(structure, groups), declared


def test_ni_bounded_depth_quadrature_against_independent_gauss(tmp_path):
    """Isolate depth error; detector centers only, not angular/basis convergence."""
    cfg = ForwardSettings(source=str(historical_xmcd_source(tmp_path)), axis_declared=True,
                          source_sha256=HISTORICAL_XMCD_SHA256, correction=False)
    structure = Structure.nickel()
    queries = np.array([[.2, .2], [.2, -.2]])
    for thickness in (2., 10.):
        settings = Settings(thickness=thickness, beam_cutoff=.9, potential_cutoff=1.8,
                            elastic_provider='nickel-lobato-2014')
        elastic = elastic_model(structure, settings)
        rotation = geometry(structure, settings)[1]
        pair = tensors(cfg, np.array([cfg.l3, cfg.l2]), rotation)
        def events(method, nodes):
            return np.array([[bw_site_event(elastic, loss, queries, np.zeros(3), tensor,
                thickness, method, nodes) for loss, tensor in
                zip((cfg.l3, cfg.l2), state.tensor_angstrom2_per_ev)] for state in pair])
        reference = events('analytic', 40)  # independent Gauss event amplitudes
        errors = []
        for nodes in (33, 65):
            actual = events('numerical', nodes)
            odd, odd_ref = (actual[0]-actual[1])/2, (reference[0]-reference[1])/2
            errors.append(dict(raw=float(np.linalg.norm(actual-reference)/np.linalg.norm(reference)),
                odd=float(np.linalg.norm(odd-odd_ref)/np.linalg.norm(odd_ref))))
        for kind in ('raw', 'odd'):
            assert errors[1][kind] < errors[0][kind]/3.8
        print('Ni independent depth quadrature', thickness, 'nm nodes33/65', errors)


def single_site_event(elastic, fields, z, loss, queries, position, tensor):
    """Direct coherent event amplitudes at each depth, no angular-map/response API."""
    phase = np.exp(2j*np.pi*(np.asarray(elastic.beams.hkl)@position))
    result = []
    for query in queries:
        q = np.column_stack((query-elastic.reciprocal_vectors_xy,
            np.full(len(phase), -characteristic_qz_angstrom_inv(
                loss, elastic.microscope.acceleration_kv))))*2*np.pi
        amplitude = (fields*phase)@(q/np.sum(q*q, axis=1)[:, None])
        values = np.einsum('za,ba,zb->z', amplitude, tensor, amplitude.conj()).real
        result.append(np.sum(np.diff(z)*(values[1:]+values[:-1])/2))
    return np.asarray(result)


@pytest.mark.parametrize('method', ['bloch', 'fft-multislice'])
@pytest.mark.parametrize('channel', ['single', 'double'])
@pytest.mark.parametrize('unequal', [False, True], ids=['equivalent', 'unequal-mdff'])
def test_bcc_cr_independent_events_and_symmetry(tmp_path, method, channel, unequal):
    structure, settings, sites, declared = cr_case(tmp_path, unequal)
    energy = np.array([710., 723.])  # illustrative synthetic labels, not Cr edges
    cfg = configuration(propagation=method, channeling_model=channel,
                        depth=17, slice_step=.02, angular_maps=False)
    result = calculate_multisite(structure, settings, sites, cfg, energy_ev=energy)
    reverse = calculate_multisite(structure, settings, sites, cfg, energy_ev=energy,
                                  reverse_magnetization=True)
    positions = structure.atoms.get_scaled_positions()
    np.testing.assert_allclose(positions, [[0, 0, 0], [.5, .5, .5]], rtol=0, atol=1e-15)
    np.testing.assert_array_equal(sum(np.asarray(g.magnetization) for g in sites.groups), [0, 0, 0])
    assert [g.indices for g in sites.groups] == [(0,), (1,)]
    elastic = elastic_model(structure, settings)
    rotation = geometry(structure, settings)[1]
    hkl = np.asarray(elastic.beams.hkl)
    assert len(hkl) == 5
    # Chemical BCC selection gives even h+k+l. Thus BOTH localized-event
    # phase factors equal one in this basis, explaining equal-pair cancellation.
    assert np.all(hkl.sum(axis=1) % 2 == 0)
    for p in positions:
        np.testing.assert_allclose(np.exp(2j*np.pi*(hkl@p)), 1., atol=1e-14)
    q = np.linspace(-cfg.halfwidth, cfg.halfwidth, cfg.grid)
    qx, qy = np.meshgrid(q, q)
    weights = {d: VirtualDetector(tuple(c), cfg.radius).integration_weights(
        qx, qy, mode='fractional', subpixels=cfg.subpixels)
        for d, c in zip(('A', 'B'), cfg.centers)}
    support = np.logical_or.reduce([w.ravel() > 0 for w in weights.values()])
    queries = np.column_stack((qx.ravel()[support], qy.ravel()[support]))
    if method == 'fft-multislice' and channel == 'double':
        grid = channeling.fft_geometry(elastic, settings, cfg)
        incoming = channeling.incident_fields(grid, settings.thickness,
            depth_steps=cfg.depth, slice_step_nm=cfg.slice_step)
    worst = 0.
    for group in sites.groups:
        entry = result['groups'][group.group_id]
        for state, tensors_crystal in zip(('plus', 'minus'), declared[group.group_id]):
            for ie, loss in enumerate(energy):
                tensor = rotation@tensors_crystal[np.argmin(abs(np.array(document()['energy_ev'])-loss))]@rotation.T
                if channel == 'single':
                    intensity = single_site_event(elastic, result['amplitudes'], result['depth_nm'],
                        loss, queries, positions[group.indices[0]], tensor)
                elif method == 'bloch':
                    intensity = bw_site_event(elastic, loss, queries, positions[group.indices[0]],
                        tensor, settings.thickness, 'numerical', cfg.depth)
                else:
                    intensity = ms_site_event(elastic, grid, incoming, loss, queries,
                        positions[group.indices[0]], tensor)
                for d in ('A', 'B'):
                    expected = np.sum(intensity*weights[d].ravel()[support])*(q[1]-q[0])**2
                    actual = entry['spectra'][f'I_{d}_{state}'][ie]
                    np.testing.assert_allclose(actual, expected, rtol=3e-12, atol=1e-17)
                    worst = max(worst, abs(actual-expected)/max(abs(expected), 1e-30))
    assert result['metadata']['multisite']['selected_atom_count'] == 2
    for key in RAW_KEYS+PARITY_KEYS:
        expected = sum(g.multiplicity*result['groups'][g.group_id]['spectra'][key]
                       for g in sites.groups)/2
        np.testing.assert_allclose(result['spectra'][key], expected, rtol=3e-13, atol=1e-18)
    for name in (None, 'up', 'down'):
        forward = result if name is None else result['groups'][name]
        backward = reverse if name is None else reverse['groups'][name]
        check_signals(forward)
        check_signals(backward)
        for d in ('A', 'B'):
            np.testing.assert_allclose(forward['spectra'][f'I_{d}_plus'],
                backward['spectra'][f'I_{d}_minus'], rtol=3e-13, atol=1e-18)
            np.testing.assert_allclose(forward['spectra']['N_'+d], backward['spectra']['N_'+d],
                                       rtol=3e-13, atol=1e-18)
            np.testing.assert_allclose(forward['spectra']['M_'+d], -backward['spectra']['M_'+d],
                                       rtol=3e-13, atol=1e-18)
    scale = max(np.max(abs(result['groups']['up']['spectra']['M_A'])), 1e-30)
    assert scale > 1e-12
    odd_ratio = float(np.max(abs(result['spectra']['M_A']))/scale)
    if unequal:
        raw_scale = max(np.max(abs(result['spectra'][k])) for k in RAW_KEYS)
        for d in ('A', 'B'):
            np.testing.assert_allclose(result['spectra']['M_'+d],
                .2*result['groups']['up']['spectra']['M_'+d], rtol=3e-13,
                atol=8*np.finfo(float).eps*raw_scale)
        assert odd_ratio > .1
    else:
        assert odd_ratio < 1e-11
    print('Cr', method, channel, 'unequal', unequal,
          'independent_event_max_relative', worst, 'total_to_up_odd', odd_ratio,
          'D_raw', result['spectra']['D_raw'].tolist(),
          'D_mag', result['spectra']['D_mag'].tolist(),
          'D_nonmag', result['spectra']['D_nonmag'].tolist())
