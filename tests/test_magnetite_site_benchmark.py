"""Patch 5B: real cubic spinel geometry, synthetic spectroscopy only.

Geometry: Fd-3m origin choice 2, 8a=(1/8,1/8,1/8), 16d=(1/2,1/2,1/2),
32e=(u,u,u), a=8.396 A, u=.2548. These room-temperature structural choices
are consistent with NBS Monograph 25-5 and Okudera et al., Acta Cryst. B52,
450-457 (1996); they are not a refinement of the 2011 specimen.
Calmels & Rusz, JAP 109, 07D328 (2011), doi:10.1063/1.3556769, supplies
[001], 200 kV, (210)/(120), and the 21-beam 000/{220}/{400}/{440}/{620}
comparison geometry. Its atomic-multiplet spectra are NOT reproduced here.
Synthetic A/B tensor amplitudes below carry no Fe valence/moment calibration.
Continuous-depth ZOLZ events, neutral-atom elastic factors, no absorption or
discrete ionization layers. Controls diagnose approximations, not certify full
convergence. All calculations are serial, one modeled loss (711.5 eV).
"""
from dataclasses import replace
import json

import numpy as np
import pytest
from ase.spacegroup import crystal

from emcd_sim.crystal import Crystal
from emcd_sim.gui.forward_pipeline import calculate_multisite
from emcd_sim.gui.generalized_forward import settings_for_source
from emcd_sim.gui.geometry import Structure, Settings, elastic_model, geometry
from emcd_sim.multisite import IonizationSiteGroup, MultiSiteIonization
from emcd_sim.scattering import IndependentAtomPotential
from single_element_helpers import document
from test_multisite_forward import configuration, RAW_KEYS
from test_multisite_scientific_validation import encoded, single_site_event


LOSS = 711.5
METHODS = ('bloch', 'fft-multislice')
CHANNELS = ('single', 'double')
THICKNESSES = (20., 36., 50.)


@pytest.fixture(scope='module')
def study(tmp_path_factory):
    directory = tmp_path_factory.mktemp('magnetite')
    atoms = crystal(['Fe', 'Fe', 'O'], basis=[(.125,)*3, (.5,)*3, (.2548,)*3],
                    spacegroup=227, setting=2, cellpar=[8.396]*3+[90]*3)
    structure = Structure(atoms, source='Cubic inverse spinel; a=8.396 A, u=.2548, Fd-3m choice 2')
    groups, pairs = [], {}
    for kind, label, direction, scale in ((0, 'Fe(A)', -1, 1.), (1, 'Fe(B)', 1, 1.6)):
        indices = tuple(np.flatnonzero(atoms.arrays['spacegroup_kinds'] == kind).tolist())
        data = document('Fe')
        even = scale*np.diag([1.2, 1.2, .8])
        odd = np.array([[0, .12j, 0], [-.12j, 0, 0], [0, 0, 0]])*scale*direction
        pair = (even+odd, even-odd)
        frame = np.eye(3) if kind == 0 else np.array(
            [[2**-.5, -2**-.5, 0], [2**-.5, 2**-.5, 0], [0, 0, 1]])
        # Explicit full frame, separate from M. Cubic transverse isotropy makes
        # this declared rotation leave the physical tensor unchanged.
        # Existing provider vocabulary declares L2,3 together. Flat synthetic
        # support includes its required L2 label; ONLY LOSS is calculated.
        data.update(edge='L2,3', energy_ev=[710.5, LOSS, 723.], selected_ev={'L3': LOSS, 'L2': 723.},
            basis='declared_local', frame_to_crystal=frame.tolist(),
            magnetization_crystal=[0, 0, direction],
            source='Original synthetic '+label+' PSD pair; amplitude='+str(scale),
            validity='SOFTWARE TEST ONLY; no multiplets, valence or absolute cross-section calibration',
            T_plus=encoded(np.repeat(pair[0][None], 3, axis=0)),
            T_minus=encoded(np.repeat(pair[1][None], 3, axis=0)),
            T_even=encoded(np.repeat(even[None], 3, axis=0)))
        for t in pair:
            assert np.linalg.eigvalsh(t).min() > 0
        path = directory/(label+'.json')
        path.write_text(json.dumps(data), encoding='utf-8')
        groups.append(IonizationSiteGroup(label, 'Fe', indices, settings_for_source(path),
                                         (0, 0, direction), len(indices)))
        pairs[label] = tuple(frame@t@frame.T for t in pair)
    settings = Settings(zone=(0, 0, 1), target=(4, 0, 0), tilt=(0., 0.), voltage=200.,
        thickness=36., beam_cutoff=.76, potential_cutoff=1., elastic_provider='adaptive-dirac-pade-2026')
    cfg = configuration(grid=17, halfwidth=.36, centers=((2/8.396, 1/8.396), (1/8.396, 2/8.396)),
        radius=.018, subpixels=32, depth=129, fft_grid=32, slice_step=.10, angular_maps=False)
    return structure, settings, MultiSiteIonization(structure, groups), cfg, pairs


def forward(study, method, channel, thickness, *, reverse=False, settings=None, cfg=None):
    structure, base_settings, sites, base_cfg, _ = study
    return calculate_multisite(structure, replace(settings or base_settings, thickness=thickness), sites,
        replace(cfg or base_cfg, propagation=method, channeling_model=channel),
        energy_ev=[LOSS], reverse_magnetization=reverse)


def values(result, keys=('I_A_plus', 'I_B_plus', 'I_A_minus', 'I_B_minus')):
    return np.concatenate([entry['spectra'][key] for entry in
        [result]+[result['groups'][g] for g in ('Fe(A)', 'Fe(B)')] for key in keys])


def gaps(actual, reference):
    return {name: float(np.linalg.norm(values(actual, keys)-values(reference, keys))/
                       max(np.linalg.norm(values(reference, keys)), 1e-30))
            for name, keys in (('raw', RAW_KEYS), ('odd', ('M_A', 'M_B')))}


def check_signals(entry):
    s = entry['spectra']
    # The near-zero differences inherit the raw-intensity subtraction scale.
    # This is floating-point error, not a tolerance on a physical asymmetry.
    tolerance = 8*np.finfo(float).eps*max(np.max(abs(s[k])) for k in RAW_KEYS)
    assert min(np.min(s[k]) for k in RAW_KEYS) >= -tolerance
    for d in ('A', 'B'):
        p, m = s[f'I_{d}_plus'], s[f'I_{d}_minus']
        np.testing.assert_allclose(s['N_'+d], (p+m)/2, rtol=3e-13, atol=tolerance)
        np.testing.assert_allclose(s['M_'+d], (p-m)/2, rtol=3e-13, atol=tolerance)
    for key, expected in (('D_raw', s['I_A_plus']-s['I_B_plus']),
        ('D_mag', s['M_A']-s['M_B']), ('D_nonmag', s['N_A']-s['N_B']),
        ('D_raw', s['D_mag']+s['D_nonmag'])):
        np.testing.assert_allclose(s[key], expected, rtol=3e-13, atol=tolerance)


def test_crystallography_coordination_and_oxygen_potential(study):
    structure, settings, sites, _, _ = study
    atoms = structure.atoms
    assert len(atoms) == 56 and sum(atoms.numbers == 8) == 32
    assert [g.multiplicity for g in sites.groups] == [8, 16]
    distances = atoms.get_all_distances(mic=True)[:, atoms.numbers == 8]
    coordination = np.sum(distances < 2.3, axis=1)
    for group, neighbors in zip(sites.groups, (4, 6)):
        # Check ALL Fe by local coordination, not just ASE basis labels/index order.
        classified = np.flatnonzero((atoms.numbers == 26) & (coordination == neighbors))
        np.testing.assert_array_equal(classified, group.indices)
    model = elastic_model(structure, settings)
    assert len(model.beams.hkl) == 21
    assert {h*h+k*k+l*l for h, k, l in model.beams.hkl} == {0, 8, 16, 32, 40}
    parts = []
    for element in ('Fe', 'O'):
        mask = np.array(model.crystal.species) == element
        c = Crystal(model.crystal.lattice_angstrom,
            np.asarray(model.crystal.fractional_positions)[mask], tuple(np.array(model.crystal.species)[mask]))
        parts.append(IndependentAtomPotential.from_provider(c, settings.elastic_provider))
    for h in ((2, 2, 0), (4, 0, 0), (4, 4, 0), (6, 2, 0)):
        np.testing.assert_allclose(model.potential.structure_factor(h),
            sum(p.structure_factor(h) for p in parts), rtol=3e-13, atol=1e-12)
    assert abs(parts[1].structure_factor((4, 0, 0))) > 1
    assert set(model.crystal.species) == {'Fe', 'O'}
    print('Structure: 8 tetrahedral Fe, d=', distances[sites.groups[0].indices[0]].min(),
          '16 octahedral Fe, d=', distances[sites.groups[1].indices[0]].min(),
          '32 O; oxygen F400=', parts[1].structure_factor((4, 0, 0)), flush=True)


@pytest.fixture(scope='module')
def calculated(study):
    results = {}
    def result(thickness, channel, method):
        key = thickness, channel, method
        if key not in results:
            r = forward(study, method, channel, thickness)
            results[key] = r
            s = r['spectra']
            print('Magnetite', method, channel, thickness, 'nm',
                'Dmag additive A/B/total=', [float(r['groups'][g]['spectra']['D_mag'][0])*n/24
                    for g, n in (('Fe(A)', 8), ('Fe(B)', 16))]+[float(s['D_mag'][0])],
                'Dnonmag=', float(s['D_nonmag'][0]),
                'raw Ap/Bp/Am/Bm=', [float(s[k][0]) for k in RAW_KEYS], flush=True)
        return results[key]
    return result


@pytest.mark.parametrize('thickness', THICKNESSES)
@pytest.mark.parametrize('channel', CHANNELS)
@pytest.mark.parametrize('method', METHODS)
def test_results_weighting_and_signal_definitions(study, calculated, thickness, channel, method):
    r = calculated(thickness, channel, method)
    assert r['metadata']['multisite']['selected_atom_count'] == 24  # NOT all 56 atoms
    assert r['metadata']['multisite']['normalization'] == 'mean_per_selected_ionizing_atom'
    for entry in [r]+list(r['groups'].values()):
        check_signals(entry)
    for key in RAW_KEYS+('N_A', 'N_B', 'M_A', 'M_B', 'D_raw', 'D_mag', 'D_nonmag'):
        weighted = sum(n*r['groups'][g]['spectra'][key] for g, n in (('Fe(A)', 8), ('Fe(B)', 16)))
        np.testing.assert_allclose(r['spectra'][key], weighted/24, rtol=3e-13, atol=1e-17)
    for key in RAW_KEYS:
        np.testing.assert_allclose(r['weighted_sum']['spectra'][key],
            24*r['spectra'][key], rtol=3e-13, atol=1e-17)
    # Symmetric, untilted [001] geometry and transverse-isotropic tensors give
    # equal reversal-even apertures. This is a checked symmetry, not enforced.
    raw_scale = max(abs(r['spectra'][k][0]) for k in RAW_KEYS)
    assert abs(r['spectra']['D_nonmag'][0]) < 1e-10*raw_scale


@pytest.mark.parametrize('channel', CHANNELS)
@pytest.mark.parametrize('method', METHODS)
def test_global_reversal(study, calculated, channel, method):
    r, reversed_result = calculated(36., channel, method), forward(study, method, channel, 36., reverse=True)
    for entry, rev in [(r, reversed_result)]+[(r['groups'][g], reversed_result['groups'][g]) for g in r['groups']]:
        for d in ('A', 'B'):
            np.testing.assert_allclose(entry['spectra'][f'I_{d}_plus'], rev['spectra'][f'I_{d}_minus'], rtol=3e-13)
            np.testing.assert_allclose(entry['spectra']['N_'+d], rev['spectra']['N_'+d], rtol=3e-13)
            np.testing.assert_allclose(entry['spectra']['M_'+d], -rev['spectra']['M_'+d], rtol=3e-13, atol=1e-17)


def test_detector_difference_is_not_implicitly_reversal_odd(study):
    # Off-axis control deliberately removes the mirror symmetry of the main
    # comparison; no nonmagnetic background is silently relabeled magnetic.
    r = forward(study, 'bloch', 'single', 36., settings=replace(study[1], tilt=(1.5, 0.)))
    check_signals(r)
    s = r['spectra']
    assert abs(s['D_nonmag'][0]) > 1e-3*s['Sigma_ref'][0]
    print('Off-axis control D_raw/mag/nonmag=', [float(s[k][0]) for k in
          ('D_raw', 'D_mag', 'D_nonmag')], flush=True)


def test_independent_site_phases_and_single_events(study, calculated):
    structure, settings, sites, cfg, pairs = study
    elastic = elastic_model(structure, settings)
    rotation = geometry(structure, settings)[1]
    positions = structure.atoms.get_scaled_positions()
    hkl = np.asarray(elastic.beams.hkl)
    phases = [np.mean(np.exp(2j*np.pi*((hkl[:, None]-hkl[None, :])@positions[list(g.indices)].T)), axis=-1)
              for g in sites.groups]
    assert np.max(abs(phases[0]-phases[1])) > .5
    for method in METHODS:
        r = calculated(36., 'single', method)
        qx, qy = r['qx'], r['qy']
        weights = r['weights']
        support = np.logical_or.reduce([w.ravel() > 0 for w in weights.values()])
        queries = np.column_stack((qx.ravel()[support], qy.ravel()[support]))
        for g in sites.groups:
            for state, matrix in zip(('plus', 'minus'), pairs[g.group_id]):
                tensor = rotation@matrix@rotation.T
                direct = np.mean([single_site_event(elastic, r['amplitudes'], r['depth_nm'], LOSS,
                    queries, positions[i], tensor) for i in g.indices], axis=0)
                for d in ('A', 'B'):
                    expected = np.sum(direct*weights[d].ravel()[support])*(qx[0, 1]-qx[0, 0])**2
                    np.testing.assert_allclose(r['groups'][g.group_id]['spectra'][f'I_{d}_{state}'],
                                               expected, rtol=3e-12, atol=1e-17)
    # Same test tensor and incoming fields: distinguish site phases themselves,
    # without mistaking the independent A/B source amplitudes for site selectivity.
    r = calculated(36., 'single', 'bloch')
    same_tensor = rotation@pairs['Fe(A)'][0]@rotation.T
    direct = [single_site_event(elastic, r['amplitudes'], r['depth_nm'], LOSS, np.array(cfg.centers),
        positions[g.indices[0]], same_tensor) for g in sites.groups]
    assert np.linalg.norm(direct[0]-direct[1])/np.linalg.norm(direct[0]) > 1e-3


def test_bounded_numerical_controls(study, calculated):
    for channel in CHANNELS:
        bw, ms = (calculated(36., channel, method) for method in METHODS)
        # The FFT backend supports an explicit TWO-beam projection, not an
        # arbitrary 21-beam projection. Use that supported real-spinel control
        # only for convention consistency, never as the literature benchmark.
        matched_settings = replace(study[1], basis_mode='two-beam')
        matched_bw = forward(study, 'bloch', channel, 36., settings=matched_settings)
        matched = forward(study, 'fft-multislice', channel, 36., settings=matched_settings)
        refined = forward(study, 'fft-multislice', channel, 36., settings=matched_settings,
                          cfg=replace(study[3], slice_step=.05))
        matched_gap = gaps(matched, matched_bw)
        refined_gap = gaps(refined, matched_bw)
        print('36nm', channel, 'production FFT/BW gap', gaps(ms, bw),
              'matched TWO-beam FFT/BW coarse/fine gap', matched_gap, refined_gap, flush=True)
        # Same finite propagation space and depth nodes: halve the actual
        # Strang step and require convergence, not an arbitrary BW/MS equality.
        for kind in ('raw', 'odd'):
            assert refined_gap[kind] < max(matched_gap[kind]/3, 1e-11)
    base_bw, base_ms = (calculated(36., 'double', m) for m in METHODS)
    fine_cfg = replace(study[3], depth=257)
    for method, base in zip(METHODS, (base_bw, base_ms)):
        fine = forward(study, method, 'double', 36., cfg=fine_cfg)
        print('36nm double depth129->257', method, gaps(fine, base), flush=True)
    half_step = forward(study, 'fft-multislice', 'double', 36., cfg=replace(study[3], slice_step=.05))
    larger_bw = forward(study, 'bloch', 'double', 36., settings=replace(study[1], beam_cutoff=.96))
    print('36nm double MS slice .10->.05', gaps(half_step, base_ms),
          'BW beams21->', len(larger_bw['metadata']['beam_hkl']), gaps(larger_bw, base_bw),
          'MS incoming excluded', base_ms['metadata']['fft']['max_excluded_population'], flush=True)


def test_one_detector_quadrature_refinement(study, calculated):
    # Baseline dq=.045 A^-1 is larger than the aperture diameter .036 A^-1.
    # One refinement is necessary to gauge this quadrature limitation; it is
    # not an angular convergence certification or a full-map calculation.
    base = calculated(36., 'double', 'bloch')
    finer = forward(study, 'bloch', 'double', 36., cfg=replace(study[3], grid=33))
    for entry in [finer]+list(finer['groups'].values()):
        check_signals(entry)
    print('36nm BW double detector grid17->33', gaps(finer, base),
          'Dmag base/refined=', float(base['spectra']['D_mag'][0]),
          float(finer['spectra']['D_mag'][0]), flush=True)
