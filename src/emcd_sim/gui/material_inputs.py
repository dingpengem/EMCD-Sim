"""Saved source-backed input records; fields and identities retain project compatibility.

These dataclasses retain historical inherited storage fields. Source declaration,
validation and preparation belong to mdff_providers, independently of GUI state.
"""
from dataclasses import dataclass
from .forward_settings import NiForwardSettings


@dataclass(frozen=True)
class ImportedSettings(NiForwardSettings):
    """Explicit tensor identity and selected edges, without inherited Ni energies.

    The source declares element, core transition, crystal-frame reversal pair
    and energy coverage. Empty declarations are invalid until acknowledged;
    a missing source never selects the historical Ni adapter.
    """
    model: str='imported'
    source: str=''
    ionizing_element: str=''
    core_edge: str='L2,3'
    magnetic_state: str=''
    site_indices: tuple|None=None
    selected_edges: tuple=()
    pair_reversed: bool=False
    l3: float=float('nan')
    l2: float=float('nan')
    correction: bool=False


@dataclass(frozen=True)
class ProviderSettings(ImportedSettings):
    """Explicit source-backed XMCD/atomic inputs without inherited Ni physics."""
    model: str='xmcd'
    provider_schema: int=1
    provider_declaration: dict|None=None
