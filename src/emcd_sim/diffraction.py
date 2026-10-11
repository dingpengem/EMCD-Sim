"""Nominal FCC Ni diffraction geometries and elastic diffraction visualization.

Reciprocal coordinates use cycles/Å (no 2π), with [001] normal to the foil.
The Bragg spots are discrete plane-wave intensities: plotting Gaussians are a
visualization only, NOT a calculated detector PSF or convergent-beam disk.
"""
from dataclasses import dataclass
from pathlib import Path
import csv
import numpy as np

from .crystal import Crystal
from .elastic import BeamSet
from .geometry import Microscope, electron_wavelength_angstrom


@dataclass(frozen=True)
class DiffractionSetup:
    name: str
    beams: BeamSet
    tilt_mrad_xy: tuple[float, float]
    zone_axis: tuple[int, int, int] = (0, 0, 1)
    approximation: str = ""


def bragg_tilt_mrad(crystal: Crystal, hkl: tuple[int, int, int], acceleration_kv: float) -> float:
    """Paraxial Bragg angle (positive magnitude); s_g=0 for tilt=-theta_B along g."""
    return 500.0 * electron_wavelength_angstrom(acceleration_kv) * float(np.linalg.norm(crystal.g_vector(hkl)))


def excitation_errors_angstrom_inv(model) -> np.ndarray:
    """Signed s_g=(|k_perp+g|²-|k_perp|²)/(2k), in cycles/Å.

    The physical solver has diagonal entries H_gg=-20π s_g in nm^-1.
    """
    g = model.reciprocal_vectors_xy
    kxy = model.microscope.incident_k_xy
    lam = electron_wavelength_angstrom(model.microscope.acceleration_kv)
    return 0.5 * lam * (np.sum((g + kxy)**2, axis=1) - np.dot(kxy, kxy))


def select_diffraction_setup(
    name: str,
    crystal: Crystal,
    acceleration_kv: float = 200.0,
    beam_order: int = 3,
    zone2d_max_g: float | None = None,
    max_beams: int = 25,
    tilt_x_mrad: float | None = None,
    tilt_y_mrad: float | None = None,
    offzone_tilt_mrad: float = 25.0,
) -> DiffractionSetup:
    """Configure physically labeled, *finite-basis* diffraction conditions.

    'symmetric-3bc' means ±(200) have equal excitation errors. It is a
    systematic-row model with an off-zone-axis tilt, not a fully validated
    experimental 3BC alignment. 'two-beam' is explicitly a 2-beam truncation;
    'near-2bc' keeps higher systematic-row beams for a less severe truncation.
    """
    allowed = {"systematic-row", "zone-axis", "two-beam", "near-2bc", "symmetric-3bc"}
    if name not in allowed:
        raise ValueError(f"Unknown diffraction condition {name!r}; choose {sorted(allowed)}")
    if not np.isfinite(offzone_tilt_mrad) or offzone_tilt_mrad < 0:
        raise ValueError("offzone_tilt_mrad must be a finite nonnegative number")
    if name not in {"zone-axis", "systematic-row"} and zone2d_max_g is not None:
        raise ValueError("--zone2d-max-g is incompatible with systematic-row 2BC/3BC presets")

    theta = bragg_tilt_mrad(crystal, (2, 0, 0), acceleration_kv)
    if name == "zone-axis" or (name == "systematic-row" and zone2d_max_g is not None):
        cutoff = 1.20 if zone2d_max_g is None else zone2d_max_g
        beams = BeamSet.zolz(crystal, cutoff, max_beams)
        default_tilt = (0.0, 0.0)
        approximation = "Finite 2D ZOLZ basis, perfect crystal, parallel-beam illumination"
        actual_name = "zone-axis"
    elif name == "two-beam":
        beams = BeamSet(((0, 0, 0), (2, 0, 0)))
        default_tilt = (-theta, offzone_tilt_mrad)
        approximation = "Ideal two-beam basis truncation: all other diffracted beams excluded"
        actual_name = name
    else:
        beams = BeamSet.systematic_row(beam_order)
        default_tilt = {
            "systematic-row": (0.0, 0.0),
            "near-2bc": (-theta, offzone_tilt_mrad),
            "symmetric-3bc": (0.0, offzone_tilt_mrad),
        }[name]
        approximation = (
            "Systematic-row approximation (off-row diffraction not propagated)"
            if name != "systematic-row" else
            "Zone-axis incidence with systematic-row basis only (NOT full zone axis)"
        )
        actual_name = name
    tilt = (
        float(default_tilt[0] if tilt_x_mrad is None else tilt_x_mrad),
        float(default_tilt[1] if tilt_y_mrad is None else tilt_y_mrad),
    )
    if not np.all(np.isfinite(tilt)):
        raise ValueError("incident tilts must be finite")
    return DiffractionSetup(actual_name, beams, tilt, approximation=approximation)


def save_diffraction_pattern(model, thickness_nm: float, output: Path | str,
                             condition: DiffractionSetup) -> dict:
    """Save calculated elastic spot intensities, s_g, and labeled PNG/NPZ/CSV.

    Spot broadening in the PNG is visual only, not a detector or probe model.
    """
    if not np.isfinite(thickness_nm) or thickness_nm <= 0:
        raise ValueError("thickness_nm must be positive and finite")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    amplitudes = model.amplitudes(np.array([thickness_nm]))[0]
    intensity = np.abs(amplitudes)**2
    hkl = np.asarray(model.beams.hkl, dtype=int)
    xy = model.reciprocal_vectors_xy
    sg = excitation_errors_angstrom_inv(model)
    np.savez_compressed(output / "diffraction_pattern.npz", beam_hkl=hkl,
        g_xy_inv_angstrom=xy, elastic_intensity=intensity,
        excitation_error_inv_angstrom=sg, amplitudes=amplitudes,
        tilt_mrad_xy=np.asarray(condition.tilt_mrad_xy),
        thickness_nm=float(thickness_nm), zone_axis=np.asarray(condition.zone_axis))
    with (output / "diffraction_spots.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["h", "k", "l", "g_x_inv_A", "g_y_inv_A", "s_g_inv_A", "intensity"])
        for indices, g, s, val in zip(hkl, xy, sg, intensity):
            writer.writerow([*map(int,indices), *map(float,g), float(s), float(val)])

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm

    labels = ["(" + ",".join(str(int(v)) for v in triple) + ")" for triple in hkl]
    gmax = max(float(np.max(np.abs(xy))), 2.0 / 3.524)
    margin = max(0.32, 0.22 * gmax)
    bound = gmax + margin
    grid = np.linspace(-bound, bound, 451)
    X,Y = np.meshgrid(grid, grid)
    sigma = max(0.026, 0.022 * bound)
    rendered = np.zeros_like(X)
    for (gx, gy), val in zip(xy, intensity):
        rendered += val * np.exp(-0.5 * ((X-gx)**2 + (Y-gy)**2) / sigma**2)

    fig, (ax, ax_bar) = plt.subplots(1, 2, figsize=(12.4, 6.1),
                                    gridspec_kw={"width_ratios": [1.15, 1.0]})
    peak = max(float(np.max(intensity)), 1e-12)
    ax.imshow(np.maximum(rendered, peak*1e-6), origin="lower", cmap="inferno",
              extent=(-bound,bound,-bound,bound),
              norm=LogNorm(vmin=peak*1e-5,vmax=peak), interpolation="nearest")
    ax.scatter(xy[:,0], xy[:,1], s=30, facecolors="none", edgecolors="white", linewidths=0.7)
    for label, (gx,gy) in zip(labels,xy):
        ax.annotate(label, (gx,gy), xytext=(-4,9) if gx > 0.88*gmax else (3,9),
                    textcoords="offset points", color="white", fontsize=8,
                    ha="right" if gx > 0.88*gmax else "left", va="bottom")
    ax.axhline(0, color="white", alpha=0.2, lw=0.7)
    ax.axvline(0, color="white", alpha=0.2, lw=0.7)
    ax.set(xlabel=r"$g_x$ (cycles / $\AA$)",ylabel=r"$g_y$ (cycles / $\AA$)",
           title="Simulated elastic diffraction (indexed)")
    ax.set_aspect("equal")
    ax.set_xlim(-bound,bound)
    ax.set_ylim(-bound,bound)

    xx = np.arange(len(hkl))
    bars = ax_bar.bar(xx, intensity, color="#477B9B")
    ax_bar.set_xticks(xx, labels, rotation=60, ha="right", fontsize=8)
    ax_bar.set(ylabel="Elastic intensity (normalized)",xlabel="(hkl)",
               title="Beam intensities at selected thickness")
    ax_bar.set_ylim(0, max(float(max(intensity))*1.20, 0.05))
    for bar, s in zip(bars, sg):
        if len(hkl) <= 15:
            ax_bar.text(bar.get_x()+bar.get_width()/2,bar.get_height()+0.006,
                        f"s={s:+.3g}",rotation=90,fontsize=7,ha="center",va="bottom")
    za = "[" + "".join(str(int(x)) for x in condition.zone_axis) + "]"
    fig.suptitle(f"FCC Ni  |  nominal zone axis {za}  |  {condition.name}\n"
                 f"{model.microscope.acceleration_kv:g} kV, t={thickness_nm:g} nm, "
                 f"tilt=({condition.tilt_mrad_xy[0]:+.2f}, "
                 f"{condition.tilt_mrad_xy[1]:+.2f}) mrad", fontsize=13)
    fig.text(0.5,0.015,condition.approximation+". Gaussian spot width is display-only.",
             ha="center",fontsize=8, color="#555555")
    fig.tight_layout(rect=(0,0.045,1,.90))
    fig.savefig(output / "diffraction_pattern.png", dpi=180)
    plt.close(fig)
    return {
        "diffraction_condition":condition.name,
        "nominal_zone_axis_hkl":list(condition.zone_axis),
        "tilt_mrad_xy":list(condition.tilt_mrad_xy),
        "beam_hkl":hkl.tolist(),
        "beam_count":len(hkl),
        "excitation_error_inv_angstrom":sg.tolist(),
        "elastic_intensity":intensity.tolist(),
        "elastic_total_intensity":float(sum(intensity)),
        "diffraction_approximation":condition.approximation,
    }
