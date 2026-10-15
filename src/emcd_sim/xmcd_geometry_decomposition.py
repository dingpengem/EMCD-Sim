"""Diffraction-resolved magnetic/nonmagnetic XMCD-effective diagnostics."""
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
from .crystal import fcc_nickel
from .diffraction import select_diffraction_setup
from .elastic import BeamSet
from .geometry import validate_detector_integration
from .wien2k_xmcd import load_wien2k_xmcd
from .xmcd_basis_convergence import selected_energy_grid
from .xmcd_reversal import CONDITIONS, run_xmcd_reversal

LABEL = ('XMCD-constrained effective MDFF | entrance-only single-channeling | relative intensity\n'
         'Not quantitatively validated Ni EMCD')
A, B = 'A-matched-2d', 'B-truncation-reference'


@dataclass(frozen=True)
class GeometryDecompositionConfig:
    conditions: tuple[str, ...] = CONDITIONS
    cutoff: float = 1.4
    max_beams: int = 81
    acceleration_kv: float = 200.
    thickness_nm: float = 30.
    eta: float = 1.
    beta: float = 1.
    offzone_tilt_mrad: float = 25.
    tilt_x_mrad: float | None = None
    tilt_y_mrad: float | None = None
    l3_energy_ev: float = 852.7
    l2_energy_ev: float | None = None
    grid: int = 65
    steps: int = 64
    finer_grid: int | None = 97
    grid_atol: float = 1e-4
    grid_rtol: float = .05
    integration_mode: str = "binary"
    aperture_subpixels: int = 64

    def validate(self):
        validate_detector_integration(self.integration_mode,self.aperture_subpixels)
        if not self.conditions or len(set(self.conditions)) != len(self.conditions) or any(c not in CONDITIONS for c in self.conditions):
            raise ValueError('Require nonempty unique supported diffraction conditions')
        for value in (self.cutoff, self.acceleration_kv, self.thickness_nm, self.l3_energy_ev):
            if not np.isfinite(value) or value <= 0:
                raise ValueError('Cutoff, voltage, thickness and energy must be finite positive')
        for value in (self.eta, self.beta, self.offzone_tilt_mrad, self.grid_atol, self.grid_rtol):
            if not np.isfinite(value):
                raise ValueError('Model parameters and comparison tolerances must be finite')
        if min(self.beta, self.offzone_tilt_mrad, self.grid_atol, self.grid_rtol) < 0:
            raise ValueError('Require nonnegative beta, offzone tilt and comparison tolerances')
        for value in (self.tilt_x_mrad, self.tilt_y_mrad, self.l2_energy_ev):
            if value is not None and not np.isfinite(value):
                raise ValueError('Optional tilts and L2 energy must be finite')
        if self.l2_energy_ev is not None and self.l2_energy_ev <= 0:
            raise ValueError('L2 energy must be positive')
        if any(not isinstance(v, int) for v in (self.grid, self.steps, self.max_beams)):
            raise ValueError('Grid, depth and beam controls must be integers')
        if self.grid < 9 or self.steps < 2 or self.max_beams < 3:
            raise ValueError('Require grid >=9, steps >=2 and max beams >=3')
        if self.finer_grid is not None and (not isinstance(self.finer_grid, int) or self.finer_grid <= self.grid):
            raise ValueError('Finer grid must be an integer larger than the baseline grid')


def magnetic_contribution_metrics(delta_mag, delta_nonmag, sigma_ref, rtol=1e-12):
    """Dimensionless contrast diagnostics; NaN below an intensity-relative floor.

    The floor is rtol*max(|Sigma_ref|, |Delta_mag|, |Delta_nonmag|) pointwise.
    f_mag is an index of detector-difference contributions, not electron counts.
    """
    if not np.isfinite(rtol) or rtol < 0:
        raise ValueError('Metric tolerance must be finite nonnegative')
    mag, nonmag, sigma = np.broadcast_arrays(np.abs(np.asarray(delta_mag, float)),
        np.abs(np.asarray(delta_nonmag, float)), np.abs(np.asarray(sigma_ref, float)))
    finite = np.isfinite(mag) & np.isfinite(nonmag) & np.isfinite(sigma)
    floor = rtol*np.maximum(np.maximum(mag, nonmag), sigma)
    valid_f = finite & (mag+nonmag > floor)
    valid_ratio = finite & (nonmag > floor)
    f = np.divide(mag, mag+nonmag, out=np.full_like(mag, np.nan), where=valid_f)
    ratio = np.divide(mag, nonmag, out=np.full_like(mag, np.nan), where=valid_ratio)
    return dict(f_mag=f, R_mag_nonmag=ratio, valid_f_mag=valid_f, valid_R_mag_nonmag=valid_ratio)


@dataclass
class GeometryDecompositionResult:
    records: list[dict]
    maps: dict[str, dict]
    metadata: dict


def compare_geometry_results(records, geometries, *, atol=1e-4, rtol=.05):
    """Compare coincident inputs, truncation and one grid refinement by edge."""
    comparisons = dict(coincident_geometries=[], truncation_reference=[], grid_refinement=[])
    keys = ('A_raw_plus', 'A_raw_minus', 'A_mag', 'A_nonmag', 'Sigma_ref')
    def differences(left, right):
        return {k: float(abs(left[k]-right[k])) for k in keys}
    for r in records:
        peers = [p for p in records if p['edge']==r['edge'] and p['sampling_role']=='baseline']
        if r['sampling_role'] == 'finer-grid':
            base = next(p for p in peers if p['group']==A and p['condition']==r['condition'])
            diff = differences(base, r)
            valid = all(np.isfinite(base[k]) and np.isfinite(r[k]) for k in keys)
            sensitive = {k: bool(diff[k] > (0. if k=='Sigma_ref' else atol)
                           + rtol*max(abs(base[k]), abs(r[k]))) for k in keys}
            comparisons['grid_refinement'].append(dict(edge=r['edge'], condition=r['condition'],
                baseline_grid=base['grid'], finer_grid=r['grid'], absolute_differences=diff,
                baseline_values={k:base[k] for k in keys}, finer_values={k:r[k] for k in keys},
                sensitive=sensitive, status=('unresolved' if not valid or any(sensitive.values())
                                             else 'limited-grid-agreement')))
        elif r['group'] == B:
            matched = next((p for p in peers if p['group']==A and p['condition'] in ('two-beam','near-2bc')), None)
            if matched:
                comparisons['truncation_reference'].append(dict(edge=r['edge'],
                    reference_id=r['run_id'], matched_id=matched['run_id'],
                    absolute_differences=differences(r, matched)))
        elif r['condition'] == 'two-beam':
            near = next((p for p in peers if p['group']==A and p['condition']=='near-2bc'), None)
            if near:
                x,y = geometries[r['run_id']], geometries[near['run_id']]
                identical = all(x[k]==y[k] for k in ('tilt_mrad_xy','beam_hkl','detectors','chiral_groups'))
                comparisons['coincident_geometries'].append(dict(edge=r['edge'],
                    labels=['two-beam','near-2bc'], identical_physical_inputs=identical,
                    absolute_differences=differences(r, near)))
    comparisons['grid_status'] = ('not-checked' if not comparisons['grid_refinement'] else
        'unresolved' if any(r['status']=='unresolved' for r in comparisons['grid_refinement'])
        else 'limited-grid-agreement-for-tested-geometry-only')
    comparisons['beam_basis_converged'] = False
    comparisons['depth_sampling_verified'] = False
    return comparisons


def run_geometry_decomposition(xmcd_file, config=GeometryDecompositionConfig()):
    """Calculate fixed-geometry parity using existing solvers; no plotting/I/O."""
    config.validate()
    source = load_wien2k_xmcd(xmcd_file)
    refs = {'L3':config.l3_energy_ev}
    if config.l2_energy_ev is not None:
        refs['L2'] = config.l2_energy_ev
    energies, selected = selected_energy_grid(source.energy_ev, refs)
    crystal = fcc_nickel()
    beams = BeamSet.zolz(crystal, config.cutoff, config.max_beams)
    if beams.hkl != BeamSet.zolz(crystal, config.cutoff, config.max_beams+2).hkl:
        raise ValueError('Beam cap truncates the 2D cutoff set; increase --max-beams')
    if not any(h[1] for h in beams.hkl):
        raise ValueError('Matched 2D basis must include off-row reflections')
    jobs = [(A, c, 'baseline', config.grid) for c in config.conditions]
    jobs.append((B, 'two-beam', 'baseline', config.grid))
    if config.finer_grid is not None:
        representative = 'near-2bc' if 'near-2bc' in config.conditions else config.conditions[0]
        jobs.append((A, representative, 'finer-grid', config.finer_grid))
    records, maps, geometries = [], {}, {}
    for group, condition, role, grid in jobs:
        setup = select_diffraction_setup(condition, crystal, config.acceleration_kv,
            offzone_tilt_mrad=config.offzone_tilt_mrad,
            tilt_x_mrad=config.tilt_x_mrad, tilt_y_mrad=config.tilt_y_mrad)
        basis = beams if group==A else setup.beams
        model = nickel_physical_benchmark(acceleration_kv=config.acceleration_kv,
            tilt_mrad_xy=setup.tilt_mrad_xy, beams_override=basis, diffraction_condition=condition)
        parity = run_xmcd_reversal(model, xmcd_file, energies, eta=config.eta, beta=config.beta,
            thickness_nm=config.thickness_nm, grid_size=grid, depth_steps=config.steps,
            l3_energy_ev=selected['L3'], l2_energy_ev=selected.get('L2',selected['L3']),
            integration_mode=config.integration_mode, aperture_subpixels=config.aperture_subpixels)
        run_id = f'{group}_{condition}_{role}'
        qx, qy = parity.maps['L3']['qx_inv_angstrom'], parity.maps['L3']['qy_inv_angstrom']
        detectors = {k:dict(center_q_xy=list(v.center_q_xy), radius_q=v.radius_q,
            grid_points=int(v.mask(qx,qy).sum()),
            **v.integration_info(qx,qy,mode=config.integration_mode,subpixels=config.aperture_subpixels))
            for k,v in model.detectors.items()}
        elastic = abs(model.elastic.amplitudes(np.array([config.thickness_nm]))[0])**2
        geometries[run_id] = dict(group=group, condition=condition, sampling_role=role,
            basis_kind='2d-zolz' if group==A else 'two-beam-truncated',
            beam_count=len(basis.hkl), beam_hkl=[list(h) for h in basis.hkl],
            reciprocal_gxy=model.elastic.reciprocal_vectors_xy.tolist(),
            elastic_intensity=elastic.tolist(), tilt_mrad_xy=list(setup.tilt_mrad_xy),
            detectors=detectors, chiral_groups=model.chiral_groups, grid=grid, depth_steps=config.steps,
            tensor_sources=parity.tensor_sources,
            approximation=('Common finite 2D ZOLZ basis; nominal geometry, not exact two-beam'
                           if group==A else setup.approximation),
            coincident_with=('near-2bc' if condition=='two-beam' else 'two-beam')
                            if group==A and condition in ('two-beam','near-2bc') else None,
            symmetric_3bc_note='Illustrative nominal geometry, not independently established experimental 3BC alignment'
                              if condition=='symmetric-3bc' else None)
        for edge, energy in selected.items():
            i = int(np.argmin(abs(energies-energy)))
            record = dict(run_id=run_id, group=group, sampling_role=role, condition=condition,
                basis_kind=geometries[run_id]['basis_kind'], beam_count=len(basis.hkl),
                cutoff_inv_angstrom=config.cutoff if group==A else np.nan,
                tilt_x_mrad=setup.tilt_mrad_xy[0], tilt_y_mrad=setup.tilt_mrad_xy[1],
                edge=edge, energy_ev=energy, grid=grid, steps=config.steps,
                integration_mode=config.integration_mode, aperture_subpixels=config.aperture_subpixels,
                thickness_nm=config.thickness_nm, acceleration_kv=config.acceleration_kv,
                eta=config.eta, beta=config.beta, detectors_json=json.dumps(detectors),
                chiral_groups_json=json.dumps(model.chiral_groups), beam_hkl_json=json.dumps(basis.hkl))
            record.update({k:v[i].item() for k,v in parity.spectra.items() if k!='energy_ev'})
            record.update(A_mag=record['A_odd'], A_nonmag=record['A_even'],
                          Delta_mag=record['delta_odd'], Delta_nonmag=record['delta_even'],
                          Sigma_ref=record['sigma_ref'])
            record.update({k:v.item() for k,v in magnetic_contribution_metrics(
                record['Delta_mag'], record['Delta_nonmag'], record['Sigma_ref']).items()})
            record['map_file'] = f'{run_id}_{edge}_maps.npz'
            records.append(record)
            m = parity.maps[edge]
            maps[record['map_file']] = dict(**m, I_mag=m['I_odd'], I_nonmag=m['I_even'],
                beam_hkl=np.asarray(basis.hkl), reciprocal_gxy=model.elastic.reciprocal_vectors_xy,
                elastic_intensity=elastic, detectors_json=np.asarray(json.dumps(detectors)),
                chiral_groups_json=np.asarray(json.dumps(model.chiral_groups)),
                group=np.asarray(group), condition=np.asarray(condition), grid=grid,
                tilt_mrad_xy=np.asarray(setup.tilt_mrad_xy), thickness_nm=config.thickness_nm,
                depth_steps=config.steps, integration_mode=np.asarray(config.integration_mode),
                aperture_subpixels=config.aperture_subpixels)
    try:
        root = Path(__file__).resolve().parents[2]
        commit = subprocess.check_output(['git','rev-parse','HEAD'], cwd=root, stderr=subprocess.DEVNULL).decode().strip()
        dirty = bool(subprocess.check_output(['git','status','--porcelain'], cwd=root).strip())
    except (OSError, subprocess.CalledProcessError):
        commit, dirty = None, None
    metadata = dict(config=asdict(config), model=LABEL, xmcd_file=str(Path(xmcd_file).resolve()),
        xmcd_sha256=source.source_sha256, source_peak_N=float(source.nonmagnetic.max()),
        requested_energies_ev=refs, selected_energies_ev=selected, energy_grid_ev=energies.tolist(),
        geometries=geometries, software_commit=commit, software_worktree_dirty=dirty,
        python_version=platform.python_version(), reciprocal_coordinate_units='cycles/angstrom',
        map_halfwidth_q=1., elastic_potential='Existing Ni independent-atom physical potential; B=0',
        reversal='eta -> -eta; diagonal unchanged; common source peak N normalization',
        metric_floor='1e-12 * max(abs(Sigma_ref), abs(Delta_mag), abs(Delta_nonmag)) per sample',
        ratio_policy='NaN with false valid_R_mag_nonmag when denominator <= metric floor',
        normalization='A_mag/nonmag use Sigma_ref; raw +/- use their own sums; inherited NaN/masks',
        comparison_groups={A:'Matched common 2D basis; two-beam and near-2bc are coincident labels',
                           B:'Original truncated two-beam approximation; not a separate incident geometry'},
        absolute_cross_section=False, outgoing_channeling=False, quantitative_Ni=False,
        beam_basis_converged=False, depth_sampling_verified=False,
        limitations='Finite ZOLZ, axisymmetric effective dipole proxy, no absorption/TDS, outgoing channeling or calibrated counts')
    metadata['comparisons'] = compare_geometry_results(records, geometries, atol=config.grid_atol, rtol=config.grid_rtol)
    return GeometryDecompositionResult(records, maps, metadata)


def _json_safe(value):
    """Use standard JSON null for undefined numerical comparisons."""
    if isinstance(value, dict):
        return {k:_json_safe(v) for k,v in value.items()}
    if isinstance(value, (tuple,list)):
        return [_json_safe(v) for v in value]
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def save_geometry_decomposition(result, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    with (output/'geometry_comparison.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(result.records[0]))
        writer.writeheader()
        writer.writerows(result.records)
    np.savez_compressed(output/'geometry_comparison.npz',
        **{k:np.asarray([r[k] for r in result.records]) for k in result.records[0]})
    for filename, data in result.maps.items():
        np.savez_compressed(output/filename, **data)
    (output/'geometry_metadata.json').write_text(
        json.dumps(_json_safe(result.metadata), indent=2, allow_nan=False)+'\n', encoding='utf-8')


def plot_geometry_decomposition(result, output):
    """Shared map scales; separate panels for matched geometry and truncation."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    base = [r for r in result.records if r['sampling_role']=='baseline']
    edges = list(result.metadata['selected_energies_ev'])
    for field, filename, diverging in [('I_mag','magnetic_odd_maps.png',True),
                                       ('I_nonmag','nonmagnetic_even_maps.png',False)]:
        n = len(base)//len(edges)
        fig, axes = plt.subplots(len(edges), n, figsize=(3.6*n,4*len(edges)),
                                 squeeze=False, constrained_layout=True)
        for row, edge in enumerate(edges):
            peers = [r for r in base if r['edge']==edge]
            lim = max(max(float(np.max(abs(result.maps[r['map_file']][field]))) for r in peers),1e-30)
            for col,r in enumerate(peers):
                ax, m = axes[row,col], result.maps[r['map_file']]
                qx, qy = m['qx_inv_angstrom'], m['qy_inv_angstrom']
                # Pixel edges align overlays with the actual sampled centers.
                half = (qx[0,1]-qx[0,0])/2
                extent = (qx.min()-half, qx.max()+half, qy.min()-half, qy.max()+half)
                im = ax.imshow(m[field], origin='lower', extent=extent,
                    cmap='coolwarm' if diverging else 'viridis', vmin=-lim if diverging else 0, vmax=lim)
                geo = result.metadata['geometries'][r['run_id']]
                for h,g,intensity in zip(geo['beam_hkl'],geo['reciprocal_gxy'],geo['elastic_intensity']):
                    if qx.min() <= g[0] <= qx.max() and qy.min() <= g[1] <= qy.max():
                        ax.scatter(*g, marker='o', s=8+50*intensity, facecolors='none', edgecolors='black')
                        ax.annotate(str(tuple(h)),g,xytext=(2,3),textcoords='offset points',fontsize=5)
                for label,det in geo['detectors'].items():
                    ax.add_patch(Circle(det['center_q_xy'],det['radius_q'],fill=False,ec='black'))
                    ax.text(*det['center_q_xy'],label,ha='center',va='center',fontsize=7)
                coincident = '\ncoincident 2BC/near-2BC' if r['group']==A and geo['coincident_with'] else ''
                ax.set(title=f'{r["group"]}\n{r["condition"]}, {edge} {r["energy_ev"]:.3f} eV{coincident}',
                       xlabel='qx (cycles/angstrom)', ylabel='qy (cycles/angstrom)', aspect='equal')
                ax.set_xlim(extent[:2]); ax.set_ylim(extent[2:])
            fig.colorbar(im,ax=axes[row,:].tolist(),shrink=.65,label=field+' (relative intensity)')
        fig.suptitle(LABEL+'\n'+('Reversal-odd intensity' if diverging else
                     'Reversal-even intensity map (not the even detector difference)'))
        fig.savefig(output/filename,dpi=150)
        plt.close(fig)
    for filename, metrics in [('geometry_asymmetry_comparison.png',('A_raw_plus','A_mag','A_nonmag')),
                              ('magnetic_contribution_comparison.png',('f_mag','R_mag_nonmag','Sigma_ref'))]:
        fig,axes = plt.subplots(len(edges),2,figsize=(13,4*len(edges)),squeeze=False,constrained_layout=True)
        for row,edge in enumerate(edges):
            for col,group in enumerate((A,B)):
                peers = [r for r in base if r['edge']==edge and r['group']==group]
                positions = np.arange(len(peers))
                ax = axes[row,col]
                if filename.startswith('magnetic_contribution'):
                    # Different units/scales: use a table rather than one misleading axis.
                    labels = [r['condition'] for r in peers]
                    cells = [[f'{r[k]:.5g}' if np.isfinite(r[k]) else 'undefined' for k in metrics] for r in peers]
                    table = ax.table(cellText=cells,rowLabels=labels,colLabels=metrics,loc='center',cellLoc='center')
                    table.auto_set_font_size(False); table.set_fontsize(9); table.scale(.85,1.8)
                    ax.axis('off')
                else:
                    for j,key in enumerate(metrics):
                        ax.bar(positions+(j-1)*.24,[r[key] for r in peers],width=.24,label=key)
                    ax.set_xticks(positions,[r['condition'] for r in peers],rotation=15)
                    ax.set_ylabel('Fractional asymmetry'); ax.legend(); ax.axhline(0,color='grey',lw=.7)
                ax.set_title(f'{group} | {edge} {result.metadata["selected_energies_ev"][edge]:.3f} eV')
        fig.suptitle(LABEL+'\n2BC/near-2BC coincide in Group A; Group B isolates truncation')
        fig.savefig(output/filename,dpi=150)
        plt.close(fig)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--xmcd-file',type=Path,required=True)
    p.add_argument('--output',type=Path,default=Path('outputs/ni_xmcd_geometry_decomposition'))
    p.add_argument('--conditions',nargs='+',choices=CONDITIONS,default=list(CONDITIONS))
    for key,default in [('cutoff',1.4),('acceleration-kv',200.),('thickness-nm',30.),
        ('eta',1.),('beta',1.),('offzone-tilt-mrad',25.),('l3-energy-ev',852.7),('grid-atol',1e-4),('grid-rtol',.05)]:
        p.add_argument('--'+key,type=float,default=default)
    for key in ('tilt-x-mrad','tilt-y-mrad','l2-energy-ev'):
        p.add_argument('--'+key,type=float)
    for key,default in [('grid',65),('steps',64),('max-beams',81),('finer-grid',97)]:
        p.add_argument('--'+key,type=int,default=default)
    p.add_argument('--integration-mode',choices=('binary','fractional'),default='binary')
    p.add_argument('--aperture-subpixels',type=int,default=64)
    p.add_argument('--skip-finer-grid',action='store_true')
    args = vars(p.parse_args(argv))
    output,source = args.pop('output'),args.pop('xmcd_file')
    if args.pop('skip_finer_grid'):
        args['finer_grid'] = None
    args['conditions'] = tuple(args['conditions'])
    try:
        result = run_geometry_decomposition(source,GeometryDecompositionConfig(**args))
    except ValueError as exc:
        p.error(str(exc))
    save_geometry_decomposition(result,output)
    plot_geometry_decomposition(result,output)
    for r in result.records:
        print(json.dumps(_json_safe({k:r[k] for k in ('group','condition','sampling_role','energy_ev',
            'A_raw_plus','A_mag','A_nonmag','Sigma_ref','f_mag','R_mag_nonmag')}),allow_nan=False))
    print(f'Grid check: {result.metadata["comparisons"]["grid_status"]}; output: {output}')


if __name__ == '__main__':
    main()
