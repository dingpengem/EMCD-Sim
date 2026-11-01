"""Run complete suites in reproducible fresh processes; never waive failures."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/physics_correction_final_integration'


def fingerprint():
    files=sorted([*ROOT.glob('src/**/*.py'),*ROOT.glob('tests/**/*.py'),*ROOT.glob('tests/fixtures/*')])
    return hashlib.sha256(b''.join(str(p.relative_to(ROOT)).encode()+p.read_bytes() for p in files if p.is_file())).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--rounds',type=int,default=2)
    parser.add_argument('--tag',default='acceptance_v1');args=parser.parse_args()
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(ROOT/'src'),
             QT_QPA_PLATFORM='offscreen',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    identity=fingerprint();records=[]
    for index in range(1,args.rounds+1):
        folder=OUT/f'{args.tag}_run{index}';folder.mkdir(parents=True,exist_ok=True)
        complete=folder/'result.json'
        if complete.exists():
            record=json.loads(complete.read_text());assert record['fingerprint']==identity
            assert record['returncode']==0,'Previous failed run retained; select a new tag for a reviewed retry'
            records.append(record);continue
        assert not (folder/'pytest.log').exists(),'Incomplete run retained; inspect it before choosing a new tag'
        env['EMCD_TEST_LIFECYCLE_LOG']=str(folder/'lifecycle.jsonl')
        command=[sys.executable,'-B','-m','pytest','tests','-q','-p','no:cacheprovider',
                 '--basetemp='+str(folder/'tmp'),'--junitxml='+str(folder/'pytest.xml')]
        print('START FULL RUN',index,'fingerprint',identity,flush=True);start=time.perf_counter()
        with (folder/'pytest.log').open('w',encoding='utf-8') as stream:
            result=subprocess.run(command,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
        record=dict(index=index,command=command,returncode=result.returncode,elapsed_seconds=time.perf_counter()-start,
                    fingerprint=identity,source_unchanged=fingerprint()==identity)
        if (folder/'pytest.xml').exists():
            cases=list(ET.parse(folder/'pytest.xml').getroot().iter('testcase'))
            record.update(collected=len(cases),failed=sum(c.find('failure') is not None for c in cases),
                          errors=sum(c.find('error') is not None for c in cases),
                          skipped=[dict(c.attrib,reason=c.find('skipped').get('message')) for c in cases if c.find('skipped') is not None])
            record['passed']=len(cases)-record['failed']-record['errors']-len(record['skipped'])
        complete.write_text(json.dumps(record,indent=2),encoding='utf-8');records.append(record)
        print('FINISHED FULL RUN',index,json.dumps(record),flush=True)
        assert record['source_unchanged'],'Source or tests changed during suite execution'
        if result.returncode:sys.exit(result.returncode)
    (OUT/(args.tag+'_complete.json')).write_text(json.dumps(records,indent=2),encoding='utf-8')


if __name__=='__main__':main()
