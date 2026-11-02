"""Fail early when declared Windows build/license metadata is unavailable."""
from importlib.metadata import PackageNotFoundError, distribution
import json
import sys


LICENSE_DISTRIBUTIONS = (
    'numpy', 'scipy', 'matplotlib', 'ase', 'PySide6', 'PySide6_Essentials',
    'PySide6_Addons', 'shiboken6', 'pillow', 'contourpy', 'cycler', 'fonttools',
    'kiwisolver', 'packaging', 'pyparsing', 'python-dateutil', 'six',
)
REQUIRED_DISTRIBUTIONS = LICENSE_DISTRIBUTIONS + ('pyinstaller',)


class MissingBuildMetadata(RuntimeError):
    pass


def require_metadata():
    found = {}
    missing = []
    errors = []
    for name in REQUIRED_DISTRIBUTIONS:
        try:
            found[name] = distribution(name)
        except PackageNotFoundError as error:
            missing.append(name)
            errors.append(error)
    if missing:
        raise MissingBuildMetadata(
            'Missing Windows build distribution metadata: ' + ', '.join(missing)
            + '. Install into the selected build interpreter with: '
            + sys.executable + ' -m pip install -e ".[dev,gui]" '
            + '-r packaging/requirements-windows.txt'
        ) from errors[0]
    return found


def main():
    try:
        found = require_metadata()
    except MissingBuildMetadata as error:
        print(str(error))
        return 1
    print('Windows build metadata preflight passed:')
    print(json.dumps({name: dist.version for name, dist in found.items()}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
