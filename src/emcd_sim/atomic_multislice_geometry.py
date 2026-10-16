"""Unstrained atomic supercells and depth intervals for future 3D multislice.

P1 geometry only: no potential, transmission, propagation or ionization.
ASE is an optional structural dependency, as for the existing GUI.
"""
from dataclasses import dataclass
from fractions import Fraction
from functools import reduce
from math import gcd, lcm
import hashlib
import json

import numpy as np
from ase import Atoms
from ase.build import make_supercell
from ase.neighborlist import neighbor_list

from .gui.geometry import orientation


class GeometryCapabilityError(ValueError):
    """No supported exact, bounded, unstrained construction was found."""


@dataclass(frozen=True)
class OrientedAtomicCell:
    atoms: Atoms
    zone_axis: tuple[int, int, int]
    frame: np.ndarray                 # rows: crystal Cartesian -> local
    translations_input: np.ndarray    # rows, in supplied lattice coordinates
    primitive_basis_input: np.ndarray
    integer_supercell_matrix: np.ndarray
    source_sha256: str

    @property
    def period_angstrom(self):
        return float(self.atoms.cell[2, 2])


@dataclass(frozen=True)
class AtomicPlanes:
    depths_angstrom: np.ndarray
    atom_plane_index: np.ndarray
    counts: np.ndarray
    species: tuple[tuple[str, ...], ...]
    next_spacing_angstrom: np.ndarray
    period_angstrom: float
    tolerance_angstrom: float


@dataclass(frozen=True)
class SliceGeometry:
    boundaries_angstrom: np.ndarray
    repeat_boundaries_angstrom: np.ndarray
    parent_boundaries_angstrom: np.ndarray
    period_index: np.ndarray
    parent_index: np.ndarray
    mode: str
    max_slice_thickness_angstrom: float
    period_angstrom: float

    @property
    def thicknesses_angstrom(self):
        return np.diff(self.boundaries_angstrom)


def structure_hash(atoms):
    """Numeric input identity; independent of file paths and ASE object identity."""
    value = dict(cell=atoms.cell.array.tolist(), numbers=atoms.numbers.tolist(),
                 positions=atoms.positions.tolist(), pbc=atoms.pbc.tolist())
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def _translation_basis(atoms, tol):
    # Only a verified monatomic F-centred motif is reduced. A general decorated
    # cell is retained, including all species/sites; no symmetry is guessed.
    fcc = np.array([[0, 0, 0], [0, .5, .5], [.5, 0, .5], [.5, .5, 0]])
    scaled = atoms.get_scaled_positions() % 1
    if len(atoms) == 4 and len(set(atoms.numbers)) == 1:
        delta = scaled[:, None, :] - fcc[None, :, :]
        delta -= np.rint(delta)
        # A real small displacement must not be idealized away as FCC symmetry.
        roundoff = 64*np.finfo(float).eps*np.linalg.norm(atoms.cell.array)
        matched = np.linalg.norm(delta @ atoms.cell.array, axis=-1) < min(tol, roundoff)
        if np.all(matched.sum(axis=0) == 1) and np.all(matched.sum(axis=1) == 1):
            basis = np.array([[0, .5, .5], [.5, 0, .5], [.5, .5, 0]])
            return Atoms(numbers=[int(atoms.numbers[0])], positions=[[0, 0, 0]],
                         cell=basis @ atoms.cell.array, pbc=True), basis
    return atoms.copy(), np.eye(3)


def _integer_translation(axis, cell, limit, tol):
    direction = axis @ np.linalg.inv(cell)
    pivot = int(np.argmax(abs(direction)))
    ratios = direction / abs(direction[pivot])
    fractions = [Fraction(float(v)).limit_denominator(limit) for v in ratios]
    denominator = lcm(*(f.denominator for f in fractions))
    values = [f.numerator * (denominator // f.denominator) for f in fractions]
    divisor = reduce(gcd, (abs(v) for v in values))
    values = [v // divisor for v in values]
    if max(abs(v) for v in values) > limit:
        raise GeometryCapabilityError('Commensurate translation exceeds max_translation_index; no lattice strain applied.')
    n = np.array(values, dtype=int)
    vector = n @ cell
    roundoff = 128*np.finfo(float).eps*max(np.linalg.norm(cell), np.linalg.norm(vector))
    if np.dot(vector, axis) <= 0 or np.linalg.norm(vector - np.dot(vector, axis)*axis) > min(tol, roundoff):
        raise GeometryCapabilityError('No exact commensurate orthogonal translation found within search limits; no lattice strain applied.')
    return n


def oriented_atomic_cell(atoms, zone_axis=(0, 1, 7), *, max_translation_index=256,
                         max_atoms=100000, tolerance_angstrom=1e-8):
    """Construct a right-handed orthogonal periodic cell without affine strain.

    [uvw] is expressed in the supplied direct-lattice basis, as in the GUI.
    Bounded rational reconstruction finds integer translations along the same
    local frame. Failure is a capability error, not a strained approximation.
    """
    raw = np.asarray(zone_axis, dtype=float)
    if raw.shape != (3,) or not np.isfinite(raw).all() or not np.all(raw == np.rint(raw)) or not raw.any():
        raise ValueError('zone_axis must contain three nonzero-as-a-vector integer indices')
    zone = tuple(int(v) for v in raw)
    divisor = reduce(gcd, (abs(v) for v in zone))
    zone = tuple(v // divisor for v in zone)
    if (not len(atoms) or not atoms.pbc.all() or not np.isfinite(atoms.positions).all()
            or not np.isfinite(atoms.cell.array).all() or np.linalg.det(atoms.cell.array) <= 0):
        raise GeometryCapabilityError('A finite, nonempty, right-handed, fully periodic 3D structure is required.')
    if not np.isfinite(tolerance_angstrom) or tolerance_angstrom <= 0:
        raise ValueError('tolerance_angstrom must be positive and finite')
    if np.min(np.linalg.svd(atoms.cell.array, compute_uv=False)) <= 100*tolerance_angstrom:
        raise GeometryCapabilityError('Cell is singular or too small relative to the geometric tolerance.')
    for name, value in [('max_atoms', max_atoms), ('max_translation_index', max_translation_index)]:
        if not isinstance(value, int) or value < 1:
            raise ValueError(name+' must be a positive integer')
    if len(atoms) > max_atoms:
        raise GeometryCapabilityError('Input exceeds max_atoms before supercell construction.')
    for occupancies in atoms.info.get('occupancy', {}).values():
        if len(occupancies) != 1 or not np.isclose(sum(occupancies.values()), 1., atol=1e-12, rtol=0):
            raise GeometryCapabilityError('Partial/disordered occupancies are not supported in P1.')
    if neighbor_list('i', atoms, tolerance_angstrom, self_interaction=False).size:
        raise GeometryCapabilityError('Input has duplicate atomic sites under periodic wrapping.')
    frame = orientation(atoms.cell.array, zone)
    base, basis = _translation_basis(atoms, tolerance_angstrom)
    matrix = np.stack([_integer_translation(axis, base.cell.array, max_translation_index,
                                          tolerance_angstrom) for axis in frame])
    determinant = int(round(np.linalg.det(matrix)))
    if determinant <= 0:
        raise GeometryCapabilityError('Supercell translations must be right-handed and independent.')
    if determinant * len(base) > max_atoms:
        raise GeometryCapabilityError('Exact orthogonal supercell exceeds max_atoms; no sites were removed.')
    expected = matrix @ base.cell.array @ frame.T
    diagonal = np.diag(np.diag(expected))
    roundoff = 128*np.finfo(float).eps*np.linalg.norm(expected)
    if not np.allclose(expected, diagonal, atol=min(tolerance_angstrom, roundoff), rtol=0) or np.any(np.diag(expected) <= 0):
        raise GeometryCapabilityError('Exact orthogonal cell validation failed; no strain applied.')
    expanded = make_supercell(base, matrix, wrap=True, tol=1e-10)
    fractional = expanded.get_scaled_positions(wrap=False) % 1
    # Snap only floating-point boundary roundoff, not the plane-grouping tolerance.
    fractional[np.abs(fractional - 1) < 32*np.finfo(float).eps] = 0
    fractional[np.abs(fractional) < 32*np.finfo(float).eps] = 0
    # Rotation is rigid. Discard only off-diagonal numerical roundoff, checked above.
    local = Atoms(numbers=expanded.numbers, scaled_positions=fractional,
                  cell=diagonal, pbc=True)
    if len(local) != determinant * len(base) or neighbor_list('i', local, tolerance_angstrom, self_interaction=False).size:
        raise GeometryCapabilityError('Supercell atom count or periodic uniqueness validation failed.')
    order = np.lexsort((local.positions[:, 0], local.positions[:, 1], local.positions[:, 2]))
    return OrientedAtomicCell(local[order], zone, frame.copy(), matrix @ basis,
                              basis, matrix, structure_hash(atoms))


def atomic_planes(cell, *, tolerance_angstrom=1e-8):
    """Group nominal z planes; retain every atom's distinct Cartesian position.

    Groups span at most tolerance (no transitive close-site merging). Boundary
    wrap uses machine precision; diagnostic grouping never moves atomic sites.
    """
    period = cell.period_angstrom
    if not np.isfinite(tolerance_angstrom) or not 0 < tolerance_angstrom < period/4:
        raise ValueError('Plane tolerance must be positive and much smaller than the period.')
    z = cell.atoms.positions[:, 2] % period
    z[np.abs(z-period) < 32*np.finfo(float).eps*period] = 0
    groups = []
    for index in np.argsort(z, kind='stable'):
        if not groups or z[index]-z[groups[-1][0]] > tolerance_angstrom:
            groups.append([int(index)])
        else:
            groups[-1].append(int(index))
    # Join a plane straddling the periodic seam, without counting either site twice.
    if len(groups) > 1 and z[groups[0][-1]] + period-z[groups[-1][0]] <= tolerance_angstrom:
        groups[0] = groups[-1] + groups[0]
        groups.pop()
    depths = np.array([np.mean(np.where(z[g] > period/2, z[g]-period, z[g])) % period
                       if np.ptp(z[g]) > period/2 else np.mean(z[g]) for g in groups])
    groups = [groups[i] for i in np.argsort(depths)]
    depths.sort()
    indices = np.empty(len(z), dtype=int)
    for i, g in enumerate(groups):
        indices[g] = i
    symbols = cell.atoms.get_chemical_symbols()
    return AtomicPlanes(depths, indices, np.array([len(g) for g in groups]),
                        tuple(tuple(sorted({symbols[i] for i in g})) for g in groups),
                        np.diff(np.r_[depths, depths[0]+period]), period, tolerance_angstrom)


def _subdivide(parents, maximum, limit):
    count = np.ceil(np.diff(parents)/maximum).astype(float)
    if not np.isfinite(count).all() or count.sum() > limit:
        raise GeometryCapabilityError('Requested maximum thickness exceeds max_slices budget; increase it explicitly.')
    edges = [float(parents[0])]
    for lo, hi, n in zip(parents[:-1], parents[1:], count.astype(int)):
        edges.extend((lo + np.arange(1, n)*maximum).tolist())
        edges.append(float(hi))
    return np.array(edges)


def slice_geometry(cell, thickness_angstrom, *, max_slice_thickness_angstrom=.5,
                   mode='uniform', plane_tolerance_angstrom=1e-8, max_slices=200000):
    """Repeat physical intervals, then clip the final period at the specimen exit.

    Uniform means maximum-sized intervals anchored in each structural repeat,
    retaining its final shorter interval. Plane-aware parents are periodic
    nearest-plane midpoints, clipped at the repeat entrance/exit, and subdivided
    using the same maximum. No potential is assigned or duplicated here.
    """
    maximum = float(max_slice_thickness_angstrom)
    thickness = float(thickness_angstrom)
    if not np.isfinite([maximum, thickness]).all() or min(maximum, thickness) <= 0:
        raise ValueError('Specimen and maximum slice thickness must be positive finite angstrom.')
    if not isinstance(max_slices, int) or max_slices < 1:
        raise ValueError('max_slices must be a positive integer')
    if mode not in ('uniform', 'plane-aware'):
        raise ValueError('mode must be uniform or plane-aware')
    period = cell.period_angstrom
    if thickness/maximum > max_slices or thickness/period > max_slices:
        raise GeometryCapabilityError('Requested thickness/sampling exceeds max_slices budget.')
    parents = np.array([0., period])
    if mode == 'plane-aware':
        planes = atomic_planes(cell, tolerance_angstrom=plane_tolerance_angstrom)
        d = planes.depths_angstrom
        midpoints = (d + np.r_[d[1:], d[0]+period])/2 % period
        eps = 32*np.finfo(float).eps*period
        parents = np.r_[0., np.sort(midpoints[(midpoints > eps) & (midpoints < period-eps)]), period]
    repeat = _subdivide(parents, maximum, max_slices)
    # Build only periods actually present; exact exit periods add no empty slice.
    nperiods = int(np.ceil(thickness/period))
    if (nperiods-1)*(len(repeat)-1) > max_slices:
        raise GeometryCapabilityError('Repeated slice count exceeds max_slices budget before allocation.')
    arrays = []
    for i in range(nperiods):
        edges = i*period + repeat[:-1]
        arrays.append(edges[edges < thickness])
    if sum(len(e) for e in arrays) > max_slices:
        raise GeometryCapabilityError('Physical slice count exceeds max_slices budget; no planes were removed.')
    boundaries = np.r_[np.concatenate(arrays), thickness]
    delta = np.diff(boundaries)
    if np.any(delta <= 0) or np.any(delta > maximum + 64*np.finfo(float).eps*max(thickness, period)):
        raise GeometryCapabilityError('Slice coverage/maximum validation failed at floating-point precision.')
    period_index = np.concatenate([np.full(len(e), i, dtype=int) for i, e in enumerate(arrays)])
    # Use template indices rather than recomputing boundary membership after a large shift.
    parent_index = np.concatenate([np.searchsorted(parents, repeat[:len(e)], side='right')-1 for e in arrays])
    return SliceGeometry(boundaries, repeat, parents, period_index, parent_index, mode, maximum, period)


def specimen_positions(cell, thickness_angstrom, *, max_atoms=1000000):
    """Half-open [0, thickness) atomic slab from unchanged periodic repeats.

    This specifies structural termination only; electrostatic surface/tail
    boundary conditions are deliberately undecided until potential generation.
    """
    thickness = float(thickness_angstrom)
    if not np.isfinite(thickness) or thickness <= 0:
        raise ValueError('Specimen thickness must be positive finite angstrom.')
    if not isinstance(max_atoms, int) or max_atoms < 1:
        raise ValueError('max_atoms must be a positive integer')
    nperiods = int(np.ceil(thickness/cell.period_angstrom))
    if (nperiods-1)*len(cell.atoms) > max_atoms:
        raise GeometryCapabilityError('Specimen atom count exceeds max_atoms budget.')
    positions = []
    numbers = []
    for i in range(nperiods):
        p = cell.atoms.positions.copy()
        p[:, 2] += i*cell.period_angstrom
        keep = p[:, 2] < thickness
        positions.append(p[keep])
        numbers.extend(cell.atoms.numbers[keep])
    if len(numbers) > max_atoms:
        raise GeometryCapabilityError('Specimen atom count exceeds max_atoms budget.')
    slab = np.diag(cell.atoms.cell).copy()
    slab[2] = thickness
    return Atoms(numbers=numbers, positions=np.concatenate(positions), cell=np.diag(slab), pbc=(True, True, False))


def assign_atoms_to_slices(z_angstrom, boundaries_angstrom):
    """Diagnostic centre assignment, NOT a finite-potential integration rule.

    At an internal boundary the atom belongs to the interval on its right;
    atoms at the exit are excluded. Finite atomic tails must cross intervals
    in P2 even if the centre is assigned to just one interval here.
    """
    b = np.asarray(boundaries_angstrom, dtype=float)
    z = np.asarray(z_angstrom, dtype=float)
    if b.ndim != 1 or len(b) < 2 or not np.isfinite(b).all() or np.any(np.diff(b) <= 0):
        raise ValueError('Boundaries must be finite and strictly increasing.')
    if not np.isfinite(z).all() or np.any(z < b[0]) or np.any(z >= b[-1]):
        raise ValueError('Atom centres must be in the half-open specimen interval.')
    return np.searchsorted(b, z, side='right')-1
