"""Finite diffraction beam support and entrance-wave depth quadrature."""
from dataclasses import dataclass
import numpy as np
from .crystal import Crystal


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


def depth_coherence(model, thickness_nm: float, steps: int = 64) -> np.ndarray:
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
