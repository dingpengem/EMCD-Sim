"""Desktop writable-data paths and logging; scientific provenance has a neutral owner."""
from ..provenance import build_info
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
import os
import platform
import sys
import faulthandler

_native_fault_file=None










def user_directory():
    base = Path(os.environ.get('LOCALAPPDATA', str(Path.home() / '.local/share')))
    return base / 'EMCD-Sim'


def workspace():
    return Path(os.environ.get('EMCD_GUI_WORKSPACE', str(user_directory() / 'workspace')))




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
