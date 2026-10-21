"""Supported launch/import surfaces and packaging dependencies after source cleanup."""
import ast
import importlib
from pathlib import Path
import subprocess
import sys
import tomllib

ROOT=Path(__file__).resolve().parents[1]


def test_supported_console_interfaces():
    entries=tomllib.loads((ROOT/'pyproject.toml').read_text())['project']['scripts']
    assert set(entries)=={'emcd-gui','emcd-import-transitions','emcd-ni-local-mdff'}
    for target in entries.values():
        module,name=target.split(':')
        assert callable(getattr(importlib.import_module(module),name))
        result=subprocess.run([sys.executable,'-m',module,'--help'],capture_output=True,text=True,timeout=60)
        assert result.returncode==0,result.stderr


def test_packaging_hiddenimports_resolve_without_building():
    tree=ast.parse((ROOT/'packaging/emcd_gui.spec').read_text())
    imports=next(k.value for n in ast.walk(tree) if isinstance(n,ast.Call)
        and isinstance(n.func,ast.Name) and n.func.id=='Analysis'
        for k in n.keywords if k.arg=='hiddenimports')
    for name in ast.literal_eval(imports):importlib.import_module(name)


def test_package_public_exports_resolve_without_qt_launch():
    import emcd_sim
    for name in emcd_sim.__all__:assert getattr(emcd_sim,name) is not None
