"""Finite-beam Hermitian dynamical-diffraction *surrogate*.

Off-diagonal couplings are parameterized by extinction distances rather than
computed from tabulated electron scattering factors. The propagator is unitary
when absorptive potentials are absent. A full Bloch-wave / multislice channeling
engine can replace the resulting beam amplitudes without changing the MDFF API.
"""
from dataclasses import dataclass
import numpy as np
from .crystal import Crystal
from .geometry import Microscope, electron_wavelength_angstrom


@dataclass(frozen=True)
class BeamSet:
    hkl: tuple[tuple[int, int, int], ...] = ((0, 0, 0), (2, 0, 0), (-2, 0, 0))

    @classmethod
    def systematic_row(cls, order: int = 3,
                       fundamental_hkl: tuple[int,int,int] = (2,0,0)) -> "BeamSet":
        """Generate 0, +g, -g, +2g, -2g, ... (2*order+1 beams)."""
        if not isinstance(order, int) or order < 1:
            raise ValueError("systematic row order must be a positive integer")
        if len(fundamental_hkl) != 3 or fundamental_hkl == (0,0,0):
            raise ValueError("fundamental_hkl must be a nonzero Miller-index triple")
        indices = [(0,0,0)]
        for n in range(1, order+1):
            indices.extend([tuple(n*h for h in fundamental_hkl),
                            tuple(-n*h for h in fundamental_hkl)])
        return cls(tuple(indices))

    @classmethod
    def zolz(cls, crystal: Crystal, max_g_angstrom_inv: float,
             max_beams: int = 25) -> "BeamSet":
        """Select centered ZOLZ beams sorted by |g|, then hkl, in lab frame."""
        if not np.isfinite(max_g_angstrom_inv) or max_g_angstrom_inv <= 0 or max_beams < 2:
            raise ValueError("g cutoff must be positive and max_beams >= 2")
        # Bound integer indices conservatively using the smallest singular value.
        sigma_min = float(np.linalg.svd(crystal.reciprocal_angstrom_inv)[1][-1])
        hmax = int(np.ceil(max_g_angstrom_inv / sigma_min))
        candidates=[]
        for h in range(-hmax,hmax+1):
            for k in range(-hmax,hmax+1):
                hk0=(h,k,0)
                g=crystal.g_vector(hk0)
                length=float(np.linalg.norm(g))
                if 1e-10 < length <= max_g_angstrom_inv+1e-10 and crystal.is_allowed(hk0):
                    candidates.append((length,hk0))
        candidates.sort(key=lambda item:(round(item[0],12),item[1]))
        available={hkl for _,hkl in candidates}
        selected=[(0,0,0)]
        visited={(0,0,0)}
        for _,hkl in candidates:
            if hkl in visited:
                continue
            opposite=tuple(-h for h in hkl)
            if opposite not in available:
                continue
            if len(selected)+2 > max_beams:
                break
            selected.extend([hkl, opposite])
            visited.update([hkl, opposite])
        return cls(tuple(selected))

    def __post_init__(self) -> None:
        if len(self.hkl) < 2 or len(self.hkl) != len(set(self.hkl)):
            raise ValueError("at least two unique beams are required")
        if self.hkl[0] != (0, 0, 0):
            raise ValueError("first beam must be the transmitted beam (000)")


@dataclass(frozen=True)
class ElasticModel:
    crystal: Crystal
    microscope: Microscope
    beams: BeamSet
    xi_reference_nm: float = 55.0
    reference_hkl: tuple[int, int, int] = (2, 0, 0)
    coupling_power: float = 2.0

    def __post_init__(self) -> None:
        if self.xi_reference_nm <= 0 or self.coupling_power < 0:
            raise ValueError("extinction distance must be positive; coupling_power nonnegative")
        if not self.crystal.is_allowed(self.reference_hkl):
            raise ValueError("reference reflection must be structurally allowed")
        for hkl in self.beams.hkl:
            if not self.crystal.is_allowed(hkl):
                raise ValueError(f"reflection {hkl} is forbidden for this crystal")
            g = self.crystal.g_vector(hkl)
            if abs(g[2]) > 1e-9:
                raise ValueError("v0 supports ZOLZ beams with g_z=0 in the lab frame")

    @property
    def reciprocal_vectors_xy(self) -> np.ndarray:
        return np.stack([self.crystal.g_vector(h)[:2] for h in self.beams.hkl])

    def hamiltonian_nm_inv(self) -> np.ndarray:
        """H such that psi(z)=exp(i*H*z)psi(0), z in nm.

        Off-diagonal H_ij=pi/xi(dG); diagonal H_ii=2pi*s_g,
        with s_g approx (|kperp+g|^2-|kperp|^2)/(2*k) in cycles/angstrom.
        """
        g = self.reciprocal_vectors_xy
        kxy = self.microscope.incident_k_xy
        k0 = 1.0 / electron_wavelength_angstrom(self.microscope.acceleration_kv)
        s_nm = 10.0 * (np.sum((g + kxy)**2, axis=1) - np.dot(kxy, kxy)) / (2 * k0)
        n = len(g)
        H = np.diag(2 * np.pi * s_nm)
        ref_norm = np.linalg.norm(self.crystal.g_vector(self.reference_hkl))
        for i in range(n):
            for j in range(i + 1, n):
                delta = tuple(a - b for a, b in zip(self.beams.hkl[i], self.beams.hkl[j]))
                if self.crystal.is_allowed(delta):
                    factor = (ref_norm / np.linalg.norm(g[i] - g[j])) ** self.coupling_power
                    H[i, j] = H[j, i] = np.pi / self.xi_reference_nm * factor
        return H

    def amplitudes(self, depths_nm: np.ndarray) -> np.ndarray:
        """Amplitudes (n_depth,n_beams), normalized to one elastic electron."""
        z = np.atleast_1d(np.asarray(depths_nm, dtype=float))
        if not np.all(np.isfinite(z)) or np.any(z < 0):
            raise ValueError("depths must be finite and nonnegative")
        eigval, eigvec = np.linalg.eigh(self.hamiltonian_nm_inv())
        initial = np.zeros(len(self.beams.hkl), dtype=complex)
        initial[0] = 1.0
        coeff = eigvec.conj().T @ initial
        return (np.exp(1j * z[:, None] * eigval[None, :]) * coeff[None, :]) @ eigvec.T


def depth_coherence(model: ElasticModel, thickness_nm: float, steps: int = 64) -> np.ndarray:
    """Depth-averaged beam coherences: C_ij=<psi_i(z) conj(psi_j(z))>.

    This is the *incident* wave only. No outgoing-beam channeling, absorption,
    incoherent thermal diffuse scattering, or atomic-site-resolved MDFF.
    """
    if not np.isfinite(thickness_nm) or thickness_nm <= 0 or steps < 2:
        raise ValueError("thickness>0 and steps>=2 required")
    z = np.linspace(0.0, thickness_nm, steps)
    psi = model.amplitudes(z)
    pair = psi[:, :, None] * psi[:, None, :].conj()
    coherence = np.trapezoid(pair, x=z, axis=0) / thickness_nm if hasattr(np, "trapezoid") else np.trapz(pair, x=z, axis=0) / thickness_nm
    return np.asarray(coherence)
