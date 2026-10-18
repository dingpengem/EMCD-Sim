"""Read-only numerical/package checks after native cancellation acceptance."""
import argparse,csv,hashlib,json
from pathlib import Path


def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024*1024),b''):digest.update(block)
    return digest.hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--build-root',type=Path,required=True)
    parser.add_argument('--app-root',type=Path,required=True)
    args=parser.parse_args();root=args.output
    source=json.loads((root/'source_sequential/acceptance.json').read_text(encoding='utf-8'))
    frozen=json.loads((root/'frozen_native/acceptance.json').read_text(encoding='utf-8'))
    assert source['outcome']==frozen['outcome']=='PASS'
    assert source['completed_solver_fingerprints']==frozen['completed_solver_fingerprints']
    manifest=json.loads((args.build_root/'build_manifest.json').read_text(encoding='utf-8-sig'))
    for record in manifest['files']:
        path=args.app_root/record['path']
        assert path.stat().st_size==record['bytes'] and sha(path)==record['sha256'],path
    actual={p.relative_to(args.app_root).as_posix() for p in args.app_root.rglob('*') if p.is_file()}
    assert actual=={r['path'] for r in manifest['files']}|{'SHA256SUMS.txt'}
    assert sha(args.app_root/'_internal/data/wien2k_ni/Ni_fm.xmcd')=='4fd517af3e54db94588a76b7a6ed9c2f9a1b745cd8fe52b9fca0f87fc4938db3'
    assert sha('build/windows-beta-rc-20261018/EMCD-Sim-0.4.5-Beta-RC-Windows.zip')=='0c1eaec31dd09a4eed75b1500e02ef5baf86910d2aa1a5a9b9d15e3670533751'
    protected=json.loads((root/'protected_hashes.json').read_text(encoding='utf-8'))
    for name,expected in protected.items():assert sha(name)==expected,name
    archive=next(args.build_root.glob('*.zip'))
    assert sha(archive)==(args.build_root/'SHA256SUMS.txt').read_text(encoding='ascii').split()[0]
    summary=dict(outcome='PASS',source_frozen_completed_bw_ms_bitwise_identical=True,
        protected_scientific_files=len(protected),protected_files_unchanged=True,
        extraction_matches_manifest=True,build_source_commit=manifest['build']['commit'],
        zip_path=str(archive),zip_bytes=archive.stat().st_size,zip_sha256=sha(archive),
        exe_sha256=sha(args.app_root/'EMCD-Sim.exe'),
        source_worst_idle_seconds=source['worst_idle_seconds'],frozen_worst_idle_seconds=frozen['worst_idle_seconds'])
    (root/'verification.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    with (root/'latency.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.writer(stream);writer.writerow(['environment','case','controlled','ack_seconds','stop_seconds','idle_seconds','gui_ticks'])
        for environment,report in [('source',source),('frozen',frozen)]:
            for case,row in report['cases'].items():writer.writerow([environment,case,row['controlled'],row['acknowledgement_seconds'],row['stop_seconds'],row['idle_seconds'],row['gui_ticks']])
    print(json.dumps(summary),flush=True)


if __name__=='__main__':main()
