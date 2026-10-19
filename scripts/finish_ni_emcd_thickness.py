"""Finish reports/controls only after the checkpointed full scan exits.

Can wait on the existing Windows worker; never starts a duplicate full scan.
Commits only the explicit task files, only on the requested branch, after tests.
"""
import argparse,csv,ctypes,hashlib,json,subprocess,sys,time
from pathlib import Path
import numpy as np
import ni_emcd_complete_thickness as scan


def wait_for(pid):
    from ctypes import wintypes
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD];kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.OpenProcess(0x100000,False,pid)
    if handle:
        try:
            while kernel.WaitForSingleObject(handle,30000)==258:pass
        finally:kernel.CloseHandle(handle)


def controls(records,summary):
    if summary['numerical_gate_passed']:return []
    with (scan.ROOT/'bw_ms_comparison.csv').open(newline='') as f:rows=list(csv.DictReader(f))
    selected=[]
    for metric in ('prb_change_pp','raw_relative'):
        r=max(rows,key=lambda r:abs(float(r[metric])));key=(r['zone'],int(float(r['thickness_nm'])))
        if key not in selected:selected.append(key)
    output=[];ctx=scan.contexts()
    for zone,t in selected:
        c,d=ctx[zone]
        for engine,label,depth,step,fft in [('ms','depth513',513,.04,48),('ms','step_half',257,.02,48),('ms','fft64',257,.04,64)]+([('bw','depth513',513,.04,48)] if zone=='017' else []):
            path=scan.ROOT/'validation'/f'{zone}_{engine}_t{t:03}_{label}.npz'
            p=scan.parameters(c,d,t,engine);p.update(depth_steps=depth,maximum_slice_step_nm=step,fft_grid=fft)
            if path.exists():
                with np.load(path,allow_pickle=False) as f:
                    assert str(f['parameters_json'])==scan.encode(p);raw=f['raw'].copy()
            else:
                start=time.perf_counter();data=scan.study.engine(c,d,t,engine,fft=fft,depth=depth,step=step);raw=data['raw'];del data
                scan.save_case(path,p,raw,time.perf_counter()-start,dict(kind='targeted_control',production_profile_unchanged=True))
            output.append(dict(zone=zone,thickness_nm=t,engine=engine,control=label,
                sensitivity=scan.study.comparison(records[zone,t,engine]['raw'],raw),
                versus_production_bw=scan.study.comparison(records[zone,t,'bw']['raw'],raw)))
    return output


def report(records,summary,control_rows):
    with (scan.ROOT/'bw_ms_comparison.csv').open(newline='') as f:comparison=list(csv.DictReader(f))
    summary['worst_asymmetry_case']=max(comparison,key=lambda r:abs(float(r['prb_change_pp'])))
    summary['worst_raw_case']=max(comparison,key=lambda r:float(r['raw_relative']))
    summary['targeted_controls']=control_rows
    (scan.ROOT/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    lines=['# Full-field EMCD and complete 200 kV thickness study','',
        '**All eight series have 51 actual thickness points (0:2:100 nm).** Zero inelastic intensity is exact; its percentage is NaN.',
        'No MS interpolation, BW copying, rescaling, peak retuning or full-energy-per-thickness recomputation was used.','',
        'Full-field maps use original I_plus/I_minus at actual (qx,qy)/(qx,-qy) pairs. Detector outlines do not limit the field or require mirrored manual apertures. This mathematical pairing does not assume a symmetric nonmagnetic diffraction field. Raw maps show M(q)-M(q\') and N(q)-N(q\'); total asymmetry is 100*(I_plus(q)-I_plus(q\'))/(I_plus(q)+I_plus(q\')). Invalid denominators remain NaN with the existing floor. No aperture weighting is used as a full-field mask.',
        'Legacy aperture-restricted/corrected maps remain Advanced Diagnostics. The earlier primary formula already used the full grid when its physical-detector prerequisite passed; this patch removes that prerequisite and dependence on historical D_* fields, and explicitly identifies the full-field view.',
        'Detector-integrated spectra remain different observables: integrate raw A/B intensities first, then take their difference/sum. Moving overlays cannot change the original intensity field or its point-pair ratios. Existing EELS/solver arrays are unchanged.','',
        '## Runtime, reuse and provenance','',
        'Initial audit reused 102 BW and 16 MS geometry/thickness checkpoints (both models per checkpoint), leaving 86 joint MS jobs: 86 Single plus 86 Double cases. The initial sequential wall-time estimate was 7.64 hours, with a conservative 4.97-12.23 hour workload interval. Timings already existed at 8/12, 50 and 100 nm, so no completed case was restarted for profiling.',
        'Parameters/tensors/frame/energies/detectors/weights must match exactly. Historical byte hashes differ because of optional prepared-incoming and cancellation support; a default-path AST audit proves equivalence to the recorded baseline. Only that audited source equivalence and the previously audited scheduler change are allowed. Original checkpoint bytes are hash-checked unchanged.',
        'Fixed profile: Ni [017] full finite ZOLZ and [001] explicit (200) systematic-row approximation; 200 kV; potential 6.2 and incoming/outgoing beam 4.6 inverse Angstrom; FFT 48; 257 depth nodes; maximum MS step 0.04 nm; float64/complex128; fractional 193-grid apertures with 64 subpixels; crystal [001] magnetization rotated into each local frame; eta=beta=1; fixed native 831.4778/848.698 eV. No experimental energy calibration or geometry optimization by thickness.','',
        '## Sampled extrema','',
        '| Zone | Solver | Model | Edge | Thickness (nm) | Signed asymmetry (%) |','| --- | --- | --- | --- | ---: | ---: |']
    for r in summary['extrema']:lines.append(f"| {r['zone']} | {r['solver']} | {r['model']} | {r['edge']} | {r['thickness_nm']} | {r['asymmetry_percent']:.10g} |")
    lines+=['','These are maxima of the requested 2 nm samples, not globally converged or experimentally optimal thicknesses.','',
        f"Numerical BW/MS gate: **{'PASS' if summary['numerical_gate_passed'] else 'FAIL'}**. Maximum difference {summary['max_difference_pp']:.10g} percentage points; maximum raw-state relative difference {100*summary['max_raw_relative']:.10g}%. Thresholds remain 0.01 pp and 0.1%.",
        'Worst cases, per-thickness errors, magnetic-only/even diagnostics, sign-reversal brackets and any targeted depth/slice controls are recorded in summary.json and bw_ms_comparison.csv. A failed production-profile gate remains failed even when a focused control improves agreement; production curves are never silently replaced.',
        'Outgoing-channeling effects are assessed by the separate Single/Double sampled extrema and sign-bracket lists. BW/MS differences are numerical solver comparisons; neither solver agreement nor this profile establishes global parameter convergence or physical MDFF accuracy.','',
        '## Representative values','',
        '| Zone | Solver | Model | nm | L3 (%) | L2 (%) |','| --- | --- | --- | ---: | ---: | ---: |']
    for zone in ('001','017'):
        for engine in ('bw','ms'):
            for im,model in enumerate(('single','double')):
                for t in (8,12,20,30,50,80,100):
                    values=scan.study.base.study.base.observables(records[zone,t,engine]['raw'][im])['prb_relative_dichroism_percent']
                    lines.append(f'| {zone} | {engine} | {model} | {t} | {values[0]:.9g} | {values[1]:.9g} |')
    lines+=['','## Outputs and limits','',
        'Angular examples/arrays: outputs/full_field_emcd_maps/ (saved BW/MS Single/Double L3/L2 references; no new energy-spectrum calculations).',
        'Thickness outputs: outputs/ni_emcd_asymmetry_thickness_200kv/. Full-precision thickness_series.csv/npz, comparison CSV, configuration/provenance, runtime assessment, immutable per-case checkpoints and summary.json remain local. Twelve separate standalone figures are saved in PNG and SVG under figures/: ni{017,001}_{L3,L2}_{BW_single_double,MS_single_double,BW_MS_all_models}. Each has fixed energy, geometry, signed axes, zero baseline and real calculated samples.',
        'Focused full-field tests and final data-only integrity tests are saved under the output validation folders. No broad regression suite, voltage scan, 1 nm refinement, packaging, push or release modification is performed.',
        'The MDFF remains XMCD-constrained and approximate, without a complete DFT transition tensor. Potentials remain projected IAM, longitudinal transfer uses the existing approximation, absolute EELS/counts are uncalibrated, and numerical convergence is representative. Arbitrary intensities/percentages are not experimental SNR.']
    Path('docs/FULL_FIELD_EMCD_THICKNESS_200KV.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--watch-pid',type=int);parser.add_argument('--commit',action='store_true');args=parser.parse_args()
    if args.watch_pid:wait_for(args.watch_pid)
    progress=json.loads((scan.ROOT/'progress.json').read_text())
    if not progress['complete']:raise RuntimeError('Worker exited with incomplete scan; completed checkpoints are preserved. Resume missing points only.')
    aliases,_=scan.implementation_audit();records,rejected=scan.inventory(scan.contexts(),aliases);assert not rejected and len(records)==204
    scan.export(records)
    summary=json.loads((scan.ROOT/'summary.json').read_text());control_rows=controls(records,summary);report(records,summary,control_rows)
    validation=scan.ROOT/'validation';validation.mkdir(exist_ok=True)
    subprocess.run([sys.executable,'-m','pytest','tests/test_full_thickness_series.py','-q','-p','no:cacheprovider','--junitxml='+str(validation/'final_series_tests.xml')],check=True)
    if args.commit:
        branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip()
        assert branch=='feat/full-field-emcd-thickness','Branch changed; automatic commit refused'
        assert not subprocess.check_output(['git','diff','--cached','--name-only'],text=True).strip(),'Existing staged changes; automatic commit refused'
        files=['scripts/ni_emcd_complete_thickness.py','scripts/finish_ni_emcd_thickness.py','src/emcd_sim/gui/component_display.py','src/emcd_sim/gui/results.py','tests/test_full_field_emcd.py','tests/test_full_thickness_series.py','tests/test_v060_presentation.py','docs/EMCD_GUI.md','docs/USER_GUIDE.md','docs/FULL_FIELD_EMCD_THICKNESS_200KV.md']
        subprocess.run(['git','add','--',*files],check=True);subprocess.run(['git','diff','--cached','--check'],check=True)
        subprocess.run(['git','commit','-m','Add full-field EMCD maps and complete checkpointed 200 kV thickness study'],check=True)
    (scan.ROOT/'completion.json').write_text(json.dumps(dict(complete=True,numerical_gate_passed=summary['numerical_gate_passed'],commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),pushed=False),indent=2),encoding='utf-8')
    print('Full study complete; local commit only.',flush=True)


if __name__=='__main__':
    try:main()
    except Exception as exc:
        (scan.ROOT/'finisher_error.json').write_text(json.dumps(dict(error=str(exc),complete=False,checkpoints_preserved=True),indent=2),encoding='utf-8')
        raise
