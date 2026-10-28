"""Structure-derived orientations and integer reciprocal lattices (cycles/Å).

No propagation or projected-potential dependencies: atomic 3D geometry can use
this layer directly. Mistilt is deliberately not a crystal-orientation input.
"""
from dataclasses import dataclass
from fractions import Fraction
from math import gcd
import numpy as np
from .crystal import Crystal


def integer_triplet(value, name='indices') -> tuple[int,int,int]:
    values=np.asarray(value)
    if values.shape!=(3,) or not np.isfinite(values.astype(float)).all() or any(int(x)!=x for x in values):
        raise ValueError(f'{name} must contain three finite integer indices')
    result=tuple(int(x) for x in values)
    if max(map(abs,result))>10000:raise ValueError(f'{name} exceeds the bounded integer-geometry capability (10000)')
    return result


def primitive_direction(value) -> tuple[int,int,int]:
    u=integer_triplet(value,'Zone direction');d=gcd(gcd(abs(u[0]),abs(u[1])),abs(u[2]))
    if not d:raise ValueError('Zone direction cannot be [000]')
    return tuple(x//d for x in u)


def extended_gcd(a:int,b:int) -> tuple[int,int,int]:
    x0,x1,y0,y1=1,0,0,1;r,s=abs(a),abs(b)
    while s:
        q=r//s;r,s=s,r-q*s;x0,x1=x1,x0-q*x1;y0,y1=y1,y0-q*y1
    return r,x0*(1 if a>=0 else -1),y0*(1 if b>=0 else -1)


def integer_plane(zone) -> np.ndarray:
    """Primitive rank-two integer kernel of h*u+k*v+l*w=0, without search."""
    u,v,w=primitive_direction(zone);d,p,q=extended_gcd(u,v)
    if not d:return np.array([[1,0,0],[0,1,0]],dtype=np.int64)
    return np.array([[v//d,-u//d,0],[-w*p,-w*q,d]],dtype=np.int64)


def infer_zone(crystal:Crystal) -> tuple[int,int,int]:
    """Recover a commensurate structural local-z direction, never a beam tilt."""
    coefficients=np.array([0.,0.,1.])@np.linalg.inv(crystal.lattice_angstrom)
    scale=float(np.max(abs(coefficients)));ratios=coefficients/scale
    rational=[Fraction(float(x)).limit_denominator(10000) for x in ratios]
    if max(abs(float(x)-v) for x,v in zip(rational,ratios))>1e-12:
        raise ValueError('Structural local z is not a supported commensurate direction; provide an exact crystallographic orientation')
    denominator=1
    for f in rational:denominator=denominator*f.denominator//gcd(denominator,f.denominator)
    zone=primitive_direction(tuple(int(f*denominator) for f in rational))
    direction=np.asarray(zone)@crystal.lattice_angstrom;direction/=np.linalg.norm(direction)
    if not np.allclose(direction,[0,0,1],rtol=0,atol=1e-12):raise ValueError('Inferred direction does not align with structural local z')
    return zone


def translation_constraints(crystal:Crystal, labels=None) -> list[tuple[int,int,int,int]]:
    """Exact rational translations that permute the actual decorated motif.

    Per-site labels can include occupancy/B as well as species. A potential
    whose site properties break a chemical translation must use those labels.
    No assumption of FCC or of a particular direction is made.
    """
    positions=np.asarray(crystal.fractional_positions)%1;n=len(positions)
    if not n or n>256:raise ValueError('Periodic translation search supports 1–256 sites; supply a smaller verified cell')
    labels=tuple(crystal.species) if labels is None else tuple(labels)
    if len(labels)!=n:raise ValueError('Translation labels must match the site count')
    result=[]
    for j in range(n):
        if labels[j]!=labels[0]:continue
        shift=(positions[j]-positions[0])%1
        rational=[Fraction(float(x)).limit_denominator(n) for x in shift]
        if max(abs(float(x)-v) for x,v in zip(rational,shift))>1e-10:continue
        valid=True
        for label,p in zip(labels,positions):
            delta=positions-(p+shift);delta-=np.rint(delta)
            matches=np.flatnonzero(np.max(abs(delta),axis=1)<1e-10)
            if len(matches)!=1 or labels[int(matches[0])]!=label:valid=False;break
        if not valid:continue
        denominator=1
        for f in rational:denominator=denominator*f.denominator//gcd(denominator,f.denominator)
        result.append(tuple(int(f*denominator) for f in rational)+(denominator,))
    return result


def reciprocal_plane(zone, crystal:Crystal, labels=None) -> np.ndarray:
    """Primitive ZOLZ lattice respecting actual motif translations.

    Intersect the integer kernel with each exact translation congruence. Motif
    extinctions beyond translational symmetry remain Fourier coefficients;
    they are not confused with a Bravais reciprocal basis.
    """
    basis=integer_plane(zone)
    for x,y,z,denominator in translation_constraints(crystal,labels):
        a,b=(int(v) for v in basis@np.array([x,y,z],dtype=np.int64))
        ga=gcd(a,denominator);common=gcd(ga,b);period=denominator//ga
        x0=0 if period==1 else (-b//common*pow(a//ga,-1,period))%period
        transform=np.array([[period,0],[x0,ga//common]],dtype=np.int64)
        basis=_bounded_product(transform,basis)
    return basis


def _bounded_product(a,b):
    result=np.asarray(a,dtype=object)@np.asarray(b,dtype=object)
    if max(abs(int(x)) for x in result.flat)>10**9:
        raise ValueError('Integer geometry exceeds the bounded reciprocal-index capability')
    return np.asarray(result,dtype=np.int64)


def row_coordinates(vector,basis) -> np.ndarray:
    """Exact integer coordinates of an hkl in a two-generator plane."""
    h=integer_triplet(vector,'Reflection');B=np.asarray(basis,dtype=np.int64)
    for i,j in ((0,1),(0,2),(1,2)):
        det=int(B[0,i])*int(B[1,j])-int(B[0,j])*int(B[1,i])
        if not det:continue
        a=h[i]*int(B[1,j])-h[j]*int(B[1,i]);b=int(B[0,i])*h[j]-int(B[0,j])*h[i]
        if a%det or b%det:raise ValueError('Reflection is outside the selected reciprocal lattice')
        result=np.array([a//det,b//det],dtype=np.int64)
        if not np.array_equal(_bounded_product(result,B),h):raise ValueError('Reflection is outside the selected ZOLZ plane')
        return result
    raise ValueError('Reciprocal generators are linearly dependent')


def target_basis(basis,reciprocal,target=None) -> np.ndarray:
    """Metric reduction and target-compatible unimodular change of generators."""
    B=np.array(basis,dtype=np.int64,copy=True)
    if target is not None:
        a,b=(int(x) for x in row_coordinates(target,B));d=gcd(abs(a),abs(b))
        if not d:raise ValueError('Target reflection must be nonzero')
        a//=d;b//=d;_,p,q=extended_gcd(a,b)
        B=_bounded_product([[a,b],[-q,p]],B)
    else:
        for _ in range(128):
            g=B@reciprocal;lengths=np.sum(g*g,axis=1)
            if lengths[1]<lengths[0]-1e-12:B=B[[1,0]];continue
            n=int(np.rint(g[0]@g[1]/lengths[0]))
            if not n:break
            B=_bounded_product([[1,0],[-n,1]],B)
        else:raise ValueError('Reciprocal metric reduction did not converge')
        if next((v for v in B[0] if v),1)<0:B[0]*=-1
    g=B@reciprocal
    if np.linalg.det(g[:,:2])<0:B[1]*=-1
    g=B@reciprocal
    shift=int(np.ceil(g[0]@g[1]/(g[0]@g[0])-.5-1e-12))
    B=_bounded_product([[1,0],[-shift,1]],B)
    return B


@dataclass(frozen=True)
class CrystalOrientation:
    """A proper crystal-to-laboratory rotation, independent of any solver."""
    source:Crystal
    zone:tuple[int,int,int]
    frame:np.ndarray
    crystal:Crystal

    @classmethod
    def create(cls,crystal:Crystal,zone,target=None,*,frame=None):
        zone=primitive_direction(zone);cell=crystal.lattice_angstrom
        if not np.isfinite(cell).all() or not np.isfinite(crystal.fractional_positions).all() or np.linalg.cond(cell)>1e10:
            raise ValueError('Finite, well-conditioned crystal cell and finite atomic positions required')
        z=np.asarray(zone)@cell;z=z/np.linalg.norm(z)
        if frame is None:
            if target is not None:
                target=integer_triplet(target,'Target reflection')
                if np.dot(zone,target)!=0 or not any(target):raise ValueError('A nonzero target in the selected ZOLZ plane is required')
                x=crystal.g_vector(target)
            else:
                reference=min(np.eye(3),key=lambda v:abs(v@z));x=reference-reference.dot(z)*z
            x=x-x.dot(z)*z;x=x/np.linalg.norm(x);frame=np.stack((x,np.cross(z,x),z))
        frame=np.asarray(frame,dtype=float)
        if (frame.shape!=(3,3) or not np.isfinite(frame).all() or not np.allclose(frame@frame.T,np.eye(3),rtol=0,atol=1e-12)
            or np.linalg.det(frame)<0 or not np.allclose(frame[2],z,rtol=0,atol=1e-12)):
            raise ValueError('Frame must be right-handed, orthonormal and aligned with the declared crystal direction')
        local=Crystal(cell@frame.T,crystal.fractional_positions,crystal.species)
        return cls(crystal,zone,frame.copy(),local)

    @property
    def positions_local(self) -> np.ndarray:
        return self.source.fractional_positions@self.source.lattice_angstrom@self.frame.T
