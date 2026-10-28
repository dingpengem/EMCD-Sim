"""General periodic ZOLZ geometry; no orientation-specific providers.

The structural orientation is reusable by atomic 3D through crystallography;
only this layer imposes a reciprocal plane and a periodic transverse FFT cell.
"""
from dataclasses import dataclass
from itertools import product
import numpy as np
from .crystal import Crystal
from .crystallography import CrystalOrientation,reciprocal_plane,target_basis,row_coordinates,integer_triplet
from .elastic import BeamSet
from .geometry import electron_wavelength_angstrom


def fft_shape(value) -> tuple[int,int]:
    shape=(value,value) if isinstance(value,(int,np.integer)) else tuple(value)
    if len(shape)!=2 or any(not isinstance(n,(int,np.integer)) or n<12 or n%2 for n in shape):
        raise ValueError('FFT sampling requires two even dimensions >=12')
    if max(shape)>512:raise ValueError('FFT dimensions exceed the bounded 512-point geometry capability; review memory and sampling explicitly')
    return tuple(int(n) for n in shape)


@dataclass(frozen=True)
class ProjectedGeometry:
    orientation:CrystalOrientation
    generators:np.ndarray
    support_generators:np.ndarray
    target:tuple[int,int,int] | None=None

    @classmethod
    def from_crystal(cls,crystal:Crystal,zone,target=None,*,frame=None,labels=None,generators=None):
        target=None if target is None else integer_triplet(target,'Target reflection')
        orientation=CrystalOrientation.create(crystal,zone,target,frame=frame)
        canonical=target_basis(reciprocal_plane(zone,crystal,labels),orientation.crystal.reciprocal_angstrom_inv,target)
        if generators is None:generators=canonical.copy()
        else:
            values=np.asarray(generators)
            if values.shape!=(2,3):raise ValueError('FFT reciprocal cell needs two integer Miller-index generators')
            generators=np.array([integer_triplet(h,'FFT generator') for h in values],dtype=np.int64)
            if np.any(generators@np.asarray(orientation.zone)):raise ValueError('FFT generators do not belong to the specified ZOLZ plane')
            for h in canonical:
                try:row_coordinates(h,generators)
                except ValueError as exc:raise ValueError('FFT cell omits part of the structure-derived reciprocal lattice') from exc
        return cls(orientation,generators.copy(),canonical,target)

    @classmethod
    def from_oriented(cls,crystal:Crystal,zone,target=None,*,labels=None,generators=None):
        return cls.from_crystal(crystal,zone,target,frame=np.eye(3),labels=labels,generators=generators)

    @property
    def crystal(self) -> Crystal:return self.orientation.crystal

    @property
    def frame(self) -> np.ndarray:return self.orientation.frame

    @property
    def reciprocal_xy(self) -> np.ndarray:return (self.generators@self.crystal.reciprocal_angstrom_inv)[:,:2]

    @property
    def real_cell_xy(self) -> np.ndarray:
        """Row-vector dual cell in Å, including oblique cells; a_i dot b_j=δij."""
        return np.linalg.inv(self.reciprocal_xy).T

    @property
    def area_angstrom2(self) -> float:return float(abs(np.linalg.det(self.real_cell_xy)))

    def hkl_within(self,cutoff) -> tuple[tuple[int,int,int],...]:
        if not np.isfinite(cutoff) or cutoff<=0:raise ValueError('Positive finite reciprocal cutoff required')
        B=(self.support_generators@self.crystal.reciprocal_angstrom_inv)[:,:2]
        bounds=np.ceil(cutoff*np.linalg.norm(np.linalg.inv(B),axis=0)).astype(int)
        if np.prod(2*bounds.astype(float)+1)>500000:
            raise ValueError('Reciprocal-plane search exceeds 500000 candidates; reduce cutoff or use a better conditioned verified cell')
        items=[]
        for coefficients in product(*(range(-int(b),int(b)+1) for b in bounds)):
            h=tuple(int(v) for v in np.asarray(coefficients)@self.support_generators)
            length=float(np.linalg.norm(self.crystal.g_vector(h)))
            if length<=cutoff+1e-12:items.append((length,h))
        items.sort(key=lambda x:(round(x[0],12),x[1]))
        return tuple(h for _,h in items)

    def beams(self,cutoff) -> BeamSet:
        """Complete radial Bravais-ZOLZ support; motif extinctions are not cropped."""
        return BeamSet(self.hkl_within(cutoff))

    def harmonics(self,grid_points,cutoff):
        shape=fft_shape(grid_points)
        for h in self.hkl_within(cutoff):
            coordinates=row_coordinates(h,self.generators)
            if any(abs(int(v))>=n//2 for v,n in zip(coordinates,shape)):
                raise ValueError('FFT mesh misses physical ZOLZ harmonics or reaches its Nyquist boundary; enlarge the grid explicitly')
        f=[np.rint(np.fft.fftfreq(n)*n).astype(int) for n in shape]
        m,n=np.meshgrid(*f,indexing='ij')
        hkl=(m[...,None]*self.generators[0]+n[...,None]*self.generators[1]).reshape(-1,3)
        return hkl,(hkl@self.crystal.reciprocal_angstrom_inv)[:,:2]

    def bragg_tilt(self,kv=200.,target=None) -> float:
        h=self.target if target is None else integer_triplet(target)
        if h is None:raise ValueError('Specify a target reflection for Bragg alignment')
        g=self.crystal.g_vector(h)
        if abs(g[2])>1e-10 or abs(g[1])>1e-10 or g[0]<=0:
            raise ValueError('Scalar Bragg tilt requires a positive local-x ZOLZ target; use vector alignment for another frame')
        return -500*electron_wavelength_angstrom(kv)*float(g[0])
