"""Cross-platform P2 reference calculation from a transition table or toy data."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import numpy as np
from .mdff_tensor import TransitionDataset, dipole_tensor_from_transitions


def toy_transitions() -> TransitionDataset:
    """Synthetic mathematical chirality example, NOT Ni DFT or experimental data."""
    # A complex in-plane dipole represents a circular/helicity-sensitive mode.
    # L3 and L2 are assigned opposite handedness only to exercise the algebra.
    return TransitionDataset(
        energy_ev=np.array([852.7, 870.0, 852.7, 870.0]),
        dipoles_angstrom=np.array([[1,1j,0],[1,-1j,0],[0,0,.65],[0,0,.45]],complex),
        weights=np.array([1,.5,.3,.3]),
        edge=np.array(["L3","L2","L3","L2"]),
        site=np.array(["Ni_demo"]*4),
        source="SYNTHETIC toy transitions: NOT computed from Ni wavefunctions",
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Construct a dipole MDFF tensor from complex transition amplitudes")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--transitions", type=Path, help="NPZ with energies, complex dipoles, weights, edges and sites")
    group.add_argument("--toy", action="store_true", help="Synthetic chirality example; NOT a Ni calculation")
    parser.add_argument("--output", type=Path, default=Path("outputs/mdff_tensor"))
    parser.add_argument("--sigma-ev", type=float, default=0.8)
    parser.add_argument("--min-ev", type=float, default=840.0)
    parser.add_argument("--max-ev", type=float, default=883.0)
    parser.add_argument("--points", type=int, default=173)
    args = parser.parse_args(argv)
    if not (args.points >= 2 and args.min_ev > 0 and args.max_ev > args.min_ev):
        parser.error("Requires points>=2 and 0 < min-ev < max-ev")
    trans = toy_transitions() if args.toy else TransitionDataset.load_npz(args.transitions)
    energy = np.linspace(args.min_ev, args.max_ev, args.points)
    tensor = dipole_tensor_from_transitions(trans, energy, args.sigma_ev)
    args.output.mkdir(parents=True, exist_ok=True)
    tensor.save_npz(args.output / "mdff_tensor.npz")
    if args.toy:
        trans.save_npz(args.output / "toy_transitions.npz")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8,4))
    values = tensor.tensor_angstrom2_per_ev
    ax.plot(energy, np.trace(values, axis1=1,axis2=2).real/3, label="Tr(T)/3, nonmag-like")
    ax.plot(energy, values[:,0,1].imag, label="Im[Txy], chiral")
    ax.set(xlabel="Energy loss (eV)",ylabel="Tensor spectral weight (Å²/eV)",
           title="Synthetic MDFF tensor" if args.toy else "Transition-derived MDFF tensor")
    ax.legend()
    fig.tight_layout(); fig.savefig(args.output / "mdff_tensor.png",dpi=160);plt.close(fig)
    metadata={"source":trans.source,"toy":args.toy,"num_transitions":len(trans.energy_ev),
              "sigma_ev":args.sigma_ev,"tensor_convention":"T_ab=sum w*d_a*conj(d_b)*G(E-En)",
              "dipoles":"<i|r|f> Angstrom", "q_required":"angular rad/Angstrom",
              "quantitative_Ni":False,"note":"No Ni SOC-DFT transitions supplied; no outgoing channeling"}
    (args.output/"metadata.json").write_text(json.dumps(metadata,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"output":str(args.output),"transitions":len(trans.energy_ev),
                      "source":trans.source,"quantitative_Ni":False},indent=2))

if __name__ == "__main__":
    main()
