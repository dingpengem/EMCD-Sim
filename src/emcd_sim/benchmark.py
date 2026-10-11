"""FCC Ni [001] three-beam demonstrator, 200/(-200) systematic row."""
from .crystal import fcc_nickel
from .elastic import BeamSet, ElasticModel
from .geometry import Microscope, VirtualDetector
from .inelastic import LEdgeSpectrum, DipoleMDFF
from .simulation import EMCDSimulation
from .voltage import ConstantMagnetization, MagnetizationLaw


def nickel_three_beam(magnetization: MagnetizationLaw | None = None,
                      tilt_mrad_xy: tuple[float, float] = (0, 0),
                      acceleration_kv: float = 200.0,
                      extinction_distance_200_nm: float = 55.0) -> EMCDSimulation:
    crystal = fcc_nickel()
    g200 = 2 / 3.524
    elastic = ElasticModel(
        crystal=crystal,
        microscope=Microscope(acceleration_kv, tilt_mrad_xy),
        beams=BeamSet(),
        xi_reference_nm=extinction_distance_200_nm,
    )
    # Left/right detector locations have opposite signed y coordinate. To avoid
    # symmetry cancellation of +g and -g, use x != 0 (a standard 4-quadrant cut).
    centers = (0.55*g200, 0.52*g200)
    return EMCDSimulation(
        elastic=elastic, mdff=DipoleMDFF(LEdgeSpectrum()),
        magnetization=magnetization or ConstantMagnetization(),
        detectors={
            "A": VirtualDetector((centers[0], centers[1]), 0.16*g200),
            "B": VirtualDetector((centers[0], -centers[1]), 0.16*g200),
        },
    )


def nickel_physical_benchmark(magnetization: MagnetizationLaw | None = None,
                              tilt_mrad_xy: tuple[float, float] = (0, 0),
                              acceleration_kv: float = 200.0,
                              beam_order: int = 3,
                              debye_waller_b_angstrom2: float = 0.0,
                              zone2d_max_g_angstrom_inv: float | None = None,
                              max_beams: int = 25,
                              beams_override: BeamSet | None = None) -> EMCDSimulation:
    """FCC Ni neutral-atom physical-potential *entrance-only* EMCD benchmark.

    Default basis: (000), ±(200), ±(400), ±(600). The optionally centered
    ZOLZ basis is automatically selected from the FCC structure.
    The inelastic model is still deliberately illustrative, not quantitative.
    """
    from .scattering import IndependentAtomPotential
    from .physical_elastic import PhysicalElasticModel
    crystal = fcc_nickel()
    beams = (beams_override if beams_override is not None else
             BeamSet.systematic_row(beam_order) if zone2d_max_g_angstrom_inv is None else
             BeamSet.zolz(crystal, zone2d_max_g_angstrom_inv, max_beams))
    elastic = PhysicalElasticModel(
        crystal=crystal,
        microscope=Microscope(acceleration_kv, tilt_mrad_xy),
        beams=beams,
        potential=IndependentAtomPotential(
            crystal=crystal, debye_waller_b_angstrom2=debye_waller_b_angstrom2),
    )
    g200 = 2 / 3.524
    centers = (0.55 * g200, 0.52 * g200)
    return EMCDSimulation(
        elastic=elastic, mdff=DipoleMDFF(LEdgeSpectrum()),
        magnetization=magnetization or ConstantMagnetization(),
        detectors={
            "A": VirtualDetector((centers[0], centers[1]), 0.16 * g200),
            "B": VirtualDetector((centers[0], -centers[1]), 0.16 * g200),
        },
    )
