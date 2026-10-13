"""Produce indexed elastic diffraction and L2/L3 EMCD maps for Ni diffraction presets.

Reads the user-provided WIEN2k Ni_fm.xmcd from --xmcd-file. The model is an
XMCD-constrained effective tensor with entrance-only channeling.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import numpy as np

from .benchmark import nickel_physical_benchmark
from .crystal import fcc_nickel
from .diffraction import select_diffraction_setup, save_diffraction_pattern
from .single_channeling_tensor import run_tensor_single_channeling
from .xmcd_effective_mdff import effective_tensor_from_xmcd

CONDITIONS = ("zone-axis", "two-beam", "near-2bc", "symmetric-3bc")

def main(argv=None):
    p = argparse.ArgumentParser(description="WIEN2k XMCD-based indexed Ni EMCD maps (entrance-only)")
    p.add_argument("--xmcd-file", type=Path, required=True)
    p.add_argument("--output", type=Path, default=Path("outputs/ni_xmcd_indexed"))
    p.add_argument("--acceleration-kv", type=float, default=200.0)
    p.add_argument("--thickness-nm", type=float, default=30.0)
    p.add_argument("--beam-order", type=int, default=3)
    p.add_argument("--zone2d-max-g", type=float, default=1.2)
    p.add_argument("--max-beams", type=int, default=25)
    p.add_argument("--grid", type=int, default=65)
    p.add_argument("--steps", type=int, default=64)
    p.add_argument("--eta", type=float, default=1.0)
    p.add_argument("--beta", type=float, default=1.0)
    p.add_argument("--offzone-tilt-mrad", type=float, default=25.0)
    args = p.parse_args(argv)
    if args.thickness_nm <= 0 or args.grid < 9 or args.steps < 2:
        p.error("Require thickness_nm > 0, grid >= 9, steps >= 2")
    from .wien2k_xmcd import load_wien2k_xmcd
    s = load_wien2k_xmcd(args.xmcd_file)
    lo, hi = max(837., s.energy_ev[0]), min(882., s.energy_ev[-1])
    if hi <= 871.0 or lo >= 852.0:
        p.error("XMCD file must cover both Ni L3 and L2 reference energies")
    energies = np.linspace(lo, hi, 185)
    tensor = effective_tensor_from_xmcd(args.xmcd_file, energies, eta=args.eta, beta=args.beta)
    args.output.mkdir(parents=True, exist_ok=True)
    allmeta = {}
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    for name in CONDITIONS:
        folder = args.output / name
        folder.mkdir(parents=True, exist_ok=True)
        setup = select_diffraction_setup(name, fcc_nickel(), args.acceleration_kv,
            beam_order=args.beam_order, zone2d_max_g=(args.zone2d_max_g if name == "zone-axis" else None),
            max_beams=args.max_beams, offzone_tilt_mrad=args.offzone_tilt_mrad)
        sim = nickel_physical_benchmark(tilt_mrad_xy=setup.tilt_mrad_xy,
             acceleration_kv=args.acceleration_kv, beam_order=args.beam_order,
             beams_override=setup.beams, diffraction_condition=setup.name)
        dmeta = save_diffraction_pattern(sim.elastic, args.thickness_nm, folder, setup,
             detectors=sim.detectors, chiral_groups=sim.chiral_groups)
        result = run_tensor_single_channeling(sim, tensor, thickness_nm=args.thickness_nm,
            grid_size=args.grid, depth_steps=args.steps)
        np.savez_compressed(folder / "emcd_spectra.npz",
            energy_ev=result.energy_ev, detector_A=result.chiral_spectrum("A"),
            detector_B=result.chiral_spectrum("B"),
            difference=result.difference(), asymmetry=result.asymmetry())
        fig, axs = plt.subplots(2, 2, figsize=(11, 9), constrained_layout=True)
        hkl = np.asarray(dmeta["beam_hkl"])
        gxy = np.asarray(sim.elastic.reciprocal_vectors_xy)
        extent = (result.qx_angstrom_inv.min(), result.qx_angstrom_inv.max(),
                  result.qy_angstrom_inv.min(), result.qy_angstrom_inv.max())
        maps = []
        for row, edge_ev in enumerate((852.7, 870.0)):
            i = int(np.argmin(abs(energies-edge_ev)))
            subset = type(tensor)(energies[i:i+2],tensor.tensor_angstrom2_per_ev[i:i+2],tensor.source)
            r = run_tensor_single_channeling(sim, subset, thickness_nm=args.thickness_nm,
                grid_size=args.grid, depth_steps=args.steps, reference_energy_ev=edge_ev)
            maps.append((r.nonmag_map_at_l3, r.magnetic_map_at_l3, energies[i]))
        vmax_n = max(np.max(x[0]) for x in maps)
        vmax_m = max(np.max(abs(x[1])) for x in maps)
        for row, (nonmag, magnetic, edge_ev) in enumerate(maps):
            for col, (data, cmap, lim) in enumerate(((nonmag, "viridis", vmax_n),
                                                      (magnetic, "coolwarm", vmax_m))):
                ax=axs[row,col]
                if col:
                    im=ax.imshow(data,origin="lower",extent=extent,cmap=cmap,
                                 vmin=-max(lim,1e-30),vmax=max(lim,1e-30))
                else:
                    im=ax.imshow(data,origin="lower",extent=extent,cmap=cmap,vmin=0,
                                 vmax=max(lim,1e-30))
                for (h,k,l),(gx,gy) in zip(hkl,gxy):
                    if extent[0] <= gx <= extent[1] and extent[2] <= gy <= extent[3]:
                        ax.plot(gx,gy,"k+",ms=5)
                        ax.annotate(f"({h},{k},{l})",(gx,gy),xytext=(3,4),
                                    textcoords="offset points",fontsize=6)
                for label,det in sim.detectors.items():
                    ax.add_patch(Circle(det.center_q_xy,det.radius_q,fill=False,
                                        ec="black",lw=.9))
                    ax.text(*det.center_q_xy,label,ha="center",va="center",fontsize=7)
                ax.set(xlabel="Qx (cycles/Angstrom)",ylabel="Qy (cycles/Angstrom)",
                       title=f"{'L3' if row==0 else 'L2'} {edge_ev:.2f} eV | {'nonmagnetic' if col==0 else 'chiral'}")
                ax.set_aspect("equal")
                fig.colorbar(im,ax=ax,shrink=.7)
            np.savez_compressed(folder / ("emcd_L3_map.npz" if row==0 else "emcd_L2_map.npz"),
                energy_ev=edge_ev, qx_inv_angstrom=result.qx_angstrom_inv,
                qy_inv_angstrom=result.qy_angstrom_inv, nonmag_map=nonmag,
                magnetic_map=magnetic, hkl=hkl, reciprocal_gxy=gxy)
        fig.suptitle(f"FCC Ni [001] {name}; XMCD-effective (NOT full DFT-MDFF); t={args.thickness_nm:g} nm")
        fig.savefig(folder / "emcd_L23_indexed.png",dpi=160)
        plt.close(fig)
        allmeta[name]={**dmeta,"mdff_source":tensor.source,
                       "xmcd_eta":args.eta,"xmcd_beta":args.beta,
                       "absolute_cross_section":False,"outgoing_channeling":False}
        (folder/"metadata.json").write_text(json.dumps(allmeta[name],indent=2)+"\n")
    (args.output/"index.json").write_text(json.dumps(allmeta,indent=2)+"\n")
    print(json.dumps({"output":str(args.output),"conditions":list(allmeta),
                      "source":tensor.source,"quantitative_Ni":False},indent=2))

if __name__ == "__main__":
    main()
