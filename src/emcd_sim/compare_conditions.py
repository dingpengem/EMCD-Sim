"""Compare FCC Ni entrance-only EMCD reciprocal maps for diffraction presets.

This is an illustrative Gaussian-MDFF comparison, not quantitative Ni EMCD.
The same physical 000-centered reciprocal grid and global color limits are used
for each map, so a visually larger response is not simply an autoscaled panel.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .benchmark import nickel_physical_benchmark
from .crystal import fcc_nickel
from .diffraction import select_diffraction_setup

CONDITIONS = ("two-beam", "near-2bc", "symmetric-3bc", "zone-axis")
L3_EV = 852.7


def calculate_maps(
    *, thickness_nm: float = 30.0, acceleration_kv: float = 200.0,
    grid: int = 65, depth_steps: int = 64, beam_order: int = 3,
    max_beams: int = 13, b_factor: float = 0.0,
) -> dict:
    """Calculate condition-specific L3 maps without an unnecessary full EELS sweep."""
    if not (np.isfinite(thickness_nm) and thickness_nm > 0 and
            np.isfinite(acceleration_kv) and acceleration_kv > 0 and
            np.isfinite(b_factor) and b_factor >= 0):
        raise ValueError("thickness/accelerating voltage must be positive, B nonnegative")
    if grid < 9 or depth_steps < 2 or beam_order < 1 or max_beams < 3:
        raise ValueError("grid>=9, depth_steps>=2, beam_order>=1, max_beams>=3")
    crystal = fcc_nickel()
    maps = {}
    for condition in CONDITIONS:
        setup = select_diffraction_setup(
            condition, crystal, acceleration_kv, beam_order=beam_order,
            max_beams=max_beams,
        )
        sim = nickel_physical_benchmark(
            tilt_mrad_xy=setup.tilt_mrad_xy,
            acceleration_kv=acceleration_kv,
            debye_waller_b_angstrom2=b_factor,
            beams_override=setup.beams,
            diffraction_condition=setup.name,
        )
        # SimulationResult stores the L3 map at the point nearest the reference
        # energy (852.7 eV). Two points satisfy the existing energy-array API.
        result = sim.run(
            np.array((L3_EV, L3_EV + 0.05)), thickness_nm=thickness_nm,
            grid_size=grid, depth_steps=depth_steps,
        )
        a = float(result.chiral_spectrum("A")[0])
        b = float(result.chiral_spectrum("B")[0])
        maps[condition] = {
            "qx": result.qx_angstrom_inv,
            "qy": result.qy_angstrom_inv,
            "nonmagnetic": result.nonmag_map_at_l3,
            "magnetic": result.magnetic_map_at_l3,
            "beam_hkl": np.asarray(sim.elastic.beams.hkl, dtype=int),
            "beam_g": sim.elastic.reciprocal_vectors_xy,
            "apertures": {name: (float(det.center_q_xy[0]),
                                  float(det.center_q_xy[1]), float(det.radius_q))
                          for name, det in sim.detectors.items()},
            "chiral_groups": sim.chiral_groups,
            "tilt_mrad_xy": setup.tilt_mrad_xy,
            "approximation": setup.approximation,
            "A": a, "B": b,
            "difference": a - b,
            "asymmetry": (a - b) / (a + b) if a + b else 0.0,
        }
    return maps


def _draw_map(ax, image, item, *, cmap, limit, title):
    from matplotlib.patches import Circle

    extent = (float(item["qx"].min()), float(item["qx"].max()),
              float(item["qy"].min()), float(item["qy"].max()))
    im = ax.imshow(image, origin="lower", extent=extent, cmap=cmap,
                   vmin=-limit, vmax=limit, interpolation="nearest")
    for hkl, g in zip(item["beam_hkl"], item["beam_g"]):
        x, y = g
        if extent[0] <= x <= extent[1] and extent[2] <= y <= extent[3]:
            ax.plot(x, y, marker="+", color="black", markersize=4, alpha=0.65)
            label = "(" + ",".join(str(int(n)) for n in hkl) + ")"
            ax.annotate(label, (x, y), xytext=(3, 4),
                        textcoords="offset points", fontsize=6, color="black")
    for name, (x, y, r) in item["apertures"].items():
        ax.add_patch(Circle((x, y), r, fill=False, color="black", lw=1.0))
        ax.annotate(name, (x, y), fontsize=7, color="black", ha="center", va="center")
    ax.set(xlabel=r"$q_x$ ($\AA^{-1}$)", ylabel=r"$q_y$ ($\AA^{-1}$)", title=title)
    ax.set_aspect("equal")
    ax.set_xlim(extent[:2]); ax.set_ylim(extent[2:])
    return im


def save_comparison(maps: dict, output: Path | str, *, thickness_nm: float,
                    acceleration_kv: float, b_factor: float, grid: int,
                    depth_steps: int) -> dict:
    """Write plots + compact numeric arrays, all using the same reciprocal axes."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    scale = max(float(np.max(np.abs(m["magnetic"]))) for m in maps.values())
    scale = max(scale, 1e-15)
    # Suppress relative contrast where the *nonmagnetic* signal is effectively
    # zero. Use a single global threshold/scale to avoid hiding differences.
    max_nonmag = max(float(np.max(m["nonmagnetic"])) for m in maps.values())
    threshold = max(max_nonmag * 1e-3, 1e-15)
    relative = {}
    for condition, item in maps.items():
        nonmag = item["nonmagnetic"]
        rel = np.divide(item["magnetic"], nonmag,
                        out=np.full(nonmag.shape, np.nan, dtype=float),
                        where=nonmag > threshold)
        relative[condition] = rel
    finite_max = [float(np.max(np.abs(x[np.isfinite(x)])))
                  for x in relative.values() if np.any(np.isfinite(x))]
    contrast_limit = max(finite_max or [0.], default=0.)
    contrast_limit = max(contrast_limit, 1e-12)

    fig, axs = plt.subplots(2, len(maps), figsize=(17.0, 8.3),
                            constrained_layout=True, squeeze=False)
    images = []
    infos = {}
    data = {"energy_ev": np.array(L3_EV),
            "grid": np.array(grid), "thickness_nm": np.array(thickness_nm)}
    for col, (condition, item) in enumerate(maps.items()):
        x_tilt, y_tilt = item["tilt_mrad_xy"]
        header = (f"{condition} | {len(item['beam_hkl'])} beams\n"
                  f"tilt ({x_tilt:+.2f}, {y_tilt:+.2f}) mrad")
        images.append(_draw_map(axs[0,col], item["magnetic"], item,
                                cmap="coolwarm", limit=scale, title=header))
        _draw_map(axs[1,col], np.ma.masked_invalid(relative[condition]), item,
                  cmap="coolwarm", limit=contrast_limit,
                  title=f"M/N | A−B={item['difference']:.3g} (arb.)")
        suffix = condition.replace("-", "_")
        data[f"{suffix}_magnetic"] = item["magnetic"]
        data[f"{suffix}_nonmagnetic"] = item["nonmagnetic"]
        data[f"{suffix}_magnetic_over_nonmagnetic"] = relative[condition]
        data[f"{suffix}_beam_hkl"] = item["beam_hkl"]
        data[f"{suffix}_beam_g_xy_inv_angstrom"] = item["beam_g"]
        data[f"{suffix}_tilt_mrad_xy"] = np.array(item["tilt_mrad_xy"])
        infos[condition] = {
            "beam_count": len(item["beam_hkl"]),
            "beam_hkl": item["beam_hkl"].tolist(),
            "incident_tilt_mrad_xy": list(item["tilt_mrad_xy"]),
            "apertures": {k:list(v) for k,v in item["apertures"].items()},
            "chiral_groups": item["chiral_groups"],
            "detector_A": item["A"], "detector_B": item["B"],
            "difference_arbitrary": item["difference"],
            "asymmetry": item["asymmetry"],
            "approximation": item["approximation"],
        }
    first = next(iter(maps.values()))
    data["qx_inv_angstrom"] = first["qx"]
    data["qy_inv_angstrom"] = first["qy"]
    np.savez_compressed(output / "emcd_condition_maps.npz", **data)
    fig.colorbar(images[0], ax=list(axs[0]), fraction=.015, shrink=.68,
                 label="Magnetic contribution M (arb. units)")
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import Normalize
    sm = ScalarMappable(norm=Normalize(-contrast_limit, contrast_limit),cmap="coolwarm")
    fig.colorbar(sm, ax=list(axs[1]), fraction=.015, shrink=.68,
                 label="M/N where nonmagnetic > global threshold")
    fig.suptitle("FCC Ni [001] · L3 = 852.7 eV · entrance-only · illustrative MDFF\n"
                 f"{acceleration_kv:g} kV · t={thickness_nm:g} nm · fixed axes and color scales",
                 fontsize=13)
    fig.savefig(output / "emcd_diffraction_conditions.png", dpi=135)
    fig.savefig(output / "emcd_diffraction_conditions.svg")
    plt.close(fig)
    metadata = {
        "material":"FCC Ni", "nominal_zone_axis":"[001]",
        "l3_energy_ev":L3_EV,
        "acceleration_kv":acceleration_kv,
        "thickness_nm":thickness_nm,
        "debye_waller_b_angstrom2":b_factor,
        "grid":grid, "depth_steps":depth_steps,
        "conditions":infos,
        "magnetic_abs_color_limit":scale,
        "magnetic_over_nonmagnetic_color_limit":contrast_limit,
        "low_signal_mask_threshold":threshold,
        "map_coordinates":"000-centered cycles/angstrom (fixed across conditions)",
        "approximation":"entrance-only, finite-beam IAM, Gaussian N(E)/M(E) with magnetic_fraction=0.12",
        "quantitative":False,
        "interpretation":"M/N is local magnetization-reversal contrast for the illustrative model, not integrated detector asymmetry. Aperture-based A-B is listed per condition.",
        "limitation":"Condition-specific preset tilts; basis cutoff and missing outgoing channeling prohibit direct quantitative comparison to measured EMCD.",
    }
    (output / "comparison_metadata.json").write_text(json.dumps(metadata, indent=2)+"\n", encoding="utf-8")
    return {"output":str(output), "plot":"emcd_diffraction_conditions.png",
            "conditions":list(maps),"energy_ev":L3_EV}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Compare FCC Ni L3 EMCD maps across diffraction conditions")
    parser.add_argument("--output",default="outputs/ni_condition_maps")
    parser.add_argument("--thickness-nm",type=float,default=30.)
    parser.add_argument("--acceleration-kv",type=float,default=200.)
    parser.add_argument("--grid",type=int,default=65)
    parser.add_argument("--steps",type=int,default=64)
    parser.add_argument("--beam-order",type=int,default=3)
    parser.add_argument("--max-beams",type=int,default=13)
    parser.add_argument("--b-factor",type=float,default=0.)
    args=parser.parse_args(argv)
    maps=calculate_maps(thickness_nm=args.thickness_nm,
        acceleration_kv=args.acceleration_kv, grid=args.grid,
        depth_steps=args.steps, beam_order=args.beam_order,
        max_beams=args.max_beams,b_factor=args.b_factor)
    summary=save_comparison(maps,args.output,thickness_nm=args.thickness_nm,
        acceleration_kv=args.acceleration_kv,b_factor=args.b_factor,
        grid=args.grid,depth_steps=args.steps)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
