"""CLI generating a Ni benchmark map, detector spectra and machine-readable data."""
import argparse
import json
from pathlib import Path
import numpy as np

from .benchmark import nickel_three_beam, nickel_physical_benchmark
from .voltage import TabulatedMagnetization


def main() -> None:
    parser = argparse.ArgumentParser(description="FCC Ni physical multi-beam Bloch-wave + illustrative MDFF")
    parser.add_argument("--output", default="outputs/ni_baseline")
    parser.add_argument("--thickness-nm", type=float, default=30.0)
    parser.add_argument("--voltage-v", type=float, default=0.0,
                        help="Sample bias voltage, NOT microscope accelerating voltage")
    parser.add_argument("--acceleration-kv", type=float, default=200.0)
    parser.add_argument("--elastic-backend", choices=("physical", "surrogate"), default="physical",
                        help="Default uses tabulated neutral Ni scattering factors")
    parser.add_argument("--xi-nm", type=float, default=55.0,
                        help="Only used with --elastic-backend surrogate")
    parser.add_argument("--beam-order", type=int, default=3,
                        help="Physical systematic-row ±n(200) order; default 3 = 7 beams")
    parser.add_argument("--zone2d-max-g", type=float, default=None,
                        help="Use centered 2D [001] ZOLZ basis with |g| cutoff in 1/Å")
    parser.add_argument("--max-beams", type=int, default=25)
    parser.add_argument("--b-factor", type=float, default=0.0,
                        help="Isotropic Debye-Waller B in Å²; default 0 (no guessed Ni B)")
    parser.add_argument("--tilt-x-mrad", type=float, default=0.0)
    parser.add_argument("--tilt-y-mrad", type=float, default=0.0)
    parser.add_argument("--grid", type=int, default=65)
    parser.add_argument("--steps", type=int, default=64)
    parser.add_argument("--voltage-table", default=None,
                        help="CSV with header voltage_v,moment_muB from experiment/theory")
    args = parser.parse_args()
    law = None
    if args.voltage_table:
        data = np.genfromtxt(args.voltage_table, delimiter=",", names=True)
        law = TabulatedMagnetization(tuple(np.atleast_1d(data["voltage_v"]).tolist()),
                                    tuple(np.atleast_1d(data["moment_muB"]).tolist()))
    tilt = (args.tilt_x_mrad, args.tilt_y_mrad)
    if args.elastic_backend == "physical":
        sim = nickel_physical_benchmark(
            law, tilt_mrad_xy=tilt, acceleration_kv=args.acceleration_kv,
            beam_order=args.beam_order, debye_waller_b_angstrom2=args.b_factor,
            zone2d_max_g_angstrom_inv=args.zone2d_max_g, max_beams=args.max_beams)
    else:
        if args.zone2d_max_g is not None:
            parser.error("--zone2d-max-g requires the physical solver")
        sim = nickel_three_beam(law, tilt_mrad_xy=tilt,
                                acceleration_kv=args.acceleration_kv,
                                extinction_distance_200_nm=args.xi_nm)
    result = sim.run(np.linspace(837., 883., 185), thickness_nm=args.thickness_nm,
                     voltage_v=args.voltage_v, grid_size=args.grid, depth_steps=args.steps)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output / "ni_emcd.npz", energy_ev=result.energy_ev,
        qx_inv_angstrom=result.qx_angstrom_inv, qy_inv_angstrom=result.qy_angstrom_inv,
        nonmag_map=result.nonmag_map_at_l3, magnetic_map=result.magnetic_map_at_l3,
        detector_A=result.detector_spectra["A"], detector_B=result.detector_spectra["B"],
        difference=result.difference(), asymmetry=result.asymmetry())
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    ext = (result.qx_angstrom_inv.min(), result.qx_angstrom_inv.max(),
           result.qy_angstrom_inv.min(), result.qy_angstrom_inv.max())
    im = axes[0].imshow(result.magnetic_map_at_l3, origin="lower", extent=ext, cmap="coolwarm")
    for name, det in sim.detectors.items():
        import matplotlib.patches as patches
        axes[0].add_patch(patches.Circle(det.center_q_xy, det.radius_q, fill=False,
                                        edgecolor="black", linewidth=1.4))
        axes[0].text(*det.center_q_xy, name, ha="center", va="center", color="black")
    fig.colorbar(im, ax=axes[0], shrink=.8, label="magnetic term (arb.)")
    axes[0].set(xlabel=r"$q_x$ ($\AA^{-1}$)", ylabel=r"$q_y$ ($\AA^{-1}$)", title="Ni L3 magnetic angular term")
    for label, val in result.detector_spectra.items():
        axes[1].plot(result.energy_ev, val, label=label)
    axes[1].set(xlabel="Energy loss (eV)", ylabel="Integrated signal (arb.)", title="Virtual detector EELS")
    axes[1].legend()
    axes[2].plot(result.energy_ev, result.asymmetry())
    axes[2].axhline(0., linewidth=.6, color="gray")
    axes[2].set(xlabel="Energy loss (eV)", ylabel="(A−B)/(A+B)", title="EMCD asymmetry")
    fig.suptitle(f"FCC Ni EMCD (illustrative MDFF; {args.elastic_backend} elastic) | "
                 f"{result.thickness_nm:g} nm | {result.voltage_v:g} V")
    fig.tight_layout()
    fig.savefig(output / "ni_emcd.png", dpi=180)
    plt.close(fig)
    # Directly inspect the elastic solver independently of illustrative EMCD.
    depths = np.linspace(0.0, max(80.0, 2 * args.thickness_nm), 161)
    intensities = np.abs(sim.elastic.amplitudes(depths)) ** 2
    np.savez_compressed(output / "ni_elastic_diffraction.npz",
        thickness_nm=depths, beam_hkl=np.array(sim.elastic.beams.hkl,dtype=int),
        beam_intensity=intensities,
        hamiltonian_nm_inv=sim.elastic.hamiltonian_nm_inv())
    fig_el, ax_el = plt.subplots(figsize=(8.0, 4.6))
    for beam_index, hkl in enumerate(sim.elastic.beams.hkl):
        ax_el.plot(depths, intensities[:,beam_index],
                   label="("+" ".join(str(h) for h in hkl)+")", linewidth=1.4)
    ax_el.axvline(args.thickness_nm, color="black", alpha=.6, ls="--", lw=1,
                  label="sample thickness")
    ax_el.set(xlabel="Ni thickness (nm)",ylabel="Elastic beam intensity (normalized)",
              title=f"Ni [001] {args.elastic_backend} elastic propagation | "
                    f"{len(sim.elastic.beams.hkl)} beams")
    ax_el.set_ylim(bottom=0)
    ax_el.legend(ncol=2,fontsize=8)
    fig_el.tight_layout()
    fig_el.savefig(output / "ni_elastic_diffraction.png",dpi=180)
    plt.close(fig_el)
    energy, difference, contrast = result.at_edge()
    from .physical_elastic import PhysicalElasticModel
    is_physical = isinstance(sim.elastic, PhysicalElasticModel)
    metrics = dict(model="entrance_channeling_dipole_mdff_illustrative_v1",
        material="FCC Ni", zone_axis="[001]", reflections=[list(h) for h in sim.elastic.beams.hkl],
        lattice_constant_angstrom=3.524, moment_muB_per_atom=result.moment_muB,
        thickness_nm=result.thickness_nm, sample_bias_v=result.voltage_v,
        acceleration_kv=args.acceleration_kv, tilt_mrad_xy=list(tilt),
        elastic_backend=args.elastic_backend,
        elastic_scattering_source=("Lobato & Van Dyck (2014), Z=28, IAM" if is_physical else "power-law surrogate"),
        extinction_distance_200_nm=(sim.elastic.extinction_distance_nm((2,0,0))
                                      if is_physical else args.xi_nm),
        beam_count=len(sim.elastic.beams.hkl),
        b_factor_angstrom2=(args.b_factor if is_physical else None),
        elastic_absorption=False, outgoing_channeling=False,
        edge_sample_ev=energy, difference_at_l3_arbitrary= difference,
        asymmetry_at_l3=contrast, calibrated=False,
        limitations="no outgoing channeling, absorption, quantitative atomic MDFF or voltage-magnetism prediction")
    (output / "metadata.json").write_text(json.dumps(metrics, indent=2)+"\n")
    print(json.dumps({"output":str(output),"L3_ev":energy,
                      "L3_asymmetry":contrast,"muB_per_atom":result.moment_muB},indent=2))


if __name__ == "__main__":
    main()
