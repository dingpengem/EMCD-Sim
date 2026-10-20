"""OS-neutral packaging, CLI, and filesystem smoke tests."""
import json
import subprocess
import sys
from pathlib import Path

from emcd_sim import __version__


def test_version_matches_source_metadata():
    import tomllib
    from emcd_sim.gui.runtime import build_info, LABEL
    project = Path(__file__).resolve().parents[1]/'pyproject.toml'
    assert __version__ == '0.6.1b2' == tomllib.loads(project.read_text(encoding='utf-8'))['project']['version']
    assert build_info()['application_version'] == __version__
    assert __version__ in LABEL and 'Beta' in LABEL


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
