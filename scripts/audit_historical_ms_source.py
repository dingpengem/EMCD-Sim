"""Recover the exact old fingerprint and audit known subsequent changes.

Does not replace historical metadata or admit arbitrary source hashes.
"""
import ast,hashlib,json,subprocess,sys,types,time
from pathlib import Path
import numpy as np
import ni_emcd_complete_thickness as current_audit
from emcd_sim.double_channeling import equivalent_site_phases

HISTORICAL='be8c3c34477f2a197646bf07f01a64d38fde1b33'
EXPECTED='625fdc503711f06f3eeaad37893d9464fc108e4b47b8fa3dc9354d65a798d3df'
PATH='src/emcd_sim/multislice_double_channeling.py'
OUT=Path('outputs/angular_resolution_convergence')


def recovered_source():
    committed=subprocess.check_output(['git','show',HISTORICAL+':'+PATH])
    assert committed.startswith(b'\xef\xbb\xbf') and committed.endswith(b'\n')
    assert committed.count(b'return response,diagnostics\n')==1
    recovered=committed.replace(b'return response,diagnostics\n',b'return response,diagnostics\r\n')
    recovered=recovered[:-1]+b'\r\n'
    assert hashlib.sha256(recovered).hexdigest()==EXPECTED
    assert ast.dump(ast.parse(recovered.decode('utf-8-sig')))==ast.dump(ast.parse(committed.decode('utf-8-sig')))
    return recovered


def audit():
    old=recovered_source();aliases,default=current_audit.implementation_audit()
    old_double=subprocess.check_output(['git','show',HISTORICAL+':src/emcd_sim/double_channeling.py']).decode('utf-8-sig')
    current_double=Path('src/emcd_sim/double_channeling.py').read_text(encoding='utf-8-sig')
    function=lambda source,name:next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name==name)
    assert ast.dump(function(old_double,'dipole_kernel'))==ast.dump(function(current_double,'dipole_kernel'))
    # Independent algebraic check: four incoherent FCC site events and weighted
    # unique site phases must yield the same Cartesian response for arbitrary amplitudes.
    rng=np.random.default_rng(97193)
    h=np.array([(0,0,0),(2,0,0),(-2,0,0),(0,2,0),(1,1,1)])
    positions=np.array([[0,0,0],[0,.5,.5],[.5,0,.5],[.5,.5,0]])
    delta=h[None,:,:]-h[:,None,:]
    phases=np.exp(2j*np.pi*np.einsum('ghc,sc->sgh',delta,positions))
    grouped,weights=equivalent_site_phases(h,h,positions)
    amplitude=rng.normal(size=(5,5,3))+1j*rng.normal(size=(5,5,3))
    def response(p,w):
        vectors=np.einsum('gha,sgh->sa',amplitude,p)
        return np.einsum('s,sa,sb->ab',w,vectors,vectors.conj())
    a=response(phases,np.ones(4)/4);b=response(grouped,weights)
    np.testing.assert_allclose(a,b,rtol=2e-14,atol=2e-13)
    rows=[]
    prior=Path('outputs/ni_double_channeling_ms_validation')
    reproduction=Path('outputs/ni_double_channeling_full_benchmark/reproduction')
    for t in (10,12,20,30):
        with np.load(prior/'checkpoints'/f'primary_t{t}.npz',allow_pickle=False) as f:reference=f['raw'].copy()
        with np.load(reproduction/f't{t}.npz',allow_pickle=False) as f:actual=f['raw'][3].copy()
        np.testing.assert_allclose(actual,reference,rtol=2e-12,atol=1e-14)
        rows.append(dict(thickness_nm=t,max_raw_absolute=float(abs(actual-reference).max())))
    metadata=json.loads((prior/'configuration.json').read_text())
    recorded={str(Path(p).resolve().relative_to(Path.cwd())).replace('\\','/'):sha for p,sha in metadata['implementation_sha256'].items()}
    assert recorded[PATH]==EXPECTED
    return dict(recovered_exact_hash=EXPECTED,current_sha256=hashlib.sha256(Path(PATH).read_bytes()).hexdigest(),
        historical_encoding=dict(utf8_bom=old.startswith(b'\xef\xbb\xbf'),crlf_boundaries=old.count(b'\r\n'),total_newlines=old.count(b'\n')),
        historical_git_commit=HISTORICAL,files_in_historical_hash_record=recorded,
        newline_cause='PowerShell Set-Content and Add-Content retained LF inside here-strings and appended CRLF at each boundary; UTF-8 BOM retained. Git normalized the two CRLF boundaries.',
        known_changes='A: BOM/newlines, cancellation and optional prepared arguments. B: multiplicity-weighted grouping of equivalent-site phases, default FCC harmonic selection. Oriented projected_geometry is an explicit extension, not the old cubic default.',
        current_default_path_audit=default,
        dipole_kernel_ast_equal_to_original=True,
        equivalent_site_response_max_absolute=float(abs(a-b).max()),existing_four_point_reproduction=rows,
        qualification='B is validated for the recorded cubic/systematic-row baseline by existing raw-state reproduction. This is not a global equivalence claim for arbitrary structures or the new [017] model.')


def legacy_hash_compatible(path,expected):
    """Narrow compatibility: exact recovered legacy MS hash plus strict current audit."""
    normalized=Path(path).resolve().relative_to(Path.cwd()).as_posix()
    if normalized==PATH and expected==EXPECTED:
        audit()
        return True
    if normalized=='src/emcd_sim/double_channeling.py':
        aliases,_=current_audit.implementation_audit()
        if expected in aliases[normalized]:return True
        if expected=='c0d85049d1681587b357ca1c70694373bae26c142c04692cfb1b0a801758f6ae':
            old=subprocess.check_output(['git','show',HISTORICAL+':'+normalized])
            assert hashlib.sha256(old.replace(b'\n',b'\r\n')).hexdigest()==expected
            audit()
            return True
        return False
    return False


def main():
    OUT.mkdir(exist_ok=True);report=audit()
    (OUT/'hash_reconstruction.json').write_text(json.dumps(dict(found=True,expected_sha256=EXPECTED,
        method='Pinned original git source plus the two PowerShell CRLF boundaries and retained BOM',historical_git_commit=HISTORICAL),indent=2))
    # Small independent kernel comparison, not a production recalculation:
    # two detector directions in the original 11-beam cubic row at one energy.
    path=OUT/'historical_direct_equivalence.npz'
    current=hashlib.sha256(Path(PATH).read_bytes()).hexdigest()
    if path.exists():
        with np.load(path,allow_pickle=False) as f:
            assert str(f['current_sha256'])==current
            old_response=f['old_response'];new_response=f['new_response'];seconds=float(f['seconds'])
    else:
        module=types.ModuleType('emcd_sim._recovered_ms_audit');module.__package__='emcd_sim';sys.modules[module.__name__]=module
        exec(compile(recovered_source().decode('utf-8-sig'),'<exact recovered historical MS source>','exec'),module.__dict__)
        from emcd_sim.multislice_double_channeling import multislice_double_channeling_response
        c=current_audit.study.base.context('001',cutoff=2.2)
        assert len(c['hkl'])==11
        args=dict(fft_grid=32,potential_cutoff=2.2,systematic_row=True,row_reduction=True,depth_steps=257,slice_step_nm=.04)
        start=time.perf_counter()
        old_response,_=module.multislice_double_channeling_response(c['model'].elastic,831.4778,np.asarray(c['centers']),10,**args)
        new_response,_=multislice_double_channeling_response(c['model'].elastic,831.4778,np.asarray(c['centers']),10,**args)
        seconds=time.perf_counter()-start
        np.savez_compressed(path,old_response=old_response,new_response=new_response,seconds=seconds,current_sha256=np.array(current))
    np.testing.assert_allclose(old_response,new_response,rtol=2e-12,atol=1e-14)
    report['independent_direct_kernel_check']=dict(directions=2,thickness_nm=10,energy_ev=831.4778,
        geometry='Original 11-beam [001] systematic-row baseline; FFT32/depth257/step0.04/potential2.2',
        seconds=seconds,max_response_absolute=float(abs(old_response-new_response).max()))
    (OUT/'historical_ms_source.py').write_bytes(recovered_source())
    (OUT/'historical_source_audit.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
