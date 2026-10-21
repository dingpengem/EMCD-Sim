"""Export P1 Ni structural diagnostics; no potentials or waves are calculated.

python scripts/research/atomic_slicing_diagnostics.py --output outputs/ni_017_atomic_3d
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import subprocess

import numpy as np
from ase.build import bulk
from ase.io import write

from emcd_sim import atomic_multislice_geometry as geometry


def _csv(path, header, rows):
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def export_diagnostics(output, *, zone_axis=(0, 1, 7), lattice_angstrom=3.524,
                       thickness_nm=30., max_slice_thickness_angstrom=.5):
    cell = geometry.oriented_atomic_cell(bulk('Ni', 'fcc', a=lattice_angstrom, cubic=True), zone_axis)
    planes = geometry.atomic_planes(cell)
    slab = geometry.specimen_positions(cell, 10*thickness_nm)
    slices = {mode: geometry.slice_geometry(cell, 10*thickness_nm, mode=mode,
              max_slice_thickness_angstrom=max_slice_thickness_angstrom) for mode in ('uniform', 'plane-aware')}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    write(output/'crystal_oriented.cif', cell.atoms)
    symbols = cell.atoms.get_chemical_symbols()
    _csv(output/'atomic_positions.csv', ['atom_index', 'species', 'x_local_angstrom', 'y_local_angstrom', 'z_local_angstrom', 'plane_index'],
         ((i, s, *p, int(planes.atom_plane_index[i])) for i, (s, p) in enumerate(zip(symbols, cell.atoms.positions))))
    _csv(output/'atomic_depths.csv', ['plane_index', 'z_angstrom', 'atom_count', 'species', 'next_spacing_angstrom', 'period_angstrom'],
         ((i, z, int(n), '+'.join(s), gap, cell.period_angstrom) for i, (z, n, s, gap) in enumerate(
             zip(planes.depths_angstrom, planes.counts, planes.species, planes.next_spacing_angstrom))))
    _csv(output/'specimen_atomic_positions.csv', ['atom_index', 'species', 'x_local_angstrom', 'y_local_angstrom', 'z_local_angstrom'],
         ((i, s, *p) for i, (s, p) in enumerate(zip(slab.get_chemical_symbols(), slab.positions))))
    rows = []
    arrays = dict(orientation_matrix=cell.frame, translations_input=cell.translations_input,
                  primitive_basis_input=cell.primitive_basis_input, integer_supercell_matrix=cell.integer_supercell_matrix,
                  cell_angstrom=cell.atoms.cell.array, atomic_numbers=cell.atoms.numbers,
                  positions_angstrom=cell.atoms.positions, plane_depths_angstrom=planes.depths_angstrom,
                  plane_counts=planes.counts, atom_plane_index=planes.atom_plane_index,
                  specimen_positions_angstrom=slab.positions, specimen_atomic_numbers=slab.numbers)
    summaries = {}
    for mode, result in slices.items():
        edges = result.boundaries_angstrom
        ids = geometry.assign_atoms_to_slices(slab.positions[:, 2], edges)
        counts = np.bincount(ids, minlength=len(edges)-1)
        rows.extend((mode, i, int(period), int(parent), lo, hi, hi-lo, int(n))
                    for i, (lo, hi, period, parent, n) in enumerate(zip(edges[:-1], edges[1:], result.period_index, result.parent_index, counts)))
        key = mode.replace('-', '_')
        arrays[key+'_boundaries_angstrom'] = edges
        arrays[key+'_repeat_boundaries_angstrom'] = result.repeat_boundaries_angstrom
        arrays[key+'_parent_boundaries_angstrom'] = result.parent_boundaries_angstrom
        arrays[key+'_period_index'] = result.period_index
        arrays[key+'_parent_index'] = result.parent_index
        arrays[key+'_atom_center_counts'] = counts
        summaries[mode] = dict(slices_per_full_repeat=len(result.repeat_boundaries_angstrom)-1,
            specimen_slice_count=len(edges)-1, min_thickness_angstrom=float(np.min(np.diff(edges))),
            max_thickness_angstrom=float(np.max(np.diff(edges))), final_thickness_angstrom=float(edges[-1]-edges[-2]),
            repeat_thicknesses_angstrom=np.diff(result.repeat_boundaries_angstrom).tolist(),
            empty_center_intervals=int(np.sum(counts == 0)), all_centres_assigned_once=int(counts.sum()) == len(slab))
    _csv(output/'slice_boundaries.csv', ['mode', 'slice_index', 'period_index', 'parent_index', 'start_angstrom', 'end_angstrom', 'thickness_angstrom', 'atom_center_count'], rows)
    np.savez_compressed(output/'geometry_arrays.npz', **arrays)
    _plots(output, cell, planes, slices, thickness_nm)
    try:
        root = Path(__file__).resolve().parents[2]
        commit = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
        dirty = bool(subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain'], text=True))
    except (OSError, subprocess.CalledProcessError):
        commit, dirty = 'unknown', None
    meta = dict(milestone='P1: structural geometry and integration boundaries only',
        potential_representation='3D atomic geometry; potential NOT GENERATED; no scattering result',
        generated_utc=datetime.now(timezone.utc).isoformat(), software_commit=commit, source_dirty=dirty,
        implementation_sha256={Path(p).name: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in (geometry.__file__, __file__)},
        versions={name: version(name) for name in ('numpy', 'ase', 'matplotlib')},
        crystal_source='ASE built-in conventional FCC Ni', source_structure_sha256=cell.source_sha256,
        lattice_angstrom=lattice_angstrom, actual_zone_axis=list(cell.zone_axis), orientation_matrix=cell.frame.tolist(),
        translations_in_conventional_lattice=cell.translations_input.tolist(),
        primitive_basis_in_conventional_lattice=cell.primitive_basis_input.tolist(), integer_supercell_matrix=cell.integer_supercell_matrix.tolist(),
        cell_angstrom=cell.atoms.cell.array.tolist(), repeat_length_angstrom=cell.period_angstrom,
        atoms_per_repeat=len(cell.atoms), specimen_atom_count=len(slab), specimen_thickness_nm=thickness_nm,
        full_repeats=int(np.floor(10*thickness_nm/cell.period_angstrom)),
        partial_repeat_angstrom=float(10*thickness_nm % cell.period_angstrom),
        plane_grouping_tolerance_angstrom=planes.tolerance_angstrom, unique_plane_depths_angstrom=planes.depths_angstrom.tolist(),
        next_plane_spacings_angstrom=planes.next_spacing_angstrom.tolist(),
        max_slice_thickness_angstrom=max_slice_thickness_angstrom, slice_modes=summaries,
        slice_boundaries_file='slice_boundaries.csv', numeric_arrays_file='geometry_arrays.npz',
        limits=dict(max_translation_index=256, supercell_max_atoms=100000, specimen_max_atoms=1000000, max_slices=200000),
        exact_translation_policy='Parallelism and orthogonality require floating-point roundoff agreement, capped by geometric tolerance; nearly commensurate cells are rejected, not strained.',
        slicing_policy='Structural-repeat anchored; fixed maximum increments and retained shorter remainder. Plane-aware parents are periodic nearest-plane midpoints, split at repeat boundaries. Final specimen period clipped, never stretched.',
        boundary_policy='Half-open atom centres [start,end); internal-boundary centres belong to right interval. Empty-centre intervals retained. This is NOT finite-potential integration.',
        limitations=['No potential, finite-z integration, transmission, wave propagation, HOLZ calculation or EMCD in P1.',
                     'No strain. Exact commensurate orthogonal translations required within bounded rational search; otherwise capability error.',
                     'Finite atomic potential tails and slab electrostatic boundary conditions remain P2 work; atom-centre assignment must not replace finite integration.',
                     'No slice-thickness, transverse-grid or potential-cutoff physical convergence claim. No GUI or saved-result relabeling.'],
        parameters_not_used=dict(acceleration_voltage='No electron propagation in P1', fft_grid=None, transverse_sampling=None,
                                 atomic_potential_parametrization='Not evaluated', fourier_cutoff=None, projection_method='Not implemented'),
        abtem='Official concepts reviewed; no GPL code copied; no abTEM import, dependency or numerical benchmark in P1')
    meta['output_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file()}
    (output/'metadata.json').write_text(json.dumps(meta, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    return meta


def _plots(output, cell, planes, slices, thickness_nm):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    xyz = cell.atoms.positions
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), layout='constrained')
    im = axes[0].scatter(xyz[:, 0], xyz[:, 1], c=xyz[:, 2], s=30, cmap='viridis', edgecolors='.25', linewidths=.3)
    axes[0].set(xlabel='Local x (Å)', ylabel='Local y (Å)', title='Actual atomic xy positions; colour = z')
    axes[0].set_aspect('equal')
    fig.colorbar(im, ax=axes[0], label='Local z (Å)')
    axes[1].scatter(xyz[:, 2], xyz[:, 1], s=20, c=xyz[:, 0], cmap='plasma')
    axes[1].set(xlabel='Local z (Å)', ylabel='Local y (Å)', title='Side view; colour = local x')
    axes[2].stem(planes.depths_angstrom, planes.counts, markerfmt='.', basefmt=' ')
    axes[2].set(xlabel='Local z (Å)', ylabel='Atoms per nominal plane', title=f'{len(planes.counts)} distinct atomic planes', ylim=(0, 1.3*planes.counts.max()))
    fig.suptitle(f'FCC Ni {list(cell.zone_axis)} | {len(xyz)} atoms | z repeat {cell.period_angstrom:.8f} Å\nP1 structure only: no electrostatic potential or wave calculation')
    fig.savefig(output/'atomic_planes.png', dpi=160)
    plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(12, 7), layout='constrained')
    zoom = min(2., cell.period_angstrom)
    for i, (mode, result) in enumerate(slices.items()):
        b = result.repeat_boundaries_angstrom
        axes[0, 0].vlines(b, i-.25, i+.25, color='C'+str(i), lw=.8)
        axes[0, 1].vlines(b[b <= zoom], i-.25, i+.25, color='C'+str(i), lw=1.2)
        mid = result.parent_boundaries_angstrom
        if mode == 'plane-aware':
            axes[0, 1].plot(mid[mid <= zoom], np.full(np.sum(mid <= zoom), i+.32), 'v', color='C1', ms=4, label='Plane-parent boundaries')
        edges = result.boundaries_angstrom
        end = edges[-1]
        show = edges > max(0, end-1.2*cell.period_angstrom)
        axes[1, 0].vlines(edges[show], i-.25, i+.25, color='C'+str(i), lw=.8)
        widths, counts = np.unique(np.round(np.diff(edges), 10), return_counts=True)
        axes[1, 1].stem(widths, counts, linefmt='C'+str(i)+'-', markerfmt='C'+str(i)+'o', basefmt=' ', label=f'{mode}: {len(edges)-1} intervals')
    axes[0, 1].plot(planes.depths_angstrom[planes.depths_angstrom <= zoom], np.full(np.sum(planes.depths_angstrom <= zoom), 1.), 'k.', ms=4, label='Actual atom planes')
    for ax in (axes[0, 0], axes[0, 1], axes[1, 0]):
        ax.set(yticks=[0, 1], yticklabels=['Uniform', 'Plane-aware'], xlabel='Depth z (Å)')
    axes[0, 0].set_title('One unchanged structural repeat')
    axes[0, 1].set(title='Entrance zoom: centres versus boundaries', xlim=(0, zoom))
    axes[0, 1].legend(fontsize=7)
    axes[1, 0].axvline(10*thickness_nm, color='crimson', ls='--', label='Actual specimen exit')
    axes[1, 0].set_title('Final periods: exit clipped, not rescaled')
    axes[1, 0].legend(fontsize=7)
    axes[1, 1].set(xlabel='Actual interval thickness (Å)', ylabel='Number of intervals', title='Thickness distribution (rounded 1e-10 Å)')
    axes[1, 1].legend(fontsize=8)
    fig.suptitle(f'{thickness_nm:g} nm specimen | max {next(iter(slices.values())).max_slice_thickness_angstrom:g} Å\nIntervals are future integration bounds, not repeated projected potentials')
    fig.savefig(output/'slice_geometry_overview.png', dpi=160)
    plt.close(fig)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=Path('outputs/ni_017_atomic_3d'))
    p.add_argument('--zone', type=int, nargs=3, default=(0, 1, 7))
    p.add_argument('--a', type=float, default=3.524)
    p.add_argument('--thickness-nm', type=float, default=30.)
    p.add_argument('--max-slice-thickness-angstrom', type=float, default=.5)
    a = p.parse_args()
    m = export_diagnostics(a.output, zone_axis=a.zone, lattice_angstrom=a.a, thickness_nm=a.thickness_nm,
                           max_slice_thickness_angstrom=a.max_slice_thickness_angstrom)
    print(json.dumps({k: m[k] for k in ('atoms_per_repeat', 'repeat_length_angstrom', 'specimen_atom_count', 'slice_modes')}, indent=2))


if __name__ == '__main__':
    main()
