"""PRB-inspired geometry/aperture/depth study; existing engines, compact checkpoints.

Atomic-3D is audited honestly: this branch implements P1 geometry, not a 3D
potential or propagator. No artificial projected-potential '3D' result is made.
"""
import argparse
import csv
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import subprocess
import time

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

import ni_017_thickness_scan as base
from emcd_sim.gui.geometry import Structure, Settings, geometry, elastic_model
from emcd_sim.gui.emcd_forward import tensors
from emcd_sim.gui.propagation import numerical_info
from emcd_sim.gui.memory_budget import BUDGETS_MIB, reserve_memory
from emcd_sim.geometry import VirtualDetector, electron_wavelength_angstrom
from emcd_sim.multislice_reference import fft_multislice_ni
from emcd_sim.multislice_emcd_reference import project_fft_amplitudes, coherence_from_amplitudes
from emcd_sim.single_channeling_tensor import _tensor_angular_maps, fcc_site_phase_matrix
from emcd_sim.atomic_multislice_geometry import oriented_atomic_cell, atomic_planes, slice_geometry, specimen_positions
from emcd_sim.elastic import BeamSet

RADII = (.03, .06, .0908059024, .12)
REPRESENTATIVE = (10., 12., 20., 30., 50.)
DEPTH_THICKNESSES = (12., 30., 64., 100.)


def make_context(saved, zone, budget, systematic_row=False):
    settings = replace(saved['settings'], zone=zone)
    # Chosen ~2-degree off-row tilt: paper supplies no numerical value.
    if zone == (0, 0, 1):
        settings = replace(settings, tilt=(settings.tilt[0], 35.))
    structure = Structure.nickel()
    _, R, hkl, g, _ = geometry(structure, settings)
    target = g[hkl.index((2, 0, 0))]
    wavelength = electron_wavelength_angstrom(settings.voltage)
    # Derive exact Bragg x tilt in the actual frame, keeping chosen y fixed.
    if zone == (0, 0, 1):
        tx = (-np.dot(target, target)/2-target[1]*settings.tilt[1]*1e-3/wavelength)/target[0]*wavelength*1000
        settings = replace(settings, tilt=(float(tx), settings.tilt[1]))
    elastic = elastic_model(structure, settings)
    if systematic_row:
        hkl = tuple(h for h in hkl if h[1] == h[2] == 0)
        elastic = replace(elastic, beams=BeamSet(hkl))
        g = elastic.reciprocal_vectors_xy
    perpendicular = np.array([-target[1], target[0]])
    centers = np.stack((target/2+perpendicular/2, target/2-perpendicular/2))
    cfg = replace(saved['config'], centers=tuple(map(tuple, centers)), memory_budget_mib=budget, correction=False)
    detectors = {d: VirtualDetector(tuple(p), cfg.radius) for d, p in zip(('A', 'B'), centers)}
    model = replace(base.nickel_physical_benchmark(), elastic=elastic, detectors=detectors, chiral_groups=None)
    ts = tensors(cfg, base.ENERGIES, R)
    np.testing.assert_allclose(ts[1].tensor_angstrom2_per_ev, ts[0].tensor_angstrom2_per_ev.conj(), atol=1e-14)
    sg = base.excitation_errors_angstrom_inv(elastic)
    assert abs(sg[hkl.index((2, 0, 0))]) < 1e-10
    return dict(settings=settings, cfg=cfg, model=model, hkl=hkl, g=g, R=R, ts=ts,
                phase=fcc_site_phase_matrix(model), s=sg, centers=centers, systematic_row=systematic_row)


class DetectorGrid:
    """One weight set per geometry/grid/radius; evaluate only supported pixels."""
    def __init__(self, centers, radii, grid, halfwidth, subpixels=64):
        q = np.linspace(-halfwidth, halfwidth, grid)
        self.qx, self.qy = np.meshgrid(q, q, indexing='xy')
        self.dq2 = (q[1]-q[0])**2
        self.weights = np.array([[VirtualDetector(tuple(p), r).integration_weights(self.qx, self.qy,
            mode='fractional', subpixels=subpixels) for p in centers] for r in radii])
        assert all(max(abs(p))+max(radii) < halfwidth for p in centers)
        assert np.all(self.weights.sum(axis=(2, 3)) > 0)
        self.support = self.weights.any(axis=(0, 1)).ravel()
        self.x = self.qx.ravel()[self.support]; self.y = self.qy.ravel()[self.support]
        self.w = self.weights.reshape(len(radii), 2, -1)[:, :, self.support]
        self.areas = self.weights.sum(axis=(2, 3))*self.dq2
        self.grid, self.halfwidth, self.subpixels = grid, halfwidth, subpixels
        self.radii = radii


def contract_detectors(context, coherence, t, detector, batch=64):
    """Unchanged core tensor/Coulomb kernel on batches; no map interpolation."""
    result = np.zeros((len(detector.radii), 2, 4), dtype=np.float64)
    if t == 0:
        return result
    np.testing.assert_allclose(coherence, coherence.conj().T, atol=1e-12)
    for ie, energy in enumerate(base.ENERGIES):
        tensor = context['ts'][0].tensor_angstrom2_per_ev[ie]
        for start in range(0, len(detector.x), batch):
            sl = slice(start, start+batch)
            even, odd = _tensor_angular_maps(context['model'], tensor, energy, coherence,
                context['phase'], detector.x[sl], detector.y[sl])
            plus, minus = t*(even+odd), t*(even-odd)
            assert plus.min() >= -1e-12 and minus.min() >= -1e-12
            ip = np.einsum('rdp,p->rd', detector.w[:, :, sl], plus)*detector.dq2
            im = np.einsum('rdp,p->rd', detector.w[:, :, sl], minus)*detector.dq2
            result[:, ie, :2] += ip
            result[:, ie, 2:] += im
    return result


def analytic_bw_coherence(elastic, t):
    """Diagnostic exact depth integral of this finite BW Hamiltonian, not a new solver."""
    val, vec = np.linalg.eigh(elastic.hamiltonian_nm_inv())
    c = vec[elastic.beams.hkl.index((0, 0, 0))].conj()
    phase = (val[:, None]-val[None, :])*t
    integral = np.exp(.5j*phase)*np.sinc(phase/(2*np.pi))*c[:, None]*c[None, :].conj()
    return vec@integral@vec.conj().T


def allocation_info(context, detector, depth, batch=64):
    # Reuse the existing retained-array estimator, substituting actual batched
    # pixel count and including full FFT/depth storage for both propagations.
    cfg = replace(context['cfg'], depth=depth, grid=9, propagation='bloch')
    info = numerical_info(Structure.nickel(), context['settings'], cfg, hkl=context['hkl'], check_memory=False)
    dense = 64*min(batch, len(detector.x))*len(context['hkl'])**2/2**20
    extra = (24*depth+160)*cfg.fft_grid**2/2**20 + detector.weights.nbytes/2**20 + 8.
    working = info['estimated_working_mib']-info['dense_working_estimate_mib']+dense+extra
    return dict(dense_mib=dense, working_mib=working)


def calculate_point(root, stage, name, context, t, depth, detector, analytic=False):
    folder = root/'checkpoints'; folder.mkdir(exist_ok=True)
    key = f'{stage}_{name}_t{int(t):03d}_d{depth}_g{detector.grid}'+('_analytic' if analytic else '')
    if context['systematic_row']:key += '_row'
    path = folder/(key+'.npz')
    parameters = dict(name=name, thickness_nm=t, depth=depth, grid=detector.grid,
        halfwidth=detector.halfwidth, radii=detector.radii, analytic=analytic,
        settings=asdict(context['settings']), source_sha256=context['cfg'].source_sha256)
    params_json = json.dumps(base.clean(parameters), sort_keys=True)
    if stage.startswith('C-step'):
        parameters['max_slice_step_nm'] = context['cfg'].slice_step
        params_json = json.dumps(base.clean(parameters), sort_keys=True)
    if context['systematic_row']:
        parameters['systematic_row_hkl'] = [2,0,0]
        params_json = json.dumps(base.clean(parameters), sort_keys=True)
    if path.exists():
        with np.load(path, allow_pickle=False) as saved:
            assert str(saved['parameters_json']) == params_json, 'Checkpoint configuration changed'
            return {k: saved[k] for k in saved.files}
    info = allocation_info(context, detector, depth)
    with reserve_memory(info['working_mib'], context['cfg'].memory_budget_mib, dense_mib=info['dense_mib']) as admission:
        elastic = context['model'].elastic
        z = np.linspace(0, t, depth)
        result = dict(parameters_json=np.array(params_json), areas=detector.areas,
                      memory_admission_json=np.array(json.dumps(admission)), actual_thickness_nm=float(t))
        if t == 0:
            for method in base.METHODS:
                result[method+'__raw'] = np.zeros((len(detector.radii), 2, 4))
                pop = np.zeros(len(context['hkl'])); pop[0] = 1.
                result[method+'__exit'] = result[method+'__average'] = pop
        else:
            bw = elastic.amplitudes(z)
            C = analytic_bw_coherence(elastic, t) if analytic else coherence_from_amplitudes(z, bw)
            result['bloch__raw'] = contract_detectors(context, C, t, detector)
            result['bloch__exit'] = abs(bw[-1])**2
            result['bloch__average'] = np.diag(C).real
            del bw, C
            if not analytic:
                projected_geometry = None
                if name == '017':
                    from emcd_sim.ni_017_geometry import Ni017Geometry
                    projected_geometry = Ni017Geometry()
                fft = fft_multislice_ni(z, acceleration_kv=context['settings'].voltage,
                    tilt_mrad_xy=context['settings'].tilt, grid_points=context['cfg'].fft_grid,
                    slice_step_nm=context['cfg'].slice_step, potential_cutoff_inv_angstrom=context['settings'].potential_cutoff,
                    b_factor_angstrom2=context['settings'].b_factor, return_amplitudes=True, projected_geometry=projected_geometry,
                    systematic_row_hkl=(2,0,0) if context['systematic_row'] else None)
                psi, outside = project_fft_amplitudes(fft, context['hkl'])
                C = coherence_from_amplitudes(z, psi)
                result['fft-multislice__raw'] = contract_detectors(context, C, t, detector)
                result['fft-multislice__exit'] = abs(psi[-1])**2
                result['fft-multislice__average'] = np.diag(C).real
                result['fft_norm_error'] = fft.norm_error
                result['fft_excluded_population_max'] = outside.max()
                result['fft_full_exit'] = fft.intensity[-1].copy()
                result['fft_full_hkl'] = fft.beam_hkl
                del psi, C, outside, fft
        np.savez_compressed(path, **result)
    print(key+' complete', flush=True)
    return result


def rows_for_point(stage, name, context, t, depth, detector, point):
    rows = []
    for method in base.METHODS:
        if method+'__raw' not in point:
            continue
        for ir, radius in enumerate(detector.radii):
            obs = base.observables(point[method+'__raw'][ir])
            for ie, edge in enumerate(base.EDGES):
                rows.append(dict(stage=stage, geometry=name, thickness_nm=t, actual_thickness_nm=t,
                    solver=method, potential_model='projected-2D IAM systematic-row projection' if context['systematic_row'] else 'projected-2D IAM full ZOLZ', edge=edge, energy_ev=base.ENERGIES[ie],
                    mdff_model='XMCD-constrained',eta=context['cfg'].eta,beta=context['cfg'].beta,
                    accelerating_voltage_kv=context['settings'].voltage,beam_count=len(context['hkl']),
                    beam_cutoff=context['settings'].beam_cutoff,potential_cutoff=context['settings'].potential_cutoff,
                    systematic_row_projection=context['systematic_row'],integration='fractional',
                    A_qx=context['centers'][0,0],A_qy=context['centers'][0,1],B_qx=context['centers'][1,0],B_qy=context['centers'][1,1],
                    radius_cycles_per_angstrom=radius,
                    collection_semiangle_mrad=1000*radius*electron_wavelength_angstrom(context['settings'].voltage),
                    detector_grid=detector.grid, detector_halfwidth=detector.halfwidth, subpixels=detector.subpixels,
                    depth_nodes=depth, area_A=detector.areas[ir, 0], area_B=detector.areas[ir, 1],
                    max_slice_step_nm=context['cfg'].slice_step,
                    **{k: v[ie] for k, v in obs.items()}))
    return rows


def atomic_audit(root):
    cell = oriented_atomic_cell(Structure.nickel().atoms, (0, 1, 7)); planes = atomic_planes(cell)
    rows = []; arrays = dict(frame=cell.frame, cell_angstrom=cell.atoms.cell.array,
        positions_angstrom=cell.atoms.positions, plane_depths_angstrom=planes.depths_angstrom)
    for t in (10., 12., 30., 50.):
        positions = specimen_positions(cell, 10*t)
        slices = slice_geometry(cell, 10*t, mode='plane-aware')
        bounds = slices.boundaries_angstrom
        assert bounds[0] == 0 and bounds[-1] == 10*t and np.all(np.diff(bounds) > 0)
        arrays[f't{int(t)}_boundaries_angstrom'] = bounds
        rows.append(dict(thickness_nm=t, actual_structural_thickness_nm=bounds[-1]/10,
            atom_count=len(positions), slice_count=len(bounds)-1, plane_count_per_repeat=len(planes.depths_angstrom),
            atomic_3d_potential_available=False, atomic_3d_propagation_available=False,
            integrated_electrostatic_potential='undefined: no finite-z potential builder',
            atomic_3d_emcd='unavailable: no elastic amplitudes/coherence'))
    base.write_csv(root/'atomic_3d_readiness.csv', rows)
    np.savez_compressed(root/'atomic_geometry_only.npz', **arrays)
    base.write_json(root/'atomic_3d_readiness.json', dict(status='P1 geometry only; 3D scattering comparison unavailable',
        local_cell_angstrom=cell.atoms.cell.array, atoms_per_repeat=len(cell.atoms),
        period_angstrom=cell.period_angstrom, planes_per_repeat=len(planes.depths_angstrom),
        interface='run_tensor_with_coherence requires finite Hermitian common-hkl coherence C_gh. P1 supplies OrientedAtomicCell/SliceGeometry, not potential/transmission/waves. No propagator produces psi(z,g), hkl mapping or C_gh; this is upstream of inelastic contraction.',
        missing=['Finite-z atomic potential integration including tails and surface convention', 'Periodic potential arrays and integrated-potential/phase-unit validation',
                 'Physical-slice propagation with observations at quadrature depths', 'Full-3D harmonic to common-ZOLZ mapping and excluded/HOLZ population checks'],
        no_full_3d_scan=True, no_projected_potential_substitution=True, structural_checks=rows))
    return cell, planes


def analyze_results(root, rows, old):
    """Absolute errors plus explicitly gated relative signal errors."""
    grid_rows=[]; suppression=[]; depth_rows=[]; summary={}
    for name in ('001','017'):
        for m in base.METHODS:
            for edge in base.EDGES:
                selected=[r for r in rows if r['stage']=='B' and r['geometry']==name and r['solver']==m and r['edge']==edge]
                for t in REPRESENTATIVE:
                    series=sorted([r for r in selected if r['thickness_nm']==t],key=lambda r:r['radius_cycles_per_angstrom'])
                    small,big=series[0],series[-1]
                    suppression.append(dict(geometry=name,solver=m,edge=edge,thickness_nm=t,
                        small_radius=small['radius_cycles_per_angstrom'],large_radius=big['radius_cycles_per_angstrom'],
                        small_prb_percent=small[base.METRICS[0]],large_prb_percent=big[base.METRICS[0]],
                        prb_magnitude_reduction_percent=100*(1-abs(big[base.METRICS[0]]/small[base.METRICS[0]])),
                        magnetic_magnitude_reduction_percent=100*(1-abs(big[base.METRICS[1]]/small[base.METRICS[1]]))))
                for radius in RADII:
                    ref=next(r for r in rows if r['stage']=='B-grid' and r['geometry']==name and r['solver']==m and r['edge']==edge and r['detector_grid']==385 and r['radius_cycles_per_angstrom']==radius)
                    for grid,stage in ((97,'B-grid'),(193,'B')):
                        r=next(r for r in rows if r['stage']==stage and r['geometry']==name and r['solver']==m and r['edge']==edge and r['thickness_nm']==12 and r['detector_grid']==grid and r['radius_cycles_per_angstrom']==radius)
                        grid_rows.append(dict(geometry=name,solver=m,edge=edge,radius=radius,thickness_nm=12.,grid=grid,reference_grid=385,
                            prb_difference_pp=r[base.METRICS[0]]-ref[base.METRICS[0]],magnetic_difference_pp=r[base.METRICS[1]]-ref[base.METRICS[1]],
                            I_A_relative_change=r['I_A_plus']/ref['I_A_plus']-1,I_B_relative_change=r['I_B_plus']/ref['I_B_plus']-1,
                            area_relative_error=r['area_A']/(np.pi*radius**2)-1))
    for m in base.METHODS:
        for edge in base.EDGES:
            references=[r for r in rows if r['stage']=='C-exact' and r['edge']==edge]
            mag_floor=.05*max(abs(r['D_mag']) for r in references)
            prb_floor=.05*max(abs(r[base.METRICS[0]]) for r in references)
            for t in DEPTH_THICKNESSES:
                sampled=[r for r in rows if r['stage']=='C' and r['solver']==m and r['edge']==edge and r['thickness_nm']==t]
                exact=next(r for r in references if r['thickness_nm']==t)
                ref=exact if m=='bloch' else max(sampled,key=lambda r:r['depth_nodes'])
                for r in sampled:
                    valid_mag=abs(ref['D_mag'])>=mag_floor
                    valid_prb=abs(ref[base.METRICS[0]])>=prb_floor
                    depth_rows.append(dict(solver=m,edge=edge,thickness_nm=t,depth_nodes=r['depth_nodes'],
                        reference='analytic finite-BW integral' if m=='bloch' else f'MS {ref["depth_nodes"]} nodes (not proven exact)',
                        prb_error_pp=r[base.METRICS[0]]-ref[base.METRICS[0]],
                        magnetic_error_pp=r[base.METRICS[1]]-ref[base.METRICS[1]],
                        analytic_bw_prb_difference_pp=r[base.METRICS[0]]-exact[base.METRICS[0]],
                        I_A_relative_error=r['I_A_plus']/ref['I_A_plus']-1,
                        I_B_relative_error=r['I_B_plus']/ref['I_B_plus']-1,
                        D_mag_absolute_error=r['D_mag']-ref['D_mag'],
                        D_mag_relative_error=(r['D_mag']/ref['D_mag']-1) if valid_mag else np.nan,
                        prb_relative_error=(r[base.METRICS[0]]/ref[base.METRICS[0]]-1) if valid_prb else np.nan,
                        relative_mag_valid=valid_mag,relative_prb_valid=valid_prb,magnetic_signal_floor=mag_floor,prb_signal_floor=prb_floor))
    for m in base.METHODS:
        a=[r for r in rows if r['stage']=='A' and r['solver']==m and r['edge']=='L3' and r['thickness_nm']>0]
        peak=max(a,key=lambda r:abs(r[base.METRICS[0]]))
        summary[m]=dict(l3_peak=peak)
    for edge in base.EDGES:
        b=sorted([r for r in rows if r['stage']=='A' and r['solver']=='bloch' and r['edge']==edge and r['thickness_nm']>0],key=lambda r:r['thickness_nm'])
        ms=sorted([r for r in rows if r['stage']=='A' and r['solver']=='fft-multislice' and r['edge']==edge and r['thickness_nm']>0],key=lambda r:r['thickness_nm'])
        summary[edge+'_max_bw_ms_difference_pp']=max(abs(x[base.METRICS[0]]-y[base.METRICS[0]]) for x,y in zip(b,ms))
    summary['grid_193_vs_385_max_prb_difference_pp']=max(abs(r['prb_difference_pp']) for r in grid_rows if r['grid']==193)
    summary['grid_193_vs_385_max_intensity_relative_change']=max(max(abs(r['I_A_relative_change']),abs(r['I_B_relative_change'])) for r in grid_rows if r['grid']==193)
    summary['depth_64_max_abs_prb_error_pp']=max(abs(r['prb_error_pp']) for r in depth_rows if r['depth_nodes']==64)
    summary['depth_64_max_abs_intensity_relative_error']=max(max(abs(r['I_A_relative_error']),abs(r['I_B_relative_error'])) for r in depth_rows if r['depth_nodes']==64)
    summary['depth_64_max_abs_valid_magnetic_relative_error']=max(abs(r['D_mag_relative_error']) for r in depth_rows if r['depth_nodes']==64 and r['relative_mag_valid'])
    summary['trend_accuracy_criterion']='0.01 percentage points PRB and 0.1% A/B intensity, plus 0.1% magnetic-difference relative error only above 5% of tested peak. Local checks, not global physical convergence.'
    summary['depth_64_passes_local_trend_criterion']=bool(summary['depth_64_max_abs_prb_error_pp']<.01 and summary['depth_64_max_abs_intensity_relative_error']<.001 and summary['depth_64_max_abs_valid_magnetic_relative_error']<.001)
    summary['atomic_3d_status']='UNAVAILABLE: P1 geometry only; no 3D potential/propagator, no 3D EMCD result or full scan.'
    base.write_csv(root/'aperture_grid_convergence.csv',grid_rows)
    base.write_csv(root/'aperture_suppression.csv',suppression)
    base.write_csv(root/'depth_convergence.csv',depth_rows)
    base.write_csv(root/'fft_step_control.csv',[r for r in rows if r['stage']=='C-step002'])
    base.write_json(root/'summary.json',summary)
    return summary


def plot_results(root, rows, old, cell, planes):
    def figure(n, shape=(1, 1), figsize=(9, 5)):
        fig = Figure(figsize=figsize, layout='constrained'); FigureCanvasAgg(fig)
        return fig, np.asarray(fig.subplots(*shape)).reshape(shape)
    def save(fig, n):
        for ext in ('png', 'svg'):fig.savefig(root/f'figure_{n}.{ext}', dpi=170)
    for ie, n in enumerate((1, 2)):
        fig, axes = figure(n); ax = axes[0, 0]
        for method, label, ls in zip(base.METHODS, ('BW', 'projected MS'), ('-', '--')):
            selected = [r for r in rows if r['stage'] == 'A' and r['solver'] == method and r['edge'] == base.EDGES[ie]]
            selected.sort(key=lambda r: r['thickness_nm'])
            ax.plot([r['thickness_nm'] for r in selected], [r[base.METRICS[0]] for r in selected], ls, label='[001] '+label)
            ax.plot(old['requested_thickness_nm'], old[method+'__'+base.METRICS[0]][:, ie], ls, label='[017] saved '+label)
        ax.axhline(0, color='.4', lw=.7); ax.set(xlim=(0, 100), xlabel='Thickness (nm)', ylabel='Raw PRB dichroism (%)',
            title=f'{base.EDGES[ie]} fixed {base.ENERGIES[ie]:.4f} eV | 200 kV, r=0.0908059024 cycles/Angstrom\n[001] systematic-row approximation; [017] full ZOLZ; entrance-only MDFF')
        ax.legend(fontsize=8); ax.grid(alpha=.2); save(fig, n)
    fig, axes = figure(3, (2, 2), (12, 8))
    for j, name in enumerate(('001', '017')):
        for ie, edge in enumerate(base.EDGES):
            ax = axes[ie, j]
            for t in REPRESENTATIVE:
                selected = sorted([r for r in rows if r['stage'] == 'B' and r['geometry'] == name and r['edge'] == edge and r['solver'] == 'bloch' and r['thickness_nm'] == t], key=lambda r: r['radius_cycles_per_angstrom'])
                line=ax.plot([r['radius_cycles_per_angstrom'] for r in selected], [r[base.METRICS[0]] for r in selected], '.-', label=f'{t:g} nm')
                ms=sorted([r for r in rows if r['stage']=='B' and r['geometry']==name and r['edge']==edge and r['solver']=='fft-multislice' and r['thickness_nm']==t],key=lambda r:r['radius_cycles_per_angstrom'])
                ax.plot([r['radius_cycles_per_angstrom'] for r in ms],[r[base.METRICS[0]] for r in ms],'--',color=line[0].get_color(),lw=.9)
            ax.axhline(0, color='.4', lw=.7); ax.set(xlabel='Aperture radius (cycles/Angstrom)', ylabel='Raw PRB (%)', title=f'[{name}] {edge} | BW solid / MS dashed, grid 193')
            ax.legend(fontsize=7); ax.grid(alpha=.2)
    save(fig, 3)
    fig, axes = figure(4, (2, 2), (12, 8))
    for it, t in enumerate(DEPTH_THICKNESSES):
        ax = axes.flat[it]
        for method, ls in zip(base.METHODS, ('-', '--')):
            for edge, marker in zip(base.EDGES, ('o', 's')):
                selected = sorted([r for r in rows if r['stage'] == 'C' and r['solver'] == method and r['edge'] == edge and r['thickness_nm'] == t], key=lambda r:r['depth_nodes'])
                ref = [r for r in rows if r['stage'] == 'C-exact' and r['edge'] == edge and r['thickness_nm'] == t][0]
                ax.plot([r['depth_nodes'] for r in selected], [r[base.METRICS[0]]-ref[base.METRICS[0]] for r in selected], ls+marker, ms=3, label=method+' '+edge)
        ax.axhline(0, color='.4', lw=.7); ax.set(xlabel='Depth nodes', ylabel='PRB - analytic BW reference (pp)', title=f'[017] {t:g} nm; MS includes solver difference')
        ax.grid(alpha=.2); ax.legend(fontsize=6)
    save(fig, 4)
    fig, axes = figure(5, (1, 2), (12, 5))
    axes[0, 0].scatter(cell.atoms.positions[:, 2], cell.atoms.positions[:, 1], s=12)
    axes[0, 0].set(xlabel='Local z (Angstrom)', ylabel='Local y (Angstrom)', title='Actual [017] atoms: structure only')
    ax = axes[0, 1]
    for m in base.METHODS:
        ids = np.array([5, 6, 15, 25]); ax.plot(old['requested_thickness_nm'][ids], old[m+'__'+base.METRICS[0]][ids, 0], 'o-', label=m+' projected IAM')
    ax.set(xlabel='Thickness (nm)', ylabel='L3 raw PRB (%)', title='Atomic-3D EMCD: unavailable on this branch')
    ax.text(.03, .6, 'P1: atomic geometry and slice boundaries only.\nNo finite-z potential or 3D propagation.\nNo 3D curve or fabricated comparison.', transform=ax.transAxes, fontsize=8,bbox=dict(facecolor='white',edgecolor='none',alpha=.9))
    ax.axhline(0, color='.4', lw=.7); ax.legend(fontsize=7); save(fig, 5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('outputs/ni_prb2007_geometry_validation'))
    parser.add_argument('--memory-budget-mib', type=int, choices=BUDGETS_MIB, default=2048)
    parser.add_argument('--full-zolz-control',action='store_true',help='Also retain the explicit full-[001]-ZOLZ contrast control (no row projection).')
    args = parser.parse_args(); root=args.output; root.mkdir(parents=True, exist_ok=True)
    original = base.file_hashes('outputs/ni_017_thickness_0_100nm')
    saved = base.load_project('outputs/gui_stage_d/windows_20261016/reference_project')
    with np.load('outputs/ni_017_thickness_0_100nm/thickness_series.npz', allow_pickle=False) as f:old={k:f[k] for k in f.files}
    assert base.load_wien2k_xmcd(saved['config'].source).source_sha256 == saved['config'].source_sha256
    contexts = {name: make_context(saved, zone, args.memory_budget_mib, systematic_row=name=='001') for name, zone in (('001',(0,0,1)),('017',(0,1,7)))}
    metadata = dict(base_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        worktree_dirty=bool(subprocess.check_output(['git','status','--porcelain'],text=True)),
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        implementation_sha256={name:hashlib.sha256((Path('src/emcd_sim')/name).read_bytes()).hexdigest() for name in
            ('single_channeling_tensor.py','multislice_reference.py','physical_elastic.py','xmcd_effective_mdff.py','atomic_multislice_geometry.py','gui/memory_budget.py')},
        fixed_energies_ev=base.ENERGIES, source_sha256=saved['config'].source_sha256,
        python=base.platform.python_version(),numpy=np.__version__,
        eta=1., beta=1., mdff='XMCD-constrained; unchanged normalization', post_edge_correction=False,
        primary_definition=base.DEFINITION,physical_limitations=base.LIMITATION,
        sampling_by_stage=dict(A='33x33, halfwidth 1 cycles/Angstrom, 64 depth nodes',
            B='193x193, halfwidth 0.5; 97/385 controls at 12 nm; fractional weights, 64 subpixels',
            C='33x33, halfwidth 1; original 64-node states reused, 128/256 tested, conditional 512; analytic finite-BW integral reference',
            C_step='100 nm, 512 nodes, maximum split step 0.02 nm, separate from production 0.04 nm'),
        thickness_convention='Requested depths reached exactly by existing FFT substeps, no unit-cell rounding; 2 nm output spacing. Sequential, compact checkpoints, no retained full-series wavefields.',
        memory_budget_mib=args.memory_budget_mib, original_017_reused=True,
        paper_url='https://arxiv.org/pdf/0704.1407',
        paper_conditions='FCC Ni near [001], G200 systematic-row approximation, row-projected LCC=G/2, top/bottom Thales detectors; raw difference/sum. Incoming/outgoing Bloch waves; no absorption in Fig5. Numerical voltage, off-row tilt and precise Fig5 energy not established from inspected manuscript.',
        comparison_limits='200 kV and ty=35 mrad are study choices, not verified paper values. Explicit systematic-row Fourier projection for [001], full ZOLZ for [017]; entrance-only IAM/XMCD model; native fixed energies, finite circular apertures. Not a quantitative reproduction.',
        batch_pixels=64, numerical_precision='float64/complex128', geometry={})
    for name, c in contexts.items():
        metadata['geometry'][name] = dict(settings=asdict(c['settings']), config=asdict(c['cfg']), systematic_row_projection=c['systematic_row'],
            frame=c['R'], beam_hkl=c['hkl'], g=c['g'], excitation_errors=c['s'], centers=c['centers'],
            transmitted_q=[0.,0.], zone_axis_q=-c['model'].elastic.microscope.incident_k_xy,
            electron_wavelength_angstrom=electron_wavelength_angstrom(c['settings'].voltage),
            thales_center=c['g'][c['hkl'].index((2,0,0))]/2,
            thales_radius=np.linalg.norm(c['g'][c['hkl'].index((2,0,0))])/2,
            laue_circle_center_full=-c['model'].elastic.microscope.incident_k_xy,
            row_projected_laue_center=c['g'][c['hkl'].index((2,0,0))]/2,
            magnetization_local=c['R']@np.array([0.,0.,1.]))
    base.write_json(root/'configuration.json', metadata)
    rows=[]; elastic_rows=[]; started=time.perf_counter()
    if args.full_zolz_control:
        cfull=make_context(saved,(0,0,1),args.memory_budget_mib,systematic_row=False)
        control=DetectorGrid(cfull['centers'],(RADII[2],),33,1.)
        control_rows=[];control_elastic=[]
        folder=root/'full_001_zolz_control';folder.mkdir(exist_ok=True)
        for t in base.thickness_sequence():
            point=calculate_point(root,'A','001',cfull,float(t),64,control)
            control_rows.extend(rows_for_point('A','001',cfull,float(t),64,control,point))
            for method in base.METHODS:
                for i,h in enumerate(cfull['hkl']):
                    control_elastic.append(dict(thickness_nm=t,solver=method,h=h[0],k=h[1],l=h[2],excitation_error=cfull['s'][i],exit_fraction=point[method+'__exit'][i],depth_average_fraction=point[method+'__average'][i]))
            del point
        base.write_csv(folder/'results.csv',control_rows)
        base.write_csv(folder/'elastic_beams.csv',control_elastic)
        base.write_json(folder/'configuration.json',dict(settings=asdict(cfull['settings']),config=asdict(cfull['cfg']),frame=cfull['R'],
            beam_hkl=cfull['hkl'],g=cfull['g'],excitation_errors=cfull['s'],centers=cfull['centers'],
            systematic_row_projection=False,execution_metadata=metadata,role='Full-ZOLZ control; not the paper systematic-row approximation'))
        np.savez_compressed(folder/'results.npz',**{k:np.array([r[k] for r in control_rows]) for k in control_rows[0]})
    # A: representative checks, then full new [001] scan; [017] is loaded only.
    c=contexts['001']; d=DetectorGrid(c['centers'], (RADII[2],), 33, 1.)
    for t in (10.,30.,100.)+tuple(t for t in base.thickness_sequence() if t not in (10.,30.,100.)):
        point=calculate_point(root,'A','001',c,t,64,d)
        rows.extend(rows_for_point('A','001',c,t,64,d,point))
        for method in base.METHODS:
            for i,h in enumerate(c['hkl']):
                elastic_rows.append(dict(thickness_nm=t,solver=method,h=h[0],k=h[1],l=h[2],excitation_error=c['s'][i],exit_fraction=point[method+'__exit'][i],depth_average_fraction=point[method+'__average'][i]))
        del point
    # B: finer detector grid; no full secondary aperture thickness scans.
    for name,c in contexts.items():
        d=DetectorGrid(c['centers'], RADII, 193, .5)
        for t in REPRESENTATIVE:
            point=calculate_point(root,'B',name,c,t,64,d); rows.extend(rows_for_point('B',name,c,t,64,d,point)); del point
        for grid in (97,385):
            control=DetectorGrid(c['centers'], RADII, grid, .5)
            point=calculate_point(root,'B-grid',name,c,12.,64,control)
            rows.extend(rows_for_point('B-grid',name,c,12.,64,control,point)); del point
    # C: original geometry, reuse all 64-node detector states from completed scan.
    c=contexts['017']; d=DetectorGrid(c['centers'],(RADII[2],),33,1.)
    for t in DEPTH_THICKNESSES:
        point={m+'__raw':np.stack([old[m+'__'+k][int(t/2)] for k in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus')],axis=-1)[None] for m in base.METHODS}
        rows.extend(rows_for_point('C','017',c,t,64,d,point)); del point
        exact=calculate_point(root,'C-exact','017',c,t,64,d,analytic=True)
        rows.extend(rows_for_point('C-exact','017',c,t,64,d,exact))
        for depth in (128,256):
            point=calculate_point(root,'C','017',c,t,depth,d); rows.extend(rows_for_point('C','017',c,t,depth,d,point))
        error = abs(base.observables(point['bloch__raw'][0])[base.METRICS[0]]-base.observables(exact['bloch__raw'][0])[base.METRICS[0]]).max()
        intensity_error = np.max(abs(point['bloch__raw']-exact['bloch__raw'])/exact['bloch__raw'])
        if error > 1e-4 or intensity_error > 1e-6:
            point=calculate_point(root,'C','017',c,t,512,d); rows.extend(rows_for_point('C','017',c,t,512,d,point))
        del point, exact
    step_context=dict(c,cfg=replace(c['cfg'],slice_step=.02))
    point=calculate_point(root,'C-step002','017',step_context,100.,512,d)
    rows.extend(rows_for_point('C-step002','017',step_context,100.,512,d,point));del point
    base.write_csv(root/'results.csv', rows); base.write_csv(root/'elastic_001.csv',elastic_rows)
    np.savez_compressed(root/'results.npz', **{k:np.array([r[k] for r in rows]) for k in rows[0]}, configuration_json=np.array(json.dumps(base.clean(metadata))))
    analyze_results(root,rows,old)
    cell,planes=atomic_audit(root); plot_results(root,rows,old,cell,planes)
    assert base.file_hashes('outputs/ni_017_thickness_0_100nm') == original
    assert base.load_wien2k_xmcd(saved['config'].source).source_sha256 == saved['config'].source_sha256
    base.write_json(root/'preservation.json',dict(original_017_files_unchanged=True,original_hashes=original,mdff_source_unchanged=True,runtime_seconds=time.perf_counter()-started))
    print('Study complete. Atomic-3D scattering explicitly unavailable.',flush=True)


if __name__ == '__main__':main()
