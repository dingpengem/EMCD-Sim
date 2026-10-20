# BW parallel-worker safety: local diagnostic validation

This development change is local and unreleased. It does not change solver physics,
precision, the published Beta, or the 204 production checkpoints.

## Crash identity and evidence

The repeated Windows crashes used `build/windows-main-dev/dist/EMCD-Sim/EMCD-Sim.exe`,
whose embedded source commit is `7878c7e6ce1a823c53b564de72818951278f817e`.
It predates the source-only fix `f8a2b5e4e285ce011b9d7264f573b502c3c2499b`.
Recent Windows events record native access violations (0xc0000005) in ntdll.
Those events alone do not identify the faulting numerical operation.

The earlier controlled source reproduction isolated outgoing BW eigensolves:
Ni [017], 300 kV, 8 nm, potential cutoff 2.0, beam cutoff 3.0 (27 beams),
four detector workers and 12 native OpenBLAS threads failed in NumPy linear algebra.
One worker with 12 native threads and four workers with one native thread passed.
The corresponding 2.5 cutoff retains 21 beams. This is a bounded reproduction,
not evidence that every larger basis fails or every smaller basis is safe.
The old executable and source environment contain the same OpenBLAS DLL,
SHA256 `63c857e738469261263c764a36be9436ebdeaa272e340a828f42047a97131080`.
It reports OpenBLAS 0.3.31.188.0; its actual count is queried through its public
getter. `MAX_THREADS=24` is a build limit, not the observed count of 12.

## Controls and resource policy

Computational Resources offers independent Automatic/Manual worker controls
(1–4 requested workers), separate from Automatic/Manual numerical settings.
Windows BW Double defaults to one detector worker, retaining the cancellable
guard between concurrent BW executor calls. Single channeling uses one worker.
Manual unsupported requests are rejected, not silently clamped.
Windows BW Double requests above one require a verified native thread count of
one; the reproduced four-worker/12-thread case is specifically marked unsafe.
Other untested combinations remain unverified. No native thread setter is called.
Startup environment settings can establish a one-thread native runtime for an
explicit parallel diagnostic; the GUI does not change global BLAS state.

The preview reports solver/channeling, voltage, cutoffs, actual beam count, FFT
support, requested/effective workers, observed native backend/thread count, CPU
count, dense-kernel bound, estimated process peak, budget, available RAM and
active reservations. The Qt calculation thread is distinct from detector workers
and native BLAS threads. Peak estimates include important additional allocations
and worker multiplicity; they are estimates, not an operating-system guarantee.
Automatic MS may lower worker count to fit resources; manual requests are exact.
Admission checks repeat before calculation and reject changed pinned execution
plans. Concurrent RAM queries are serialized to avoid ctypes signature races.
Logs include build/configuration/resource decisions, without dumping source files.
A per-process faulthandler log supports future native-crash diagnosis.

New-project starting defaults are **300 kV, beam cutoff 3.0 cycles/Å, potential
cutoff 2.0 cycles/Å, 97×97 angular grid and 2048 MiB**. The starting Bragg tilt
uses the existing relativistic wavelength. Saved projects retain their own
geometry and numerical settings. These defaults are convenient starting values,
not universally converged settings. Existing scientific limitations remain.

## Focused source validation (2026-10-20)

142 focused tests passed in 464.84 s, with one Matplotlib layout warning.
Tests cover controls, legacy restoration, blocked execution before worker launch,
resource estimates, concurrent RAM queries, pinned plans, cancellation, persistence
and unchanged physics interfaces. No broad regression suite was run.

Bounded real Qt/native runs used the recovered saved Ni [017] 300 kV/8 nm case,
plus a fresh 300 kV/30 nm default project. The saved case retains its original
incident tilt (-7.11672544, 0) mrad rather than substituting the new Bragg tilt.
Selected native source energies are L3 831.271 and L2 848.698 eV, without shifting.
Automatic one-worker/native-12 and explicit four-worker/native-one runs completed;
unsafe requests were blocked before launching calculation. Save/reopen, exports,
GUI heartbeats and unchanged native-thread counts were checked.

| Comparison | Arrays | Maximum absolute difference |
| --- | ---: | ---: |
| Automatic 1/native 12 vs manual 4/native 1 spectra | 16 | 0 (bitwise) |
| Current vs previous corrected source spectra | 16 | 0 (bitwise) |
| Full 97×97 L3/L2 fields, 4/native 1 vs corrected reference | 38 | 0 (bitwise) |
| Single 2.5, Single 3.0, Double 2.5 vs corrected references | 16 each | 0 (bitwise) |

The core double-channeling, multislice, elastic-potential, MDFF and shared tensor
implementations are unchanged. All 204 checkpoint hashes and both prior ZIP
hashes match their recorded values. Local evidence is under
`outputs/bw_parallel_worker_safety/` (tests, comparison CSV/JSON, numerical NPZ,
acceptance reports and screenshots). Existing compatible complex-response
comparisons are reused; they were not recomputed unnecessarily.

## Diagnostic executable acceptance

The new diagnostic executable was built from clean source commit
`2810e8d9aff4ad4e3e903cdad56de15905d1c082` (embedded `dirty=false`).
Application version remains 0.6.1b1. Exact executable:

```text
C:\Users\peng863\EMCD-Sim\build\windows-bw-worker-diagnostic\dist\EMCD-Sim\EMCD-Sim.exe
```

The sibling archive is `EMCD-Sim-bw-worker-diagnostic-2810e8d-Windows.zip`.
Its SHA256 is
`7e7f054ea28475187d58f9c76ad32feab33a227f11355a4b972b9597818e01ae`.
All 609 distribution files match the manifest and the ZIP CRC check passes.
Acceptance initially overlapped ZIP compression and locked python311.dll;
compression was completed after test processes closed, without rebuilding or
changing the executable. Existing ZIPs were never replaced.

| Actual frozen BW Double run | PID | Detector / native threads | Exit | Heartbeats | Spectral agreement |
| --- | ---: | --- | ---: | ---: | --- |
| Saved 300 kV, 8 nm case, Automatic | 7276 | 1 / 12 | 0 | 30 | All 16 arrays bitwise equal to source |
| Fresh 300 kV, 30 nm defaults, Automatic | 3476 | 1 / 12 | 0 | 36 | All 16 arrays bitwise equal to source |
| Saved case, Manual four, startup BLAS one | 21736 | 4 / 1 | 0 | 26 | All 16 arrays bitwise equal to source |

Each real selected-edge calculation used beam cutoff 3.0, potential cutoff 2.0,
97-grid detector support, and unchanged numerical settings. These bounded frozen
runs intentionally disabled full-field maps; full-field equivalence was tested
separately in source. Save/reopen, exports, array preservation, unchanged actual
native thread counts, effective-worker metadata, responsive timer events and
return to enabled inputs all passed. The matching four-worker/native-12 request
was blocked before creating a calculation thread. Changing 2.5/3.0 updated the
preview from 21 to 27 beams. The controls are exercised through actual Qt widgets.
These automated calculation runs used Qt's offscreen platform; its widget text
screenshots have missing system-font glyphs and are not visual typography evidence.
A separate normal Windows Qt startup (PID 11404, exit 0) verified readable native
rendering and the default 27-beam diffraction preview, without running EMCD.

Local evidence includes `frozen_verification.json`, each `frozen_*/acceptance.json`,
process exit records, screenshots, exported results and the build manifest.
Native-fault tracing was enabled; no fatal native exception occurred in these runs.
The final integrity recheck again confirmed all 204 production checkpoints,
both old ZIPs, and unchanged numerical core implementations.

The new executable resolves the reproduced execution-policy failure under the
tested conditions. It does not certify arbitrary material, thickness, beam basis,
runtime backend, worker count or full-spectrum memory load. Manual two/three
workers, other native backends and wider parameter combinations remain unverified.
Memory admission and bounded native stability are distinct from physical numerical
convergence. No runtime BLAS mutations or universal cutoff safety rule are used.
The automatic one-worker strategy is the recommended Windows BW Double starting
policy; four workers require a verified one-thread native runtime and are not
claimed faster from these GUI/export timings.

The host is Windows 11 Enterprise 10.0.26200, Intel i7-1365U, 12 logical CPUs,
31.58 GiB RAM, with Python/Conda installed. Local acceptance is not a clean-machine
installation test. No full-spectrum, thickness or voltage scan is part of this fix.
