"""Entrance-only EMCD from an externally sourced complex proper dipole MDFF.

Research-level coupling, NOT a calibrated cross section or validated Ni MDFF.
In the EMCD-Sim coordinate convention q_g = k_f - k_000 - g in cycles/angstrom.
Angular Q_g = 2*pi*q_g enters the dipole MDFF and Coulomb factors.
Each localized Ni core-loss site is summed incoherently, while incoming Bragg
channels at the same site interfere coherently. No outgoing channeling.
"""
from __future__ import annotations

import numpy as np

from .elastic import depth_coherence
from .geometry import characteristic_qz_angstrom_inv
from .mdff_tensor import DipoleTensor, cycles_to_angular_q
from .simulation import EMCDSimulation, SimulationResult


def fcc_site_phase_matrix(model: EMCDSimulation) -> np.ndarray:
    """Average exp(i(g_i-g_j).R) across equivalent localized Ni core sites.

    An average fixes a relative per-atom scale, not a calibrated physical
    cross-section or experimental dose.
    """
    crystal = model.elastic.crystal
    hkl = np.asarray(model.elastic.beams.hkl, dtype=int)
    positions = np.asarray(crystal.fractional_positions, dtype=float)
    if not len(positions) or not all(s == "Ni" for s in crystal.species):
        raise ValueError("Equivalent-site tensor backend currently requires only Ni atoms")
    phase = np.exp(2j * np.pi * (hkl[:, None, :] - hkl[None, :, :]) @ positions.T)
    return phase.mean(axis=-1)


def _tensor_angular_maps(model: EMCDSimulation, tensor_matrix: np.ndarray,
                         energy_ev: float, coherence: np.ndarray,
                         site_phase: np.ndarray, qx: np.ndarray,
                         qy: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Nonchiral and chiral additive maps at one energy (arbitrary units).

    T_even=Re(T), T_chiral=i*Im(T). Coulomb factors are included here but
    remain outside the proper dipole MDFF itself. Transition amplitudes use
    d=<core|r|final> and T=d outer conj(d).
    """
    qz = -characteristic_qz_angstrom_inv(
        float(energy_ev), model.elastic.microscope.acceleration_kv)
    g = model.elastic.reciprocal_vectors_xy
    q = np.stack((qx[..., None] - g[:, 0],
                  qy[..., None] - g[:, 1],
                  np.broadcast_to(np.asarray(qz), qx.shape)[..., None] * np.ones(len(g))),
                 axis=-1)
    angular_q = cycles_to_angular_q(q)
    q2 = np.sum(angular_q**2, axis=-1)
    denominator = q2[..., :, None] * q2[..., None, :]
    weighted_coherence = coherence * site_phase

    def project(part: np.ndarray) -> np.ndarray:
        mdff = np.einsum("...ia,ab,...jb->...ij", angular_q, part, angular_q, optimize=True)
        return np.real(np.einsum("ij,...ij->...", weighted_coherence,
                                  mdff / denominator, optimize=True))

    return project(tensor_matrix.real), project(1j * tensor_matrix.imag)


def run_tensor_single_channeling(
    model: EMCDSimulation,
    tensor: DipoleTensor,
    *,
    thickness_nm: float = 30.0,
    grid_size: int = 65,
    depth_steps: int = 64,
    map_halfwidth_q: float = 1.0,
    reference_energy_ev: float = 852.7,
) -> SimulationResult:
    """Contract the existing incoming Bloch-wave coherence with a dipole tensor.

    Relative intensity, no outgoing channeling or fitted magnetic scale.
    """
    if not np.isfinite(thickness_nm) or thickness_nm <= 0 or depth_steps < 2:
        raise ValueError("Thickness must be positive; depth steps must be >=2")
    coherence = depth_coherence(model.elastic, thickness_nm, depth_steps)
    return run_tensor_with_coherence(model, tensor, coherence,
        thickness_nm=thickness_nm, grid_size=grid_size,
        map_halfwidth_q=map_halfwidth_q, reference_energy_ev=reference_energy_ev)


def run_tensor_with_coherence(
    model: EMCDSimulation,
    tensor: DipoleTensor,
    coherence: np.ndarray,
    *,
    thickness_nm: float = 30.0,
    grid_size: int = 65,
    map_halfwidth_q: float = 1.0,
    reference_energy_ev: float = 852.7,
) -> SimulationResult:
    """Apply the unchanged tensor kernel to a supplied incoming coherence.

    The model carries ordered beam hkl/reciprocal geometry, Ni site phases and
    physical detector apertures. Grid coordinates and legacy hard-mask weights
    are identical to run_tensor_single_channeling. Trace need not equal one:
    FFT projection leakage must not be removed by renormalization.
    """
    if not np.isfinite(thickness_nm) or thickness_nm <= 0:
        raise ValueError("Thickness must be positive")
    if grid_size < 9 or not np.isfinite(map_halfwidth_q) or map_halfwidth_q <= 0:
        raise ValueError("grid >=9 and positive finite map halfwidth required")
    if not np.isfinite(reference_energy_ev) or reference_energy_ev <= 0:
        raise ValueError("Reference energy must be finite positive")
    q = np.linspace(-map_halfwidth_q, map_halfwidth_q, grid_size)
    qx, qy = np.meshgrid(q, q, indexing="xy")
    dq2 = float((q[1] - q[0])**2)
    coherence = np.asarray(coherence, dtype=complex)
    n = len(model.elastic.beams.hkl)
    if (coherence.shape != (n,n) or not np.all(np.isfinite(coherence))
            or not np.allclose(coherence, coherence.conj().T, rtol=1e-10, atol=1e-12)):
        raise ValueError("Coherence must be finite Hermitian and match the ordered beam basis")
    if np.linalg.eigvalsh(coherence).min() < -1e-10*max(1., np.linalg.norm(coherence)):
        raise ValueError("Coherence must be positive semidefinite")
    site_phase = fcc_site_phase_matrix(model)
    masks = {name: det.mask(qx, qy) for name, det in model.detectors.items()}
    if not all(mask.any() for mask in masks.values()):
        raise ValueError("At least one virtual aperture is outside the reciprocal map")
    spectra = {name: np.empty(len(tensor.energy_ev), dtype=float) for name in masks}
    selected_index = int(np.argmin(abs(tensor.energy_ev - reference_energy_ev)))
    nonmag_map, chiral_map = None, None
    for i, energy in enumerate(tensor.energy_ev):
        nonmag, chiral = _tensor_angular_maps(
            model, tensor.tensor_angstrom2_per_ev[i],
            float(energy), coherence, site_phase, qx, qy)
        total = thickness_nm * (nonmag + chiral)
        if total.min() < -1e-8 * max(1., total.max()):
            raise ValueError("Negative tensor-derived inelastic intensity: check conventions/phase")
        for name, mask in masks.items():
            spectra[name][i] = float(total[mask].sum() * dq2)
        if i == selected_index:
            nonmag_map, chiral_map = thickness_nm * nonmag, thickness_nm * chiral
    return SimulationResult(
        tensor.energy_ev, qx, qy, nonmag_map, chiral_map,
        spectra, masks, None, thickness_nm, 0.0, model.chiral_groups)
