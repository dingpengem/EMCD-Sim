"""Read-only checkpoint/scientific and preservation checks for final review."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/physics_correction_final_integration'
PRIOR=ROOT/'outputs/physics_convention_correction_acceptance'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def scientific():
    start=json.loads((OUT/'start_state.json').read_text())
    for p,h in start['files'].items():
        if p.startswith('src'):
            assert sha(ROOT/p)==h,('Production changed during regression cleanup',p)
    summary=json.loads((PRIOR/'scientific_summary.json').read_text())
    results=[]
    for folder in sorted((PRIOR/'ni017/corrected').glob('t*')):
        saved=json.loads((folder/'complete.json').read_text())
        assert sha(folder/'results.npz')==saved['results_sha256']
        for name,h in saved['kernel_sha256'].items():assert sha(ROOT/'src/emcd_sim'/name)==h
        original=PRIOR/'ni017/original'/folder.name
        config=json.loads((folder/'configuration.json').read_text())
        assert sha(Path(config['config']['source']))==config['source_sha256']
        with np.load(folder/'results.npz',allow_pickle=False) as a,np.load(original/'results.npz',allow_pickle=False) as b:
            for method in ['bloch','fft-multislice']:
                keys=['I_A_plus','I_B_plus','I_A_minus','I_B_minus']
                new=np.array([a[method+'__'+k] for k in keys]).T
                old=np.array([b[method+'__'+k] for k in keys]).T
                np.testing.assert_allclose(new,old[:,[2,3,0,1]],rtol=1e-12,atol=1e-14)
                na,nb=(new[:,0]+new[:,2])/2,(new[:,1]+new[:,3])/2
                ma,mb=(new[:,0]-new[:,2])/2,(new[:,1]-new[:,3])/2
                for key,value in [('N_A',na),('N_B',nb),('M_A',ma),('M_B',mb),('D_mag',ma-mb),
                                  ('D_nonmag',na-nb),('D_raw',new[:,0]-new[:,1]),
                                  ('magnetic_only_percent',100*(ma-mb)/(na+nb)),
                                  ('prb_relative_dichroism_percent',100*(new[:,0]-new[:,1])/(new[:,0]+new[:,1]))]:
                    np.testing.assert_allclose(a[method+'__'+key],value,rtol=1e-12,atol=1e-14)
                np.testing.assert_allclose(new[:,0]-new[:,2],2*ma,rtol=1e-12,atol=1e-14)
                results.append(dict(case=folder.name,method=method,edges=2,passed=True))
    assert len(results)==16
    # Re-evaluate both old/new BW/MS gates from the saved full-precision spectra.
    comparisons=[]
    for label in ['original','corrected']:
        for folder in sorted((PRIOR/'ni017'/label).glob('t*')):
            with np.load(folder/'results.npz',allow_pickle=False) as f:
                for e in range(2):
                    bw=np.array([f['bloch__'+k][e] for k in ['I_A_plus','I_B_plus','I_A_minus','I_B_minus']])
                    ms=np.array([f['fft-multislice__'+k][e] for k in ['I_A_plus','I_B_plus','I_A_minus','I_B_minus']])
                    relative=float(max(abs(ms-bw)/abs(bw)))
                    percent=lambda x:100*(x[0]-x[1])/(x[0]+x[1])
                    pp=float(abs(percent(ms)-percent(bw)))
                    assert relative<=.001 and pp<=.01
                    comparisons.append(dict(label=label,case=folder.name,edge_index=e,raw_relative=relative,prb_pp=pp))
    assert len(comparisons)==32 and summary['state_exchange_passed']
    (OUT/'scientific_revalidation.json').write_text(json.dumps(dict(passed=True,method_cases=results,
        comparisons=comparisons,original_summary=summary,no_scattering_recomputed=True),indent=2),encoding='utf-8')
    print('SCIENTIFIC CHECKPOINT REVALIDATION PASS: 32 BW/MS comparisons; no solver calls',flush=True)


def preservation():
    start=json.loads((OUT/'start_state.json').read_text())
    before=json.loads((PRIOR/'pre_correction_baseline.json').read_text());original=Path(before['original_worktree']).parents[1]
    checks={}
    for label,mapping,base in [('prior_acceptance',start['prior_acceptance'],ROOT),
                               ('protected',before['protected'],original),('user',before['user'],original),
                               ('original_worktree_edits',before['old_worktree_edits'],Path('/'))]:
        bad=[p for p,h in mapping.items() if sha(base/p)!=h];assert not bad,(label,bad)
        checks[label]={'count':len(mapping),'mismatches':bad};print('VERIFIED',label,len(mapping),flush=True)
    supplement=json.loads((PRIOR/'user_guide_preservation_supplement.json').read_text())
    assert sha(Path(supplement['path']))==supplement['sha256']
    history=json.loads((PRIOR/'historical_studies_sha256.json').read_text())
    bad=[]
    for index,(p,h) in enumerate(history.items(),1):
        if sha(Path(p))!=h:bad.append(p)
        if index%1000==0:print('Historical hashes verified',index,'/',len(history),flush=True)
    assert not bad,bad;checks['historical_studies']={'count':len(history),'mismatches':bad}
    (OUT/'preservation.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
    print('ALL PROTECTED AND HISTORICAL HASHES PASS',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--preservation',action='store_true');args=parser.parse_args()
    scientific()
    if args.preservation:preservation()
