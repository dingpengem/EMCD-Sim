"""Explicit versioned guard: register approved changes, never self-update."""
from pathlib import Path
import hashlib
import json
import base64
import zlib

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path(__file__).parent/'fixtures/physics_source_manifest_v1.json'
CONVENTION = 'forward_born_dagger_g_minus_h_v1'
CURRENT_KERNEL_BASE='cdb8836388c5ccc5ae7a614b47894c0ab158a824'
# Exact complete pre-refactor kernels, read from CURRENT_KERNEL_BASE rather
# than regenerated from the candidate. Ordinary UI registration cannot approve
# changed kernels. Original convention-version identities remain below.
CURRENT_KERNELS={
    'src/emcd_sim/single_channeling_tensor.py':'3a4767dd7b390be137670dc054c84570f34733b3c0338d47474670b6204b206e',
    'src/emcd_sim/double_channeling.py':'687955a3bdf9ac15db7a806c3e2f14d86a5ba0535134798fb4967ea0c254c5aa',
    'src/emcd_sim/multislice_double_channeling.py':'06fa30e2c969a1c669ead3b91d84516832126e71be8b09054e293625c14435a8',
}


def canonical_sha256(content):
    text = content.decode('utf-8-sig').replace('\r\n', '\n')
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def recorded_kernel_sources():
    """Exact pre-generalization source, not a reconstruction of current code."""
    from mdff_usability_source_scope import readability_scope
    scope,_=readability_scope()
    return {path:zlib.decompress(base64.b85decode(content)) for path,content in scope['legacy_kernels'].items()}


def assert_registered_sources(overrides=None):
    from single_element_source_guard import assert_current_extension
    # The complete current files, including grouping, buffers and admission,
    # retain their strict versioned identities. Original convention pins below
    # authenticate the actual recorded kernel version, without rewriting code.
    assert_current_extension(overrides)
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    assert manifest['schema'] == 1 and manifest['active'] == CONVENTION
    historical=recorded_kernel_sources()
    for name, item in manifest['versions'][CONVENTION]['files'].items():
        content=(overrides or {}).get(name)
        if content is None:content=(ROOT/name).read_bytes()
        assert canonical_sha256(content)==CURRENT_KERNELS[name],(
            f'Unregistered physics change: {name}; current kernel differs from the frozen pre-refactor source')
        assert canonical_sha256(historical[name]) == item['canonical_sha256'], (
            f'Unregistered physics change: {name}; review physics and register a new convention/version explicitly')
    return manifest
