"""FCC Ni physical-model construction and paired-aperture geometry."""
from .crystal import fcc_nickel
from .elastic import BeamSet
from .geometry import Microscope, VirtualDetector
from .simulation import EMCDSimulation


def nickel_apertures(condition: str):
    """Nominal collection apertures in 000-centered reciprocal coordinates.

    Thales circle: 000--+200 for 2BC, and 000--±200 for 3BC.
    Geometry presets are not numerical optimization of EMCD SNR.
    """
    g200 = 2 / 3.524
    radius = 0.16 * g200
    if condition in {"two-beam", "near-2bc"}:
        return {
            "A": VirtualDetector((0.5*g200, 0.5*g200), radius),
            "B": VirtualDetector((0.5*g200, -0.5*g200), radius),
        }, None
    if condition == "symmetric-3bc":
        # Symmetric 3BC has four chiral positions and alternating signs:
        # (RU+LD) - (RD+LU). Two apertures on +200 side alone omit the
        # left/right symmetry cancellation of the classical double difference.
        return {
            "RU": VirtualDetector((0.5*g200, 0.5*g200), radius),
            "RD": VirtualDetector((0.5*g200, -0.5*g200), radius),
            "LU": VirtualDetector((-0.5*g200, 0.5*g200), radius),
            "LD": VirtualDetector((-0.5*g200, -0.5*g200), radius),
        }, {"A": ("RU", "LD"), "B": ("RD", "LU")}
    # Preserve original v0.3 systematic-row and zone-axis demonstrators.
    return {
        "A": VirtualDetector((0.55*g200, 0.52*g200), radius),
        "B": VirtualDetector((0.55*g200, -0.52*g200), radius),
    }, None


def nickel_physical_benchmark(tilt_mrad_xy: tuple[float, float] = (0, 0),
                              acceleration_kv: float = 200.0,
                              beam_order: int = 3,
                              debye_waller_b_angstrom2: float = 0.0,
                              zone2d_max_g_angstrom_inv: float | None = None,
                              max_beams: int = 25,
                              beams_override: BeamSet | None = None,
                              diffraction_condition: str = "systematic-row") -> EMCDSimulation:
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
    detectors, chiral_groups = nickel_apertures(diffraction_condition)
    return EMCDSimulation(
        elastic=elastic,
        detectors=detectors, chiral_groups=chiral_groups,
    )
