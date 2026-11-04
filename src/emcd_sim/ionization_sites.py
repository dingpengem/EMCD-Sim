"""Explicit equivalent localized events; no magnetic/site equivalence inferred from species alone."""
from dataclasses import dataclass
import hashlib
import numpy as np


def single_site_phase_matrix(hkl, positions):
    """Per-site mean exp(+2*pi*i*(h_i-h_j).r), with input ordering intact.

    Eligibility and crystal-context checks belong to the calling adapter.
    Do not wrap/reduce coordinates here: preserve historical rounding.
    """
    h=np.asarray(hkl,int);p=np.asarray(positions,float)
    return np.exp(2j*np.pi*(h[:,None,:]-h[None,:,:])@p.T).mean(axis=-1)


@dataclass(frozen=True)
class IonizationSites:
    element: str
    indices: tuple
    all_positions: np.ndarray
    metric: np.ndarray
    normalization: str = 'mean_per_selected_atom'

    def __post_init__(self):
        from ase.data import atomic_numbers
        p=np.asarray(self.all_positions,float);metric=np.asarray(self.metric,float)
        if self.element not in atomic_numbers or self.element=='X' or p.ndim!=2 or p.shape[1:]!=(3,) or not 1<=len(p)<=256 or not np.isfinite(p).all():
            raise ValueError('Finite explicit positions and a real element are required')
        if metric.shape!=(3,3) or not np.isfinite(metric).all() or not np.allclose(metric,metric.T,rtol=0,atol=1e-12):raise ValueError('Invalid ionization crystal metric')
        try:cell=np.linalg.cholesky(metric)
        except np.linalg.LinAlgError as exc:raise ValueError('Positive definite crystal metric required') from exc
        if self.normalization!='mean_per_selected_atom':raise ValueError('Only explicit per-selected-atom mean normalization is supported')
        selected=tuple(self.indices)
        if not selected or any(type(i) is not int or not 0<=i<len(p) for i in selected) or len(set(selected))!=len(selected):raise ValueError('Select unique explicit ionization-site indices')
        for shift in p-p[0]:
            delta=(p+shift)[:,None,:]-p[None,:,:];delta-=np.rint(delta)
            near=np.linalg.norm(delta@cell,axis=-1)<1e-7
            if not (np.all(near.sum(axis=0)==1) and np.all(near.sum(axis=1)==1)):
                raise ValueError('Inequivalent or rotation-related/duplicate sites require site-resolved MDFF')
        p=p.copy()%1;metric=metric.copy();p.setflags(write=False);metric.setflags(write=False)
        object.__setattr__(self,'all_positions',p);object.__setattr__(self,'metric',metric);object.__setattr__(self,'indices',selected)

    @classmethod
    def from_structure(cls, structure, element, indices=None):
        a=structure.atoms
        if not np.all(a.pbc) or a.cell.rank!=3 or abs(a.cell.volume)<1e-8:
            raise ValueError('Ionization requires a nonsingular fully periodic 3D cell')
        if set(a.get_chemical_symbols())!={element}:
            raise ValueError('Imported MDFF requires a matching single-element crystal; multi-element site MDFF is unsupported')
        for name in ('initial_magmoms','initial_charges'):
            if a.has(name):
                values=np.asarray(a.arrays[name],float)
                if not np.isfinite(values).all() or not np.allclose(values,values[0],rtol=0,atol=1e-10):
                    raise ValueError('Inequivalent magnetic/charge sites require site-resolved MDFF; AFM/SDW is unsupported')
        for occ in a.info.get('occupancy',{}).values():
            if len(occ)!=1 or set(occ)!={element} or not np.isfinite(list(occ.values())).all() or abs(sum(occ.values())-1)>1e-8:
                raise ValueError('Partial/disordered ionization-site occupancies are unsupported')
        p=np.asarray(a.get_scaled_positions(wrap=True),float)
        if not 1<=len(p)<=256 or not np.isfinite(p).all():
            raise ValueError('Equivalent-site certification requires 1..256 finite explicit sites')
        # Translation is sufficient to preserve a Cartesian tensor unchanged.
        # Do not silently use space-group rotations without rotating each site's MDFF.
        def matching(q):
            delta=q[:,None,:]-p[None,:,:];delta-=np.rint(delta)
            near=np.linalg.norm(delta@a.cell.array,axis=-1)<1e-7
            return np.all(near.sum(axis=0)==1) and np.all(near.sum(axis=1)==1)
        if not matching(p):raise ValueError('Duplicate or ambiguous periodic ionization sites')
        if not all(matching((p+(q-p[0]))%1) for q in p):
            raise ValueError('Inequivalent or rotation-related sites: a single Cartesian MDFF cannot be assigned; site-resolved MDFF required')
        selected=tuple(range(len(p))) if indices is None else tuple(indices)
        if not selected or any(type(i) is not int or not 0<=i<len(p) for i in selected) or len(set(selected))!=len(selected):
            raise ValueError('Select unique, explicit zero-based equivalent ionization-site indices')
        metric=a.cell.array@a.cell.array.T
        p=p.copy();metric=metric.copy();p.setflags(write=False);metric.setflags(write=False)
        return cls(element,selected,p,metric)

    def positions_for(self,crystal):
        if (set(crystal.species)!={self.element} or len(crystal.species)!=len(self.all_positions)
                or not np.allclose(crystal.fractional_positions%1,self.all_positions,rtol=0,atol=1e-9)
                or not np.allclose(crystal.lattice_angstrom@crystal.lattice_angstrom.T,self.metric,rtol=1e-10,atol=1e-10)):
            raise ValueError('Ionization sites do not match the complete elastic crystal context')
        if self.normalization!='mean_per_selected_atom':raise ValueError('Unsupported ionization normalization')
        return self.all_positions[list(self.indices)]

    def single_phase(self,crystal,hkl):
        return single_site_phase_matrix(hkl,self.positions_for(crystal))

    def provenance(self):
        return dict(element=self.element,indices=list(self.indices),fractional_positions=self.all_positions[list(self.indices)].tolist(),
            equivalence='whole-cell translation orbit; rotations/inequivalent MDFF unsupported',normalization=self.normalization,
            structure_positions_sha256=hashlib.sha256(self.all_positions.astype('<f8').tobytes()).hexdigest())
