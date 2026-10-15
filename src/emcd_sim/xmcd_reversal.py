"""Magnetic parity of XMCD-effective, entrance-only relative intensities."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess

import numpy as np

from .benchmark import nickel_physical_benchmark
from .crystal import fcc_nickel
from .diffraction import select_diffraction_setup
from .mdff_tensor import DipoleTensor
from .single_channeling_tensor import run_tensor_single_channeling
from .wien2k_xmcd import load_wien2k_xmcd
from .xmcd_effective_mdff import effective_tensor_from_xmcd

CONDITIONS = ('zone-axis', 'two-beam', 'near-2bc', 'symmetric-3bc')


def normalized_signal(numerator, denominator, rtol=1e-12):
    """NaN below rtol times the peak denominator; return validity explicitly."""
    denominator = np.asarray(denominator, dtype=float)
    threshold = rtol * np.max(np.abs(denominator))
    valid = np.isfinite(denominator) & (denominator > threshold)
    return np.divide(numerator, denominator, out=np.full_like(denominator, np.nan),
                     where=valid), valid


def parity_spectra(plus, minus):
    """Use physical aperture groups and a common reversal-even denominator."""
    if not np.array_equal(plus.energy_ev, minus.energy_ev):
        raise ValueError('Reversal energy grids must match')
    a, b = plus.chiral_spectrum('A'), plus.chiral_spectrum('B')
    c, d = minus.chiral_spectrum('A'), minus.chiral_spectrum('B')
    dp, dm = a-b, c-d
    sp, sm = a+b, c+d
    odd, even, ref = (dp-dm)/2, (dp+dm)/2, (sp+sm)/2
    rawp, vp = normalized_signal(dp, sp)
    rawm, vm = normalized_signal(dm, sm)
    ao, valid = normalized_signal(odd, ref)
    ae, _ = normalized_signal(even, ref)
    return dict(energy_ev=plus.energy_ev, I_A_plus=a, I_B_plus=b,
                I_A_minus=c, I_B_minus=d, delta_plus=dp, delta_minus=dm,
                delta_odd=odd, delta_even=even, sigma_plus=sp, sigma_minus=sm,
                sigma_ref=ref, A_raw_plus=rawp, A_raw_minus=rawm,
                A_odd=ao, A_even=ae, valid=valid,
                valid_raw_plus=vp, valid_raw_minus=vm)


@dataclass
class ReversalResult:
    spectra: dict
    maps: dict
    tensor_sources: tuple[str, str]


def run_xmcd_reversal(model, xmcd_file, energy_ev=None, *, eta=1., beta=1.,
                      thickness_nm=30., grid_size=65, depth_steps=64,
                      l3_energy_ev=852.7, l2_energy_ev=870.):
    """Pair +/-eta on the identical model, grid and source normalization.

    Only the effective imaginary antisymmetric tensor changes. This operation
    is not a prescription for reversal of an arbitrary external DFT tensor.
    """
    tensors = [effective_tensor_from_xmcd(xmcd_file, energy_ev, eta=sign*eta,
                                         beta=beta) for sign in (1, -1)]
    options = dict(thickness_nm=thickness_nm, grid_size=grid_size,
                   depth_steps=depth_steps)
    plus, minus = [run_tensor_single_channeling(model, t, **options,
                        reference_energy_ev=l3_energy_ev) for t in tensors]
    maps = {}
    for edge, reference in [('L3', l3_energy_ev), ('L2', l2_energy_ev)]:
        index = int(np.argmin(abs(tensors[0].energy_ev-reference)))
        selected = float(tensors[0].energy_ev[index])
        if edge == 'L3':
            rp, rm = plus, minus
        else:
            # Two adjacent samples satisfy DipoleTensor's energy-grid contract.
            start = min(index, len(tensors[0].energy_ev)-2)
            subset = [DipoleTensor(t.energy_ev[start:start+2],
                        t.tensor_angstrom2_per_ev[start:start+2], t.source) for t in tensors]
            rp, rm = [run_tensor_single_channeling(model, t, **options,
                        reference_energy_ev=selected) for t in subset]
        ip = rp.nonmag_map_at_l3 + rp.magnetic_map_at_l3
        im = rm.nonmag_map_at_l3 + rm.magnetic_map_at_l3
        maps[edge] = dict(energy_ev=selected, qx_inv_angstrom=rp.qx_angstrom_inv,
                         qy_inv_angstrom=rp.qy_angstrom_inv,
                         I_plus=ip, I_minus=im, I_odd=(ip-im)/2, I_even=(ip+im)/2)
    return ReversalResult(parity_spectra(plus, minus), maps,
                          tuple(t.source for t in tensors))


def plot_summary(result, path, condition):
    """Plotting is independent of the forward calculation."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    s = result.spectra
    fig, axes = plt.subplots(2, 1, figsize=(9, 7), constrained_layout=True)
    for key in ('delta_plus', 'delta_minus', 'delta_odd', 'delta_even'):
        axes[0].plot(s['energy_ev'], s[key], label=key)
    for key in ('A_raw_plus', 'A_raw_minus', 'A_odd', 'A_even'):
        axes[1].plot(s['energy_ev'], s[key], label=key)
    for ax in axes:
        for edge, m in result.maps.items():
            ax.axvline(m['energy_ev'], color='grey', linestyle=':', linewidth=.8)
            ax.text(m['energy_ev'], .98, edge, transform=ax.get_xaxis_transform(), va='top')
        ax.legend()
        ax.set_xlabel('Energy loss (eV)')
    axes[0].set_ylabel('Detector difference (relative intensity)')
    axes[1].set_ylabel('Normalized asymmetry')
    fig.suptitle(f'{condition}: XMCD-constrained effective-model diagnostic\n'
                 'Entrance-only; relative intensity; not quantitative Ni')
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--xmcd-file', type=Path, required=True)
    p.add_argument('--condition', choices=(*CONDITIONS, 'all'), default='near-2bc')
    p.add_argument('--output', type=Path, default=Path('outputs/ni_xmcd_reversal'))
    for flag, default in [('eta', 1.), ('beta', 1.), ('acceleration-kv', 200.),
                          ('thickness-nm', 30.), ('zone2d-max-g', 1.2),
                          ('offzone-tilt-mrad', 25.), ('l3-energy-ev', 852.7),
                          ('l2-energy-ev', 870.)]:
        p.add_argument('--'+flag, type=float, default=default)
    for flag, default in [('beam-order', 3), ('max-beams', 25), ('grid', 65), ('steps', 64),
                          ('energy-points', 185)]:
        p.add_argument('--'+flag, type=int, default=default)
    p.add_argument('--tilt-x-mrad', type=float)
    p.add_argument('--tilt-y-mrad', type=float)
    args = p.parse_args(argv)
    source = load_wien2k_xmcd(args.xmcd_file)  # hash exact bytes before calculations
    lo, hi = max(837., source.energy_ev[0]), min(882., source.energy_ev[-1])
    if args.energy_points < 2 or not lo <= args.l3_energy_ev <= hi or not lo <= args.l2_energy_ev <= hi:
        p.error('Require >=2 energy points and source coverage of L3/L2 references')
    energies = np.linspace(lo, hi, args.energy_points)
    try:
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'],
                     cwd=Path(__file__).resolve().parents[2], stderr=subprocess.DEVNULL).decode().strip()
    except (OSError, subprocess.CalledProcessError):
        commit = None
    for name in (CONDITIONS if args.condition == 'all' else (args.condition,)):
        setup = select_diffraction_setup(name, fcc_nickel(), args.acceleration_kv,
            beam_order=args.beam_order, max_beams=args.max_beams,
            zone2d_max_g=args.zone2d_max_g if name == 'zone-axis' else None,
            offzone_tilt_mrad=args.offzone_tilt_mrad,
            tilt_x_mrad=args.tilt_x_mrad, tilt_y_mrad=args.tilt_y_mrad)
        model = nickel_physical_benchmark(tilt_mrad_xy=setup.tilt_mrad_xy,
            acceleration_kv=args.acceleration_kv, beams_override=setup.beams,
            diffraction_condition=name)
        result = run_xmcd_reversal(model, args.xmcd_file, energies, eta=args.eta,
            beta=args.beta, thickness_nm=args.thickness_nm, grid_size=args.grid,
            depth_steps=args.steps, l3_energy_ev=args.l3_energy_ev, l2_energy_ev=args.l2_energy_ev)
        folder = args.output / name
        folder.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(folder/'magnetic_parity_spectra.npz', **result.spectra)
        for edge, data in result.maps.items():
            np.savez_compressed(folder/f'magnetic_parity_{edge}_map.npz', **data)
        metadata = dict(xmcd_file=str(args.xmcd_file.resolve()), xmcd_sha256=source.source_sha256,
            model='XMCD-constrained axisymmetric effective tensor; entrance-only',
            eta=args.eta, beta=args.beta, tensor_sources=result.tensor_sources,
            reversal='Txy=+i*eta*(RP-LP)/2 -> -i*eta*(RP-LP)/2; Tyx=-Txy; diagonal unchanged',
            normalization='Both tensors divided by the same peak source N=(RP+LP)/2',
            denominator_policy='NaN unless denominator > 1e-12 times its spectral peak',
            thickness_nm=args.thickness_nm, acceleration_kv=args.acceleration_kv,
            tilt_mrad_xy=setup.tilt_mrad_xy, condition=name, approximation=setup.approximation,
            beam_hkl=np.asarray(setup.beams.hkl).tolist(),
            detectors={k: dict(center_q_xy=v.center_q_xy, radius_q=v.radius_q)
                       for k,v in model.detectors.items()}, chiral_groups=model.chiral_groups,
            reciprocal_coordinate_units='cycles/angstrom', grid_size=args.grid,
            map_halfwidth_q=1., depth_steps=args.steps, energy_points=args.energy_points,
            energy_range_ev=[lo, hi], selected_energies_ev={k:v['energy_ev'] for k,v in result.maps.items()},
            reference_energies_ev={'L3':args.l3_energy_ev, 'L2':args.l2_energy_ev},
            beam_order=args.beam_order, zone2d_max_g=args.zone2d_max_g, max_beams=args.max_beams,
            software_commit=commit, absolute_cross_section=False, outgoing_channeling=False,
            quantitative_Ni=False)
        (folder/'metadata.json').write_text(json.dumps(metadata, indent=2)+'\n', encoding='utf-8')
        plot_summary(result, folder/'magnetic_parity_summary.png', name)
        i = int(np.argmin(abs(energies-args.l3_energy_ev)))
        values = {k: (float(result.spectra[k][i]) if np.isfinite(result.spectra[k][i]) else None)
                  for k in ('A_raw_plus', 'A_odd', 'A_even')}
        print(json.dumps(dict(condition=name, L3_energy_ev=float(energies[i]),
                              **values, output=str(folder)), allow_nan=False))


if __name__ == '__main__':
    main()
