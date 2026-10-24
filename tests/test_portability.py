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
    assert __version__ == '0.6.1b3' == tomllib.loads(project.read_text(encoding='utf-8'))['project']['version']
    assert build_info()['application_version'] == __version__
    from emcd_sim import __display_version__
    assert __display_version__ == 'v0.6.1-beta.3'
    assert __display_version__ in LABEL and build_info()['display_version'] == __display_version__


def test_current_launcher_help():
    result=subprocess.run([sys.executable,"-m","emcd_sim","--help"],capture_output=True,text=True,timeout=60)
    assert result.returncode==0,result.stderr
    assert "desktop" in result.stdout and "--parallel-acceptance" in result.stdout
