"""P1 atomic geometry only; no new potential or propagation implementation."""
from dataclasses import replace
from itertools import product
import json
from unittest.mock import patch

import numpy as np
import pytest

pytest.importorskip('ase')
from ase import Atoms
from ase.build import bulk
from ase.neighborlist import neighbor_list
from emcd_sim.atomic_multislice_geometry import (
    oriented_atomic_cell, atomic_planes, slice_geometry, specimen_positions,
    assign_atoms_to_slices, GeometryCapabilityError,
)
from emcd_sim.ni_017_geometry import Ni017Geometry


@pytest.fixture(scope='module')
def ni017():
    return oriented_atomic_cell(bulk('Ni', 'fcc', a=3.524, cubic=True))


def test_actual_017_frame_and_lattice_translations(ni017):
    np.testing.assert_allclose(ni017.frame, Ni017Geometry().frame, atol=1e-15)
    np.testing.assert_allclose(ni017.frame@ni017.frame.T, np.eye(3), atol=1e-15)
    assert np.linalg.det(ni017.frame) == pytest.approx(1.)
    np.testing.assert_array_equal(ni017.translations_input, [[1, 0, 0], [0, 3.5, -.5], [0, .5, 3.5]])
    np.testing.assert_allclose(ni017.atoms.cell.lengths(), [3.524, 3.524*np.sqrt(50)/2, 3.524*np.sqrt(50)/2])
    assert ni017.period_angstrom == pytest.approx(12.459221484506966)


def test_periodicity_atom_count_density_and_no_duplicates(ni017):
    source = bulk('Ni', 'fcc', a=3.524, cubic=True)
    assert len(ni017.atoms) == 50
    assert round(np.linalg.det(ni017.integer_supercell_matrix)) == 50
    assert len(ni017.atoms)/ni017.atoms.get_volume() == pytest.approx(4/3.524**3)
    assert not neighbor_list('i', ni017.atoms, 1e-7, self_interaction=False).size
    # Independently check each smaller FCC translation permutes the motif.
    original = {tuple(p) for p in source.get_scaled_positions()}
    for translation in ni017.translations_input:
        shifted = {tuple(p) for p in (source.get_scaled_positions()+translation) % 1}
        assert shifted == original


def test_transformed_positions_against_direct_crystal_enumeration(ni017):
    source = bulk('Ni', 'fcc', a=3.524, cubic=True)
    positions = np.concatenate([source.positions+np.array(n)*3.524 for n in product(range(-5, 6), repeat=3)])
    local = positions@ni017.frame.T
    lengths = ni017.atoms.cell.lengths()
    keep = np.all((local >= -1e-9) & (local < lengths-1e-9), axis=1)
    reference = np.round(local[keep], 8)
    actual = np.round(ni017.atoms.positions, 8)
    order = lambda p: p[np.lexsort((p[:, 0], p[:, 1], p[:, 2]))]
    np.testing.assert_array_equal(order(actual), order(reference))


def test_017_atomic_planes_follow_orientation_not_001(ni017):
    planes = atomic_planes(ni017)
    assert len(planes.depths_angstrom) == 50
    np.testing.assert_array_equal(planes.counts, np.ones(50))
    np.testing.assert_allclose(planes.depths_angstrom, np.arange(50)*3.524/(2*np.sqrt(50)), atol=1e-13)
    np.testing.assert_allclose(planes.next_spacing_angstrom, 3.524/(2*np.sqrt(50)), atol=1e-13)
    assert sum(planes.counts) == len(ni017.atoms)
    c001 = oriented_atomic_cell(bulk('Ni', 'fcc', a=3.524, cubic=True), (0, 0, 1))
    np.testing.assert_allclose(atomic_planes(c001).depths_angstrom, [0, 1.762])


@pytest.mark.parametrize('zone,count', [((0, 0, 1), 4), ((0, 1, 1), 2), ((1, 1, 1), 6), ((7, 1, 0), 50)])
def test_other_commensurate_orientations_use_same_framework(zone, count):
    cell = oriented_atomic_cell(bulk('Ni', 'fcc', a=3.524, cubic=True), zone)
    assert len(cell.atoms) == count
    assert np.linalg.det(cell.frame) == pytest.approx(1)
    np.testing.assert_allclose(cell.atoms.cell.angles(), [90, 90, 90])


@pytest.mark.parametrize('mode', ['uniform', 'plane-aware'])
def test_full_coverage_repeat_clipping_and_maximum(ni017, mode):
    slices = slice_geometry(ni017, 300, mode=mode)
    edges = slices.boundaries_angstrom
    assert edges[0] == 0 and edges[-1] == 300
    assert np.all(np.diff(edges) > 0)
    assert np.max(np.diff(edges)) <= .5+1e-12
    assert np.sum(np.diff(edges)) == pytest.approx(300)
    # The second repeat has the identical intervals, no stretching.
    n = len(slices.repeat_boundaries_angstrom)-1
    np.testing.assert_allclose(edges[n:2*n+1]-ni017.period_angstrom, slices.repeat_boundaries_angstrom, atol=1e-13)
    assert slices.period_index[-1] == 24
    assert slices.thicknesses_angstrom[-1] <= .5


def test_expected_native_slices_and_retained_empty_intervals(ni017):
    uniform = slice_geometry(ni017, 300)
    aware = slice_geometry(ni017, 300, mode='plane-aware')
    assert len(uniform.repeat_boundaries_angstrom)-1 == 25
    assert len(uniform.thicknesses_angstrom) == 602
    assert len(aware.repeat_boundaries_angstrom)-1 == 51
    assert len(aware.thicknesses_angstrom) == 1229
    slab = specimen_positions(ni017, 300)
    assert len(slab) == 1204
    for slices in (uniform, aware):
        ids = assign_atoms_to_slices(slab.positions[:, 2], slices.boundaries_angstrom)
        counts = np.bincount(ids, minlength=len(slices.thicknesses_angstrom))
        assert counts.sum() == 1204
    assert np.any(counts == 0)   # Do not discard empty-centre intervals: finite tails are future P2.


def test_parent_intervals_are_subdivided_and_preserved(ni017):
    cell = oriented_atomic_cell(bulk('Ni', 'fcc', a=3.524, cubic=True), (0, 0, 1))
    slices = slice_geometry(cell, 3.524, mode='plane-aware', max_slice_thickness_angstrom=.3)
    assert np.max(np.diff(slices.parent_boundaries_angstrom)) > .3
    assert np.max(slices.thicknesses_angstrom) <= .3+1e-12
    assert all(np.any(abs(slices.boundaries_angstrom-p) < 1e-12) for p in slices.parent_boundaries_angstrom)
    assert len(slices.thicknesses_angstrom) > len(slices.parent_boundaries_angstrom)-1


def test_partial_period_and_half_open_boundary_assignment(ni017):
    period = ni017.period_angstrom
    assert len(specimen_positions(ni017, 2*period)) == 100
    assert len(specimen_positions(ni017, .1)) == 1
    np.testing.assert_array_equal(assign_atoms_to_slices([0, .5, 1., 1.999], [0, .5, 1, 2]), [0, 1, 2, 2])
    with pytest.raises(ValueError, match='half-open'):
        assign_atoms_to_slices([2], [0, 1, 2])
    s = slice_geometry(ni017, .1)
    np.testing.assert_allclose(s.boundaries_angstrom, [0, .1])


def test_seam_grouping_retains_distinct_sites_and_close_planes(ni017):
    atoms = Atoms('Ni3', positions=[[0, 0, 1e-10], [1, 1, 2-1e-10], [0, 1, .0001]], cell=[2, 2, 2], pbc=True)
    cell = replace(ni017, atoms=atoms)
    before = atoms.positions.copy()
    planes = atomic_planes(cell)
    assert sorted(planes.counts) == [1, 2]
    assert len(planes.atom_plane_index) == 3
    np.testing.assert_array_equal(atoms.positions, before)


def test_geometry_capabilities_and_duplicate_sites_fail_explicitly():
    atoms = Atoms('Ni', positions=[[0, 0, 0]], cell=[[3, 0, 0], [.123456789, np.pi, 0], [.17, .4, np.e]], pbc=True)
    with pytest.raises(GeometryCapabilityError, match='commensurate'):
        oriented_atomic_cell(atoms, (1, 1, 1), max_translation_index=16)
    ni = bulk('Ni', 'fcc', a=3.524, cubic=True)
    with pytest.raises(GeometryCapabilityError, match='max_atoms'):
        oriented_atomic_cell(ni, max_atoms=49)
    with pytest.raises(GeometryCapabilityError, match='duplicate'):
        oriented_atomic_cell(ni+ni)
    for zone in [(0, 0, 0), (.5, 1, 7), (float('nan'), 1, 7)]:
        with pytest.raises(ValueError):
            oriented_atomic_cell(ni, zone)


def test_budget_and_invalid_slices_reject_before_large_allocations(ni017):
    for maximum in (0, -1, float('nan')):
        with pytest.raises(ValueError):
            slice_geometry(ni017, 300, max_slice_thickness_angstrom=maximum)
    with pytest.raises(GeometryCapabilityError, match='budget'):
        slice_geometry(ni017, 300, max_slice_thickness_angstrom=1e-12)
    # Thickness / maximum alone is insufficient: repeat-tail intervals also count.
    with pytest.raises(GeometryCapabilityError, match='budget'):
        slice_geometry(ni017, 300, max_slices=601)
    with pytest.raises(GeometryCapabilityError, match='budget'):
        specimen_positions(ni017, 300, max_atoms=100)


def test_general_decorated_structure_is_not_reduced_to_monatomic_fcc():
    atoms = bulk('Ni', 'fcc', a=3.524, cubic=True)
    atoms.numbers[1] = 29
    cell = oriented_atomic_cell(atoms)
    assert len(cell.atoms) == 200  # conventional translations required by this decoration
    assert cell.atoms.get_chemical_symbols().count('Cu') == 50
    np.testing.assert_array_equal(cell.primitive_basis_input, np.eye(3))


def test_real_small_displacement_is_not_idealized_as_fcc():
    atoms = bulk('Ni', 'fcc', a=3.524, cubic=True)
    atoms.positions[1, 0] += 1e-9
    before = atoms.positions.copy()
    cell = oriented_atomic_cell(atoms)
    assert len(cell.atoms) == 200
    np.testing.assert_array_equal(cell.primitive_basis_input, np.eye(3))
    np.testing.assert_array_equal(atoms.positions, before)


def test_nearly_commensurate_cell_is_not_silently_strained():
    atoms = Atoms('Ni', positions=[[0, 0, 0]], cell=[[3, 0, 0], [0, 4, 0], [1e-9, 0, 5]], pbc=True)
    with pytest.raises(GeometryCapabilityError, match='commensurate'):
        oriented_atomic_cell(atoms, (0, 0, 1))


def test_pickle_free_diagnostics_cif_roundtrip_and_no_propagation(tmp_path):
    from ase.io import read
    from emcd_sim.atomic_slicing_diagnostics import export_diagnostics
    with patch('emcd_sim.physical_elastic.PhysicalElasticModel.amplitudes', side_effect=AssertionError('P1 propagation')), \
         patch('emcd_sim.multislice_reference.fft_multislice_ni', side_effect=AssertionError('P1 propagation')):
        result = export_diagnostics(tmp_path/'p1', thickness_nm=.15)
    assert result['milestone'].startswith('P1')
    assert result['specimen_atom_count'] == 7
    restored = read(tmp_path/'p1/crystal_oriented.cif')
    assert len(restored) == 50
    np.testing.assert_allclose(restored.cell.lengths(), [3.524, 12.459221484506966, 12.459221484506966])
    with np.load(tmp_path/'p1/geometry_arrays.npz', allow_pickle=False) as arrays:
        assert all(not arrays[k].dtype.hasobject for k in arrays.files)
        assert arrays['positions_angstrom'].shape == (50, 3)
        for mode in ('uniform', 'plane_aware'):
            assert arrays[mode+'_boundaries_angstrom'][-1] == 1.5
    assert json.loads((tmp_path/'p1/metadata.json').read_text())['atoms_per_repeat'] == 50
