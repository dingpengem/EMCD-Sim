"""Pinned-kernel import compatibility; no memory state or implementation here.

Consumers: double_channeling, multislice_double_channeling,
multislice_reference and projected_potential. Their authenticated source imports
this name. All admission/reservation work and state belong to memory_budget;
other maintained callers import that owner directly.
"""
from ..memory_budget import reserve_memory

__all__ = ('reserve_memory',)
