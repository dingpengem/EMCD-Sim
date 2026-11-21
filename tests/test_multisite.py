"""Data-model checks only; synthetic cells do not predict EMCD spectra."""
from types import SimpleNamespace

import numpy as np
import pytest
from ase import Atoms
from ase.build import bulk

from emcd_sim.ionization_sites import IonizationSites
from emcd_sim.multisite import IonizationSiteGroup, MultiSiteIonization


def group(name, element, indices, direction=(0, 0, 1), reference='source.json', **kw):
    return IonizationSiteGroup(name, element, indices, reference, direction,
                               kw.pop('multiplicity', len(indices)), **kw)


def test_bcc_cr_antiparallel():
    atoms = bulk('Cr', 'bcc', a=2.88, cubic=True)
    atoms.set_initial_magnetic_moments([1, -1])
    model = MultiSiteIonization(atoms, [group('up', 'Cr', (0,), reference='up.json'),
                                      group('down', 'Cr', (1,), (0, 0, -2), 'down.json')])
    assert model.groups[1].magnetization == (0., 0., -1.)
    assert model.groups[0].mdff_reference != model.groups[1].mdff_reference
    model.validate_structure(atoms.copy())


def test_synthetic_magnetite_distinct_fe_and_oxygen():
    # Stoichiometry and assignments only; not a crystallographic magnetite model.
    atoms = Atoms('Fe3O4', scaled_positions=[(i / 7, 0, 0) for i in range(7)],
                  cell=[8, 8, 8], pbc=True)
    provider = object()
    model = MultiSiteIonization(SimpleNamespace(atoms=atoms), [
        group('Fe(A)', 'Fe', (0,), (0, 0, -1)),
        group('Fe(B)', 'Fe', (1, 2), (1, 1, 0), provider),
        group('O', 'O', (3, 4, 5, 6))])
    assert [g.multiplicity for g in model.groups] == [1, 2, 4]
    assert model.groups[1].mdff_reference is provider
    np.testing.assert_allclose(model.groups[1].magnetization, [2**-.5, 2**-.5, 0])
    assert all(g.normalization == 'mean_per_selected_atom' for g in model.groups)


@pytest.mark.parametrize('indices', [(), (-1,), (True,), (0.5,), (0, 0)])
def test_bad_indices(indices):
    with pytest.raises(ValueError):
        group('a', 'Ni', indices)


@pytest.mark.parametrize('direction', [(0, 0, 0), (np.nan, 0, 1),
                                       (0, np.inf, 1), (1, 2)])
def test_bad_direction(direction):
    with pytest.raises(ValueError):
        group('a', 'Ni', (0,), direction)


@pytest.mark.parametrize('kwargs', [dict(multiplicity=2), dict(normalization='sum'),
                                    dict(reference=None)])
def test_bad_group_metadata(kwargs):
    with pytest.raises(ValueError):
        group('a', 'Ni', (0,), **kwargs)


@pytest.mark.parametrize('name,element', [('', 'Ni'), ('  ', 'Ni'), ('a', 'X'), ('a', 'Bad')])
def test_bad_identity(name, element):
    with pytest.raises(ValueError):
        group(name, element, (0,))


def test_cif_expanded_indices(tmp_path):
    from ase.io import read, write

    path = tmp_path / 'ordered.cif'
    write(path, bulk('Cr', 'bcc', a=2.88, cubic=True))
    atoms = read(path)
    model = MultiSiteIonization(atoms, [group('Cr0', 'Cr', (0,)),
                                      group('Cr1', 'Cr', (1,), (0, 0, -1))])
    model.validate_structure(atoms)
    assert model.species == ('Cr', 'Cr')


@pytest.mark.parametrize('groups', [
    [group('a', 'Ni', (4,))], [group('a', 'Fe', (0,))],
    [group('a', 'Ni', (0,)), group('b', 'Ni', (0,))],
    [group('a', 'Ni', (0,)), group('a', 'Ni', (1,))], []])
def test_bad_assignments(groups):
    with pytest.raises(ValueError):
        MultiSiteIonization(bulk('Ni', 'fcc', a=3.52, cubic=True), groups)


@pytest.mark.parametrize('change', ['cell', 'position', 'species', 'pbc', 'duplicate',
                                    'partial', 'mixed', 'occupancy_array', 'occupancy_species'])
def test_structure_validation(change):
    atoms = bulk('Ni', 'fcc', a=3.52, cubic=True)
    model = MultiSiteIonization(atoms, [group('a', 'Ni', (0,))])
    if change == 'cell':
        atoms.set_cell(atoms.cell.array @ np.diag([-1, -1, 1]))
    elif change == 'position':
        atoms.positions[0, 0] += .1
    elif change == 'species':
        atoms[1].symbol = 'Fe'
    elif change == 'pbc':
        atoms.pbc = False
    elif change == 'duplicate':
        atoms.positions[1] = atoms.positions[0]
    elif change == 'partial':
        atoms.info['occupancy'] = {'0': {'Ni': .5}}
    elif change == 'mixed':
        atoms.info['occupancy'] = {'0': {'Ni': .5, 'Fe': .5}}
    elif change == 'occupancy_array':
        atoms.new_array('occupancies', np.array([1., 1., .5, 1.]))
    else:
        atoms.info['occupancy'] = {'0': {'Fe': 1.}}
    with pytest.raises(ValueError):
        model.validate_structure(atoms)
    if change not in ('cell', 'position', 'species'):
        with pytest.raises(ValueError):
            MultiSiteIonization(atoms, model.groups)


def test_ni_legacy_unchanged_and_snapshot_independent():
    atoms = bulk('Ni', 'fcc', a=3.524, cubic=True)
    structure = SimpleNamespace(atoms=atoms)
    old = IonizationSites.from_structure(structure, 'Ni')
    model = MultiSiteIonization(structure, [group('Ni', 'Ni', tuple(range(4)))])
    assert old.indices == model.groups[0].indices
    assert old.normalization == model.groups[0].normalization
    np.testing.assert_allclose(old.all_positions, model.fractional_positions)
    np.testing.assert_allclose(old.metric, np.asarray(model.cell) @ np.asarray(model.cell).T)
    atoms.positions[0] += atoms.cell[0]
    model.validate_structure(atoms)
    atoms.positions[0, 0] += .1
    with pytest.raises(ValueError):
        model.validate_structure(atoms)
    np.testing.assert_array_equal(old.single_phase(SimpleNamespace(
        species=('Ni',) * 4, fractional_positions=old.all_positions,
        lattice_angstrom=np.asarray(model.cell)), [[0, 0, 0]]), [[1.]])
