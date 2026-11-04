"""Explicit versioned guard: register approved changes, never self-update."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path(__file__).parent/'fixtures/physics_source_manifest_v1.json'
CONVENTION = 'forward_born_dagger_g_minus_h_v1'


def canonical_sha256(content):
    text = content.decode('utf-8-sig').replace('\r\n', '\n')
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def assert_registered_sources(overrides=None):
    from single_element_source_guard import assert_current_extension,legacy_kernel_source
    assert_current_extension(overrides)
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    assert manifest['schema'] == 1 and manifest['active'] == CONVENTION
    for name, item in manifest['versions'][CONVENTION]['files'].items():
        content = (overrides or {}).get(name)
        if content is None:
            content = (ROOT/name).read_bytes()
        assert canonical_sha256(legacy_kernel_source(name,content)) == item['canonical_sha256'], (
            f'Unregistered physics change: {name}; review physics and register a new convention/version explicitly')
    return manifest
