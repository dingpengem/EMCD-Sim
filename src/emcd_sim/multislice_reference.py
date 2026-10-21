"""Independent *elastic* FFT split-step reference for oriented FCC Ni [001].

Real-space propagation is deliberately distinct from finite-basis Bloch-wave
matrix diagonalization. This is a projected IAM-potential, paraxial,
nonabsorbing **elastic** reference only; it does not model EMCD/MDFF or outgoing
channeling. Coordinate conventions match PhysicalElasticModel: g in cycles/Å,
z in nm, Fourier phase exp(+2 pi i g.r), and H_gg < 0 for off-axis beams.

For the [001] FCC Ni *projected potential*, the in-plane primitive repeat is
(a/2, a/2), so FFT harmonics (m,n) correspond to hkl=(2m,2n,0).
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from .crystal import fcc_nickel
from .geometry import electron_wavelength_angstrom
from .scattering import IndependentAtomPotential


@dataclass(frozen=True)
class ElasticFFTResult:
    thickness_nm: np.ndarray
    beam_hkl: np.ndarray           # (n_grid**2,3), FFT frequency ordering
    reciprocal_xy_inv_angstrom: np.ndarray
    intensity: np.ndarray          # (n_thickness,n_grid**2)
    norm_error: float
    grid_points: int
    slice_step_nm: float
    potential_cutoff_inv_angstrom: float
    amplitudes: np.ndarray | None = None  # optional (n_depth,n_grid**2), no renormalization
    systematic_row_hkl: tuple[int, int, int] | None = None

    def intensity_at(self, hkl: tuple[int, int, int]) -> np.ndarray:
        selection = np.all(self.beam_hkl == hkl, axis=1)
        if not np.any(selection):
            raise ValueError(f"Beam {hkl} outside FFT grid")
        return self.intensity[:, int(np.flatnonzero(selection)[0])]


def _projected_ni_potential(
    grid_points: int, acceleration_kv: float, b_factor_angstrom2: float,
    cutoff_inv_angstrom: float, projected_geometry=None, systematic_row_hkl=None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return real U(x,y) (nm^-1), hkl indices and reciprocal xy (cycles/Å).

    U_G = (10 gamma lambda / Omega) F_G, with U_000=0 (global phase).
    U(x,y) = sum_G U_G exp(+2pi i G.r). Transverse cell repeats by a/2.
    """
    if grid_points < 12 or grid_points % 2:
        raise ValueError("grid_points must be an even integer >= 12")
    if not np.isfinite(cutoff_inv_angstrom) or cutoff_inv_angstrom <= 0:
        raise ValueError("potential cutoff must be positive")
    if not np.isfinite(b_factor_angstrom2) or b_factor_angstrom2 < 0:
        raise ValueError("B factor must be finite and nonnegative")
    row = None if systematic_row_hkl is None else np.asarray(systematic_row_hkl, float)
    if row is not None and (row.shape != (3,) or not np.isfinite(row).all() or not np.any(row) or np.any(row != np.rint(row))):
        raise ValueError('Systematic row must be a nonzero three-integer hkl vector')
    crystal = fcc_nickel() if projected_geometry is None else projected_geometry.crystal
    potential = IndependentAtomPotential(crystal, debye_waller_b_angstrom2=b_factor_angstrom2)
    a = float(crystal.lattice_angstrom[0, 0]) if projected_geometry is None else projected_geometry.a_angstrom
    fft_indices = np.rint(np.fft.fftfreq(grid_points) * grid_points).astype(int)
    mx, my = np.meshgrid(fft_indices, fft_indices, indexing="ij")
    hkl = np.stack((2*mx, 2*my, np.zeros_like(mx)), axis=-1).reshape(-1, 3)
    g = np.stack((2*mx/a, 2*my/a), axis=-1).reshape(-1, 2)
    if projected_geometry is not None:
        hkl,g=projected_geometry.harmonics(grid_points,cutoff_inv_angstrom)
    # Do not let requested potential harmonics reach the Nyquist boundary.
    nyquist_g = (grid_points//2 - 1) * 2/a
    if projected_geometry is None and cutoff_inv_angstrom >= nyquist_g:
        raise ValueError("FFT grid too coarse for potential cutoff; increase grid_points")
    fourier = np.zeros((grid_points, grid_points), dtype=complex)
    lam = electron_wavelength_angstrom(acceleration_kv)
    gamma = 1 + 1000*acceleration_kv/510998.95
    prefactor = 10*gamma*lam/potential.cell_volume_angstrom3
    for i in range(grid_points):
        for j in range(grid_points):
            indices = tuple(int(x) for x in hkl[i*grid_points+j])
            if indices == (0, 0, 0) or np.linalg.norm(g[i*grid_points+j]) > cutoff_inv_angstrom:
                continue
            # Explicit publication-style systematic-row APPROXIMATION. This is
            # a Fourier projection of the IAM potential, not a physical FCC
            # extinction, an isolated two-beam model, or atomic-3D slicing.
            if row is not None and np.any(np.cross(indices, row)):
                continue
            if projected_geometry is not None and not crystal.is_allowed(indices):
                continue
            fourier[i, j] = prefactor * potential.structure_factor(indices)
    # numpy ifft2 uses +2*pi*i*m*x in real space; inverse transform needs N^2.
    projected = np.fft.ifft2(fourier)*grid_points**2
    if np.max(np.abs(projected.imag)) > 1e-9:
        raise ValueError("Potential violates real-space Hermitian Fourier symmetry")
    return projected.real, hkl, g


def fft_multislice_ni(
    thickness_nm: tuple[float, ...] | np.ndarray,
    *,
    acceleration_kv: float = 200.,
    tilt_mrad_xy: tuple[float, float] = (0., 0.),
    grid_points: int = 32,
    slice_step_nm: float = 0.1,
    potential_cutoff_inv_angstrom: float = 2.2,
    b_factor_angstrom2: float = 0.,
    return_amplitudes: bool = False,
    projected_geometry=None,
    systematic_row_hkl=None,
) -> ElasticFFTResult:
    """Elastic projected-potential FFT multislice on periodic FCC Ni [001].

    Kinetic and potential propagators are symmetrically split in real space:
    exp(i D dz/2) exp(i U_xy dz) exp(i D dz/2). The periodic entrance
    envelope is unity; tilt enters the transverse kinetic operator.
    Finite FFT grid and finite Fourier potential cutoff must be converged.
    return_amplitudes retains raw fft2(wave)/N^2 coefficients at the requested
    depths; the default historical intensity output and propagation are unchanged.
    systematic_row_hkl explicitly retains only potential Fourier components
    parallel to this row. Default None preserves the complete projected IAM.
    """
    depth = np.asarray(thickness_nm, dtype=float)
    if depth.ndim != 1 or not len(depth) or not np.all(np.isfinite(depth)) or np.any(depth < 0) or np.any(np.diff(depth) <= 0):
        raise ValueError("thickness must be a finite sorted increasing 1D array of nonnegative nm")
    if not np.isfinite(slice_step_nm) or slice_step_nm <= 0:
        raise ValueError("slice_step_nm must be positive finite")
    if not np.isfinite(acceleration_kv) or acceleration_kv <= 0:
        raise ValueError("acceleration_kv must be positive")
    tilt = np.asarray(tilt_mrad_xy, dtype=float)
    if tilt.shape != (2,) or not np.all(np.isfinite(tilt)):
        raise ValueError("tilt_mrad_xy must contain two finite numbers")

    u, hkl, g = _projected_ni_potential(grid_points, acceleration_kv, b_factor_angstrom2, potential_cutoff_inv_angstrom,projected_geometry,systematic_row_hkl)
    lam = electron_wavelength_angstrom(acceleration_kv)
    ki = tilt*1e-3/lam
    d = (-10*np.pi*lam*(np.sum((g+ki)**2, axis=1)-float(ki @ ki))).reshape(grid_points, grid_points)

    wave = np.ones((grid_points, grid_points), dtype=complex)
    n2 = grid_points**2
    values = np.empty((len(depth), n2), dtype=float)
    amplitudes = np.empty((len(depth), n2), dtype=complex) if return_amplitudes else None
    current_z = 0.
    for index, target in enumerate(depth):
        delta = float(target-current_z)
        n_steps = int(np.ceil(delta/slice_step_nm)) if delta > 0 else 0
        step = delta/n_steps if n_steps else 0.
        if n_steps:
            kinetic = np.exp(0.5j*step*d)
            transmission = np.exp(1j*step*u)
            for _ in range(n_steps):
                q = np.fft.fft2(wave)/n2
                wave = np.fft.ifft2(q*kinetic)*n2
                wave *= transmission
                q = np.fft.fft2(wave)/n2
                wave = np.fft.ifft2(q*kinetic)*n2
        coeff = (np.fft.fft2(wave)/n2).reshape(-1)
        values[index] = np.abs(coeff)**2
        if amplitudes is not None:
            amplitudes[index] = coeff
        current_z = float(target)
    norm_error = float(np.max(np.abs(values.sum(axis=1)-1)))
    return ElasticFFTResult(depth, hkl, g, values, norm_error,
                            grid_points, slice_step_nm, potential_cutoff_inv_angstrom, amplitudes,
                            None if systematic_row_hkl is None else tuple(int(v) for v in systematic_row_hkl))


def project_fft_amplitudes(fft, beam_hkl):
    """Exact integer hkl lookup; no sign reversal, conjugation or rescaling."""
    if fft.amplitudes is None:
        raise ValueError('Request return_amplitudes=True from fft_multislice_ni')
    lookup = {tuple(h):i for i,h in enumerate(fft.beam_hkl)}
    try:
        indices = np.asarray([lookup[tuple(h)] for h in beam_hkl],dtype=int)
    except KeyError as exc:
        raise ValueError(f'Common beam outside FFT grid: {exc.args[0]}') from exc
    if len(set(indices)) != len(indices):
        raise ValueError('Common hkl basis must be unique')
    retained = np.zeros(len(fft.beam_hkl),dtype=bool)
    retained[indices] = True
    outside = fft.intensity[:,~retained].sum(axis=1)
    return fft.amplitudes[:,indices].copy(), outside

def coherence_from_amplitudes(depth_nm, amplitudes):
    """Same trapezoidal quadrature and C_gh=psi_g*conj(psi_h) as depth_coherence."""
    z, psi = np.asarray(depth_nm,float), np.asarray(amplitudes,complex)
    if (z.ndim!=1 or len(z)<2 or not np.isfinite(z).all() or z[0]!=0
            or np.any(np.diff(z)<=0) or psi.ndim!=2 or psi.shape[0]!=len(z)
            or not np.isfinite(psi).all()):
        raise ValueError('Require finite amplitudes on increasing depths from zero to t>0')
    pair = psi[:,:,None]*psi[:,None,:].conj()
    integral = np.trapezoid(pair,x=z,axis=0) if hasattr(np,'trapezoid') else np.trapz(pair,x=z,axis=0)
    return integral/z[-1]

def complex_wave_diagnostics(bloch, multislice):
    """Per-depth global-phase alignment for diagnostics only; no change to C."""
    overlap = np.sum(bloch.conj()*multislice,axis=1)
    valid = abs(overlap)>1e-14
    phase = np.where(valid,np.angle(overlap),np.nan)
    aligned = multislice*np.exp(-1j*phase[:,None])
    return dict(global_phase_ms_vs_bw=phase, phase_valid=valid,
        amplitude_max_abs_raw=np.max(abs(multislice-bloch),axis=1),
        amplitude_max_abs_aligned=np.max(abs(aligned-bloch),axis=1))
