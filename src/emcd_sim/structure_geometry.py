"""Scientific structure records, oriented geometry and lossless snapshot operations.

Calculation callers supply the actual structure and geometry settings.
Historical Ni demonstrations are selected explicitly through study_presets.
"""
from dataclasses import dataclass
from itertools import product
from pathlib import Path
import hashlib,warnings
import numpy as np
from ase import Atoms
from ase.build import bulk
from ase.io import read
from .projected_geometry import ProjectedGeometry
from .crystal import Crystal
from .elastic import BeamSet
from .geometry import Microscope,electron_wavelength_angstrom
from .physical_elastic import PhysicalElasticModel
from .scattering import IndependentAtomPotential
from .scattering import FourierCutoffPotential, elastic_reflection_allowed
from .elastic_providers import factors_for_provider


def orientation(cell,zone,target=None):
    """Proper structural frame; a supplied reciprocal target defines local x."""
    from .crystallography import CrystalOrientation
    source=Crystal(np.asarray(cell),np.empty((0,3)),())
    return CrystalOrientation.create(source,zone,target).frame


@dataclass
class Structure:
    atoms: object
    source: str='In-memory ASE structure'
    sha256: str=''
    import_warnings: str=''

    @classmethod
    def nickel(cls):return cls(bulk('Ni','fcc',a=3.524,cubic=True),'Built-in FCC Ni, a=3.524 Å')

    @classmethod
    def from_cif(cls,path):
        path=Path(path)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always');atoms=read(path,format='cif',store_tags=True)
        if atoms.cell.rank!=3 or abs(atoms.cell.volume)<1e-8:raise ValueError('A nonsingular 3D periodic cell is required')
        from .crystallographic_sites import crystallographic_sites
        atoms.info['crystallographic_sites'] = crystallographic_sites(atoms)
        return cls(atoms,str(path.resolve()),hashlib.sha256(path.read_bytes()).hexdigest(),'\n'.join(str(w.message) for w in caught))

    @property
    def elastic_reason(self):
        return self.elastic_reason_for('auto')

    def elastic_reason_for(self,provider):
        for occ in self.atoms.info.get('occupancy',{}).values():
            values=np.asarray(list(occ.values()),float)
            if (len(occ)!=1 or not np.isfinite(values).all() or abs(sum(values)-1)>1e-8):return 'Reciprocal geometry only: partial/disordered CIF occupancies are not supported.'
        try:factors_for_provider(self.atoms.get_chemical_symbols(),provider)
        except (ValueError,TypeError,OSError,ImportError) as exc:return f'Reciprocal geometry only: {exc}'
        return ''

    def description(self):
        a=self.atoms;sg=a.info.get('spacegroup','Not determined (no symmetry inference)')
        return (f'Source: {self.source}\nSHA256: {self.sha256 or "internally generated"}\nFormula: {a.get_chemical_formula()}\n'
                f'Cell a,b,c (Å), alpha,beta,gamma (deg): {a.cell.cellpar().tolist()}\nSpecies: {sorted(set(a.get_chemical_symbols()))}\n'
                f'Atoms: {len(a)}\nSpace group supplied by CIF: {sg}\nIndexing: hkl labels refer to the ASE-imported cell shown above; no automatic primitive reduction.\nFractional positions:\n'
                +'\n'.join(f'{s}: {p[0]:.8f} {p[1]:.8f} {p[2]:.8f}' for s,p in zip(a.get_chemical_symbols(),a.get_scaled_positions()))
                + ('\nImport warnings:\n'+self.import_warnings if self.import_warnings else ''))


@dataclass(frozen=True)
class Settings:
    zone: tuple=(0,0,1)
    target: tuple=(2,0,0)
    tilt: tuple=(0.,0.)
    voltage: float=300.
    thickness: float=30.
    beam_cutoff: float=2.5
    potential_cutoff: float=2.0
    b_factor: float=0.
    basis_mode: str='full'
    elastic_provider: str='adaptive-dirac-pade-2026'


def geometry(structure,settings,*,systematic_row=False):
    if not np.isfinite([*settings.tilt,settings.voltage,settings.thickness,settings.beam_cutoff,settings.potential_cutoff,settings.b_factor]).all():raise ValueError('Settings must be finite')
    if min(settings.voltage,settings.thickness,settings.beam_cutoff,settings.potential_cutoff)<=0 or settings.b_factor<0:raise ValueError('Positive voltage, thickness and cutoffs, and nonnegative B are required')
    cell=structure.atoms.cell.array;R=orientation(cell,settings.zone,settings.target)
    if settings.basis_mode not in ('full','two-beam'):raise ValueError('Diffraction basis must be full or two-beam')
    if settings.basis_mode=='two-beam' and systematic_row:
        raise ValueError('Ideal two-beam support is distinct from a multibeam systematic-row restriction')
    crystal=Crystal(cell@R.T,structure.atoms.get_scaled_positions(),tuple(structure.atoms.get_chemical_symbols()))
    # |h_i|=|g dot a_i| <= cutoff*|a_i| gives a complete finite search.
    limits=np.ceil(settings.beam_cutoff*np.linalg.norm(cell,axis=1))
    # Check in floating point before integer conversion/product: large but
    # valid CIF cells can overflow int64 and otherwise bypass this work bound.
    if not np.isfinite(limits).all() or np.prod(2*limits+1)>500000:
        raise ValueError('Cell/cutoff search too large for interactive preview; lower the beam cutoff.')
    bounds=limits.astype(int)
    items=[];has_factors=not structure.elastic_reason_for(settings.elastic_provider)
    selection_potential=(IndependentAtomPotential(crystal,debye_waller_b_angstrom2=settings.b_factor,
        atomic_factors=factors_for_provider(crystal.species,settings.elastic_provider)) if has_factors else None)
    for h in product(*(range(-v,v+1) for v in bounds)):
        if settings.basis_mode=='two-beam' and h not in ((0,0,0),settings.target):continue
        if systematic_row and np.any(np.cross(h,settings.target)):continue
        if np.dot(h,settings.zone)!=0:continue
        g=crystal.g_vector(h);length=np.linalg.norm(g)
        if length>settings.beam_cutoff+1e-10:continue
        if has_factors and not elastic_reflection_allowed(crystal,h,selection_potential):continue
        items.append((length,h))
    items.sort(key=lambda p:(round(p[0],12),p[1]));hkl=tuple(p[1] for p in items)
    if len(hkl)>121:raise ValueError(f'{len(hkl)} beams exceed the interactive limit 121. Lower the radial cutoff; no beams were silently dropped.')
    if len(hkl)<2:raise ValueError('No nonzero ZOLZ reflections at this cutoff; increase it or change zone direction.')
    g=np.stack([crystal.g_vector(h)[:2] for h in hkl]);microscope=Microscope(settings.voltage,settings.tilt)
    return crystal,R,hkl,g,microscope


def elastic_model(structure,settings,*,systematic_row=False):
    reason=structure.elastic_reason_for(settings.elastic_provider)
    if reason:raise ValueError(reason)
    crystal,R,hkl,g,microscope=geometry(structure,settings,systematic_row=systematic_row)
    potential=FourierCutoffPotential(IndependentAtomPotential(crystal,debye_waller_b_angstrom2=settings.b_factor,
        atomic_factors=factors_for_provider(crystal.species,settings.elastic_provider)),settings.potential_cutoff)
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


def structure_snapshot(structure):
    """Capture existing snapshot fields without changing original atom order."""
    a=structure.atoms
    snapshot = dict(species=a.get_chemical_symbols(),lattice_angstrom=a.cell.array.tolist(),fractional_positions=a.get_scaled_positions().tolist(),
        pbc=a.pbc.tolist(),occupancies=a.info.get('occupancy',{}),source=structure.source,sha256=structure.sha256,import_warnings=structure.import_warnings,
        description=structure.description())
    if 'crystallographic_sites' in a.info:snapshot['crystallographic_sites'] = a.info['crystallographic_sites']
    if 'spacegroup_kinds' in a.arrays:
        kinds=a.arrays['spacegroup_kinds']
        snapshot['atom_arrays']={'spacegroup_kinds':dict(dtype=str(kinds.dtype),values=kinds.tolist())}
    return snapshot


def restore_structure(snapshot):
    """Restore stored geometry, including any saved original-index ASE arrays."""
    if not snapshot:raise ValueError('Legacy export has no complete numeric crystal snapshot; inspect results read-only, or prepare a verified structure explicitly.')
    atoms=Atoms(snapshot['species'],cell=snapshot['lattice_angstrom'],scaled_positions=snapshot['fractional_positions'],pbc=snapshot['pbc'])
    atoms.info['occupancy']=snapshot.get('occupancies',{})
    if 'crystallographic_sites' in snapshot:atoms.info['crystallographic_sites'] = snapshot['crystallographic_sites']
    if 'cartesian_positions' in snapshot:atoms.set_positions(snapshot['cartesian_positions'])
    for name,array in snapshot.get('atom_arrays',{}).items():
        if name in ('numbers','positions'):raise ValueError('Reserved ASE array in structure snapshot')
        atoms.new_array(name,np.asarray(array['values'],dtype=array['dtype']))
    return Structure(atoms,snapshot['source'],snapshot.get('sha256',''),snapshot.get('import_warnings',''))


def structures_match(snapshot,structure):
    """Compare stored identity and coordinates using the existing tolerances."""
    current=structure_snapshot(structure)
    return (snapshot['species']==current['species'] and snapshot.get('sha256','')==current.get('sha256','')
        and snapshot.get('occupancies',{})==current.get('occupancies',{})
        and all(np.allclose(snapshot[k],current[k],rtol=0,atol=1e-12) for k in ('lattice_angstrom','fractional_positions','pbc')))


def projected_geometry_from_oriented_crystal(settings,crystal,fft_generators=None):
    """Build FFT support from this request's explicit oriented elastic crystal.

    The crystal includes all species/sites, with lattice rows already rotated
    into beam Cartesian axes. No material or orientation preset is selected.
    ProjectedGeometry validates periodic ZOLZ support for the declared zone.
    """
    return ProjectedGeometry.from_oriented(crystal,settings.zone,settings.target,generators=fft_generators)
