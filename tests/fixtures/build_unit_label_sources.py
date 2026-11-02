from pathlib import Path
import subprocess,hashlib,json,zipfile,io
R=Path(__file__).resolve().parents[2];F=R/'tests/fixtures'
commits=dict(pre_unit='cf8fa647d1cbe7457362f54fbd4ecdce5c65cea5',unit='b3edf65e8f539b6f4e37e35b8b35144566b7838a',zolz='dfd60115e73cf0fcfc4c7d7c44432c667c771b34')
files=['gui/app.py','gui/geometry.py','gui/propagation.py','gui/emcd_forward.py','gui/project_io.py','gui/stage_b.py','gui/results.py','gui/prb_benchmark.py','scattering.py']
g=lambda *a:subprocess.check_output(['git',*a],cwd=R)
sha=lambda b:hashlib.sha256(b).hexdigest()
manifest=dict(schema=1,commits=commits,trees={k:g('rev-parse',v+'^{tree}').decode().strip() for k,v in commits.items()},files=files,entries={})
payload={}
for version,commit in commits.items():
    paths=['src/emcd_sim/'+n for n in (files if version!='zolz' else ['gui/app.py'])]
    if version=='pre_unit':paths+=['docs/WINDOWS_BETA_3.md']
    for path in paths:
        b=g('show',commit+':'+path);blob=g('rev-parse',commit+':'+path).decode().strip()
        assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==blob
        key=version+'/'+path;payload[key]=b
        manifest['entries'][key]=dict(commit=commit,path=path,sha256=sha(b),git_blob=blob)
out=io.BytesIO()
with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for key,b in sorted(payload.items()):
        info=zipfile.ZipInfo(key,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
        info.external_attr=0o100644<<16;z.writestr(info,b,compresslevel=9)
archive=out.getvalue();manifest['archive_sha256']=sha(archive)
data=(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode()
(F/'unit_label_sources_v1.zip').write_bytes(archive)
(F/'unit_label_sources_v1.json').write_bytes(data)
print('MANIFEST',sha(data));print('ARCHIVE',sha(archive));print('ENTRIES',len(payload),'BYTES',len(archive))
