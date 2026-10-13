"""CLI generating a Ni benchmark map, detector spectra and machine-readable data."""
import argparse
import json
from pathlib import Path
import numpy as np

from .benchmark import nickel_three_beam, nickel_physical_benchmark
from .crystal import fcc_nickel
from .diffraction import select_diffraction_setup, save_diffraction_pattern
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
    parser.add_argument("--diffraction-condition",
                        choices=("systematic-row", "zone-axis", "two-beam", "near-2bc", "symmetric-3bc"),
                        default="systematic-row",
                        help="Nominal diffraction geometry; default preserves the v0.2 row model")
    parser.add_argument("--diffraction-only", action="store_true",
                        help="Only calculate indexed elastic pattern and excitation errors (no MDFF)")
    parser.add_argument("--offzone-tilt-mrad", type=float, default=25.0,
                        help="Y tilt preset in the off-zone 2BC/3BC systematic-row approximations")
    parser.add_argument("--beam-order", type=int, default=3,
                        help="Physical systematic-row ±n(200) order; default 3 = 7 beams")
    parser.add_argument("--zone2d-max-g", type=float, default=None,
                        help="Use centered 2D [001] ZOLZ basis with |g| cutoff in 1/Å")
    parser.add_argument("--max-beams", type=int, default=25)
    parser.add_argument("--b-factor", type=float, default=0.0,
                        help="Isotropic Debye-Waller B in Å²; default 0 (no guessed Ni B)")
    parser.add_argument("--tilt-x-mrad", type=float, default=None,
                        help="Override geometry preset x tilt; mrad")
    parser.add_argument("--tilt-y-mrad", type=float, default=None,
                        help="Override geometry preset y tilt; mrad")
    parser.add_argument("--grid", type=int, default=65)
    parser.add_argument("--steps", type=int, default=64)
    parser.add_argument("--mdff-model", choices=("gaussian", "ni-local", "transitions", "ni-metal-external"), default="gaussian",
                        help="gaussian: original illustrative model; ni-local: non-DFT atomic complex tensor; transitions: complex transition NPZ")
    parser.add_argument("--mdff-transitions", type=Path, default=None,
                        help="TransitionDataset NPZ, mandatory for --mdff-model transitions")
    parser.add_argument("--mdff-provenance", type=Path, default=None,
                        help="Required external FCC Ni dipole provenance JSON for ni-metal-external mode")
    parser.add_argument("--mdff-site", default=None,
                        help="Select one explicit site label from an imported transition dataset")
    parser.add_argument("--mdff-sigma-ev", type=float, default=0.8,
                        help="Gaussian transition broadening (eV) for complex tensor")
    parser.add_argument("--mdff-radial-table", type=Path, default=None,
                        help="Optional radial-function CSV for non-DFT Ni local model")
    parser.add_argument("--voltage-table", default=None,
                        help="CSV with header voltage_v,moment_muB from experiment/theory")
    args = parser.parse_args()
    if args.mdff_model != "gaussian":
        if args.voltage_table is not None or args.voltage_v != 0.0:
            parser.error("Complex MDFF uses the electronic state supplied by its transitions; the illustrative bias-to-moment scaling is unsupported")
        if args.elastic_backend != "physical":
            parser.error("Complex MDFF is currently supported with the physical elastic backend only")
        if args.mdff_model in ("transitions", "ni-metal-external") and args.mdff_transitions is None:
            parser.error("--mdff-model transitions requires --mdff-transitions FILE.npz")
        if args.mdff_model == "ni-local" and args.mdff_transitions is not None:
            parser.error("--mdff-transitions is only used with --mdff-model transitions")
        if args.mdff_model == "ni-metal-external" and args.mdff_provenance is None:
            parser.error("--mdff-model ni-metal-external requires --mdff-provenance FILE.json")
        if args.mdff_provenance is not None and args.mdff_model != "ni-metal-external":
            parser.error("--mdff-provenance applies only to --mdff-model ni-metal-external")
        if args.mdff_radial_table is not None and args.mdff_model != "ni-local":
            parser.error("--mdff-radial-table applies only to --mdff-model ni-local")
    law = None
    if args.voltage_table:
        data = np.genfromtxt(args.voltage_table, delimiter=",", names=True)
        law = TabulatedMagnetization(tuple(np.atleast_1d(data["voltage_v"]).tolist()),
                                    tuple(np.atleast_1d(data["moment_muB"]).tolist()))
    if args.elastic_backend != "physical" and (args.diffraction_condition != "systematic-row" or args.zone2d_max_g is not None):
        parser.error("diffraction presets and 2D ZOLZ require --elastic-backend physical")
    try:
        setup = select_diffraction_setup(
            args.diffraction_condition, fcc_nickel(), args.acceleration_kv,
            beam_order=args.beam_order, zone2d_max_g=args.zone2d_max_g,
            max_beams=args.max_beams, tilt_x_mrad=args.tilt_x_mrad,
            tilt_y_mrad=args.tilt_y_mrad,
            offzone_tilt_mrad=args.offzone_tilt_mrad)
    except ValueError as exc:
        parser.error(str(exc))
    tilt = setup.tilt_mrad_xy
    if args.elastic_backend == "physical":
        sim = nickel_physical_benchmark(
            law, tilt_mrad_xy=tilt, acceleration_kv=args.acceleration_kv,
            beam_order=args.beam_order, debye_waller_b_angstrom2=args.b_factor,
            beams_override=setup.beams,
            diffraction_condition=setup.name)
    else:
        sim = nickel_three_beam(law, tilt_mrad_xy=tilt,
                                acceleration_kv=args.acceleration_kv,
                                extinction_distance_200_nm=args.xi_nm)
        # Surrogate retains its original fixed 3-beam basis.
        from dataclasses import replace
        setup = replace(setup, beams=sim.elastic.beams,
                        approximation="Legacy 3-beam surrogate, not physical Ni potential")
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    diffraction = save_diffraction_pattern(sim.elastic, args.thickness_nm, output, setup,
                                           detectors=sim.detectors,
                                           chiral_groups=sim.chiral_groups)
    if args.diffraction_only:
        metadata = {**diffraction, "material":"FCC Ni", "acceleration_kv":args.acceleration_kv,
                    "thickness_nm":args.thickness_nm,"elastic_backend":args.elastic_backend,
                    "mdff_computed":False}
        (output / "metadata.json").write_text(json.dumps(metadata, indent=2)+"\n")
        print(json.dumps({"output":str(output),"condition":setup.name,
                          "beam_count":diffraction["beam_count"],
                          "elastic_total_intensity":diffraction["elastic_total_intensity"]},indent=2))
        return
    energies = np.linspace(837., 883., 185)
    tensor = None
    external_audit = None
    mdff_source = "ILLUSTRATIVE_GAUSSIAN_magnetic_fraction_0.12"
    if args.mdff_model == "gaussian":
        result = sim.run(energies, thickness_nm=args.thickness_nm,
                         voltage_v=args.voltage_v, grid_size=args.grid, depth_steps=args.steps)
    else:
        from .mdff_tensor import TransitionDataset, dipole_tensor_from_transitions
        from .single_channeling_tensor import run_tensor_single_channeling
        if args.mdff_model == "ni-local":
            from .ni_local_mdff import ni_local_transitions, radial_dipole_from_table, NiLocalConfig
            radial_override = None
            if args.mdff_radial_table is not None:
                tab = np.genfromtxt(args.mdff_radial_table, names=True, delimiter=",", encoding="utf-8")
                required = ("radius_angstrom", "R_2p", "R_3d")
                if tab.dtype.names is None or not set(required) <= set(tab.dtype.names):
                    parser.error("Radial CSV needs radius_angstrom,R_2p,R_3d")
                radial_override = radial_dipole_from_table(*(tab[k] for k in required))
            transitions = ni_local_transitions(NiLocalConfig(), radial_override_angstrom=radial_override)
        else:
            if args.mdff_model == "ni-metal-external":
                from .ni_data_audit import audit_metallic_ni_transitions
                try:
                    external_audit = audit_metallic_ni_transitions(args.mdff_transitions, args.mdff_provenance)
                except (ValueError, OSError, json.JSONDecodeError) as exc:
                    parser.error(str(exc))
            transitions = TransitionDataset.load_npz(args.mdff_transitions)
        available_sites = set(transitions.site.tolist())
        if args.mdff_site is None and len(available_sites) != 1:
            parser.error("Multi-site transition data require an explicit --mdff-site; spatial site registration is not automatic")
        selected_site = args.mdff_site or next(iter(available_sites))
        if selected_site not in available_sites:
            parser.error(f"Unknown transition site: {selected_site!r}")
        try:
            tensor = dipole_tensor_from_transitions(transitions, energies, args.mdff_sigma_ev,
                                                    site=selected_site)
        except ValueError as exc:
            parser.error(str(exc))
        mdff_source = tensor.source
        result = run_tensor_single_channeling(sim, tensor, thickness_nm=args.thickness_nm,
                                                grid_size=args.grid, depth_steps=args.steps)
        tensor.save_npz(output / "input_mdff_tensor.npz")
        if external_audit is not None:
            (output / "external_ni_data_audit.json").write_text(json.dumps(external_audit, indent=2)+"\n", encoding="utf-8")
        # Single-energy L2 reciprocal maps use precisely the same experiment
        # and site-phase contraction as the L3 maps. Avoid repeating full EELS.
        l2_index = int(np.argmin(abs(energies - 870.0)))
        l2_window = slice(l2_index, l2_index + 2)
        from .mdff_tensor import DipoleTensor
        l2_tensor = DipoleTensor(energies[l2_window],
                                 tensor.tensor_angstrom2_per_ev[l2_window], tensor.source)
        l2_result = run_tensor_single_channeling(sim, l2_tensor,
                    thickness_nm=args.thickness_nm, grid_size=args.grid,
                    depth_steps=args.steps, reference_energy_ev=870.0)
        np.savez_compressed(output / "ni_l2_reciprocal.npz",
                    energy_ev=l2_result.energy_ev[0],
                    qx_inv_angstrom=l2_result.qx_angstrom_inv,
                    qy_inv_angstrom=l2_result.qy_angstrom_inv,
                    nonmag_map=l2_result.nonmag_map_at_l3,
                    chiral_map=l2_result.magnetic_map_at_l3)
    np.savez_compressed(output / "ni_emcd.npz", energy_ev=result.energy_ev,
        qx_inv_angstrom=result.qx_angstrom_inv, qy_inv_angstrom=result.qy_angstrom_inv,
        nonmag_map=result.nonmag_map_at_l3, magnetic_map=result.magnetic_map_at_l3,
        detector_A=result.chiral_spectrum("A"), detector_B=result.chiral_spectrum("B"),
        difference=result.difference(), asymmetry=result.asymmetry(),
        **{"aperture_"+name:spectrum for name, spectrum in result.detector_spectra.items()})
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
    for hkl, g in zip(sim.elastic.beams.hkl, sim.elastic.reciprocal_vectors_xy):
        if ext[0] <= g[0] <= ext[1] and ext[2] <= g[1] <= ext[3]:
            axes[0].plot(g[0], g[1], 'k+', ms=4, alpha=.5)
            axes[0].annotate("("+"".join(str(x) for x in hkl)+")", g,
                             xytext=(3,4), textcoords="offset points", fontsize=6)
    fig.colorbar(im, ax=axes[0], shrink=.8, label="magnetic term (arb.)")
    axes[0].set(xlabel=r"$q_x$ ($\AA^{-1}$)", ylabel=r"$q_y$ ($\AA^{-1}$)", title="Ni L3 magnetic angular term")
    for label in ("A", "B"):
        axes[1].plot(result.energy_ev, result.chiral_spectrum(label), label=label)
    axes[1].set(xlabel="Energy loss (eV)", ylabel="Integrated signal (arb.)", title="Virtual detector EELS")
    axes[1].legend()
    axes[2].plot(result.energy_ev, result.asymmetry())
    axes[2].axhline(0., linewidth=.6, color="gray")
    axes[2].set(xlabel="Energy loss (eV)", ylabel="(A−B)/(A+B)", title="EMCD asymmetry")
    fig.suptitle(f"FCC Ni {setup.name} EMCD ({args.mdff_model} MDFF; {args.elastic_backend} elastic) | "
                 f"{result.thickness_nm:g} nm | {result.voltage_v:g} V")
    fig.tight_layout()
    fig.savefig(output / "ni_emcd.png", dpi=180)
    plt.close(fig)
    if tensor is not None:
        # Two energy slices, identical axes and shared color scales. Magnetic
        # (chiral) maps are signed *model contributions*, not measured asymmetry.
        from matplotlib.colors import TwoSlopeNorm
        from matplotlib.patches import Circle
        pair = (("L3", result), ("L2", l2_result))
        n_lim = max(max(float(np.max(v.nonmag_map_at_l3)), 0.) for _,v in pair)
        m_lim = max(float(np.max(np.abs(v.magnetic_map_at_l3))) for _,v in pair)
        n_lim, m_lim = max(n_lim, 1e-30), max(m_lim, 1e-30)
        fig2, axes2 = plt.subplots(2, 2, figsize=(10, 8.2),
                                   constrained_layout=True, sharex=True, sharey=True)
        for row, (edge, rv) in enumerate(pair):
            extent = (rv.qx_angstrom_inv.min(),rv.qx_angstrom_inv.max(),
                      rv.qy_angstrom_inv.min(),rv.qy_angstrom_inv.max())
            a = axes2[row,0].imshow(rv.nonmag_map_at_l3,origin="lower",extent=extent,
                                   cmap="viridis", vmin=0,vmax=n_lim)
            b = axes2[row,1].imshow(rv.magnetic_map_at_l3,origin="lower",extent=extent,
                                   cmap="coolwarm",norm=TwoSlopeNorm(vmin=-m_lim,
                                                                     vcenter=0,vmax=m_lim))
            for col in range(2):
                ax=axes2[row,col]
                for hkl,g in zip(sim.elastic.beams.hkl,sim.elastic.reciprocal_vectors_xy):
                    if extent[0]<=g[0]<=extent[1] and extent[2]<=g[1]<=extent[3]:
                        ax.plot(g[0],g[1],"k+",ms=4)
                        ax.annotate("("+",".join(map(str,hkl))+")",g,xytext=(2,3),
                                    textcoords="offset points",fontsize=6)
                for name,det in sim.detectors.items():
                    ax.add_patch(Circle(det.center_q_xy,det.radius_q,
                                        fill=False,lw=.9,ec="black"))
                    ax.text(*det.center_q_xy,name,fontsize=7,ha="center",va="center")
                ax.set_aspect("equal")
                ax.set(xlabel=r"$q_x$ (cycles/$\AA$)",ylabel=r"$q_y$ (cycles/$\AA$)")
            axes2[row,0].set_title(f"{edge} nonchiral term")
            axes2[row,1].set_title(f"{edge} chiral tensor term")
        fig2.colorbar(a,ax=list(axes2[:,0]),shrink=.65,label="Relative intensity (arb.)")
        fig2.colorbar(b,ax=list(axes2[:,1]),shrink=.65,label="Chiral term (arb.)")
        fig2.suptitle("FCC Ni [001] · entrance-only · transition-derived complex MDFF\n"
                      "Non-DFT model unless independently verified; shared scales")
        fig2.savefig(output / "ni_mdff_reciprocal.png",dpi=160)
        plt.close(fig2)
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
    metrics = dict(**diffraction, model=("entrance_channeling_dipole_mdff_illustrative_v1" if tensor is None
                                            else "entrance_only_complex_transition_dipole_tensor"),
        material="FCC Ni", zone_axis="[001]", reflections=[list(h) for h in sim.elastic.beams.hkl],
        lattice_constant_angstrom=3.524, moment_muB_per_atom=result.moment_muB,
        thickness_nm=result.thickness_nm, sample_bias_v=result.voltage_v,
        acceleration_kv=args.acceleration_kv,
        elastic_backend=args.elastic_backend,
        elastic_scattering_source=("Lobato & Van Dyck (2014), Z=28, IAM" if is_physical else "power-law surrogate"),
        extinction_distance_200_nm=(sim.elastic.extinction_distance_nm((2,0,0))
                                      if is_physical else args.xi_nm),
        b_factor_angstrom2=(args.b_factor if is_physical else None),
        aperture_coordinates="transmitted-beam-centered Q=(kf-ki)_perp, cycles/angstrom",
        emcd_difference_definition="A-B; symmetric-3bc A=RU+LD, B=RD+LU",
        mdff_model=args.mdff_model, mdff_source=mdff_source,
        mdff_quantitative_Ni=False,
        external_ni_source_audit_status=(None if external_audit is None else external_audit["status"]),
        cross_section_units="relative_only_missing_fast_electron_prefactors",
        core_loss_site_phase="localized core, equivalent FCC Ni sites averaged incoherently",
        magnetic_fraction_applied=(tensor is None),
        elastic_absorption=False, outgoing_channeling=False,
        edge_sample_ev=energy, difference_at_l3_arbitrary= difference,
        asymmetry_at_l3=contrast, calibrated=False,
        limitations="no outgoing channeling, absorption, validated Ni electronic structure, absolute cross section or voltage-magnetism prediction")
    (output / "metadata.json").write_text(json.dumps(metrics, indent=2)+"\n")
    print(json.dumps({"output":str(output), "mdff_model":args.mdff_model,
                      "L3_ev":energy, "L3_asymmetry":contrast,
                      "muB_per_atom":result.moment_muB,
                      "quantitative_Ni":False},indent=2))


if __name__ == "__main__":
    main()
