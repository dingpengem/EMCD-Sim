"""Focused regression of the entrance-only tilt/thickness scan."""
import json
import numpy as np
import pytest

from emcd_sim.scan import ScanConfig, run_scan


def test_scan_y_tilt_invariance_and_2d_dependence(tmp_path):
    cfg = ScanConfig(conditions=("systematic-row", "zone-axis"),
                     tilt_x_mrad=(0.,), tilt_y_mrad=(-6., 0., 6.),
                     thickness_nm=(10., 30.), grid=25, steps=12, max_beams=13)
    output = tmp_path / "scan with spaces"
    summary = run_scan(cfg, output)
    assert summary["calculations"] == 12
    for mode in cfg.conditions:
        with np.load(output / f"scan_{mode}.npz") as data:
            assert data["difference"].shape == (1, 3, 2)
            assert np.all(np.isfinite(data["asymmetry"]))
            assert np.allclose(data["difference"], data["A"]-data["B"])
            assert np.allclose(data["asymmetry"], data["difference"]/(data["A"]+data["B"]))
            if mode == "systematic-row":
                assert np.ptp(data["difference"],axis=1).max() < 1e-10
                assert np.ptp(data["asymmetry"],axis=1).max() < 1e-10
            else:
                assert np.ptp(data["asymmetry"],axis=1).max() > 1e-3
                assert abs(data["asymmetry"][0,0,1]-data["asymmetry"][0,0,0]) > 1e-3
        assert (output / f"heatmaps_{mode}_x00.png").is_file()
        assert (output / f"reciprocal_map_{mode}.npz").is_file()
    metadata=json.loads((output / "scan_metadata.json").read_text())
    assert metadata["model"] == "entrance_only_illustrative_gaussian_mdff"
    assert not metadata["quantitative"]
    for name in ("comparison_reciprocal_maps.png", "comparison_y_tilt.png", "scan_results.csv"):
        assert (output / name).is_file()


@pytest.mark.parametrize("name,values", [
    ("conditions", ()), ("tilt_x_mrad", (0., 0.)),
    ("thickness_nm", (-10., 10.)), ("tilt_y_mrad", (2., 1.)),
])
def test_bad_scan_axes_rejected(name, values):
    with pytest.raises(ValueError):
        ScanConfig(**{name: values}).validate()
