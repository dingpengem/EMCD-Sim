"""OS-neutral packaging, CLI, and filesystem smoke tests."""
import json
import subprocess
import sys

from emcd_sim import __version__


def test_version_matches_public_release():
    assert __version__ == "0.3.2"


def test_module_entrypoint_writes_outputs_into_path_with_spaces(tmp_path):
    output = tmp_path / "Ni 2BC results"
    result = subprocess.run(
        [sys.executable, "-m", "emcd_sim",
         "--diffraction-condition", "two-beam",
         "--diffraction-only", "--output", str(output)],
        capture_output=True, text=True, check=True, timeout=90,
    )
    assert json.loads(result.stdout)["condition"] == "two-beam"
    for name in ("diffraction_pattern.png", "diffraction_pattern.npz",
                 "diffraction_spots.csv", "metadata.json"):
        assert (output / name).is_file()
    assert json.loads((output / "metadata.json").read_text(encoding="utf-8"))["mdff_computed"] is False
