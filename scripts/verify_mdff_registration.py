"""Frozen, bounded registration acceptance; outputs must be outside the checkout."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,data):path.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def inventory():
    names=[]
    for args in (['ls-files','-z'],['ls-files','--others','--exclude-standard','-z']):
        names+=subprocess.check_output(['git',*args],cwd=ROOT).decode().split('\0')
    return {p:dict(sha256=digest(ROOT/p),bytes=(ROOT/p).stat().st_size) for p in sorted(set(names)-{''})}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    out=parser.parse_args().output.resolve()
    assert not out.is_relative_to(ROOT),'Verification output must be outside candidate'
    out.mkdir(parents=True,exist_ok=False)
    before=inventory();write(out/'source-before.json',before)
    old=['test_unified_starting_choices_have_no_material_electronic_defaults','test_required_physical_definitions_and_blank_material_inputs','test_element_drafts_do_not_transfer_or_restore_validation','test_missing_references_and_unsupported_element','test_historical_ni_is_not_silently_migrated']
    nodes=['tests/test_mdff_editor_source_scope.py::test_each_reviewed_path_mutation[packaging/emcd_gui.spec]',
        'tests/test_mdff_editor_source_scope.py::test_evidence_mutation[tests/fixtures/generalized_mdff_editor_scope_v1.json-editor scope manifest]',
        'tests/test_packaging_content_source_scope.py::test_historical_editor_maps_and_archive_are_still_independent',
        'tests/test_packaging_content_source_scope.py::test_additive_scope_rejects_target_mutation[tests/test_mdff_editor_source_scope.py]',
        'tests/test_packaging_content_source_scope.py::test_additive_scope_rejects_target_mutation[src/emcd_sim/double_channeling.py]',
        'tests/test_packaging_content_source_scope.py::test_packaging_scope_cannot_authorize_a_kernel_even_with_new_manifest_pin',
        'tests/test_mdff_usability_source_scope.py',*['tests/test_atomic_parameter_editor.py::'+name for name in old],
        'tests/test_xmcd_usability_preview.py::test_missing_source_keeps_visible_preview_and_directs_to_main_input',
        'tests/test_xmcd_usability_preview.py::test_main_source_selected_once_serves_preview_and_calculation']
    command=[sys.executable,'-u','-m','pytest',*nodes,'--rootdir='+str(ROOT),'--basetemp='+str(out/'tmp'),'-p','no:cacheprovider','-q','--tb=short','--maxfail=1','--junitxml='+str(out/'checks.xml')]
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONHASHSEED='0',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',QT_QPA_PLATFORM='offscreen',PYTHONPATH=str(ROOT/'src')+os.pathsep+str(ROOT/'tests'))
    record=dict(command=command,cwd=str(ROOT),python=sys.executable,python_version=sys.version,platform=platform.platform(),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),environment={k:env[k] for k in ('PYTHONPATH','PYTHONDONTWRITEBYTECODE','PYTHONHASHSEED','QT_QPA_PLATFORM','OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')},source_before_sha256=digest(out/'source-before.json'))
    write(out/'run.json',record)
    with (out/'checks.log').open('wb') as log:result=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    after=inventory();write(out/'source-after.json',after)
    record.update(exit_code=result.returncode,source_unchanged=before==after,source_after_sha256=digest(out/'source-after.json'),log_sha256=digest(out/'checks.log'),junit_sha256=digest(out/'checks.xml'),finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    def cases(xml):
        return [dict(identity=c.attrib['classname']+'::'+c.attrib['name'],outcome='failed' if any(c.find(k) is not None for k in ('failure','error')) else 'skipped' if c.find('skipped') is not None else 'passed') for c in ET.parse(xml).findall('.//testcase')]
    record['cases']=cases(out/'checks.xml')
    record['workflow_contracts']=[]
    for p in sorted((out/'tmp').rglob('registered-workflow/*/checks.xml')):
        child=json.loads((p.parent/'run.json').read_bytes())
        assert all(digest(p.parent/name)==value for name,value in child['hashes'].items())
        record['workflow_contracts'].append(dict(junit=str(p.relative_to(out)),sha256=digest(p),cases=cases(p),run_sha256=digest(p.parent/'run.json'),source_unchanged=child['source_unchanged'],exit_code=child['exit_code']))
    if result.returncode==0:
        assert len(record['cases'])==80 and all(c['outcome']=='passed' for c in record['cases']),'Required checks must all execute and pass'
        assert len(record['workflow_contracts'])==10,'All five historical/current workflow pairs must execute'
        assert sum(len(c['cases']) for c in record['workflow_contracts'])==11
        assert all(c['exit_code']==0 and c['source_unchanged'] and all(t['outcome']=='passed' for t in c['cases']) for c in record['workflow_contracts'])
    write(out/'run.json',record);assert before==after,'Source changed during registration verification'
    print(json.dumps(dict(exit_code=result.returncode,source_unchanged=before==after,checks=len(record['cases']),workflow_contracts=len(record['workflow_contracts'])),indent=2))
    return result.returncode


if __name__=='__main__':sys.exit(main())
