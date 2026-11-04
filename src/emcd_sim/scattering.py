"""Neutral-atom elastic electron scattering factors and crystal structure factors.

Crystallographic reciprocal magnitude ``g`` is |h b1 + k b2 + l b3| in Å⁻¹, with |g|=1/d.
The tabulated Lobato--Van Dyck electron form factors are *non-relativistic*
Born scattering amplitudes in Å. The microscope gamma factor is applied when
building the relativistic elastic propagation matrix, not inside f(g).

The unversioned constructor retains Ni compatibility. ``from_provider`` uses
the separately bundled neutral Z=1..118 Dirac-Pade data by default.
"""
from dataclasses import dataclass, field
from typing import Callable, Mapping
import numpy as np
from .crystal import Crystal

# I. Lobato and D. Van Dyck, Acta Cryst. A70, 636-649 (2014), Table 1, Z=28.
# f(g) = sum_i a_i (2 + b_i*g^2)/(1+b_i*g^2)^2, g in Å^-1, f in Å.
_NI_A = np.array([2.969080787252864, -75.74770691290402,
                  76.03982876253073, 0.02101621136929670,
                  0.0002311517511351530], dtype=float)
_NI_B = np.array([5.041809491093800, 1.182755079216293,
                  1.162165458466299, 0.03374790878830353,
                  0.002786808620707405], dtype=float)


def nickel_lobato_factor(g_angstrom_inv: float | np.ndarray) -> float | np.ndarray:
    """Neutral Ni electron elastic scattering factor, f(g) in Å.

    Parameters from Lobato & Van Dyck (2014), Z=28; not an adjustable
    extinction-distance approximation. This is an independent-atom potential
    (not a self-consistent, spin-polarized Ni crystal potential).
    """
    g = np.asarray(g_angstrom_inv, dtype=float)
    if not np.all(np.isfinite(g)) or np.any(g < 0):
        raise ValueError("Crystallographic g=1/d must be finite and nonnegative (Å⁻¹)")
    t = g[..., None] ** 2 * _NI_B
    value = np.sum(_NI_A * (2.0 + t) / (1.0 + t) ** 2, axis=-1)
    return float(value) if g.ndim == 0 else value


@dataclass(frozen=True)
class IndependentAtomPotential:
    """Real, elastic Fourier coefficients for a periodic neutral-atom crystal.

    ``structure_factor`` F_G = sum_j occupancy_j f_species_j(|G|)
      exp(-2πi hkl·fractional_position_j) exp(-B_j |G|² / 4), in Å.

    ``fourier_potential_volts`` V_G = (2π ħ² / m0 e) F_G / cell_volume;
    mean-inner-potential V_000 contributes only a global phase and is removed
    in the propagation matrix. No absorptive potential or charge transfer.
    """
    crystal: Crystal
    debye_waller_b_angstrom2: float | tuple[float, ...] = 0.0
    occupancies: float | tuple[float, ...] = 1.0
    atomic_factors: Mapping[str, Callable[[float], float]] = field(
        default_factory=lambda: {"Ni": nickel_lobato_factor}
    )

    def __post_init__(self) -> None:
        count = len(self.crystal.species)
        for fieldname, default, maximum in (
            ("debye_waller_b_angstrom2", 0., None),
            ("occupancies", 1., 1.),
        ):
            values = np.asarray(getattr(self, fieldname), dtype=float)
            if values.ndim == 0:
                values = np.full(count, float(values))
            if values.shape != (count,) or not np.all(np.isfinite(values)):
                raise ValueError(f"{fieldname} must be finite scalar or one value per atom")
            if np.any(values < 0) or (maximum is not None and np.any(values > maximum)):
                raise ValueError(f"{fieldname} must be within physical bounds")
            object.__setattr__(self, fieldname, tuple(float(v) for v in values))
        missing = set(self.crystal.species) - set(self.atomic_factors)
        if missing:
            raise ValueError(f"Missing electron scattering factors for {sorted(missing)}")

    @classmethod
    def from_provider(cls,crystal,provider='adaptive-dirac-pade-2026',**kwargs):
        """Explicit modern provider factory; the unversioned constructor stays legacy-compatible."""
        from .elastic_providers import factors_for_provider
        return cls(crystal,atomic_factors=factors_for_provider(crystal.species,provider),**kwargs)

    @property
    def cell_volume_angstrom3(self) -> float:
        return float(abs(np.linalg.det(self.crystal.lattice_angstrom)))

    def structure_factor(self, hkl: tuple[int, int, int]) -> complex:
        if len(hkl) != 3 or any(int(h) != h for h in hkl):
            raise ValueError("hkl must consist of three integer Miller indices")
        g = float(np.linalg.norm(self.crystal.g_vector(hkl)))
        phase = np.exp(-2j * np.pi * (self.crystal.fractional_positions @ np.asarray(hkl)))
        f = np.array([self.atomic_factors[s](g) for s in self.crystal.species], dtype=float)
        if f.shape != (len(self.crystal.species),) or not np.all(np.isfinite(f)):
            raise ValueError("Atomic factors must return finite scalar scattering amplitudes in angstrom")
        dw = np.exp(-np.array(self.debye_waller_b_angstrom2) * (g ** 2) / 4)
        return complex(np.dot(phase, f * dw * np.array(self.occupancies)))

    def fourier_potential_volts(self, hkl: tuple[int, int, int]) -> complex:
        """Physical independent-atom crystal potential V_G in volts.

        ħ²/(m_e e) = 7.619964... V Å², using the non-relativistic rest mass;
        relativistic interaction with this potential occurs in the propagator.
        """
        HBAR2_PER_M0_E_V_ANGSTROM2 = 7.619964231073853
        return (2 * np.pi * HBAR2_PER_M0_E_V_ANGSTROM2
                * self.structure_factor(hkl) / self.cell_volume_angstrom3)


@dataclass(frozen=True)
class FourierCutoffPotential:
    """Explicit finite Fourier-harmonic reference potential, not full IAM Ni."""
    original: IndependentAtomPotential
    cutoff_inv_angstrom: float

    @property
    def crystal(self):
        return self.original.crystal

    @property
    def cell_volume_angstrom3(self):
        return self.original.cell_volume_angstrom3

    def structure_factor(self, hkl):
        return (self.original.structure_factor(hkl) if
                np.linalg.norm(self.crystal.g_vector(hkl)) <= self.cutoff_inv_angstrom + 1e-10
                else 0j)


def elastic_reflection_allowed(crystal: Crystal, hkl: tuple[int, int, int],
                               potential=None, tol: float = 1e-9) -> bool:
    """Test actual IAM extinction when an explicit elastic potential is supplied.

    The historical equal-atom test remains the default for legacy Ni callers.
    Multi-species/site-dependent callers must supply their potential. A finite
    potential cutoff is a numerical approximation, not a structural extinction;
    unwrap it before choosing beams, including beams reached indirectly.
    """
    if not np.isfinite(tol) or tol < 0:
        raise ValueError("Reflection tolerance must be finite and nonnegative")
    if potential is None:
        return crystal.is_allowed(hkl, tol=tol)
    while isinstance(potential, FourierCutoffPotential):
        potential = potential.original
    source = potential.crystal
    if (source.species != crystal.species
            or source.fractional_positions.shape != crystal.fractional_positions.shape
            or not np.allclose(source.lattice_angstrom, crystal.lattice_angstrom, rtol=0, atol=1e-12)
            or not np.allclose(source.fractional_positions, crystal.fractional_positions, rtol=0, atol=1e-12)):
        raise ValueError("Beam selection potential must describe the same crystal and site ordering")
    coefficient = potential.structure_factor(hkl)
    if not np.isfinite(coefficient):
        raise ValueError("Elastic structure factor must be finite")
    return abs(coefficient) > tol
