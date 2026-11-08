"""Nonmagnetic symmetry suggestions in original ASE order, never MDFF inputs."""
import string
import numpy as np


def crystallographic_sites(atoms, symprec=1e-5):
    """Return JSON-compatible structural provenance and optional site suggestions.

    ``equivalent_atoms`` uses the actual input-cell operations. No standardizing,
    idealizing, reordering, magnetic symmetry, or tolerance relaxation is applied.
    Unsupported/ambiguous inputs remain available to the ordinary viewer.
    """
    if not np.isfinite(symprec) or symprec <= 0:
        raise ValueError('Symmetry tolerance must be positive and finite')
    result = dict(method='spglib equivalent_atoms', symprec_angstrom=float(symprec),
                  angle_tolerance=-1., status='manual', groups=[], warnings=[])
    try:
        from .multisite import _ordered_atoms
        _ordered_atoms(atoms)
        if not len(atoms) or atoms.cell.rank != 3 or not all(atoms.pbc):
            raise ValueError('Symmetry grouping requires a nonempty 3D periodic cell')
        import spglib
        result['spglib_version'] = spglib.__version__
        cell = (atoms.cell.array, atoms.get_scaled_positions(), atoms.numbers)
        data = spglib.get_symmetry_dataset(cell, symprec=symprec)
        if data is None:raise ValueError('No unambiguous symmetry dataset found')
        # Origin choices change Wyckoff letters (e.g. spinel 8a/16d vs 8b/16c).
        # Honor ASE's CIF setting only when its space group matches the structure.
        declared = atoms.info.get('spacegroup')
        if declared is not None and hasattr(declared, 'no'):
            if declared.no == data.number and data.choice in ('1','2'):
                hall = data.hall_number + int(declared.setting) - int(data.choice)
                kind = spglib.get_spacegroup_type(hall)
                if kind.number == data.number and kind.choice == str(declared.setting):
                    data = spglib.get_symmetry_dataset(cell, hall_number=hall, symprec=symprec)
            elif declared.no != data.number:
                result['warnings'].append('CIF space group disagrees with the actual structure; inferred symmetry is used.')
        if data is None:raise ValueError('Declared CIF setting is incompatible with the structure')
        result.update(spacegroup_number=int(data.number), international=data.international,
                      hall_number=int(data.hall_number), setting=data.choice,
                      origin_shift=data.origin_shift.tolist(),
                      transformation_matrix=data.transformation_matrix.tolist())
        symbols = atoms.get_chemical_symbols()
        kinds = atoms.arrays.get('spacegroup_kinds')
        labels = atoms.info.get('_atom_site_label', [])
        labels = [labels] if isinstance(labels, str) else labels
        source_symbols = atoms.info.get('_atom_site_type_symbol', [])
        source_symbols = [source_symbols] if isinstance(source_symbols, str) else source_symbols
        orbits = []
        volume_ratio = abs(np.linalg.det(data.std_lattice))/atoms.cell.volume
        for representative in sorted(set(map(int, data.equivalent_atoms))):
            indices = np.flatnonzero(data.equivalent_atoms == representative).tolist()
            element = symbols[indices[0]]
            if any(symbols[i] != element for i in indices):
                raise ValueError('A symmetry orbit mixes chemical species')
            orbit_labels = []
            if labels and kinds is not None:
                for i in indices:
                    k = int(kinds[i])
                    if k < 0 or k >= len(labels) or (source_symbols and
                            (k >= len(source_symbols) or source_symbols[k] != element)):
                        result['warnings'].append('CIF labels could not be validated against the imported species; labels ignored.')
                        orbit_labels = [];break
                    orbit_labels.append(str(labels[k]))
            letter = data.wyckoffs[representative]
            orbits.append(dict(element=element, indices=indices, atom_count=len(indices),
                               wyckoff=f'{round(len(indices)*volume_ratio)}{letter}',
                               site_symmetry=data.site_symmetry_symbols[representative],
                               cif_labels=sorted(set(orbit_labels))))
        # Separate orbits with the same element/Wyckoff letter stay separate.
        orbits.sort(key=lambda g:(g['element'], g['wyckoff'][-1], g['indices'][0]))
        for element in dict.fromkeys(g['element'] for g in orbits):
            same = [g for g in orbits if g['element'] == element]
            for n, group in enumerate(same):
                suffix = string.ascii_uppercase[n] if n < 26 else str(n+1)
                group['group_id'] = element if len(same) == 1 else f'{element}({suffix})'
                # A single, unique CIF label is useful, but never defines membership.
                label = group['cif_labels']
                if len(label) == 1 and sum(label[0] in g['cif_labels'] for g in orbits) == 1:
                    group['cif_label'] = label[0]
        result.update(status='ready', groups=orbits)
    except (ImportError, ValueError, TypeError, RuntimeError) as exc:
        result['warnings'].append(str(exc));result['groups'] = []
    return result
