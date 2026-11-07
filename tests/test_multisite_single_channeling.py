"""Synthetic numerical checks, not predictions of material-specific spectra."""
from dataclasses import replace
import json

import numpy as np
import pytest
from ase import Atoms
from ase.build import bulk

from emcd_sim.crystal import Crystal
from emcd_sim.elastic import BeamSet, depth_coherence
from emcd_sim.geometry import Microscope, VirtualDetector, characteristic_qz_angstrom_inv
from emcd_sim.gui.generalized_forward import settings_for_source
from emcd_sim.ionization_sites import IonizationSites
from emcd_sim.mdff_providers import load_provider
from emcd_sim.multisite import IonizationSiteGroup, MultiSiteIonization
from emcd_sim.multisite_single_channeling import run_multisite_with_coherence
from emcd_sim.physical_elastic import PhysicalElasticModel
from emcd_sim.scattering import IndependentAtomPotential
from emcd_sim.simulation import EMCDSimulation
from emcd_sim.single_channeling_tensor import _tensor_angular_maps, run_tensor_with_coherence
from single_element_helpers import document


ENERGY = np.array([710., 723.])
QX = np.array([.13, -.22, .31])
QY = np.array([.17, .19, -.23])
IDENTITY = np.eye(3)


def source(tmp_path, name='source', element='Ni', scale=1., axis=(0, 0, 1),
           frame=None, real_odd=False, reverse=False, nonmagnetic=False):
    d = document(element, nonmagnetic=nonmagnetic)
    if element == 'O':
        d.update(edge='K', selected_ev=dict(K=710.))
    d['magnetization_crystal'] = list(axis)
    if frame is not None:
        d.update(basis='declared_local', frame_to_crystal=np.asarray(frame).tolist())
    if real_odd:
        even = np.asarray(d['T_even']['real'])
        odd = .1 * even
        for key, array in [('T_plus', even + odd), ('T_minus', even - odd)]:
            d[key] = dict(real=array.tolist(), imag=np.zeros_like(array).tolist())
    if reverse:
        d['T_plus'], d['T_minus'] = d['T_minus'], d['T_plus']
    for key in ('T', 'T_plus', 'T_minus', 'T_even'):
        if key in d:
            for part in ('real', 'imag'):
                d[key][part] = (scale * np.asarray(d[key][part])).tolist()
    path = tmp_path / (name + '.json')
    path.write_text(json.dumps(d), encoding='utf-8')
    return settings_for_source(path)


def group(name, element, indices, cfg):
    return IonizationSiteGroup(name, element, indices, cfg, cfg.magnetization, len(indices))


def model_for(atoms, hkl=((0, 0, 0), (1, 0, 0)), rotation=IDENTITY):
    crystal = Crystal(atoms.cell.array @ rotation.T, atoms.get_scaled_positions(),
                      tuple(atoms.get_chemical_symbols()))
    potential = IndependentAtomPotential.from_provider(crystal, 'auto')
    elastic = PhysicalElasticModel(crystal, Microscope(200), BeamSet(hkl), potential)
    return EMCDSimulation(elastic, dict(A=VirtualDetector((.2, .2), .2),
                                      B=VirtualDetector((.2, -.2), .2)))


def generic_atoms(symbols='Ni3'):
    return Atoms(symbols, scaled_positions=[(i * .23, i * .19, i * .11)
                                           for i in range(len(Atoms(symbols)))],
                 cell=[4, 4, 4], pbc=True)


def coherence_for(model):
    # Non-unit trace deliberately represents retained incoming-beam population.
    a = np.array([.6, .3 + .2j])
    assert len(model.elastic.beams.hkl) == len(a)
    return np.outer(a, a.conj())


def run(model, sites, coherence=None, **kwargs):
    return run_multisite_with_coherence(model, sites,
        coherence_for(model) if coherence is None else coherence,
        kwargs.pop('energy_ev', ENERGY), kwargs.pop('qx', QX), kwargs.pop('qy', QY),
        crystal_to_microscope=kwargs.pop('rotation', IDENTITY), thickness_nm=.7, **kwargs)


def event_reference(model, amplitudes, position, tensor, loss):
    """Direct coherent elastic-path amplitude for ONE localized event."""
    g = model.elastic.reciprocal_vectors_xy
    q = np.empty((len(QX), len(g), 3))
    q[..., 0] = QX[:, None] - g[:, 0]
    q[..., 1] = QY[:, None] - g[:, 1]
    q[..., 2] = -characteristic_qz_angstrom_inv(loss, 200.)
    angular_q = 2 * np.pi * q
    kernel = angular_q / np.sum(angular_q**2, axis=-1)[..., None]
    phase = np.exp(2j * np.pi * (np.asarray(model.elastic.beams.hkl) @ position))
    v = np.einsum('g,g,pga->pa', amplitudes, phase, kernel)
    return .7 * np.einsum('pa,ba,pb->p', v, tensor, v.conj()).real, v


def test_ni_matches_existing_single_channeling(tmp_path):
    atoms = bulk('Ni', 'fcc', a=3.524, cubic=True)
    model = model_for(atoms, ((0, 0, 0), (2, 0, 0)))
    cfg = source(tmp_path)
    sites = MultiSiteIonization(atoms, [group('Ni', 'Ni', (0, 1, 2, 3), cfg)])
    c = depth_coherence(model.elastic, .7, steps=9)
    result = run(model, sites, c)
    legacy = IonizationSites.from_structure(type('Structure', (), dict(atoms=atoms))(), 'Ni')
    tensors = load_provider(cfg).tensors(ENERGY, IDENTITY, cfg.magnetization)
    for state, tensor in zip(('plus', 'minus'), tensors):
        for ie, loss in enumerate(ENERGY):
            parts = _tensor_angular_maps(model, tensor.tensor_angstrom2_per_ev[ie], loss,
                                        c, legacy.single_phase(model.elastic.crystal, model.elastic.beams.hkl), QX, QY)
            np.testing.assert_allclose(result['total'][state][ie], .7 * sum(parts), rtol=1e-13)
        q = np.linspace(-.7, .7, 9)
        qx, qy = np.meshgrid(q, q)
        grid_result = run(model, sites, c, qx=qx, qy=qy)
        old = run_tensor_with_coherence(model, tensor, c, thickness_nm=.7, grid_size=9,
                                       map_halfwidth_q=.7, reference_energy_ev=710.)
        for name in ('A', 'B'):
            integrated = np.sum(grid_result['total'][state] * old.detector_weights[name], axis=(1, 2)) * (q[1] - q[0])**2
            np.testing.assert_allclose(integrated, old.detector_spectra[name], rtol=1e-13)


def test_splitting_weighting_and_amplitude_preservation(tmp_path):
    atoms = generic_atoms()
    model = model_for(atoms)
    cfg = source(tmp_path)
    merged = run(model, MultiSiteIonization(atoms, [group('all', 'Ni', (0, 1, 2), cfg)]))
    split = run(model, MultiSiteIonization(atoms, [group('a', 'Ni', (0,), cfg),
                                                group('b', 'Ni', (1, 2), cfg)]))
    for state in ('plus', 'minus'):
        expected = (split['groups']['a'][state] + 2 * split['groups']['b'][state]) / 3
        np.testing.assert_allclose(split['total'][state], expected, rtol=1e-13)
        np.testing.assert_allclose(split['total'][state], merged['total'][state], rtol=1e-13)
        np.testing.assert_allclose(split['weighted_sum'][state], 3 * expected)
    stronger = source(tmp_path, 'stronger', scale=7.)
    scaled = run(model, MultiSiteIonization(atoms, [group('a', 'Ni', (0,), cfg),
                                                 group('b', 'Ni', (1, 2), stronger)]))
    np.testing.assert_allclose(scaled['groups']['b']['plus'], 7 * split['groups']['b']['plus'])
    assert scaled['groups']['b']['source']['sha256'] == stronger.source_sha256
    assert scaled['metadata']['selected_atom_count'] == 3


def test_phase_interference_is_coherent_within_each_event_only(tmp_path):
    atoms = generic_atoms('Ni2')
    model = model_for(atoms)
    cfg = source(tmp_path)
    sites = MultiSiteIonization(atoms, [group('a', 'Ni', (0,), cfg), group('b', 'Ni', (1,), cfg)])
    result = run(model, sites)
    a = np.array([.6, .3 + .2j])
    tensor = load_provider(cfg).tensors(ENERGY, IDENTITY, cfg.magnetization)[0].tensor_angstrom2_per_ev[0]
    refs = [event_reference(model, a, p, tensor, ENERGY[0]) for p in atoms.get_scaled_positions()]
    for name, (intensity, _) in zip(('a', 'b'), refs):
        np.testing.assert_allclose(result['groups'][name]['plus'][0], intensity, rtol=1e-13)
    assert not np.allclose(refs[0][0], refs[1][0])
    v = refs[0][1] + refs[1][1]
    wrong = .7 / 2 * np.einsum('pa,ba,pb->p', v, tensor, v.conj()).real
    assert not np.allclose(result['total']['plus'][0], wrong)
    diagonal = run(model, sites, np.diag(np.diag(coherence_for(model))))
    assert not np.allclose(result['total']['plus'], diagonal['total']['plus'])
    half = run(model, sites, .5 * coherence_for(model))
    np.testing.assert_allclose(half['total']['plus'], .5 * result['total']['plus'])


@pytest.mark.parametrize('second_scale', [1., 2.])
def test_afm_ferrimagnetic_global_reversal(tmp_path, second_scale):
    atoms = bulk('Cr', 'bcc', a=2.88, cubic=True)
    model = model_for(atoms, ((0, 0, 0), (1, 1, 0)))
    up = source(tmp_path, 'up', 'Cr')
    down = source(tmp_path, 'down', 'Cr', axis=(0, 0, -1), reverse=True, scale=second_scale)
    sites = MultiSiteIonization(atoms, [group('up', 'Cr', (0,), up), group('down', 'Cr', (1,), down)])
    result, reversed_result = run(model, sites), run(model, sites, reverse_magnetization=True)
    for name in ('up', 'down'):
        np.testing.assert_allclose(reversed_result['groups'][name]['plus'], result['groups'][name]['minus'])
    np.testing.assert_allclose(reversed_result['total']['plus'], result['total']['minus'])
    np.testing.assert_allclose(reversed_result['total']['even'], result['total']['even'])
    np.testing.assert_allclose(reversed_result['total']['odd'], -result['total']['odd'])
    if second_scale == 1:
        np.testing.assert_allclose(result['total']['odd'], 0, atol=1e-16)
    else:
        assert np.max(abs(result['total']['odd'])) > 1e-8


def test_noncollinear_local_and_microscope_frames(tmp_path):
    atoms = generic_atoms('FeNi')
    angle = .37
    r = np.array([[np.cos(angle), -np.sin(angle), 0], [np.sin(angle), np.cos(angle), 0], [0, 0, 1]])
    f = np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]])
    model = model_for(atoms, rotation=r)
    configs = [source(tmp_path, 'Fe', 'Fe'), source(tmp_path, 'Ni', axis=(1, 0, 0), frame=f)]
    sites = MultiSiteIonization(atoms, [group('Fe', 'Fe', (0,), configs[0]), group('Ni', 'Ni', (1,), configs[1])])
    result = run(model, sites, rotation=r)
    for i, (cfg, frame) in enumerate(zip(configs, (IDENTITY, f))):
        d = json.loads(open(cfg.source, encoding='utf-8').read())
        j = d['energy_ev'].index(710.)
        for state in ('plus', 'minus'):
            encoded = d['T_' + state]
            local = np.asarray(encoded['real'])[j] + 1j * np.asarray(encoded['imag'])[j]
            tensor = r @ frame @ local @ frame.T @ r.T
            expected, _ = event_reference(model, np.array([.6, .3 + .2j]), atoms.get_scaled_positions()[i], tensor, 710.)
            np.testing.assert_allclose(result['groups'][('Fe', 'Ni')[i]][state][0], expected, rtol=1e-13)


def test_real_tensor_reversal_odd_and_nonmagnetic_source(tmp_path):
    atoms = generic_atoms('NiO')
    model = model_for(atoms)
    cfg = source(tmp_path, real_odd=True)
    oxygen = source(tmp_path, 'oxygen', 'O', nonmagnetic=True)
    result = run(model, MultiSiteIonization(atoms, [group('Ni', 'Ni', (0,), cfg), group('O', 'O', (1,), oxygen)]))
    assert np.max(abs(result['total']['odd'])) > 1e-8
    np.testing.assert_array_equal(result['groups']['O']['plus'], result['groups']['O']['minus'])
    np.testing.assert_allclose(result['total']['odd'], (result['total']['plus'] - result['total']['minus']) / 2)


def test_replication_with_matched_physical_support(tmp_path):
    atoms = bulk('Ni', 'fcc', a=3.524, cubic=True)
    repeated = atoms.repeat((2, 1, 1))
    cfg = source(tmp_path)
    models = [model_for(atoms, ((0, 0, 0), (2, 0, 0))),
              model_for(repeated, ((0, 0, 0), (4, 0, 0)))]
    np.testing.assert_allclose(models[0].elastic.reciprocal_vectors_xy, models[1].elastic.reciprocal_vectors_xy)
    cs = [depth_coherence(m.elastic, .7, steps=9) for m in models]
    np.testing.assert_allclose(cs[0], cs[1], atol=1e-14)
    results = [run(m, MultiSiteIonization(a, [group('Ni', 'Ni', tuple(range(len(a))), cfg)]), c)
               for m, a, c in zip(models, (atoms, repeated), cs)]
    for state in ('plus', 'minus'):
        np.testing.assert_allclose(results[0]['total'][state], results[1]['total'][state], rtol=1e-13)
        np.testing.assert_allclose(results[1]['weighted_sum'][state], 2 * results[0]['weighted_sum'][state])


@pytest.mark.parametrize('failure', ['species', 'axis', 'frame', 'coverage', 'identity', 'state', 'bare_path'])
def test_provider_rejections(tmp_path, failure):
    atoms = generic_atoms('Ni')
    model = model_for(atoms)
    cfg = source(tmp_path, element='Fe' if failure == 'species' else 'Ni')
    if failure in ('frame', 'state'):
        path = tmp_path / 'source.json'
        d = json.loads(path.read_text())
        if failure == 'frame':
            d['frame_to_crystal'] = np.diag([1, 1, -1]).tolist()
        else:
            d['magnetic_state'] = 'afm'
        path.write_text(json.dumps(d))
        # Refresh only the expected identity, so the invalid declaration is tested.
        import hashlib
        cfg = replace(cfg, source_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    if failure == 'identity':
        with open(cfg.source, 'a') as stream:
            stream.write(' ')
    g = group('Ni', 'Ni', (0,), cfg)
    if failure == 'axis':
        g = replace(g, magnetization=(1, 0, 0))
    elif failure == 'bare_path':
        g = replace(g, mdff_reference=cfg.source)
    with pytest.raises(ValueError):
        run(model, MultiSiteIonization(atoms, [g]), energy_ev=[703., 710.] if failure == 'coverage' else ENERGY)


@pytest.mark.parametrize('failure', ['cell', 'position', 'coherence', 'negative_coherence', 'rotation', 'energy', 'query'])
def test_numerical_context_rejections(tmp_path, failure):
    atoms = generic_atoms()
    cfg = source(tmp_path)
    sites = MultiSiteIonization(atoms, [group('Ni', 'Ni', (0,), cfg)])
    changed = atoms.copy()
    if failure == 'cell':
        changed.set_cell([5, 4, 4])
    elif failure == 'position':
        changed.positions[0, 0] += .1
    model = model_for(changed)
    c = coherence_for(model)
    kwargs = {}
    if failure == 'coherence':
        c[0, 1] += 1
    elif failure == 'negative_coherence':
        c = np.diag([1., -1.])
    elif failure == 'rotation':
        kwargs['rotation'] = np.diag([1, -1, 1])
    elif failure == 'energy':
        kwargs['energy_ev'] = [710, 709]
    elif failure == 'query':
        kwargs['qx'] = [np.nan, 0, 0]
    with pytest.raises(ValueError):
        run(model, sites, c, **kwargs)


def test_source_changed_during_contraction_is_rejected(tmp_path, monkeypatch):
    import emcd_sim.multisite_single_channeling as module

    atoms = generic_atoms()
    cfg = source(tmp_path)
    sites = MultiSiteIonization(atoms, [group('Ni', 'Ni', (0,), cfg)])
    original = module._tensor_angular_maps
    def change_source(*args):
        with open(cfg.source, 'a') as stream:
            stream.write(' ')
        return original(*args)
    monkeypatch.setattr(module, '_tensor_angular_maps', change_source)
    with pytest.raises(ValueError, match='checksum changed'):
        run(model_for(atoms), sites)
