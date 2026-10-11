"""Simple crystallography with 1/angstrom reciprocal-vector convention (no 2pi)."""
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class Crystal:
    lattice_angstrom: np.ndarray
    fractional_positions: np.ndarray
    species: tuple[str, ...]

    def __post_init__(self) -> None:
        cell = np.asarray(self.lattice_angstrom, dtype=float)
        frac = np.asarray(self.fractional_positions, dtype=float)
        if cell.shape != (3, 3) or abs(np.linalg.det(cell)) < 1e-10:
            raise ValueError("lattice_angstrom must be a nonsingular (3,3) row-vector cell")
        if frac.ndim != 2 or frac.shape[1] != 3 or len(frac) != len(self.species):
            raise ValueError("fractional positions must match species, shape (N,3)")
        object.__setattr__(self, "lattice_angstrom", cell.copy())
        object.__setattr__(self, "fractional_positions", frac.copy())

    @property
    def reciprocal_angstrom_inv(self) -> np.ndarray:
        """Reciprocal basis vectors as rows, a_i dot b_j = delta_ij."""
        return np.linalg.inv(self.lattice_angstrom).T

    def g_vector(self, hkl: tuple[int, int, int]) -> np.ndarray:
        return np.asarray(hkl, dtype=float) @ self.reciprocal_angstrom_inv

    def geometric_structure_factor(self, hkl: tuple[int, int, int]) -> complex:
        """Equal atomic form factors only. NOT an electron-scattering potential."""
        return complex(np.exp(2j * np.pi * (self.fractional_positions @ hkl)).sum())

    def is_allowed(self, hkl: tuple[int, int, int], tol: float = 1e-9) -> bool:
        return abs(self.geometric_structure_factor(hkl)) > tol


def fcc_nickel(a_angstrom: float = 3.524) -> Crystal:
    if a_angstrom <= 0:
        raise ValueError("lattice constant must be positive")
    return Crystal(
        lattice_angstrom=np.eye(3) * a_angstrom,
        fractional_positions=np.array([
            [0, 0, 0], [0, 0.5, 0.5],
            [0.5, 0, 0.5], [0.5, 0.5, 0],
        ], dtype=float),
        species=("Ni",) * 4,
    )
