"""Audit actual saved spectra; no scattering calculation or spectrum fitting."""
import argparse,csv,json
from pathlib import Path
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from emcd_sim.gui.project_io import load_project
from emcd_sim.gui.results import draw_eels
from emcd_sim.gui.prb_benchmark import benchmark_spectra,benchmark_readout
from ni_double_channeling_full_spectra import ROOT,PILOT,RAW,fixed_reference


def folder(z,t,model,solver):return ROOT/f'{z}_{int(t):03}_{model}_{solver}'/'prepared_v1'


def compare(a,b):
    ea,eb=[r['spectra']['energy_ev'] for r in (a,b)]
    ix=np.searchsorted(ea,eb)
    if np.any(ix>=len(ea)) or not np.allclose(ea[ix],eb,rtol=0,atol=1e-10):raise ValueError('No common exact energy samples; interpolation is not validation')
    sa,sb=a['spectra'],b['spectra'];pa,pb=[benchmark_spectra(s)[0] for s in (sa,sb)]
    rows=[]
    for i,j in enumerate(ix):
        raw_a=np.array([sa[k][j] for k in RAW]);raw_b=np.array([sb[k][i] for k in RAW])
        rows.append(dict(energy_ev=float(eb[i]),max_raw_relative=float(np.max(abs(raw_a-raw_b)/np.maximum(abs(raw_a),abs(raw_b)))),
            max_raw_absolute=float(abs(raw_a-raw_b).max()),
            prb_delta_pp=float(pb['prb_relative_dichroism_percent'][i]-pa['prb_relative_dichroism_percent'][j]),
            magnetic_delta_pp=float(pb['magnetic_only_percent'][i]-pa['magnetic_only_percent'][j]),
            D_mag_delta=float(sb['D_mag'][i]-sa['D_mag'][j]),D_nonmag_delta=float(sb['D_nonmag'][i]-sa['D_nonmag'][j])))
    return rows


def write_csv(path,rows):
    if not rows:return
    keys=list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,keys);writer.writeheader();writer.writerows(rows)


def audit(result):
    s=result['spectra'];e=s['energy_ev'];raw=np.stack([s[k] for k in RAW])
    assert raw.dtype==np.float64 and np.isfinite(raw).all() and raw.min()>=0
    np.testing.assert_allclose(s['D_raw'],s['D_mag']+s['D_nonmag'],atol=1e-14)
    curves,_=benchmark_spectra(s)
    for key,v in curves.items():np.testing.assert_allclose(v,s[key],rtol=1e-13,atol=1e-13)
    c=result['config'];records=[]
    for edge,energy in (('L3',c.l3),('L2',c.l2)):
        r=benchmark_readout(result,selection='selected',energy_ev=energy)
        i=int(np.argmin(abs(e-energy)))
        records.append(dict(edge=edge,energy_ev=float(e[i]),D_mag=float(s['D_mag'][i]),D_nonmag=float(s['D_nonmag'][i]),
            magnetic_percent=r['magnetic_only_percent'],nonmagnetic_percent=r['nonmagnetic_imbalance_percent'],prb_percent=r['prb_relative_dichroism_percent']))
    return records


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--checkpoint-1',action='store_true');args=parser.parse_args()
    root=folder('001',8,'double','bloch');primary=load_project(root/'full')
    assert len(primary['spectra']['energy_ev'])>200
    rows=audit(primary);fixed=fixed_reference(primary,'001',8,'bw')
    pilot=load_project(folder('001',8,'double','fft-multislice')/'pilot')
    # The pilot shoulders need not lie on a uniform production energy grid;
    # compare its locked energies exactly, never interpolated intensities.
    ms_full=folder('001',8,'double','fft-multislice')/'full'
    if ms_full.exists():comparisons=compare(primary,load_project(ms_full))
    else:
        pilot=dict(pilot,spectra={k:v[[1,3]] for k,v in pilot['spectra'].items()})
        comparisons=compare(primary,pilot)
    passed=all(abs(r['prb_delta_pp'])<=.01 and r['max_raw_relative']<=.001 for r in comparisons)
    status=dict(passed=passed,full_bw_samples=len(primary['spectra']['energy_ev']),native_bounds_ev=primary['spectra']['energy_ev'][[0,-1]].tolist(),
        fixed_reference=fixed,max_bw_ms_prb_pp=max(abs(r['prb_delta_pp']) for r in comparisons),
        max_bw_ms_raw_relative=max(r['max_raw_relative'] for r in comparisons),ms_verified_energy_samples=len(comparisons),
        full_spectrum_bw_ms_agreement_checked=bool(ms_full.exists()),full_spectrum_convergence_claimed=False,edge_values=rows)
    (ROOT/'checkpoint_1.json').write_text(json.dumps(status,indent=2))
    if not passed:raise RuntimeError('Spectral checkpoint failed')
    print(json.dumps(status),flush=True)
    if args.checkpoint_1:return
    metrics=[];comparisons=[];single_double=[];raw_cases=[];fixed_cases=[];pilot_raw=[]
    derived_keys=('D_mag','D_nonmag','D_raw','Sigma_ref','magnetic_only_percent','nonmagnetic_imbalance_percent','prb_relative_dichroism_percent')
    derived={k:[] for k in derived_keys}
    for zone,t in (('001',8),('001',12),('017',8)):
        case_raw=[];case_derived={k:[] for k in derived_keys}
        for model in ('single','double'):
            path=folder(zone,t,model,'bloch')/'full'
            if not path.exists():raise ValueError('Incomplete reference: '+str(path))
            result=load_project(path)
            np.testing.assert_array_equal(result['spectra']['energy_ev'],primary['spectra']['energy_ev'])
            case_raw.append(np.stack([result['spectra'][k] for k in RAW],axis=-1))
            for k in derived_keys:case_derived[k].append(result['spectra'][k])
            if model=='double':fixed_cases.append(dict(zone=zone,thickness_nm=t,**fixed_reference(result,zone,t,'bw')))
            metrics.extend(dict(zone=zone,thickness_nm=t,channeling_model=model,solver='bloch',**r) for r in audit(result))
            fig=Figure(figsize=(10,7),layout='constrained');FigureCanvasAgg(fig);draw_eels(fig,result)
            for ext in ('png','svg'):fig.savefig(ROOT/f'{zone}_{t:03}_{model}_eels_emcd.{ext}',dpi=175)
        raw_cases.append(case_raw)
        for k in derived_keys:derived[k].append(case_derived[k])
        bw=load_project(folder(zone,t,'double','bloch')/'full')
        ms_path=folder(zone,t,'double','fft-multislice')/('full' if zone=='001' and t==8 and ms_full.exists() else 'pilot')
        ms=load_project(ms_path)
        selected_ms=load_project(folder(zone,t,'double','fft-multislice')/'pilot')
        pilot_raw.append(np.stack([selected_ms['spectra'][k] for k in RAW],axis=-1))
        reference=bw if ms_path.name=='full' else load_project(folder(zone,t,'double','bloch')/'pilot')
        comparisons.extend(dict(zone=zone,thickness_nm=t,coverage='full' if ms_path.name=='full' else 'five actual pilot energies',**r) for r in compare(reference,ms))
        single=load_project(folder(zone,t,'single','bloch')/'full')
        single_double.extend(dict(zone=zone,thickness_nm=t,**r) for r in compare(single,bw))
        if ms_path.name=='full':
            overlay=dict(bw,methods={'bloch':bw,'fft-multislice':ms})
            fig=Figure(figsize=(10,7),layout='constrained');FigureCanvasAgg(fig);draw_eels(fig,overlay,method='overlay')
            for ext in ('png','svg'):fig.savefig(ROOT/f'{zone}_{t:03}_double_bw_ms.{ext}',dpi=175)
    write_csv(ROOT/'edge_metrics.csv',metrics);write_csv(ROOT/'bw_ms_comparison.csv',comparisons)
    write_csv(ROOT/'single_double_comparison.csv',single_double)
    ms_primary=load_project(ms_full)
    np.savez_compressed(ROOT/'full_spectral_comparison.npz',energy_ev=primary['spectra']['energy_ev'],
        case_labels=np.array(['001_8nm','001_12nm','017_8nm']),model_labels=np.array(['single','double']),raw_labels=np.array(RAW),
        bw_raw=np.asarray(raw_cases),ms_001_8_raw=np.stack([ms_primary['spectra'][k] for k in RAW],axis=-1),
        pilot_energy_ev=PILOT,ms_pilot_raw=np.asarray(pilot_raw),
        source_sha256=np.array(primary['config'].source_sha256),
        **{'bw_'+k:np.asarray(v) for k,v in derived.items()},
        **{'ms_001_8_'+k:ms_primary['spectra'][k] for k in derived_keys})
    refined=load_project(folder('001',8,'double','bloch')/'refined')
    common=compare(refined,primary)
    refinement=dict(coarse_samples=242,refined_samples=len(refined['spectra']['energy_ev']),
        max_common_raw_relative=max(r['max_raw_relative'] for r in common),peaks=[])
    for edge,energy in (('L3',primary['config'].l3),('L2',primary['config'].l2)):
        for key in ('I_A_plus','I_B_plus','D_mag','prb_relative_dichroism_percent'):
            peaks=[]
            for r in (primary,refined):
                s=r['spectra'];ix=np.flatnonzero(abs(s['energy_ev']-energy)<3);i=ix[np.argmax(abs(s[key][ix]))]
                peaks.append(dict(energy_ev=float(s['energy_ev'][i]),value=float(s[key][i])))
            refinement['peaks'].append(dict(edge=edge,observable=key,coarse=peaks[0],refined=peaks[1],
                energy_shift_ev=peaks[1]['energy_ev']-peaks[0]['energy_ev'],value_change=peaks[1]['value']-peaks[0]['value']))
    (ROOT/'energy_refinement.json').write_text(json.dumps(refinement,indent=2))
    accepted=all(abs(r['prb_delta_pp'])<=.01 and r['max_raw_relative']<=.001 for r in comparisons)
    acceptance=dict(passed=accepted,max_bw_ms_prb_pp=max(abs(r['prb_delta_pp']) for r in comparisons),
        max_bw_ms_raw_relative=max(r['max_raw_relative'] for r in comparisons),comparisons=len(comparisons),
        full_spectrum_case='[001] 8 nm; 242 native samples',selected_energy_cases='[001] 12 nm and [017] 8 nm; five samples each',
        common_grid_raw_invariance=refinement['max_common_raw_relative'],full_spectrum_numerical_convergence_claimed=False)
    acceptance['fixed_reference_all_bw_cases']=fixed_cases
    (ROOT/'spectral_acceptance.json').write_text(json.dumps(acceptance,indent=2))
    if not accepted:raise RuntimeError('BW/MS spectral gate failed; thresholds unchanged')
    performance=[]
    for zone,t,solver in (('001',8,'bloch'),('001',12,'bloch'),('017',8,'bloch'),('001',8,'fft-multislice')):
        p=json.loads((folder(zone,t,'double',solver)/'full_performance.json').read_text())
        n=p['numerics'];before=p['ram_before']['process_rss_mib']
        performance.append(dict(zone=zone,thickness_nm=t,solver=solver,energy_samples=p['energy_samples'],
            elapsed_seconds=p['elapsed_seconds'],dense_estimate_mib=n['dense_working_estimate_mib'],
            estimated_working_mib=n['estimated_working_mib'],rss_before_mib=before,rss_after_mib=p['ram_after']['process_rss_mib'],
            estimated_total_peak_from_before_snapshot_mib=before+128+1.25*n['estimated_working_mib'],
            note='Total estimate reconstructed from pre-run RSS and existing allocation estimator; not measured peak RSS. Run reused compatible pilot energy checkpoints.'))
    write_csv(ROOT/'performance.csv',performance)
    print(json.dumps(acceptance),flush=True)
    print('Scientific tables and genuine full-spectrum figures saved',flush=True)


if __name__=='__main__':main()
