"""Optional desktop interface; importing the core package never imports Qt."""


def main():
    try:
        from .app import main as launch
    except ModuleNotFoundError as exc:
        if exc.name in ('PySide6','ase'):
            raise SystemExit('Desktop dependencies are optional. Install with: python -m pip install -e ".[gui]"') from exc
        raise
    return launch()
