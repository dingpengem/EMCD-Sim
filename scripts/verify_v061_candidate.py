"""Verify local archive manifest and saved-data source/frozen GUI acceptance."""
import hashlib
import json
import zipfile
import argparse
import xml.etree.ElementTree as ET
import numpy as np
from pathlib import Path


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-root',type=Path,default=Path('build/windows-v061-beta-final'))
    parser.add_argument('--acceptance-root',type=Path,default=Path('outputs/v061_final_acceptance'))
    args=parser.parse_args();root=args.build_root
    app=root/'dist/EMCD-Sim'
    manifest=json.loads((root/'build_manifest.json').read_text(encoding='utf-8-sig'))
    assert manifest['version']=='0.6.1b1'
    for name,sha in manifest['build']['runtime_source_sha256'].items():
        assert digest(Path('src')/name)==sha,name
    for entry in manifest['files']:
        p=app/entry['path']
        assert p.stat().st_size==entry['bytes'] and digest(p)==entry['sha256'],str(p)
    actual={p.relative_to(app).as_posix() for p in app.rglob('*') if p.is_file()}
    assert actual=={e['path'] for e in manifest['files']}|{'SHA256SUMS.txt'}
    assert not any('/outputs/' in '/'+p or '/.git/' in '/'+p or 'symmat' in p for p in actual)
    archive=root/'EMCD-Sim-0.6.1-beta.1-Windows-RC.zip'
    assert digest(archive)==(root/'SHA256SUMS.txt').read_text().split()[0]
    with zipfile.ZipFile(archive) as zipped:
        assert zipped.testzip() is None
        for entry in manifest['files']:
            name='EMCD-Sim/'+entry['path']
            assert hashlib.sha256(zipped.read(name)).hexdigest()==entry['sha256'],name
    folder=args.acceptance_root
    source,frozen=[json.loads((folder/p/'acceptance.json').read_text()) for p in ('source_double_final','frozen_double')]
    assert frozen['build']['application_version']=='0.6.1b1'
    assert source['original_arrays']==frozen['original_arrays']
    for r in (source,frozen):
        assert r['forward_calls']==0 and r['original_arrays_unchanged'] and r['project_files_unchanged']
    for mode in ('source_double_final','frozen_double'):
        metadata=json.loads((folder/mode/'paired_maps.png.json').read_text())
        assert 'Full-field' in metadata['support'] and metadata['mode']=='asymmetry'
    single=json.loads((folder/'frozen_single/acceptance.json').read_text())
    assert single['forward_calls']==0 and single['original_arrays_unchanged'] and single['project_files_unchanged']
    from emcd_sim.gui.project_io import load_project
    from emcd_sim.gui.stage_f_acceptance import fingerprints
    assert fingerprints(load_project('outputs/v060_release/source_native/single_both_project'))==single['original_arrays']
    for result in (source,frozen,single):
        assert result['release_controls']['new_project_grid']==97
        assert result['release_controls']['new_project_memory_mib']==2048
        assert result['release_saved_checks']['saved_512_compatible']
        assert set(result['release_saved_checks']['methods'])=={'bloch','fft-multislice'}
    hashes=json.loads(Path('outputs/ni_emcd_thickness_scientific_audit/production_hashes.json').read_text())
    assert len(hashes)==204 and all(digest(Path(p))==sha for p,sha in hashes.items())
    scientific=json.loads(Path('outputs/ni_emcd_thickness_scientific_audit/audit.json').read_text())
    assert scientific['passed']
    assert abs(scientific['worst_asymmetry']['difference_pp'])<=.01
    assert scientific['worst_raw']['raw_relative']<=.001
    angular={}
    for method in ('bw','ms'):
        rows=[]
        for n in (33,97,193):
            with np.load(f'outputs/angular_resolution_convergence/{method}_{n}.npz',allow_pickle=False) as data:
                assert data['I_plus'].shape==(n,n) and np.isfinite(data['I_plus']).all()
                d=json.loads(str(data['detector_json']))
                actual=100*(d['I_A_plus']-d['I_B_plus'])/(d['I_A_plus']+d['I_B_plus'])
                np.testing.assert_allclose(actual,d['A_raw'],rtol=1e-14)
                rows.append(dict(grid=n,detector_asymmetry_percent=actual))
        angular[method]=dict(values=rows,increment_97_to_193_pp=rows[2]['detector_asymmetry_percent']-rows[1]['detector_asymmetry_percent'])
    regression=ET.parse(folder/'regression.xml').getroot().find('testsuite')
    tests={k:regression.attrib[k] for k in ('tests','failures','errors','skipped','time')}
    assert tests['failures']==tests['errors']=='0'
    historical=ET.parse(folder/'historical.xml').getroot().find('testsuite')
    assert historical.attrib['tests']=='1' and historical.attrib['failures']==historical.attrib['errors']=='0'
    report=dict(passed=True,version=manifest['version'],archive=str(archive),sha256=digest(archive),bytes=archive.stat().st_size,
        source_frozen_arrays_equal=True,solver_calls=0,manifest_verified=True,clean_machine='NOT TESTED',
        source_commit=manifest['build']['commit'],build_dirty=manifest['build']['dirty'],
        exact_packaged_source_hashes=manifest['build']['runtime_source_sha256'])
    report.update(regression=tests,historical_test='PASSED',production_checkpoints_verified=204,
        scientific_gate='PASSED',angular_convergence=angular)
    (folder/'package_acceptance.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='exact_packaged_source_hashes'}))


if __name__=='__main__':main()
