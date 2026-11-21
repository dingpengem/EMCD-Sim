"""Build-only metadata guards: no scientific imports or calculations."""
from pathlib import Path
from types import SimpleNamespace
import importlib.util
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('windows_build_metadata', ROOT/'packaging/check_windows_metadata.py')
metadata = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metadata)


def test_all_metadata_is_reported_without_importing_runtime(monkeypatch, capsys):
    calls = []
    def lookup(name):
        calls.append(name)
        return SimpleNamespace(version='1.0')
    monkeypatch.setattr(metadata, 'distribution', lookup)
    assert metadata.main() == 0
    assert calls == list(metadata.REQUIRED_DISTRIBUTIONS)
    assert '"six": "1.0"' in capsys.readouterr().out


def test_missing_metadata_lists_every_missing_package_and_keeps_cause(monkeypatch):
    def lookup(name):
        if name in {'six', 'ase'}:
            raise metadata.PackageNotFoundError(name)
        return SimpleNamespace(version='1.0')
    monkeypatch.setattr(metadata, 'distribution', lookup)
    with pytest.raises(metadata.MissingBuildMetadata, match='ase, six') as caught:
        metadata.require_metadata()
    assert isinstance(caught.value.__cause__, metadata.PackageNotFoundError)
    assert 'requirements-windows.txt' in str(caught.value)


def test_cli_missing_metadata_is_a_failure(monkeypatch, capsys):
    def missing(name):
        raise metadata.PackageNotFoundError(name)
    monkeypatch.setattr(metadata, 'distribution', missing)
    assert metadata.main() == 1
    message = capsys.readouterr().out
    assert 'Missing Windows build distribution metadata' in message
    assert 'six' in message and 'pyinstaller' in message


def test_corrupt_metadata_is_not_suppressed(monkeypatch):
    def broken(name):
        raise ValueError('corrupt metadata')
    monkeypatch.setattr(metadata, 'distribution', broken)
    with pytest.raises(ValueError, match='corrupt metadata'):
        metadata.require_metadata()


def test_build_additions_preserve_existing_scientific_versions():
    def pins(text):
        return dict(line.split('==') for line in text.splitlines() if line and not line.startswith('#'))
    baseline = subprocess.check_output(['git','show','c10190c:packaging/requirements-windows.txt'], cwd=ROOT).decode()
    current = pins((ROOT/'packaging/requirements-windows.txt').read_text())
    assert current == dict(pins(baseline), six='1.17.0', spglib='2.7.0')


def test_spec_shares_license_inventory_and_preflight_precedes_pyinstaller():
    source = (ROOT/'packaging/emcd_gui.spec').read_text()
    assert 'for package in LICENSE_DISTRIBUTIONS:' in source
    assert 'checked_distributions = require_metadata()' in source
    assert source.index('require_metadata()') < source.index('a = Analysis(')
    script = (ROOT/'packaging/build_windows.ps1').read_text()
    assert script.index('check_windows_metadata.py') < script.index('-m PyInstaller')
    assert 'pyinstaller' in metadata.REQUIRED_DISTRIBUTIONS
    assert len(metadata.LICENSE_DISTRIBUTIONS) == 19
    assert {'spglib','typing_extensions'} <= set(metadata.LICENSE_DISTRIBUTIONS)
