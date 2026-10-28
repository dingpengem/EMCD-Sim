"""Desktop adapters for ASE structures and the unchanged elastic BW solver."""
from dataclasses import dataclass,asdict
from math import gcd
from functools import reduce
from itertools import product
from pathlib import Path
import hashlib,warnings
import numpy as np
from ase.build import bulk
from ase.io import read
from emcd_sim.crystal import Crystal
from emcd_sim.elastic import BeamSet
from emcd_sim.geometry import Microscope,electron_wavelength_angstrom
from emcd_sim.physical_elastic import PhysicalElasticModel
from emcd_sim.scattering import IndependentAtomPotential
from emcd_sim.scattering import FourierCutoffPotential
from emcd_sim.physical_elastic import excitation_errors_angstrom_inv


def indices(text,direction=False):
    cleaned=text.translate(str.maketrans({'[':' ',']':' ','(':' ',')':' ', ',':' ','−':'-'})).strip()
    fields=cleaned.split()
    if len(fields)==1 and len(fields[0])==3 and fields[0].isdigit():fields=list(fields[0])
    if len(fields)!=3:raise ValueError('Enter three integer indices, e.g. 0 1 7 or [017].')
    result=tuple(int(x) for x in fields)
    if result==(0,0,0) and direction:raise ValueError('A zone direction cannot be [000].')
    if direction:
        divisor=reduce(gcd,(abs(v) for v in result));result=tuple(v//divisor for v in result)
    return result


def orientation(cell,zone,target=None):
    """Proper structural frame; a supplied reciprocal target defines local x."""
    from ..crystallography import CrystalOrientation
    source=Crystal(np.asarray(cell),np.empty((0,3)),())
    return CrystalOrientation.create(source,zone,target).frame


@dataclass
class Structure:
    atoms: object
    source: str='Built-in FCC Ni, a=3.524 A'
    sha256: str=''
    import_warnings: str=''

    @classmethod
    def nickel(cls):return cls(bulk('Ni','fcc',a=3.524,cubic=True))

    @classmethod
    def from_cif(cls,path):
        path=Path(path)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always');atoms=read(path,format='cif')
        if atoms.cell.rank!=3 or abs(atoms.cell.volume)<1e-8:raise ValueError('A nonsingular 3D periodic cell is required')
        return cls(atoms,str(path.resolve()),hashlib.sha256(path.read_bytes()).hexdigest(),'\n'.join(str(w.message) for w in caught))

    @property
    def elastic_reason(self):
        if set(self.atoms.get_chemical_symbols())!={'Ni'}:return 'Reciprocal geometry only: bundled IAM elastic factors support Ni, not these species.'
        for occ in self.atoms.info.get('occupancy',{}).values():
            if len(occ)!=1 or abs(sum(occ.values())-1)>1e-8:return 'Reciprocal geometry only: partial/disordered CIF occupancies are not supported.'
        return ''

    def description(self):
        a=self.atoms;sg=a.info.get('spacegroup','Not determined (no symmetry inference)')
        return (f'Source: {self.source}\nSHA256: {self.sha256 or "internally generated"}\nFormula: {a.get_chemical_formula()}\n'
                f'Cell a,b,c (A), alpha,beta,gamma (deg): {a.cell.cellpar().tolist()}\nSpecies: {sorted(set(a.get_chemical_symbols()))}\n'
                f'Atoms: {len(a)}\nSpace group supplied by CIF: {sg}\nFractional positions:\n'
                +'\n'.join(f'{s}: {p[0]:.8f} {p[1]:.8f} {p[2]:.8f}' for s,p in zip(a.get_chemical_symbols(),a.get_scaled_positions()))
                + ('\nImport warnings:\n'+self.import_warnings if self.import_warnings else ''))


@dataclass(frozen=True)
class Settings:
    zone: tuple=(0,1,7)
    target: tuple=(2,0,0)
    tilt: tuple=(round(float(-1000*electron_wavelength_angstrom(300)/3.524),10),0.)
    voltage: float=300.
    thickness: float=30.
    beam_cutoff: float=3.2
    potential_cutoff: float=2.5
    b_factor: float=0.
    basis_mode: str='full'


def geometry(structure,settings,*,systematic_row=False):
    if not np.isfinite([*settings.tilt,settings.voltage,settings.thickness,settings.beam_cutoff,settings.potential_cutoff,settings.b_factor]).all():raise ValueError('Settings must be finite')
    if min(settings.voltage,settings.thickness,settings.beam_cutoff,settings.potential_cutoff)<=0 or settings.b_factor<0:raise ValueError('Positive voltage, thickness and cutoffs, and nonnegative B are required')
    cell=structure.atoms.cell.array;R=orientation(cell,settings.zone,settings.target)
    if settings.basis_mode not in ('full','two-beam'):raise ValueError('Diffraction basis must be full or two-beam')
    if settings.basis_mode=='two-beam' and systematic_row:
        raise ValueError('Ideal two-beam support is distinct from a multibeam systematic-row restriction')
    crystal=Crystal(cell@R.T,structure.atoms.get_scaled_positions(),tuple(structure.atoms.get_chemical_symbols()))
    # |h_i|=|g dot a_i| <= cutoff*|a_i| gives a complete finite search.
    bounds=np.ceil(settings.beam_cutoff*np.linalg.norm(cell,axis=1)).astype(int)
    if np.prod(2*bounds+1)>500000:raise ValueError('Cell/cutoff search too large for interactive preview; lower the beam cutoff.')
    items=[];has_factors=not structure.elastic_reason
    for h in product(*(range(-v,v+1) for v in bounds)):
        if settings.basis_mode=='two-beam' and h not in ((0,0,0),settings.target):continue
        if systematic_row and np.any(np.cross(h,settings.target)):continue
        if np.dot(h,settings.zone)!=0:continue
        g=crystal.g_vector(h);length=np.linalg.norm(g)
        if length>settings.beam_cutoff+1e-10:continue
        if has_factors and not crystal.is_allowed(h):continue
        items.append((length,h))
    items.sort(key=lambda p:(round(p[0],12),p[1]));hkl=tuple(p[1] for p in items)
    if len(hkl)>121:raise ValueError(f'{len(hkl)} beams exceed the interactive limit 121. Lower the radial cutoff; no beams were silently dropped.')
    if len(hkl)<2:raise ValueError('No nonzero ZOLZ reflections at this cutoff; increase it or change zone direction.')
    g=np.stack([crystal.g_vector(h)[:2] for h in hkl]);microscope=Microscope(settings.voltage,settings.tilt)
    return crystal,R,hkl,g,microscope


def elastic_model(structure,settings,*,systematic_row=False):
    if structure.elastic_reason:raise ValueError(structure.elastic_reason)
    crystal,R,hkl,g,microscope=geometry(structure,settings,systematic_row=systematic_row)
    potential=FourierCutoffPotential(IndependentAtomPotential(crystal,debye_waller_b_angstrom2=settings.b_factor),settings.potential_cutoff)
    return PhysicalElasticModel(crystal,microscope,BeamSet(hkl),potential)


def excitation(g,tilt,voltage):
    lam=electron_wavelength_angstrom(voltage);ki=np.asarray(tilt)*.001/lam
    return .5*lam*(np.sum((np.asarray(g)+ki)**2,axis=-1)-np.dot(ki,ki))


def za_from_tilt(tilt,voltage):return -np.asarray(tilt)*.001/electron_wavelength_angstrom(voltage)
def tilt_from_za(q,voltage):return -np.asarray(q)*electron_wavelength_angstrom(voltage)*1000


def align_bragg(g,tilt,voltage,lock='None'):
    g=np.asarray(g,float);result=np.asarray(tilt,float).copy()
    if np.dot(g,g)<1e-16:raise ValueError('Select a nonzero reflection')
    error=float(excitation(g,tilt,voltage))
    free=np.array([lock!='X',lock!='Y'],bool);norm=np.dot(g[free],g[free])
    if norm<1e-16:
        if abs(error)<1e-12:return result
        raise ValueError('The locked component prevents alignment for this reflection')
    result[free]-=1000*error*g[free]/norm
    return result


def preview(structure,settings,*,systematic_row=False):
    model=elastic_model(structure,settings,systematic_row=systematic_row);z=np.array([0.,settings.thickness]);psi=model.amplitudes(z)
    return dict(settings=asdict(settings),beam_hkl=np.array(model.beams.hkl),g=model.reciprocal_vectors_xy,
        s=excitation_errors_angstrom_inv(model),depth_nm=z,amplitudes=psi,intensity=abs(psi[-1])**2,
        frame=orientation(structure.atoms.cell.array,settings.zone,settings.target),source=structure.source,systematic_row=systematic_row,
        source_sha256=structure.sha256,structure_description=structure.description(),model='Ni IAM, finite oriented ZOLZ BW; elastic only, no absorption/TDS or physical CBED disks')
