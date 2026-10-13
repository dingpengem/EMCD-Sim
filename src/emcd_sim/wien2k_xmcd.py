"""Import WIEN2k joint XMCD data; this is not a complex transition dataset."""
from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
import hashlib
import numpy as np

@dataclass(frozen=True)
class XMCDSpectrum:
    energy_ev: np.ndarray
    right: np.ndarray
    left: np.ndarray
    source_sha256: str

    @property
    def nonmagnetic(self):
        return (self.right + self.left) / 2

    @property
    def dichroic(self):
        return (self.right - self.left) / 2

def load_wien2k_xmcd(path: str | Path) -> XMCDSpectrum:
    path = Path(path)
    a = np.loadtxt(path, comments="#", ndmin=2)
    if a.ndim != 2 or a.shape[1] != 5 or len(a) < 2:
        raise ValueError("Expected 5 columns: energy, RP, LP, XMCD, XAS")
    if not np.all(np.isfinite(a)) or np.any(a[:,0] <= 0) or np.any(np.diff(a[:,0]) <= 0):
        raise ValueError("Invalid energy sampling")
    if np.any(a[:,1:3] < 0):
        raise ValueError("Negative polarization intensity")
    scale = max(float(np.max(np.abs(a[:,1:]))), 1e-20)
    if not np.allclose(a[:,1]-a[:,2], a[:,3], atol=5e-6*scale, rtol=5e-5):
        raise ValueError("XMCD mismatch with RP - LP")
    if not np.allclose(a[:,1]+a[:,2], a[:,4], atol=5e-6*scale, rtol=5e-5):
        raise ValueError("XAS mismatch with RP + LP")
    return XMCDSpectrum(a[:,0].copy(), a[:,1].copy(), a[:,2].copy(),
                        hashlib.sha256(path.read_bytes()).hexdigest())
