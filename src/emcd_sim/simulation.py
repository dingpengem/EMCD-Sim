"""Geometry/model containers and tensor-solver detector results."""
from dataclasses import dataclass
from typing import Mapping
import numpy as np
from .physical_elastic import PhysicalElasticModel
from .geometry import VirtualDetector


@dataclass(frozen=True)
class SimulationResult:
    energy_ev: np.ndarray
    qx_angstrom_inv: np.ndarray
    qy_angstrom_inv: np.ndarray
    nonmag_map_at_l3: np.ndarray
    magnetic_map_at_l3: np.ndarray
    detector_spectra: Mapping[str, np.ndarray]
    detector_masks: Mapping[str, np.ndarray]
    moment_muB: float | None
    thickness_nm: float
    voltage_v: float
    chiral_groups: Mapping[str, tuple[str, ...]] | None = None

    # Boolean masks retain center membership; integration weights are separate.
    detector_weights: Mapping[str, np.ndarray] | None = None
    integration_mode: str = "binary"
    aperture_subpixels: int = 64

    def chiral_spectrum(self, label: str) -> np.ndarray:
        """Sum physical aperture spectra belonging to one chirality group."""
        names = (self.chiral_groups[label] if self.chiral_groups is not None
                 else (label,))
        return sum((self.detector_spectra[name] for name in names),
                   np.zeros_like(self.energy_ev))

    def difference(self, positive: str = "A", negative: str = "B") -> np.ndarray:
        return self.chiral_spectrum(positive) - self.chiral_spectrum(negative)

    def asymmetry(self, positive: str = "A", negative: str = "B") -> np.ndarray:
        a, b = self.chiral_spectrum(positive), self.chiral_spectrum(negative)
        return np.divide(a-b, a+b, out=np.zeros_like(a), where=(a+b)!=0)

    def at_edge(self, edge_ev: float = 852.7) -> tuple[float, float, float]:
        i = int(np.argmin(abs(self.energy_ev-edge_ev)))
        return float(self.energy_ev[i]), float(self.difference()[i]), float(self.asymmetry()[i])


@dataclass(frozen=True)
class EMCDSimulation:
    elastic: PhysicalElasticModel
    detectors: Mapping[str, VirtualDetector]
    magnetization_direction_xyz: tuple[float, float, float] = (0.0, 0.0, 1.0)
    chiral_groups: Mapping[str, tuple[str, ...]] | None = None

    def __post_init__(self) -> None:
        if len(self.detectors) < 2:
            raise ValueError("At least two detectors are required")
        direction = np.asarray(self.magnetization_direction_xyz, dtype=float)
        if direction.shape != (3,) or not np.all(np.isfinite(direction)) or np.linalg.norm(direction) < 1e-12:
            raise ValueError("magnetization direction must be a nonzero 3-vector")
        if self.chiral_groups is not None:
            if set(self.chiral_groups) != {"A", "B"}:
                raise ValueError("chiral_groups must define A and B")
            a, b = set(self.chiral_groups["A"]), set(self.chiral_groups["B"])
            if not a or not b or a & b or a | b != set(self.detectors):
                raise ValueError("chiral groups must partition all physical apertures")
