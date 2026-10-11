"""Entrance-channeling dipole-MDFF integration over reciprocal-space apertures."""
from dataclasses import dataclass
from typing import Mapping
import numpy as np
from .elastic import ElasticModel, depth_coherence
from .physical_elastic import PhysicalElasticModel
from .geometry import VirtualDetector, characteristic_qz_angstrom_inv
from .inelastic import DipoleMDFF
from .voltage import MagnetizationLaw


@dataclass(frozen=True)
class SimulationResult:
    energy_ev: np.ndarray
    qx_angstrom_inv: np.ndarray
    qy_angstrom_inv: np.ndarray
    nonmag_map_at_l3: np.ndarray
    magnetic_map_at_l3: np.ndarray
    detector_spectra: Mapping[str, np.ndarray]
    detector_masks: Mapping[str, np.ndarray]
    moment_muB: float
    thickness_nm: float
    voltage_v: float

    def difference(self, positive: str = "A", negative: str = "B") -> np.ndarray:
        return self.detector_spectra[positive] - self.detector_spectra[negative]

    def asymmetry(self, positive: str = "A", negative: str = "B") -> np.ndarray:
        a, b = self.detector_spectra[positive], self.detector_spectra[negative]
        return np.divide(a-b, a+b, out=np.zeros_like(a), where=(a+b)!=0)

    def at_edge(self, edge_ev: float = 852.7) -> tuple[float, float, float]:
        i = int(np.argmin(abs(self.energy_ev-edge_ev)))
        return float(self.energy_ev[i]), float(self.difference()[i]), float(self.asymmetry()[i])


@dataclass(frozen=True)
class EMCDSimulation:
    elastic: ElasticModel | PhysicalElasticModel
    mdff: DipoleMDFF
    magnetization: MagnetizationLaw
    detectors: Mapping[str, VirtualDetector]
    magnetization_direction_xyz: tuple[float, float, float] = (0.0, 0.0, 1.0)

    def __post_init__(self) -> None:
        if len(self.detectors) < 2:
            raise ValueError("At least two detectors are required")
        direction = np.asarray(self.magnetization_direction_xyz, dtype=float)
        if direction.shape != (3,) or not np.all(np.isfinite(direction)) or np.linalg.norm(direction) < 1e-12:
            raise ValueError("magnetization direction must be a nonzero 3-vector")

    def angular_components(self, energy_ev: float, coherence: np.ndarray,
                           qx: np.ndarray, qy: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Returns geometry kernels K_N, K_M without spectral prefactors.

        Dipole tensor contraction uses incident-beam coherences C_ij = psi_i psi_j*;
        intensity contribution is Re[C_ij * S_ij]. Sign depends on q convention.
        """
        qz = -characteristic_qz_angstrom_inv(energy_ev, self.elastic.microscope.acceleration_kv)
        g = self.elastic.reciprocal_vectors_xy
        incident_kxy = self.elastic.microscope.incident_k_xy
        # Q is absolute outgoing transverse k, referenced to incident optic axis.
        # q_j = k_f - k_i - g_j, with inelastic |k_f| effects retained only in qz.
        q = np.stack((
            qx[..., None] - incident_kxy[0] - g[:, 0],
            qy[..., None] - incident_kxy[1] - g[:, 1],
            np.broadcast_to(np.asarray(qz), qx.shape)[..., None] * np.ones(len(g)),
        ), axis=-1)
        norm2 = np.sum(q*q, axis=-1)
        # The qz component makes the denominator strictly positive for core-loss E>0.
        denom = norm2[..., :, None] * norm2[..., None, :]
        dot = np.einsum("...ic,...jc->...ij", q, q)
        cross = np.cross(q[..., :, None, :], q[..., None, :, :])
        magnet = np.asarray(self.magnetization_direction_xyz, dtype=float)
        magnet /= np.linalg.norm(magnet)
        axial = np.einsum("...ijc,c->...ij", cross, magnet)
        nonmag = np.real(np.einsum("ij,...ij->...", coherence, dot / denom))
        magnetic = np.real(np.einsum("ij,...ij->...", coherence * 1j, axial / denom))
        return nonmag, magnetic

    def run(self, energy_ev: np.ndarray, thickness_nm: float = 30.0,
            voltage_v: float = 0.0, map_halfwidth_q: float = 1.0,
            grid_size: int = 65, depth_steps: int = 64) -> SimulationResult:
        energies = np.asarray(energy_ev, dtype=float)
        if energies.ndim != 1 or len(energies) < 2 or not np.all(np.isfinite(energies)) or np.any(energies <= 0):
            raise ValueError("energy_ev must be a finite 1D positive array")
        if not np.all(np.diff(energies)>0):
            raise ValueError("energy_ev must be strictly ascending")
        if grid_size < 9 or map_halfwidth_q <= 0:
            raise ValueError("grid_size>=9 and map_halfwidth_q>0 required")
        moment = float(self.magnetization(voltage_v))
        if not np.isfinite(moment):
            raise ValueError("moment must be finite")
        energy_nonmag, energy_mag = self.mdff.terms(energies, moment)
        q = np.linspace(-map_halfwidth_q, map_halfwidth_q, grid_size)
        qx, qy = np.meshgrid(q, q, indexing="xy")
        dq2 = float((q[1]-q[0])**2)
        coherence = depth_coherence(self.elastic, thickness_nm, depth_steps)
        masks = {name: det.mask(qx,qy) for name,det in self.detectors.items()}
        if not all(np.any(mask) for mask in masks.values()):
            raise ValueError("A detector is outside the map or too small for the chosen grid")
        spectra = {name: np.empty(len(energies)) for name in masks}
        nonmag_l3 = None
        magnetic_l3 = None
        l3_index = int(np.argmin(abs(energies-self.mdff.reference_energy_ev)))
        for i, e in enumerate(energies):
            n, m = self.angular_components(float(e), coherence, qx, qy)
            signal = thickness_nm * (n * energy_nonmag[i] + m * energy_mag[i])
            # Reject rather than silently clip a mathematically invalid approximation.
            if np.min(signal) < -1e-8 * max(1.0, np.max(signal)):
                raise ValueError("Computed negative cross section: inspect MDFF convention/parameters")
            for name, mask in masks.items():
                spectra[name][i] = float(signal[mask].sum() * dq2)
            if i == l3_index:
                nonmag_l3 = thickness_nm * n * energy_nonmag[i]
                magnetic_l3 = thickness_nm * m * energy_mag[i]
        return SimulationResult(energies, qx, qy, nonmag_l3, magnetic_l3,
                                spectra, masks, moment, thickness_nm, voltage_v)
