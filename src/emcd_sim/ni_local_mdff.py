"""Ni 2p->3d *independent-electron atomic crystal-field* MDFF example.

NO DFT is performed. The orbital forms are normalized screened-hydrogenic
2p and 3d orbitals with user-supplied effective nuclear charges, a cubic
crystal-field splitting, exchange energy and hole populations. Core spin-orbit
angular states and complex dipole phases are calculated from angular algebra.

NOT an atomic multiplet/charge-transfer solver; neither Ni bands nor many-body
2p^5 3d^(n+1) states nor Ni absolute MDFF are predicted by this model.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from math import factorial
from pathlib import Path

import numpy as np

from .mdff_tensor import TransitionDataset, dipole_tensor_from_transitions
from .ni_atomic_reference import ni_2p_to_3d_dipole

BOHR_ANGSTROM = 0.529177210903


def hydrogenic_radial_dipole_angstrom(z2p: float, z3d: float) -> float:
    """Analytic <3d|r|2p> (Angstrom) for *normalized* screened H orbitals.

    R_21(r)=A_p r exp(-z2p r/(2a0)),
    R_32(r)=A_d r^2 exp(-z3d r/(3a0)),
    with A_p=(z2p/a0)^(5/2)/sqrt(24),
    A_d=(2*z3d/(3a0))^(7/2)/sqrt(720).
    The radial integral is integral(R_32 R_21 r^3 dr) = 6! A_p A_d/beta^7.
    Effective charges are *inputs*, never inferred as self-consistent Ni values.
    """
    if not (np.isfinite(z2p) and np.isfinite(z3d) and z2p > 0 and z3d > 0):
        raise ValueError("effective charges must be finite and positive")
    ap = z2p / BOHR_ANGSTROM
    ad = 2 * z3d / (3 * BOHR_ANGSTROM)
    beta = ap / 2 + ad / 2
    # Work in log-space to avoid spurious overflows for large charges.
    return float(np.exp(
        np.log(factorial(6)) + 2.5*np.log(ap) + 3.5*np.log(ad)
        - 0.5*np.log(24) - 0.5*np.log(720) - 7*np.log(beta)
    ))


def radial_dipole_from_table(
    radius_angstrom: np.ndarray, radial_2p: np.ndarray, radial_3d: np.ndarray,
) -> float:
    """Normalize supplied full radial R_nl(r) then evaluate <3d|r|2p>.

    Input must be full radial R(r), *not* reduced u(r)=r R(r), all sampled on
    the same strictly increasing radius grid in Angstrom. This can accept
    external atomic Hartree-Fock radial functions without running any DFT.
    """
    r = np.asarray(radius_angstrom, dtype=float)
    p = np.asarray(radial_2p, dtype=float)
    d = np.asarray(radial_3d, dtype=float)
    if r.ndim != 1 or len(r) < 8 or p.shape != r.shape or d.shape != r.shape:
        raise ValueError("radius, 2p and 3d radial arrays must have matching 1D length >= 8")
    if (not np.all(np.isfinite(r)) or not np.all(np.isfinite(p)) or
            not np.all(np.isfinite(d)) or r[0] < 0 or np.any(np.diff(r) <= 0)):
        raise ValueError("radius must be nonnegative ascending; all radial values finite")
    nporm = np.trapezoid((p*r)**2, r)
    ndorm = np.trapezoid((d*r)**2, r)
    if nporm <= 1e-30 or ndorm <= 1e-30:
        raise ValueError("radial functions must have nonzero normalization")
    integral = np.trapezoid(p*d*r**3, r) / np.sqrt(nporm*ndorm)
    if abs(integral) <= 1e-14:
        raise ValueError("radial dipole integral is effectively zero")
    return float(integral)


def cubic_orbital_coefficients() -> dict[str, np.ndarray]:
    """Orthonormal real cubic 3d orbitals in |l=2,m>, m=-2,...,+2.

    Overall orbital phases are arbitrary and cancel within the transition
    tensor; mutually coherent m components of a *single orbital* do not.
    """
    s = 2**-0.5
    vectors: dict[str, dict[int, complex]] = {
        "z2": {0: 1},
        "x2_y2": {-2: s, 2: s},
        "xy": {-2: 1j*s, 2: -1j*s},
        "xz": {-1: s, 1: -s},
        "yz": {-1: 1j*s, 1: 1j*s},
    }
    out = {}
    for label, values in vectors.items():
        coeff = np.zeros(5, complex)
        for m, value in values.items():
            coeff[m+2] = value
        out[label] = coeff
    return out


@dataclass(frozen=True)
class NiLocalConfig:
    """All material-dependent inputs are illustrative, *not Ni fitted data*."""
    l3_ev: float = 852.7
    l2_ev: float = 870.0
    zeff_2p: float = 25.0
    zeff_3d: float = 9.0
    crystal_field_10dq_ev: float = 0.8
    exchange_split_ev: float = 0.2
    eg_up_holes: float = 0.20
    eg_down_holes: float = 0.40
    t2g_up_holes: float = 0.20
    t2g_down_holes: float = 0.40

    def validate(self) -> None:
        values = np.asarray(list(asdict(self).values()), dtype=float)
        if not np.all(np.isfinite(values)) or not np.all(values[:4] > 0):
            raise ValueError("edge energies/effective charges must be positive finite; all fields finite")
        if self.l3_ev >= self.l2_ev:
            raise ValueError("L3 edge must be below L2")
        if self.crystal_field_10dq_ev < 0 or self.exchange_split_ev < 0:
            raise ValueError("crystal-field/exchange splittings must be nonnegative")
        holes = values[-4:]
        if not np.all((0 <= holes) & (holes <= 1)) or not np.any(holes > 0):
            raise ValueError("orbital/spin hole weights must be in [0,1] and nonzero")


def ni_local_transitions(config: NiLocalConfig = NiLocalConfig(), *,
                         radial_override_angstrom: float | None = None,
                         magnetization_sign: int = 1) -> TransitionDataset:
    """Local one-electron Ni transitions using 2p SOC and cubic d orbitals.

    Individual final cubic-orbital components interfere in dipole *amplitude*;
    different final orbitals and core states are incoherently summed later.
    Reversal swaps spin holes and reverses exchange shifts in this fixed
    core-SOC basis; the default +1 retains the historical calculation.
    """
    config.validate()
    if magnetization_sign not in (-1, 1):
        raise ValueError('magnetization_sign must be +1 or -1')
    if radial_override_angstrom is not None and (not np.isfinite(radial_override_angstrom)
                                                 or abs(radial_override_angstrom) < 1e-14):
        raise ValueError("radial override must be finite and nonzero")
    radial = (hydrogenic_radial_dipole_angstrom(config.zeff_2p, config.zeff_3d)
              if radial_override_angstrom is None else abs(radial_override_angstrom))
    basis = cubic_orbital_coefficients()
    energies, dipoles, weights, edges = [], [], [], []
    for two_j, edge, edge_energy in ((3, "L3", config.l3_ev), (1, "L2", config.l2_ev)):
        for two_mj in range(-two_j, two_j + 1, 2):
            for spin, name in ((1, "up"), (-1, "down")):
                for orbital, components in basis.items():
                    group = "eg" if orbital in ("z2", "x2_y2") else "t2g"
                    occupation_name = name if magnetization_sign == 1 else ('down' if name == 'up' else 'up')
                    holes = getattr(config, f"{group}_{occupation_name}_holes")
                    if holes <= 0:
                        continue
                    # Cubic 3d centroid fixed at zero:
                    # 2 eg at +3/5 Delta, 3 t2g at -2/5 Delta.
                    crystal_shift = (0.6 if group == "eg" else -0.4) * config.crystal_field_10dq_ev
                    exchange_shift = -0.5 * spin * magnetization_sign * config.exchange_split_ev
                    energy = edge_energy + crystal_shift + exchange_shift
                    if energy <= 0:
                        raise ValueError("resulting transition energy must be positive")
                    amplitude = np.zeros(3, dtype=complex)
                    for m in range(-2, 3):
                        if components[m+2] != 0:
                            amplitude += components[m+2] * ni_2p_to_3d_dipole(
                                two_j, two_mj, m, spin, radial)
                    if np.max(np.abs(amplitude)) > 1e-14:
                        energies.append(energy)
                        dipoles.append(amplitude)
                        weights.append(holes)
                        edges.append(edge)
    return TransitionDataset(
        energy_ev=np.asarray(energies, float),
        dipoles_angstrom=np.asarray(dipoles, complex),
        weights=np.asarray(weights, float),
        edge=np.asarray(edges, dtype=str),
        site=np.asarray(["Ni_local_atomic_model"] * len(energies), dtype=str),
        source=("NON_DFT_ILLUSTRATIVE_LOCAL_Ni_2p3d: normalized screened hydrogenic radial functions "
                f"(Zeff_2p={config.zeff_2p:g},Zeff_3d={config.zeff_3d:g}), "
                f"cubic field 10Dq={config.crystal_field_10dq_ev:g}eV, "
                f"exchange={config.exchange_split_ev:g}eV; M_sign={magnetization_sign}; "
                f"radial_source={'hydrogenic' if radial_override_angstrom is None else 'external_tabulated'}; "
                "NO many-body multiplets or Ni fit"),
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Ni local atomic crystal-field MDFF (NON-DFT, NOT quantitative Ni)")
    parser.add_argument("--output", type=Path, default=Path("outputs/ni_local_atomic_mdff"))
    parser.add_argument("--zeff-2p", type=float, default=25.0)
    parser.add_argument("--zeff-3d", type=float, default=9.0)
    parser.add_argument("--ten-dq-ev", type=float, default=0.8)
    parser.add_argument("--exchange-ev", type=float, default=0.2)
    parser.add_argument("--sigma-ev", type=float, default=0.8)
    parser.add_argument("--radial-table", type=Path, default=None,
                        help="CSV: radius_angstrom,R_2p,R_3d (full normalized or unnormalized R(r))")
    args = parser.parse_args(argv)
    cfg = NiLocalConfig(zeff_2p=args.zeff_2p, zeff_3d=args.zeff_3d,
                        crystal_field_10dq_ev=args.ten_dq_ev,
                        exchange_split_ev=args.exchange_ev)
    try:
        table_radial = None
        if args.radial_table is not None:
            tab = np.genfromtxt(args.radial_table, names=True, delimiter=",", encoding="utf-8")
            required = ("radius_angstrom", "R_2p", "R_3d")
            if tab.dtype.names is None or any(k not in tab.dtype.names for k in required):
                raise ValueError("radial table must contain radius_angstrom,R_2p,R_3d")
            table_radial = radial_dipole_from_table(*(tab[k] for k in required))
        ds = ni_local_transitions(cfg, radial_override_angstrom=table_radial)
        e = np.linspace(cfg.l3_ev-10, cfg.l2_ev+10, 251)
        tensor = dipole_tensor_from_transitions(ds, e, args.sigma_ev)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    args.output.mkdir(parents=True, exist_ok=True)
    ds.save_npz(args.output / "transitions.npz")
    tensor.save_npz(args.output / "mdff_tensor.npz")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    t = tensor.tensor_angstrom2_per_ev
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(e, np.trace(t, axis1=-2, axis2=-1).real/3, label="Tr(T)/3")
    ax.plot(e, t[:, 0, 1].imag, label="Im(Txy)")
    ax.set(xlabel="Energy loss (eV)", ylabel="Model tensor spectral weight (Å²/eV)",
           title="Non-DFT screened-hydrogenic Ni 2p → cubic 3d example")
    ax.legend()
    fig.tight_layout()
    fig.savefig(args.output / "mdff_tensor.png", dpi=160)
    plt.close(fig)
    metadata = {
        "model": "screened_hydrogenic_independent_electron_cubic_3d",
        "quantitative_Ni": False,
        "is_dft": False,
        "is_atomic_multiplet": False,
        "no_automatic_emcd_coupling": True,
        "config": asdict(cfg),
        "sigma_ev": args.sigma_ev,
        "radial_source": "tabulated_full_R" if args.radial_table else "screened_hydrogenic",
        "radial_table": str(args.radial_table) if args.radial_table else None,
        "radial_dipole_angstrom": (abs(table_radial) if table_radial is not None
                                     else hydrogenic_radial_dipole_angstrom(cfg.zeff_2p, cfg.zeff_3d)),
        "num_transitions": len(ds.energy_ev),
        "missing_physics": ["real Ni radial potential", "2p-3d Coulomb multiplets", "core hole",
                            "ligand charge transfer", "band dispersion", "DFT", "absolute cross section", "outgoing channeling"],
    }
    (args.output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "transitions": len(ds.energy_ev),
                      "radial_dipole_angstrom": metadata["radial_dipole_angstrom"],
                      "quantitative_Ni": False}, indent=2))


if __name__ == "__main__":
    main()
