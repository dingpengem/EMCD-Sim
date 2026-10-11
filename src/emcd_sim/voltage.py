"""Voltage-to-magnetization interfaces; data-driven only, no guessed magnetoelectric law."""
from dataclasses import dataclass
from typing import Protocol
import numpy as np


class MagnetizationLaw(Protocol):
    def __call__(self, voltage_v: float) -> float: ...


@dataclass(frozen=True)
class ConstantMagnetization:
    moment_muB: float = 0.60

    def __call__(self, voltage_v: float) -> float:
        return float(self.moment_muB)


@dataclass(frozen=True)
class TabulatedMagnetization:
    """Interpolate user-supplied Ni moment (muB/atom) vs applied bias (V).

    Requires experimentally established or externally calculated inputs.
    Extrapolation is disallowed. Negative values encode magnetization reversal.
    """
    voltages_v: tuple[float, ...]
    moments_muB: tuple[float, ...]

    def __post_init__(self) -> None:
        vs, ms = np.asarray(self.voltages_v), np.asarray(self.moments_muB)
        if len(vs) < 2 or vs.shape != ms.shape or not np.all(np.isfinite(vs)) or not np.all(np.isfinite(ms)) or not np.all(np.diff(vs) > 0):
            raise ValueError("Provide >=2 finite, strictly ascending bias values and equal-length moments")

    def __call__(self, voltage_v: float) -> float:
        if not np.isfinite(voltage_v) or not self.voltages_v[0] <= voltage_v <= self.voltages_v[-1]:
            raise ValueError("Requested voltage outside calibrated bias range")
        return float(np.interp(voltage_v, self.voltages_v, self.moments_muB))
