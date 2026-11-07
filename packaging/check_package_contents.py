"""Offline, pinned packaging inputs and post-collection distribution checks.

Updating a pin is a separate reviewed packaging scope change, never a build step.
"""
import argparse
import hashlib
import json
from importlib.metadata import version
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = 'packaging/assets/required-content.json'
MANIFEST_SHA256 = 'c8e183f56d4675ea110df11aff9f5c27f31ee55951f2906148df8e2d47e6634a'
QT_VERSIONS = {name: '6.12.0' for name in
               ('PySide6', 'PySide6_Essentials', 'PySide6_Addons', 'shiboken6')}
QT_VERSIONS.update(PySide6_Pdf='6.12.0.140', PySide6_WebEngine='6.12.0.140')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def checked_file(root, path, digest):
    name = PurePosixPath(path)
    if name.is_absolute() or '..' in name.parts or '\\' in path:
        raise ValueError('Unsafe required-content path: '+path)
    file = root/path
    if not file.resolve().is_relative_to(root.resolve()) or not file.is_file():
        raise ValueError('Missing required packaging content: '+path)
    if sha(file.read_bytes()) != digest:
        raise ValueError('Changed required packaging content: '+path)
    return file


def inputs(root=ROOT):
    manifest = checked_file(root, MANIFEST, MANIFEST_SHA256)
    data = json.loads(manifest.read_bytes())
    if set(data) != {'schema', 'files'} or data['schema'] != 1:
        raise ValueError('Unsupported required-content manifest')
    for path, entry in data['files'].items():
        checked_file(root, path, entry['sha256'])
    return data['files']


def check_environment():
    for name, expected in QT_VERSIONS.items():
        if version(name) != expected:
            raise ValueError('Unreviewed Qt distribution: '+name+' (expected '+expected+')')


def datas(root=ROOT):
    """Explicit per-file PyInstaller data entries; never sweep output folders."""
    entries = inputs(root)
    return [(str(root/path), str(PurePosixPath(entry['destination']).parent).removeprefix('_internal/'))
            for path, entry in entries.items()] + [(str(root/MANIFEST), 'licenses/qt')]


def validate_distribution(dist, root=ROOT):
    from windows_dependencies import system_runtime
    runtime_copies = sorted(p.relative_to(dist).as_posix() for p in dist.rglob('*.dll')
                            if system_runtime(p.name))
    if runtime_copies:
        raise ValueError('App-local Microsoft runtimes must not be distributed: '+str(runtime_copies))
    entries = inputs(root)
    checked_file(dist, '_internal/licenses/qt/required-content.json', MANIFEST_SHA256)
    for path, entry in entries.items():
        checked_file(dist, entry['destination'], entry['sha256'])
    baseline = json.loads((root/'packaging/assets/bundled-qt-components.json').read_bytes())
    expected = {entry['path']: entry['sha256'] for entry in
                baseline['components'] + baseline['translations']}
    actual = {p.relative_to(dist).as_posix()
              for directory in ('_internal/PySide6', '_internal/shiboken6')
              for p in (dist/directory).rglob('*') if p.is_file()}
    if actual != set(expected):
        raise ValueError('Unreviewed Qt component inventory: missing='+str(sorted(set(expected)-actual))
                         +' extra='+str(sorted(actual-set(expected))))
    for path, digest in expected.items():
        checked_file(dist, path, digest)
    return {'required_assets': len(entries),
            'qt_binary_components': len(baseline['components']),
            'qt_translation_catalogs': len(baseline['translations'])}


def source_packages(source_root, root=ROOT):
    inputs(root)
    provenance = json.loads((root/'packaging/assets/qt-licenses/upstream-provenance.json').read_bytes())
    packages = provenance['source_packages']
    for entry in packages:
        checked_file(source_root, entry['filename'], entry['sha256'])
    return packages


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dist', type=Path)
    parser.add_argument('--environment', action='store_true')
    parser.add_argument('--source-root', type=Path)
    args = parser.parse_args()
    try:
        if args.environment:
            check_environment()
        if args.source_root:
            source_packages(args.source_root)
        result = validate_distribution(args.dist) if args.dist else {'required_assets': len(inputs())}
    except (OSError, ValueError) as error:
        parser.exit(1, str(error)+'\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
