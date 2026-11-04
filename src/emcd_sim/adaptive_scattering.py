"""Neutral-atom electron amplitudes from the pinned 2026 Dirac-Pade deposit.

Only coefficient data are vendored, under their Apache-2.0 notices. This
independent NumPy evaluator needs neither the upstream Python package nor HDF5.
The Fourier convention is exp(-2*pi*i*g.r), not radians/angstrom or STL.
"""
from functools import lru_cache, partial
import hashlib
from importlib import resources
import json
from numbers import Integral

import numpy as np

PROVIDER = 'adaptive-dirac-pade-2026'
COEFFICIENT_SHA256 = 'a67788f59b426c07cf27913e023ed08e3a748fdb6b634d0bb5eed6b4ecf77b5c'


def element_number(element):
    if isinstance(element,(bool,np.bool_)):
        raise TypeError('Expected a neutral element symbol or integer Z')
    if isinstance(element,Integral):
        z=int(element)
    elif isinstance(element,str):
        from ase.data import atomic_numbers
        z=atomic_numbers.get(element,0)
    else:
        raise TypeError('Expected a neutral element symbol or integer Z')
    if not 1<=z<=118:
        raise ValueError('Neutral elements Z=1..118 are supported; ions and isotope aliases are not')
    return z


def data_resource(name):
    return resources.files('emcd_sim').joinpath('data','adaptive_dirac_pade_2026',name)


@lru_cache(maxsize=1)
def coefficient_data():
    raw=data_resource('coefficients.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=COEFFICIENT_SHA256:
        raise ValueError('Bundled Dirac-Pade coefficient SHA256 mismatch')
    data=json.loads(raw)
    if set(data)!=set(map(str,range(1,119))):raise ValueError('Incomplete Dirac-Pade element coverage')
    result={}
    for key,entry in data.items():
        a,b=np.asarray(entry['a'],float),np.asarray(entry['b'],float)
        dp=np.asarray([kind=='DP' for kind in entry['types']])
        if (a.ndim!=1 or b.shape!=a.shape or dp.shape!=a.shape or dp.sum()!=1 or not dp[-1]
                or not np.isfinite(a).all() or not np.isfinite(b).all() or (b<=0).any()):
            raise ValueError('Invalid Dirac-Pade coefficient record')
        a.setflags(write=False);b.setflags(write=False);dp.setflags(write=False)
        result[int(key)]=(a,b,dp)
    return result


def adaptive_factor(element,g_angstrom_inv):
    """f_e(|g|) in angstrom; 0<=|g|<=36 in crystallographic inverse angstrom.

    Reciprocals of 1+b*g^2 avoid cancellation in Z-f_x and needless large
    polynomial powers. Signed coefficients are retained; no clipping is used.
    The 36 limit is the upstream fitted reference range, not universal accuracy.
    """
    z=element_number(element)
    raw=np.asarray(g_angstrom_inv)
    if raw.dtype.kind not in 'iuf':raise TypeError('|g| must be real numeric data')
    g=np.asarray(raw,float)
    if not np.isfinite(g).all() or (g<0).any() or (g>36).any():
        raise ValueError('Dirac-Pade |g| must be finite in 0..36 inverse angstrom')
    a,b,dp=coefficient_data()[z]
    # At subnormal g, g squared may round to zero. The rational expression
    # then evaluates its continuous origin limit; no Mott subtraction occurs.
    with np.errstate(under='ignore'):
        t=1/(1+b*g[...,None]**2)
        terms=a*(t+t*t+dp*t*t*t)
    value=np.sum(terms,axis=-1)
    if not np.isfinite(value).all() or (value<=0).any():
        raise ValueError('Dirac-Pade evaluation failed finite/positive checks; no replacement applied')
    return float(value) if g.ndim==0 else value


def atomic_factors(species):
    return {symbol:partial(adaptive_factor,element_number(symbol)) for symbol in set(species)}


def provenance():
    return json.loads(data_resource('provenance.json').read_text(encoding='utf-8'))
