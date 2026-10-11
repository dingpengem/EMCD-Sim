"""2BC/3BC chiral detector geometry and coordinate-frame regression tests."""
import numpy as np
import pytest

from emcd_sim.benchmark import nickel_physical_benchmark
from emcd_sim.crystal import fcc_nickel
from emcd_sim.diffraction import select_diffraction_setup, save_diffraction_pattern
from emcd_sim.elastic import depth_coherence
from emcd_sim.voltage import ConstantMagnetization


def make_sim(condition, moment=0.6):
    setup = select_diffraction_setup(condition, fcc_nickel())
    sim = nickel_physical_benchmark(ConstantMagnetization(moment),
                                    tilt_mrad_xy=setup.tilt_mrad_xy,
                                    beams_override=setup.beams,
                                    diffraction_condition=condition)
    return setup, sim


def test_2bc_apertures_exact_transverse_thales_positions():
    g = 2 / 3.524
    for condition in ('two-beam', 'near-2bc'):
        _, sim = make_sim(condition)
        assert set(sim.detectors) == {'A', 'B'}
        for name, sign in [('A',1),('B',-1)]:
            x, y = sim.detectors[name].center_q_xy
            assert x == pytest.approx(g/2)
            assert y == pytest.approx(sign*g/2)
            # (x-g/2)^2+y^2=(g/2)^2: circle through 000 and +200.
            assert (x-g/2)**2+y*y == pytest.approx((g/2)**2)


def test_3bc_quadrant_double_difference_and_magnetic_reversal():
    _, sim = make_sim('symmetric-3bc')
    g = 2 / 3.524
    assert set(sim.detectors) == {'RU','RD','LU','LD'}
    assert sim.chiral_groups == {'A':('RU','LD'),'B':('RD','LU')}
    for name, (sx,sy) in {'RU':(1,1),'RD':(1,-1),
                          'LU':(-1,1),'LD':(-1,-1)}.items():
        assert sim.detectors[name].center_q_xy == pytest.approx((sx*g/2,sy*g/2))
    energies=np.array([852.7,870.0])
    plus=sim.run(energies,grid_size=45,depth_steps=24)
    _, simzero=make_sim('symmetric-3bc',0)
    _, simminus=make_sim('symmetric-3bc',-0.6)
    zero=simzero.run(energies,grid_size=45,depth_steps=24)
    minus=simminus.run(energies,grid_size=45,depth_steps=24)
    np.testing.assert_allclose(plus.chiral_spectrum('A'),
                               plus.detector_spectra['RU']+plus.detector_spectra['LD'])
    np.testing.assert_allclose(plus.difference(),-minus.difference(),atol=1e-11)
    assert np.max(np.abs(zero.difference())) < 1e-11
    assert np.abs(plus.asymmetry()[0]) > 1e-4
    np.testing.assert_allclose(plus.chiral_spectrum('A')+minus.chiral_spectrum('A'),
                               2*zero.chiral_spectrum('A'),atol=1e-10)


def test_reciprocal_coordinate_is_transmitted_beam_centered():
    _, sim = make_sim('symmetric-3bc')
    coh = depth_coherence(sim.elastic,30,16)
    qx=np.array([[0.25,-0.25]])
    qy=np.array([[0.25,-0.25]])
    n1,m1=sim.angular_components(852.7,coh,qx,qy)
    from emcd_sim.geometry import Microscope
    from emcd_sim.physical_elastic import PhysicalElasticModel
    # Construct a different incident tilt but hold the *same* coherence matrix.
    # An angle-dependent shift in q at this stage would be a coordinate error.
    tilted = PhysicalElasticModel(sim.elastic.crystal,Microscope(200,(11,37)),sim.elastic.beams)
    from dataclasses import replace
    n2,m2=replace(sim,elastic=tilted).angular_components(852.7,coh,qx,qy)
    np.testing.assert_allclose(n1,n2,atol=1e-12)
    np.testing.assert_allclose(m1,m2,atol=1e-12)


def test_aperture_diagram_and_metadata(tmp_path):
    setup, sim = make_sim('symmetric-3bc')
    data=save_diffraction_pattern(sim.elastic,30,tmp_path,setup,sim.detectors,sim.chiral_groups)
    assert (tmp_path/'aperture_geometry.png').stat().st_size > 1000
    assert len(data['physical_apertures']) == 4
    assert data['chiral_groups']['A'] == ('RU','LD')
