"""Plot WIEN2k Ni XMCD/XAS spectra and save publication-friendly SVG/PNG outputs.

This visualizes the user-provided 5-column `Ni_fm.xmcd` file:
energy (eV), RIGHT_POL, LEFT_POL, XMCD=RP-LP, XAS=RP+LP.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .wien2k_xmcd import load_wien2k_xmcd


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Plot WIEN2k Ni XMCD / XAS spectra")
    parser.add_argument("--xmcd-file", type=Path, default=Path("data/wien2k_ni/Ni_fm.xmcd"))
    parser.add_argument("--output-dir", type=Path, default=Path("examples/ni_xmcd_indexed"))
    parser.add_argument("--window-min-ev", type=float, default=845.0)
    parser.add_argument("--window-max-ev", type=float, default=878.0)
    args = parser.parse_args(argv)

    spec = load_wien2k_xmcd(args.xmcd_file)
    E = spec.energy_ev
    RP = spec.right
    LP = spec.left
    XMCD = spec.right - spec.left
    XAS = spec.right + spec.left
    NXMCD = np.divide(XMCD, XAS, out=np.zeros_like(XMCD), where=np.abs(XAS) > 0)

    mask = (E >= args.window_min_ev) & (E <= args.window_max_ev)
    Ef, RPf, LPf, XMCDf, XASf, NXMCDf = E[mask], RP[mask], LP[mask], XMCD[mask], XAS[mask], NXMCD[mask]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(8.2, 9.6))
    axs = [fig.add_subplot(4, 1, i + 1) for i in range(4)]

    axs[0].plot(Ef, RPf, label="RIGHT_POL (RP)")
    axs[0].plot(Ef, LPf, label="LEFT_POL (LP)")
    axs[0].plot(Ef, XASf, label="XAS = RP + LP")
    axs[0].set_ylabel("Intensity (arb. units)")
    axs[0].set_title("FCC Ni WIEN2k DFT XAS / XMCD around Ni L3 and L2")
    axs[0].legend(fontsize=8)

    axs[1].plot(Ef, XMCDf)
    axs[1].axhline(0.0, linewidth=0.8)
    axs[1].set_ylabel("XMCD = RP - LP")
    axs[1].set_title("XMCD difference spectrum")

    axs[2].plot(Ef, NXMCDf)
    axs[2].axhline(0.0, linewidth=0.8)
    axs[2].set_ylabel("XMCD / XAS")
    axs[2].set_title("Normalized XMCD")

    axs[3].plot(E, XAS, label="Full-range XAS")
    axs[3].plot(E, XMCD, label="Full-range XMCD")
    axs[3].set_xlabel("Energy (eV)")
    axs[3].set_ylabel("Intensity (arb. units)")
    axs[3].set_title("Full energy range from WIEN2k output")
    axs[3].legend(fontsize=8)

    for ax in axs:
        ax.grid(True, alpha=0.25)
        ax.axvline(852.7, linewidth=0.8)
        ax.axvline(870.0, linewidth=0.8)
    axs[0].text(852.7, axs[0].get_ylim()[1] * 0.92, "L3", ha="center", va="top", fontsize=9)
    axs[0].text(870.0, axs[0].get_ylim()[1] * 0.92, "L2", ha="center", va="top", fontsize=9)

    fig.tight_layout()
    fig.savefig(args.output_dir / "ni_dft_xmcd.svg")
    fig.savefig(args.output_dir / "ni_dft_xmcd.png", dpi=180)
    plt.close(fig)

    with (args.output_dir / "ni_dft_xmcd_summary.txt").open("w", encoding="utf-8") as f:
        f.write("WIEN2k FCC Ni DFT XMCD summary\n")
        f.write(f"Energy range: {E.min():.3f} to {E.max():.3f} eV\n")
        f.write(f"Max XAS: {XAS.max():.6e}\n")
        f.write(f"Max |XMCD|: {np.max(np.abs(XMCD)):.6e}\n")
        f.write("Figure files: ni_dft_xmcd.svg, ni_dft_xmcd.png\n")


if __name__ == "__main__":
    main()