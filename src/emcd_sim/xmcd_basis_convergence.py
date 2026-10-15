"""Matched systematic-row/2D ZOLZ XMCD-effective parity diagnostics."""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import platform
import subprocess

import numpy as np

from .benchmark import nickel_physical_benchmark
from .convergence import _total_variation
from .crystal import fcc_nickel
from .diffraction import select_diffraction_setup
from .elastic import BeamSet
from .wien2k_xmcd import load_wien2k_xmcd
from .xmcd_reversal import run_xmcd_reversal


@dataclass(frozen=True)
class BasisConvergenceConfig:
    g_cutoffs: tuple[float, ...] = (.75, 1.2, 1.4)
    y_tilts_mrad: tuple[float, ...] = (0., 25.)
    acceleration_kv: float = 200.
    thickness_nm: float = 30.
    eta: float = 1.
    beta: float = 1.
    l3_energy_ev: float = 852.7
    l2_energy_ev: float | None = None
    beam_order: int = 3
    max_beams: int = 81
    grid: int = 25
    steps: int = 20

    def validate(self):
        cuts = np.asarray(self.g_cutoffs, dtype=float)
        tilts = np.asarray(self.y_tilts_mrad, dtype=float)
        if (cuts.ndim != 1 or len(cuts) < 2 or not np.isfinite(cuts).all()
                or np.any(cuts <= 0) or np.any(np.diff(cuts) <= 0)):
            raise ValueError('Require at least two positive increasing finite cutoffs')
        if tilts.ndim != 1 or not len(tilts) or not np.isfinite(tilts).all() or len(set(tilts)) != len(tilts):
            raise ValueError('Require nonempty unique finite y tilts')
        for value in (self.acceleration_kv, self.thickness_nm, self.l3_energy_ev):
            if not np.isfinite(value) or value <= 0:
                raise ValueError('Voltage, thickness and edge energy must be finite positive')
        if self.l2_energy_ev is not None and (not np.isfinite(self.l2_energy_ev) or self.l2_energy_ev <= 0):
            raise ValueError('L2 energy must be finite positive')
        if not np.isfinite(self.eta) or not np.isfinite(self.beta) or self.beta < 0:
            raise ValueError('Require finite eta and nonnegative finite beta')
        if any(not isinstance(v, int) for v in (self.beam_order, self.max_beams, self.grid, self.steps)):
            raise ValueError('Beam, grid and depth controls must be integers')
        if self.beam_order < 1 or self.max_beams < 3 or self.grid < 9 or self.steps < 2:
            raise ValueError('Require beam order >=1, max beams >=3, grid >=9, steps >=2')


def selected_energy_grid(source_energy, references):
    """Nearest source samples, with one adjacent support point if necessary."""
    if any(not source_energy[0] <= e <= source_energy[-1] for e in references.values()):
        raise ValueError('Source must cover requested reference energies; no extrapolation')
    selected = {k: float(source_energy[np.argmin(abs(source_energy-v))])
                for k, v in references.items()}
    energies = sorted(set(selected.values()))
    if len(energies) == 1:
        i = int(np.searchsorted(source_energy, energies[0]))
        energies.append(float(source_energy[i+1 if i+1 < len(source_energy) else i-1]))
    return np.asarray(sorted(energies)), selected


def run_basis_convergence(xmcd_file, config=BasisConvergenceConfig()):
    """Return matched-basis records and provenance, without plotting or writes.

    Largest ZOLZ basis is a finite comparison, not a convergence certificate.
    Systematic row is a separate approximation, not part of a nested sequence.
    """
    config.validate()
    source = load_wien2k_xmcd(xmcd_file)
    refs = {'L3': config.l3_energy_ev}
    if config.l2_energy_ev is not None:
        refs['L2'] = config.l2_energy_ev
    energies, selected = selected_energy_grid(source.energy_ev, refs)
    crystal = fcc_nickel()
    preset = select_diffraction_setup('near-2bc', crystal, config.acceleration_kv)
    tx = preset.tilt_mrad_xy[0]
    bases = [('systematic-row', None, BeamSet.systematic_row(config.beam_order))]
    for cutoff in config.g_cutoffs:
        beams = BeamSet.zolz(crystal, cutoff, config.max_beams)
        # Detect clipping even when pair selection stops below an even cap.
        larger = BeamSet.zolz(crystal, cutoff, config.max_beams+2)
        if beams.hkl != larger.hkl:
            raise ValueError('max_beams truncates a cutoff basis; increase --max-beams')
        if not any(h[1] != 0 for h in beams.hkl):
            raise ValueError('Each 2D basis must include off-row reflections')
        bases.append(('2d-zolz', cutoff, beams))
    if bases[1][2].hkl == bases[-1][2].hkl:
        raise ValueError('All ZOLZ cutoffs select the same basis; widen the range')
    records, basis_metadata = [], []
    for ib, (kind, cutoff, beams) in enumerate(bases):
        base_model = nickel_physical_benchmark(tilt_mrad_xy=(tx, 0.),
            acceleration_kv=config.acceleration_kv, beams_override=beams,
            diffraction_condition='near-2bc')
        h0 = base_model.elastic.hamiltonian_nm_inv()
        basis_metadata.append(dict(basis_index=ib, basis_kind=kind, cutoff_inv_angstrom=cutoff,
                                   beam_count=len(beams.hkl), beam_hkl=beams.hkl))
        for ty in config.y_tilts_mrad:
            model = nickel_physical_benchmark(tilt_mrad_xy=(tx, ty),
                acceleration_kv=config.acceleration_kv, beams_override=beams,
                diffraction_condition='near-2bc')
            elastic = abs(model.elastic.amplitudes(np.array([config.thickness_nm]))[0])**2
            parity = run_xmcd_reversal(model, xmcd_file, energies, eta=config.eta,
                beta=config.beta, thickness_nm=config.thickness_nm, grid_size=config.grid,
                depth_steps=config.steps, l3_energy_ev=selected['L3'],
                l2_energy_ev=selected.get('L2', selected['L3']))
            indices = {h: i for i, h in enumerate(beams.hkl)}
            for edge, energy in selected.items():
                i = int(np.argmin(abs(energies-energy)))
                record = dict(basis_index=ib, basis_kind=kind,
                    cutoff_inv_angstrom=cutoff, beam_count=len(beams.hkl),
                    condition='near-2bc', tilt_x_mrad=tx, tilt_y_mrad=ty,
                    thickness_nm=config.thickness_nm, acceleration_kv=config.acceleration_kv,
                    eta=config.eta, beta=config.beta, grid=config.grid, steps=config.steps,
                    edge=edge, energy_ev=energy, beam_hkl=beams.hkl,
                    elastic_intensity=elastic.tolist(), total_elastic=float(elastic.sum()),
                    hamiltonian_change_vs_y0=float(np.max(abs(model.elastic.hamiltonian_nm_inv()-h0))))
                for key, hkl in [('elastic_000',(0,0,0)), ('elastic_200',(2,0,0)),
                                 ('elastic_m200',(-2,0,0)), ('elastic_020',(0,2,0))]:
                    # Missing selected reflections are explicit, not interpreted as zero.
                    record[key] = float(elastic[indices[hkl]]) if hkl in indices else np.nan
                for key, value in parity.spectra.items():
                    if key != 'energy_ev':
                        record[key] = value[i].item()
                records.append(record)
    for record in records:
        peers = [r for r in records if r['edge'] == record['edge']
                 and r['tilt_y_mrad'] == record['tilt_y_mrad']]
        references = {'largest': peers[-1], 'row': peers[0],
                      'previous': next((r for r in peers if r['basis_index'] == record['basis_index']-1), None)
                                  if record['basis_index'] > 1 else None}
        for name, reference in references.items():
            for key in ('A_raw_plus', 'A_raw_minus', 'A_odd', 'A_even',
                        'elastic_000', 'elastic_200', 'elastic_m200', 'elastic_020'):
                record[f'{key}_abs_diff_{name}'] = (abs(record[key]-reference[key])
                                                     if reference else np.nan)
            record[f'elastic_tv_{name}'] = (_total_variation(reference['beam_hkl'],
                reference['elastic_intensity'], record['beam_hkl'], record['elastic_intensity'])
                if reference else np.nan)
    try:
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'],
            cwd=Path(__file__).resolve().parents[2], stderr=subprocess.DEVNULL).decode().strip()
    except (OSError, subprocess.CalledProcessError):
        commit = None
    metadata = dict(config=asdict(config), xmcd_file=str(Path(xmcd_file).resolve()),
        xmcd_sha256=source.source_sha256, source_peak_N=float(source.nonmagnetic.max()),
        energy_grid_ev=energies.tolist(), selected_energies_ev=selected, requested_energies_ev=refs,
        bases=basis_metadata, condition='near-2bc', tilt_x_mrad=tx,
        detectors={k: dict(center_q_xy=v.center_q_xy, radius_q=v.radius_q)
                   for k,v in base_model.detectors.items()}, chiral_groups=base_model.chiral_groups,
        reciprocal_coordinate_units='cycles/angstrom', map_halfwidth_q=1.,
        model='XMCD-effective; entrance-only; relative intensity; not quantitatively validated Ni EMCD',
        elastic_potential='Existing Ni independent-atom physical potential; B=0 angstrom^2',
        reversal='eta -> -eta; diagonals unchanged; shared source peak N normalization',
        denominator_policy='Inherited parity_spectra: NaN and validity mask at <=1e-12 peak denominator',
        comparison='previous: successive ZOLZ only; largest: last ZOLZ; row: systematic row at same tilt/energy',
        missing_reflections='Selected elastic intensity is NaN if absent; elastic TV treats absent beams as zero',
        hamiltonian_check='max absolute element change vs y=0 at fixed x and identical basis (nm^-1)',
        reference_is_finite_not_validated=True, absolute_cross_section=False,
        outgoing_channeling=False, quantitative_Ni=False,
        software_commit=commit, python_version=platform.python_version())
    return records, metadata


def save_basis_convergence(records, metadata, output):
    """Write flat records with JSON basis vectors in CSV, padded arrays in NPZ."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    vectors = ('beam_hkl', 'elastic_intensity')
    scalars = [key for key in records[0] if key not in vectors]
    with (output/'convergence_results.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=scalars+['beam_hkl_json', 'elastic_intensity_json'])
        writer.writeheader()
        for record in records:
            writer.writerow({**{k: record[k] for k in scalars},
                'beam_hkl_json':json.dumps(record['beam_hkl']),
                'elastic_intensity_json':json.dumps(record['elastic_intensity'])})
    max_n = max(r['beam_count'] for r in records)
    hkl = np.zeros((len(records), max_n, 3), dtype=int)
    intensity = np.full((len(records), max_n), np.nan)
    mask = np.zeros((len(records), max_n), dtype=bool)
    for i, r in enumerate(records):
        n = r['beam_count']
        hkl[i,:n], intensity[i,:n], mask[i,:n] = r['beam_hkl'], r['elastic_intensity'], True
    arrays = {k: np.asarray([np.nan if r[k] is None else r[k] for r in records]) for k in scalars}
    np.savez_compressed(output/'convergence_results.npz', **arrays,
                       beam_hkl=hkl, elastic_intensity=intensity, beam_valid=mask)
    (output/'convergence_metadata.json').write_text(json.dumps(metadata, indent=2)+'\n', encoding='utf-8')
    plot_basis_convergence(records, metadata, output/'basis_parity_comparison.png')


def plot_basis_convergence(records, metadata, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    edges = list(metadata['selected_energies_ev'])
    fig, axes = plt.subplots(len(edges), 3, figsize=(13, 4*len(edges)),
                             squeeze=False, constrained_layout=True)
    for row, edge in enumerate(edges):
        for col, key in enumerate(('A_odd', 'A_even', 'A_raw_plus')):
            ax = axes[row,col]
            for ty in metadata['config']['y_tilts_mrad']:
                peers = [r for r in records if r['edge']==edge and r['tilt_y_mrad']==ty]
                color = ax.plot([r['beam_count'] for r in peers[1:]],
                    [r[key] for r in peers[1:]], 'o-', label=f'2D ZOLZ, y={ty:g} mrad')[0].get_color()
                ax.scatter(peers[0]['beam_count'], peers[0][key], color=color, marker='x',
                           s=65, label=f'Row, y={ty:g} mrad')
            ax.set(xlabel='Beam count (row is a separate approximation)', ylabel=key,
                   title=f'{edge}: {metadata["selected_energies_ev"][edge]:.4f} eV')
            ax.ticklabel_format(axis='y', style='sci', scilimits=(-3,3))
            ax.grid(alpha=.25)
            ax.legend(fontsize=8)
    fig.suptitle('XMCD-effective | entrance-only | relative intensity\n'
                 'Not quantitatively validated Ni EMCD; largest finite basis is not a convergence certificate')
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--xmcd-file', type=Path, required=True)
    p.add_argument('--output', type=Path, default=Path('outputs/ni_xmcd_basis_convergence'))
    p.add_argument('--g-cutoffs', type=float, nargs='+', default=[.75, 1.2, 1.4])
    p.add_argument('--y-tilts-mrad', type=float, nargs='+', default=[0.,25.])
    for key, default in [('acceleration-kv',200.), ('thickness-nm',30.), ('eta',1.),
                         ('beta',1.), ('l3-energy-ev',852.7)]:
        p.add_argument('--'+key, type=float, default=default)
    p.add_argument('--l2-energy-ev', type=float, help='Include this L2 reference (e.g. 870)')
    for key, default in [('beam-order',3), ('max-beams',81), ('grid',25), ('steps',20)]:
        p.add_argument('--'+key, type=int, default=default)
    args = p.parse_args(argv)
    settings = vars(args).copy()
    output, source = settings.pop('output'), settings.pop('xmcd_file')
    settings['g_cutoffs'], settings['y_tilts_mrad'] = tuple(args.g_cutoffs), tuple(args.y_tilts_mrad)
    try:
        records, metadata = run_basis_convergence(source, BasisConvergenceConfig(**settings))
    except ValueError as exc:
        p.error(str(exc))
    save_basis_convergence(records, metadata, output)
    for r in records:
        print(json.dumps({k: (None if isinstance(r[k], float) and not np.isfinite(r[k]) else r[k])
                          for k in ('basis_kind', 'beam_count', 'tilt_y_mrad', 'edge',
                                    'energy_ev', 'A_raw_plus', 'A_odd', 'A_even')}))
    print(f'Output: {output}; largest basis is a finite comparison, not verified convergence.')


if __name__ == '__main__':
    main()
