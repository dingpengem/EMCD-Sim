"""Verify local integration/native evidence and write the two acceptance reports.

Run after the full suite and the extracted candidate's native smoke process.
No remote writes, historical recalculations, builds or source changes occur.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'outputs/unified-main-integration'
DOC=ROOT/'docs/acceptance/unified-elastic-2026-11-03'
FEATURE='592dd85893875dfa3d7fbdbb9a85be025d96505d'
REMOTE='2810e86cba609dc3dc8cd42208b1c0b8ac747a2d'
MERGE='b48b57032e425292775aeaa3ecb5e8d8630a67c5'
SOURCE='29697538f57c5cc9bf84b7012b51a57a40c9a52b'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--candidate-root',type=Path,required=True)
    parser.add_argument('--native-output',type=Path,required=True);args=parser.parse_args()
    candidate=args.candidate_root.resolve();native=args.native_output.resolve()
    report=json.loads((native/'acceptance.json').read_text())
    launch=json.loads((OUT/'native_launch.json').read_text(encoding='utf-8-sig'))
    assert report['frozen'] and report['qt_platform']=='windows' and report['complete']
    assert not report['errors'] and report['all_workers_stopped'] and launch['exit_code']==0
    assert report['build']['commit']==SOURCE and report['build']['dirty'] is False
    assert report['build']['application_version']=='0.7.0b1'
    assert report['build']['physics_convention']=='forward_born_dagger_g_minus_h_v1'
    assert git('rev-list','--parents','-n','1',MERGE).decode().split()[1:]==[REMOTE,FEATURE]
    initial_tests=list(ET.parse(OUT/'source-all-native.xml').iter('testcase'))
    initial_failures=[t for t in initial_tests if t.find('failure') is not None or t.find('error') is not None]
    identity=lambda t:(t.get('classname'),t.get('name'))
    latest={identity(t):t for t in initial_tests}
    reruns=list(ET.parse(OUT/'reviewed-reruns.xml').iter('testcase'))
    assert all(t.find('failure') is None and t.find('error') is None for t in reruns)
    latest.update({identity(t):t for t in reruns})
    tests=list(latest.values())
    failures=[t for t in tests if t.find('failure') is not None or t.find('error') is not None]
    assert not failures,[t.attrib for t in failures]
    skipped=[t for t in tests if t.find('skipped') is not None]
    counts=dict(passed=len(tests)-len(skipped),skipped=len(skipped),failed=len(failures),collected=len(tests))
    offline=list(ET.parse(OUT/'offline-reference.xml').iter('testcase'))
    assert len(offline)==1 and not list(offline[0])
    app=candidate/'final-extracted/EMCD-Sim';manifest=json.loads((candidate/'build_manifest.json').read_text(encoding='utf-8-sig'))
    for item in manifest['files']:assert sha(app/item['path'])==item['sha256'],item['path']
    assert not any(Path(item['path']).suffix.lower() in ('.h5','.hdf5') for item in manifest['files'])
    data=app/'_internal/emcd_sim/data/adaptive_dirac_pade_2026'
    for name in ('coefficients.json','provenance.json','LICENSE','NOTICE'):
        assert (data/name).read_bytes()==(ROOT/'src/emcd_sim/data/adaptive_dirac_pade_2026'/name).read_bytes()
    assert len(json.loads((data/'coefficients.json').read_text()))==118
    assert (app/'_internal/ase/spacegroup/spacegroup.dat').is_file()
    assert not report['checks'][0]['h5py_imported']
    preserved=json.loads((OUT/'preserved_inputs_before.json').read_text())
    outer=ROOT.parents[1]
    assert all(sha(outer/name)==value for name,value in preserved.items())
    for name,value in json.loads((DOC/'ARTIFACT_SHA256.json').read_text()).items():assert sha(DOC/name)==value
    for name in git('ls-tree','-r','--name-only',REMOTE,'docs/images/ni017_flipm_recomputed').decode().splitlines():
        if name.endswith('/README.md'):continue
        assert git('show',REMOTE+':'+name)==git('show','HEAD:'+name),name
    for name in ('mdff_tensor','ni_local_mdff','xmcd_effective_mdff','single_channeling_tensor','double_channeling','multislice_double_channeling','gui/channeling'):
        p='src/emcd_sim/'+name+'.py'
        assert git('show',REMOTE+':'+p)==git('show','HEAD:'+p),p
    canonical=lambda b:b.decode('utf-8-sig').replace('\r\n','\n')
    for path in git('ls-tree','-r','--name-only',SOURCE,'src').decode().splitlines():
        if path.endswith('.py'):assert canonical((ROOT/path).read_bytes())==canonical(git('show',SOURCE+':'+path)),path
    archive=candidate/'EMCD-Sim-v0.7.0-beta.1-unified-elastic-local.zip'
    skips=Counter(t.find('skipped').get('message','') for t in skipped)
    evidence=dict(feature=FEATURE,remote_main_at_fetch=REMOTE,merge=MERGE,candidate_source=SOURCE,
        tests=counts,initial_full_run=dict(collected=len(initial_tests),passed=sum(not list(t) for t in initial_tests),
            skipped=sum(t.find('skipped') is not None for t in initial_tests),failures=[dict(t.attrib,message=t.find('failure').get('message','')) for t in initial_failures]),
        reviewed_reruns=dict(passed=sum(not list(t) for t in reruns),skipped=sum(t.find('skipped') is not None for t in reruns)),
        build_wrapper_exit_code=1,build_artifacts_independently_verified=True,
        skip_reasons=dict(skips),native_build=report['build'],native_checks=report['checks'],native_exit=launch,
        executable_sha256=sha(app/'EMCD-Sim.exe'),archive_sha256=sha(archive),
        packaged_files_verified=len(manifest['files']),package_manifest_sha256=sha(candidate/'build_manifest.json'),preserved_inputs=preserved,
        coefficient_sha256=sha(data/'coefficients.json'),clean_machine_tested=False)
    (DOC/'MAIN_INTEGRATION_EVIDENCE.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    native_rows='\n'.join('| '+v['name']+' | PASS |' for v in report['checks'])
    common=f"Feature `{FEATURE}`; fetched main `{REMOTE}`; normal --no-ff merge `{MERGE}`; exact clean candidate source `{SOURCE}`. Public version remains 0.7.0b1, physics convention forward_born_dagger_g_minus_h_v1.\n"
    (DOC/'MAIN_INTEGRATION_ACCEPTANCE.md').write_text('# Local main integration acceptance\n\n**LOCAL MAIN INTEGRATION READY FOR GITHUB PUSH**\n\n'+common+f'\nFull relevant source suite: **{counts["passed"]} passed, {counts["skipped"]} skipped, 0 failures/errors, {counts["collected"]} collected**. The pinned offline HDF5/reference extraction check separately passed under the existing Python3.10 audit environment. HDF5 is not a runtime dependency. Skip reasons are retained in [machine-readable evidence](MAIN_INTEGRATION_EVIDENCE.json).\n\nThe first sandboxed Python3.11 attempt was abandoned because secure temporary-directory ACLs denied fixture access. Its incomplete logs are preserved, not counted as passing. The complete canonical suite ran with native Windows permissions. No production algorithm was changed to bypass those access errors.\n\nLocal main was moved to the dedicated integration worktree by detaching the previous checkout at its unchanged commit; its two untracked acceptance documents remain intact. Main fast-forwarded to fetched origin/main, then merged the feature with two parents. Git merged README automatically; deliberate provider notes reconcile the documentation. Raw a.u. remains the primary README example, normalized percentages supplementary. Recalculated9/30nm arrays, figures, selected-energy CSV and provenance are unchanged. Their original Lobato provider is explicit; these are not new Adaptive recalculations. Ideal Flip-M cancels the nonmagnetic residual, not the underlying nonmagnetic EELS.\n\nAll six feature reports and their29-artifact SHA manifest were verified without editing the historical records. New GUI/factory calculations use bundled neutral Z=1..118 Adaptive Dirac–Padé at crystallographic g=0..36 inverse angstrom, with f in angstrom and the original IAM conversion applied once. Named Lobato, the unversioned constructor and absent-provider historical settings retain the original Ni provider. Genuine archived Ni amplitudes reproduced exactly in native acceptance; saved arrays remain unchanged. Fe, CsCl100, ZnO, monoclinic, Hermitian potentials, BW/MS, missing-table diagnostics and saved-provider provenance are covered by the source suite and companion native report.\n\n|Claim|Evidence and limit|\n|---|---|\n|Numerical compatibility|Protected Ni controls, old-project provider restoration and native saved-array checks pass. Distinct Adaptive factors are not required to equal Lobato.|\n|BW/MS convergence|Bounded finite-potential thin-cell refinement passed; no broad geometry/thickness convergence certification.|\n|Quantitative physical accuracy|No experimental accuracy certification. Atomic reference fit agreement is not a diffraction error bound; neutral IAM omits ions/bonding/TDS/absorption.|\n|Windows application functionality|Extracted frozen EXE passed native Windows GUI workers/save/open/CIF/click/MDFF gates. Same-host, not independent clean-machine installation.|\n\nRedistribution: pinned Adaptive coefficient subset ships under Apache-2.0 with full LICENSE, NOTICE, author attribution and transformation/pin metadata. MIT does not supersede those data terms. The original unlicensed Z=1..98 table remains excluded and externally opt-in; its all44 XF/Mott guard stays g=0 or .08..12. All published EXE/ZIP hashes, unrelated input data and preserved documents match their recorded identities. Ni kernels, physics convention and public version are unchanged.\n\nThe local readiness statement authorizes no network publication. No push/tag/release occurred. Independent clean-machine installation, experimental accuracy and broad convergence remain unclaimed. The existing public binary was not replaced. The final reporting commit is distinct from the exact executable source SHA above.\n',encoding='utf-8')
    (DOC/'WINDOWS_NATIVE_CANDIDATE_ACCEPTANCE.md').write_text('# Windows native unified-elastic candidate acceptance\n\n**PASS — separate local candidate; no public binary replacement.**\n\n'+common+f'\nCandidate directory: `{candidate}`. Actual executable: `{app/"EMCD-Sim.exe"}`.\n\nEXE SHA256 `{evidence["executable_sha256"]}`. Portable ZIP SHA256 `{evidence["archive_sha256"]}`. All {len(manifest["files"])} manifest files were rehashed after native testing; all4 coefficient/provenance/license resources exactly match source. ASE CIF space-group data are present. No HDF5 archive is packaged and h5py is not imported; all118 factors evaluate through the bundled JSON resource.\n\nThe portable ZIP was extracted to a fresh directory and its EXE launched with QT_QPA_PLATFORM=windows, PATH limited to Windows/System32 and Windows, and Python/Conda/Qt override paths removed. Exit code0 and clean worker shutdown were verified after the process ended, with no observed native crash or missing coefficient error. Build metadata identifies the exact clean source and pinned toolchain. Automatic path selection bypassed modal file choosers; calculations/rendering/click callbacks/save/open ran in the actual frozen application.\n\n|Native check|Result|\n|---|---|\n'+native_rows+'\n\nThe genuine historical Ni project predates provider metadata; it restored Lobato and reproduced its selected archived incoming amplitudes at zero measured discrepancy. Original project and saved arrays were not altered. This checks elastic compatibility, not the signed inelastic correctness of an old convention: its existing convention warning is preserved. The new Ni MDFF smoke uses only two selected energies in a bounded entrance-only configuration; it is not a new243-energy quantitative study.\n\nEvidence, process exit and skip details are in [MAIN_INTEGRATION_EVIDENCE.json](MAIN_INTEGRATION_EVIDENCE.json). Raw native JSON/screenshots/projects and source JUnit/log files remain under local `outputs/unified-main-integration/`. The package has unchanged version0.7.0b1 and a LOCAL CANDIDATE build label. Its Apache-2.0 coefficient LICENSE/NOTICE remain separate from MIT; no unlicensed legacy table is bundled.\n\nThis establishes same-host Windows application functionality and the stated numerical controls. It does not establish independent clean-machine installation, experimental quantitative accuracy, or universal BW/MS convergence. No release/tag/push or change to the existing public Windows binary occurred.\n',encoding='utf-8')
    with (DOC/'MAIN_INTEGRATION_ACCEPTANCE.md').open('a',encoding='utf-8') as f:
        f.write(f'\nRegression execution detail: the complete703-test invocation finished660 passed,40 skipped,3 failures. The failures were one asynchronous small-screen assertion and two current-source fingerprint guards still expecting pre-feature GUI files. The layout fixture now waits for the actual debounce timer/state, without forcing the production layout or relaxing its assertions. The current-source guard uses a separate pinned manifest of candidate2969753; historical unit-only snapshots and registered physics-kernel hashes are unchanged, with an added manifest-tamper rejection test. Reviewed reruns: {evidence["reviewed_reruns"]["passed"]} passed, {evidence["reviewed_reruns"]["skipped"]} skipped. The final coverage above combines the complete run with these targeted reruns; it is not a claim that the original invocation passed. No unresolved failure remains.\n\nAbsent-table source run:32 passed,14 skipped (13 external-data cases plus optional h5py reference check). The latter passed separately in the offline audit environment. Deprecation and small offscreen constrained-layout warnings are retained in logs.\n')
    main_report=DOC/'MAIN_INTEGRATION_ACCEPTANCE.md'
    main_report.write_text(main_report.read_text(encoding='utf-8').replace('Full relevant source suite:','Final relevant source coverage after reviewed reruns:'),encoding='utf-8')
    with (DOC/'WINDOWS_NATIVE_CANDIDATE_ACCEPTANCE.md').open('a',encoding='utf-8') as f:
        f.write('\nBuild invocation caveat: the outer PowerShell invocation recorded status1 while classifying PyInstaller informational stderr as NativeCommandError (Conda environment detection warning). The build log explicitly records successful EXE/COLLECT completion, ZIP and SHA256 creation. Those artifacts were independently extracted and every manifest file verified, and the actual EXE exited0 after all native checks. The wrapper status is preserved in evidence; no missing build artifact or native failure was ignored.\n')
        f.write('\nActual extracted-EXE screenshots: [default Ni](windows_native_ni.png), [indexed CsCl](windows_native_cscl.png).\n')
    from shutil import copyfile
    copyfile(native/'default_ni.png',DOC/'windows_native_ni.png')
    copyfile(native/'cscl.png',DOC/'windows_native_cscl.png')
    print(json.dumps(dict(status='LOCAL MAIN INTEGRATION READY FOR GITHUB PUSH',tests=counts,executable_sha256=evidence['executable_sha256'])))


if __name__=='__main__':main()
