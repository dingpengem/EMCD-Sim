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
Version-matched Beta 2 build identity and frozen acceptance are recorded below
after completion; the prior diagnostic EXE is not relabeled as Beta 2.

Remaining scientific limitations include an XMCD-effective rather than complete
DFT-derived MDFF, projected IAM elastic potential, finite reciprocal support,
energy-calibration conventions and profile-specific sampling convergence.
Double channeling includes outgoing propagation within the implemented
approximations; it is not a complete many-body treatment. Corrected contrast is
not intrinsically magnetic; arbitrary-unit intensity is not calibrated electron
counts or experimental SNR. Other runtimes, worker counts and parameter sets
remain unverified. See the existing manual and scientific-analysis reports.
