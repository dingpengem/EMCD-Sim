"""Read-only A/B release checkpoints from existing full-precision references."""
import hashlib,json,platform,subprocess,sys
from pathlib import Path
from importlib.metadata import version
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from ni_double_channeling_spectral_report import compare,folder,audit
from emcd_sim.gui.project_io import load_project
from emcd_sim.gui.prb_benchmark import benchmark_spectra

ROOT=Path('outputs/windows_beta_acceptance');ROOT.mkdir(parents=True,exist_ok=True)


def main():
    source=Path('data/wien2k_ni/Ni_fm.xmcd');sha=hashlib.sha256(source.read_bytes()).hexdigest()
    provenance=json.loads(Path('outputs/ni_double_channeling_final_200kv/provenance.json').read_text())
    assert sha==provenance['source_sha256']
    with np.load('outputs/ni_double_channeling_final_200kv/results.npz',allow_pickle=False) as a:
        previous={tuple(k):v for k,v in zip(json.loads(str(a['keys_json'])),a['raw'])}
    references=[]
    for zone,t,model in (('001',12,'single'),('001',8,'double'),('017',12,'single'),('017',8,'double')):
        mi=int(model=='double');reference=previous[zone,float(t),'bw'][mi]
        if zone=='017' and t==12:
            with np.load(f'outputs/ni_double_channeling_final_200kv/gui_validation/{zone}_{t:03}_{model}.npz',allow_pickle=False) as a:actual=a['raw'][0]
        else:
            r=load_project(folder(zone,t,model,'bloch')/'full');s=r['spectra'];ix=np.searchsorted(s['energy_ev'],[831.4778,848.698]);actual=np.stack([s[k][ix] for k in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus')],axis=-1)
        relative=float(np.max(abs(actual-reference)/np.maximum(abs(actual),abs(reference))))
        assert relative<=.001
        def curves(raw):return benchmark_spectra(dict(zip(('I_A_plus','I_B_plus','I_A_minus','I_B_minus'),raw.T)))[0]
        aa,bb=curves(actual),curves(reference)
        gap=float(abs(aa['prb_relative_dichroism_percent']-bb['prb_relative_dichroism_percent']).max());assert gap<=.01
        references.append(dict(zone=zone,thickness_nm=t,model=model,raw_max_relative=relative,prb_max_difference_pp=gap,prb_percent=aa['prb_relative_dichroism_percent'].tolist()))
    checks=[]
    for z,t in (('001',8),('001',12),('017',8)):
        tag='full' if (z,t)==('001',8) else 'pilot'
        b,m=[load_project(folder(z,t,'double',engine)/tag) for engine in ('bloch','fft-multislice')]
        data=compare(b,m)
        for row in data:assert row['max_raw_relative']<=.001 and abs(row['prb_delta_pp'])<=.01 and abs(row['magnetic_delta_pp'])<=.01
        checks.append(dict(zone=z,thickness_nm=t,samples=len(data),max_prb_pp=max(abs(r['prb_delta_pp']) for r in data),max_raw_relative=max(r['max_raw_relative'] for r in data)))
    for zone,n,row in (('001',17,True),('017',59,False)):
        r=load_project(folder(zone,8,'double','bloch')/'full')
        assert len(r['metadata']['beam_hkl'])==n and r['config'].systematic_row==row and abs(r['metadata']['s_target'])<1e-12
        assert r['config'].l3==831.4778 and r['config'].l2==848.698 and r['config'].eta==r['config'].beta==1
        assert r['config'].source_sha256==sha
    report=dict(checkpoint_A='PASS',checkpoint_B='PASS',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip(),source_sha256=sha,versions={p:version(p) for p in ('emcd-sim','numpy','scipy','matplotlib','ase','PySide6')},python=sys.version,platform=platform.platform(),references=references,bw_ms=checks,
        method='Read-only comparison against saved full-precision independently validated results; no new production calculation',
        scientific_audit='Actual GUI dispatch tests exercise six routes. Double core retains incoming fields, localized depth-distributed ionization, post-loss outgoing propagation, complex MDFF, depth and fractional detector integration. No solver physics modified for acceptance.')
    (ROOT/'checkpoint_AB.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)


if __name__=='__main__':main()
