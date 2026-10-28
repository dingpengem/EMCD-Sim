"""Study conveniences using the shared structure-derived orientation engine.

Historical studies select configurations in their scripts; no axis-specific
reciprocal, Fourier-potential or propagation algorithm lives here.
"""
from dataclasses import dataclass,replace
import numpy as np
from emcd_sim.crystal import fcc_nickel
from emcd_sim.projected_geometry import ProjectedGeometry
from emcd_sim.geometry import Microscope,VirtualDetector
from emcd_sim.elastic import BeamSet
from emcd_sim.scattering import IndependentAtomPotential,FourierCutoffPotential
from emcd_sim.physical_elastic import PhysicalElasticModel
from emcd_sim.benchmark import nickel_physical_benchmark

@dataclass(frozen=True)
class StudyGeometry:
    zone:tuple
    target:tuple
    a_angstrom:float=3.524
    @property
    def geometry(self):return ProjectedGeometry.from_crystal(fcc_nickel(self.a_angstrom),self.zone,self.target)
    @property
    def crystal(self):return self.geometry.crystal
    @property
    def frame(self):return self.geometry.frame
    @property
    def generators(self):return self.geometry.generators
    def beams(self,cutoff):return self.geometry.beams(cutoff)
    def harmonics(self,grid_points,cutoff):return self.geometry.harmonics(grid_points,cutoff)
    def bragg_tilt(self,kv=200.):return self.geometry.bragg_tilt(kv)
    def model(self,offset=0.,*,y_offset=0.,kv=200.,beam_cutoff=3.2,potential_cutoff=2.2,ideal=False):
        c=self.crystal;beams=BeamSet(((0,0,0),self.target)) if ideal else self.beams(beam_cutoff)
        p=FourierCutoffPotential(IndependentAtomPotential(c),potential_cutoff)
        e=PhysicalElasticModel(c,Microscope(kv,(self.bragg_tilt(kv)+offset,y_offset)),beams,p)
        g=c.g_vector(self.target)[0]
        detectors={k:VirtualDetector((g/2,s*g/2),.16*g) for k,s in (('A',1),('B',-1))}
        return replace(nickel_physical_benchmark(),elastic=e,detectors=detectors,chiral_groups=None)

def rotated_tensor(path,energy_ev=None,*,eta=1.,beta=1.,frame):
    from emcd_sim.xmcd_effective_mdff import effective_tensor_from_xmcd
    from emcd_sim.mdff_tensor import DipoleTensor
    R=np.asarray(frame,float)
    if R.shape!=(3,3) or not np.allclose(R@R.T,np.eye(3),atol=1e-12) or np.linalg.det(R)<0:raise ValueError('Proper orthonormal tensor frame required')
    t=effective_tensor_from_xmcd(path,energy_ev,eta=eta,beta=beta)
    return DipoleTensor(t.energy_ev,np.einsum('ia,eab,jb->eij',R,t.tensor_angstrom2_per_ev,R),t.source+';crystal_to_local_R_T_RT')
