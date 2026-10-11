"""Focused geometry, indexing and output tests for v0.3 diffraction conditions."""
import csv
import numpy as np
import pytest
from emcd_sim.crystal import fcc_nickel
from emcd_sim.diffraction import (
    select_diffraction_setup, bragg_tilt_mrad,
    excitation_errors_angstrom_inv, save_diffraction_pattern,
)
from emcd_sim.geometry import Microscope
from emcd_sim.physical_elastic import PhysicalElasticModel


def make_model(condition):
    ni = fcc_nickel()
    setup = select_diffraction_setup(condition, ni, acceleration_kv=200, max_beams=13)
    return setup, PhysicalElasticModel(ni, Microscope(200, setup.tilt_mrad_xy), setup.beams)


def test_two_beam_bragg_condition():
    setup, elastic = make_model("two-beam")
    assert elastic.beams.hkl == ((0,0,0), (2,0,0))
    assert setup.tilt_mrad_xy[0] == pytest.approx(-bragg_tilt_mrad(elastic.crystal, (2,0,0), 200))
    assert excitation_errors_angstrom_inv(elastic)[1] == pytest.approx(0, abs=1e-13)


def test_near_two_beam_retains_higher_order_row():
    setup, elastic = make_model("near-2bc")
    assert len(elastic.beams.hkl) == 7
    s = excitation_errors_angstrom_inv(elastic)
    assert s[1] == pytest.approx(0, abs=1e-13)
    assert abs(s[2]) > abs(s[1]) + .005


def test_three_beam_symmetric_excitation_and_offzone_tilt():
    setup, elastic = make_model("symmetric-3bc")
    s = excitation_errors_angstrom_inv(elastic)
    assert s[1] == pytest.approx(s[2], abs=1e-14)
    assert setup.tilt_mrad_xy == (0.0, 25.0)
    assert s[1] > 0


def test_zone_axis_spots_and_friedel_pairs():
    setup, elastic = make_model("zone-axis")
    beams = set(elastic.beams.hkl)
    assert (2,0,0) in beams and (0,2,0) in beams and (2,2,0) in beams
    assert len(beams) == 13
    for hkl in beams:
        assert tuple(-x for x in hkl) in beams
    assert setup.tilt_mrad_xy == (0.0,0.0)


def test_export_spot_index_and_elastic_conservation(tmp_path):
    setup, elastic = make_model("zone-axis")
    result = save_diffraction_pattern(elastic,30.0,tmp_path,setup)
    assert result["nominal_zone_axis_hkl"] == [0,0,1]
    assert result["elastic_total_intensity"] == pytest.approx(1.0, abs=1e-12)
    assert (tmp_path/"diffraction_pattern.png").stat().st_size > 1000
    a = np.load(tmp_path/"diffraction_pattern.npz")
    assert a["beam_hkl"].shape == (13,3)
    assert len(a["elastic_intensity"]) == 13
    with (tmp_path/"diffraction_spots.csv").open() as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 13
    assert any((r["h"],r["k"],r["l"]) == ("2","2","0") for r in rows)


def test_incompatible_cutoff_rejected():
    with pytest.raises(ValueError, match="incompatible"):
        select_diffraction_setup("near-2bc",fcc_nickel(),zone2d_max_g=1.2)
