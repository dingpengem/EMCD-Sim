"""Separate reviewed extension; immutable earlier physics/unit snapshots stay intact."""
from pathlib import Path
import hashlib,json

ROOT=Path(__file__).resolve().parents[1]
EXTENSION_SHA256='0599a74e3b48d4182b34bd7f91c9ac7b62bf7e3cb4fb2817e348f288f343fc76'


ATOMIC_EXTENSION_SHA256='5bd0ecb4f65c7ca713179b8b9f652d8cc47e8ceae6f0e4ceaab5d492980ec302'
REFACTOR_SHA256='ed5acc0cb5583b7b3988436c59aa59a297e307003395289e2772174a1399ff16'
CONSOLIDATION_SHA256='e49f4392817744babe6dcca42ecf983f82f4d885f1356740e9e346775e7720d3'


def canonical(content):return content.decode('utf-8-sig').replace('\r\n','\n').encode('utf-8')


def extension():
    raw=(ROOT/'tests/fixtures/single_element_scope_v1.json').read_bytes()
    assert hashlib.sha256(canonical(raw)).hexdigest()==EXTENSION_SHA256,'Unreviewed single-element source scope'
    d=json.loads(raw)
    assert d['base']=='2f9c130099dce5df4e4609b521c42f53c5385518'
    assert d['physics_convention']=='forward_born_dagger_g_minus_h_v1'
    raw=(ROOT/'tests/fixtures/atomic_ionization_scope_v1.json').read_bytes()
    assert hashlib.sha256(canonical(raw)).hexdigest()==ATOMIC_EXTENSION_SHA256,'Unreviewed atomic-ionization source scope'
    atomic=json.loads(raw)
    assert atomic['schema']==1 and atomic['base']=='237944148151d784b6b2e3597e853dbc32779bd0'
    assert atomic['physics_convention']==d['physics_convention']
    raw=(ROOT/'tests/fixtures/unified_mdff_scope_v1.json').read_bytes()
    assert hashlib.sha256(canonical(raw)).hexdigest()==CONSOLIDATION_SHA256,'Unreviewed MDFF consolidation source scope'
    consolidation=json.loads(raw)
    assert consolidation['schema']==1 and consolidation['base']=='52b36ee41e20aed5a86fb37db56ca372fac936f8'
    assert consolidation['physics_convention']==d['physics_convention']
    # Additive Part 1C scope: historical manifests remain immutable.
    raw=(ROOT/'tests/fixtures/part1c_refactor_scope_v1.json').read_bytes()
    assert hashlib.sha256(canonical(raw)).hexdigest()==REFACTOR_SHA256,'Unreviewed Part 1C source scope'
    refactor=json.loads(raw)
    assert refactor['base']=='133c3da6e69d633b0e1ea61a4de8005820885bbb'
    reviewed=dict(d['canonical_sha256'],**dict(atomic['canonical_sha256'],
        **dict(consolidation['canonical_sha256'],**refactor['canonical_sha256'])))
    for path in refactor['removed_modules']:
        assert not (ROOT/path).exists(),'Retired production module reintroduced: '+path
        reviewed.pop(path,None)
    return reviewed



def legacy_kernel_source(path,content):
    """Remove only the exact opt-in site plumbing; hash the original default kernel.

    Full current-file hashes are checked separately. No formula, phase sign,
    conjugation, quadrature or accumulation expression is normalized here.
    """
    text=canonical(content).decode('utf-8')
    if path.endswith('/single_channeling_tensor.py'):
        text=text.replace('from .ionization_sites import single_site_phase_matrix\n','')
        text=text.replace('    return single_site_phase_matrix(hkl, positions)',
            '    phase = np.exp(2j * np.pi * (hkl[:, None, :] - hkl[None, :, :]) @ positions.T)\n    return phase.mean(axis=-1)')
    if path.endswith('/double_channeling.py'):
        text=text.replace('cancelled=None,ionization_sites=None):','cancelled=None):')
        text=text.replace("if ionization_sites is None and not all(s == 'Ni'", "if not all(s == 'Ni'")
        text=text.replace('elastic.crystal.fractional_positions if ionization_sites is None else ionization_sites.positions_for(elastic.crystal)','elastic.crystal.fractional_positions')
    if path.endswith('/multislice_double_channeling.py'):
        text=text.replace('cancelled=None,ionization_sites=None):','cancelled=None):')
        text=text.replace('elastic.crystal.fractional_positions if ionization_sites is None else ionization_sites.positions_for(elastic.crystal)','elastic.crystal.fractional_positions')
    return text.encode('utf-8')


def assert_current_extension(overrides=None):
    for path,digest in extension().items():
        raw=(overrides or {}).get(path)
        if raw is None:raw=(ROOT/path).read_bytes()
        assert hashlib.sha256(canonical(raw)).hexdigest()==digest,'Unregistered physics change: '+path
