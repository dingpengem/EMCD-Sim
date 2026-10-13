"""Ni 2p(j,mj) -> 3d(m,ms) *angular* dipoles with exact core SOC coupling.

This is an atomic angular-momentum benchmark, not self-consistent Ni DFT:
3d final states are pure spherical harmonics with illustrative spin-dependent
hole occupations, 2p core edge energies are supplied, and the common radial
matrix element is freely specified. Do not use for quantitative Ni EMCD.

States follow the Condon--Shortley phase convention. Spin is conserved in the
length-gauge electric dipole, with 2p spin-orbit j coupling exactly included.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .mdff_tensor import TransitionDataset, dipole_tensor_from_transitions


# C(1, m_l; 1, q | 2, m_l + q), Condon--Shortley phases.
_SQRT2 = np.sqrt(2.0)
_CG_P_TO_D = {
    (-1, -1): 1.0, (-1, 0): 1.0/_SQRT2, (-1, 1): 1.0/np.sqrt(6.0),
    (0, -1): 1.0/_SQRT2, (0, 0): np.sqrt(2.0/3.0), (0, 1): 1.0/_SQRT2,
    (1, -1): 1.0/np.sqrt(6.0), (1, 0): 1.0/_SQRT2, (1, 1): 1.0,
}


def core_spinor_amplitude(two_j: int, two_mj: int, two_ms: int) -> float:
    """<l=1,m_l; s=1/2,m_s|j,m_j>, where m_l=(2mj-2ms)/2.

    Integers represent twice j/m_j/m_s, avoiding half-integer indexing.
    """
    if two_j not in (1, 3) or two_ms not in (-1, 1):
        raise ValueError("Core j must be 1/2 or 3/2, ms must be +/-1/2")
    if abs(two_mj) > two_j or (two_mj % 2) != (two_j % 2):
        raise ValueError("Invalid 2p core m_j")
    ml = (two_mj - two_ms)//2
    if abs(ml) > 1:
        return 0.0
    mj = two_mj / 2.0
    if two_j == 3:  # j = l + 1/2
        return float(np.sqrt((1.5 + mj) / 3.0) if two_ms == 1
                     else np.sqrt((1.5 - mj) / 3.0))
    # j = l - 1/2, CS phase convention
    return float(np.sqrt((1.5 - mj) / 3.0) if two_ms == 1
                 else -np.sqrt((1.5 + mj) / 3.0))


def ni_2p_to_3d_dipole(two_j: int, two_mj: int, final_m: int,
                       two_ms: int, radial_angstrom: float = 1.0) -> np.ndarray:
    """Cartesian complex d=<core|r|final> for a pure atomic |3d,m,ms>.

    0 radial integral is a shared model parameter; for angular harmonics
    <2m_f|n_q|1m_i> = sqrt(2/5)*C(1 m_i, 1 q|2 m_f).
    Spherical n_{+1}=-(x+iy)/sqrt(2), n_{-1}=(x-iy)/sqrt(2).
    """
    if final_m not in range(-2, 3):
        raise ValueError("3d magnetic quantum number must be -2,...,+2")
    if not np.isfinite(radial_angstrom) or radial_angstrom <= 0:
        raise ValueError("radial_angstrom must be finite positive")
    core = core_spinor_amplitude(two_j, two_mj, two_ms)
    ml = (two_mj - two_ms)//2
    components = {}
    for q in (-1, 0, 1):
        components[q] = (radial_angstrom * core * np.sqrt(2.0/5.0)
                         * _CG_P_TO_D.get((ml, q), 0.0)
                         if final_m == ml + q else 0.0)
    # First calculate <final|r|core>; Hermitian conjugation gives <core|r|final>.
    x = (components[-1] - components[1]) / _SQRT2
    y = 1j * (components[-1] + components[1]) / _SQRT2
    z = components[0]
    return np.conjugate(np.asarray((x, y, z), dtype=complex))


@dataclass(frozen=True)
class NiAtomicReferenceConfig:
    """Illustrative final-state hole occupations; not fitted Ni DFT values."""
    l3_ev: float = 852.7
    l2_ev: float = 870.0
    radial_dipole_angstrom: float = 1.0
    spin_up_hole_weight: float = 0.2
    spin_down_hole_weight: float = 0.4

    def validate(self) -> None:
        numbers = np.asarray((self.l3_ev, self.l2_ev, self.radial_dipole_angstrom,
                              self.spin_up_hole_weight, self.spin_down_hole_weight), dtype=float)
        if not np.all(np.isfinite(numbers)) or np.any(numbers[:3] <= 0):
            raise ValueError("Energies and radial amplitude must be positive and finite")
        if self.l3_ev >= self.l2_ev:
            raise ValueError("L3 must precede L2")
        if not np.all((numbers[3:] >= 0) & (numbers[3:] <= 1)):
            raise ValueError("Spin hole weights must lie within [0, 1]")
        if not np.any(numbers[3:] > 0):
            raise ValueError("At least one unoccupied final-state weight is required")


def ni_atomic_transitions(config: NiAtomicReferenceConfig = NiAtomicReferenceConfig()) -> TransitionDataset:
    """Generate exact 2p core spinor-angular dipoles; model 3d holes/energies.

    Final basis |3d,m,spin> is *not* a Ni band-structure eigenbasis. Every
    occupied 2p (j,mj) is counted once, transitions weighted by 3d holes.
    """
    config.validate()
    energies, dipoles, weights, edges = [], [], [], []
    for two_j, edge, energy in ((3, "L3", config.l3_ev), (1, "L2", config.l2_ev)):
        for two_mj in range(-two_j, two_j + 1, 2):
            for two_ms, hole in ((1, config.spin_up_hole_weight),
                                 (-1, config.spin_down_hole_weight)):
                for final_m in range(-2, 3):
                    if hole == 0:
                        continue
                    d = ni_2p_to_3d_dipole(two_j, two_mj, final_m,
                                           two_ms, config.radial_dipole_angstrom)
                    if np.any(np.abs(d) > 1e-14):
                        energies.append(energy)
                        dipoles.append(d)
                        weights.append(hole)
                        edges.append(edge)
    return TransitionDataset(
        energy_ev=np.asarray(energies, dtype=float),
        dipoles_angstrom=np.asarray(dipoles, dtype=complex),
        weights=np.asarray(weights, dtype=float),
        edge=np.asarray(edges, dtype=str),
        site=np.asarray(["Ni_atomic_angular"] * len(energies), dtype=str),
        source=("NI_ATOMIC_ANGULAR_REFERENCE_NOT_DFT: 2p j,mj core SOC and "
                "2p->3d dipole CG angular matrix elements; spin-hole weights "
                "and common radial integral are illustrative"),
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Ni 2p spin-orbit atomic angular reference, NOT DFT")
    parser.add_argument("--output", type=Path, default=Path("outputs/ni_atomic_reference"))
    parser.add_argument("--l3-ev", type=float, default=852.7)
    parser.add_argument("--l2-ev", type=float, default=870.0)
    parser.add_argument("--radial-dipole-angstrom", type=float, default=1.0)
    parser.add_argument("--spin-up-holes", type=float, default=0.2)
    parser.add_argument("--spin-down-holes", type=float, default=0.4)
    parser.add_argument("--sigma-ev", type=float, default=0.9)
    args = parser.parse_args(argv)
    cfg = NiAtomicReferenceConfig(args.l3_ev, args.l2_ev, args.radial_dipole_angstrom,
                                  args.spin_up_holes, args.spin_down_holes)
    try:
        transitions = ni_atomic_transitions(cfg)
        if not np.isfinite(args.sigma_ev) or args.sigma_ev <= 0:
            raise ValueError("sigma must be positive")
        energy = np.linspace(args.l3_ev - 10, args.l2_ev + 10, 241)
        tensor = dipole_tensor_from_transitions(transitions, energy, args.sigma_ev)
    except ValueError as exc:
        parser.error(str(exc))
    args.output.mkdir(parents=True, exist_ok=True)
    transitions.save_npz(args.output/"ni_atomic_transitions.npz")
    tensor.save_npz(args.output/"ni_atomic_tensor.npz")
    values = tensor.tensor_angstrom2_per_ev
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8,4))
    ax.plot(energy, np.trace(values,axis1=-2,axis2=-1).real/3, label="Tr(T)/3")
    ax.plot(energy, values[:,0,1].imag, label="Im(Txy)")
    ax.set(xlabel="Energy loss (eV)", ylabel="Spectral dipole weight (model Å²/eV)",
           title="Ni 2p SOC angular reference — illustrative 3d holes/radial scale")
    ax.legend(); fig.tight_layout()
    fig.savefig(args.output/"ni_atomic_tensor.png", dpi=160);plt.close(fig)
    metadata = {"model":"Ni 2p->3d atomic angular reference with exact core j coupling",
                "not_dft": True,"quantitative_ni": False,
                "illustrative_final_state": True,
                "config": vars(args) | {"output":str(args.output)},
                "num_transitions": len(transitions.energy_ev),
                "source":transitions.source,
                "limitations":"No DFT bands, final-state SOC/crystal field, core hole, calibrated radial integral or absolute cross section"}
    (args.output/"metadata.json").write_text(json.dumps(metadata,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"output":str(args.output),"transitions":len(transitions.energy_ev),
                      "quantitative_ni":False},indent=2))

if __name__=="__main__":
    main()
