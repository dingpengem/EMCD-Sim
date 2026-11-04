"""Explicit provider identities shared by elastic GUI, exports and projects."""
from .scattering import nickel_lobato_factor
from .adaptive_scattering import atomic_factors, provenance
from .legacy_atomic_factors import configured_legacy_factors

LOBATO='nickel-lobato-2014'
ADAPTIVE='adaptive-dirac-pade-2026'
LEGACY='legacy-atomicscatfact-neutral-v1'
DEFAULT_PROVIDER=ADAPTIVE
CHOICES=(('Adaptive Dirac-Pade 2026 (default; neutral Z=1-118)',ADAPTIVE),
         ('Ni Lobato 2014 (legacy compatibility)',LOBATO),
         ('External legacy atomic table (Z=1-98)',LEGACY))


def resolved_provider(species,selection='auto'):
    if selection=='auto':return LOBATO if set(species)=={'Ni'} else ADAPTIVE
    if selection not in (LOBATO,ADAPTIVE,LEGACY):raise ValueError('Unknown elastic scattering provider: '+str(selection))
    return selection


def factors_for_provider(species,selection='auto'):
    provider=resolved_provider(species,selection)
    if provider==LOBATO:
        if set(species)!={'Ni'}:raise ValueError('Ni Lobato provider supports only Ni; select Dirac-Pade for other neutral atoms')
        return {'Ni':nickel_lobato_factor}
    if provider==ADAPTIVE:return atomic_factors(species)
    return configured_legacy_factors().atomic_factors(species)


def provider_provenance(species,selection='auto'):
    provider=resolved_provider(species,selection)
    if provider==ADAPTIVE:return provenance()
    if provider==LEGACY:return configured_legacy_factors().provenance()
    return dict(provider=LOBATO,output='electron amplitude in angstrom',source='Lobato and Van Dyck (2014), Z=28',compatibility='original Ni coefficients and evaluation unchanged')
