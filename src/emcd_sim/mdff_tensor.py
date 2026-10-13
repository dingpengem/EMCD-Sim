"""Complex dipole MDFF from supplied *transition amplitudes*, not DOS.

No Ni electronic-structure wavefunctions or DFT calculations are supplied by
this module. This is an independently implemented P2 mathematical kernel.

Convention: d_a = <i|r_a|f> in Angstrom, Q in *angular* rad/Angstrom,
T_ab(E) = sum_n w_n d_{n,a} conj(d_{n,b}) G_sigma(E-E_n),
S_dip(Q,Q',E) = Q_a T_ab(E) Q'_b.
The MDFF is separate from Coulomb 1/(Q^2 Q'^2) scattering factors.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


def _finite_array(a: np.ndarray) -> bool:
    return bool(np.all(np.isfinite(a)))


@dataclass(frozen=True)
class TransitionDataset:
    """Spin/SOC-resolved transitions already computed by an external provider.

    weights include k-point weights, occupied initial and unoccupied final
    factors and any statistical factors. States that must interfere are encoded
    in their *complex* Cartesian dipoles before the transition summation.

    This class does not automatically account for site structure phases,
    wavefunction gauge conversions or core-to-band normalization.
    """

    energy_ev: np.ndarray                   # (n_transitions,), positive energy loss
    dipoles_angstrom: np.ndarray            # (n_transitions, 3), complex
    weights: np.ndarray                     # (n_transitions,), nonnegative
    edge: np.ndarray                        # (n_transitions,), e.g. 'L3', 'L2'
    site: np.ndarray                        # (n_transitions,), local atom/site label
    source: str                             # required nonempty provenance

    def __post_init__(self) -> None:
        e = np.asarray(self.energy_ev, dtype=float)
        d = np.asarray(self.dipoles_angstrom, dtype=complex)
        w = np.asarray(self.weights, dtype=float)
        edge = np.asarray(self.edge)
        site = np.asarray(self.site)
        n = len(e) if e.ndim == 1 else 0
        if not n or d.shape != (n, 3) or w.shape != (n,) or edge.shape != (n,) or site.shape != (n,):
            raise ValueError("Transition arrays require shapes (n,), (n,3), (n,), (n,), (n,)")
        if not (_finite_array(e) and _finite_array(d) and _finite_array(w)) or np.any(e <= 0) or np.any(w < 0):
            raise ValueError("Transition energies must be finite positive, dipoles finite, weights nonnegative")
        if edge.dtype.kind not in "US" or site.dtype.kind not in "US":
            raise ValueError("edge and site labels must be plain Unicode strings, not objects")
        if np.any(np.char.str_len(edge.astype(str)) == 0) or np.any(np.char.str_len(site.astype(str)) == 0):
            raise ValueError("edge and site labels must be nonempty")
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("Transition dataset requires nonempty source/provenance")
        for key, arr in (("energy_ev", e), ("dipoles_angstrom", d),
                         ("weights", w), ("edge", edge), ("site", site)):
            copied = np.array(arr, copy=True)
            copied.setflags(write=False)
            object.__setattr__(self, key, copied)

    def save_npz(self, path: Path | str) -> None:
        """Portable NumPy representation; no pickle or code execution."""
        np.savez_compressed(Path(path), energy_ev=self.energy_ev,
                            dipoles_angstrom=self.dipoles_angstrom,
                            weights=self.weights, edge=self.edge, site=self.site,
                            source=np.asarray(self.source),
                            convention=np.asarray("d=<i|r|f>; angular Q=2*pi*g; length=angstrom"))

    @classmethod
    def load_npz(cls, path: Path | str) -> TransitionDataset:
        with np.load(path, allow_pickle=False) as f:
            required = {"energy_ev", "dipoles_angstrom", "weights", "edge", "site", "source", "convention"}
            if not required <= set(f.files):
                raise ValueError("Transition dataset is missing schema fields")
            if str(f["convention"].item()) != "d=<i|r|f>; angular Q=2*pi*g; length=angstrom":
                raise ValueError("Unsupported dipole phase/units convention")
            return cls(f["energy_ev"], f["dipoles_angstrom"], f["weights"],
                       f["edge"], f["site"], str(f["source"].item()))


def gaussian_broadening_ev(energy_ev: np.ndarray, center_ev: np.ndarray, sigma_ev: float) -> np.ndarray:
    """Unit-area normal/Gaussian line shape, in inverse eV."""
    if not np.isfinite(sigma_ev) or sigma_ev <= 0:
        raise ValueError("sigma_ev must be finite and >0")
    return np.exp(-0.5*((energy_ev[..., None]-center_ev)/sigma_ev)**2) / (sigma_ev*np.sqrt(2*np.pi))


@dataclass(frozen=True)
class DipoleTensor:
    energy_ev: np.ndarray                 # (n_energy,)
    tensor_angstrom2_per_ev: np.ndarray   # (n_energy,3,3); spectral dipole tensor
    source: str

    def __post_init__(self) -> None:
        e = np.asarray(self.energy_ev, dtype=float)
        t = np.asarray(self.tensor_angstrom2_per_ev, dtype=complex)
        if e.ndim != 1 or not len(e) or t.shape != (len(e), 3, 3):
            raise ValueError("Expected energy (n,) and tensor (n,3,3)")
        if not _finite_array(e) or not _finite_array(t) or np.any(e <= 0) or np.any(np.diff(e) <= 0):
            raise ValueError("Energy grid must be finite, positive, ascending; tensor finite")
        if not np.allclose(t, t.swapaxes(-1, -2).conj(), rtol=1e-10, atol=1e-12):
            raise ValueError("Dipole spectral tensor must be Hermitian")
        for name, arr in (("energy_ev", e), ("tensor_angstrom2_per_ev", t)):
            out = np.array(arr, copy=True)
            out.setflags(write=False)
            object.__setattr__(self, name, out)

    def mdff(self, q_angstrom_inv: np.ndarray, qp_angstrom_inv: np.ndarray) -> np.ndarray:
        """Evaluate *proper* S_dip at every energy; Q/Q' angular rad/Angstrom.

        q and qp broadcast in their leading dimensions; output shape is
        (n_energy, *broadcast_q_shape). No fast-electron Coulomb denominators.
        """
        q = np.asarray(q_angstrom_inv, dtype=float)
        qp = np.asarray(qp_angstrom_inv, dtype=float)
        if q.shape[-1:] != (3,) or qp.shape[-1:] != (3,) or not _finite_array(q) or not _finite_array(qp):
            raise ValueError("q and q_prime must be finite (...,3) angular wavevectors")
        return np.einsum("...a,eab,...b->e...", q, self.tensor_angstrom2_per_ev, qp,
                         optimize=True)

    def save_npz(self, path: Path | str) -> None:
        np.savez_compressed(path, energy_ev=self.energy_ev,
                            tensor_angstrom2_per_ev=self.tensor_angstrom2_per_ev,
                            source=np.asarray(self.source),
                            angular_q_required=np.asarray(True))


def dipole_tensor_from_transitions(transitions: TransitionDataset,
                                   energy_ev: np.ndarray,
                                   sigma_ev: float,
                                   *, edge: str | None = None,
                                   site: str | None = None) -> DipoleTensor:
    """Spectral Gram tensor: sum w * (d outer conj(d)) * gaussian(E-Efi).

    Terms are incoherently summed *between transitions* after complex
    amplitude products are formed. The result is Hermitian and PSD for
    nonnegative weights, including SOC-entangled/chiral dipole channels.
    """
    e = np.asarray(energy_ev, dtype=float)
    if e.ndim != 1 or len(e) < 2 or not _finite_array(e) or np.any(e <= 0) or np.any(np.diff(e) <= 0):
        raise ValueError("Energy grid must be finite, positive, strictly increasing")
    mask = np.ones(len(transitions.energy_ev), dtype=bool)
    if edge is not None:
        mask &= transitions.edge == edge
    if site is not None:
        mask &= transitions.site == site
    if not np.any(mask):
        raise ValueError("No transitions found for requested edge/site")
    widths = gaussian_broadening_ev(e, transitions.energy_ev[mask], sigma_ev)
    weighted = widths * transitions.weights[mask][None, :]
    d = transitions.dipoles_angstrom[mask]
    tensor = np.einsum("en,na,nb->eab", weighted, d, d.conj(), optimize=True)
    return DipoleTensor(e, tensor, transitions.source)


def cycles_to_angular_q(q_cycles_per_angstrom: np.ndarray) -> np.ndarray:
    """Convert reciprocal crystallographic cycles/Angstrom to rad/Angstrom."""
    return 2*np.pi*np.asarray(q_cycles_per_angstrom, dtype=float)
