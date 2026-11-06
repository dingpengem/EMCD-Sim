"""Freeze actual tracked and added candidate files around bounded corrective checks."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT.parents[1]/'outputs'/'mdff-usability-correction-20261106'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory():
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    added=subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')
    return {name:dict(sha256=digest(ROOT/name),bytes=(ROOT/name).stat().st_size,kind='tracked' if name in tracked else 'added') for name in sorted(set(tracked+added)-{''})}


def write(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n',encoding='utf-8')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--kind',choices=['tests','native'],default='tests');parser.add_argument('--label',required=True)
    args=parser.parse_args();folder=EVIDENCE/args.label
    folder.mkdir(parents=True,exist_ok=False)
    before=inventory();write(folder/'source-before.json',before)
    environment=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONHASHSEED='0',PYTHONPATH=str(ROOT/'src')+';'+str(ROOT/'tests'))
    if args.kind=='tests':
        environment['QT_QPA_PLATFORM']='offscreen'
        original=EVIDENCE.parent/'mdff-usability-independent-review-20261106'/'test_review_risks.py'
        reproducer=EVIDENCE/'test_review_risks.py'
        assert digest(original)==digest(reproducer),'Independent assertions changed'
        command=[sys.executable,'-u','-m','pytest',str(reproducer),str(ROOT/'tests/test_mdff_corrective.py'),
            str(ROOT/'tests/test_manual_l23.py')+'::test_independent_profiles_and_exact_provider_off_grid',
            str(ROOT/'tests/test_manual_l23.py')+'::test_frame_rotation_reversal_and_heatmaps_use_provider',
            str(ROOT/'tests/test_manual_l23.py')+'::test_solver_agreement_and_portable_complete_restoration',
            '--rootdir='+str(ROOT),'--basetemp='+str(folder/'tmp'),'-p','no:cacheprovider','-q','--tb=short','--junitxml='+str(folder/'checks.xml')]
    else:
        environment.pop('QT_QPA_PLATFORM',None)
        command=[sys.executable,'-u',str(ROOT/'scripts/mdff_corrective_walkthrough.py'),'--output',str(folder/'native')]
    record=dict(kind=args.kind,label=args.label,base=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),command=command,cwd=str(ROOT),python=sys.executable,
        python_version=sys.version,platform=platform.platform(),source_before_sha256=digest(folder/'source-before.json'),
        environment={key:environment.get(key) for key in ('PYTHONPATH','PYTHONDONTWRITEBYTECODE','PYTHONHASHSEED','QT_QPA_PLATFORM')})
    if args.kind=='tests':record['independent_reproducer_sha256']=digest(reproducer)
    write(folder/'run.json',record)
    with (folder/'checks.log').open('wb') as log:
        if args.kind=='tests':
            result=subprocess.run(command,cwd=ROOT,env=environment,stdout=log,stderr=subprocess.STDOUT);code=result.returncode
        else:
            process=subprocess.Popen(command,cwd=ROOT,env=environment,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            deadline=time.monotonic()+240;completed=folder/'native'/'completed.json'
            while process.poll() is None and not completed.exists() and time.monotonic()<deadline:time.sleep(.2)
            outcome=json.loads(completed.read_bytes()) if completed.exists() else dict(exit_code=process.poll() if process.poll() is not None else 124,error='Native walkthrough did not complete')
            code=outcome['exit_code'];record.update(gui_process_pid=process.pid,gui_process_exit_code=process.poll(),walkthrough=outcome)
    after=inventory();write(folder/'source-after.json',after)
    record.update(exit_code=code,source_unchanged=before==after,source_after_sha256=digest(folder/'source-after.json'),
        finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),log_sha256=digest(folder/'checks.log'))
    if args.kind=='tests':
        record['junit_sha256']=digest(folder/'checks.xml');tree=ET.parse(folder/'checks.xml')
        record['tests']=[dict(identity=c.attrib['classname']+'::'+c.attrib['name'],outcome='failed' if c.find('failure') is not None or c.find('error') is not None else 'skipped' if c.find('skipped') is not None else 'passed') for c in tree.findall('.//testcase')]
    write(folder/'run.json',record)
    if before!=after:raise RuntimeError('Corrective candidate changed during verification')
    print(json.dumps(dict(folder=str(folder),exit_code=code,source_unchanged=before==after,tests=len(record.get('tests',[]))),indent=2))
    return code


if __name__=='__main__':sys.exit(main())
