"""Fail-closed metadata/structure audit for externally computed FCC-Ni L2,3 dipoles.

This audit is NOT scientific validation of a DFT calculation. It checks that
its owner supplied a phase-specific, complex-amplitude dataset with consistent
units and provenance. Neither XAS/ELNES intensities nor NiO/ionic Ni sources
can substitute for metallic FCC Ni transition dipoles.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from .mdff_tensor import TransitionDataset, dipole_tensor_from_transitions


REQUIRED = (
    "material", "phase", "absorber", "edges", "method", "code",
    "code_version", "core_spin_orbit", "spin_polarized",
    "data_type", "dipole_convention", "dipole_units", "complex_phase_preserved",
    "weights_definition", "core_state_definition", "k_point_definition",
    "reference_url", "citation", "input_description",
)


def audit_metallic_ni_transitions(
    transitions: Path | str, provenance: Path | str,
) -> dict[str, Any]:
    """Audit *declared metadata* and algebra, not the truth of its DFT provenance.

    Input is a TransitionDataset NPZ containing physical *complex amplitudes*.
    The accompanying JSON must describe FCC Ni specifically. Even after all
    checks, a publication-quality Ni MDFF needs independent spectroscopic and
    electronic-structure convergence benchmarks.
    """
    path = Path(transitions)
    meta_path = Path(provenance)
    with meta_path.open("r", encoding="utf-8") as stream:
        metadata = json.load(stream)
    if not isinstance(metadata, dict):
        raise ValueError("Provenance JSON must contain an object")
    missing = [field for field in REQUIRED if field not in metadata]
    if missing:
        raise ValueError("Missing required Ni transition provenance fields: " + ", ".join(missing))
    exact = {
        "material": "Ni", "phase": "fcc_metal", "absorber": "Ni",
        "data_type": "complex_length_gauge_dipoles", "dipole_units": "angstrom",
        "dipole_convention": "<i|r|f>",
    }
    for key, value in exact.items():
        if metadata[key] != value:
            raise ValueError(f"{key} must be exactly {value!r}; NiO and other Ni compounds are NOT FCC metallic Ni")
    if not isinstance(metadata["edges"], list) or set(metadata["edges"]) != {"L2", "L3"}:
        raise ValueError("Both separately identified L2 and L3 edges are required")
    for key in ("core_spin_orbit", "spin_polarized", "complex_phase_preserved"):
        if metadata[key] is not True:
            raise ValueError(f"{key} must be declared true for a metallic magnetic Ni transition source")
    for key in ("method", "code", "code_version", "weights_definition",
                "core_state_definition", "k_point_definition", "reference_url", "citation", "input_description"):
        if not isinstance(metadata[key], str) or not metadata[key].strip():
            raise ValueError(f"{key} needs a specific non-empty provenance string")
    if metadata["method"].strip().lower() in {"toy", "illustrative", "synthetic", "gaussian", "non-dft atomic"}:
        raise ValueError("Toy/illustrative models cannot be relabeled as external metallic Ni reference transitions")
    ds = TransitionDataset.load_npz(path)
    src = ds.source.casefold()
    if any(mark in src for mark in ("synthetic", "not_dft", "illustrative", "toy transitions", "angular_reference", "ni_local")):
        raise ValueError("Dataset itself is marked illustrative/non-DFT; cannot relabel its provenance")
    if set(ds.edge.tolist()) != {"L2", "L3"}:
        raise ValueError("Transition data must contain exactly L2 and L3 labels")
    if not np.any(np.abs(ds.dipoles_angstrom.imag) > 1e-12):
        raise ValueError("No imaginary transition amplitudes are resolved; phase-sensitive magnetic MDFF cannot be audited")
    if not np.any(ds.weights > 0):
        raise ValueError("At least one nonzero transition weight required")
    grid = np.linspace(float(ds.energy_ev.min())-3, float(ds.energy_ev.max())+3, 65)
    tensors = dipole_tensor_from_transitions(ds, grid, 0.8)
    minimum = min(float(np.linalg.eigvalsh(t).min()) for t in tensors.tensor_angstrom2_per_ev)
    if minimum < -1e-9:
        raise ValueError("Tensor violates positive semidefiniteness")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "status": "format_and_declared_provenance_passed_NOT_physics_validated",
        "material": "Ni", "phase": "fcc_metal",
        "input_sha256": digest,
        "transition_count": int(len(ds.energy_ev)),
        "edges": sorted(set(ds.edge.tolist())),
        "sites": sorted(set(ds.site.tolist())),
        "energy_ev_min": float(ds.energy_ev.min()),
        "energy_ev_max": float(ds.energy_ev.max()),
        "tensor_min_eigenvalue": minimum,
        "declared_source": ds.source,
        "metadata": metadata,
        "quantitative_Ni_certified": False,
        "warning": "Metadata assertions cannot establish DFT physics, SOC accuracy, correct absolute normalization, or experimental agreement.",
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Audit provenance of external FCC Ni complex L2,3 transition matrices (not scientific verification)")
    parser.add_argument("--transitions", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("outputs/ni_transition_data_audit.json"))
    args = parser.parse_args(argv)
    try:
        report = audit_metallic_ni_transitions(args.transitions, args.provenance)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "status": report["status"],
                      "quantitative_Ni_certified": False}, indent=2))


if __name__ == "__main__":
    main()
