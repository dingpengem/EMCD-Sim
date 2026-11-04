"""Declared dipole-MDFF imports: explicit magnetic states, no inferred reversal or extrapolation."""
from dataclasses import dataclass
from pathlib import Path
import hashlib,json
import numpy as np
from ase.data import atomic_numbers
from .mdff_tensor import DipoleTensor
from .mdff_edges import validate_edge, validate_selected

CONVENTION='d=<i|r|f>;T=d*d_dagger;I=ReTr(RT);angular_Q=2*pi*g'


def proper_frame(value):
    r=np.asarray(value,float)
    if r.shape!=(3,3) or not np.isfinite(r).all() or not np.allclose(r.T@r,np.eye(3),rtol=0,atol=1e-10) or not np.isclose(np.linalg.det(r),1,rtol=0,atol=1e-10):
        raise ValueError('Tensor frame_to_crystal must be a proper orthonormal Cartesian rotation')
    return r


def psd_tensor(energy,value,source):
    # Existing DipoleTensor supplies dimensions, finite, energy and Hermiticity checks.
    t=DipoleTensor(energy,np.asarray(value,complex),source)
    scale=np.max(abs(t.tensor_angstrom2_per_ev),axis=(1,2))
    defect=np.max(abs(t.tensor_angstrom2_per_ev-t.tensor_angstrom2_per_ev.swapaxes(-1,-2).conj()),axis=(1,2))
    if np.any(defect>1e-10*np.maximum(scale,1e-300)):
        raise ValueError('Imported tensor must be Hermitian relative to its own spectral scale')
    if np.any(np.linalg.eigvalsh(t.tensor_angstrom2_per_ev).min(axis=-1)<-1e-12*np.maximum(scale,1e-300)):
        raise ValueError('Imported dipole tensor must be positive semidefinite (no clipping/repair)')
    return t


@dataclass(frozen=True)
class ImportedMDFF:
    energy_ev: np.ndarray
    plus: DipoleTensor
    minus: DipoleTensor
    even: DipoleTensor
    metadata: dict
    sha256: str
    path: str

    @classmethod
    def load(cls,path,expected_sha256=''):
        p=Path(path)
        try:raw=p.read_bytes()
        except OSError as exc:raise ValueError('Missing/unreadable imported MDFF source: '+str(p)) from exc
        digest=hashlib.sha256(raw).hexdigest()
        if expected_sha256 and digest!=expected_sha256:raise ValueError('Imported MDFF checksum changed; validate source again')
        try:d=json.loads(raw)
        except (ValueError,UnicodeError) as exc:raise ValueError('Imported MDFF requires a UTF-8 JSON declaration') from exc
        required={'schema','element','edge','energy_ev','selected_ev','units','normalization','basis','frame_to_crystal',
            'magnetic_state','magnetization_crystal','reversal','source','validity','status','convention'}
        if not isinstance(d,dict) or not required<=d.keys():raise ValueError('Imported MDFF missing required declarations')
        if d['schema']!=1 or d['convention']!=CONVENTION:raise ValueError('Unsupported tensor schema/convention')
        validate_edge(d['element'],d['edge'])
        if d['units']!='angstrom^2/eV' or d['normalization']!='per_atom_relative':raise ValueError('Explicit angstrom^2/eV per_atom_relative tensor units required; no cross-section calibration')
        if d['basis'] not in ('crystal_cartesian','declared_local'):raise ValueError('Declare tensor Cartesian basis')
        frame=proper_frame(d['frame_to_crystal'])
        if d['basis']=='crystal_cartesian' and not np.allclose(frame,np.eye(3),rtol=0,atol=1e-12):raise ValueError('Crystal Cartesian tensors require identity frame_to_crystal')
        for key in ('source','validity'):
            if not isinstance(d[key],str) or not d[key].strip():raise ValueError('Nonempty source provenance and validity assumptions required')
        if d['status'] not in ('synthetic','physical_source_unvalidated'):raise ValueError('Import status must be synthetic or physical_source_unvalidated; importing does not establish scientific validation')
        e=np.asarray(d['energy_ev'],float)
        if e.ndim!=1 or len(e)<2 or not np.isfinite(e).all() or e[0]<=0 or np.any(np.diff(e)<=0):raise ValueError('Strictly increasing positive finite energy grid required')
        validate_selected(d['element'],d['edge'],d['selected_ev'],e[[0,-1]])
        m=np.asarray(d['magnetization_crystal'],float)
        if m.shape!=(3,) or not np.isfinite(m).all() or not np.isfinite(np.linalg.norm(m)) or np.linalg.norm(m)<1e-12:raise ValueError('Declare a finite nonzero crystal Cartesian magnetic/reference axis with finite norm')
        def tensor(name):
            try:
                v=d[name];real=np.asarray(v['real'],float);imag=np.asarray(v['imag'],float)
            except (KeyError,TypeError,ValueError) as exc:raise ValueError('Missing/invalid explicit tensor '+name) from exc
            if real.shape!=(len(e),3,3) or imag.shape!=(len(e),3,3):
                raise ValueError('Each tensor real/imag component requires shape (n_energy,3,3); broadcasting is unsupported')
            a=real+1j*imag
            return psd_tensor(e,a,d['source'])
        if d['magnetic_state']=='nonmagnetic':
            if d['reversal']!='identical_nonmagnetic' or any(k in d for k in ('T_plus','T_minus')):raise ValueError('Nonmagnetic source requires T and identical_nonmagnetic declaration')
            plus=minus=even=tensor('T')
            if not np.allclose(plus.tensor_angstrom2_per_ev.imag,0,rtol=0,atol=1e-12*max(float(abs(plus.tensor_angstrom2_per_ev).max()),1e-300)):
                raise ValueError('Declared time-reversal-invariant nonmagnetic electric-dipole tensor must be real')
        elif d['magnetic_state']=='uniform_fm':
            if d['reversal']!='explicit_pair_shared_even':raise ValueError('Uniform FM requires explicit +M/-M and shared-even reversal declaration; no state is manufactured')
            plus,minus,even=[tensor(k) for k in ('T_plus','T_minus','T_even')]
            v=(plus.tensor_angstrom2_per_ev+minus.tensor_angstrom2_per_ev)/2
            if not np.allclose(v,even.tensor_angstrom2_per_ev,rtol=1e-10,atol=1e-12*max(float(abs(v).max()),1e-300)):
                raise ValueError('Explicit magnetic states do not share the declared nonmagnetic tensor')
        else:raise ValueError('Only nonmagnetic and uniform_fm states supported; AFM/ferrimagnetic/SDW unsupported')
        # Atomic declarations are a reserved, complete schema. In particular,
        # stripping only the model tag must not turn generated data into an
        # unchecked ordinary import while retaining atomic provenance claims.
        atomic_fields={key for key in d if key.startswith('atomic_')}
        required_atomic={'atomic_model','atomic_parameters','atomic_parameter_document',
            'atomic_parameter_source_utf8','atomic_parameter_sha256','atomic_parameter_path'}
        if atomic_fields and atomic_fields!=required_atomic:
            raise ValueError('Incomplete or unsupported atomic model provenance')
        if atomic_fields:
            from .atomic_ionization import validate_embedded_atomic
            validate_embedded_atomic(d,plus,minus)
        return cls(e,plus,minus,even,d,digest,str(p.resolve()))

    def tensors(self,energy,crystal_to_microscope,magnetization):
        e=np.asarray(energy,float)
        if e.ndim!=1 or not len(e) or not np.isfinite(e).all() or np.any(np.diff(e)<=0) or e[0]<self.energy_ev[0] or e[-1]>self.energy_ev[-1]:
            raise ValueError('No imported MDFF energy extrapolation; require finite ascending samples')
        m=np.asarray(magnetization,float);native=np.asarray(self.metadata['magnetization_crystal'],float)
        if m.shape!=(3,) or not np.isfinite(m).all() or not np.isfinite(np.linalg.norm(m)) or np.linalg.norm(m)<1e-12 or not np.allclose(m/np.linalg.norm(m),native/np.linalg.norm(native),rtol=0,atol=1e-10):
            raise ValueError('Imported tensor magnetic axis differs from declared crystal axis; supply a validated rotated source')
        a=proper_frame(crystal_to_microscope)@proper_frame(self.metadata['frame_to_crystal'])
        result=[]
        for t in (self.plus,self.minus):
            v=t.tensor_angstrom2_per_ev
            # Convex interpolation preserves PSD; interpolation never extrapolates.
            value=np.stack([np.interp(e,self.energy_ev,v[:,i,j].real)+1j*np.interp(e,self.energy_ev,v[:,i,j].imag) for i in range(3) for j in range(3)],axis=-1).reshape(-1,3,3)
            rotated=np.einsum('ia,eab,jb->eij',a,value,a)
            result.append(psd_tensor(e,rotated,self.metadata['source']+';sha256='+self.sha256))
        return result

    def provenance(self):
        result=dict(path=self.path,sha256=self.sha256,energy_bounds_ev=self.energy_ev[[0,-1]].tolist(),**{k:self.metadata[k] for k in ('element','edge','selected_ev','units','normalization','basis','frame_to_crystal','magnetic_state','magnetization_crystal','reversal','source','validity','status','convention')})
        for key in ('atomic_model','atomic_parameters','atomic_parameter_document','atomic_parameter_source_utf8','atomic_parameter_sha256','atomic_parameter_path'):
            if key in self.metadata:result[key]=self.metadata[key]
        for key in ('provider_identity','xmcd_declarations','xmcd_source_path'):
            if key in self.metadata:result[key]=self.metadata[key]
        return result
