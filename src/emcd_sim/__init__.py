"""Production BW/FFT and tensor-based EMCD runtime interfaces.

Projected IAM and approximate MDFF models remain research approximations.
"""

from .crystal import Crystal, fcc_nickel
from .elastic import BeamSet, depth_coherence
from .physical_elastic import PhysicalElasticModel
from .scattering import IndependentAtomPotential, nickel_lobato_factor
from .geometry import Microscope, VirtualDetector, electron_wavelength_angstrom
from .simulation import EMCDSimulation, SimulationResult
from .mdff_tensor import TransitionDataset, DipoleTensor, dipole_tensor_from_transitions, cycles_to_angular_q
from .single_channeling_tensor import run_tensor_single_channeling

__version__ = "0.6.1b2"
__all__ = [
    "Crystal", "fcc_nickel", "BeamSet", "PhysicalElasticModel",
    "IndependentAtomPotential", "nickel_lobato_factor", "depth_coherence",
    "Microscope", "VirtualDetector", "electron_wavelength_angstrom",
    "EMCDSimulation", "SimulationResult",
    "TransitionDataset", "DipoleTensor", "dipole_tensor_from_transitions", "cycles_to_angular_q", "run_tensor_single_channeling",
]
