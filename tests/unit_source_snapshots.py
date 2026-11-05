"""Pinned source evidence; ordinary tests need neither Git nor network access."""
from pathlib import Path
import hashlib
import io
import json
import zipfile

ROOT=Path(__file__).resolve().parents[1]
FIXTURES=Path(__file__).parent/'fixtures'
MANIFEST_SHA256='5616769da62ac86993b64883f198b85e3e050d638fd7e37cd3b7223cca8c3693'
ARCHIVE_SHA256='5cbc066ad681e765b0478b2c56300c53a5f197e67ad075704460b4be68c378a1'
CURRENT_SCOPE_SHA256='8e4ecaf4e799120e14edade99cb69b67afad004e018618993ce3338914acce5a'
GUI_SCOPE_SHA256='a3a23ce6c92cbb52c4b6a019f406b36d38a30ac329a68e2cd8c4ded8463d9d32'
GUI_PATH='src/emcd_sim/gui/app.py'
GUI_BASELINE_SHA256='b5783a8014864a44705f1d8c0173ec34ce18171e78406617112d6bbada41d68f'
GUI_CANDIDATE_SHA256='9f42e1e3c4aad3a0f20c136335cf5c1b64fce85949fb6b49415113ccf555ae90'
COMMITS=dict(pre_unit='cf8fa647d1cbe7457362f54fbd4ecdce5c65cea5',
             unit='b3edf65e8f539b6f4e37e35b8b35144566b7838a',
             zolz='dfd60115e73cf0fcfc4c7d7c44432c667c771b34')


def canonical(content):
    return content.decode('utf-8-sig').replace('\r\n','\n').encode('utf-8')


def load_snapshots(*,manifest_bytes=None,archive_bytes=None):
    manifest_bytes=(FIXTURES/'unit_label_sources_v1.json').read_bytes() if manifest_bytes is None else manifest_bytes
    archive_bytes=(FIXTURES/'unit_label_sources_v1.zip').read_bytes() if archive_bytes is None else archive_bytes
    assert hashlib.sha256(canonical(manifest_bytes)).hexdigest()==MANIFEST_SHA256,'Unreviewed snapshot manifest'
    assert hashlib.sha256(archive_bytes).hexdigest()==ARCHIVE_SHA256,'Unreviewed snapshot archive'
    manifest=json.loads(manifest_bytes)
    assert manifest['schema']==1 and manifest['commits']==COMMITS
    assert manifest['archive_sha256']==ARCHIVE_SHA256
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        assert sorted(archive.namelist())==sorted(manifest['entries'])
        sources={key:archive.read(key) for key in manifest['entries']}
    for key,item in manifest['entries'].items():
        content=sources[key]
        assert hashlib.sha256(content).hexdigest()==item['sha256'],key
        assert hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest()==item['git_blob'],key
    return manifest,sources


def reviewed_baseline_sources(*,scope_bytes=None):
    """Build the original reviewed map; never overlay or relabel its identity."""
    manifest,_=load_snapshots()
    if scope_bytes is None:scope_bytes=(FIXTURES/'unified_elastic_current_scope_v1.json').read_bytes()
    assert hashlib.sha256(canonical(scope_bytes)).hexdigest()==CURRENT_SCOPE_SHA256,'Unreviewed current scope manifest'
    scope=json.loads(scope_bytes)
    assert scope['schema']==1 and scope['candidate_source']=='29697538f57c5cc9bf84b7012b51a57a40c9a52b'
    assert set(scope['canonical_sha256'])=={'src/emcd_sim/'+name for name in manifest['files']}
    from single_element_source_guard import extension
    reviewed_extension=extension()
    return {('src/emcd_sim/'+name):reviewed_extension.get('src/emcd_sim/'+name,scope['canonical_sha256']['src/emcd_sim/'+name]) for name in manifest['files']}


def _validate_gui_scope(scope):
    """Closed, single-file scope; even a repinned manifest cannot add kernels."""
    expected=dict(schema=1,scope_id='bcc-fe-gui-v1',
        baseline_commit='cdd5dc3efa43e4f3874e011aa1cfc98f80cf46dd',
        path=GUI_PATH,baseline_snapshot='bcc_fe_gui_baseline_v1.py.txt',
        baseline_canonical_sha256=GUI_BASELINE_SHA256,
        candidate_canonical_sha256=GUI_CANDIDATE_SHA256,
        authorized_methods=['MainWindow.refresh','MainWindow.start_preview'],
        physics_convention='forward_born_dagger_g_minus_h_v1')
    assert isinstance(scope,dict) and type(scope.get('schema')) is int and scope==expected,'Unsupported GUI source scope'


def load_gui_scope(*,manifest_bytes=None,baseline_bytes=None):
    """Read pinned evidence only: no Git, network, execution, or hash adoption."""
    raw=(FIXTURES/'bcc_fe_gui_scope_v1.json').read_bytes() if manifest_bytes is None else manifest_bytes
    assert hashlib.sha256(canonical(raw)).hexdigest()==GUI_SCOPE_SHA256,'Unreviewed GUI scope manifest'
    scope=json.loads(raw)
    _validate_gui_scope(scope)
    baseline=(FIXTURES/'bcc_fe_gui_baseline_v1.py.txt').read_bytes() if baseline_bytes is None else baseline_bytes
    assert hashlib.sha256(canonical(baseline)).hexdigest()==GUI_BASELINE_SHA256,'Unreviewed GUI baseline snapshot'
    return scope,baseline


def assert_reviewed_current_sources(overrides=None,*,scope_bytes=None,gui_scope_bytes=None):
    """Validate history, the BCC GUI scope, then the reviewed editor scope.

    The baseline map remains independently available and pinned. Only app.py
    receives the BCC digest before the separate editor scope validates and
    extends current expectations. Historical baseline maps remain unchanged.
    """
    baseline=reviewed_baseline_sources(scope_bytes=scope_bytes)
    gui,_=load_gui_scope(manifest_bytes=gui_scope_bytes)
    assert baseline[GUI_PATH]==gui['baseline_canonical_sha256'],'GUI scope parent identity mismatch'
    expected=dict(baseline)
    expected[GUI_PATH]=gui['candidate_canonical_sha256']
    from mdff_editor_source_scope import current_sources
    expected=current_sources(expected,overrides)
    for path,digest in expected.items():
        content=(overrides or {}).get(path)
        if content is None:content=(ROOT/path).read_bytes()
        assert hashlib.sha256(canonical(content)).hexdigest()==digest,f'Unreviewed current source: {path}'
