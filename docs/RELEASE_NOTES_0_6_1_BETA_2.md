# EMCD-Sim v0.6.1-beta.2

This Windows research prerelease adds the validated BW worker-safety fix and the
recent GUI/performance improvements to the unchanged v0.6.1-beta.1 baseline.
The previous release, tag, ZIP and 204 production checkpoints are preserved.

- Independent Automatic/Manual numerical settings and parallel-worker controls.
- Actual BLAS backend/thread introspection, estimated process-memory preview,
  and pre-Run unsafe/unsupported worker and resource rejection.
- Conservative Windows BW Double execution: one detector worker by default.
  Multiple workers require a verified single-thread native runtime; no runtime
  BLAS thread settings are mutated. This is not a universal crash guarantee.
- New-project defaults: 300 kV, beam cutoff 3.0 cycles/Å, potential cutoff
  2.0 cycles/Å, 97×97 angular grid, 2048 MiB. Saved settings are preserved.
  These are starting values, not universally converged numerical parameters.
- Reversible diffraction full-basis view, exact detector-support sampling away
  from selected angular-map energies, and private MS Double buffer reuse.
- Retained full-field L3/L2 maps, raw and relative EMCD analysis, BW/MS Single
  and Double Channeling, projects and CSV/NPZ/PNG/SVG exports.

The incoming/outgoing propagation, MDFF, potentials, physical beam selection,
precision and normalization are unchanged by the worker-safety fix. The completed
200 kV Ni thickness study remains historical validation of its matched profile;
it does not certify the new convenience defaults or untested thicknesses.

## Installation

Download `EMCD-Sim-0.6.1-beta.2-Windows.zip` and `SHA256SUMS.txt` from the
[release](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.6.1-beta.2).
Verify the ZIP checksum, Extract All, then open `EMCD-Sim/EMCD-Sim.exe` with
the complete `_internal` directory alongside it. Python/Conda is bundled.
The package is unsigned; independent clean-machine acceptance is not claimed.
Inspect Help → About / build for package version `0.6.1b2` and source provenance.

## Validation and limits

The implementation passed 142 focused tests and bounded real source/frozen
calculations, including the saved Ni [017] 300 kV/8 nm case, a fresh 30 nm default
project, and explicit four-worker/native-one execution. Compared spectra and
selected L3/L2 fields were bitwise unchanged. The matching four-worker/native-12
request is blocked before worker launch. See the
[worker-safety report](BW_PARALLEL_WORKER_SAFETY.md) for exact diagnostic evidence.
The prior diagnostic EXE was not relabeled as Beta 2. The version-matched package
was built from clean commit `81a74f51d2de8d66a086e9ba361f91fe96a61b06`, with
application version `0.6.1b2` and the Beta 2 build label. Only version metadata
differs in its runtime Python sources from the validated worker-safety diagnostic.
Subsequent release-documentation and test-fixture corrections do not change the
packaged implementation; the release tag includes those corrections.

ZIP SHA256:

```text
04511b73d52fc1a843323e9b859dcbdc081dbc6a0abf3bff67ae320bce4b48d9
```

All 609 packaged files match the build manifest; ZIP CRC verification passed.
The three actual Beta 2 BW Double selected-edge runs passed: saved 300 kV/8 nm
case with one detector worker/native 12 (PID 8124), fresh 300 kV/30 nm defaults
with one/native 12 (PID 8112), and saved case with four/native one (PID 21692).
Each matched all 16 source spectral arrays bitwise. Unsafe requests were rejected
before worker launch; native thread counts, numerical inputs, save/reopen and
exports were preserved. Event-loop heartbeats were 24, 39 and 29 respectively.
Automated calculation runs used Qt offscreen; a separate native Windows Qt
startup verified normal rendering without an EMCD calculation. This remains
same-host testing, not clean-machine acceptance or a whole-parameter-space test.

28 release-focused version/worker checks passed. Inspection of pre-release CI
found six legacy tests depending on superseded 200 kV/cutoff defaults. Their
fixtures now explicitly select the historical reference, use the current voltage
for coordinate conversion, actually change voltage, or check input preservation.
All 19 focused tests covering those corrections passed; numerical tolerances
were not relaxed. No further runtime change or rebuild was required.

**CI limitation:** the earlier `4192caf` cross-platform workflow was not green.
Besides those fixture failures, Linux reported a C-extension `bool_dealloc`
fault during interpreter finalization. That shutdown fault has not been isolated
or certified fixed. It was not observed in the bounded Windows package tests.
The release does not claim a new full cross-platform regression pass; the
historical 426-test result belongs to the previous acceptance milestone.

Remaining scientific limitations include an XMCD-effective rather than complete
DFT-derived MDFF, projected IAM elastic potential, finite reciprocal support,
energy-calibration conventions and profile-specific sampling convergence.
Double channeling includes outgoing propagation within the implemented
approximations; it is not a complete many-body treatment. Corrected contrast is
not intrinsically magnetic; arbitrary-unit intensity is not calibrated electron
counts or experimental SNR. Other runtimes, worker counts and parameter sets
remain unverified. See the existing manual and scientific-analysis reports.
