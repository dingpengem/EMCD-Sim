"""Source/provenance guards supplement independent mathematical controls."""
from pathlib import Path
import hashlib
import json
import subprocess
import numpy as np
import pytest
from physics_source_guard import ROOT, assert_registered_sources, canonical_sha256


def test_registered_correction_preserves_historical_source_identity():
    manifest = assert_registered_sources()
    old = manifest['versions']['legacy_same_index_h_minus_g']
    for name, identity in old['files'].items():
        historical = subprocess.check_output(['git','show',old['base_commit']+':'+name],cwd=ROOT)
        assert hashlib.sha256(historical).hexdigest() == identity['git_blob_sha256']
        assert canonical_sha256(historical) == identity['canonical_sha256']
        assert identity['canonical_sha256'] != manifest['versions'][manifest['active']]['files'][name]['canonical_sha256']


@pytest.mark.parametrize('path,before,after', [
    ('src/emcd_sim/double_channeling.py', "'...ab,ba->...'", "'...ab,ab->...'"),
    ('src/emcd_sim/double_channeling.py',
     'np.asarray(incoming_hkl)[:,None,:]-np.asarray(outgoing_hkl)[None,:,:]',
     'np.asarray(outgoing_hkl)[None,:,:]-np.asarray(incoming_hkl)[:,None,:]'),
    ('src/emcd_sim/multislice_double_channeling.py', 'transition_modes(tensor).conj()', 'transition_modes(tensor)'),
])
def test_guard_rejects_reverted_conventions_without_writing_source(path,before,after):
    source=(ROOT/path).read_text(encoding='utf-8-sig')
    assert source.count(before) == 1
    with pytest.raises(AssertionError,match='Unregistered physics change'):
        assert_registered_sources({path:source.replace(before,after).encode('utf-8')})


def test_historical_and_current_ni_inputs_have_distinct_exact_provenance():
    directory=Path(__file__).parent/'fixtures'
    manifest=json.loads((directory/'ni_xmcd_provenance_v1.json').read_text(encoding='utf-8'))
    historic=directory/manifest['historical']['fixture'];current=ROOT/manifest['canonical_package']['path']
    assert hashlib.sha256(historic.read_bytes()).hexdigest()==manifest['historical']['sha256']
    assert hashlib.sha256(current.read_bytes()).hexdigest()==manifest['canonical_package']['sha256']
    assert manifest['historical']['sha256']!=manifest['canonical_package']['sha256']
    # Additional semantic evidence, not a replacement for exact provenance.
    np.testing.assert_array_equal(np.loadtxt(historic),np.loadtxt(current))
