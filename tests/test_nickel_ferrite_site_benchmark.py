"""Patch 5C: ordered inverse-spinel NiFe2O4; synthetic MDFFs, not spectroscopy.

Reference: Wang et al., Nat. Commun. 4, 1395 (2013), doi:10.1038/ncomms2323,
Fig. 2: [110] reference zone, distinct 004 and (-2,2,0) systematic rows,
300 kV, 29 nm, opposite Fe but unchanged Ni experimental edge-sign patterns.

Parent spinel: Fd-3m choice 2, a=8.34 A, u=.255 (representative, not a
refinement of the specimen). Explicit ordered B realization: Ni at x=0,1/2,
Fe at x=1/4,3/4. This is NOT a unique B order or the random/disordered cubic
average. No half-occupied sites, virtual-crystal factors or inferred valences.
The full Fe/Ni/O potential is retained before the systematic-row projection.

Two real off-zone incident directions: microscope tilt (0,50) mrad in the
right-handed frames x=selected row, z=[110]. M is fixed crystal [110] (about
2.87 degrees from the tilted beam); it is not silently rotated between cases.
Detectors are fixed by the same rule (g/2,+/-g/2). The reported ~4 mrad
collection angle is treated as a semi-angle here; exact aperture/tilt matching
to the experiment is not established. Baseline 000,+/-g is a three-beam
truncation; MS elastic fields retain higher row harmonics. No HOLZ, discrete
ionization layers, multiplets, calibrated cross-element strengths or moments.
"""
from dataclasses import replace
import json
from pathlib import Path

import numpy as np
import pytest
from ase.spacegroup import crystal

from emcd_sim.crystal import Crystal
from emcd_sim.geometry import electron_wavelength_angstrom
from emcd_sim.gui import forward_pipeline
from emcd_sim.gui.forward_pipeline import calculate_multisite
from emcd_sim.gui.generalized_forward import settings_for_source
from emcd_sim.gui.geometry import Structure, Settings, elastic_model, geometry, excitation
from emcd_sim.gui.multisite_results import spectral_series, covered_segments
from emcd_sim.mdff_providers import load_site_group_provider
from emcd_sim.multisite import IonizationSiteGroup, MultiSiteIonization
from emcd_sim.multisite_spectrum import ModeledEdgeWindow
from emcd_sim.scattering import IndependentAtomPotential
from single_element_helpers import document
from test_multisite_forward import configuration, RAW_KEYS
from test_multisite_scientific_validation import encoded
from test_magnetite_site_benchmark import check_signals


ROWS = {'004': (0, 0, 4), '2bar20': (-2, 2, 0)}
FE = np.array([704., 708., 711.5, 715., 720., 724.5, 730.])
NI = np.array([846., 851., 855., 860., 867., 872., 880.])
L3 = [711.5, 855.]
METHODS = ('bloch', 'fft-multislice')


@pytest.fixture(scope='module')
def study(tmp_path_factory):
    directory = tmp_path_factory.mktemp('nickel-ferrite')
    atoms = crystal(['Fe', 'Fe', 'O'], basis=[(.125,)*3, (.5,)*3, (.255,)*3],
                    spacegroup=227, setting=2, cellpar=[8.34]*3+[90]*3)
    positions = atoms.get_scaled_positions()
    kinds = atoms.arrays['spacegroup_kinds']
    b = np.flatnonzero(kinds == 1)
    nickel = b[np.rint(4*positions[b, 0]).astype(int) % 2 == 0]
    for i in nickel:
        atoms[i].symbol = 'Ni'
    atoms.info.pop('spacegroup', None)  # chemical ordering reduces parent symmetry
    atoms.info.update(parent_spacegroup='Fd-3m choice 2',
        B_site_order='Ni x=0,1/2; Fe x=1/4,3/4; explicit ordered approximation')
    structure = Structure(atoms, source='Ordered inverse-spinel NiFe2O4, a=8.34 A, u=.255')
    indices = {'Fe(A)': tuple(np.flatnonzero(kinds == 0).tolist()),
               'Fe(B)': tuple(i for i in b.tolist() if i not in nickel),
               'Ni(B)': tuple(nickel.tolist())}
    axis = np.array([1., 1., 0.])/np.sqrt(2)
    frame = np.column_stack(([0., 0., 1.], np.cross(axis, [0., 0., 1.]), axis))
    groups, declarations = [], {}
    for gid, element, sign, scale, energy in (
        ('Fe(A)', 'Fe', -1, 1., FE), ('Fe(B)', 'Fe', 1, 1.25, FE), ('Ni(B)', 'Ni', 1, .65, NI)):
        e3, e2 = (711.5, 724.5) if element == 'Fe' else (855., 872.)
        n = np.exp(-((energy-e3)/2.5)**2)+.65*np.exp(-((energy-e2)/2.5)**2)+.03
        m = .12*(np.exp(-((energy-e3)/2.5)**2)-.65*np.exp(-((energy-e2)/2.5)**2))
        even = scale*n[:, None, None]*np.diag([1.2, 1.2, .8])
        odd = np.zeros_like(even, dtype=complex)
        odd[:, 0, 1] = 1j*sign*scale*m
        odd[:, 1, 0] = -1j*sign*scale*m
        plus, minus = even+odd, even-odd
        assert np.linalg.eigvalsh(plus).min() > 0 and np.linalg.eigvalsh(minus).min() > 0
        data = document(element)
        data.update(energy_ev=energy.tolist(), selected_ev={'L3': e3, 'L2': e2},
            basis='declared_local', frame_to_crystal=frame.tolist(),
            magnetization_crystal=(sign*axis).tolist(), T_plus=encoded(plus), T_minus=encoded(minus),
            T_even=encoded(even), source='Original synthetic '+gid+' tensor pair; scale='+str(scale),
            validity='SOFTWARE BENCHMARK ONLY; uncalibrated independent relative Fe/Ni amplitudes')
        path = directory/(gid+'.json')
        path.write_text(json.dumps(data), encoding='utf-8')
        cfg = settings_for_source(path)
        groups.append(IonizationSiteGroup(gid, element, indices[gid], cfg, tuple(sign*axis), 8))
        declarations[gid] = data
    sites = MultiSiteIonization(structure, groups)
    return structure, sites, declarations


def controls(row, *, larger=False):
    target = ROWS[row]
    g = np.linalg.norm(target)/8.34
    settings = Settings(zone=(1, 1, 0), target=target, tilt=(0., 50.), voltage=300.,
        thickness=29., beam_cutoff=(2.1 if larger else 1.5)*g, potential_cutoff=1.5,
        elastic_provider='adaptive-dirac-pade-2026')
    radius = .004/electron_wavelength_angstrom(300.)
    cfg = configuration(channeling_model='double', systematic_row=True, angular_maps=False,
        grid=25, halfwidth=.60, centers=((g/2, g/2), (g/2, -g/2)), radius=radius,
        subpixels=16, depth=129, fft_grid=32, slice_step=.10)
    return settings, cfg


def windows(samples=None, selected=None):
    return {gid: ModeledEdgeWindow((float(e[0]), float(e[-1])), tuple(e) if samples is None else None)
            for gid, e in (('Fe(A)', FE), ('Fe(B)', FE), ('Ni(B)', NI))
            if selected is None or gid in selected}


def run(study, row, method, *, samples=None, reverse=False, selected=None,
        settings=None, cfg=None, sites=None):
    structure, original_sites, _ = study
    base_settings, base_cfg = controls(row)
    return calculate_multisite(structure, settings or base_settings, sites or original_sites,
        replace(cfg or base_cfg, propagation=method), energy_ev=samples,
        energy_windows=windows(samples, selected), reverse_magnetization=reverse)


def relative_gap(actual, reference):
    def array(r, keys):
        return np.concatenate([entry['spectra'][k] for entry in [r]+list(r['groups'].values()) for k in keys])
    return {label: float(np.linalg.norm(array(actual, keys)-array(reference, keys))/
                         max(np.linalg.norm(array(reference, keys)), 1e-30))
            for label, keys in (('raw', RAW_KEYS), ('odd', ('M_A', 'M_B')))}


@pytest.fixture(scope='module')
def calculated(study):
    results = {}
    def get(row, method):
        if (row, method) not in results:
            r = run(study, row, method)
            results[row, method] = r
            s = r['spectra']
            numbers = []
            for gid, energy in (('Fe(A)', L3[0]), ('Fe(B)', L3[0]), ('Ni(B)', L3[1])):
                ie = np.flatnonzero(s['energy_ev'] == energy)[0]
                numbers.append(float(r['groups'][gid]['spectra']['D_mag'][ie])/3)
            print('NFO', row, method, 'L3 additive FeA/FeB/NiB=', numbers,
                  'Fe/Ni totals=', [numbers[0]+numbers[1], numbers[2]],
                  'max Dnonmag=', float(np.max(abs(s['D_nonmag']))), flush=True)
        return results[row, method]
    return get


def test_inverse_spinel_chemistry_coordination_and_plane_populations(study):
    structure, sites, _ = study
    atoms = structure.atoms
    assert len(atoms) == 56 and sum(atoms.numbers == 8) == 32
    d = atoms.get_all_distances(mic=True)[:, atoms.numbers == 8]
    n = np.sum(d < 2.3, axis=1)
    for group, count in zip(sites.groups, (4, 6, 6)):
        assert group.multiplicity == 8 and len(group.indices) == 8
        assert all(atoms[i].symbol == group.element for i in group.indices)
        assert np.all(n[list(group.indices)] == count)
    assert set(np.flatnonzero((atoms.numbers == 26) & (n == 4))) == set(sites.groups[0].indices)
    assert set(np.flatnonzero((atoms.numbers == 26) & (n == 6))) == set(sites.groups[1].indices)
    assert set(np.flatnonzero(atoms.numbers == 28)) == set(sites.groups[2].indices)
    p = atoms.get_scaled_positions()
    # 004 row: alternating tetrahedral and octahedral planes normal to 008.
    layers004 = np.rint(8*p[:, 2]).astype(int) % 2
    assert np.all(layers004[list(sites.groups[0].indices)] == 1)
    for group in sites.groups[1:]:
        assert np.all(layers004[list(group.indices)] == 0)
    # (-2,2,0) row: all A and half B on one family; remaining B on the other.
    layers220 = np.rint(4*(p[:, 1]-p[:, 0])).astype(int) % 2
    assert np.all(layers220[list(sites.groups[0].indices)] == 0)
    assert sum(layers220[list(sites.groups[1].indices+sites.groups[2].indices)] == 0) == 8
    settings, _ = controls('004')
    elastic = elastic_model(structure, settings, systematic_row=True)
    c = elastic.crystal
    oxygen = np.array(c.species) == 'O'
    op = IndependentAtomPotential.from_provider(Crystal(c.lattice_angstrom,
        np.asarray(c.fractional_positions)[oxygen], tuple(np.array(c.species)[oxygen])), settings.elastic_provider)
    assert abs(op.structure_factor((0, 0, 4))) > 1
    assert set(c.species) == {'Fe', 'Ni', 'O'}
    print('NFO structure: 8 Fe(A), 8 Fe(B), 8 Ni(B), 32 O; nearest O distances=',
          [float(d[g.indices[0]].min()) for g in sites.groups], flush=True)


def test_distinct_incident_directions_and_three_beam_excitation(study):
    incident = []
    for row in ROWS:
        settings, cfg = controls(row)
        c, rotation, hkl, gxy, _ = geometry(study[0], settings, systematic_row=True)
        assert set(hkl) == {(0, 0, 0), ROWS[row], tuple(-x for x in ROWS[row])}
        s = excitation(gxy, settings.tilt, settings.voltage)
        assert s[0] == 0 and np.all(s[1:] > 0)
        np.testing.assert_allclose(s[1], s[2], rtol=1e-12)
        direction = rotation.T@np.array([0., .05, np.sqrt(1-.05**2)])
        incident.append(direction)
        print('NFO geometry', row, 'hkl=', hkl, 'incident crystal=', direction.tolist(),
              'excitation A^-1=', s.tolist(), 'detectors=', cfg.centers,
              'radius A^-1=', cfg.radius, flush=True)
    assert np.linalg.norm(incident[0]-incident[1]) > .05


@pytest.mark.parametrize('row', ROWS)
@pytest.mark.parametrize('method', METHODS)
def test_independent_channels_fixed_normalization_and_element_sums(study, calculated, row, method):
    r = calculated(row, method)
    s, meta = r['spectra'], r['metadata']['multisite']
    np.testing.assert_array_equal(s['energy_ev'], np.r_[FE, NI])
    assert meta['selected_atom_count'] == 24 and meta['spectrum_kind'] == 'modeled_partial_core_edge_spectrum'
    for entry in [r]+list(r['groups'].values()):
        check_signals(entry)
    for ie, energy in enumerate(s['energy_ev']):
        expected = ['Fe(A)', 'Fe(B)'] if energy < 800 else ['Ni(B)']
        assert meta['active_channels_by_energy'][ie] == expected
    for gid, group in r['groups'].items():
        coverage = group['metadata']['coverage']
        mask = np.asarray(coverage['active_energy_mask'])
        assert coverage['amplitude_multiplier'] == 1.
        assert set(np.asarray(coverage['status_at_energy'])[~mask]) == {'outside_modeled_window'}
        for key in RAW_KEYS:
            np.testing.assert_array_equal(group['spectra'][key][~mask], 0.)  # labeled exclusion ONLY
    roundoff = 8*np.finfo(float).eps*max(np.max(abs(s[k])) for k in RAW_KEYS)
    for key in RAW_KEYS+('M_A', 'M_B', 'D_raw', 'D_mag', 'D_nonmag'):
        expected = sum(g['spectra'][key]/3 for g in r['groups'].values())
        np.testing.assert_allclose(s[key], expected, rtol=3e-13, atol=roundoff)
    assert np.max(abs(s['D_nonmag'])) < 1e-10*np.max(s['Sigma_ref'])
    for element, gids, per_atom_factor in (('Fe', ('Fe(A)', 'Fe(B)'), 2/3), ('Ni', ('Ni(B)',), 1/3)):
        series = spectral_series(r, ('element', element))[0]
        for key in RAW_KEYS:
            mean = sum(r['groups'][gid]['spectra'][key] for gid in gids)/len(gids)
            np.testing.assert_allclose(series['spectra'][key], per_atom_factor*mean, rtol=3e-13, atol=1e-16)
    assert len(covered_segments(r, s['energy_ev'])) == 2
    for group in study[1].groups:
        source = load_site_group_provider(group)
        tensors = source.tensors(source.energy_ev, np.eye(3), group.magnetization)
        data = study[2][group.group_id]
        t = np.array(data['T_plus']['real'])+1j*np.array(data['T_plus']['imag'])
        frame = np.array(data['frame_to_crystal'])
        np.testing.assert_allclose(tensors[0].tensor_angstrom2_per_ev,
            np.einsum('ia,eab,jb->eij', frame, t, frame), rtol=3e-13, atol=1e-16)


@pytest.mark.parametrize('row', ROWS)
@pytest.mark.parametrize('method', METHODS)
def test_all_three_sublattices_reverse_together(study, calculated, row, method):
    base = calculated(row, method)
    rev = run(study, row, method, samples=L3, reverse=True)
    indices = [int(np.flatnonzero(base['spectra']['energy_ev'] == e)[0]) for e in L3]
    for a, b in [(base, rev)]+[(base['groups'][gid], rev['groups'][gid]) for gid in base['groups']]:
        for detector in ('A', 'B'):
            np.testing.assert_allclose(a['spectra'][f'I_{detector}_plus'][indices],
                b['spectra'][f'I_{detector}_minus'], rtol=3e-13, atol=1e-16)
            np.testing.assert_allclose(a['spectra']['M_'+detector][indices],
                -b['spectra']['M_'+detector], rtol=3e-13, atol=1e-16)
            np.testing.assert_allclose(a['spectra']['N_'+detector][indices],
                b['spectra']['N_'+detector], rtol=3e-13, atol=1e-16)


def test_omission_amplitudes_and_detector_asymmetry(study, calculated, tmp_path):
    base = calculated('004', 'bloch')
    base_indices = [int(np.flatnonzero(base['spectra']['energy_ev'] == e)[0]) for e in L3]
    fe_only = run(study, '004', 'bloch', samples=[L3[0]], selected=('Fe(A)', 'Fe(B)'))
    assert fe_only['metadata']['multisite']['selected_atom_count'] == 24
    assert fe_only['metadata']['multisite']['omitted_site_groups'] == ['Ni(B)']
    assert fe_only['groups']['Ni(B)']['metadata']['coverage']['status_at_energy'] == ['omitted_by_request']
    for key in RAW_KEYS:
        np.testing.assert_allclose(fe_only['spectra'][key], base['spectra'][key][base_indices[:1]], rtol=3e-13)
    data = json.loads(json.dumps(study[2]['Ni(B)']))
    for key in ('T_plus', 'T_minus', 'T_even'):
        for part in ('real', 'imag'):
            data[key][part] = (2*np.asarray(data[key][part])).tolist()
    path = tmp_path/'double-ni.json'
    path.write_text(json.dumps(data), encoding='utf-8')
    groups = list(study[1].groups)
    groups[2] = replace(groups[2], mdff_reference=settings_for_source(path))
    scaled = run(study, '004', 'bloch', samples=L3, sites=MultiSiteIonization(study[0], groups))
    for key in RAW_KEYS:
        np.testing.assert_allclose(scaled['spectra'][key], base['spectra'][key][base_indices]*[1, 2], rtol=3e-13)
    settings, cfg = controls('004')
    # In a strict row potential, an in-row tilt still preserves y reflection.
    # Break the aperture mirror symmetry in THIS control only; the published
    # sign comparison always uses the original symmetric detector rule.
    asymmetric_cfg = replace(cfg, centers=(cfg.centers[0],
        (cfg.centers[1][0]+.05, cfg.centers[1][1])))
    asymmetric = run(study, '004', 'bloch', samples=L3, settings=settings, cfg=asymmetric_cfg)
    check_signals(asymmetric)
    assert np.max(abs(asymmetric['spectra']['D_nonmag'])) > 1e-6*np.max(asymmetric['spectra']['Sigma_ref'])
    print('NFO asymmetric D_raw/mag/nonmag=', {k: asymmetric['spectra'][k].tolist()
          for k in ('D_raw', 'D_mag', 'D_nonmag')}, flush=True)


def test_missing_required_coverage_is_not_a_zero(study, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('Elastic preparation must not precede coverage validation')
    monkeypatch.setattr(forward_pipeline, 'elastic_model', forbidden)
    bad = windows()
    bad['Ni(B)'] = ModeledEdgeWindow((840., 880.), tuple(NI))
    settings, cfg = controls('004')
    with pytest.raises(ValueError, match='Missing MDFF coverage'):
        calculate_multisite(study[0], settings, study[1], cfg, energy_windows=bad)


def test_one_beam_basis_control_and_supported_matched_solvers(study, calculated):
    settings, cfg = controls('004')
    base = run(study, '004', 'bloch', samples=L3)
    larger = run(study, '004', 'bloch', samples=L3, settings=controls('004', larger=True)[0])
    assert len(base['metadata']['beam_hkl']) == 3 and len(larger['metadata']['beam_hkl']) == 5
    print('NFO 004 BW beams3->5', relative_gap(larger, base),
          'refined total Fe/Ni L3=', larger['spectra']['D_mag'].tolist(), flush=True)
    # Existing FFT projection supports exactly two retained beams. This small
    # control checks conventions, NOT convergence of the three-beam benchmark.
    settings = replace(settings, basis_mode='two-beam')
    cfg = replace(cfg, systematic_row=False)
    bw = run(study, '004', 'bloch', samples=L3, settings=settings, cfg=cfg)
    ms = run(study, '004', 'fft-multislice', samples=L3, settings=settings, cfg=cfg)
    # At 29 nm/128 intervals, max step .10 gives 3 substeps. Max .04 gives
    # 6, halving the ACTUAL step (.07552 -> .03776 nm) for the Strang control.
    fine = run(study, '004', 'fft-multislice', samples=L3, settings=settings, cfg=replace(cfg, slice_step=.04))
    coarse_gap, fine_gap = relative_gap(ms, bw), relative_gap(fine, bw)
    print('NFO matched TWO-beam BW/MS coarse/fine', coarse_gap, fine_gap, flush=True)
    for key in ('raw', 'odd'):
        assert fine_gap[key] < max(coarse_gap[key]/3, 1e-11)
    for row in ROWS:
        print('NFO production BW/MS', row, relative_gap(calculated(row, 'fft-multislice'),
              calculated(row, 'bloch')), flush=True)


def test_element_spectral_comparison_plot(study, calculated):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 7.8), sharey='col')
    for row_index, row in enumerate(ROWS):
        for method, style in (('bloch', '-o'), ('fft-multislice', '--s')):
            result = calculated(row, method)
            method_label = 'BW' if method == 'bloch' else 'MS'
            for col, element in enumerate(('Fe', 'Ni')):
                total = spectral_series(result, ('element', element))[0]
                segments = covered_segments(result, result['spectra']['energy_ev'], total['groups'])
                for mask in segments:
                    energy = result['spectra']['energy_ev'][mask]
                    if element == 'Fe':
                        for gid, color in (('Fe(A)', 'tab:blue'), ('Fe(B)', 'tab:orange')):
                            axes[row_index, col].plot(energy, result['groups'][gid]['spectra']['D_mag'][mask]/3,
                                style, color=color, label=gid+' '+method_label, ms=3)
                    axes[row_index, col].plot(energy, total['spectra']['D_mag'][mask], style,
                        color='black' if element == 'Fe' else 'tab:purple', label=element+' total '+method_label, ms=3)
                axes[row_index, col].set_title(row+' systematic row: '+element+' L2,3')
                axes[row_index, col].set_xlabel('Energy loss (eV); calculated samples marked')
                axes[row_index, col].set_ylabel('Additive magnetic A-B\n(relative units / selected ionizing atom)')
                axes[row_index, col].axhline(0, color='grey', lw=.7)
                axes[row_index, col].grid(alpha=.2)
                axes[row_index, col].ticklabel_format(axis='y', style='sci', scilimits=(0, 0))
                axes[row_index, col].legend(fontsize=7, ncol=2 if element == 'Fe' else 1)
    fig.suptitle('Ordered inverse-spinel NiFe2O4, 300 kV, 29 nm; SYNTHETIC tensors\n'
                 'Fixed denominator 24; Fe/Ni amplitude scales uncalibrated; finite systematic-row models', fontsize=12)
    fig.text(.5, .015, 'Shared scales within each element. Synthetic spectra; quantitative convergence and experimental agreement remain unvalidated.',
             ha='center', fontsize=8)
    fig.tight_layout(rect=(0, .045, 1, .92))
    output = Path(__file__).resolve().parents[1]/'outputs/nickel_ferrite_site_validation'
    output.mkdir(parents=True, exist_ok=True)
    fig.savefig(output/'element_spectra.png', dpi=160)
    plt.close(fig)
