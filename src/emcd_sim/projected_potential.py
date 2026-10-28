"""Structure-derived projected IAM Fourier phases for the existing FFT engine.

U is sigma*V_avg in radians/nm. Multiplication by dz belongs to the split
step. It is not an atomic slice-integrated potential and contains no atomic-z
event model. The source crystal's 3D volume fixes normalization; a reduced
transverse cell must not introduce another density or area factor.
"""
from dataclasses import dataclass
import numpy as np
from .cancellation import check_cancelled
from .geometry import electron_wavelength_angstrom
from .projected_geometry import ProjectedGeometry,fft_shape
from .crystallography import integer_triplet,row_coordinates
from .scattering import IndependentAtomPotential
from .gui.memory_budget import reserve_memory


def potential_site_labels(potential):
    """Translations must preserve actual per-site scattering parameters."""
    source=potential
    for _ in range(16):
        if not hasattr(source,'original'):break
        source=source.original
    else:raise ValueError('Potential wrapper nesting exceeds the supported bound')
    if isinstance(source,IndependentAtomPotential):
        return tuple(zip(source.crystal.species,source.occupancies,source.debye_waller_b_angstrom2))
    # An unknown provider cannot assert chemical translations preserve its V_G.
    return tuple(range(len(potential.crystal.species)))


def interaction_parameter_volt_nm(kv:float) -> float:
    """Same gamma/lambda and rest-mass convention as existing IAM/BW phases."""
    return 10*(1+1000*kv/510998.95)*electron_wavelength_angstrom(kv)/(2*np.pi*7.619964231073853)


@dataclass(frozen=True)
class ProjectedPotential:
    geometry:ProjectedGeometry
    phase_nm_inv:np.ndarray
    phase_fourier_nm_inv:np.ndarray
    hkl:np.ndarray
    reciprocal_xy:np.ndarray
    acceleration_kv:float
    cutoff_inv_angstrom:float
    mean_phase_removed:bool=True


def prepare_projected_potential(geometry:ProjectedGeometry,potential,acceleration_kv:float,
        grid_points,cutoff:float,*,support_cutoff=None,systematic_row_hkl=None,
        memory_budget_mib=2048,cancelled=None) -> ProjectedPotential:
    check_cancelled(cancelled);shape=fft_shape(grid_points)
    if not np.isfinite(cutoff) or cutoff<=0:raise ValueError('Positive finite potential cutoff required')
    if not np.isfinite(acceleration_kv) or acceleration_kv<=0:raise ValueError('Positive finite accelerating voltage required')
    if support_cutoff is not None and (not np.isfinite(support_cutoff) or support_cutoff<=0):raise ValueError('Positive finite beam-support cutoff required')
    wavelength=electron_wavelength_angstrom(acceleration_kv)
    if hasattr(potential,'cutoff_inv_angstrom') and cutoff>potential.cutoff_inv_angstrom+1e-10:
        raise ValueError('Requested Fourier cutoff exceeds the supplied potential bandwidth; rebuild the potential explicitly')
    a=geometry.crystal;b=potential.crystal
    if (a.species!=b.species or a.fractional_positions.shape!=b.fractional_positions.shape
        or not np.allclose(a.lattice_angstrom,b.lattice_angstrom,rtol=0,atol=1e-12)
        or not np.allclose(a.fractional_positions,b.fractional_positions,rtol=0,atol=1e-12)):
        raise ValueError('Projected geometry and potential must describe the same oriented crystal and site ordering')
    checked=ProjectedGeometry.from_oriented(b,geometry.orientation.zone,geometry.target,
        labels=potential_site_labels(potential),generators=geometry.generators)
    row=None if systematic_row_hkl is None else integer_triplet(systematic_row_hkl,'Systematic row')
    if row is not None and (not any(row) or np.dot(row,geometry.orientation.zone)!=0):
        raise ValueError('Systematic row must be a nonzero reflection in the selected ZOLZ plane')
    # Coordinates, phases, FFT temporaries and returned arrays, not just U.
    working=128*int(np.prod(shape))/2**20+1
    with reserve_memory(working,memory_budget_mib,dense_mib=16*int(np.prod(shape))/2**20):
        hkl,g=checked.harmonics(shape,max(cutoff,cutoff if support_cutoff is None else support_cutoff))
        fourier=np.zeros(len(hkl),complex)
        prefactor=10*(1+1000*acceleration_kv/510998.95)*wavelength/potential.cell_volume_angstrom3
        for i,(h,vector) in enumerate(zip(hkl,g)):
            if i%64==0:check_cancelled(cancelled)
            if not np.any(h) or np.linalg.norm(vector)>cutoff:continue
            if row is not None and np.any(np.cross(h,row)):continue
            try:row_coordinates(h,checked.support_generators)
            except ValueError:
                # An explicitly larger compatibility cell can contain exact
                # translational extinctions. They are zero by the verified
                # decorated-motif symmetry, not dropped to fit an FFT mesh.
                continue
            # Use actual species/occupancy/B structure factors, not an equal-
            # form-factor geometric extinction rule for arbitrary structures.
            coefficient=potential.structure_factor(tuple(int(v) for v in h))
            if not np.isfinite(coefficient):raise ValueError('Potential provider returned a nonfinite Fourier coefficient')
            fourier[i]=prefactor*coefficient
        u=np.fft.ifft2(fourier.reshape(shape))*int(np.prod(shape))
        if np.max(abs(u.imag))>1e-10:raise ValueError('Projected Fourier potential is not real/Hermitian on this grid')
        check_cancelled(cancelled)
        return ProjectedPotential(geometry,u.real,fourier.reshape(shape),hkl,g,float(acceleration_kv),float(cutoff))
