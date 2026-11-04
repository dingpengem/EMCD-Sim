"""Shared 2p->3d angular/radial interfaces; non-Ni quantitative models remain disabled."""
from dataclasses import dataclass
from .ni_local_mdff import (core_spinor_amplitude,ni_2p_to_3d_dipole,
    cubic_orbital_coefficients,hydrogenic_radial_dipole_angstrom,radial_dipole_from_table)
from .mdff_tensor import gaussian_broadening_ev

# Reuse the historical implementation exactly; no duplicate angular algebra.
dipole_2p_to_3d=ni_2p_to_3d_dipole


@dataclass(frozen=True)
class AtomicMaterialParameters:
    """No fabricated element-specific values: future providers must supply every field."""
    element: str
    edge_energies_ev: tuple
    radial_integral_angstrom: float
    spin_resolved_holes: tuple
    exchange_ev: float
    crystal_field_ev: float
    broadening_ev: float
    source: str


def transitions_for_material(parameters):
    raise ValueError('Generalized atomic-ionization spectra are not implemented/validated; use an explicit imported MDFF. Historical NiLocalConfig route is unchanged.')
