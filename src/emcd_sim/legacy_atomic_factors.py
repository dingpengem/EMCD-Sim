"""Opt-in adapter for the user's external neutral-atom ATOMICSCATFACT table.

No third-party table data are bundled here. The pinned source is loaded only
on explicit request, never in place of the historical Ni Lobato provider.
"""
from dataclasses import dataclass, field
from functools import lru_cache, partial
import hashlib
from numbers import Integral
import os
from pathlib import Path
from types import ModuleType

import numpy as np

PROVIDER_NAME = 'legacy-atomicscatfact-neutral-v1'
SOURCE_SHA256 = '1a93fe5b5fa86ea968049d8f4daee99a00981f225b3e8b8d0d9417460443535a'
SOURCE_POTENTIAL_SCALE = 47.878009
# Pinned-source audit of all 44 XF/Mott rows: the first common native knot
# after every failed positivity/origin-bound/monotonicity interval. This is
# an operating limit, not a certification of the underlying atomic data.
MOTT_MIN_STL = 0.04
TABLE_ENVIRONMENT = 'EMCD_SIM_LEGACY_ATOMIC_TABLE'


def atomic_number(element):
    """Resolve neutral element symbols/numbers through ASE's periodic table.

    Do not accept ions, isotope aliases, atomic-number strings or booleans.
    ASE is already the application's CIF/chemical-symbol dependency.
    """
    if isinstance(element, (bool, np.bool_)):
        raise TypeError('An element symbol or integer atomic number is required')
    if isinstance(element, Integral):
        z = int(element)
    elif isinstance(element, str):
        from ase.data import atomic_numbers
        if element not in atomic_numbers:
            raise ValueError(f'Unknown neutral chemical symbol: {element!r}')
        z = atomic_numbers[element]
    else:
        raise TypeError('An element symbol or integer atomic number is required')
    if not 1 <= z <= 98:
        raise ValueError('Legacy neutral atomic factors support Z=1..98 only')
    return z


@dataclass(frozen=True)
class LegacyNeutralAtomFactors:
    """Nonrelativistic electron amplitudes in angstrom, not potential factors."""
    source_path: str
    source_sha256: str
    _module: ModuleType = field(repr=False, compare=False)

    @classmethod
    def from_file(cls, path):
        """Load only the reviewed source bytes; changes require a fresh audit.

        Compile in memory to avoid writing bytecode beside the external file.
        There is no search-path import of a module named ``scattering``.
        """
        source = Path(path).expanduser().resolve()
        try:
            data = source.read_bytes()
        except OSError as exc:
            raise ValueError(
                f'Legacy neutral-atom elastic provider cannot read {source}: {exc}. '
                f'Configure {TABLE_ENVIRONMENT} with the reviewed external scattering.py; '
                'the table is not bundled. Ni-only Lobato calculations do not need it.'
            ) from exc
        digest = hashlib.sha256(data).hexdigest()
        if digest != SOURCE_SHA256:
            raise ValueError('Legacy atomic source SHA256 differs from the reviewed file')
        return _load_source(str(source), digest, data)

    def factor(self, element, g_angstrom_inv):
        z = atomic_number(element)
        raw = np.asarray(g_angstrom_inv)
        if raw.dtype.kind not in 'iuf':
            raise TypeError('Crystallographic |g| must be real numeric values')
        g = np.asarray(raw, dtype=float)
        limit = 3.0 if z == 1 else 12.0
        if not np.isfinite(g).all() or np.any(g < 0) or np.any(g > limit):
            raise ValueError(f'Z={z}: crystallographic |g| must be finite in 0..{limit} inverse angstrom')
        if self._module._METHOD[z-1] == 2 and np.any((g>0) & (g<2*MOTT_MIN_STL)):
            raise ValueError(
                f'Z={z}: unsupported positive STL below {MOTT_MIN_STL} '
                f'(|g| below {2*MOTT_MIN_STL} inverse angstrom) for the XF/Mott provider. '
                'Finite source values here can be physically unreliable. '
                'STL=0 retains its separate source definition; no extrapolation is applied.'
            )
        # Both EF and XF/Mott source branches return potential-scaled factors.
        # Their different source expressions must share this one conversion.
        try:
            values = np.array([self._module.elastic_atomic_scattering_factor(z, float(x)/2,
                               option=2) / SOURCE_POTENTIAL_SCALE for x in g.flat])
        except ArithmeticError as exc:
            raise ValueError(
                f'Legacy atomic source numerical failure for Z={z}: {exc}. '
                'XF/Mott evaluation is unreliable near zero positive |g|; '
                'no replacement value or extrapolation was applied.'
            ) from exc
        values = values.reshape(g.shape)
        if not np.isfinite(values).all():
            raise ValueError('Legacy atomic source returned nonfinite factors')
        return float(values) if g.ndim == 0 else values

    def atomic_factors(self, species):
        return {s: partial(self.factor, atomic_number(s)) for s in set(species)}

    def provenance(self):
        return dict(provider=PROVIDER_NAME, source_path=self.source_path,
            source_sha256=self.source_sha256, coverage='neutral Z=1..98',
            input='crystallographic |g| in inverse angstrom; source STL=|g|/2',
            output='nonrelativistic electron scattering amplitude in angstrom',
            source_scale_removed=SOURCE_POTENTIAL_SCALE,
            interpolation='unchanged external source: four-point cubic, skip -1/-2 markers',
            source_input_limits='H: |g|<=3; Z=2..98: |g|<=12; these are not accuracy bounds',
            numerical_operating_range='EF: source limits; XF/Mott: |g|=0 or 0.08<=|g|<=12; no extrapolation',
            quantitative_accuracy='Not established against independent atomic data for this legacy table',
            numerical_limitations='XF/Mott 0<STL<0.04 rejected for all 44 affected elements; source interpolation unchanged in the accepted domain',
            redistribution='unverified; external table is not bundled or licensed by EMCD-Sim',
            original_fortran_equivalence='not verified against the original Fortran executable')


@lru_cache(maxsize=4)
def _load_source(path, digest, data):
    module = ModuleType('_emcd_external_atomicscatfact')
    exec(compile(data, path, 'exec'), module.__dict__)
    if len(module._STL) != 62 or len(module._EF) != 98 or len(module._XF) != 98:
        raise ValueError('Unexpected external atomic table dimensions')
    return LegacyNeutralAtomFactors(path, digest, module)


def configured_legacy_factors():
    path = os.environ.get(TABLE_ENVIRONMENT)
    if not path:
        raise ValueError(f'Configure {TABLE_ENVIRONMENT} with the reviewed external scattering.py for non-Ni elastic diffraction')
    return LegacyNeutralAtomFactors.from_file(path)


def factors_for_elastic_species(species):
    """Ni-only structures retain Lobato; opt-in multi-species use one table."""
    from .scattering import nickel_lobato_factor
    if set(species) == {'Ni'}:
        return {'Ni': nickel_lobato_factor}
    return configured_legacy_factors().atomic_factors(species)
