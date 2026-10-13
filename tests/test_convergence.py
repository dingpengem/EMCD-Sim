"""Focused basis-convergence workflow tests (no numerical convergence claim)."""
import json
import numpy as np
import pytest

from emcd_sim.convergence import ConvergenceConfig, run_convergence, _total_variation


def test_total_variation_matches_missing_and_common_intensity():
    assert _total_variation([(0,0,0),(2,0,0)], [0.5,0.5],
                            [(0,0,0)], [1.0]) == pytest.approx(0.5)
    assert _total_variation([(0,0,0),(2,0,0)], [0.5,0.5],
                            [(2,0,0),(0,0,0)], [0.5,0.5]) == pytest.approx(0)


def test_config_rejects_broken_cutoffs():
    with pytest.raises(ValueError):
        ConvergenceConfig(g_cutoffs_inv_angstrom=(1.2,1.2)).validate()
    with pytest.raises(ValueError):
        ConvergenceConfig(max_beams=2).validate()


def test_finite_basis_scan_and_files(tmp_path):
    output = tmp_path / "convergence with spaces"
    cfg = ConvergenceConfig(conditions=("zone-axis", "near-2bc"),
        g_cutoffs_inv_angstrom=(0.75,1.2), thickness_nm=(10.,30.),
        reciprocal_grid=25,depth_steps=5,max_beams=25)
    summary=run_convergence(cfg, output)
    assert summary["beam_counts"]==[5,13]
    assert summary["calculations"]==8
    assert summary["max_elastic_norm_error"]<1e-11
    assert summary["reference_is_finite_not_validated"]
    for name in ("convergence_results.csv","convergence_results.npz",
                 "convergence_metadata.json","basis_convergence.png"):
        assert (output/name).is_file()
    with np.load(output/"convergence_results.npz",allow_pickle=False) as d:
        assert d["emcd_asymmetry"].shape==(2,2,2)
        np.testing.assert_allclose(d["elastic_total_variation"][:,-1],0,atol=1e-12)
        assert np.max(np.abs(d["total_elastic"]-1))<1e-11
    meta=json.loads((output/"convergence_metadata.json").read_text())
    assert meta["reference_is_finite_not_validated"] is True
    assert meta["incident_tilt_mrad_by_condition"]["near-2bc"][0]<0
