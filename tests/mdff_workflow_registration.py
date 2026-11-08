"""Exact active replacements: execute old contracts on real parent, new on current."""
import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import uuid
from mdff_usability_source_scope import ROOT,WORKFLOWS,load_scope,read,digest


def parent_snapshot(config,request):
    if hasattr(config,'_mdff_parent_snapshot'):return config._mdff_parent_snapshot
    scope,parents=load_scope()
    folder=request.getfixturevalue('tmp_path_factory').mktemp('authenticated-mdff-parent')
    boundary=ROOT.resolve()
    for path,entry in scope['protected'].items():
        raw=read(ROOT,path,resolved_root=boundary);mode=entry['mode']
        assert digest(raw,mode)==entry[mode+'_sha256'],'Historical workflow source changed: '+path
        target=folder/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    for path,raw in parents.items():
        target=folder/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    # The retained legacy workflows use current Results and CIF adapters.
    # Include their ordinary dependencies without replacing any
    # archived parent source or changing the historical test assertions.
    support=('src/emcd_sim/gui/multisite_results_controls.py',
             'src/emcd_sim/gui/multisite_results.py','src/emcd_sim/gui/multisite_export.py',
             'src/emcd_sim/crystallographic_sites.py','src/emcd_sim/multisite.py')
    for path in support:
        target=folder/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/path).read_bytes())
    config._mdff_parent_snapshot=folder
    config._mdff_parent_paths=sorted(set(scope['protected'])|set(parents)|set(support))
    return folder


def run_contract(root,node,folder,source_paths):
    folder.mkdir(parents=True,exist_ok=False)
    def inventory():return {p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in source_paths}
    before=inventory()
    (folder/'source-before.json').write_text(json.dumps(before,indent=2,sort_keys=True),encoding='utf-8')
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONHASHSEED='0',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',QT_QPA_PLATFORM='offscreen',PYTHONPATH=str(root/'src')+os.pathsep+str(root/'tests'))
    # Keep generated managed-source/project names below native Windows limits.
    # Evidence remains alongside the bridge; only disposable test inputs move.
    temp_parent=ROOT.parents[1]/'outputs'/'mdff-reg-tmp'
    temp_parent.mkdir(parents=True,exist_ok=True)
    temp=temp_parent/uuid.uuid4().hex[:12]
    assert not temp.exists() and temp.resolve().is_relative_to(temp_parent.resolve())
    command=[sys.executable,'-u','-m','pytest',node,'--rootdir='+str(root),'--basetemp='+str(temp),'-p','no:cacheprovider','-q','--tb=short','--junitxml='+str(folder/'checks.xml')]
    with (folder/'checks.log').open('wb') as log:result=subprocess.run(command,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT)
    after=inventory()
    (folder/'source-after.json').write_text(json.dumps(after,indent=2,sort_keys=True),encoding='utf-8')
    record=dict(command=command,cwd=str(root),python=sys.executable,environment={k:env[k] for k in ('PYTHONPATH','PYTHONDONTWRITEBYTECODE','PYTHONHASHSEED','QT_QPA_PLATFORM','OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')},exit_code=result.returncode,source_unchanged=before==after,
        hashes={name:hashlib.sha256((folder/name).read_bytes()).hexdigest() for name in ('source-before.json','source-after.json','checks.xml','checks.log')})
    (folder/'run.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    assert before==after,'Workflow subprocess changed its source inventory'
    assert result.returncode==0,(folder/'checks.log').read_text(encoding='utf-8',errors='replace')


def install(config,items):
    for item in items:
        node=item.nodeid.replace('\\','/')
        prefix='tests/test_atomic_parameter_editor.py::'
        if not node.startswith(prefix):continue
        name=node[len(prefix):]
        if name not in WORKFLOWS:continue
        load_scope()  # Authenticate mapping and original historical test bytes.
        target='tests/test_mdff_corrective.py::'+WORKFLOWS[name]
        item.user_properties.extend([('mdff_historical_contract',node),('mdff_current_contract',target)])
        def bridge(_item=item,_node=node,_target=target,**_):
            from unit_source_snapshots import assert_reviewed_current_sources
            from physics_source_guard import assert_registered_sources
            assert_reviewed_current_sources();assert_registered_sources()
            folder=_item._request.getfixturevalue('tmp_path')/'registered-workflow'
            parent=parent_snapshot(config,_item._request)
            declaration,_=load_scope()
            current_paths=sorted(set(declaration['protected'])|set(declaration['candidate'])|set(declaration['bootstrap']))
            run_contract(parent,_node,folder/'historical',config._mdff_parent_paths)
            run_contract(ROOT,_target,folder/'current',current_paths)
        # Keep the original collected identity and assertions intact on disk.
        # No skip/deselection: this item must pass both explicit contracts.
        item.obj=bridge
