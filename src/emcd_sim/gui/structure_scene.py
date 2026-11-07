"""Read-only ASE-to-view scene data; no diffraction or MDFF eligibility rules."""
from dataclasses import dataclass
from itertools import product
from copy import deepcopy

import numpy as np
from ase import Atoms
from ase.data import covalent_radii, vdw_radii
from ase.data.colors import jmol_colors
from ase.neighborlist import neighbor_list


MAX_ATOMS = 3000
MAX_BOND_ATOMS = 1000
MAX_BONDS = 10000


def cell_segments(cell):
    """Twelve Cartesian edges of a general row-vector cell."""
    corners = np.asarray(list(product((0, 1), repeat=3)), float)
    edges = [(i, j) for i in range(8) for j in range(i + 1, 8)
             if np.count_nonzero(corners[i] != corners[j]) == 1]
    return (corners @ np.asarray(cell))[np.asarray(edges)]


def occupancy_record(atoms, index):
    kinds = atoms.arrays.get('spacegroup_kinds')
    kind = int(kinds[index]) if kinds is not None else index
    records = atoms.info.get('occupancy', {})
    record = records.get(str(kind), records.get(kind)) if isinstance(records, dict) else records
    available = {}
    if record is not None:available['CIF occupancy'] = deepcopy(record)
    for name in ('occupancy', 'occupancies'):
        if atoms.has(name):available[name] = np.asarray(atoms.arrays[name][index]).tolist()
    return available


@dataclass(frozen=True)
class CrystalScene:
    """Rendered replicas refer to original ASE indices, never reordered atoms."""
    cell: np.ndarray
    positions: np.ndarray
    fractional: np.ndarray
    original_positions: np.ndarray
    indices: np.ndarray
    offsets: np.ndarray
    symbols: tuple
    colors: np.ndarray
    ball_radii: np.ndarray
    space_radii: np.ndarray
    occupancies: tuple
    bonds: np.ndarray
    repetitions: tuple
    requested_count: int
    notices: tuple


def build_scene(atoms, repetitions=(1, 1, 1)):
    reps = tuple(repetitions)
    if len(reps) != 3 or any(type(n) is not int or not 1 <= n <= 4 for n in reps):
        raise ValueError('Display repetitions must be three integers from 1 to 4')
    cell = np.asarray(atoms.cell.array, float).copy()
    positions = np.asarray(atoms.get_positions(), float)
    if cell.shape != (3, 3) or not np.isfinite(cell).all() or not np.isfinite(positions).all():
        raise ValueError('Finite atom positions and lattice vectors required for display')
    count = len(atoms) * int(np.prod(reps))
    sequence = np.arange(min(count, MAX_ATOMS))
    indices = sequence % len(atoms) if len(atoms) else sequence
    translations = np.asarray(list(product(*(range(n) for n in reps))), int)
    offsets = translations[sequence // len(atoms)] if len(atoms) else np.empty((0, 3), int)
    rendered = positions[indices] + offsets @ cell
    original_symbols = atoms.get_chemical_symbols()
    symbols = tuple(original_symbols[i] for i in indices)
    numbers = np.asarray(atoms.numbers)[indices]
    covalent = np.asarray([covalent_radii[z] if z < len(covalent_radii) else 1. for z in numbers], float)
    covalent = np.where(np.isfinite(covalent) & (covalent > 0), covalent, 1.)
    space = np.asarray([vdw_radii[z] if z < len(vdw_radii) else np.nan for z in numbers], float)
    space = np.where(np.isfinite(space) & (space > 0), space, 1.5 * covalent)
    colors = np.asarray([jmol_colors[z] if z < len(jmol_colors) else (.6, .6, .6) for z in numbers], float).reshape(-1, 3)
    notices = []
    if count > MAX_ATOMS:
        notices.append(f'Displaying the first {MAX_ATOMS} of {count} display atoms; the source is unchanged.')
    bonds = np.empty((0, 2), int)
    if 1 < len(rendered) <= MAX_BOND_ATOMS:
        # Finite display cluster: bonds can cross into displayed replicas, but
        # never point to invisible periodic images. This is a geometric contact
        # heuristic, with no bond orders or chemical-state inference.
        display = Atoms(symbols, positions=rendered, pbc=False)
        i, j = neighbor_list('ij', display, 1.15 * covalent, max_nbins=10000)
        bonds = np.column_stack((i[i < j], j[i < j]))
        if len(bonds) > MAX_BONDS:
            bonds = bonds[:MAX_BONDS]
            notices.append(f'Contact display limited to {MAX_BONDS} bonds.')
    elif len(rendered) > MAX_BOND_ATOMS:
        notices.append(f'Bonds are hidden above {MAX_BOND_ATOMS} display atoms to keep interaction responsive.')
    if atoms.info.get('occupancy') or any(atoms.has(k) for k in ('occupancy', 'occupancies')):
        notices.append('Spheres show ASE representative elements. Mixed/partial occupancies are metadata, not additional atoms; discarded CIF species cannot be reconstructed.')
    else:
        notices.append('Occupancies were not supplied; no occupancy, magnetic state or oxidation state is inferred.')
    return CrystalScene(cell, rendered.copy(), atoms.get_scaled_positions(wrap=False)[indices].copy(),
        positions[indices].copy(), indices.copy(), offsets.copy(), symbols, colors,
        .35 * covalent, space, tuple(occupancy_record(atoms, int(i)) for i in indices),
        bonds, reps, count, tuple(notices))
