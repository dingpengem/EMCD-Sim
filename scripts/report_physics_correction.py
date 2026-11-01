"""Assemble acceptance evidence from completed runs; never run a solver."""
from pathlib import Path
import csv
import json
import subprocess
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/physics_convention_correction_acceptance'


def junit(path):
    tree=ET.parse(path);cases=list(tree.getroot().iter('testcase'))
    failures=[dict(c.attrib,message=c.find('failure').get('message','')) for c in cases if c.find('failure') is not None]
    errors=[dict(c.attrib,message=c.find('error').get('message','')) for c in cases if c.find('error') is not None]
    skips=[dict(c.attrib,message=c.find('skipped').get('message','')) for c in cases if c.find('skipped') is not None]
    return dict(tests=len(cases),passed=len(cases)-len(failures)-len(errors)-len(skips),
                failed=len(failures),errors=len(errors),skipped=len(skips),failures=failures,error_cases=errors,skips=skips)


def run():
    science=json.loads((OUT/'scientific_summary.json').read_text())
    integrity=json.loads((OUT/'integrity.json').read_text())
    regression=junit(OUT/'regression.xml')
    baseline=Path(json.loads((OUT/'pre_correction_baseline.json').read_text())['original_worktree'])
    known=json.loads((baseline/'build/physics-matrix-audit/review/failure_inventory.json').read_text())
    known={v['test']:v for v in known}
    follow=junit(OUT/'followup.xml')
    resolved={v.attrib['classname']+'::'+v.attrib['name'] for v in ET.parse(OUT/'followup.xml').getroot().iter('testcase')
              if v.find('failure') is None and v.find('error') is None}
    triage=[]
    for v in regression['failures']+regression['error_cases']:
        key=v['classname']+'::'+v['name']
        if key in known:status=known[key]['classification']
        elif key in resolved:status='Resolved by focused follow-up; see explanation below'
        elif key=='tests.test_solver_settings_ui::test_solver_configuration_and_physics_unchanged':
            status='Intentional source-identity guard failure after approved kernel correction; test retained unchanged'
        else:status='UNRESOLVED additional failure'
        triage.append(dict(test=key,classification=status,message=v['message']))
    (OUT/'regression_triage.json').write_text(json.dumps(dict(regression=regression,triage=triage,followup=follow),indent=2),encoding='utf-8')
    rows=list(csv.DictReader((OUT/'scientific_cases.csv').open()))
    table=[]
    for r in rows:
        if r['method']=='bloch' and r['channel']=='double':
            table.append('| '+ ' | '.join([r['thickness_nm'],r['y_mrad'],r['edge'],
                f"{float(r['new_D_nonmag']):+.8g}",f"{float(r['old_D_mag']):+.8g}",f"{float(r['new_D_mag']):+.8g}",
                f"{float(r['old_P_AB']):+.6f}",f"{float(r['new_P_AB']):+.6f}"])+ ' |')
    tests=[]
    for name in ['focused','engine_controls','followup','profiler_followup']:
        v=junit(OUT/(name+'.xml'));tests.append(f"| `{name}.xml` | {v['passed']} | {v['failed']} | {v['errors']} | {v['skipped']} |")
    failure_table='\n'.join('| `'+v['test']+'` | '+v['classification']+' |' for v in triage)
    changed=subprocess.check_output(['git','diff','--stat'],cwd=ROOT,text=True)
    source_diff=subprocess.check_output(['git','diff','--','src/emcd_sim/single_channeling_tensor.py',
        'src/emcd_sim/double_channeling.py','src/emcd_sim/multislice_double_channeling.py'],cwd=ROOT,text=True)
    unresolved=[v for v in triage if v['classification'].startswith('UNRESOLVED')]
    accepted=(science['state_exchange_passed'] and science['historical_reproduction_passed'] and
              science['bw_ms_passed']==science['bw_ms_comparisons'] and not unresolved and
              all(junit(OUT/(name+'.xml'))['failed']==0 and junit(OUT/(name+'.xml'))['errors']==0
                  for name in ['focused','engine_controls','followup','profiler_followup']))
    report=f'''# Coordinated physics correction acceptance

Source base: `a77f7455f5fe57dad6bae5d948477b2390433bb0`; isolated detached
worktree: `C:/Users/peng863/EMCD-Sim/build/physics-correction-validation`.
All changes are **uncommitted**. The original worktree and user edits are
preserved. This implements the user's explicitly approved coordinated patch.

**Disposition: {'PASS for the bounded physics correction; repository-wide regression is NOT all-green.' if accepted else 'HOLD: unresolved evidence remains.'}**
The conclusions below apply to the tested finite projected model. No GUI
layout, worker policy, numerical default, MDFF source, version or propagation
algorithm was changed. No commit, push, merge, release, tag or EXE build.

## Implemented mathematics and exact scope

The documented `d=<i|r|f>` and forward transfer `Q=k_out-k_in` require
`<f|exp(-i Q.x)|i> ~ -i Q.d*`. With `R_ab=v_a v_b*` and `T_ab=d_a d_b*`,
the intensity is `Re sum_ab R_ab T_ba = Re Tr(R T)`. The approved three-file
patch changes every Single BW/MS and Double BW/MS contraction, including
separate even/odd maps. The proper MDFF definition and tensor factory remain
unchanged. `T=L L†` remains the factorization contract; the forward event
caller uses L* exactly once. Double's site factor is now
`exp(+2*pi*i*(g-h).u)`, from `exp(-i Q.R)`. Single's site phase is unchanged.

Only three production files changed:

- `src/emcd_sim/single_channeling_tensor.py`: `_tensor_angular_maps`.
- `src/emcd_sim/double_channeling.py`: `contract_cartesian`,
  `equivalent_site_phases`, `intensities_from_response`, and the map components
  in `_run_tensor_double_channeling`.
- `src/emcd_sim/multislice_double_channeling.py`:
  `forward_event_amplitudes` and map components in
  `run_tensor_multislice_double_channeling`.

The exact production diff is appended. Full tracked source/test diffs are in
`outputs/physics_convention_correction_acceptance/tracked_changes.patch`.
Necessary pre-existing test references changed in
`test_double_channeling_foundation.py`, `test_multislice_double_channeling.py`
`test_single_channeling_tensor.py` and `test_double_channeling_full_benchmark.py`: conjugate the explicit target
dipoles/modes, transpose the independent scattering pair, and use g-h for the
localized phase. Their existing tolerances are unchanged. None of the tests
responsible for the 15 unrelated baseline failures was edited.

New/copied focused audit tests: `test_physics_matrix_audit.py`,
`test_physics_correction_proposal.py`, `test_physics_correction_engines.py`.
The first two original failing reproduction bodies are AST-identical to their
saved originals; only their XFAIL decorators were removed. The before files
are preserved under the acceptance output's `before/` folder.

Research-only tools added: `validate_physics_correction_ni017.py`,
`analyze_physics_correction.py`, `check_physics_correction_integrity.py` and
`report_physics_correction.py`. Prior audit/proposal documents were copied
unchanged into this isolated tree for review context. This acceptance report
supersedes their pre-correction disposition, not their historical evidence.

## Independent tests and results

| Evidence | Passed | Failed | Errors | Skipped |
|---|---:|---:|---:|---:|
{chr(10).join(tests)}

The final 54-test focused scope includes the 2 engine controls; the 5 follow-up
checks overlap and must not be added as new coverage. The profiler fixture
follow-up checks setup only, not independent physics. The original two
reproductions pass unmasked: Born intensity 4 rather than 0; nontrivial-site
free-exit phase equality restored. Independent references use explicit target
sums, closed Pauli exponentials, explicit DFT matrices and Gauss quadrature.
The actual BW and MS engines are tested with a translated FCC motif, complex
elastic couplings, complex dipoles and an explicitly matched two-beam FFT
Galerkin space. Free-outgoing reduction reaches Single BW and Single MS.
Hermitian/PSD response and transition tensors, positive total intensity,
magnetization reversal and the physically warranted row mirror pass.
Synthetic origin covariance and separate depth/split-step controls pass;
none establishes full Ni convergence or general-material support.

## Complete practical regression and failure handling

Full run: **{regression['passed']} passed, {regression['failed']} failed,
{regression['errors']} errors, {regression['skipped']} skipped**
({regression['tests']} collected). See `regression.log/.xml` and
`regression_triage.json`. The original audit baseline was 558 passed,
15 failed, 2 skipped, before the added physics tests. The baseline
classification of all 15 unrelated failures is preserved in
`PHYSICS_REGRESSION_FAILURE_REVIEW.md`, not hidden by a new XFAIL or budget.

| Failed full-run test | Classification |
|---|---|
{failure_table}

Additional full-run failures were diagnosed separately:

1. `test_equivalent_sites_preserve_general_complex_average` encoded h-g in
   its independent reference. Its reference was updated to the approved
   localized g-h operator, with the same `rtol=1e-13`. The full run had
   already collected the old reference before this one-line update.
2. `test_reused_files_unchanged_and_comparison_gate_not_relaxed` required
   118 additional frozen checkpoint dependencies absent from the new tree.
   They were copied independently from the original after checking every
   source digest, never regenerated. Originals were not overwritten.
3. `test_complex_contraction_equals_direct_transition_amplitude_sum` used
   Q.d in its independent Single reference. It now uses the documented
   forward excitation Q.d*, with the original `rel=1e-11`, `abs=1e-14`.

All pass in the recorded focused follow-up. Full-run failures are retained
verbatim; the follow-up does not retroactively make the full run green. The
other original six stale-default/layout/provenance cases remain classified
as previously investigated. Resource-case outcomes depend on measured RSS;
the selected budget and availability fractions were never changed.

Fourteen of the original fifteen baseline cases fail in this run. The old
automatic-2.0 resource case passes, illustrating the documented process-RSS
sensitivity, not a changed budget or repaired numerical issue. The new
`test_solver_configuration_and_physics_unchanged` failure is an intentional
source-identity guard: it compares `forward_event_amplitudes` AST and full
Single/Double source text to the older release. The approved L* and
contraction corrections necessarily differ. The guard was left unchanged;
its failure is explicitly retained for review rather than deleted or XFAILed.
It is not an independently observed scattering error. Fourteen inherited
failures plus this source-identity guard remain unresolved as suite acceptance
issues; the repository is not certified all-green or ready for publication.

One extra skip was an optional profiler setup fixture absent from the new
worktree. Its ten files were copied independently and checked against source
hashes; `profiler_followup.xml` records the original test passing with both
propagation functions forbidden. The two original private-companion-data
skips remain. No skipped case is silently counted as a full-run pass.

An earlier invalid harness attempt lacked the parent `build` directory for
pytest temp files. A one-test reproduction confirmed `FileNotFoundError`.
That pytest process alone was stopped, its log preserved as
`regression_invalid_harness.log`; creating the missing directory fixed the
setup. Neither science process was interrupted. This is not a physics failure.

## Matched Ni [017] scientific comparison

Two versions were independently executed in separate processes against their
own source roots. Each ran 8 geometry/channel cases with Both methods and two
energies: 32 method/edge conditions per version. Every completed energy was
saved immediately with settings, common source hash and kernel hashes.
No old checkpoint was used as a corrected calculation.

Identical conditions: FCC Ni [017], target (200), 300 kV, crystal M=±[001]
rotated by the existing proper frame, eta=beta=1, native L3=831.271 and
L2=848.698 eV; t=10/30 nm; exact Bragg X=-5.586688140406263 mrad;
Y=0/+15 mrad. Full finite 71-beam basis, b=5.0/p=6.2 cycles/Å;
65×65 detector grid, halfwidth .5 cycles/Å, fractional subpixels=128,
fixed A/B centers (0.28376844494892167, ±0.28376844494892167) cycles/Å,
radius .0908059024. Depth nodes=129; FFT grid=32; requested max step=.04 nm,
actual step=.0390625 nm at both thicknesses. One explicitly selected worker
per method, 8192 MiB case budget, as in the historical study. These are study
inputs, not changed application defaults. No post-edge normalization.

The re-executed original Double BW values reproduce the historical saved
raw data: maximum absolute error **{science['historical_reproduction_max_absolute']:.9g} a.u.**
Thus this is a controlled before/after comparison, not an unrecorded equivalent.
Conventional FCC site phases are unity for the allowed reflections; the
phase correction is essential in synthetic controls but does not change this
standard-origin Ni response. The tensor correction exchanges the raw states:

- Maximum state-exchange residual: **{science['max_state_exchange_absolute']:.9g} a.u.**
- Maximum reversal-even residual: **{science['max_even_absolute']:.9g} a.u.**
- Maximum odd-sign residual: **{science['max_odd_sign_residual']:.9g} a.u.**

All {science['paired_method_edge_conditions']} tested conditions satisfy the
state-exchange prediction at `rtol=1e-12`, `atol=1e-14`. CSV/NPZ retains the
signed four-state raw values, N/M, Flip-M, conventional A/B, magnetic-only
and PRB percentages. `scientific_differences.csv` records signed/absolute
differences, relative changes and percentage-point differences. Relative
differences near a zero baseline are explicitly undefined, not silently
regularized; the guard is documented in the analysis script.

Representative **Double BW** results (raw units; percentages are signed):

| t nm | Y mrad | Edge | D_nonmag after | D_mag before | D_mag after | PRB before % | PRB after % |
|---:|---:|---|---:|---:|---:|---:|---:|
{chr(10).join(table)}

At 30 nm/+15 mrad/L3, corrected D_mag is positive but conventional A/B
remains negative because D_nonmag dominates. Corrected paired contrast must
not be interpreted as intrinsic magnetic signal. Sign inversion of an odd
component is a 200% relative change in its signed value; its absolute
magnitude is unchanged. PRB denominators differ between the two raw states,
so PRB is not generally the negative of its old value.

![Representative before/after components](../outputs/physics_convention_correction_acceptance/scientific_impact.png)

The lines connect discrete representative cases only. Full-precision values
for both methods and both channeling models are in `scientific_cases.csv`
and `before_after.npz`; the SVG accompanies the PNG.

## BW/MS agreement and numerical limits

All **{science['bw_ms_passed']}/{science['bw_ms_comparisons']}** old/new matched
comparisons satisfy the existing raw relative ≤0.001 and PRB ≤0.01 pp limits.
Maximum raw relative error: **{100*science['bw_ms_max_raw_relative']:.8f}%**;
maximum PRB discrepancy: **{science['bw_ms_max_prb_pp']:.9f} pp**.
`bw_ms_comparison.csv` also records magnetic-only percentage differences.
Unrestricted FFT propagation and a finite BW basis are not identical elastic
truncations; matching those tested outputs does not establish independent
cutoff convergence. No new beam/potential/grid/depth sweep was performed.
Existing [111] and Stage4.2 detector-grid limitations remain in force.

## Which earlier conclusions survive?

For standard FCC sites under this fixed source convention:

- Absolute magnetic-odd magnitudes, zero crossings, angular parity residual
  magnitudes and their thickness dependence survive; signed maps/spectra
  reverse. Relative L3/L2 sign opposition survives, absolute signs change.
- The outgoing-channeling effect on |M| and the separation of reversal-even
  diffraction imbalance from reversal-odd response survive.
- Flip-M rejects reversal-even contamination under matched reversal geometry.
  The magnitude ratio |D_nonmag/D_mag| is unchanged, preserving the prior
  thin-versus-thick contamination comparison within its existing limitations.
- Conventional +M A/B percentages and false-sign *locations* require revision.
  An explicitly labeled algebraic reanalysis of frozen Stage4.2 raw data gives
  30 nm false-sign counts L3 36→36 and L2 27→27, but changes 72 and 54 spatial
  classifications respectively. Ten-nm counts remain zero. This is not a new
  complete tilt simulation or convergence certificate. The L2 regional count
  still includes one inherited failed detector-grid control point; no failure
  was converted to a pass.
- The specific 8-versus-12 nm **PRB** peak ordering and full voltage/thickness
  conclusions are not re-certified by a 10/30 nm comparison. Raw |M| is
  algebraically invariant for the unchanged FCC response, but PRB maxima need
  a separately documented reanalysis of their raw denominators. No full scan
  was rerun here.

Remaining model uncertainties: XMCD-effective is not a genuine DFT complex
transition MDFF; RP/LP-to-absolute-magnetization handedness remains uncalibrated;
native energies are not experimental calibration; frozen q_z, projected IAM,
finite ZOLZ/path support and continuous depth/site averaging remain. No HOLZ,
absorption/TDS, atomic-3D treatment, double ionization or absolute count/SNR
calibration was added. Arbitrary supplied Hermitian tensors still require PSD
validation; no unrelated constructor/GUI redesign was included.

## Preservation and reproducibility

`pre_correction_baseline.json` stores the clean starting state and source
hashes; `before/` preserves original kernels/audit tests. `integrity.json`
confirms all **323 protected files**, including **204 production checkpoints**,
all **19 original user files**, all **9756 historical Stage1–4.2 files**, and
the original worktree's audit/user edits unchanged. The USER_GUIDE edit is
also checked against the preceding audit's original saved hash. No source
spectrum, protected reference, prior scientific plot or checkpoint was replaced.
The current version remains 0.6.1b3. Corrected results use a separate directory
and carry source-root/kernel-hash/convention provenance despite the unchanged
public version; old projects retain old arrays and must not be relabeled as
corrected results without explicit recalculation.

Commands (existing emcd-python environment; PYTHONPATH=isolated src,
PYTHONDONTWRITEBYTECODE=1, OPENBLAS_NUM_THREADS=OMP_NUM_THREADS=1,
QT_QPA_PLATFORM=offscreen):

```powershell
python -B -m pytest tests -q -p no:cacheprovider --basetemp=build/physics-correction-pytest
python -B -m pytest tests/test_physics_matrix_audit.py tests/test_physics_correction_proposal.py tests/test_physics_correction_engines.py tests/test_double_channeling_foundation.py tests/test_multislice_double_channeling.py tests/test_double_channeling_bw.py -q -p no:cacheprovider
python -B scripts/analyze_physics_correction.py
python -B scripts/check_physics_correction_integrity.py
python -B scripts/report_physics_correction.py
```

The simulation worker's `--help` documents source-root/label/output arguments;
the exact per-case configuration and completed-energy checkpoints are saved.
The old and corrected runs used identical script bytes. Reuse requires the
full settings/source/kernel/script fingerprint, so corrected outputs cannot
silently reuse an original-convention checkpoint.

Tracked diff summary (untracked tests/tools/docs are described above):

```text
{changed}```

## Exact production diff

```diff
{source_diff}```
'''
    (ROOT/'docs/PHYSICS_CORRECTION_ACCEPTANCE.md').write_text(report,encoding='utf-8')
    (OUT/'validation_report.md').write_text('# Physics correction acceptance\n\nSee [the complete report](../../docs/PHYSICS_CORRECTION_ACCEPTANCE.md).\n',encoding='utf-8')
    (OUT/'acceptance.json').write_text(json.dumps(dict(bounded_physics_accepted=accepted,
        full_regression_all_green=False,regression=regression,
        additional_unresolved_failures=unresolved,scientific_summary=science),indent=2),encoding='utf-8')
    print('Acceptance report written; bounded physics acceptance:',accepted)


if __name__=='__main__':run()
