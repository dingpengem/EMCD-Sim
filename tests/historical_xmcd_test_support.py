"""Explicit relocation of the authenticated historical XMCD in disposable tests."""
from dataclasses import replace
import hashlib
from pathlib import Path


HISTORICAL_XMCD_SHA256 = 'a0e28ea6423b6c7832bb3cce6d69d71aa59336a221baeee3d2556b49ba501283'
ROOT = Path(__file__).resolve().parents[1]


def _verified_bytes(path):
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError('Historical XMCD source missing or unreadable') from exc
    if hashlib.sha256(raw).hexdigest() != HISTORICAL_XMCD_SHA256:
        raise ValueError('Historical XMCD source raw SHA256 mismatch')
    return raw


def historical_xmcd_source(directory):
    """Copy exact pinned repository bytes, never a source from local run outputs."""
    raw = _verified_bytes(ROOT / 'tests/fixtures/Ni_fm_historical_full_benchmark.xmcd')
    target = Path(directory) / 'historical-original.xmcd'
    with target.open('xb') as stream:
        stream.write(raw)
    _verified_bytes(target)
    return target.resolve()


def relocate_historical_xmcd_config(config, source):
    """Change only location; reject any different saved or supplied identity."""
    if config.model != 'xmcd' or config.source_sha256 != HISTORICAL_XMCD_SHA256:
        raise ValueError('Expected the pinned historical XMCD saved identity')
    source = Path(source).resolve()
    _verified_bytes(source)
    return replace(config, source=str(source))
