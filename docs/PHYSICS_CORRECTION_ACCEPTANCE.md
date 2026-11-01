# Coordinated physics correction acceptance

Source base: `a77f7455f5fe57dad6bae5d948477b2390433bb0`; isolated detached
worktree: `C:/Users/peng863/EMCD-Sim/build/physics-correction-validation`.
All changes are **uncommitted**. The original worktree and user edits are
preserved. This implements the user's explicitly approved coordinated patch.

**Disposition: PASS for the bounded physics correction; repository-wide regression is NOT all-green.**
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
| `focused.xml` | 54 | 0 | 0 | 0 |
| `engine_controls.xml` | 2 | 0 | 0 | 0 |
| `followup.xml` | 5 | 0 | 0 | 0 |
| `profiler_followup.xml` | 1 | 0 | 0 | 0 |

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

Full run: **576 passed, 18 failed,
0 errors, 3 skipped**
(597 collected). See `regression.log/.xml` and
`regression_triage.json`. The original audit baseline was 558 passed,
15 failed, 2 skipped, before the added physics tests. The baseline
classification of all 15 unrelated failures is preserved in
`PHYSICS_REGRESSION_FAILURE_REVIEW.md`, not hidden by a new XFAIL or budget.

| Failed full-run test | Classification |
|---|---|
| `tests.test_double_channeling_full_benchmark::test_equivalent_sites_preserve_general_complex_average` | Resolved by focused follow-up; see explanation below |
| `tests.test_double_channeling_full_outputs::test_orientation_source_reproduction_and_preservation` | Pre-existing provenance mismatch (not physics) |
| `tests.test_full_thickness_series::test_reused_files_unchanged_and_comparison_gate_not_relaxed` | Resolved by focused follow-up; see explanation below |
| `tests.test_multislice_slice_step_range::test_manual_gui_preserves_requested_maximum[automatic-5.0]` | Test isolation / process-memory environment (not physics) |
| `tests.test_multislice_slice_step_range::test_manual_gui_preserves_requested_maximum[automatic-10.0]` | Test isolation / process-memory environment (not physics) |
| `tests.test_multislice_slice_step_range::test_manual_gui_preserves_requested_maximum[manual-0.04]` | Test isolation / process-memory environment (not physics) |
| `tests.test_multislice_slice_step_range::test_manual_gui_preserves_requested_maximum[manual-0.5]` | Test isolation / process-memory environment (not physics) |
| `tests.test_multislice_slice_step_range::test_manual_gui_preserves_requested_maximum[manual-1.0]` | Test isolation / process-memory environment (not physics) |
| `tests.test_multislice_slice_step_range::test_manual_gui_preserves_requested_maximum[manual-2.0]` | Test isolation / process-memory environment (not physics) |
| `tests.test_multislice_slice_step_range::test_manual_gui_preserves_requested_maximum[manual-5.0]` | Test isolation / process-memory environment (not physics) |
| `tests.test_multislice_slice_step_range::test_manual_gui_preserves_requested_maximum[manual-10.0]` | Test isolation / process-memory environment (not physics) |
| `tests.test_single_channeling_tensor::test_complex_contraction_equals_direct_transition_amplitude_sum` | Resolved by focused follow-up; see explanation below |
| `tests.test_solver_settings_ui::test_released_configuration_exactly_preserved[0]` | Stale pre-existing expectation after approved UI/default change (not physics) |
| `tests.test_solver_settings_ui::test_released_configuration_exactly_preserved[1]` | Stale pre-existing expectation after approved UI/default change (not physics) |
| `tests.test_solver_settings_ui::test_solver_visibility_and_classification[0]` | Stale pre-existing layout expectation after approved UI change (not physics) |
| `tests.test_solver_settings_ui::test_solver_visibility_and_classification[1]` | Stale pre-existing layout expectation after approved UI change (not physics) |
| `tests.test_solver_settings_ui::test_solver_visibility_and_classification[2]` | Stale pre-existing layout expectation after approved UI change (not physics) |
| `tests.test_solver_settings_ui::test_solver_configuration_and_physics_unchanged` | Intentional source-identity guard failure after approved kernel correction; test retained unchanged |

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
raw data: maximum absolute error **5.55111512e-17 a.u.**
Thus this is a controlled before/after comparison, not an unrecorded equivalent.
Conventional FCC site phases are unity for the allowed reflections; the
phase correction is essential in synthetic controls but does not change this
standard-origin Ni response. The tensor correction exchanges the raw states:

- Maximum state-exchange residual: **2.77555756e-17 a.u.**
- Maximum reversal-even residual: **2.77555756e-17 a.u.**
- Maximum odd-sign residual: **4.16333634e-17 a.u.**

All 32 tested conditions satisfy the
state-exchange prediction at `rtol=1e-12`, `atol=1e-14`. CSV/NPZ retains the
signed four-state raw values, N/M, Flip-M, conventional A/B, magnetic-only
and PRB percentages. `scientific_differences.csv` records signed/absolute
differences, relative changes and percentage-point differences. Relative
differences near a zero baseline are explicitly undefined, not silently
regularized; the guard is documented in the analysis script.

Representative **Double BW** results (raw units; percentages are signed):

| t nm | Y mrad | Edge | D_nonmag after | D_mag before | D_mag after | PRB before % | PRB after % |
|---:|---:|---|---:|---:|---:|---:|---:|
| 10.0 | 0.0 | L3 | +1.3877788e-17 | -0.011537768 | +0.011537768 | -14.017545 | +14.202079 |
| 10.0 | 0.0 | L2 | -3.469447e-18 | +0.012536523 | -0.012536523 | +23.098238 | -22.604152 |
| 10.0 | 15.0 | L3 | +0.0013143975 | -0.011251896 | +0.011251896 | -12.254678 | +15.639068 |
| 10.0 | 15.0 | L2 | +0.00087737253 | +0.012225729 | -0.012225729 | +24.379718 | -20.794934 |
| 30.0 | 0.0 | L3 | +0 | -0.0066732093 | +0.0066732093 | -2.591050 | +2.597339 |
| 30.0 | 0.0 | L2 | +4.1633363e-17 | +0.0072494023 | -0.0072494023 | +4.208439 | -4.191611 |
| 30.0 | 15.0 | L3 | -0.011075553 | -0.0041027467 | +0.0041027467 | -6.259951 | -2.937059 |
| 30.0 | 15.0 | L2 | -0.0074441163 | +0.0044618593 | -0.0044618593 | -1.884610 | -7.271259 |

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

All **32/32** old/new matched
comparisons satisfy the existing raw relative ≤0.001 and PRB ≤0.01 pp limits.
Maximum raw relative error: **0.01749585%**;
maximum PRB discrepancy: **0.005387449 pp**.
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
 src/emcd_sim/double_channeling.py              | 13 +++++++------
 src/emcd_sim/multislice_double_channeling.py   |  7 ++++---
 src/emcd_sim/single_channeling_tensor.py       |  3 ++-
 tests/test_double_channeling_foundation.py     | 10 +++++-----
 tests/test_double_channeling_full_benchmark.py |  3 ++-
 tests/test_multislice_double_channeling.py     |  6 +++---
 tests/test_single_channeling_tensor.py         |  2 +-
 7 files changed, 24 insertions(+), 20 deletions(-)
```

## Exact production diff

```diff
diff --git a/src/emcd_sim/double_channeling.py b/src/emcd_sim/double_channeling.py
index f7380d1..8829fdb 100644
--- a/src/emcd_sim/double_channeling.py
+++ b/src/emcd_sim/double_channeling.py
@@ -77,8 +77,8 @@ def dipole_kernel(q_cycles):
 
 
 def contract_cartesian(vectors, tensor):
-    """v T v*, matching existing d=<core|r|final>, T=d d* convention."""
-    return np.einsum('...a,ab,...b->...', vectors, tensor, vectors.conj()).real
+    """v T^T v*, for forward excitation with d=<core|r|final>."""
+    return np.einsum('...a,ba,...b->...', vectors, tensor, vectors.conj()).real
 
 
 def depth_response(incoming, outgoing, kernel, thickness_nm, *, method='analytic', depth_steps=257, cancelled=None):
@@ -152,7 +152,8 @@ def equivalent_site_phases(incoming_hkl,outgoing_hkl,positions):
     This removes repeated evaluations for equivalent FCC sites without dropping
     independent events or changing their incoherent per-atom normalization.
     """
-    delta=np.asarray(outgoing_hkl)[None,:,:]-np.asarray(incoming_hkl)[:,None,:]
+    # exp(-i Q.R), dropping only the common detector/longitudinal phase.
+    delta=np.asarray(incoming_hkl)[:,None,:]-np.asarray(outgoing_hkl)[None,:,:]
     cycles=np.remainder(np.einsum('ghc,sc->sgh',delta,np.asarray(positions)),1.)
     if not len(cycles):raise ValueError('At least one core site required')
     unique,counts=np.unique(cycles,axis=0,return_counts=True)
@@ -222,7 +223,7 @@ def intensities_from_response(response, tensor):
         raise ValueError('Finite Hermitian dipole tensor required')
     if np.linalg.eigvalsh(t).min() < -1e-12*max(np.linalg.norm(t), 1e-30):
         raise ValueError('Dipole tensor must be positive semidefinite')
-    return np.einsum('...ab,ab->...', response, t).real
+    return np.einsum('...ab,ba->...', response, t).real
 
 
 
@@ -264,8 +265,8 @@ def _run_tensor_double_channeling(model, tensor, *, thickness_nm=30., grid_size=
             spectra[k][ie]=(total[masks[k]].sum() if integration_mode=='binary'
                             else (total*weights[k]).sum())*(q[1]-q[0])**2
         if ie==selected:
-            even=np.einsum('pab,ab->p',response,t.real).real.reshape(qx.shape)
-            odd=np.einsum('pab,ab->p',response,1j*t.imag).real.reshape(qx.shape)
+            even=np.einsum('pab,ba->p',response,t.real).real.reshape(qx.shape)
+            odd=np.einsum('pab,ba->p',response,1j*t.imag).real.reshape(qx.shape)
     return SimulationResult(tensor.energy_ev,qx,qy,even,odd,spectra,masks,None,
         thickness_nm,0.,model.chiral_groups,weights,integration_mode,aperture_subpixels)
 
diff --git a/src/emcd_sim/multislice_double_channeling.py b/src/emcd_sim/multislice_double_channeling.py
index 03f24d5..3182fc7 100644
--- a/src/emcd_sim/multislice_double_channeling.py
+++ b/src/emcd_sim/multislice_double_channeling.py
@@ -128,7 +128,8 @@ def forward_event_amplitudes(incoming,kernel,tensor,outgoing_plan,slices,outgoin
     kernel[g,h,a] includes Coulomb factor and a single site's phase. Return
     complex exit amplitudes per independent target mode (never summed coherently).
     """
-    modes=transition_modes(tensor)
+    # T=L L^dagger is unchanged; excitation amplitudes use L*.
+    modes=transition_modes(tensor).conj()
     scattered=np.einsum('g,gha,af->fh',incoming,kernel,modes,optimize=True)
     full=np.zeros((3,outgoing_plan.size),complex)
     full[:,outgoing_indices]=scattered
@@ -387,7 +388,7 @@ def run_tensor_multislice_double_channeling(model,tensor,*,thickness_nm=30.,grid
                 spectra[k][i]=(total[masks[k]].sum() if integration_mode=='binary' else
                     (total*weights[k]).sum())*(q[1]-q[0])**2
             if i==selected:
-                even=np.einsum('pab,ab->p',response,t.real).real.reshape(qx.shape)
-                odd=np.einsum('pab,ab->p',response,1j*t.imag).real.reshape(qx.shape)
+                even=np.einsum('pab,ba->p',response,t.real).real.reshape(qx.shape)
+                odd=np.einsum('pab,ba->p',response,1j*t.imag).real.reshape(qx.shape)
         return SimulationResult(tensor.energy_ev,qx,qy,even,odd,spectra,masks,None,thickness_nm,
             0.,model.chiral_groups,weights,integration_mode,aperture_subpixels)
diff --git a/src/emcd_sim/single_channeling_tensor.py b/src/emcd_sim/single_channeling_tensor.py
index 1a2794c..12bf7c2 100644
--- a/src/emcd_sim/single_channeling_tensor.py
+++ b/src/emcd_sim/single_channeling_tensor.py
@@ -54,7 +54,8 @@ def _tensor_angular_maps(model: EMCDSimulation, tensor_matrix: np.ndarray,
     weighted_coherence = coherence * site_phase
 
     def project(part: np.ndarray) -> np.ndarray:
-        mdff = np.einsum("...ia,ab,...jb->...ij", angular_q, part, angular_q, optimize=True)
+        # Forward excitation uses d*=<f|r|i>, hence S(Q_j,Q_i).
+        mdff = np.einsum("...ia,ba,...jb->...ij", angular_q, part, angular_q, optimize=True)
         return np.real(np.einsum("ij,...ij->...", weighted_coherence,
                                   mdff / denominator, optimize=True))
 
```
