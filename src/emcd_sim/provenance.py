"""Source/frozen asset locations and recorded scientific build provenance.

Frozen metadata is returned unchanged. Source mode retains existing inventory
keys and adds the moved scientific geometry owner to preserve traced coverage.
"""
from pathlib import Path
import hashlib,json,subprocess,sys
from . import __version__, __display_version__


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
    return Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[2]


def reference_source():
    return resource_root() / 'data/wien2k_ni/Ni_fm.xmcd'


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
                implementation_sha256={p: hashlib.sha256((Path(__file__).with_name(p) if p=='structure_geometry.py' else Path(__file__).parent/'gui'/p).read_bytes()).hexdigest()
                                       for p in ('forward_pipeline.py', 'geometry.py', 'propagation.py', 'channeling.py', 'result_export.py', 'structure_geometry.py')})
