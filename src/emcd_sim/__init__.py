"""Research-stage EMCD simulator with physical Ni elastic Bloch-wave entrance channeling.

The magnetic/core-loss MDFF and outgoing wave remain approximations, and
the program is not yet a quantitatively validated EMCD solver.
"""

from .crystal import Crystal, fcc_nickel
from .elastic import BeamSet, ElasticModel, depth_coherence
from .physical_elastic import PhysicalElasticModel
from .scattering import IndependentAtomPotential, nickel_lobato_factor
from .geometry import Microscope, VirtualDetector, electron_wavelength_angstrom
from .inelastic import LEdgeSpectrum, TabulatedEdgeSpectrum, DipoleMDFF
from .simulation import EMCDSimulation, SimulationResult
from .voltage import ConstantMagnetization, TabulatedMagnetization

__version__ = "0.2.0"
__all__ = [
    "Crystal", "fcc_nickel", "BeamSet", "ElasticModel", "PhysicalElasticModel",
    "IndependentAtomPotential", "nickel_lobato_factor", "depth_coherence",
    "Microscope", "VirtualDetector", "electron_wavelength_angstrom",
    "LEdgeSpectrum", "TabulatedEdgeSpectrum", "DipoleMDFF", "EMCDSimulation", "SimulationResult",
    "ConstantMagnetization", "TabulatedMagnetization",
]
