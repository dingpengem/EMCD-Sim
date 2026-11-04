"""Separate reviewed extension; immutable earlier physics/unit snapshots stay intact."""
from pathlib import Path
import hashlib,json

ROOT=Path(__file__).resolve().parents[1]
EXTENSION_SHA256='fdc2775266d214ae0659cdd2e51ce29ed63e4f0cb71f84fac38357f4550551f2'


def canonical(content):return content.decode('utf-8-sig').replace('\r\n','\n').encode('utf-8')


def extension():
    raw=(ROOT/'tests/fixtures/single_element_scope_v1.json').read_bytes()
    assert hashlib.sha256(canonical(raw)).hexdigest()==EXTENSION_SHA256,'Unreviewed single-element source scope'
    d=json.loads(raw)
    assert d['base']=='2f9c130099dce5df4e4609b521c42f53c5385518'
    assert d['physics_convention']=='forward_born_dagger_g_minus_h_v1'
    return d['canonical_sha256']


def legacy_kernel_source(path,content):
    """Remove only the exact opt-in site plumbing; hash the original default kernel.

    Full current-file hashes are checked separately. No formula, phase sign,
    conjugation, quadrature or accumulation expression is normalized here.
    """
    text=canonical(content).decode('utf-8')
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
