"""Candidate-specific GUI identity; historical evidence and kernels stay pinned."""
import copy
import hashlib
import json
from unittest.mock import patch

import pytest
import single_element_source_guard as physics
from unit_source_snapshots import (
    FIXTURES, ROOT, GUI_PATH, GUI_BASELINE_SHA256, GUI_CANDIDATE_SHA256,
    canonical, load_gui_scope, reviewed_baseline_sources,
    assert_reviewed_current_sources, _validate_gui_scope,
)


def test_baseline_and_candidate_are_distinct_explicit_identities():
    original=reviewed_baseline_sources()
    scope,snapshot=load_gui_scope()
    assert hashlib.sha256(canonical(snapshot)).hexdigest()==GUI_BASELINE_SHA256
    assert original[GUI_PATH]==scope['baseline_canonical_sha256']==GUI_BASELINE_SHA256
    assert scope['candidate_canonical_sha256']==GUI_CANDIDATE_SHA256!=GUI_BASELINE_SHA256
    assert_reviewed_current_sources()
    assert reviewed_baseline_sources()==original  # No in-place historical overlay.
    for content in (snapshot,canonical(snapshot).replace(b'\n',b'\r\n')):
        with pytest.raises(AssertionError,match='Unreviewed current source: '+GUI_PATH):
            assert_reviewed_current_sources({GUI_PATH:content})


@pytest.mark.parametrize('before,after',[
    ('self.show_laue.setChecked(True)','self.show_laue.setChecked(False)'),
    ('def start_preview(self):','def start_preview(self):\n        return'),
])
def test_candidate_mutations_inside_and_outside_authorized_methods_rejected(before,after):
    source=(ROOT/GUI_PATH).read_text(encoding='utf-8-sig')
    assert before in source
    with pytest.raises(AssertionError,match='Unreviewed current source: '+GUI_PATH):
        assert_reviewed_current_sources({GUI_PATH:source.replace(before,after,1).encode()})


@pytest.mark.parametrize('field,value',[
    ('candidate_canonical_sha256','0'*64),
    ('baseline_canonical_sha256','1'*64),
    ('baseline_commit','0'*40),
    ('schema',2),
    ('schema',True),
    ('scope_id','unreviewed-v2'),
    ('path','src/emcd_sim/double_channeling.py'),
    ('path','../src/emcd_sim/gui/app.py'),
    ('path','src/emcd_sim/gui/../gui/app.py'),
    ('path',r'src\emcd_sim\gui\app.py'),
    ('path',['src/emcd_sim/gui/app.py']),
    ('path','SRC/emcd_sim/gui/app.py'),
    ('baseline_snapshot','../outside.py'),
    ('authorized_methods',['MainWindow.refresh','MainWindow.start_preview','MainWindow.settings']),
    ('physics_convention','unreviewed'),
])
def test_manifest_edits_rejected_by_digest_and_closed_schema(field,value):
    document=json.loads((FIXTURES/'bcc_fe_gui_scope_v1.json').read_bytes())
    document[field]=value
    raw=(json.dumps(document,indent=2)+'\n').encode()
    with pytest.raises(AssertionError,match='Unreviewed GUI scope manifest'):
        load_gui_scope(manifest_bytes=raw)
    # Semantic confinement remains independently tested, not just checksum failure.
    with pytest.raises(AssertionError,match='Unsupported GUI source scope'):
        _validate_gui_scope(document)


@pytest.mark.parametrize('extra',[
    {'additional_paths':['src/emcd_sim/gui/geometry.py']},
    {'canonical_sha256':{'src/emcd_sim/double_channeling.py':'0'*64}},
])
def test_additional_paths_and_kernel_authorization_forbidden(extra):
    scope,_=load_gui_scope();scope=copy.deepcopy(scope);scope.update(extra)
    with pytest.raises(AssertionError,match='Unsupported GUI source scope'):
        _validate_gui_scope(scope)
    with pytest.raises(AssertionError,match='Unreviewed GUI scope manifest'):
        assert_reviewed_current_sources(gui_scope_bytes=json.dumps(scope).encode())


def test_even_whitespace_manifest_tampering_rejected():
    raw=(FIXTURES/'bcc_fe_gui_scope_v1.json').read_bytes()
    with pytest.raises(AssertionError,match='Unreviewed GUI scope manifest'):
        load_gui_scope(manifest_bytes=raw+b' ')


def test_baseline_snapshot_tampering_rejected():
    _,raw=load_gui_scope()
    with pytest.raises(AssertionError,match='Unreviewed GUI baseline snapshot'):
        load_gui_scope(baseline_bytes=raw+b'\n# unauthorized\n')


def test_unrelated_numerical_source_mutation_still_rejected():
    path='src/emcd_sim/gui/geometry.py'
    source=(ROOT/path).read_text(encoding='utf-8-sig');assert '.5*lam*' in source
    with pytest.raises(AssertionError,match='Unreviewed current source: '+path):
        assert_reviewed_current_sources({path:source.replace('.5*lam*','.6*lam*').encode()})


def test_existing_physics_kernel_guard_is_not_overlaid():
    path='src/emcd_sim/double_channeling.py'
    source=(ROOT/path).read_bytes()
    assert path not in (GUI_PATH,)
    with pytest.raises(AssertionError,match='Unregistered physics change: '+path):
        physics.assert_current_extension({path:source+b'\n# unauthorized kernel edit\n'})


def test_historical_extension_manifest_tampering_rejected(monkeypatch):
    target=FIXTURES/'part1c_refactor_scope_v1.json'
    read=type(target).read_bytes
    def changed(path):
        raw=read(path)
        return raw+b'changed' if path==target else raw
    monkeypatch.setattr(type(target),'read_bytes',changed)
    with pytest.raises(AssertionError,match='Unreviewed Part 1C source scope'):
        assert_reviewed_current_sources()


def test_all_identity_checks_work_without_git_network_or_snapshot_execution():
    # Import test helpers before blocking process/network/execution mechanisms.
    with (patch('subprocess.Popen',side_effect=AssertionError('No subprocess')),
          patch('socket.create_connection',side_effect=AssertionError('No network')),
          patch('builtins.exec',side_effect=AssertionError('No snapshot execution'))):
        assert_reviewed_current_sources()
        scope,snapshot=load_gui_scope()
        assert scope['scope_id']=='bcc-fe-gui-v1' and snapshot
        physics.assert_current_extension()
