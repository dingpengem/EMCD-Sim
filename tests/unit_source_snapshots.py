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


def assert_reviewed_current_sources(overrides=None,*,scope_bytes=None):
    """Protect the current scope separately from the immutable unit-only audit.

    Historical unit-only evidence remains immutable. The current scope is a
    separately pinned manifest of the reviewed unified-elastic candidate; it
    does not relabel those additions as unit-only changes. No executable or
    string changes are silently whitelisted; future changes need scope review.
    """
    manifest,_=load_snapshots()
    if scope_bytes is None:scope_bytes=(FIXTURES/'unified_elastic_current_scope_v1.json').read_bytes()
    assert hashlib.sha256(canonical(scope_bytes)).hexdigest()==CURRENT_SCOPE_SHA256,'Unreviewed current scope manifest'
    scope=json.loads(scope_bytes)
    assert scope['schema']==1 and scope['candidate_source']=='29697538f57c5cc9bf84b7012b51a57a40c9a52b'
    assert set(scope['canonical_sha256'])=={'src/emcd_sim/'+name for name in manifest['files']}
    for name in manifest['files']:
        path='src/emcd_sim/'+name
        content=(overrides or {}).get(path)
        if content is None:content=(ROOT/path).read_bytes()
        assert hashlib.sha256(canonical(content)).hexdigest()==scope['canonical_sha256'][path],f'Unreviewed current source: {path}'
