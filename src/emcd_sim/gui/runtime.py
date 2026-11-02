"""Small source/frozen resource, provenance and writable-data boundary."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import platform
import subprocess
import sys
import faulthandler

_native_fault_file=None

from .. import __version__, __display_version__

LABEL = f'EMCD-Sim {__display_version__} - Double-Channeling EMCD Simulation'
PHYSICS_CONVENTION = 'forward_born_dagger_g_minus_h_v1'


def result_convention_status(metadata):
    """Interpret recorded provenance without stamping old arrays as current."""
    value = metadata.get('physics_convention')
    if value == PHYSICS_CONVENTION:
        return dict(identifier=value, status='recorded-corrected', warning=None)
    if value:
        return dict(identifier=value, status='recorded-other', warning=(
            'Saved physics convention '+str(value)+' differs from the current forward-Born convention. '
            'Raw arrays and original provenance are preserved; revalidate signed magnetic EMCD before interpretation.'))
    return dict(identifier=None, status='unknown-or-legacy-unverified', warning=(
        'Saved physics convention is unknown or legacy-unverified. Raw arrays and original source/version '
        'identifiers are preserved; do not interpret signed magnetic EMCD as corrected without revalidation.'))


def resource_root():
    return Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[3]


def reference_source():
    return resource_root() / 'data/wien2k_ni/Ni_fm.xmcd'


def user_directory():
    base = Path(os.environ.get('LOCALAPPDATA', str(Path.home() / '.local/share')))
    return base / 'EMCD-Sim'


def workspace():
    return Path(os.environ.get('EMCD_GUI_WORKSPACE', str(user_directory() / 'workspace')))


def build_info():
    if getattr(sys, 'frozen', False):
        return json.loads((resource_root() / 'build_info.json').read_text(encoding='utf-8'))
    root = resource_root()
    try:
        commit = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True, stderr=subprocess.DEVNULL).strip()
        dirty = bool(subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain'], text=True, stderr=subprocess.DEVNULL))
    except (OSError, subprocess.CalledProcessError):
        commit, dirty = 'unknown', None
    return dict(label=LABEL, application_version=__version__, display_version=__display_version__, commit=commit, dirty=dirty, build_utc=None,
                physics_convention=PHYSICS_CONVENTION,
                implementation_sha256={p: hashlib.sha256(Path(__file__).with_name(p).read_bytes()).hexdigest()
                                       for p in ('emcd_forward.py', 'geometry.py', 'propagation.py')})


def configure_logging():
    global _native_fault_file
    logger = logging.getLogger('emcd_sim.gui')
    if not logger.handlers:
        folder = user_directory() / 'logs'
        folder.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(folder / 'runtime.log', maxBytes=2_000_000, backupCount=2, encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        if _native_fault_file is None:
            try:
                _native_fault_file=(folder/f'native_fault_{os.getpid()}.log').open('ab',buffering=0)
                faulthandler.enable(file=_native_fault_file,all_threads=True)
            except (OSError,RuntimeError):logger.warning('Native fault trace file could not be enabled',exc_info=True)
        logger.info('Build %s; platform=%s Python=%s', build_info(), platform.platform(), platform.python_version())
        previous = sys.excepthook
        def unhandled(kind, value, tb):
            logger.error('Unhandled application error', exc_info=(kind, value, tb))
            previous(kind, value, tb)
        sys.excepthook = unhandled
    return logger
