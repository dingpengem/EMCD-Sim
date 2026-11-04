"""Shared 2p-to-3d angular/radial algebra; no element-specific parameters.

Moved verbatim from the historical Ni module, preserving operation order and
the d=<core|r|final> convention. This is not an arbitrary-transition model.
"""
from math import factorial
import numpy as np

# C(1, m_l; 1, q | 2, m_l + q), Condon--Shortley phases.
_SQRT2 = np.sqrt(2.0)
_CG_P_TO_D = {
    (-1, -1): 1.0, (-1, 0): 1.0/_SQRT2, (-1, 1): 1.0/np.sqrt(6.0),
    (0, -1): 1.0/_SQRT2, (0, 0): np.sqrt(2.0/3.0), (0, 1): 1.0/_SQRT2,
    (1, -1): 1.0/np.sqrt(6.0), (1, 0): 1.0/_SQRT2, (1, 1): 1.0,
}


def core_spinor_amplitude(two_j: int, two_mj: int, two_ms: int) -> float:
    """<l=1,m_l; s=1/2,m_s|j,m_j>, where m_l=(2mj-2ms)/2.

    Integers represent twice j/m_j/m_s, avoiding half-integer indexing.
    """
    if two_j not in (1, 3) or two_ms not in (-1, 1):
        raise ValueError("Core j must be 1/2 or 3/2, ms must be +/-1/2")
    if abs(two_mj) > two_j or (two_mj % 2) != (two_j % 2):
        raise ValueError("Invalid 2p core m_j")
    ml = (two_mj - two_ms)//2
    if abs(ml) > 1:
        return 0.0
    mj = two_mj / 2.0
    if two_j == 3:  # j = l + 1/2
        return float(np.sqrt((1.5 + mj) / 3.0) if two_ms == 1
                     else np.sqrt((1.5 - mj) / 3.0))
    # j = l - 1/2, CS phase convention
    return float(np.sqrt((1.5 - mj) / 3.0) if two_ms == 1
                 else -np.sqrt((1.5 + mj) / 3.0))

def dipole_2p_to_3d(two_j: int, two_mj: int, final_m: int,
                       two_ms: int, radial_angstrom: float = 1.0) -> np.ndarray:
    """Cartesian complex d=<core|r|final> for a pure atomic |3d,m,ms>.

    0 radial integral is a shared model parameter; for angular harmonics
    <2m_f|n_q|1m_i> = sqrt(2/5)*C(1 m_i, 1 q|2 m_f).
    Spherical n_{+1}=-(x+iy)/sqrt(2), n_{-1}=(x-iy)/sqrt(2).
    """
    if final_m not in range(-2, 3):
        raise ValueError("3d magnetic quantum number must be -2,...,+2")
    if not np.isfinite(radial_angstrom) or radial_angstrom <= 0:
        raise ValueError("radial_angstrom must be finite positive")
    core = core_spinor_amplitude(two_j, two_mj, two_ms)
    ml = (two_mj - two_ms)//2
    components = {}
    for q in (-1, 0, 1):
        components[q] = (radial_angstrom * core * np.sqrt(2.0/5.0)
                         * _CG_P_TO_D.get((ml, q), 0.0)
                         if final_m == ml + q else 0.0)
    # First calculate <final|r|core>; Hermitian conjugation gives <core|r|final>.
    x = (components[-1] - components[1]) / _SQRT2
    y = 1j * (components[-1] + components[1]) / _SQRT2
    z = components[0]
    return np.conjugate(np.asarray((x, y, z), dtype=complex))


BOHR_ANGSTROM = 0.529177210903


def hydrogenic_radial_dipole_angstrom(z2p: float, z3d: float) -> float:
    """Analytic <3d|r|2p> (Angstrom) for *normalized* screened H orbitals.

    R_21(r)=A_p r exp(-z2p r/(2a0)),
    R_32(r)=A_d r^2 exp(-z3d r/(3a0)),
    with A_p=(z2p/a0)^(5/2)/sqrt(24),
    A_d=(2*z3d/(3a0))^(7/2)/sqrt(720).
    The radial integral is integral(R_32 R_21 r^3 dr) = 6! A_p A_d/beta^7.
    Effective charges are *inputs*, never inferred as self-consistent Ni values.
    """
    if not (np.isfinite(z2p) and np.isfinite(z3d) and z2p > 0 and z3d > 0):
        raise ValueError("effective charges must be finite and positive")
    ap = z2p / BOHR_ANGSTROM
    ad = 2 * z3d / (3 * BOHR_ANGSTROM)
    beta = ap / 2 + ad / 2
    # Work in log-space to avoid spurious overflows for large charges.
    return float(np.exp(
        np.log(factorial(6)) + 2.5*np.log(ap) + 3.5*np.log(ad)
        - 0.5*np.log(24) - 0.5*np.log(720) - 7*np.log(beta)
    ))


def radial_dipole_from_table(
    radius_angstrom: np.ndarray, radial_2p: np.ndarray, radial_3d: np.ndarray,
) -> float:
    """Normalize supplied full radial R_nl(r) then evaluate <3d|r|2p>.

    Input must be full radial R(r), *not* reduced u(r)=r R(r), all sampled on
    the same strictly increasing radius grid in Angstrom. This can accept
    external atomic Hartree-Fock radial functions without running any DFT.
    """
    r = np.asarray(radius_angstrom, dtype=float)
    p = np.asarray(radial_2p, dtype=float)
    d = np.asarray(radial_3d, dtype=float)
    if r.ndim != 1 or len(r) < 8 or p.shape != r.shape or d.shape != r.shape:
        raise ValueError("radius, 2p and 3d radial arrays must have matching 1D length >= 8")
    if (not np.all(np.isfinite(r)) or not np.all(np.isfinite(p)) or
            not np.all(np.isfinite(d)) or r[0] < 0 or np.any(np.diff(r) <= 0)):
        raise ValueError("radius must be nonnegative ascending; all radial values finite")
    nporm = np.trapezoid((p*r)**2, r)
    ndorm = np.trapezoid((d*r)**2, r)
    if nporm <= 1e-30 or ndorm <= 1e-30:
        raise ValueError("radial functions must have nonzero normalization")
    integral = np.trapezoid(p*d*r**3, r) / np.sqrt(nporm*ndorm)
    if abs(integral) <= 1e-14:
        raise ValueError("radial dipole integral is effectively zero")
    return float(integral)


def cubic_orbital_coefficients() -> dict[str, np.ndarray]:
    """Orthonormal real cubic 3d orbitals in |l=2,m>, m=-2,...,+2.

    Overall orbital phases are arbitrary and cancel within the transition
    tensor; mutually coherent m components of a *single orbital* do not.
    """
    s = 2**-0.5
    vectors: dict[str, dict[int, complex]] = {
        "z2": {0: 1},
        "x2_y2": {-2: s, 2: s},
        "xy": {-2: 1j*s, 2: -1j*s},
        "xz": {-1: s, 1: -s},
        "yz": {-1: 1j*s, 1: 1j*s},
    }
    out = {}
    for label, values in vectors.items():
        coeff = np.zeros(5, complex)
        for m, value in values.items():
            coeff[m+2] = value
        out[label] = coeff
    return out


