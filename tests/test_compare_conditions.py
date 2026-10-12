"""Focused tests for multi-condition EMCD reciprocal-space maps."""
import json
import numpy as np
import pytest
from emcd_sim.compare_conditions import CONDITIONS, calculate_maps, save_comparison


def test_condition_maps_are_comparable_and_have_correct_apertures():
    maps = calculate_maps(grid=15,depth_steps=8,max_beams=13,thickness_nm=15)
    assert tuple(maps) == CONDITIONS
    for cond,item in maps.items():
        assert item["magnetic"].shape == (15,15)
        assert item["nonmagnetic"].shape == (15,15)
        assert np.isfinite(item["magnetic"]).all()
        assert np.isfinite(item["A"]) and np.isfinite(item["B"])
        assert np.all(item["nonmagnetic"] >= -1e-7)
        assert len(item["apertures"]) == (4 if cond=="symmetric-3bc" else 2)
    np.testing.assert_array_equal(maps["two-beam"]["qx"],maps["zone-axis"]["qx"])
    assert len(maps["two-beam"]["beam_hkl"]) == 2
    assert len(maps["zone-axis"]["beam_hkl"]) == 13


def test_save_plot_and_machine_readable_outputs(tmp_path):
    maps=calculate_maps(grid=15,depth_steps=8,max_beams=13,thickness_nm=15)
    save_comparison(maps,tmp_path,thickness_nm=15.,acceleration_kv=200.,b_factor=0.,grid=15,depth_steps=8)
    assert (tmp_path/"emcd_diffraction_conditions.png").is_file()
    metadata=json.loads((tmp_path/"comparison_metadata.json").read_text())
    assert metadata["quantitative"] is False
    assert len(metadata["conditions"]["symmetric-3bc"]["apertures"]) == 4
    with np.load(tmp_path/"emcd_condition_maps.npz") as d:
        assert d["zone_axis_magnetic"].shape==(15,15)
        assert d["two_beam_magnetic_over_nonmagnetic"].shape==(15,15)


def test_bad_args_rejected():
    with pytest.raises(ValueError):
        calculate_maps(grid=7)
