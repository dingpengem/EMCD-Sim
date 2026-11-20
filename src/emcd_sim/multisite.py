"""Explicit ordered ionization-site groups for shared-crystal forward calculations.

No symmetry, magnetic equivalence, tensor rotation or spectral summation is
inferred here. Indices refer to ASE's expanded atom list, not CIF row numbers.
"""
from dataclasses import dataclass
from numbers import Integral

import numpy as np


@dataclass(frozen=True)
class IonizationSiteGroup:
    """One explicitly equivalent MDFF assignment, declared by the caller.

    ``mdff_reference`` is an existing provider/configuration or source reference;
    its loading, species metadata and source validation remain the provider's
    responsibility. Magnetization is a unit direction in crystal Cartesian
    coordinates, not fractional lattice coordinates or a moment magnitude.
    Multiplicity counts explicit atoms in this cell. A group MDFF is normalized
    per selected atom; a future cell sum must apply multiplicity exactly once.
    """

    group_id: str
    element: str
    indices: tuple[int, ...]
    mdff_reference: object
    magnetization: tuple[float, float, float]
    multiplicity: int
    normalization: str = 'mean_per_selected_atom'

    def __post_init__(self):
        from ase.data import atomic_numbers

        if not isinstance(self.group_id, str) or not self.group_id.strip():
            raise ValueError('A nonempty site-group identifier is required')
        if self.element not in atomic_numbers or self.element == 'X':
            raise ValueError('A real element is required')
        indices = tuple(self.indices)
        if (not indices or any(isinstance(i, bool) or not isinstance(i, Integral)
                               or i < 0 for i in indices)
                or len(set(indices)) != len(indices)):
            raise ValueError('Select unique nonnegative integer site indices')
        if (isinstance(self.multiplicity, bool)
                or not isinstance(self.multiplicity, Integral)
                or self.multiplicity != len(indices)):
            raise ValueError('Multiplicity must equal the explicit selected atom count')
        if self.normalization != 'mean_per_selected_atom':
            raise ValueError('Only mean_per_selected_atom normalization is supported')
        if self.mdff_reference is None or (isinstance(self.mdff_reference, str)
                                          and not self.mdff_reference.strip()):
            raise ValueError('An independent MDFF provider/source reference is required')
        m = np.asarray(self.magnetization, dtype=float)
        if m.shape != (3,) or not np.isfinite(m).all() or not np.any(m):
            raise ValueError('A finite nonzero magnetization direction is required')
        # Scale first to avoid overflow/underflow for finite input directions.
        m = m / np.max(np.abs(m))
        m = m / np.linalg.norm(m)
        object.__setattr__(self, 'indices', tuple(int(i) for i in indices))
        object.__setattr__(self, 'magnetization', tuple(float(v) for v in m))


def _ordered_atoms(structure):
    atoms = getattr(structure, 'atoms', structure)
    if (not np.all(atoms.pbc) or atoms.cell.rank != 3
            or not np.isfinite(atoms.cell.array).all()
            or abs(atoms.cell.volume) < 1e-8):
        raise ValueError('A nonsingular fully periodic 3D crystal is required')
    positions = atoms.get_scaled_positions(wrap=True)
    if not len(atoms) or not np.isfinite(positions).all() or np.any(atoms.numbers == 0):
        raise ValueError('Finite explicit atoms with real species are required')
    occupancy = atoms.info.get('occupancy', {})
    for occ in occupancy.values():
        values = np.asarray(list(occ.values()), float)
        if (len(occ) != 1 or not np.isfinite(values).all()
                or not np.allclose(values, 1., rtol=0, atol=1e-8)):
            raise ValueError('Partial/disordered occupancies are unsupported')
    kinds = atoms.arrays.get('spacegroup_kinds', np.arange(len(atoms)))
    for symbol, kind in zip(atoms.get_chemical_symbols(), kinds):
        occ = occupancy.get(str(int(kind)), occupancy.get(int(kind)))
        if occ is not None and set(occ) != {symbol}:
            raise ValueError('Occupancy species disagree with explicit atoms')
    for name in ('occupancy', 'occupancies'):
        if atoms.has(name):
            weights = np.asarray(atoms.arrays[name], float)
            if not np.isfinite(weights).all() or not np.allclose(weights, 1., rtol=0, atol=1e-8):
                raise ValueError('Partial/disordered occupancies are unsupported')
    for i, p in enumerate(positions):
        delta = positions[i + 1:] - p
        delta -= np.rint(delta)
        if np.any(np.linalg.norm(delta @ atoms.cell.array, axis=1) < 1e-7):
            raise ValueError('Duplicate periodic atom positions are unsupported')
    return atoms, positions


@dataclass(frozen=True, init=False)
class MultiSiteIonization:
    """Groups bound to an ordered crystal snapshot; unassigned atoms are allowed.

    No completeness requirement: non-ionizing host atoms may remain unassigned.
    Compatibility requires the same Cartesian cell basis as well as species and
    atom ordering, because magnetization is expressed in that basis.
    """

    groups: tuple[IonizationSiteGroup, ...]
    species: tuple[str, ...]
    fractional_positions: tuple
    cell: tuple

    def __init__(self, structure, groups):
        atoms, positions = _ordered_atoms(structure)
        groups = tuple(groups)
        if not groups or any(not isinstance(g, IonizationSiteGroup) for g in groups):
            raise ValueError('Explicit ionization-site groups are required')
        if len({g.group_id for g in groups}) != len(groups):
            raise ValueError('Site-group identifiers must be unique')
        species = tuple(atoms.get_chemical_symbols())
        assigned = set()
        for group in groups:
            for i in group.indices:
                if i >= len(atoms):
                    raise ValueError('Site index is outside the crystal')
                if species[i] != group.element:
                    raise ValueError('Site species does not match group element')
                if i in assigned:
                    raise ValueError('Duplicate site assignment across groups')
                assigned.add(i)
        object.__setattr__(self, 'groups', groups)
        object.__setattr__(self, 'species', species)
        object.__setattr__(self, 'fractional_positions', tuple(map(tuple, positions)))
        object.__setattr__(self, 'cell', tuple(map(tuple, atoms.cell.array)))

    def validate_structure(self, structure):
        """Reject changed species, ordering, geometry, occupancy or cell frame."""
        atoms, positions = _ordered_atoms(structure)
        if (tuple(atoms.get_chemical_symbols()) != self.species
                or not np.allclose(atoms.cell.array, self.cell, rtol=0, atol=1e-10)
                or positions.shape != (len(self.species), 3)):
            raise ValueError('Site groups do not match the crystal structure')
        delta = positions - np.asarray(self.fractional_positions)
        delta -= np.rint(delta)
        if not np.allclose(delta, 0, rtol=0, atol=1e-9):
            raise ValueError('Site groups do not match the ordered crystal positions')


def validate_site_rows(atoms, rows):
    """Shared validation of editor drafts; only complete rows form a Stage 1 model."""
    if not rows:return None
    _ordered_atoms(atoms)
    names = set();assigned = set();complete = []
    for name,element,indices,direction,reference in rows:
        if not name.strip() or name in names:raise ValueError('Group IDs must be nonempty and unique')
        names.add(name)
        if not indices:raise ValueError('Groups need at least one atom; delete an empty group instead')
        if len(set(indices))!=len(indices) or assigned.intersection(indices):
            raise ValueError('Duplicate assignments: remove atoms from their current group first')
        if any(isinstance(i,bool) or not isinstance(i,(int,np.integer)) or i<0 or i>=len(atoms) or atoms[i].symbol!=element for i in indices):
            raise ValueError('Each group must contain valid original indices of one element')
        assigned.update(indices)
        if direction is None and getattr(reference,'magnetic_state',None)=='nonmagnetic':
            # This is the source's declared compatibility/reference axis, not
            # an inferred Material magnetization. The structural row stays None.
            direction=reference.magnetization
        if direction is None:
            if reference is not None:raise ValueError('Declare a magnetic direction before binding an MDFF provider')
            continue  # Structural draft only: no magnetic direction is inferred.
        vector = np.asarray(direction)
        if vector.shape!=(3,) or not np.isfinite(vector).all() or not np.any(vector):
            raise ValueError('A finite nonzero magnetization direction is required')
        if reference is not None:
            complete.append(IonizationSiteGroup(name,element,indices,reference,direction,len(indices)))
    model = MultiSiteIonization(atoms,complete) if complete else None
    return model if len(complete)==len(rows) else None
