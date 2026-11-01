"""Read-only audit of protected data and the approved change boundary."""
from pathlib import Path
import ast
import hashlib
import json
import subprocess

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/physics_convention_correction_acceptance'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    before=json.loads((OUT/'pre_correction_baseline.json').read_text())
    original=Path(before['original_worktree']).parents[1]
    allowed={'src/emcd_sim/double_channeling.py','src/emcd_sim/single_channeling_tensor.py',
        'src/emcd_sim/multislice_double_channeling.py','tests/test_double_channeling_foundation.py',
        'tests/test_multislice_double_channeling.py','tests/test_double_channeling_full_benchmark.py',
        'tests/test_single_channeling_tensor.py'}
    source_changed=[p for p,h in before['source_hashes'].items() if sha(ROOT/p)!=h]
    assert set(p.replace('\\','/') for p in source_changed)==allowed,source_changed
    result={'source_changes':source_changed,'unchanged_tracked_source_test_data_count':len(before['source_hashes'])-len(source_changed)}
    for label,base in [('protected',original),('user',original),('old_worktree_edits',Path('/'))]:
        bad=[p for p,h in before[label].items() if sha(base/p)!=h]
        assert not bad,(label,bad)
        result[label]=dict(count=len(before[label]),mismatches=bad)
        print('VERIFIED',label,len(before[label]),flush=True)
    supplement=json.loads((OUT/'user_guide_preservation_supplement.json').read_text())
    assert sha(Path(supplement['path']))==supplement['sha256']
    result['original_user_guide_edit']=supplement
    history=json.loads((OUT/'historical_studies_sha256.json').read_text())
    bad=[p for p,h in history.items() if sha(Path(p))!=h]
    assert not bad,bad
    result['historical_studies']=dict(count=len(history),mismatches=bad)
    print('VERIFIED historical studies',len(history),flush=True)
    p='tests/test_physics_matrix_audit.py'
    old=ast.parse((OUT/'before'/p).read_text(encoding='utf-8-sig'))
    new=ast.parse((ROOT/p).read_text(encoding='utf-8-sig'))
    bodies={}
    for name in ['test_microscopic_born_dipole_conjugation','test_nontrivial_site_phase_single_double_reduction']:
        a=next(n for n in old.body if isinstance(n,ast.FunctionDef) and n.name==name)
        b=next(n for n in new.body if isinstance(n,ast.FunctionDef) and n.name==name)
        same=all(ast.dump(x)==ast.dump(y) for x,y in zip(a.body,b.body)) and len(a.body)==len(b.body)
        assert same and not b.decorator_list,name
        bodies[name]=dict(body_unchanged=True,xfail_removed=True)
    result['original_reproductions']=bodies
    result['commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    assert result['commit']==before['commit']
    assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).strip()
    result['status']=subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True)
    result['source_sha256']={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'src').rglob('*.py')}
    result['new_files_sha256']={str(p.relative_to(ROOT)):sha(p) for parent in ['tests','scripts'] for p in (ROOT/parent).glob('*physics*correction*.py')}
    (OUT/'integrity.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    diff=subprocess.check_output(['git','diff','--binary'],cwd=ROOT)
    (OUT/'tracked_changes.patch').write_bytes(diff)
    print('APPROVED CHANGE BOUNDARY AND INTEGRITY PASS',flush=True)


if __name__=='__main__':main()
