"""Relativistic wavelength and reciprocal-space virtual detectors."""
from dataclasses import dataclass
import numpy as np

HC_EV_ANGSTROM = 12398.419843320026
MC2_EV = 510998.95


def electron_wavelength_angstrom(acceleration_kv: float) -> float:
    """Relativistic de Broglie wavelength in angstroms."""
    if acceleration_kv <= 0:
        raise ValueError("accelerating voltage must be positive")
    kinetic_ev = acceleration_kv * 1e3
    return HC_EV_ANGSTROM / np.sqrt(kinetic_ev * (kinetic_ev + 2 * MC2_EV))


def electron_beta(acceleration_kv: float) -> float:
    if acceleration_kv <= 0:
        raise ValueError("accelerating voltage must be positive")
    gamma = 1.0 + acceleration_kv * 1e3 / MC2_EV
    return float(np.sqrt(1.0 - 1.0 / gamma**2))


def characteristic_qz_angstrom_inv(loss_ev: float, acceleration_kv: float) -> float:
    """Small-loss longitudinal momentum transfer E/(h*v), cycles per angstrom."""
    if loss_ev <= 0:
        raise ValueError("energy loss must be positive")
    return loss_ev / (HC_EV_ANGSTROM * electron_beta(acceleration_kv))


@dataclass(frozen=True)
class Microscope:
    acceleration_kv: float = 200.0
    tilt_mrad_xy: tuple[float, float] = (0.0, 0.0)

    def __post_init__(self) -> None:
        electron_wavelength_angstrom(self.acceleration_kv)
        if len(self.tilt_mrad_xy) != 2:
            raise ValueError("tilt_mrad_xy must be a pair")

    @property
    def incident_k_xy(self) -> np.ndarray:
        return np.asarray(self.tilt_mrad_xy, dtype=float) * 1e-3 / electron_wavelength_angstrom(self.acceleration_kv)


@dataclass(frozen=True)
class VirtualDetector:
    """Circular virtual EELS aperture in reciprocal units, cycles per angstrom."""
    center_q_xy: tuple[float, float]
    radius_q: float

    def __post_init__(self) -> None:
        if len(self.center_q_xy) != 2 or self.radius_q <= 0:
            raise ValueError("detector needs center (qx,qy) and positive radius")

    def mask(self, qx: np.ndarray, qy: np.ndarray) -> np.ndarray:
        return ((qx - self.center_q_xy[0]) ** 2
                + (qy - self.center_q_xy[1]) ** 2 <= self.radius_q**2)
