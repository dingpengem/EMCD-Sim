"""Explicit independent-electron 2p -> cubic 3d model; no material defaults.

Angular algebra is shared with the unchanged historical Ni implementation.
"""
from dataclasses import asdict, dataclass
from pathlib import Path
import hashlib
import json
import numpy as np
from ase.data import atomic_numbers
from .ni_local_mdff import (core_spinor_amplitude, ni_2p_to_3d_dipole,
    cubic_orbital_coefficients, hydrogenic_radial_dipole_angstrom, radial_dipole_from_table)
from .mdff_tensor import TransitionDataset, dipole_tensor_from_transitions, gaussian_broadening_ev
from .imported_mdff import ImportedMDFF, CONVENTION

dipole_2p_to_3d = ni_2p_to_3d_dipole
ORBITALS = tuple(cubic_orbital_coefficients())


@dataclass(frozen=True)
class AtomicMaterialParameters:
    """All inputs required. Holes: (up,down) pairs in ORBITALS order.

    Energies/splittings/sigma in eV; radial dipole in Angstrom. The proper
    frame rotates the entire cubic orbital/spin model, not spin alone.
    """
    element: str
    atomic_number: int
    edge_energies_ev: tuple
    radial_integral_angstrom: float
    crystal_field_basis: str
    crystal_field_ev: float
    exchange_ev: float
    spin_resolved_holes: tuple
    magnetization_local: tuple
    frame_to_crystal: tuple
    broadening_ev: float
    source: str
    radial_source: str
    validity: str
    status: str

    def validate(self):
        if not isinstance(self.atomic_number,(int,np.integer)) or isinstance(self.atomic_number,(bool,np.bool_)):
            raise ValueError('Atomic number must be an integer')
        if self.element not in ('Sc','Ti','V','Cr','Mn','Fe','Co','Ni','Cu','Zn') or atomic_numbers[self.element] != self.atomic_number:
            raise ValueError('Declare a matching 3d-series element and atomic number (Sc-Zn)')
        for values in (self.edge_energies_ev,self.spin_resolved_holes,self.frame_to_crystal,
                       [self.radial_integral_angstrom,self.crystal_field_ev,self.exchange_ev,self.broadening_ev]):
            if np.asarray(values).dtype.kind not in 'fiu':
                raise ValueError('Atomic energies, holes, frame and scalar parameters must be real numeric values')
        e = np.asarray(self.edge_energies_ev, float)
        if e.shape != (2,) or not np.isfinite(e).all() or not 0 < e[0] < e[1]:
            raise ValueError('Declare positive ascending L3/L2 edge energies in eV')
        v = np.asarray([self.radial_integral_angstrom,self.crystal_field_ev,self.exchange_ev,self.broadening_ev],float)
        if not np.isfinite(v).all() or v[0]<=0 or v[3]<=0 or np.any(v[1:3]<0):
            raise ValueError('Radial integral/broadening must be positive finite; splittings nonnegative finite')
        if self.crystal_field_basis != 'real_cubic_eg_t2g':
            raise ValueError('Only explicit real_cubic_eg_t2g basis supported')
        h = np.asarray(self.spin_resolved_holes,float)
        if h.shape!=(5,2) or not np.isfinite(h).all() or np.any((h<0)|(h>1)) or not np.any(h>0):
            raise ValueError('Declare five orbital (up,down) hole pairs in [0,1], not all zero')
        if np.asarray(self.magnetization_local).shape!=(3,) or not np.array_equal(self.magnetization_local,(0,0,1)):
            raise ValueError('Only local magnetization +z supported; rotate the entire declared frame')
        a = np.asarray(self.frame_to_crystal,float)
        if a.shape!=(3,3) or not np.isfinite(a).all() or not np.allclose(a.T@a,np.eye(3),atol=1e-12,rtol=0) or not np.isclose(np.linalg.det(a),1,atol=1e-12,rtol=0):
            raise ValueError('frame_to_crystal must be a proper orthonormal rotation')
        for name in ('source','radial_source','validity'):
            if not isinstance(getattr(self,name),str) or not getattr(self,name).strip():
                raise ValueError('Nonempty source, radial_source and validity provenance required')
        if self.status not in ('synthetic','physical_source_unvalidated'):
            raise ValueError('Atomic status must be synthetic or physical_source_unvalidated; never quantitative validated')


def transitions_for_material(parameters, *, magnetization_sign=1):
    """Coherent orbital components; incoherent core/final events.

    Reversal swaps spin holes AND exchange shifts in the fixed core-SOC basis.
    Operation order follows historical Ni without importing Ni parameters.
    """
    p = parameters
    p.validate()
    if magnetization_sign not in (-1,1):
        raise ValueError('magnetization_sign must be +1 or -1')
    energies,dipoles,weights,edges = [],[],[],[]
    for two_j,edge,edge_energy in ((3,'L3',p.edge_energies_ev[0]),(1,'L2',p.edge_energies_ev[1])):
        for two_mj in range(-two_j,two_j+1,2):
            for spin,index in ((1,0),(-1,1)):
                for k,(orbital,components) in enumerate(cubic_orbital_coefficients().items()):
                    holes = p.spin_resolved_holes[k][index if magnetization_sign==1 else 1-index]
                    if holes<=0:
                        continue
                    crystal_shift = (0.6 if orbital in ('z2','x2_y2') else -0.4)*p.crystal_field_ev
                    exchange_shift = -0.5*spin*magnetization_sign*p.exchange_ev
                    energy = edge_energy+crystal_shift+exchange_shift
                    if not np.isfinite(energy) or energy<=0:
                        raise ValueError('Resulting transition energy must be positive finite')
                    amplitude = np.zeros(3,dtype=complex)
                    for m in range(-2,3):
                        if components[m+2]!=0:
                            amplitude += components[m+2]*dipole_2p_to_3d(two_j,two_mj,m,spin,p.radial_integral_angstrom)
                    if np.max(np.abs(amplitude))>1e-14:
                        energies.append(energy);dipoles.append(amplitude);weights.append(holes);edges.append(edge)
                    elif np.any(amplitude!=0):
                        raise ValueError('Radial scale below supported transition-amplitude threshold')
    if not energies:
        raise ValueError('No supported nonzero transitions')
    return TransitionDataset(np.asarray(energies),np.asarray(dipoles),np.asarray(weights),
        np.asarray(edges),np.asarray([p.element+'_atomic_model']*len(edges)),
        'APPROXIMATE INDEPENDENT-ELECTRON ATOMIC MODEL; '+p.source+'; '+p.radial_source)


def export_atomic_parameters(parameter_path, output):
    """Snapshot strict JSON inputs and export an immutable explicit tensor pair.

    Schema 1: kind=atomic_2p3d, parameters=all fields, energy_ev=explicit grid.
    Embedded original bytes/hash preserve provenance independently of the input path.
    """
    path = Path(parameter_path)
    raw = path.read_bytes()
    d = json.loads(raw)
    if not isinstance(d,dict) or set(d)!={'schema','kind','parameters','energy_ev'} or d['schema']!=1 or d['kind']!='atomic_2p3d':
        raise ValueError('Expected atomic_2p3d schema 1 with explicit parameters and energy_ev')
    try:
        p = AtomicMaterialParameters(**d['parameters'])
    except TypeError as exc:
        raise ValueError('Incomplete/unsupported atomic parameters') from exc
    p.validate()
    e = np.asarray(d['energy_ev'],float)
    if e.ndim!=1 or len(e)<2 or not np.isfinite(e).all() or np.any(e<=0) or np.any(np.diff(e)<=0):
        raise ValueError('Energy grid must be positive finite strictly increasing')
    if e[0]>p.edge_energies_ev[0] or e[-1]<p.edge_energies_ev[1]:
        raise ValueError('Energy grid must contain both selected edges')
    a,b = [dipole_tensor_from_transitions(transitions_for_material(p,magnetization_sign=s),e,p.broadening_ev).tensor_angstrom2_per_ev for s in (1,-1)]
    enc = lambda t: dict(real=t.real.tolist(),imag=t.imag.tolist())
    frame = np.asarray(p.frame_to_crystal,float)
    doc = dict(schema=1,element=p.element,edge='L2,3',energy_ev=e.tolist(),
        selected_ev=dict(zip(('L3','L2'),p.edge_energies_ev)),units='angstrom^2/eV',normalization='per_atom_relative',
        basis='declared_local',frame_to_crystal=frame.tolist(),magnetic_state='uniform_fm',
        magnetization_crystal=(frame@np.array([0.,0.,1.])).tolist(),reversal='explicit_pair_shared_even',
        source='APPROXIMATE ATOMIC MODEL: '+p.source,
        validity=p.validity+'; independent electron; no multiplets/core-hole/bands/absolute cross-section; physically unvalidated material parameters',
        status=p.status,convention=CONVENTION,T_plus=enc(a),T_minus=enc(b),T_even=enc((a+b)/2),
        atomic_parameters=asdict(p),atomic_parameter_document=d,atomic_parameter_source_utf8=raw.decode('utf-8'),
        atomic_parameter_sha256=hashlib.sha256(raw).hexdigest(),atomic_parameter_path=str(path.resolve()),
        atomic_model='independent_electron_cubic_2p3d_v1')
    target = Path(output)
    payload = (json.dumps(doc,indent=2,allow_nan=False)+'\n').encode('utf-8')
    with target.open('xb') as stream:
        stream.write(payload)
    try:
        return ImportedMDFF.load(target,hashlib.sha256(payload).hexdigest())
    except BaseException:
        target.unlink()
        raise


def validate_embedded_atomic(d, plus, minus):
    """Verify generated-model claims at the same import boundary as its tensors."""
    if d['atomic_model'] != 'independent_electron_cubic_2p3d_v1':
        raise ValueError('Unsupported atomic model/convention')
    try:
        raw = d['atomic_parameter_source_utf8'].encode('utf-8')
        original = json.loads(raw)
        if hashlib.sha256(raw).hexdigest()!=d['atomic_parameter_sha256'] or original!=d['atomic_parameter_document']:
            raise ValueError('Atomic parameter checksum/document mismatch')
        if original['parameters']!=d['atomic_parameters'] or original['energy_ev']!=d['energy_ev'] or original['schema']!=1 or original['kind']!='atomic_2p3d':
            raise ValueError('Atomic parameter declarations differ from embedded source')
        p = AtomicMaterialParameters(**d['atomic_parameters']);p.validate()
        if (d['element']!=p.element or d['status']!=p.status or d['basis']!='declared_local'
            or d['frame_to_crystal']!=original['parameters']['frame_to_crystal']
            or [d['selected_ev']['L3'],d['selected_ev']['L2']]!=list(p.edge_energies_ev)
            or d['magnetization_crystal']!=(np.asarray(p.frame_to_crystal)@np.array([0.,0.,1.])).tolist()):
            raise ValueError('Atomic model frame/element/edges/status differ from declared parameters')
        for sign,t in ((1,plus),(-1,minus)):
            expected = dipole_tensor_from_transitions(transitions_for_material(p,magnetization_sign=sign),
                np.asarray(d['energy_ev']),p.broadening_ev).tensor_angstrom2_per_ev
            if not np.allclose(t.tensor_angstrom2_per_ev,expected,rtol=1e-12,atol=0):
                raise ValueError('Atomic tensors do not reproduce their declared parameters')
    except (KeyError,TypeError,AttributeError) as exc:
        raise ValueError('Incomplete atomic model provenance') from exc


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Approximate atomic tensors from fully declared parameters; no element defaults')
    parser.add_argument('parameters',type=Path);parser.add_argument('output',type=Path)
    args = parser.parse_args()
    source = export_atomic_parameters(args.parameters,args.output)
    print(source.path+'\nSHA256: '+source.sha256+'\n'+source.metadata['validity'])


if __name__=='__main__':
    main()
