"""Pinned additive scope; original historical maps remain independently queryable.

This loader and its manifest pin are review-bootstrap infrastructure, authenticated
by the registration-only/combined reviewed patch, not by a self-hash cycle.
"""
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import zipfile

ROOT=Path(__file__).resolve().parents[1]
BASE='3b0ce6c386f3c815f85d8b9d64db679ff7622a94'
ACCEPTED_PATCH='6e496aff8152903d8bca45bd1d6f1704139647324fd7399920e1ed03e82b7fe2'
MANIFEST_PATH='tests/fixtures/mdff_usability_scope_v4.json'
ARCHIVE_PATH='tests/fixtures/mdff_usability_parent_v4.zip'
MANIFEST_SHA256='84b54aa7f420aab8ccb881af0a80ea487e3b9378e0625f3d2c53411da78caf71'
ACCEPTED_DECLARATION_SHA256='20fef12d278544b30a96ad3b224d1a37db9c9353987f18dfcc67898dc8e52be5'
# Closed reviewed paths are literals, not inferred from working files/manifests.
ACCEPTED_PATHS=('docs/MANUAL_L23_TENSOR_MODEL.md','docs/MDFF_USABILITY_REDESIGN.md','docs/MDFF_USABILITY_SCOPE_PROPOSAL.md',
 'scripts/manual_l23_native_walkthrough.py','scripts/mdff_corrective_walkthrough.py','scripts/mdff_native_walkthrough.py','scripts/verify_mdff_corrective.py','scripts/xmcd_native_walkthrough.py',
 'src/emcd_sim/gui/app.py','src/emcd_sim/gui/atomic_editor.py','src/emcd_sim/gui/imported_tensor_ui.py','src/emcd_sim/gui/manual_l23_editor.py','src/emcd_sim/gui/mdff_usability.py','src/emcd_sim/gui/project_io.py','src/emcd_sim/gui/provider_ui.py','src/emcd_sim/gui/results_browser.py','src/emcd_sim/gui/saved_atomic_ui.py','src/emcd_sim/gui/stage_b.py','src/emcd_sim/gui/xmcd_preview.py','src/emcd_sim/imported_mdff.py','src/emcd_sim/manual_l23.py','tests/test_manual_l23.py','tests/test_mdff_corrective.py','tests/test_mdff_usability.py','tests/test_xmcd_usability_preview.py')
MODIFIED=('src/emcd_sim/gui/app.py','src/emcd_sim/gui/atomic_editor.py','src/emcd_sim/gui/imported_tensor_ui.py','src/emcd_sim/gui/project_io.py','src/emcd_sim/gui/provider_ui.py','src/emcd_sim/gui/results_browser.py','src/emcd_sim/gui/stage_b.py','src/emcd_sim/imported_mdff.py')
INTEGRATIONS=('tests/unit_source_snapshots.py','tests/single_element_source_guard.py','tests/conftest.py','tests/test_mdff_editor_source_scope.py','tests/test_packaging_content_source_scope.py','tests/test_automatic_numerical_settings.py','.gitattributes','src/emcd_sim/gui/responsive.py','src/emcd_sim/gui/desktop_acceptance.py','packaging/native_acceptance.py','tests/test_bcc_fe_cif_gui.py','tests/test_generalized_emcd_gui.py','tests/test_gui_stage_b.py','tests/test_gui_stage_c.py','tests/test_multislice_slice_step_range.py','tests/test_ni_117.py','tests/test_parallel_resources.py','tests/test_single_element_gui.py','tests/test_solver_settings_ui.py','tests/test_unified_elastic_acceptance.py','tests/test_unified_provider_gui.py')
BOOTSTRAP=INTEGRATIONS+('tests/mdff_usability_source_scope.py','tests/mdff_workflow_registration.py','tests/test_mdff_usability_source_scope.py','tests/fixtures/mdff_usability_scope_v1.json','tests/fixtures/mdff_usability_parent_v1.zip','tests/fixtures/mdff_usability_scope_v2.json','tests/fixtures/mdff_usability_parent_v2.zip','tests/fixtures/mdff_usability_scope_v3.json','tests/fixtures/mdff_usability_parent_v3.zip',MANIFEST_PATH,ARCHIVE_PATH,'scripts/verify_mdff_registration.py','docs/MDFF_USABILITY_REGISTRATION.md')
TRUST_ROOTS=('tests/mdff_usability_source_scope.py',MANIFEST_PATH,ARCHIVE_PATH)
WORKFLOWS={
 'test_unified_starting_choices_have_no_material_electronic_defaults':'test_replacement_defaults_preserve_provenance_grid_and_help',
 'test_required_physical_definitions_and_blank_material_inputs':'test_replacement_physical_definitions_units_and_holes',
 'test_element_drafts_do_not_transfer_or_restore_validation':'test_replacement_element_roundtrip_clears_executable_validation',
 'test_missing_references_and_unsupported_element':'test_replacement_missing_reference_and_unsupported_rejection',
 'test_historical_ni_is_not_silently_migrated':'test_replacement_historical_saved_zero_and_absence'}


def canonical(raw):return raw.decode('utf-8-sig').replace('\r\n','\n').encode('utf-8')
def digest(raw,mode='canonical'):return hashlib.sha256(raw if mode=='raw' else canonical(raw)).hexdigest()
def declaration(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def safe_name(path):
    assert isinstance(path,str) and path and '\\' not in path and ':' not in path,'Unsafe usability scope path: '+repr(path)
    p=PurePosixPath(path)
    assert not p.is_absolute() and str(p)==path and not any(x in ('.','..') for x in p.parts),'Unsafe usability scope path: '+path
    return path


def unique(pairs):
    result={}
    for key,value in pairs:
        assert key not in result,'Duplicate usability scope key: '+key
        result[key]=value
    return result


def read(root,path,overrides=None,*,resolved_root=None):
    safe_name(path)
    if overrides is not None and path in overrides:
        assert isinstance(overrides[path],bytes),'Invalid source override: '+path
        return overrides[path]
    target=root/path
    boundary=root.resolve() if resolved_root is None else resolved_root
    assert target.resolve().is_relative_to(boundary),'Usability scope path outside root: '+path
    try:return target.read_bytes()
    except OSError as exc:raise AssertionError('Missing usability source: '+path) from exc


def load_scope(root=None,overrides=None):
    root=ROOT if root is None else Path(root)
    raw=read(root,MANIFEST_PATH,overrides)
    assert digest(raw)==MANIFEST_SHA256,'Unreviewed usability scope manifest: '+MANIFEST_PATH
    scope=json.loads(raw,object_pairs_hook=unique)
    assert set(scope)=={'schema','scope_id','base_commit','accepted_patch_sha256','canonicalization','candidate','parent_files','parent_archive_sha256','protected','bootstrap','bootstrap_hashes','workflows'},'Unsupported usability scope schema'
    assert type(scope['schema']) is int and scope['schema']==1 and scope['scope_id']=='mdff-usability-v4','Unsupported usability scope identity'
    assert scope['base_commit']==BASE and scope['accepted_patch_sha256']==ACCEPTED_PATCH,'Usability base/accepted patch mismatch'
    assert scope['canonicalization']=='UTF-8-sig; CRLF to LF; UTF-8; binary raw','Unsupported usability canonicalization'
    assert set(scope['candidate'])==set(ACCEPTED_PATHS),'Unauthorized/missing usability candidate paths'
    assert declaration(scope['candidate'])==ACCEPTED_DECLARATION_SHA256,'Accepted usability identities changed'
    assert scope['workflows']==WORKFLOWS,'Unauthorized workflow replacement mapping'
    assert scope['bootstrap']==list(BOOTSTRAP),'Unauthorized usability registration bootstrap'
    assert set(scope['bootstrap_hashes'])==set(BOOTSTRAP)-set(TRUST_ROOTS),'Missing/extra usability bootstrap identities'
    assert set(scope['parent_files'])==set(MODIFIED)|set(INTEGRATIONS),'Unauthorized/missing usability parent paths'
    for group in ('candidate','parent_files','protected','bootstrap_hashes'):
        for path,entry in scope[group].items():
            safe_name(path)
            if group=='candidate':
                assert set(entry)=={'kind','raw_sha256','canonical_sha256'},'Malformed candidate identity: '+path
                assert entry['kind']==('modified' if path in MODIFIED else 'added'),'Wrong candidate kind: '+path
            else:assert set(entry)==({'raw_sha256','canonical_sha256','git_blob'} if group=='parent_files' else {'raw_sha256','canonical_sha256','mode'}),'Malformed usability identity: '+path
            if group in ('protected','bootstrap_hashes'):assert entry['mode'] in ('raw','canonical'),'Invalid usability byte mode: '+path
            for key,value in entry.items():
                if key in ('kind','mode'):continue
                assert isinstance(value,str) and len(value)==(40 if key=='git_blob' else 64) and all(x in '0123456789abcdef' for x in value),'Malformed usability digest: '+path
    assert not set(scope['protected']) & (set(ACCEPTED_PATHS)|set(BOOTSTRAP)),'Overlapping protected/candidate paths'
    archive=read(root,ARCHIVE_PATH,overrides)
    assert digest(archive,'raw')==scope['parent_archive_sha256'],'Unreviewed usability parent archive: '+ARCHIVE_PATH
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        names=z.namelist();assert len(names)==len(set(names)) and set(names)==set(scope['parent_files']),'Unauthorized/missing usability parent archive entries'
        for path in names:safe_name(path)
        parents={path:z.read(path) for path in names}
    for path,raw in parents.items():
        entry=scope['parent_files'][path]
        assert digest(raw,'raw')==entry['raw_sha256'] and digest(raw)==entry['canonical_sha256'],'Usability parent identity mismatch: '+path
        assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==entry['git_blob'],'Usability parent Git blob mismatch: '+path
    return scope,parents


def current_sources(parent_sources,overrides=None,*,prefix='Unreviewed current source: '):
    scope,parents=load_scope(overrides=overrides)
    boundary=ROOT.resolve()
    # Overrides are test inputs, never a way to silently authorize another path.
    if overrides:
        for path in overrides:
            safe_name(path)
            assert path in set(scope['protected'])|set(ACCEPTED_PATHS)|set(BOOTSTRAP),'Unregistered source override: '+path
    # Validate actual candidate/registration bytes before using parent
    # substitutions solely inside the unchanged historical guard chain.
    for group in ('candidate','bootstrap_hashes'):
        for path,entry in scope[group].items():
            raw=read(ROOT,path,overrides,resolved_root=boundary)
            # Binary historical evidence remains byte-pinned.
            mode=entry.get('mode','canonical')
            assert digest(raw,mode)==entry[mode+'_sha256'],prefix+path
    from mdff_editor_source_scope import current_sources as historical_current
    historical_overrides=dict(overrides or {})
    historical_overrides.update(parents)
    expected=historical_current(parent_sources,historical_overrides,prefix=prefix)
    for path in MODIFIED:
        if path in expected:assert expected[path]==scope['parent_files'][path]['canonical_sha256'],'Usability accepted-parent disagreement: '+path
    # Historical evidence keeps its original semantic diagnostics. Remaining
    # protected files are still authenticated before any current map returns.
    for path,entry in scope['protected'].items():
        raw=read(ROOT,path,overrides,resolved_root=boundary)
        assert digest(raw,entry['mode'])==entry[entry['mode']+'_sha256'],prefix+path
    expected.update({path:entry['canonical_sha256'] for path,entry in scope['candidate'].items()})
    expected.update({path:entry['canonical_sha256'] for path,entry in scope['bootstrap_hashes'].items() if entry['mode']=='canonical'})
    return expected


def support_paths():
    """Closed source set for disposable isolation trees; not a changed identity map."""
    scope,_=load_scope()
    return set(scope['protected'])|set(scope['candidate'])|set(scope['bootstrap'])


def packaging_parent_scope():
    """Query the original packaging identity, not approve current source bytes.

    Active verification pairs this historical query with both composed current
    gates. Parent bytes come only from the pinned actual-base archive.
    """
    _,parents=load_scope()
    from packaging_content_source_scope import load
    return load(ROOT,parents)
