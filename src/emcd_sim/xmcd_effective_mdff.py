"""XMCD-constrained effective dipole tensor; NOT full ab-initio MDFF."""
from __future__ import annotations
from pathlib import Path
import numpy as np
from .mdff_tensor import DipoleTensor
from .wien2k_xmcd import load_wien2k_xmcd

def effective_tensor_from_xmcd(path: str | Path,
                               energy_ev: np.ndarray | None = None,
                               *, eta: float = 1.0, beta: float = 1.0,
                               normalize: bool = True) -> DipoleTensor:
    """Axisymmetric z-magnetized proxy: Txx=Tyy=N; Txy=i*eta*D; Tzz=beta*N.

    D=(RP-LP)/2; eta sign/scale must be checked against the polarization,
    dipole conventions and experiment. beta represents unmeasured longitudinal
    response. Dipole approximation; relative units only; no extrapolation.
    """
    if not np.isfinite(eta) or not np.isfinite(beta) or beta < 0:
        raise ValueError("Require finite eta and beta>=0")
    s = load_wien2k_xmcd(path)
    e = s.energy_ev if energy_ev is None else np.asarray(energy_ev, dtype=float)
    if e.ndim != 1 or len(e) < 2 or not np.all(np.isfinite(e)) or np.any(np.diff(e) <= 0):
        raise ValueError("Energy grid must be increasing with at least 2 points")
    if e[0] < s.energy_ev[0] or e[-1] > s.energy_ev[-1]:
        raise ValueError("No XMCD spectral extrapolation")
    n = np.interp(e, s.energy_ev, s.nonmagnetic)
    m = eta * np.interp(e, s.energy_ev, s.dichroic)
    if np.any(abs(m) > n + 1e-12*max(float(n.max()),1e-30)):
        raise ValueError("Tensor is not positive semidefinite; reduce |eta|")
    scale = float(np.max(s.nonmagnetic)) if normalize else 1.
    if scale <= 0:
        raise ValueError("Zero XAS reference")
    n, m = n/scale, m/scale
    t = np.zeros((len(e),3,3), dtype=complex)
    t[:,0,0] = t[:,1,1] = n
    t[:,2,2] = beta*n
    t[:,0,1] = 1j*m
    t[:,1,0] = -1j*m
    return DipoleTensor(e, t, "XMCD_EFFECTIVE_NOT_ABINITIO;eta=%s;beta=%s;sha256=%s" %
                        (eta,beta,s.source_sha256))
