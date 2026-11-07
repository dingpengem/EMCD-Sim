"""A retained-run list on the existing configuration project manifest.

Each calculation remains an ordinary project. The whole directory is staged
before replacement, so deletion affects disk only after a successful Save.
"""
from pathlib import Path
import json
import shutil
import uuid

from . import project_io as io
from .emcd_forward import Cancelled


def _unmanaged(source,target,managed):
    if not source.is_dir():return
    for child in source.iterdir():
        if child.name in managed:continue
        if child.is_symlink() or (child.is_dir() and any(p.is_symlink() for p in child.rglob('*'))):
            raise ValueError('Project attachments contain links; use Save As')
        target.mkdir(parents=True,exist_ok=True)
        destination=target/child.name
        if destination.exists():raise ValueError('Attachment conflicts with saved data: '+child.name)
        if child.is_dir():shutil.copytree(child,destination)
        else:shutil.copy2(child,destination)


def save_collection(state,runs,path,*,replace_existing=False,cancelled=lambda:False,progress=lambda s:None):
    root=Path(path).resolve();previous={}
    if root.exists():
        if not replace_existing:raise FileExistsError('Save As requires a new project folder or explicit replacement approval')
        if not (root/'project.json').is_file():raise ValueError('Only an existing EMCD project can be replaced')
        previous=json.loads((root/'project.json').read_text(encoding='utf-8'))
    # Keep the outer staging name short: each existing run writer also stages
    # its own directory, and nested long names exceed Windows path limits.
    temp=root.parent/('.p_'+uuid.uuid4().hex[:12])
    backup=root.parent/('.b_'+uuid.uuid4().hex[:12])
    def check():
        if cancelled():raise Cancelled()
    try:
        io.save_configuration(state,temp,cancelled=cancelled,progress=progress)
        records=[];ids=set()
        for record,result in runs:
            check();identity=record['id']
            if not identity or Path(identity).name!=identity or identity in ('.','..') or identity in ids:
                raise ValueError('Calculation identifiers must be unique simple directory names')
            ids.add(identity);relative='calculations/'+identity
            io.save_project(result,temp/relative,cancelled=cancelled,progress=progress)
            records.append(dict(record,path=relative))
        # Preserve only unrelated attachments, not deleted project-owned arrays.
        old_records=previous.get('calculations',[])
        if root.exists():
            _unmanaged(root,temp,set(previous.get('files',{}))|{'project.json','calculations'})
            old_calculations=root/'calculations'
            if old_calculations.is_symlink():raise ValueError('Project history contains a link; use Save As')
            if old_calculations.is_dir():
                known={r['id'] for r in old_records}
                _unmanaged(old_calculations,temp/'calculations',known)
                for old in old_records:
                    check()
                    if (root/old['path']).is_symlink():raise ValueError('Calculation folder contains a link')
                    folder=(root/old['path']).resolve()
                    if folder.parent!=old_calculations.resolve():raise ValueError('Unsafe calculation folder')
                    if (folder/'project.json').is_file():
                        manifest=json.loads((folder/'project.json').read_text(encoding='utf-8'))
                        _unmanaged(folder,temp/'calculations'/old['id'],set(manifest['files'])|{'project.json'})
        manifest=json.loads((temp/'project.json').read_text(encoding='utf-8'))
        manifest['calculations']=records;io._json(temp/'project.json',manifest)
        check()
        if root.exists():io._rename_folder(root,backup,cancelled)
        try:io._rename_folder(temp,root,cancelled)
        except BaseException:
            if backup.exists():io._rename_folder(backup,root)
            raise
        if backup.exists() and backup.parent==root.parent:shutil.rmtree(backup)
        return root
    finally:
        if temp.exists() and temp.parent==root.parent:shutil.rmtree(temp)


def load_collection(path,*,cancelled=lambda:False,progress=lambda s:None):
    root=Path(path).resolve();manifest=json.loads((root/'project.json').read_text(encoding='utf-8'))
    if manifest.get('kind')!='configuration':
        result=io.load_project(root,cancelled=cancelled,progress=progress)
        if result['config'].model=='multisite' and result.get('configuration'):
            state=result['configuration']
            if 'numerical_selection' in result['metadata']:state.setdefault('metadata',{})['numerical_selection']=result['metadata']['numerical_selection']
        else:
            state=dict(structure=io.restore_structure(result['structure_snapshot']),settings=result['settings'],config=result['config'],
                magnetization_mode='global',metadata=result['metadata'],source_overrides={'config':result.get('source_overrides',{}).get('mdff',result.get('source_overrides',{}).get('xmcd',result['config'].source))})
        return dict(path=root,state=state,runs=[(None,result)])
    state=io.load_configuration(root,cancelled=cancelled,progress=progress);runs=[];ids=set()
    for record in manifest.get('calculations',[]):
        if cancelled():raise Cancelled()
        folder=(root/record['path']).resolve()
        if (folder.parent!=root/'calculations' or folder.name!=record['id'] or record['id'] in ids):raise ValueError('Invalid calculation history path or identity')
        ids.add(record['id']);runs.append((record,io.load_project(folder,cancelled=cancelled,progress=progress)))
    return dict(path=root,state=state,runs=runs)
