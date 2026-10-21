"""Relocated frontends remain importable/runnable without scientific execution."""
from pathlib import Path
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('name', [
    'atomic_slicing_diagnostics', 'fractional_aperture_validation',
    'plot_wien2k_xmcd', 'plot_wien2k_xmcd_suite',
])
def test_relocated_cli_help(name):
    script = ROOT/'scripts/research'/f'{name}.py'
    result = subprocess.run([sys.executable, str(script), '--help'], cwd=ROOT,
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    assert 'usage:' in result.stdout.lower()


def test_comparison_import_does_not_run_research():
    # This driver has no argparse help mode; import it without executing main.
    script = ROOT/'scripts/research/ni_017_comparison.py'
    code = "import runpy; ns=runpy.run_path("+repr(str(script))+"); assert callable(ns['compare']); assert callable(ns['export_normalized_pairs'])"
    result = subprocess.run([sys.executable, '-c', code], cwd=ROOT,
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
