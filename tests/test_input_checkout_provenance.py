"""Exact registered input bytes survive index storage and fresh Git checkout.

Use disposable repositories and indexes only; no commits or production Git
configuration changes. Numerical equality cannot replace either byte identity.
"""
from pathlib import Path
import hashlib
import json
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('autocrlf', ['true', 'false'])
def test_registered_input_bytes_in_index_and_fresh_checkout(tmp_path, autocrlf):
    manifest = json.loads((ROOT/'tests/fixtures/ni_xmcd_provenance_v1.json').read_text())
    files = {
        manifest['canonical_package']['path']: manifest['canonical_package']['sha256'],
        'tests/fixtures/'+manifest['historical']['fixture']: manifest['historical']['sha256'],
    }
    repo = tmp_path/'repo'
    repo.mkdir()

    def git(*args):
        return subprocess.check_output(
            ['git', '-c', 'core.autocrlf='+autocrlf, '-c', 'core.safecrlf=true', *args],
            cwd=repo, stderr=subprocess.STDOUT)

    git('init', '--quiet')
    # Only this non-provenance metadata copy gets CRLF so safecrlf=true also
    # accepts staging the attributes file under autocrlf=true.
    attributes = (ROOT/'.gitattributes').read_text(encoding='utf-8-sig')
    (repo/'.gitattributes').write_bytes(attributes.replace('\n', '\r\n').encode())
    for name, expected in files.items():
        content = (ROOT/name).read_bytes()
        assert hashlib.sha256(content).hexdigest() == expected
        path = repo/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        assert git('check-attr', 'text', '--', name).decode().strip().endswith(': unset')
    git('add', '--', '.gitattributes', *files)
    for name, expected in files.items():
        stored = git('show', ':'+name)
        assert hashlib.sha256(stored).hexdigest() == expected, ('Git index altered bytes', name)
    fresh = tmp_path/'fresh'
    fresh.mkdir()
    git('checkout-index', '--all', '--prefix='+fresh.as_posix()+'/')
    for name, expected in files.items():
        restored = (fresh/name).read_bytes()
        assert hashlib.sha256(restored).hexdigest() == expected, ('Checkout altered bytes', name)
        assert restored == (ROOT/name).read_bytes()
