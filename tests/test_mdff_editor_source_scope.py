"""Positive-first identity and target-specific mutation tests; real sources untouched."""
from pathlib import Path
import copy
import hashlib
import io
import json
import shutil
import zipfile
from unittest.mock import patch
import pytest
import mdff_editor_source_scope as editor
import unit_source_snapshots as units
import single_element_source_guard as historical
import physics_source_guard as physics


def positive():
    units.assert_reviewed_current_sources()
    physics.assert_registered_sources()


@pytest.fixture(scope='module', autouse=True)
def positive_gate():
    positive()  # Failure prevents every mutation case in this module.


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    scope, _ = editor.load_scope()
    paths = set(historical.extension()) | set(units.reviewed_baseline_sources()) | set(editor.MODIFIED+editor.ADDED+editor.PROTECTED+editor.HISTORY) | {editor.MANIFEST_PATH, editor.ARCHIVE_PATH}
    from packaging_content_source_scope import support_paths
    paths |= support_paths(editor.ROOT)
    for path in paths:
        target = tmp_path/path; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(editor.ROOT/path, target)
    monkeypatch.setattr(editor, 'ROOT', tmp_path)
    monkeypatch.setattr(units, 'ROOT', tmp_path)
    monkeypatch.setattr(units, 'FIXTURES', tmp_path/'tests/fixtures')
    monkeypatch.setattr(historical, 'ROOT', tmp_path)
    monkeypatch.setattr(physics, 'ROOT', tmp_path)
    monkeypatch.setattr(physics, 'MANIFEST', tmp_path/'tests/fixtures/physics_source_manifest_v1.json')
    positive()
    yield tmp_path
    positive()  # Each test must restore its disposable mutations.


def test_complete_positive_and_independent_historical_maps():
    before = historical.extension(); baseline = units.reviewed_baseline_sources()
    positive(); scope, _ = editor.load_scope()
    assert before == historical.extension() and baseline == units.reviewed_baseline_sources()
    assert not set(editor.ADDED) & set(before)
    for path in editor.MODIFIED:
        if path in before: assert before[path] == scope['parent_archive']['files'][path]['canonical_sha256']
    assert scope['scope_id'] == 'generalized-mdff-editor-v1'
    assert len(scope['candidate']) == 18 and len(scope['protected_parent']) == 93


@pytest.mark.parametrize('path', editor.MODIFIED+editor.ADDED)
def test_each_reviewed_path_mutation(isolated, path):
    positive(); file=isolated/path; original=file.read_bytes()
    try:
        file.write_bytes(original+b'\nunauthorized mutation\n')
        with pytest.raises(AssertionError, match=__import__('re').escape(path)): positive()
    finally: file.write_bytes(original)
    positive()


@pytest.mark.parametrize('path,before,after', [
 ('src/emcd_sim/double_channeling.py', "'...ab,ba->...'", "'...ab,ab->...'"),
 ('src/emcd_sim/double_channeling.py', 'np.asarray(incoming_hkl)[:,None,:]-np.asarray(outgoing_hkl)[None,:,:]', 'np.asarray(outgoing_hkl)[None,:,:]-np.asarray(incoming_hkl)[:,None,:]'),
 ('src/emcd_sim/multislice_double_channeling.py', 'transition_modes(tensor).conj()', 'transition_modes(tensor)'),
])
def test_scientific_mutations_report_intended_path(isolated,path,before,after):
    positive(); file=isolated/path; original=file.read_bytes(); text=original.decode('utf-8-sig'); assert text.count(before)==1
    try:
        file.write_bytes(text.replace(before,after,1).encode())
        with pytest.raises(AssertionError,match=__import__('re').escape(path)):
            physics.assert_registered_sources()
    finally:file.write_bytes(original)
    positive()


@pytest.mark.parametrize('path,reason', [
 (editor.MANIFEST_PATH,'editor scope manifest'),
 (editor.ARCHIVE_PATH,'editor parent archive'),
 ('tests/fixtures/bcc_fe_gui_scope_v1.json','GUI scope manifest'),
 ('tests/fixtures/unit_label_sources_v1.json','snapshot manifest'),
 ('tests/fixtures/part1c_refactor_scope_v1.json','Part 1C source scope'),
])
def test_evidence_mutation(isolated,path,reason):
    positive(); file=isolated/path; original=file.read_bytes()
    try:
        file.write_bytes(original+b' ')
        with pytest.raises(AssertionError,match=reason):positive()
    finally:file.write_bytes(original)
    positive()


@pytest.mark.parametrize('path',[editor.MODIFIED[0],editor.ADDED[0]])
def test_missing_authorized_file(isolated,path):
    file=isolated/path; original=file.read_bytes()
    try:
        file.unlink()
        with pytest.raises(AssertionError,match=__import__('re').escape(path)):positive()
    finally:file.write_bytes(original)


@pytest.mark.parametrize('variant',['schema','parent','extra','unsafe','kind','hash'])
def test_closed_manifest_semantics_even_with_replaced_test_pin(isolated,variant,monkeypatch):
    positive(); file=isolated/editor.MANIFEST_PATH; original=file.read_bytes(); scope=json.loads(original)
    if variant=='schema':scope['schema']=True
    elif variant=='parent':scope['parent_commit']='0'*40
    elif variant=='extra':scope['candidate']['src/emcd_sim/elastic.py']=copy.deepcopy(next(iter(scope['candidate'].values())))
    elif variant=='unsafe':scope['candidate']['../escape.py']=scope['candidate'].pop(editor.ADDED[0])
    elif variant=='kind':scope['candidate'][editor.ADDED[0]]['kind']='modified'
    else:scope['candidate'][editor.ADDED[0]]['canonical_sha256']='0'*64
    raw=(json.dumps(scope)+'\n').encode()
    try:
        file.write_bytes(raw)
        with monkeypatch.context() as m:
            m.setattr(editor,'MANIFEST_SHA256',editor.digest(raw))
            target=editor.ADDED[0] if variant=='hash' else 'scope|parent|path|schema'
            with pytest.raises(AssertionError,match=target):positive()
    finally:file.write_bytes(original)
    positive()


@pytest.mark.parametrize('variant',['duplicate','absolute','traversal','missing','extra'])
def test_parent_archive_structure(isolated,variant,monkeypatch):
    positive(); scope,contents=editor.load_scope(); stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w') as archive:
        for name,raw in contents.items():
            if variant=='missing' and name==editor.MODIFIED[0]:continue
            archive.writestr(name,raw)
        if variant=='duplicate':
            with pytest.warns(UserWarning,match='Duplicate'):archive.writestr(editor.MODIFIED[0],contents[editor.MODIFIED[0]])
        elif variant in ('absolute','traversal','extra'):
            archive.writestr('/absolute.py' if variant=='absolute' else '../escape.py' if variant=='traversal' else 'extra.py',b'not executable evidence')
    raw=stream.getvalue()
    with monkeypatch.context() as m:
        m.setattr(editor,'ARCHIVE_SHA256',hashlib.sha256(raw).hexdigest())
        with pytest.raises(AssertionError,match='archive entry|Unsafe scope path'):
            editor.validate_archive(raw,scope)
    positive()


def test_duplicate_manifest_keys_rejected(isolated,monkeypatch):
    file=isolated/editor.MANIFEST_PATH; original=file.read_bytes();raw=original.replace(b'{',b'{"schema":1,',1)
    try:
        file.write_bytes(raw)
        with monkeypatch.context() as m:
            m.setattr(editor,'MANIFEST_SHA256',editor.digest(raw))
            with pytest.raises(AssertionError,match='Duplicate scope key'):positive()
    finally:file.write_bytes(original)


def test_offline_no_git_network_or_snapshot_execution():
    # Import the complete helper graph before forbidding execution mechanisms.
    positive()
    with (patch('subprocess.Popen',side_effect=AssertionError('No subprocess')),
          patch('socket.create_connection',side_effect=AssertionError('No network')),
          patch('builtins.exec',side_effect=AssertionError('No archived code execution'))):
        positive()
    positive()
