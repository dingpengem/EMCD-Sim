"""True [017] cell and crystal-[001] XMCD tensor transformed to local axes."""
from dataclasses import dataclass,replace
import hashlib
from pathlib import Path
import numpy as np
from .crystal import Crystal,fcc_nickel
from .elastic import BeamSet
from .geometry import Microscope,VirtualDetector,electron_wavelength_angstrom
from .physical_elastic import PhysicalElasticModel
from .scattering import IndependentAtomPotential
from .scattering import FourierCutoffPotential
from .benchmark import nickel_physical_benchmark
from .xmcd_effective_mdff import effective_tensor_from_xmcd
from .mdff_tensor import DipoleTensor
from .wien2k_xmcd import load_wien2k_xmcd


@dataclass(frozen=True)
class Ni017Geometry:
    a_angstrom: float=3.524
    @property
    def crystal(self):
        ni=fcc_nickel(self.a_angstrom)
        return Crystal(ni.lattice_angstrom@self.frame.T,ni.fractional_positions,ni.species)
    def _basis_beams(self,cutoff):
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

    @property
    def frame(self):
        return np.array([[1.,0.,0.],[0.,7.,-1.],[0.,1.,7.]])/np.array([[1.],[np.sqrt(50.)],[np.sqrt(50.)]])

    def beams(self,cutoff):
        items=[]
        for h,k,l in self._basis_beams(cutoff).hkl:
            target=(l,-k,-h);items.append((np.linalg.norm(self.crystal.g_vector(target)),target))
        items.sort(key=lambda t:(round(t[0],12),t[1]))
        return BeamSet(tuple(h for _,h in items))

    def harmonics(self,grid_points,cutoff):
        for h,k,l in self.beams(cutoff).hkl:
            if max(abs(h),abs(l))>=grid_points//2:raise ValueError('FFT mesh misses physical oriented harmonics')
        f=np.rint(np.fft.fftfreq(grid_points)*grid_points).astype(int);m,n=np.meshgrid(f,f,indexing='ij')
        hkl=np.stack((m,7*n,-n),axis=-1).reshape(-1,3)
        return hkl,(hkl@self.crystal.reciprocal_angstrom_inv)[:,:2]

    def bragg_tilt(self,kv=200.):
        return -500*electron_wavelength_angstrom(kv)*np.linalg.norm(self.crystal.g_vector((2,0,0)))

    def model(self,offset=0.,*,y_offset=0.,kv=200.,beam_cutoff=3.2,potential_cutoff=2.2,ideal=False):
        crystal=self.crystal;beams=BeamSet(((0,0,0),(2,0,0))) if ideal else self.beams(beam_cutoff)
        p=FourierCutoffPotential(IndependentAtomPotential(crystal),potential_cutoff)
        elastic=PhysicalElasticModel(crystal,Microscope(kv,(self.bragg_tilt(kv)+offset,y_offset)),beams,p)
        g=crystal.g_vector((2,0,0))[0]
        detectors={k:VirtualDetector((g/2,s*g/2),.16*g) for k,s in (('A',1),('B',-1))}
        return replace(nickel_physical_benchmark(),elastic=elastic,detectors=detectors,chiral_groups=None)


def rotated_tensor(path,energy_ev=None,*,eta=1.,beta=1.,frame=None):
    """Reverse eta in the cubic frame first, then apply real R T R^T."""
    R=Ni017Geometry().frame if frame is None else np.asarray(frame,float)
    if R.shape!=(3,3) or not np.allclose(R@R.T,np.eye(3),atol=1e-12) or np.linalg.det(R)<0:
        raise ValueError('Tensor rotation needs a proper orthonormal frame')
    t=effective_tensor_from_xmcd(path,energy_ev,eta=eta,beta=beta)
    local=np.einsum('ia,eab,jb->eij',R,t.tensor_angstrom2_per_ev,R)
    return DipoleTensor(t.energy_ev,local,t.source+';cubic_M=[001];R_T_RT')


def energy_audit(source):
    source=Path(source);s=load_wien2k_xmcd(source);D=s.dichroic;N=s.nonmagnetic
    # Identify the two strongest separated absorption features, then select
    # signed magnetic extrema in nonoverlapping neighborhoods of those features.
    maxima=np.where((N[1:-1]>N[:-2])&(N[1:-1]>=N[2:]))[0]+1
    peaks=sorted(sorted(maxima,key=lambda i:N[i],reverse=True)[:2],key=lambda i:s.energy_ev[i])
    if s.energy_ev[peaks[1]]-s.energy_ev[peaks[0]]<10:raise ValueError('L3/L2 assignment is ambiguous')
    selected={}
    for edge,i in zip(('L3','L2'),peaks):
        mask=abs(s.energy_ev-s.energy_ev[i])<=3.;ix=np.flatnonzero(mask);j=ix[np.argmax(abs(D[mask]))]
        selected[edge]=float(s.energy_ev[j])
    files={}
    for suffix in ('xmcd','raw1','raw2','broad1','broad2','rawxmcd','inso','injoint','inc'):
        p=source.with_suffix('.'+suffix)
        if not p.exists():raise ValueError('Required energy/magnetization audit input missing: '+str(p))
        files[suffix]=hashlib.sha256(p.read_bytes()).hexdigest()
    inso=source.with_suffix('.inso').read_text()
    if '0 0 1' not in inso:raise ValueError('Verify crystal magnetization axis in .inso')
    core=[float(x) for x in source.with_suffix('.injoint').read_text().splitlines()[4].split()]
    split=abs(core[1]-core[0])*13.605693122994
    b1=np.loadtxt(source.with_suffix('.broad1'));b2=np.loadtxt(source.with_suffix('.broad2'))
    raw1=np.loadtxt(source.with_suffix('.raw1'));raw2=np.loadtxt(source.with_suffix('.raw2'))
    early=s.energy_ev<840.;early_error=float(np.max(abs(2*D[early]-b1[early,3])))
    i1=int(np.argmax(abs(b1[:,3])));i2=int(np.argmax(abs(b2[:,3])))
    offset=selected['L3']-b1[i1,0];predicted=offset+split+b2[i2,0]
    if abs(predicted-selected['L2'])>.02 or early_error>1e-7:raise ValueError('Raw-edge/source energy correspondence failed')
    return dict(selected_magnetic_energies_ev=selected,xas_peak_energies_ev=[float(s.energy_ev[i]) for i in peaks],
        native_bounds_ev=[float(s.energy_ev[0]),float(s.energy_ev[-1])],core_energies_rydberg=core,
        core_splitting_ev=split,predicted_L2_magnetic_energy_ev=predicted,early_L3_broad1_matching_error=early_error,
        raw1_raw2_relative_magnetic_peaks_ev=[float(a[np.argmax(abs(a[:,3])),0]) for a in (raw1,raw2)],
        assignment='Lower-energy raw1/broad1 is L3 (2p3/2); upper shifted raw2/broad2 is L2 (2p1/2). Core ordering and 17.4806 eV split corroborate opposite-sign peaks.',
        energy_calibration='No experimental calibration or source shift applied. 852.7/870 eV are external reference energies, not peaks on this native axis.',
        magnetization_cubic=[0,0,1],magnetization_local=(Ni017Geometry().frame@np.array([0.,0.,1.])).tolist(),input_sha256=files)
