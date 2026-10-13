"""Portable CSV -> TransitionDataset bridge for *already-computed* complex dipoles.

This is NOT an Elk/WIEN2k output parser or a DFT solver. Direct Elk ELNES.OUT
contains intensities, not the six real/imaginary components needed here.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from .mdff_tensor import TransitionDataset

REQUIRED = ("energy_ev", "dx_re", "dx_im", "dy_re", "dy_im", "dz_re", "dz_im",
            "weight", "edge", "site")


def import_transition_csv(path: Path | str, *, source: str,
                          amplitude_order: str = "initial_bra") -> TransitionDataset:
    """Read complex dipoles in Angstrom from a UTF-8 CSV (not DFT raw files).

    initial_bra: d=<i|r|f> as expected by the MDFF engine.
    final_bra: D=<f|r|i>, conjugated so d=D* (Cartesian r Hermitian).
    No conversion from <f|exp(iQ.r)|i> is assumed or performed.
    """
    if amplitude_order not in ("initial_bra", "final_bra"):
        raise ValueError("amplitude_order must be initial_bra or final_bra")
    if not isinstance(source, str) or not source.strip():
        raise ValueError("A specific nonempty data source/provenance is required")
    with Path(path).open("r", newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or not set(REQUIRED).issubset(reader.fieldnames):
            raise ValueError("Transition CSV requires columns: " + ", ".join(REQUIRED))
        energies, dipoles, weights, edges, sites = [], [], [], [], []
        for line_number, row in enumerate(reader, start=2):
            try:
                energies.append(float(row["energy_ev"]))
                dipoles.append([complex(float(row[x+"_re"]),float(row[x+"_im"]))
                                for x in ("dx","dy","dz")])
                weights.append(float(row["weight"]))
                edges.append(str(row["edge"]).strip())
                sites.append(str(row["site"]).strip())
            except (TypeError, ValueError, KeyError) as exc:
                raise ValueError(f"Malformed transition CSV row {line_number}") from exc
    if not energies:
        raise ValueError("Transition CSV has no data rows")
    d = np.asarray(dipoles, dtype=complex)
    if amplitude_order == "final_bra":
        d = d.conj()
    return TransitionDataset(np.asarray(energies), d, np.asarray(weights),
                             np.asarray(edges), np.asarray(sites),
                             source=f"CSV_DIPOLAR_TRANSITIONS: {source}; input_order={amplitude_order}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Convert already-computed complex core dipoles CSV to MDFF NPZ")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--source", required=True,
                        help="Provenance: DFT code, version, SOC, k grid, normalization (not inferred)")
    parser.add_argument("--amplitude-order", choices=("initial_bra","final_bra"),
                        default="initial_bra")
    args = parser.parse_args(argv)
    try:
        transitions = import_transition_csv(args.input, source=args.source,
                                           amplitude_order=args.amplitude_order)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    transitions.save_npz(args.output)
    print(json.dumps({"output":str(args.output),"transitions":len(transitions.energy_ev),
                      "source":transitions.source, "DFT_validated":False},indent=2))


if __name__ == "__main__":
    main()
