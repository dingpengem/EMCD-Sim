"""Portable entrance-only FCC Ni L3 tilt/thickness scanning and comparisons.

This scan deliberately reuses the existing illustrative MDFF model. Results are
*not* ab-initio predictions. The same physical aperture and reciprocal-space
coordinates are retained between systematic-row and 2D-ZOLZ comparisons.
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

CONDITIONS = ("systematic-row", "zone-axis", "two-beam", "near-2bc", "symmetric-3bc")


@dataclass(frozen=True)
class ScanConfig:
    conditions: tuple[str, ...] = ("systematic-row", "zone-axis")
    tilt_x_mrad: tuple[float, ...] = (0.0,)
    tilt_y_mrad: tuple[float, ...] = (-10.0, -5.0, 0.0, 5.0, 10.0)
    thickness_nm: tuple[float, ...] = (10.0, 20.0, 30.0, 40.0, 50.0)
    energy_ev: float = 852.7
    acceleration_kv: float = 200.0
    beam_order: int = 3
    max_beams: int = 13
    zone2d_max_g: float = 1.2
    grid: int = 33
    steps: int = 32
    b_factor: float = 0.0

    def validate(self) -> None:
        if not self.conditions or len(set(self.conditions)) != len(self.conditions):
            raise ValueError("conditions must be a nonempty set of unique modes")
        if any(item not in CONDITIONS for item in self.conditions):
            raise ValueError(f"conditions must be chosen from {CONDITIONS}")
        for name in ("tilt_x_mrad", "tilt_y_mrad", "thickness_nm"):
            vals = np.asarray(getattr(self, name), dtype=float)
            if vals.ndim != 1 or not len(vals) or not np.all(np.isfinite(vals)):
                raise ValueError(f"{name} must be a finite nonempty 1D list")
            if len(np.unique(vals)) != len(vals) or np.any(np.diff(vals) <= 0):
                raise ValueError(f"{name} must be unique and increasing")
        if any(t <= 0 for t in self.thickness_nm):
            raise ValueError("thickness_nm must be positive")
        if (not np.all(np.isfinite((self.energy_ev,self.acceleration_kv,self.b_factor))) or
            self.energy_ev <= 0 or self.acceleration_kv <= 0 or self.b_factor < 0):
            raise ValueError("energy/accelerating voltage must be positive; B nonnegative")
        if self.grid < 9 or self.steps < 2 or self.max_beams < 2 or self.beam_order < 1:
            raise ValueError("grid >= 9, steps >= 2, max_beams >= 2, beam_order >= 1 required")
        if self.zone2d_max_g <= 0:
            raise ValueError("zone2d_max_g must be positive")
        if len(self.tilt_x_mrad)*len(self.tilt_y_mrad)*len(self.thickness_nm)*len(self.conditions) > 10000:
            raise ValueError("scan exceeds 10000 combinations; split into smaller scans")


def _one_energy_result(sim, thickness: float, energy: float, grid: int, steps: int):
    # The existing simulation API requires a two-point strictly increasing
    # energy array. Its L3-like sampled map is at the requested first point.
    return sim.run(np.array((energy, energy + 0.05)), thickness_nm=thickness,
                   grid_size=grid, depth_steps=steps)


def _heatmap(ax, matrix, x, y, name, unit, cmap, symmetric=False, bound=None):
    from matplotlib.colors import TwoSlopeNorm
    a = np.asarray(matrix, dtype=float)
    if bound is None:
        bound = float(np.max(np.abs(a))) if symmetric else float(np.max(a))
    bound = max(float(bound), 1e-15)
    kwargs = {"cmap": cmap, "origin": "lower", "aspect": "auto", "interpolation": "nearest"}
    if symmetric:
        kwargs["norm"] = TwoSlopeNorm(vmin=-bound, vcenter=0, vmax=bound)
    else:
        kwargs["vmin"], kwargs["vmax"] = (0, bound)
    if len(x) == 1 or len(y) == 1:
        def edges(v):
            v = np.asarray(v, dtype=float)
            if len(v) == 1:
                return v[0] - 0.5, v[0] + 0.5
            return v[0] - (v[1]-v[0])/2, v[-1] + (v[-1]-v[-2])/2
        xx, yy = edges(x), edges(y)
        im = ax.imshow(a, extent=(xx[0], xx[1], yy[0], yy[1]), **kwargs)
    else:
        ex = (x[0]-(x[1]-x[0])/2, x[-1]+(x[-1]-x[-2])/2)
        ey = (y[0]-(y[1]-y[0])/2, y[-1]+(y[-1]-y[-2])/2)
        im = ax.imshow(a, extent=(*ex, *ey), **kwargs)
    ax.set(xlabel="Thickness (nm)", ylabel="Y tilt (mrad)", title=name)
    ax.figure.colorbar(im, ax=ax, shrink=0.84, label=unit)


def _save_plots(directory: Path, config: ScanConfig, scans: dict, examples: dict) -> dict:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import TwoSlopeNorm
    from matplotlib.patches import Circle

    diff_lim = max(float(np.max(np.abs(s["difference"]))) for s in scans.values())
    asym_lim = max(float(np.max(np.abs(s["asymmetry"]))) for s in scans.values())
    diff_lim, asym_lim = max(diff_lim, 1e-15), max(asym_lim, 1e-15)

    for condition, s in scans.items():
        for ix, xval in enumerate(config.tilt_x_mrad):
            fig, axes = plt.subplots(1, 2, figsize=(11.4, 4.3), constrained_layout=True)
            _heatmap(axes[0], s["difference"][ix],
                     config.thickness_nm, config.tilt_y_mrad,
                     f"{condition}: L3 difference", "A−B (arb. units)", "coolwarm", True, diff_lim)
            _heatmap(axes[1], s["asymmetry"][ix],
                     config.thickness_nm, config.tilt_y_mrad,
                     f"{condition}: L3 asymmetry", "(A−B)/(A+B)", "coolwarm", True, asym_lim)
            fig.suptitle(f"FCC Ni [001] | X tilt = {xval:+g} mrad | entrance-only | illustrative MDFF")
            fig.savefig(directory / f"heatmaps_{condition}_x{ix:02d}.png", dpi=165)
            plt.close(fig)

    xi = int(np.argmin(abs(np.asarray(config.tilt_x_mrad))))
    ti = len(config.thickness_nm)//2
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.2), constrained_layout=True)
    for condition, s in scans.items():
        axes[0].plot(config.tilt_y_mrad, s["difference"][xi,:,ti], "o-", label=condition)
        axes[1].plot(config.tilt_y_mrad, s["asymmetry"][xi,:,ti], "o-", label=condition)
    for ax in axes:
        ax.set_xlabel("Y tilt (mrad)")
        ax.grid(alpha=0.25)
        ax.legend(fontsize=8)
    axes[0].set_ylabel("L3 A−B (arb. units)")
    axes[1].set_ylabel("L3 (A−B)/(A+B)")
    fig.suptitle(f"Fixed X tilt {config.tilt_x_mrad[xi]:+g} mrad; t={config.thickness_nm[ti]:g} nm")
    fig.savefig(directory / "comparison_y_tilt.png", dpi=175)
    plt.close(fig)

    mag_lim = max(float(np.max(np.abs(e["magnetic"]))) for e in examples.values())
    nonmag_lim = max(float(np.max(e["nonmagnetic"])) for e in examples.values())
    mag_lim = max(mag_lim, 1e-15)
    nonmag_lim = max(nonmag_lim, 1e-15)
    fig, axs = plt.subplots(len(examples), 2, figsize=(10, 4.2*len(examples)),
                            squeeze=False, constrained_layout=True)
    for i, (condition, item) in enumerate(examples.items()):
        xq, yq = item["qx"], item["qy"]
        ext = (xq.min(), xq.max(), yq.min(), yq.max())
        nm = axs[i,0].imshow(item["nonmagnetic"], origin="lower", extent=ext,
                              vmin=0, vmax=nonmag_lim, cmap="viridis")
        mm = axs[i,1].imshow(item["magnetic"], origin="lower", extent=ext,
                              norm=TwoSlopeNorm(vmin=-mag_lim,vcenter=0,vmax=mag_lim),
                              cmap="coolwarm")
        for col in range(2):
            ax = axs[i,col]
            for coords in item["beam_g"]:
                ax.plot(coords[0], coords[1], marker="+", ms=4, c="black", alpha=.5)
            for name, (cx,cy,r) in item["apertures"].items():
                ax.add_patch(Circle((cx,cy),r,fill=False,ec="white",lw=0.75))
                ax.annotate(name,(cx,cy),xytext=(2,2),textcoords="offset points",
                            fontsize=6,color="white")
            ax.set(xlabel=r"$q_x$ ($\AA^{-1}$)",ylabel=r"$q_y$ ($\AA^{-1}$)",
                   title=f"{condition}: {'N' if col == 0 else 'M'} term")
            ax.set_aspect("equal")
            ax.set_xlim(ext[0],ext[1])
            ax.set_ylim(ext[2],ext[3])
        fig.colorbar(nm,ax=axs[i,0],shrink=.75,label="nonmagnetic (arb.)")
        fig.colorbar(mm,ax=axs[i,1],shrink=.75,label="magnetic (arb.)")
    yi = int(np.argmin(abs(np.asarray(config.tilt_y_mrad))))
    fig.suptitle(f"Ni L3 | x={config.tilt_x_mrad[xi]:+g}, y={config.tilt_y_mrad[yi]:+g} mrad, "
                 f"t={config.thickness_nm[ti]:g} nm | identical reciprocal axes / color scales")
    fig.savefig(directory / "comparison_reciprocal_maps.png", dpi=165)
    plt.close(fig)
    return {"global_difference_half_range": diff_lim, "global_asymmetry_half_range": asym_lim,
            "global_magnetic_map_half_range": mag_lim,
            "global_nonmagnetic_map_max": nonmag_lim}


def run_scan(config: ScanConfig, output: Path | str) -> dict:
    """Save a full tilt-x × tilt-y × thickness cube for each requested basis."""
    config.validate()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    shape = (len(config.tilt_x_mrad),len(config.tilt_y_mrad),len(config.thickness_nm))
    xi = int(np.argmin(abs(np.asarray(config.tilt_x_mrad))))
    yi = int(np.argmin(abs(np.asarray(config.tilt_y_mrad))))
    ti = len(config.thickness_nm)//2
    crystal = fcc_nickel()
    scans, examples, details, records = {}, {}, {}, []
    for condition in config.conditions:
        arrays = {key:np.empty(shape,dtype=float) for key in ("A","B","difference","asymmetry")}
        description = None
        beam_hkl = None
        for ix, x in enumerate(config.tilt_x_mrad):
            for iy, y in enumerate(config.tilt_y_mrad):
                setup = select_diffraction_setup(
                    condition, crystal, config.acceleration_kv,
                    beam_order=config.beam_order, zone2d_max_g=(config.zone2d_max_g if condition == "zone-axis" else None),
                    max_beams=config.max_beams, tilt_x_mrad=x, tilt_y_mrad=y)
                sim = nickel_physical_benchmark(
                    tilt_mrad_xy=(x,y), acceleration_kv=config.acceleration_kv,
                    debye_waller_b_angstrom2=config.b_factor, beams_override=setup.beams,
                    diffraction_condition=setup.name)
                description = setup.approximation
                beam_hkl = np.asarray(setup.beams.hkl,dtype=int)
                for it, thickness in enumerate(config.thickness_nm):
                    result = _one_energy_result(sim, thickness, config.energy_ev, config.grid, config.steps)
                    a, b = result.chiral_spectrum("A")[0], result.chiral_spectrum("B")[0]
                    delta = a-b
                    asym = delta/(a+b) if a+b else 0.0
                    for key, value in zip(("A","B","difference","asymmetry"),(a,b,delta,asym)):
                        arrays[key][ix,iy,it] = float(value)
                    records.append((condition,float(x),float(y),float(thickness),float(a),float(b),
                                    float(delta),float(asym)))
                    if (ix,iy,it)==(xi,yi,ti):
                        examples[condition] = {
                            "qx":result.qx_angstrom_inv,
                            "qy":result.qy_angstrom_inv,
                            "nonmagnetic":result.nonmag_map_at_l3,
                            "magnetic":result.magnetic_map_at_l3,
                            "beam_g":sim.elastic.reciprocal_vectors_xy,
                            "beam_hkl":beam_hkl,
                            "apertures": {name:(*d.center_q_xy,d.radius_q)
                                          for name,d in sim.detectors.items()},
                        }
        scans[condition]=arrays
        details[condition]={"beam_count":len(beam_hkl),"beam_hkl":beam_hkl.tolist(),
                            "diffraction_approximation":description,
                            "chiral_definition":("A=RU+LD, B=RD+LU" if condition=="symmetric-3bc" else "A/B paired")}
        np.savez_compressed(output/f"scan_{condition}.npz",
            tilt_x_mrad=np.asarray(config.tilt_x_mrad),tilt_y_mrad=np.asarray(config.tilt_y_mrad),
            thickness_nm=np.asarray(config.thickness_nm),beam_hkl=beam_hkl,energy_ev=config.energy_ev,
            **arrays)
        example=examples[condition]
        np.savez_compressed(output/f"reciprocal_map_{condition}.npz",
            qx_inv_angstrom=example["qx"], qy_inv_angstrom=example["qy"],
            nonmagnetic_map=example["nonmagnetic"], magnetic_map=example["magnetic"],
            beam_hkl=example["beam_hkl"], beam_g_xy_inv_angstrom=example["beam_g"])
    with (output/"scan_results.csv").open("w",newline="",encoding="utf-8") as f:
        wr=csv.writer(f)
        wr.writerow(["condition","tilt_x_mrad","tilt_y_mrad","thickness_nm","L3_A","L3_B",
                     "L3_difference","L3_asymmetry"])
        wr.writerows(records)
    scales = _save_plots(output,config,scans,examples)
    meta={"model":"entrance_only_illustrative_gaussian_mdff",
          "quantitative":False,"material":"FCC Ni","zone_axis":"[001]",
          "energy_ev":config.energy_ev,"acceleration_kv":config.acceleration_kv,
          "tilt_x_mrad":list(config.tilt_x_mrad),"tilt_y_mrad":list(config.tilt_y_mrad),
          "thickness_nm":list(config.thickness_nm),"conditions":list(config.conditions),
          "beam_order":config.beam_order,"zone2d_max_g":config.zone2d_max_g,
          "max_beams":config.max_beams,"grid":config.grid,"steps":config.steps,
          "b_factor_angstrom2":config.b_factor,
          "tilt_definition":"absolute incoming tilt in nominal Ni [001] crystal frame; presets overridden",
          "example_indices":{"x":xi,"y":yi,"thickness":ti},
          "emcd_definition":"A-B and (A-B)/(A+B), based on each condition's aperture groups",
          "map_definition":"nonmagnetic/magnetic additive model terms, NOT pixelwise measured asymmetry",
          "approximation":"No outgoing channeling, TDS, finite probe, DFT MDFF or physical cross-section normalization",
          "comparison_color_limits":scales,"diffraction_models":details}
    (output/"scan_metadata.json").write_text(json.dumps(meta,indent=2)+"\n",encoding="utf-8")
    return {"output":str(output),"conditions":list(config.conditions),
            "calculations":len(records),"example_at":{"x_mrad":config.tilt_x_mrad[xi],
              "y_mrad":config.tilt_y_mrad[yi],"thickness_nm":config.thickness_nm[ti]}}


def main(argv: list[str] | None=None) -> None:
    parser=argparse.ArgumentParser(description="FCC Ni entrance-only EMCD tilt × thickness scan")
    parser.add_argument("--conditions",nargs="+",choices=CONDITIONS,default=["systematic-row","zone-axis"])
    parser.add_argument("--tilt-x-mrad",nargs="+",type=float,default=[0.0])
    parser.add_argument("--tilt-y-mrad",nargs="+",type=float,default=[-10.,-5.,0.,5.,10.])
    parser.add_argument("--thickness-nm",nargs="+",type=float,default=[10.,20.,30.,40.,50.])
    parser.add_argument("--energy-ev",type=float,default=852.7)
    parser.add_argument("--acceleration-kv",type=float,default=200.)
    parser.add_argument("--beam-order",type=int,default=3)
    parser.add_argument("--max-beams",type=int,default=13)
    parser.add_argument("--zone2d-max-g",type=float,default=1.2)
    parser.add_argument("--grid",type=int,default=33)
    parser.add_argument("--steps",type=int,default=32)
    parser.add_argument("--b-factor",type=float,default=0.)
    parser.add_argument("--output",default="outputs/ni_tilt_thickness_scan")
    args=parser.parse_args(argv)
    config=ScanConfig(conditions=tuple(args.conditions),
       tilt_x_mrad=tuple(args.tilt_x_mrad),tilt_y_mrad=tuple(args.tilt_y_mrad),
       thickness_nm=tuple(args.thickness_nm), energy_ev=args.energy_ev,
       acceleration_kv=args.acceleration_kv,beam_order=args.beam_order,
       max_beams=args.max_beams,zone2d_max_g=args.zone2d_max_g,
       grid=args.grid,steps=args.steps,b_factor=args.b_factor)
    try:
        res=run_scan(config,args.output)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(res,indent=2))


if __name__=="__main__":
    main()
