"""Positive-first bounded registration checks; production files are never mutated."""
import copy
import hashlib
import json
from pathlib import Path
import re
import pytest
import mdff_usability_source_scope as scope
import unit_source_snapshots as units
import physics_source_guard as physics
import single_element_source_guard as history
import mdff_editor_source_scope as editor


_VALID_BYTES=None


def positive():
    units.assert_reviewed_current_sources(_VALID_BYTES);physics.assert_registered_sources(_VALID_BYTES)


@pytest.fixture(scope='module',autouse=True)
def positive_gate():
    global _VALID_BYTES
    positive()  # Real disk controls pass before any isolated byte override.
    d,_=scope.load_scope()
    _VALID_BYTES={p:(scope.ROOT/p).read_bytes() for p in set(d['protected'])|set(d['candidate'])|set(d['bootstrap'])}
    yield
    _VALID_BYTES=None
    positive()  # Real disk controls pass after all bounded override cases.


def rejected(overrides,path):
    positive()
    overrides={**_VALID_BYTES,**overrides}
    for gate in (units.assert_reviewed_current_sources,physics.assert_registered_sources):
        with pytest.raises(AssertionError,match=re.escape(path)):gate(overrides)
    positive()


def test_positive_and_independent_historical_queries():
    original=history.extension();baseline=units.reviewed_baseline_sources()
    positive();declaration,parents=scope.load_scope();old,_=editor.load_scope()
    assert original==history.extension() and baseline==units.reviewed_baseline_sources()
    assert old['scope_id']=='generalized-mdff-editor-v1'
    assert declaration['accepted_patch_sha256']==scope.ACCEPTED_PATCH
    assert len(declaration['candidate'])==25 and len(parents)==29
    packaging=scope.packaging_parent_scope()
    assert packaging['parent_commit']=='3609dfc762749024a3c6726c3763ef33f3e46482'
    assert packaging['modified']['tests/test_mdff_editor_source_scope.py']['canonical_sha256']==declaration['parent_files']['tests/test_mdff_editor_source_scope.py']['canonical_sha256']
    for path in set(editor.MODIFIED)&set(original):
        assert original[path]==old['parent_archive']['files'][path]['canonical_sha256']
    assert set(scope.WORKFLOWS)=={
        'test_unified_starting_choices_have_no_material_electronic_defaults',
        'test_required_physical_definitions_and_blank_material_inputs',
        'test_element_drafts_do_not_transfer_or_restore_validation',
        'test_missing_references_and_unsupported_element','test_historical_ni_is_not_silently_migrated'}


@pytest.mark.parametrize('path',scope.ACCEPTED_PATHS)
def test_each_candidate_mutation(path):
    rejected({path:(scope.ROOT/path).read_bytes()+b'\nunauthorized bytes\n'},path)


@pytest.mark.parametrize('path',sorted(set(scope.BOOTSTRAP)-set(scope.TRUST_ROOTS)))
def test_registration_support_mutation(path):
    rejected({path:(scope.ROOT/path).read_bytes()+b'\nunauthorized bytes\n'},path)


@pytest.mark.parametrize('path',[scope.MANIFEST_PATH,scope.ARCHIVE_PATH])
def test_pinned_declaration_and_archive_mutation(path):
    rejected({path:(scope.ROOT/path).read_bytes()+b' '},path)


@pytest.mark.parametrize('path',[scope.ACCEPTED_PATHS[0],scope.MANIFEST_PATH,scope.ARCHIVE_PATH])
def test_missing_source_fails_closed(monkeypatch,path):
    positive();read=Path.read_bytes
    def unavailable(p):
        if p==scope.ROOT/path:raise FileNotFoundError(str(p))
        return read(p)
    with monkeypatch.context() as m:
        m.setattr(Path,'read_bytes',unavailable)
        for gate in (units.assert_reviewed_current_sources,physics.assert_registered_sources):
            with pytest.raises(AssertionError,match=re.escape('Missing usability source: '+path)):gate()
    positive()


@pytest.mark.parametrize('variant',['schema','base','accepted_patch','canonicalization','extra','missing','unsafe','hash','mapping','bootstrap','duplicate','parent_blob'])
def test_closed_declarations_even_with_replaced_manifest_pin(monkeypatch,variant):
    positive();d,_=scope.load_scope();d=copy.deepcopy(d)
    if variant=='schema':d['schema']=True
    elif variant=='base':d['base_commit']='0'*40
    elif variant=='accepted_patch':d['accepted_patch_sha256']='0'*64
    elif variant=='canonicalization':d['canonicalization']='strip all whitespace'
    elif variant=='extra':d['candidate']['src/emcd_sim/extra.py']=copy.deepcopy(next(iter(d['candidate'].values())))
    elif variant=='missing':d['candidate'].pop(scope.ACCEPTED_PATHS[0])
    elif variant=='unsafe':d['protected']['../escape.py']=d['protected'].pop(next(iter(d['protected'])))
    elif variant=='hash':d['candidate'][scope.ACCEPTED_PATHS[0]]['canonical_sha256']='0'*64
    elif variant=='mapping':d['workflows'].pop(next(iter(d['workflows'])))
    elif variant=='bootstrap':d['bootstrap'].append('tests/unreviewed_guard.py')
    elif variant=='parent_blob':d['parent_files'][scope.MODIFIED[0]]['git_blob']='0'*40
    raw=json.dumps(d,sort_keys=True).encode()
    if variant=='duplicate':raw=b'{"schema":1,'+raw[1:]
    expected={'schema':'identity','base':'base/accepted','accepted_patch':'base/accepted','canonicalization':'canonicalization',
        'extra':'candidate paths','missing':'candidate paths','unsafe':'Unsafe usability scope path',
        'hash':'Accepted usability identities changed','mapping':'replacement mapping','bootstrap':'bootstrap',
        'duplicate':'Duplicate usability scope key','parent_blob':'parent Git blob mismatch'}[variant]
    with monkeypatch.context() as m:
        m.setattr(scope,'MANIFEST_SHA256',scope.digest(raw))
        with pytest.raises(AssertionError,match=expected):scope.load_scope(overrides={scope.MANIFEST_PATH:raw})
    positive()


@pytest.mark.parametrize('path',['tests/fixtures/generalized_mdff_editor_scope_v1.json','tests/fixtures/unit_label_sources_v1.zip','tests/fixtures/physics_source_manifest_v1.json'])
def test_historical_evidence_mutation(path):
    rejected({path:(scope.ROOT/path).read_bytes()+b' '},path)


@pytest.mark.parametrize('path,before,after',[
 ('src/emcd_sim/double_channeling.py',"'...ab,ba->...'","'...ab,ab->...'"),
 ('src/emcd_sim/double_channeling.py','np.asarray(incoming_hkl)[:,None,:]-np.asarray(outgoing_hkl)[None,:,:]','np.asarray(outgoing_hkl)[None,:,:]-np.asarray(incoming_hkl)[:,None,:]'),
 ('src/emcd_sim/multislice_double_channeling.py','transition_modes(tensor).conj()','transition_modes(tensor)')])
def test_existing_bw_ms_scientific_sentinels(path,before,after):
    positive();text=(scope.ROOT/path).read_text(encoding='utf-8-sig');assert text.count(before)==1
    with pytest.raises(AssertionError,match=re.escape('Unregistered physics change: '+path)):
        physics.assert_registered_sources({**_VALID_BYTES,path:text.replace(before,after,1).encode()})
    positive()


@pytest.mark.parametrize('path',['src/emcd_sim/not_registered.py','../escape.py'])
def test_arbitrary_override_is_not_authorized(path):
    positive()
    for gate in (units.assert_reviewed_current_sources,physics.assert_registered_sources):
        with pytest.raises(AssertionError,match='Unregistered source override|Unsafe usability scope path'):gate({**_VALID_BYTES,path:b'new bytes'})
    positive()


def test_parent_bytes_are_not_valid_current_overrides():
    _,parents=scope.load_scope()
    rejected({scope.MODIFIED[0]:parents[scope.MODIFIED[0]]},scope.MODIFIED[0])


def test_actual_disk_target_cannot_escape_resolved_root(monkeypatch):
    path=scope.ROOT/scope.MODIFIED[0];resolve=Path.resolve;boundary=scope.ROOT.resolve()
    def escaped(p,*args,**kwargs):
        return boundary.parent/'outside.py' if p==path else resolve(p,*args,**kwargs)
    with monkeypatch.context() as m:
        m.setattr(Path,'resolve',escaped)
        with pytest.raises(AssertionError,match='Usability scope path outside root'):
            scope.read(scope.ROOT,scope.MODIFIED[0],resolved_root=boundary)
