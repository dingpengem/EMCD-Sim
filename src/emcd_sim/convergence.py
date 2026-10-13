"""FCC Ni incoming Bloch-wave basis-cutoff convergence diagnostics.

All inelastic observables remain the *illustrative*, entrance-only Gaussian
MDFF of the existing simulator. This module cannot validate DFT MDFF or
quantitative experimental EMCD.
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .benchmark import nickel_physical_benchmark
from .crystal import fcc_nickel
from .diffraction import select_diffraction_setup
from .elastic import BeamSet

CONDITIONS = ("zone-axis", "two-beam", "near-2bc", "symmetric-3bc")


@dataclass(frozen=True)
class ConvergenceConfig:
    conditions: tuple[str, ...] = ("zone-axis", "symmetric-3bc")
    g_cutoffs_inv_angstrom: tuple[float, ...] = (0.75, 1.2, 1.4, 1.8)
    thickness_nm: tuple[float, ...] = (10., 30., 50.)
    acceleration_kv: float = 200.
    energy_ev: float = 852.7
    max_beams: int = 81
    reciprocal_grid: int = 25
    depth_steps: int = 20
    b_factor_angstrom2: float = 0.
    offzone_tilt_mrad: float = 25.

    def validate(self) -> None:
        if not self.conditions or len(set(self.conditions)) != len(self.conditions):
            raise ValueError("conditions must be nonempty and unique")
        if any(x not in CONDITIONS for x in self.conditions):
            raise ValueError(f"conditions must be selected from {CONDITIONS}")
        for name in ("g_cutoffs_inv_angstrom", "thickness_nm"):
            arr = np.asarray(getattr(self, name), dtype=float)
            if arr.ndim != 1 or len(arr) < (2 if name.startswith("g_") else 1):
                raise ValueError(f"{name} requires an ordered nonempty list (2+ cutoffs)")
            if not np.all(np.isfinite(arr)) or np.any(arr <= 0) or np.any(np.diff(arr) <= 0):
                raise ValueError(f"{name} must contain positive increasing finite values")
        for value in (self.acceleration_kv, self.energy_ev, self.b_factor_angstrom2,
                      self.offzone_tilt_mrad):
            if not np.isfinite(value):
                raise ValueError("physics parameters must be finite")
        if self.acceleration_kv <= 0 or self.energy_ev <= 0 or self.b_factor_angstrom2 < 0:
            raise ValueError("positive voltage/energy and nonnegative B are required")
        if self.offzone_tilt_mrad < 0 or self.max_beams < 3 or self.reciprocal_grid < 9 or self.depth_steps < 2:
            raise ValueError("invalid beam limit, grid, depth steps or off-zone tilt")


def _total_variation(reference_hkl, reference_intensity, hkl, intensity) -> float:
    """Total-variation distance of full normalized beam intensity vectors.

    Intensities absent from a smaller basis are treated as zero. This is a
    robust basis-comparison metric, not a proof of convergence to the infinite
    Bloch-wave solution.
    """
    a = {tuple(h): float(p) for h, p in zip(hkl, intensity)}
    b = {tuple(h): float(p) for h, p in zip(reference_hkl, reference_intensity)}
    return 0.5 * sum(abs(a.get(k, 0.) - b.get(k, 0.)) for k in a.keys() | b.keys())


def run_convergence(config: ConvergenceConfig, output: str | Path) -> dict:
    """Compare 2D ZOLZ cutoffs at the same physical tilt and detector geometry.

    The largest included cutoff is a *finite-basis numerical reference*, not
    an independently validated or physically converged benchmark.
    """
    config.validate()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    crystal = fcc_nickel()
    basis_list = [BeamSet.zolz(crystal, cut, max_beams=config.max_beams)
                  for cut in config.g_cutoffs_inv_angstrom]
    sizes = [len(b.hkl) for b in basis_list]
    if any(b >= config.max_beams for b in sizes):
        raise ValueError("max_beams may truncate the cutoff basis; increase --max-beams")
    if sizes[-1] == sizes[0]:
        raise ValueError("all cutoffs select the same beams; choose a wider cutoff range")

    ncond, ncut, nt = len(config.conditions), len(basis_list), len(config.thickness_nm)
    data = {key: np.empty((ncond, ncut, nt), dtype=float)
            for key in ("elastic_000", "elastic_200", "elastic_m200", "total_elastic",
                        "emcd_difference", "emcd_asymmetry", "elastic_total_variation",
                        "asymmetry_deviation")}
    records = []
    tilts = {}
    for ic, condition in enumerate(config.conditions):
        # Preset supplies the *same incident tilt for every basis*; unlike
        # 'two-beam' mode, the propagated basis is always the growing 2D ZOLZ.
        preset = select_diffraction_setup(condition, crystal, config.acceleration_kv,
                                         offzone_tilt_mrad=config.offzone_tilt_mrad)
        tilt = tuple(float(v) for v in preset.tilt_mrad_xy)
        tilts[condition] = tilt
        basis_intensities = []
        for ib, beams in enumerate(basis_list):
            sim = nickel_physical_benchmark(
                tilt_mrad_xy=tilt, acceleration_kv=config.acceleration_kv,
                debye_waller_b_angstrom2=config.b_factor_angstrom2,
                beams_override=beams, diffraction_condition=condition,
            )
            psi = sim.elastic.amplitudes(np.asarray(config.thickness_nm))
            power = np.abs(psi)**2
            basis_intensities.append(power)
            indices = {h: j for j, h in enumerate(beams.hkl)}
            for it, thickness in enumerate(config.thickness_nm):
                elastic = power[it]
                data["elastic_000"][ic, ib, it] = float(elastic[0])
                for name, hkl in (("elastic_200", (2, 0, 0)),
                                  ("elastic_m200", (-2, 0, 0))):
                    data[name][ic, ib, it] = float(elastic[indices[hkl]]) if hkl in indices else 0.
                data["total_elastic"][ic, ib, it] = float(elastic.sum())
                # Existing scalar illustrative MDFF is evaluated at Ni L3,
                # with two energies only to satisfy the current API.
                res = sim.run(np.asarray((config.energy_ev, config.energy_ev + 0.05)),
                              thickness_nm=thickness, grid_size=config.reciprocal_grid,
                              depth_steps=config.depth_steps)
                data["emcd_difference"][ic, ib, it] = float(res.difference()[0])
                data["emcd_asymmetry"][ic, ib, it] = float(res.asymmetry()[0])
        ref = basis_intensities[-1]
        for ib, beams in enumerate(basis_list):
            for it, thickness in enumerate(config.thickness_nm):
                error = _total_variation(basis_list[-1].hkl, ref[it],
                                         beams.hkl, basis_intensities[ib][it])
                data["elastic_total_variation"][ic, ib, it] = error
                da = abs(data["emcd_asymmetry"][ic, ib, it] -
                         data["emcd_asymmetry"][ic, -1, it])
                data["asymmetry_deviation"][ic, ib, it] = da
                records.append((condition, *tilt, float(config.g_cutoffs_inv_angstrom[ib]),
                                len(beams.hkl), float(thickness),
                                *[float(data[name][ic, ib, it]) for name in data]))

    with (output / "convergence_results.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(("condition", "tilt_x_mrad", "tilt_y_mrad", "g_cutoff_inv_A",
                         "beam_count", "thickness_nm", *data.keys()))
        writer.writerows(records)
    np.savez_compressed(output / "convergence_results.npz",
                        conditions=np.asarray(config.conditions),
                        g_cutoffs_inv_angstrom=np.asarray(config.g_cutoffs_inv_angstrom),
                        thickness_nm=np.asarray(config.thickness_nm),
                        beam_counts=np.asarray(sizes), **data)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(ncond, 3, figsize=(12, 3.3*ncond),
                             squeeze=False, constrained_layout=True)
    for ic, condition in enumerate(config.conditions):
        for it, thickness in enumerate(config.thickness_nm):
            label = f"{thickness:g} nm"
            axes[ic, 0].plot(sizes, data["elastic_000"][ic, :, it], "o-", label=label)
            axes[ic, 1].plot(sizes, 100*data["emcd_asymmetry"][ic, :, it], "o-", label=label)
            axes[ic, 2].plot(sizes, data["elastic_total_variation"][ic, :, it], "o-", label=label)
        for ax in axes[ic]:
            ax.set_xlabel("Number of 2D ZOLZ beams")
            ax.grid(alpha=.25)
            ax.legend(fontsize=8)
        axes[ic, 0].set_ylabel("I(000) (elastic normalized)")
        axes[ic, 1].set_ylabel("Illustrative L3 asymmetry (%)")
        axes[ic, 2].set_ylabel("Elastic total variation vs largest basis")
        axes[ic, 0].set_title(condition + " | incident tilt " + str(tuple(round(x,2) for x in tilts[condition])) + " mrad")
        axes[ic, 1].set_title("EMCD sensitivity to basis size")
        axes[ic, 2].set_title("Finite-reference elastic discrepancy")
    fig.suptitle("FCC Ni [001], 200 kV baseline (or configured kV) | entrance-only illustrative MDFF\n"
                 "Largest beam set is NOT an independently validated converged solution", fontsize=11)
    fig.savefig(output / "basis_convergence.png", dpi=150)
    plt.close(fig)

    metadata = {
        "material": "FCC Ni", "nominal_zone_axis": "[001]",
        "acceleration_kv": config.acceleration_kv, "energy_ev": config.energy_ev,
        "thickness_nm": list(config.thickness_nm), "conditions": list(config.conditions),
        "incident_tilt_mrad_by_condition": {k: list(v) for k, v in tilts.items()},
        "cutoff_inv_angstrom": list(config.g_cutoffs_inv_angstrom),
        "beam_count": sizes, "beam_hkl_by_cutoff": [list(map(list, b.hkl)) for b in basis_list],
        "reference_basis_cutoff_inv_angstrom": config.g_cutoffs_inv_angstrom[-1],
        "reference_is_finite_not_validated": True,
        "beam_limit": config.max_beams, "reciprocal_grid": config.reciprocal_grid,
        "depth_steps": config.depth_steps, "b_factor_angstrom2":config.b_factor_angstrom2,
        "approximation": "entrance-only, 2D ZOLZ finite-beam IAM; illustrative Gaussian MDFF, no outgoing channeling",
        "physics_quantitative": False,
        "two_beam_note": "two-beam selects the 2BC incident tilt and Thales apertures; its convergence series grows a 2D ZOLZ basis, never artificially retains only two beams",
        "limitations": "No independent reference comparison, beam convergence certificate, DFT MDFF, outgoing channeling, absorption/TDS or calibrated cross section",
    }
    (output / "convergence_metadata.json").write_text(json.dumps(metadata, indent=2)+"\n",encoding="utf-8")
    return {"output": str(output), "conditions": list(config.conditions),
            "beam_counts": sizes, "calculations": len(records),
            "max_elastic_norm_error": float(np.max(np.abs(data["total_elastic"]-1))),
            "reference_is_finite_not_validated": True}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="FCC Ni 2D Bloch-wave basis convergence; illustrative MDFF only")
    parser.add_argument("--conditions", nargs="+", choices=CONDITIONS, default=["zone-axis", "symmetric-3bc"])
    parser.add_argument("--g-cutoffs", nargs="+", type=float, default=[.75, 1.2, 1.4, 1.8])
    parser.add_argument("--thickness-nm", nargs="+", type=float, default=[10.,30.,50.])
    parser.add_argument("--acceleration-kv", type=float, default=200.)
    parser.add_argument("--energy-ev", type=float, default=852.7)
    parser.add_argument("--max-beams", type=int, default=81)
    parser.add_argument("--grid", type=int, default=25)
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--b-factor", type=float, default=0.)
    parser.add_argument("--offzone-tilt-mrad", type=float, default=25.)
    parser.add_argument("--output", default="outputs/ni_convergence")
    args = parser.parse_args(argv)
    config = ConvergenceConfig(
        conditions=tuple(args.conditions), g_cutoffs_inv_angstrom=tuple(args.g_cutoffs),
        thickness_nm=tuple(args.thickness_nm), acceleration_kv=args.acceleration_kv,
        energy_ev=args.energy_ev, max_beams=args.max_beams, reciprocal_grid=args.grid,
        depth_steps=args.steps, b_factor_angstrom2=args.b_factor,
        offzone_tilt_mrad=args.offzone_tilt_mrad,
    )
    try:
        result = run_convergence(config, args.output)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
