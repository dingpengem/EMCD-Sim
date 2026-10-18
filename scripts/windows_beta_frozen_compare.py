"""Verify extracted distribution integrity and matched source/frozen arrays."""
import argparse,csv,hashlib,json
from pathlib import Path
import numpy as np
from emcd_sim.gui.prb_benchmark import benchmark_spectra

ROOT=Path('outputs/windows_beta_acceptance')


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--build-root',type=Path,required=True);parser.add_argument('--app-root',type=Path,required=True)
    parser.add_argument('--frozen-report',type=Path);args=parser.parse_args()
    b=args.build_root;a=args.app_root
    manifest=json.loads((b/'build_manifest.json').read_text(encoding='utf-8-sig'))
    for entry in manifest['files']:
        path=a/entry['path'];assert path.stat().st_size==entry['bytes'] and digest(path)==entry['sha256'],entry['path']
    actual={p.relative_to(a).as_posix() for p in a.rglob('*') if p.is_file()}
    assert actual=={e['path'] for e in manifest['files']}|{'SHA256SUMS.txt'}
    assert not any('/outputs/' in '/'+p or '/.git/' in '/'+p or '/.aws/' in '/'+p or 'conda-meta/' in p for p in actual)
    inputs=sorted(p for p in actual if p.startswith('_internal/data/'))
    assert inputs==['_internal/data/wien2k_ni/Ni_fm.xmcd']
    assert digest(a/inputs[0])==manifest['build']['reference_sha256']
    archive=b/'EMCD-Sim-0.4.5-Beta-RC-Windows.zip';sha=digest(archive)
    assert sha==(b/'SHA256SUMS.txt').read_text().split()[0]
    report=dict(outcome='PASS',version=manifest['version'],build_source_commit=manifest['build']['commit'],
        zip_sha256=sha,zip_bytes=archive.stat().st_size,app_bytes=sum(p.stat().st_size for p in a.rglob('*') if p.is_file()),
        app_files=len(actual),exe_sha256=digest(a/'EMCD-Sim.exe'),bundled_source_sha256=manifest['build']['reference_sha256'],
        package_private_data_excluded=True,extraction_matches_manifest=True,app_root=str(a))
    (ROOT/'package_integrity.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
    if not args.frozen_report:return
    source=json.loads((ROOT/'source_native/acceptance.json').read_text());frozen=json.loads(args.frozen_report.read_text())
    assert source['outcome']==frozen['outcome']=='PASS' and frozen['frozen'] and frozen['development_python_paths_removed']
    assert frozen['build']['commit']==manifest['build']['commit']
    comparisons=[];csv_columns=0
    for key,reference in source['cases'].items():
        candidate=frozen['cases'][key]
        assert reference['fingerprints']==candidate['fingerprints'],key+' arrays differ'
        if 'raw' not in reference:continue
        np.testing.assert_array_equal(reference['energy_ev'],candidate['energy_ev'])
        for method,raw in reference['raw'].items():
            other=candidate['raw'][method]
            aa=np.array(list(raw.values()));bb=np.array([other[k] for k in raw])
            ca,cb=[benchmark_spectra(s)[0] for s in (raw,other)]
            comparisons.append(dict(case=key,solver=method,max_raw_absolute=float(abs(aa-bb).max()),
                max_raw_relative=float(np.max(abs(aa-bb)/np.maximum(abs(aa),abs(bb)))),
                max_prb_delta_pp=float(abs(ca['prb_relative_dichroism_percent']-cb['prb_relative_dichroism_percent']).max())))
            export=args.frozen_report.parent/(key+'_export')
            rows=list(csv.DictReader((export/(method+'_spectra.csv')).open()))
            with np.load(export/'virtual_detector_eels.npz',allow_pickle=False) as arrays:
                for column in rows[0]:
                    if column in ('solver','channeling_model'):continue
                    values=np.array([float(row[column]) for row in rows])
                    np.testing.assert_array_equal(values,arrays[method+'__'+column]);csv_columns+=1
            assert all(row['solver']==method and row['channeling_model']==key.split('_')[0] for row in rows)
    report=dict(outcome='PASS',source_vs_frozen_arrays_bitwise_equal=True,comparisons=comparisons,
        max_raw_relative=max(r['max_raw_relative'] for r in comparisons),max_prb_delta_pp=max(r['max_prb_delta_pp'] for r in comparisons),
        saved_production_cases=['BW Double 242 energies','MS Double 242 energies'],clean_machine='NOT TESTED',
        native_scaling=frozen['screen_dpr'],working_directory=frozen['working_directory'],executable=frozen['executable'])
    report['frozen_csv_columns_exactly_match_npz']=csv_columns
    (ROOT/'frozen_comparison.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)


if __name__=='__main__':main()
