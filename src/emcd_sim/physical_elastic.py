"""Finite-basis Bloch-wave propagation from *physical* crystal potentials.

Relativistic paraxial high-energy electron equation, lab z parallel to beam:
 d psi/dz = i H psi,
 H_gg [Å^-1] = -π λ (|k_perp+g|² - |k_perp|²),
 H_gh [Å^-1] = γ λ F_(g-h) / Ω,     (g != h).

F_G in Å is the non-relativistic Born electron structure factor, Ω in Å³;
γ = 1+eV/(m_e c²). The 10 factor converts Å^-1 to nm^-1.
Mean inner potential (G=0) is a common global phase, omitted.

Equivalent expression for the coupling is sigma * V_G, where
 sigma = γ m0 e λ/(2π ħ²) [radian/(V Å)]. This is a real, independent-atom
potential; elastic absorptive / thermal diffuse scattering is not included.
"""
from dataclasses import dataclass
import numpy as np
from .crystal import Crystal
from .elastic import BeamSet
from .geometry import Microscope, electron_wavelength_angstrom
from .scattering import IndependentAtomPotential


@dataclass(frozen=True)
class PhysicalElasticModel:
    crystal: Crystal
    microscope: Microscope
    beams: BeamSet
    potential: IndependentAtomPotential | None = None

    def __post_init__(self) -> None:
        if self.potential is None:
            object.__setattr__(self, "potential", IndependentAtomPotential(self.crystal))
        elif self.potential.crystal is not self.crystal:
            # Different copies of equal structures must be validated explicitly;
            # avoid silently propagating through a different lattice.
            if not (np.allclose(self.potential.crystal.lattice_angstrom, self.crystal.lattice_angstrom)
                    and np.allclose(self.potential.crystal.fractional_positions, self.crystal.fractional_positions)
                    and self.potential.crystal.species == self.crystal.species):
                raise ValueError("potential.crystal and model crystal differ")
        for hkl in self.beams.hkl:
            if not self.crystal.is_allowed(hkl):
                raise ValueError(f"forbidden FCC reflection in beam set: {hkl}")
            if abs(self.crystal.g_vector(hkl)[2]) > 1e-9:
                raise ValueError("PhysicalElasticModel currently requires oriented ZOLZ (g_z=0)")

    @property
    def reciprocal_vectors_xy(self) -> np.ndarray:
        return np.stack([self.crystal.g_vector(h)[:2] for h in self.beams.hkl])

    def hamiltonian_nm_inv(self) -> np.ndarray:
        lam = electron_wavelength_angstrom(self.microscope.acceleration_kv)
        gamma = 1.0 + 1000 * self.microscope.acceleration_kv / 510998.95
        g = self.reciprocal_vectors_xy
        kxy = self.microscope.incident_k_xy
        delta_g2 = np.sum((g+kxy)**2, axis=1) - np.dot(kxy, kxy)
        H = np.diag(-10.0 * np.pi * lam * delta_g2).astype(complex)
        for i in range(len(g)):
            for j in range(i+1, len(g)):
                hkl_delta = tuple(a-b for a,b in zip(self.beams.hkl[i], self.beams.hkl[j]))
                f = self.potential.structure_factor(hkl_delta)
                value = 10.0 * gamma * lam * f / self.potential.cell_volume_angstrom3
                H[i,j] = value
                H[j,i] = value.conjugate()
        return H

    def extinction_distance_nm(self, hkl: tuple[int, int, int]) -> float:
        """Two-beam xi_G = π / |H_0G| (nm), or infinite if F_G=0."""
        if hkl == (0,0,0):
            raise ValueError("000 has no extinction distance")
        lam = electron_wavelength_angstrom(self.microscope.acceleration_kv)
        gamma = 1.0 + 1000 * self.microscope.acceleration_kv / 510998.95
        f = abs(self.potential.structure_factor(hkl))
        return (np.pi * self.potential.cell_volume_angstrom3 / (10 * gamma * lam * f)
                if f > 1e-12 else float("inf"))

    def amplitudes(self, depths_nm: np.ndarray) -> np.ndarray:
        z = np.atleast_1d(np.asarray(depths_nm, dtype=float))
        if not np.all(np.isfinite(z)) or np.any(z < 0):
            raise ValueError("depths must be finite nonnegative nm")
        values, vectors = np.linalg.eigh(self.hamiltonian_nm_inv())
        initial = np.zeros(len(self.beams.hkl), dtype=complex)
        initial[0] = 1.0
        coeff = vectors.conj().T @ initial
        return (np.exp(1j * z[:,None] * values) * coeff[None,:]) @ vectors.T


def bragg_tilt_mrad(crystal: Crystal, hkl: tuple[int, int, int], acceleration_kv: float) -> float:
    """Paraxial Bragg angle (positive magnitude); s_g=0 for tilt=-theta_B along g."""
    return 500.0 * electron_wavelength_angstrom(acceleration_kv) * float(np.linalg.norm(crystal.g_vector(hkl)))

def excitation_errors_angstrom_inv(model) -> np.ndarray:
    """Signed s_g=(|k_perp+g|²-|k_perp|²)/(2k), in cycles/Å.

    The physical solver has diagonal entries H_gg=-20π s_g in nm^-1.
    """
    g = model.reciprocal_vectors_xy
    kxy = model.microscope.incident_k_xy
    lam = electron_wavelength_angstrom(model.microscope.acceleration_kv)
    return 0.5 * lam * (np.sum((g + kxy)**2, axis=1) - np.dot(kxy, kxy))
