"""Proposed additive packaging scope; historical editor evidence is immutable.

This loader and its pins are review bootstrap infrastructure, authenticated by
the independently reviewed complete patch, not by a self-reported manifest hash.
"""
import hashlib
import io
import json
from pathlib import PurePosixPath
import zipfile

MANIFEST_PATH = 'tests/fixtures/packaging_content_scope_v1.json'
ARCHIVE_PATH = 'tests/fixtures/packaging_content_parent_v1.zip'
MANIFEST_SHA256='f5584f72a60cf82d2669c0d00291f34a7643db0be7a5312704257afc0f2c6dac'
ARCHIVE_SHA256 = '017093f5788b1f83d34091679a7802e253220213a056cb05b35d2a6e2164e54b'
PARENT = '3609dfc762749024a3c6726c3763ef33f3e46482'
MODIFIED = ('packaging/BETA_README.txt', 'packaging/README.md',
            'packaging/build_windows.ps1', 'packaging/emcd_gui.spec',
            'pyproject.toml', 'src/emcd_sim/__init__.py', 'packaging/windows_version_info.txt',
            'tests/mdff_editor_source_scope.py', 'tests/test_mdff_editor_source_scope.py')
ADDED_INFRASTRUCTURE = ('packaging/check_package_contents.py',
                        'packaging/windows_dependencies.py',
                        'tests/test_packaging_contents.py',
                        'tests/test_packaging_content_source_scope.py',
                        'docs/PACKAGING_CONTENT_SCOPE.md')


def canonical(raw):
    return raw.decode('utf-8-sig').replace('\r\n', '\n').encode('utf-8')


def digest(raw, mode='canonical'):
    return hashlib.sha256(raw if mode == 'raw' else canonical(raw)).hexdigest()


def read(root, path, overrides=None):
    name = PurePosixPath(path)
    assert not name.is_absolute() and '..' not in name.parts and '\\' not in path, 'Unsafe packaging scope path: '+path
    assert (root/path).resolve().is_relative_to(root.resolve()), 'Packaging scope path outside root: '+path
    if overrides is not None and path in overrides:
        return overrides[path]
    try:
        return (root/path).read_bytes()
    except OSError as error:
        raise AssertionError('Missing packaging scope path: '+path) from error


def unique(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result, 'Duplicate packaging scope key: '+key
        result[key] = value
    return result


def load(root, overrides=None):
    raw = read(root, MANIFEST_PATH, overrides)
    assert digest(raw) == MANIFEST_SHA256, 'Unreviewed packaging scope manifest: '+MANIFEST_PATH
    scope = json.loads(raw, object_pairs_hook=unique)
    assert set(scope) == {'schema', 'parent_commit', 'modified', 'added', 'parent_files'}, 'Unsupported packaging scope'
    assert type(scope['schema']) is int and scope['schema'] == 1 and scope['parent_commit'] == PARENT, 'Packaging scope parent/schema mismatch'
    assert set(scope['modified']) == set(MODIFIED) == set(scope['parent_files']), 'Unauthorized packaging modified paths'
    assert set(ADDED_INFRASTRUCTURE) <= set(scope['added']), 'Missing packaging infrastructure'
    assert all(p in ADDED_INFRASTRUCTURE or p.startswith('packaging/assets/') for p in scope['added']), 'Unauthorized packaging additions'
    raw = read(root, ARCHIVE_PATH, overrides)
    assert digest(raw, 'raw') == ARCHIVE_SHA256, 'Unreviewed packaging parent archive: '+ARCHIVE_PATH
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        assert len(archive.namelist()) == len(set(archive.namelist())) and set(archive.namelist()) == set(MODIFIED), 'Unauthorized packaging archive inventory'
        for path, entry in scope['parent_files'].items():
            content = archive.read(path)
            assert set(entry) == {'raw_sha256', 'canonical_sha256', 'git_blob'}, 'Unsupported packaging parent entry'
            assert digest(content, 'raw') == entry['raw_sha256'] and digest(content) == entry['canonical_sha256'], 'Packaging parent identity mismatch: '+path
            assert hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest() == entry['git_blob'], 'Packaging parent blob mismatch: '+path
    current = {**scope['modified'], **scope['added']}
    for path, entry in current.items():
        assert set(entry) == {'mode', 'sha256', 'canonical_sha256'}, 'Unsupported packaging candidate entry: '+path
        assert entry['mode'] == ('raw' if path.startswith('packaging/assets/') else 'canonical'), 'Packaging byte contract mismatch: '+path
        content = read(root, path, overrides)
        assert digest(content, entry['mode']) == entry['sha256'], 'Unreviewed packaging source: '+path
        if entry['mode'] == 'canonical':
            assert digest(content) == entry['canonical_sha256'], 'Packaging canonical identity mismatch: '+path
    return scope


def support_paths(root, overrides=None):
    scope = load(root, overrides)
    return set(scope['modified']) | set(scope['added']) | {
        MANIFEST_PATH, ARCHIVE_PATH, 'tests/packaging_content_source_scope.py'}
