"""Phenomenological energy-loss spectra and cubic dipole MDFF tensor.

S(q,q',E) = [N(E) (q dot q') + i M(E) m_hat dot (q cross q')]
             / (|q|^2 |q'|^2)

All q are in cycles/angstrom, including |q_z|=E/(h*v). The overall prefactor,
local dynamical form factors, radial matrix elements and core-hole fine
structure are deliberately NOT calibrated in v0.
"""
from dataclasses import dataclass
from typing import Protocol
import numpy as np


def gaussian(x: np.ndarray, center: float, sigma: float) -> np.ndarray:
    return np.exp(-0.5 * ((x - center) / sigma) ** 2)


class SpectrumModel(Protocol):
    """E-resolved nonmagnetic and unit-normalized magnetic functions."""
    def values(self, energy_ev: np.ndarray) -> tuple[np.ndarray, np.ndarray]: ...


@dataclass(frozen=True)
class TabulatedEdgeSpectrum:
    """Experimental/DFT-provided energy-resolved nonmag and magnetic channels.

    The tabulated magnetic contribution corresponds to the reference moment;
    the linear moment scaling in DipoleMDFF is still a separable approximation.
    """
    energy_ev: tuple[float, ...]
    nonmagnetic: tuple[float, ...]
    magnetic: tuple[float, ...]

    def __post_init__(self) -> None:
        e = np.asarray(self.energy_ev, dtype=float)
        n = np.asarray(self.nonmagnetic, dtype=float)
        m = np.asarray(self.magnetic, dtype=float)
        if len(e) < 2 or e.shape != n.shape or e.shape != m.shape:
            raise ValueError("Spectrum arrays must be matching length >= 2")
        if not np.all(np.isfinite(e)) or not np.all(np.diff(e)>0) or np.any(e<=0):
            raise ValueError("Spectrum energies must be finite, positive and strictly increasing")
        if not np.all(np.isfinite(n)) or not np.all(np.isfinite(m)) or np.any(n<0) or np.any(np.abs(m)>n):
            raise ValueError("Require |M(E)|<=N(E) for positive-semidefinite dipole tensor")

    def values(self, energy_ev: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        e = np.asarray(energy_ev, dtype=float)
        if np.any(e < self.energy_ev[0]) or np.any(e > self.energy_ev[-1]):
            raise ValueError("Requested energy outside tabulated ELNES/MDFF data")
        return np.interp(e, self.energy_ev, self.nonmagnetic), np.interp(e, self.energy_ev, self.magnetic)


@dataclass(frozen=True)
class LEdgeSpectrum:
    """Ni L2,3-inspired *illustrative* line shapes, not measured ELNES/DFT data."""
    l3_ev: float = 852.7
    l2_ev: float = 870.0
    width_ev: float = 1.8
    l3_intensity: float = 1.0
    l2_intensity: float = 0.5
    background: float = 0.10
    magnetic_fraction: float = 0.12
    l2_magnetic_ratio: float = -0.5

    def __post_init__(self) -> None:
        if self.width_ev <= 0 or min(self.l3_intensity, self.l2_intensity, self.background) < 0:
            raise ValueError("width must be positive; intensities nonnegative")
        if abs(self.magnetic_fraction) > 1:
            raise ValueError("magnetic_fraction must be in [-1,1]")
        if abs(self.l2_magnetic_ratio * self.magnetic_fraction) > 1:
            raise ValueError("L2 magnetic tensor must remain positive semidefinite")

    def values(self, energy_ev: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        e = np.asarray(energy_ev, dtype=float)
        p3 = self.l3_intensity * gaussian(e, self.l3_ev, self.width_ev)
        p2 = self.l2_intensity * gaussian(e, self.l2_ev, self.width_ev)
        nonmag = self.background + p3 + p2
        magnetic = self.magnetic_fraction * (p3 + self.l2_magnetic_ratio * p2)
        return nonmag, magnetic


@dataclass(frozen=True)
class DipoleMDFF:
    spectrum: SpectrumModel
    reference_moment_muB: float = 0.60
    reference_energy_ev: float = 852.7

    def __post_init__(self) -> None:
        if self.reference_moment_muB <= 0 or self.reference_energy_ev <= 0:
            raise ValueError("reference_moment_muB must be positive")

    def terms(self, energy_ev: np.ndarray, moment_muB: float) -> tuple[np.ndarray, np.ndarray]:
        nonmag, mag = self.spectrum.values(energy_ev)
        scaled = mag * moment_muB / self.reference_moment_muB
        if np.any(np.abs(scaled) > nonmag + 1e-12):
            raise ValueError("Magnetic response exceeds nonmagnetic response: unsupported extrapolation")
        return nonmag, scaled
