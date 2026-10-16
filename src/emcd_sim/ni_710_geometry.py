"""Actual cubic Ni [710] projected geometry; real hkl indexing throughout."""
from dataclasses import dataclass
import numpy as np
from .crystal import Crystal,fcc_nickel
from .elastic import BeamSet
from .geometry import Microscope,electron_wavelength_angstrom,VirtualDetector
from .physical_elastic import PhysicalElasticModel
from .scattering import IndependentAtomPotential
from .elastic_reference import FourierCutoffPotential
from .benchmark import nickel_physical_benchmark
from dataclasses import replace


@dataclass(frozen=True)
class Ni710Geometry:
    a_angstrom: float=3.524

    @property
    def frame(self):
        """Rows map cubic Cartesian components to local x,y,z."""
        return np.array([[0.,0.,1.],[1.,-7.,0.],[7.,1.,0.]])/np.array([[1.],[np.sqrt(50.)],[np.sqrt(50.)]])

    @property
    def crystal(self):
        ni=fcc_nickel(self.a_angstrom)
        return Crystal(ni.lattice_angstrom@self.frame.T,ni.fractional_positions,ni.species)

    def beams(self,cutoff):
        """Complete radial cutoff, including odd FCC reflections; no beam cap."""
        hmax=int(np.ceil(cutoff*self.a_angstrom/np.sqrt(50.)))
        lmax=int(np.ceil(cutoff*self.a_angstrom));items=[]
        for h in range(-hmax,hmax+1):
            for l in range(-lmax,lmax+1):
                if (h-l)%2:continue
                hkl=(h,-7*h,l);g=self.crystal.g_vector(hkl)
                if np.linalg.norm(g)<=cutoff+1e-12:items.append((np.linalg.norm(g),hkl))
        items.sort(key=lambda item:(round(item[0],12),item[1]))
        return BeamSet(tuple(h for _,h in items))

    def harmonics(self,grid_points,cutoff):
        """Rectangular projected supercell: Lx=a, Ly=a/sqrt(50).

        FFT (m,n) -> cubic (n,-7n,m). Forbidden parity modes have exactly zero
        potential and are not artificially identified with even-only [001] modes.
        """
        for h,k,l in self.beams(cutoff).hkl:
            if max(abs(h),abs(l))>=grid_points//2:
                raise ValueError('FFT mesh does not cover all oriented potential harmonics below cutoff')
        f=np.rint(np.fft.fftfreq(grid_points)*grid_points).astype(int)
        m,n=np.meshgrid(f,f,indexing='ij')
        hkl=np.stack((n,-7*n,m),axis=-1).reshape(-1,3)
        g=hkl@self.crystal.reciprocal_angstrom_inv
        return hkl,g[:,:2]

    def bragg_tilt(self,kv=200.):
        return -500*electron_wavelength_angstrom(kv)*np.linalg.norm(self.crystal.g_vector((0,0,2)))

    def model(self,offset=0.,*,kv=200.,beam_cutoff=3.2,potential_cutoff=2.2,ideal=False):
        crystal=self.crystal
        beams=BeamSet(((0,0,0),(0,0,2))) if ideal else self.beams(beam_cutoff)
        potential=FourierCutoffPotential(IndependentAtomPotential(crystal),potential_cutoff)
        elastic=PhysicalElasticModel(crystal,Microscope(kv,(self.bragg_tilt(kv)+offset,0.)),beams,potential)
        g=crystal.g_vector((0,0,2))[0]
        detectors={name:VirtualDetector((g/2,sign*g/2),.16*g) for name,sign in (('A',1),('B',-1))}
        return replace(nickel_physical_benchmark(),elastic=elastic,detectors=detectors,chiral_groups=None)
