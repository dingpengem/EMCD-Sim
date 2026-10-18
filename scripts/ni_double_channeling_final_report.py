"""Checkpoint A: fixed-profile scientific tables and four nonredundant figures."""
import csv,json
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
import ni_double_channeling_final_200kv as run


def analyze(records):
    rows=[];peaks=[];crossings=[]
    for zone in ('001','017'):
        for t in run.MS_TIMES:
            a,b=(records[zone,t,e] for e in ('bw','ms'))
            for label,m in run.study.comparison(a,b).items():
                channel,edge=label.split('_')
                rows.append(dict(zone=zone,thickness_nm=t,channel=channel,edge=edge,**m))
        times=np.arange(2.,101.,2.)
        for im,model in enumerate(('single','double')):
            curves=np.array([run.study.base.study.base.observables(records[zone,t,'bw'][im])['prb_relative_dichroism_percent'] for t in times])
            for ie,edge in enumerate(('L3','L2')):
                values=curves[:,ie];index=int(np.argmax(abs(values)))
                peaks.append(dict(zone=zone,channeling_model=model,edge=edge,thickness_nm=float(times[index]),signed_prb_percent=float(values[index])))
                for i in np.flatnonzero(values[:-1]*values[1:]<0):
                    crossings.append(dict(zone=zone,channeling_model=model,edge=edge,lower_nm=float(times[i]),upper_nm=float(times[i+1])))
    return rows,peaks,crossings


def oscillations_and_model_changes(records):
    extrema=[];changes=[];signs=[]
    times=np.arange(2.,101.,2.)
    for zone in ('001','017'):
        for im,model in enumerate(('single','double')):
            curve=np.array([run.study.base.study.base.observables(records[zone,t,'bw'][im])['prb_relative_dichroism_percent'] for t in times])
            signs.append(dict(zone=zone,channeling_model=model,opposite_sign_samples=int(np.sum(curve[:,0]*curve[:,1]<0)),
                samples=len(times),same_sign_thicknesses_nm=times[curve[:,0]*curve[:,1]>0].tolist()))
            for ie,edge in enumerate(('L3','L2')):
                values=curve[:,ie];delta=np.diff(values)
                for i in np.flatnonzero(delta[:-1]*delta[1:]<0)+1:
                    extrema.append(dict(zone=zone,channeling_model=model,edge=edge,thickness_nm=float(times[i]),
                        kind='signed maximum' if delta[i-1]>0 else 'signed minimum',prb_percent=float(values[i])))
        for t in times:
            a,b=[run.study.base.study.base.observables(raw) for raw in records[zone,t,'bw']]
            for ie,edge in enumerate(('L3','L2')):
                changes.append(dict(zone=zone,thickness_nm=float(t),edge=edge,
                    prb_double_minus_single_pp=float(b['prb_relative_dichroism_percent'][ie]-a['prb_relative_dichroism_percent'][ie]),
                    magnetic_double_minus_single_pp=float(b['magnetic_only_percent'][ie]-a['magnetic_only_percent'][ie]),
                    D_mag_double_minus_single=float(b['D_mag'][ie]-a['D_mag'][ie]),
                    D_even_double_minus_single=float(b['D_even'][ie]-a['D_even'][ie])))
    return extrema,changes,signs


def main():
    root=run.ROOT
    with np.load(root/'results.npz',allow_pickle=False) as f:
        records={tuple(k):raw for k,raw in zip(json.loads(str(f['keys_json'])),f['raw'])}
    expected={(z,float(t),e) for z in ('001','017') for e,ts in (('bw',np.arange(0.,101.,2.)),('ms',(0.,)+run.MS_TIMES)) for t in ts}
    if set(records)!=expected:raise ValueError(f'Checkpoint A incomplete: {len(expected-set(records))} missing cases')
    for (zone,t,engine),raw in records.items():
        assert raw.dtype==np.float64 and np.isfinite(raw).all() and raw.min()>=0
        for r in raw:
            o=run.study.base.study.base.observables(r)
            np.testing.assert_allclose(o['D_raw'],o['D_mag']+o['D_even'],atol=1e-14)
            if not t:assert not raw.any() and np.isnan(o['prb_relative_dichroism_percent']).all()
    # Compact spectral quantities are independent of the GUI display mode.
    # Keep original four reversal states once, alongside signed differences and
    # percentages; never normalize the magnetic and even components separately.
    raw=np.asarray(list(records.values()))
    ap,bp,am,bm=np.moveaxis(raw,-1,0)
    na,nb,ma,mb=(ap+am)/2,(bp+bm)/2,(ap-am)/2,(bp-bm)/2
    denominator=na+nb
    def percent(a,b):
        out=np.full(a.shape,np.nan)
        np.divide(100*a,b,out=out,where=b>0)
        return out
    temporary=root/'results.temporary.npz'
    np.savez_compressed(temporary,keys_json=np.array(json.dumps(list(records))),raw=raw,
        energies_ev=run.study.base.ENERGIES,N_A=na,N_B=nb,M_A=ma,M_B=mb,
        D_mag=ma-mb,D_nonmag=na-nb,D_raw=ap-bp,Sigma_ref=denominator,
        magnetic_only_percent=percent(ma-mb,denominator),
        nonmagnetic_imbalance_percent=percent(na-nb,denominator),
        prb_relative_dichroism_percent=percent(ap-bp,ap+bp))
    temporary.replace(root/'results.npz')
    rows,peaks,crossings=analyze(records)
    extrema,changes,signs=oscillations_and_model_changes(records)
    run.study.base.study.base.write_csv(root/'bw_ms_comparison.csv',rows)
    run.study.base.study.base.write_csv(root/'sampled_extrema.csv',peaks)
    run.study.base.study.base.write_json(root/'zero_crossing_brackets.json',crossings)
    run.study.base.study.base.write_csv(root/'oscillation_extrema.csv',extrema)
    run.study.base.study.base.write_csv(root/'channeling_model_changes.csv',changes)
    run.study.base.study.base.write_json(root/'edge_sign_behavior.json',signs)
    inherited=json.loads((run.uniform.PRIOR/'factor_status.json').read_text())
    basis=json.loads((run.uniform.ROOT/'status.json').read_text())
    prerequisites=inherited['potential_cutoff']['passed'] and inherited['fft_slice_depth']['passed'] and basis['uniform_gate_passed']
    passed=prerequisites and all(abs(r['prb_change_pp'])<=.01 and r['raw_relative']<=.001 for r in rows)
    status=dict(checkpoint_A_passed=passed,complete=True,cases=len(records),
        max_bw_ms_prb_pp=max(abs(r['prb_change_pp']) for r in rows),max_bw_ms_raw_relative=max(r['raw_relative'] for r in rows),
        failed_comparisons=[r for r in rows if abs(r['prb_change_pp'])>.01 or r['raw_relative']>.001],
        sampled_extrema=peaks,edge_sign_behavior=signs,inherited_representative_controls_passed=prerequisites,
        full_curve_globally_converged=False)
    run.study.base.study.base.write_json(root/'checkpoint_A.json',status)
    def figure(name):
        fig=Figure(figsize=(10,6),layout='constrained');FigureCanvasAgg(fig);return fig
    for ie,edge in enumerate(('L3','L2')):
        fig=figure(edge);axes=fig.subplots(1,2)
        for ax,zone in zip(axes,('001','017')):
            for im,model in enumerate(('Single','Double')):
                ts=np.arange(0.,101.,2.)
                curve=[run.study.base.study.base.observables(records[zone,float(t),'bw'][im])['prb_relative_dichroism_percent'][ie] for t in ts]
                ax.plot(ts,curve,label='BW '+model,color=f'C{im}')
                ms=[run.study.base.study.base.observables(records[zone,t,'ms'][im])['prb_relative_dichroism_percent'][ie] for t in run.MS_TIMES]
                ax.plot(run.MS_TIMES,ms,'o',mfc='none',color=f'C{im}',label='MS '+model)
            ax.axhline(0,color='.5',lw=.7);ax.set(title=f'Ni [{zone}]',xlabel='Thickness (nm)',ylabel=f'{edge} PRB dichroism (%)');ax.grid(alpha=.2);ax.legend(fontsize=8)
        fig.suptitle('200 kV | fixed native energy | BW: 2 nm samples; MS: discrete controls')
        for ext in ('png','svg'):fig.savefig(root/f'{edge}_thickness.{ext}',dpi=170)
    fig=figure('comparison');axes=fig.subplots(1,2)
    for ax,zone in zip(axes,('001','017')):
        for edge in ('L3','L2'):
            selected=[r for r in rows if r['zone']==zone and r['channel']=='double' and r['edge']==edge]
            ax.plot([r['thickness_nm'] for r in selected],[r['prb_change_pp'] for r in selected],'o',label=edge)
        for bound in (-.01,.01):ax.axhline(bound,color='k',lw=.7)
        ax.set(title=f'Ni [{zone}]',xlabel='Thickness (nm)',ylabel='Double MS − BW (percentage points)');ax.legend();ax.grid(alpha=.2)
    for ext in ('png','svg'):fig.savefig(root/f'BW_MS_comparison.{ext}',dpi=170)
    # Summarize existing controls without rerunning their physics.
    controls=[dict(label='Potential cutoff (inherited)',**inherited['potential_cutoff'])]
    with (run.uniform.ROOT/'summary.csv').open(newline='') as f:summary=list(csv.DictReader(f))
    for engine in ('bw','ms'):
        selected=[r for r in summary if r['category']=='independent_basis' and r['label']==engine]
        controls.append(dict(label=engine.upper()+' basis (4 representative points)',
            max_prb_change_pp=max(float(r['max_prb_pp']) for r in selected),
            max_raw_relative=max(float(r['max_raw_percent'])/100 for r in selected)))
    controls.append(dict(label='FFT / slice / depth (inherited)',**inherited['fft_slice_depth']))
    controls.append(dict(label='BW/MS (7 current MS controls)',max_prb_change_pp=status['max_bw_ms_prb_pp'],max_raw_relative=status['max_bw_ms_raw_relative']))
    run.study.base.study.base.write_json(root/'convergence_summary.json',controls)
    fig=Figure(figsize=(11,6),layout='constrained');FigureCanvasAgg(fig);axes=fig.subplots(2,1)
    for ax,key,scale,limit,label in zip(axes,('max_prb_change_pp','max_raw_relative'),(1.,100.),(.01,.1),
            ('Maximum absolute PRB change (percentage points)','Maximum relative raw-state change (%)')):
        ax.barh([r['label'] for r in controls],[scale*r[key] for r in controls],color=['.6','C0','C1','.6','C2'])
        ax.axvline(limit,color='k',lw=.9);ax.set_xlabel(label);ax.grid(axis='x',alpha=.2)
    fig.suptitle('Distinct numerical checks; inherited controls were not repeated over the full curve')
    for ext in ('png','svg'):fig.savefig(root/f'convergence_summary.{ext}',dpi=170)
    text=['# Final 200 kV Ni double-channeling benchmark','',f"Checkpoint A: **{'PASS' if passed else 'FAIL'}**.",'',
        'The BW series contains 51 requested points per geometry (0–100 nm, 2 nm increments). MS uses seven nonzero representative thicknesses plus the exact zero-thickness boundary. Neither 2 nm sampling nor representative numerical controls establishes continuous global extrema or convergence at every thickness.','',
        '|Geometry|Model|Edge|Strongest sampled thickness (nm)|Signed PRB (%)|','|---|---|---|---:|---:|']
    text += [f"|[{r['zone']}]|{r['channeling_model']}|{r['edge']}|{r['thickness_nm']:g}|{r['signed_prb_percent']:.8f}|" for r in peaks]
    text += ['',f"Maximum matched BW/MS PRB difference: {status['max_bw_ms_prb_pp']:.8f} percentage points; maximum raw-state relative error: {100*status['max_bw_ms_raw_relative']:.8f}%. Limits remain 0.01 pp and 0.1%.",'',
        'Fixed evaluation energies are 831.4778 and 848.698 eV. The unchanged active source has an automatically audited L3 extremum at 831.271 eV; the final series deliberately retains the previously validated evaluation energy instead of retuning to that extremum. There is no energy-axis shift.','',
        'Profile: potential Fourier cutoff 6.2 Å^-1, incoming/outgoing beam cutoff 4.6 Å^-1, FFT 48, 257 depth nodes, maximum MS step 0.04 nm; float64/complex128. [001] is the existing systematic-row potential/basis; [017] retains its genuine full 2D projected basis. Crystal [001] magnetization is rotated into each local frame, eta=beta=1; physical detectors and fractional weights are unchanged.','',
        'Single means entrance-only channeling; Double additionally propagates the post-loss electron from the ionization depth to the detector. PRB is 100(A+−B+)/(A++B+). Magnetic and reversal-even components use the common N_A+N_B denominator. Percentages are formed after depth and detector integration; zero thickness has zero raw intensity and undefined (NaN) percentages.','',
        'All reversal states, component differences and denominators are saved in observables.csv and results.npz. Sign changes are reported as 2 nm brackets in zero_crossing_brackets.json; zero intensity at the origin is not counted as an EMCD sign crossing. Raw-state and signed magnetic-difference BW/MS comparisons are in bw_ms_comparison.csv.','',
        'oscillation_extrema.csv lists sampled signed maxima and minima, rather than imposing a single oscillation period on a multibeam wavefield. edge_sign_behavior.json counts opposite L3/L2 signs and identifies any same-sign sampled exceptions. channeling_model_changes.csv records the actual single-to-double magnetic and PRB changes; these physical-model changes are not numerical solver errors.','',
        'Potential-cutoff, independent beam-basis, FFT, slice and depth controls are inherited from the preceding focused studies, not repeated over this full curve. The potential and FFT/slice/depth controls used beam cutoff 3.8; independent 3.8-to-4.6 basis changes were checked at 8/12/30/100 nm. This is not a joint convergence proof at every enlarged-basis thickness. BW/MS agreement at fixed settings does not establish physical-model accuracy. The MDFF remains XMCD-constrained rather than a complete complex DFT MDFF; the potential remains projected IAM, without new atomic-3D physics. No full energy-resolved EELS spectrum is inferred from the two selected energies.']
    (root/'SCIENTIFIC_REPORT.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
    print(json.dumps(status),flush=True)


if __name__=='__main__':main()
