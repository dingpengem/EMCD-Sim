"""Fixed-energy Ni [017] thickness study; reuse existing engines, no GUI changes.

Run from the repository root with the emcd-python environment. Outputs are
new files only. The saved project defines the matched numerical configuration.
"""
import argparse
import csv
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import time

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

from emcd_sim.gui.project_io import load_project
from emcd_sim.gui.geometry import Structure, elastic_model, geometry
from emcd_sim.gui.emcd_forward import tensors, energy_grid
from emcd_sim.gui.propagation import propagate, numerical_info
from emcd_sim.gui.prb_benchmark import benchmark_spectra, DEFINITION, LIMITATION
from emcd_sim.multislice_emcd_reference import coherence_from_amplitudes
from emcd_sim.single_channeling_tensor import run_tensor_with_coherence
from emcd_sim.diffraction import excitation_errors_angstrom_inv
from emcd_sim.wien2k_xmcd import load_wien2k_xmcd
from emcd_sim.benchmark import nickel_physical_benchmark
from emcd_sim.geometry import VirtualDetector
from emcd_sim.gui.memory_budget import BUDGETS_MIB, DEFAULT_BUDGET_MIB, reserve_memory

ENERGIES = np.array([831.4778, 848.698])
EDGES = ('L3', 'L2')
METHODS = ('bloch', 'fft-multislice')
METRICS = ('prb_relative_dichroism_percent', 'magnetic_only_percent', 'nonmagnetic_imbalance_percent')


def thickness_sequence():
    return np.arange(0., 101., 2.)


def observables(raw):
    """raw shape (energy, A+, B+, A-, B-); retain original intensities."""
    ap, bp, am, bm = np.asarray(raw, float).T
    curves, _ = benchmark_spectra(dict(I_A_plus=ap, I_B_plus=bp, I_A_minus=am, I_B_minus=bm))
    na, nb, ma, mb = (ap+am)/2, (bp+bm)/2, (ap-am)/2, (bp-bm)/2
    assert np.allclose(ap-bp, (ma-mb)+(na-nb), rtol=1e-10, atol=1e-13*max(float(abs(raw).max()), 1e-30))
    return dict(curves, I_A_plus=ap, I_B_plus=bp, I_A_minus=am, I_B_minus=bm,
                N_A=na, N_B=nb, M_A=ma, M_B=mb,
                raw_denominator=ap+bp, diagnostic_denominator=na+nb,
                D_raw=ap-bp, D_mag=ma-mb, D_even=na-nb)


def write_csv(path, rows):
    with Path(path).open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def clean(value):
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (tuple, list, np.ndarray)):
        return [clean(v) for v in value]
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, np.integer):
        return int(value)
    return value


def write_json(path, value):
    Path(path).write_text(json.dumps(clean(value), indent=2, allow_nan=False)+'\n', encoding='utf-8')


def file_hashes(folder):
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(folder).rglob('*') if p.is_file()}


def calculate_case(t, elastic, settings, cfg, model, ts):
    info = numerical_info(Structure.nickel(), replace(settings, thickness=max(float(t), 1.)), cfg, hkl=elastic.beams.hkl)
    with reserve_memory(info['estimated_working_mib'], cfg.memory_budget_mib, dense_mib=info['dense_working_estimate_mib']) as admission:
        case, fft = _calculate_case(t, elastic, settings, cfg, model, ts)
        fft['memory_admission'] = admission
        return case, fft


def _calculate_case(t, elastic, settings, cfg, model, ts):
    if t == 0:
        psi = np.zeros((cfg.depth, len(elastic.beams.hkl)), complex)
        psi[:, elastic.beams.hkl.index((0, 0, 0))] = 1
        return {m: dict(raw=np.zeros((2, 4)), amplitudes=psi, coherence=psi[0, :, None]*psi[0].conj(),
                       actual_thickness_nm=0.) for m in METHODS}, {}
    local = replace(settings, thickness=float(t))
    z = np.linspace(0, t, cfg.depth)
    waves, fft = propagate(elastic, local, cfg, z, lambda _: None)
    result = {}
    for method, psi in waves.items():
        C = coherence_from_amplitudes(z, psi)
        integrals = [run_tensor_with_coherence(model, tensor, C, thickness_nm=float(t),
            grid_size=cfg.grid, map_halfwidth_q=cfg.halfwidth, reference_energy_ev=ENERGIES[0],
            integration_mode='fractional', aperture_subpixels=cfg.subpixels) for tensor in ts]
        raw = np.stack([r.chiral_spectrum(d) for r in integrals for d in ('A', 'B')], axis=1)
        assert np.all(raw >= 0)
        result[method] = dict(raw=raw, amplitudes=psi, coherence=C, actual_thickness_nm=float(z[-1]),
                              weights=np.stack(list(integrals[0].detector_weights.values())))
    return result, fft


def checkpoint_case(root, t, case, fft):
    """Persist one point, returning only small independent arrays, no waves/C."""
    compact = {m: dict(raw=data['raw'].copy(), exit_intensity=abs(data['amplitudes'][-1])**2,
        depth_average_intensity=np.diag(data['coherence']).real.copy(),
        actual_thickness_nm=data['actual_thickness_nm']) for m, data in case.items()}
    arrays = {m+'__'+k: v for m, data in compact.items() for k, v in data.items()}
    if 'exit_intensity' in fft:
        arrays.update(fft_full_exit_intensity=fft['exit_intensity'], fft_full_hkl=fft['beam_hkl'])
    np.savez_compressed(root/'checkpoints'/f't{int(t):03d}.npz', **arrays)
    return compact


def save_figures(root, tgrid, values, difference):
    for number, key, ie, title in [(1, METRICS[0], 0, 'L3 raw PRB relative dichroism'),
            (2, METRICS[1], 0, 'L3 magnetic-only asymmetry (diagnostic)'),
            (3, METRICS[2], 0, 'L3 nonmagnetic imbalance (diagnostic)'),
            (4, METRICS[0], 1, 'L2 raw PRB relative dichroism')]:
        fig = Figure(figsize=(8, 5), layout='constrained'); FigureCanvasAgg(fig)
        ax = fig.subplots()
        for m, label in zip(METHODS, ('Bloch wave', 'FFT multislice')):
            ax.plot(tgrid, values[m][key][:, ie], marker='o' if m == 'bloch' else '.', ms=3, lw=1, label=label)
        ax.axhline(0, color='.5', lw=.7)
        ax.set(xlim=(0, 100), xlabel='Requested = actual thickness (nm)', ylabel='Signed percent (%)',
            title=title+f'\nNi [017], (200) Bragg, 200 kV; fixed {ENERGIES[ie]:.4f} eV')
        ax.grid(alpha=.2); ax.legend()
        for ext in ('png', 'svg'):
            fig.savefig(root/f'figure_{number}.{ext}', dpi=180)
    fig = Figure(figsize=(8, 8), layout='constrained'); FigureCanvasAgg(fig)
    for ie, ax in enumerate(fig.subplots(2, 1, sharex=True)):
        for key, label in zip(METRICS, ('Raw PRB', 'Magnetic-only', 'Even imbalance')):
            ax.plot(tgrid, difference[key][:, ie], '.-', ms=3, lw=1, label=label)
        ax.axhline(0, color='.5', lw=.7)
        ax.set(xlim=(0, 100), ylabel='BW - MS (percentage points)', title=f'{EDGES[ie]}: fixed {ENERGIES[ie]:.4f} eV')
        ax.grid(alpha=.2); ax.legend()
    ax.set_xlabel('Requested = actual thickness (nm)')
    for ext in ('png', 'svg'):
        fig.savefig(root/f'figure_5.{ext}', dpi=180)


def depth_control(root, elastic, settings, cfg, model, ts):
    """One high-thickness quadrature check; production settings stay fixed."""
    rows = []
    for depth in (128, 256):
        cases, _ = calculate_case(100., elastic, settings, replace(cfg, depth=depth), model, ts)
        for method, data in cases.items():
            obs = observables(data['raw'])
            for ie, edge in enumerate(EDGES):
                rows.append(dict(thickness_nm=100., depth_nodes=depth, method=method,
                    edge=edge, energy_ev=ENERGIES[ie], **{k: obs[k][ie] for k in METRICS}))
        del data, cases
    write_csv(root/'depth_quadrature_control.csv', rows)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path('outputs/gui_stage_d/windows_20261016/reference_project'))
    parser.add_argument('--output', type=Path, default=Path('outputs/ni_017_thickness_0_100nm'))
    parser.add_argument('--memory-budget-mib', type=int, choices=BUDGETS_MIB, default=DEFAULT_BUDGET_MIB)
    args = parser.parse_args()
    root = args.output
    root.mkdir(parents=True, exist_ok=False)
    (root/'checkpoints').mkdir()
    started = time.perf_counter()
    original_files = file_hashes(args.project)
    saved = load_project(args.project)
    cfg, settings = replace(saved['config'], memory_budget_mib=args.memory_budget_mib), saved['settings']
    assert tuple(settings.zone) == (0, 1, 7) and tuple(settings.target) == (2, 0, 0)
    assert cfg.model == 'xmcd' and cfg.eta == cfg.beta == 1 and cfg.propagation == 'both'
    assert np.allclose(cfg.centers, [[.283768445, .283768445], [.283768445, -.283768445]], atol=1e-9, rtol=0)
    assert cfg.radius == .0908059024
    source = load_wien2k_xmcd(cfg.source)
    assert source.source_sha256 == cfg.source_sha256
    # Evaluation at exact samples in the saved GUI energy grid, interpolated
    # from the unchanged native source by the existing tensor builder.
    saved_energy = energy_grid(cfg)
    assert all(np.min(abs(saved_energy-e)) < 1e-8 for e in ENERGIES)
    structure = Structure.nickel()
    elastic = elastic_model(structure, settings)
    _, R, hkl, g, _ = geometry(structure, settings)
    assert hkl == elastic.beams.hkl
    np.testing.assert_array_equal(np.asarray(hkl), saved['metadata']['beam_hkl'])
    np.testing.assert_allclose(g, saved['metadata']['g'], atol=1e-14, rtol=0)
    model = replace(nickel_physical_benchmark(), elastic=elastic,
        detectors={d: VirtualDetector(tuple(p), cfg.radius) for d, p in zip(('A', 'B'), cfg.centers)}, chiral_groups=None)
    info = numerical_info(structure, settings, cfg, hkl=hkl)
    ts = tensors(cfg, ENERGIES, R)  # once for all thicknesses, reversals in crystal frame
    errors = excitation_errors_angstrom_inv(elastic)
    assert abs(errors[hkl.index((2, 0, 0))]) < 1e-10
    metadata = dict(configuration=asdict(cfg), diffraction_settings=asdict(settings),
        thickness_nm=thickness_sequence(), fixed_energies_ev=ENERGIES, edges=EDGES,
        native_energy_note='Exact saved GUI samples; existing interpolation of unshifted WIEN2k source. L3 summed-detector peak at saved 30 nm, L2 native saved magnetic feature; no peak tracking.',
        source_sha256=source.source_sha256, saved_project=str(args.project), saved_calculation_commit=saved['metadata'].get('software_commit'),
        study_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        study_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        python=platform.python_version(), numpy=np.__version__, numerics=info,
        streaming='One thickness at a time; checkpoint/flush compact raw states and elastic populations, then release wavefields, coherences and FFT intermediates. No full-series intermediate arrays retained.',
        frame=R, magnetization_crystal=cfg.magnetization, magnetization_local=R@cfg.magnetization,
        beam_hkl=hkl, g_cycles_per_angstrom=g, excitation_errors_inv_angstrom=errors,
        primary_definition=DEFINITION, diagnostic_definitions=dict(magnetic='100*(M_A-M_B)/(N_A+N_B)', even='100*(N_A-N_B)/(N_A+N_B)'),
        integration='fractional', post_edge_correction_applied=False,
        potential_representation='Projected 2D IAM (matched saved result), not the newer atomic-3D model',
        thickness_convention='64 equally spaced depth nodes per requested positive thickness; FFT substeps <=0.04 nm reach each node exactly; no unit-cell rounding',
        limitation=LIMITATION, further_limitations='Fixed finite basis/potential cutoff and detector/depth sampling; numerical method agreement is not physical convergence. Native energies uncalibrated; arbitrary intensity units, no absolute cross section.')
    write_json(root/'configuration.json', metadata)
    cases, admissions = {}, []
    fft_max_norm_error = fft_max_excluded_population = 0.
    # Representative checks precede the remaining production sequence.
    order = [10., 30., 100.] + [float(t) for t in thickness_sequence() if t not in (10., 30., 100.)]
    weights = None
    reference_check = []
    for t in order:
        case, fft = calculate_case(t, elastic, settings, cfg, model, ts)
        for m, data in case.items():
            observables(data['raw'])
            if t > 0:
                if weights is None:
                    weights = data['weights'].copy()
                assert np.array_equal(weights, data['weights'])
            if t == 30:
                sp = saved['methods'][m]['spectra']
                selected = np.array([np.argmin(abs(sp['energy_ev']-e)) for e in ENERGIES])
                reference = np.stack([sp[k][selected] for k in ('I_A_plus', 'I_B_plus', 'I_A_minus', 'I_B_minus')], axis=1)
                np.testing.assert_allclose(data['raw'], reference, rtol=1e-9, atol=1e-13)
                reference_check.append(dict(method=m, raw_max_abs_difference=float(abs(data['raw']-reference).max()),
                    l3_prb_percent=observables(data['raw'])[METRICS[0]][0]))
        cases[t] = checkpoint_case(root, t, case, fft)
        admissions.append(dict(thickness_nm=t, **fft['memory_admission']))
        if 'summary' in fft:
            fft_max_norm_error = max(fft_max_norm_error, fft['summary']['norm_error'])
            fft_max_excluded_population = max(fft_max_excluded_population, fft['summary']['max_excluded_population'])
        incremental = [dict(thickness_nm=t, method=m, edge=edge, energy_ev=ENERGIES[ie],
            **{key: value[ie] for key, value in observables(data['raw']).items()}) for m, data in case.items() for ie, edge in enumerate(EDGES)]
        with (root/'completed_points.csv').open('a', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, list(incremental[0]))
            if f.tell() == 0:writer.writeheader()
            writer.writerows(incremental)
        del data, case, fft, incremental
        print(f'{t:5.1f} nm complete ({time.perf_counter()-started:.1f} s)', flush=True)
    tgrid = thickness_sequence()
    rows, beams, arrays, values = [], [], {}, {}
    q = np.linspace(-cfg.halfwidth, cfg.halfwidth, cfg.grid)
    area = weights.sum(axis=(1, 2))*(q[1]-q[0])**2
    metadata['detector_areas_inv_angstrom2'] = area
    for m in METHODS:
        raw = np.stack([cases[t][m]['raw'] for t in tgrid])
        values[m] = {key: np.stack([observables(r)[key] for r in raw]) for key in observables(raw[0])}
        arrays.update({m+'__'+key: value for key, value in values[m].items()})
        arrays[m+'__exit_intensity'] = np.stack([cases[t][m]['exit_intensity'] for t in tgrid])
        arrays[m+'__depth_average_intensity'] = np.stack([cases[t][m]['depth_average_intensity'] for t in tgrid])
        arrays[m+'__actual_thickness_nm'] = np.array([cases[t][m]['actual_thickness_nm'] for t in tgrid])
        for it, t in enumerate(tgrid):
            for ie, edge in enumerate(EDGES):
                rows.append(dict(requested_thickness_nm=t, actual_thickness_nm=t, method=m, edge=edge,
                    energy_ev=ENERGIES[ie], electron_energy_kv=settings.voltage,
                    **{k: v[it, ie] for k, v in values[m].items()}))
            pop = cases[t][m]['exit_intensity']
            avg = cases[t][m]['depth_average_intensity']
            for j, h in enumerate(hkl):
                beams.append(dict(thickness_nm=t, method=m, h=h[0], k=h[1], l=h[2],
                    excitation_error_inv_angstrom=errors[j], exit_incident_fraction=pop[j],
                    exit_retained_fraction=pop[j]/pop.sum(), depth_average_incident_fraction=avg[j]))
    difference = {key: values[METHODS[0]][key]-values[METHODS[1]][key] for key in METRICS}
    arrays.update({'bw_minus_ms__'+key: v for key, v in difference.items()})
    arrays.update(requested_thickness_nm=tgrid, fixed_energies_ev=ENERGIES, beam_hkl=np.asarray(hkl),
        excitation_errors_inv_angstrom=errors, weights=weights, detector_centers=np.asarray(cfg.centers))
    metadata['reference_30nm_check'] = reference_check
    metadata['original_project_files_unchanged'] = file_hashes(args.project) == original_files
    assert metadata['original_project_files_unchanged']
    metadata['source_unchanged'] = load_wien2k_xmcd(cfg.source).source_sha256 == source.source_sha256
    assert metadata['source_unchanged']
    metadata['fft_max_norm_error'] = fft_max_norm_error
    metadata['fft_max_excluded_population'] = fft_max_excluded_population
    metadata['memory_admissions'] = admissions
    metadata['depth_quadrature_control'] = depth_control(root, elastic, settings, cfg, model, ts)
    metadata['runtime_seconds'] = time.perf_counter()-started
    write_json(root/'configuration.json', metadata)
    np.savez_compressed(root/'thickness_series.npz', **arrays, configuration_json=np.array(json.dumps(clean(metadata), allow_nan=False)))
    write_csv(root/'thickness_series.csv', rows)
    write_csv(root/'elastic_beams.csv', beams)
    comparisons = [dict(thickness_nm=t, edge=edge, energy_ev=ENERGIES[ie],
        **{m+'__'+key: values[m][key][it, ie] for m in METHODS for key in METRICS},
        **{'bw_minus_ms__'+key: v[it, ie] for key, v in difference.items()}) for it, t in enumerate(tgrid) for ie, edge in enumerate(EDGES)]
    write_csv(root/'bw_ms_comparison.csv', comparisons)
    save_figures(root, tgrid, values, difference)
    summary = {}
    for m in METHODS:
        y = values[m][METRICS[0]][:, 0]
        ix = int(np.nanargmax(abs(y)))
        summary[m] = dict(max_abs_l3_prb_percent=abs(y[ix]), signed_l3_prb_percent=y[ix], thickness_nm=tgrid[ix],
            corresponding_magnetic_only_percent=values[m][METRICS[1]][ix, 0],
            sign_change_brackets_nm=[[tgrid[i-1], tgrid[i]] for i in range(2, len(y)) if y[i-1]*y[i] < 0],
            selected_thicknesses=[r for r in rows if r['method'] == m and r['edge'] == 'L3' and r['requested_thickness_nm'] in (10, 20, 30, 50, 100)])
    summary['max_abs_bw_minus_ms_percentage_points'] = {key: np.nanmax(abs(v), axis=0) for key, v in difference.items()}
    pair = [hkl.index(h) for h in ((0, 0, 0), (2, 0, 0))]
    summary['two_beam_assessment'] = {m: dict(min_pair_exit_fraction=float(arrays[m+'__exit_intensity'][:, pair].sum(axis=1).min()),
        min_pair_depth_average_fraction=float(arrays[m+'__depth_average_intensity'][:, pair].sum(axis=1).min())) for m in METHODS}
    write_json(root/'summary.json', summary)
    print(json.dumps(clean(summary), indent=2), flush=True)


if __name__ == '__main__':
    main()
