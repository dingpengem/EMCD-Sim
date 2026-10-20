# Windows BW cutoff crash: diagnosis and local fix

Date: 2026-10-20. Branch: `fix/bw-cutoff-gui-crash`, based on fetched main
`f947889252adc15da0413f7a97d03fb178bc8fa5`. No physical model, precision,
release version or production checkpoint changes.

## Finding

The installed Windows NumPy OpenBLAS runtime can terminate the process when
multiple BW detector workers concurrently solve outgoing Bloch eigenproblems.
This is a native access violation, not an ordinary Python exception to catch.
The disposable source reproduction exits **3221225477 (`0xc0000005`)** with
faulthandler reporting `numpy/linalg/_linalg.py` during the outgoing solve loop:
`channeling.contract` → `double_channeling_response` → `BlochStates.solve` →
`np.linalg.eigh`. Incoming diagonalization/fields completed before the failure;
the final Cartesian tensor-contraction stage was not reached. A deterministic
failing detector index is not established: this is concurrency/timing sensitive.
Adding entry/return tracing made one otherwise unsafe run pass.

Windows Application event 1000 independently records the same access violation
for the existing development EXE, including a fault in
`libscipy_openblas64_-63c857e738469261263c764a36be9436.dll`; other recorded faults
are in `ntdll.dll`. The source and packaged NumPy DLLs have identical SHA256
`63c857e738469261263c764a36be9436ebdeaa272e340a828f42047a97131080`.
The source reproduction uses NumPy 2.4.6, the same DLL and 12 native BLAS threads.
Thus the issue is not confined to packaging or a missing packaged dependency.
This identifies an unsafe concurrent native-runtime path on this host; it is
not a claim that every OpenBLAS version/platform has the defect, or proof that
generic CPU oversubscription alone causes it. Four Python workers sharing a
12-thread native runtime does not establish 48 simultaneously active threads.

The runtime log was inspected. Its older October 18 resource-exhaustion messages
belong to earlier builds and are not evidence that this October 20 failure is
out of memory. Before this fix, Run logging omitted most numerical inputs and
the last calculation stage; the patch records both for future diagnosis.

## Recovered settings and controlled scope

The recent checksummed user project was recovered from
`C:/data/EMCD_sim_data/Ni017_20261020_041237Z`. It records **MS Double**, Manual,
300 kV, 8 nm, Ni [017], target (200), absolute tilt
`(-7.11672544, 0)` mrad, potential cutoff 2.0 cycles/Å, B=0, 97×97 angular grid,
64 depth nodes, 64 aperture subpixels, halfwidth 1 cycle/Å, 2048 MiB budget,
FFT 32, slice step 0.5 nm, full spectral coverage and angular maps enabled.
The crystal magnetization is [001], eta=beta=1, correction disabled, source
SHA256 `4fd517af3e54db94588a76b7a6ed9c2f9a1b745cd8fe52b9fca0f87fc4938db3`,
native selected energies 831.271/848.698 eV. Detector centers are
`(0.28376844494892167, ±0.28376844494892167)` cycles/Å, radius 0.0908059024.

This is the most recent recoverable configuration, not proof of every input of
the lost BW Run. Both Single and Double were therefore tested. Probes explicitly
changed propagation to BW, cutoff to 2.5/3.0, and coverage to the two native edge
samples; detector-only probes explicitly disabled maps. The separate full-field
test retained the complete 97×97 map grid. No full-energy sweep was run. All
other settings, source data, detector weights and normalization were retained.
The saved absolute tilt was not silently realigned for 300 kV.

## Native threading isolation

Eight outgoing detector directions at L3 were evaluated in disposable Python
subprocesses with `-X faulthandler`, retaining the saved geometry/depth settings.
Environment thread limits were set before NumPy import only in controlled
reference subprocesses; the application does not set those limits.

| Basis cutoff (cycles/Å) | Beams | BW workers | BLAS threads | Result |
| --- | ---: | ---: | ---: | --- |
| 2.5 | 21 | 1 | 1 | Passed |
| 2.5 | 21 | 4 | 1 | Passed |
| 2.5 | 21 | 4 | 12, default | Passed |
| 3.0 | 27 | 1 | 1 | Passed |
| 3.0 | 27 | 4 | 1 | Passed |
| 3.0 | 27 | 4 | 12, default | Native access violation |
| 3.0 | 27 | 1 | 12, default | Passed |

All successful controlled response comparisons were **bitwise identical** for
the complete complex 8×3×3 Cartesian response and both contracted reversal
intensities. Exceptions/Qt worker error handling cannot recover the unsafe
process termination; the fix prevents that native concurrency pattern.

## Basis and memory audit

Incoming and outgoing Hamiltonians are respectively 21×21 or 27×27 complex128;
the outgoing solve uses reduced post-loss energy. The numerical-depth route
retains 64×N complex fields, an N×N×3 Cartesian kernel and a 3×3 response per
query direction. A 64×27 field is 27,648 bytes, and a 27×27 Hamiltonian 11,664
bytes. The 97×97 response itself would be 1,354,896 bytes before mirror reuse.
Single uses its existing bounded pixel chunks.

The analytic mode-pair depth route has N⁴ phase/integral temporaries, estimated
at `80*N**4` bytes per worker. The tested full [017] route uses numerical depth
integration, which does not allocate this mode-pair matrix; the admission code
nevertheless retains that conservative bound. Existing admission already
multiplies per-worker working storage by BW worker count, accounts for retained
results, concurrent reservations, current RSS, 25% allocation margin and a
128 MiB reserve. No estimator or threshold was relaxed.

| Cutoff | Workers | Dense bound per worker (MiB) | Estimated working (MiB) | Estimated process peak (MiB) |
| --- | ---: | ---: | ---: | ---: |
| 2.5 | 4, original | 14.838 | 118.021 | 350.727 |
| 3.0 | 4, original | 40.546 | 226.555 | 486.394 |
| 2.5 | 1, fixed | 14.838 | 44.205 | 258.456 |
| 3.0 | 1, fixed | 40.546 | 75.228 | 297.235 |

The table uses the same representative 75.2 MiB RSS snapshot and 16,400 MiB
available RAM for comparison, not measured peak RSS. The crashing subprocess
reported 75.23 MiB RSS and 16,498 MiB available before outgoing work. Successful
GUI runs ended around 175–179 MiB RSS, including plotting. These before/after
snapshots are not a peak-memory trace. The evidence does not support memory
exhaustion as this failure's cause; increasing the memory budget is not the fix.

## Minimal fix

Windows GUI BW Double now uses **one detector executor worker**. A process-local
lock also prevents independent BW detector executors from overlapping on
Windows; a waiting request checks cancellation every 50 ms and always releases
its own acquired lock on error/cancellation. No process-wide BLAS thread count
is changed. The tested default remains 12. MS retains four detector workers and
bypasses this guard; other platforms retain their existing BW worker policy.

`EMCDWorker` additionally logs the complete settings/configuration snapshot and
each stage before emitting its existing queued progress signal. No exception
handler is presented as a remedy for native faults. MDFF, Hamiltonians,
propagation, reversal signs, quadrature, precision and scientific parameters
remain unchanged. Memory admission automatically uses the actual new worker
count. Windows BW throughput can decrease relative to four workers with a known
safe single-threaded BLAS runtime; safety is preferred until a separately
validated runtime permits restoring concurrent outgoing solves.

## Validation

- Focused physics/GUI batch: **105 passed**, 0 failed/skipped, 87.18 s. It covers
  scheduler equivalence, BW/MS, cancellation, memory, Automatic/Manual and saved
  settings. Final guard/UI/log tests: **6 passed**, 20.59 s, including two added
  checks for responsive rejection without a worker and input/stage logging.
- Actual source `MainWindow`/Run/QThread path: Single and Double at both cutoffs,
  original default native threading, selected L3/L2 detector support, all passed.
  Each case preserved all **16 spectral arrays bitwise**, maximum absolute
  difference **0**, relative to the original adapter with one BLAS thread.
- Actual source GUI Double at 3.0 with full 97×97 L3/L2 maps passed, with **1,301
  timer heartbeats** during the automated run. All **38 saved spectral/map
  arrays** are bitwise identical to the original four-worker adapter under safe
  one-thread BLAS. Raw A/B states, odd/even differences and all asymmetries
  derived from those identical arrays are preserved.
- Guard tests verify Windows BW serialization, unchanged MS/non-Windows policy,
  cancellation while waiting, lock ownership/release, graceful resource rejection
  with unchanged inputs, and a responsive GUI event loop. Existing focused
  tests retain actual worker cancellation and saved-project compatibility.
- All **204 production checkpoints** and both existing Windows ZIP SHA256s
  remain unchanged. No broad regression suite or production scan was run.

Evidence is retained separately under `outputs/bw_cutoff_crash/`: Windows events,
native probe logs/return codes, GUI reports/screenshots, compact NPZ/CSV
comparisons, memory audit, and JUnit XML. The evidence directory is not committed.

The reusable selected-edge harness is
[diagnose_bw_cutoff_crash.py](../scripts/diagnose_bw_cutoff_crash.py). For example:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
python -X faulthandler scripts/diagnose_bw_cutoff_crash.py --project C:/data/EMCD_sim_data/Ni017_20261020_041237Z --output outputs/bw_cutoff_crash/new_gui_check --cutoff 3.0 --channel double --maps --gui
```

Use a new output directory. `--baseline` loads the original adapter for safe
same-solver comparisons and requires `OPENBLAS_NUM_THREADS=1` before startup.
For interactive source use `python -X faulthandler -m emcd_sim.gui`. The automated
harness exercises that same MainWindow/Run/worker implementation.

## Remaining scope

The fix is locally validated source code. **Existing EXEs have not been rebuilt
and still contain the old implementation.** Source and packaged failure evidence
identify the same native library path, so a packaging-only diagnostic rebuild
was unnecessary. Run the fixed source for this workaround; a future EXE needs
an explicitly built candidate containing this commit and its own acceptance.
No claim is made of a newly tested packaged fix, a vendor-level OpenBLAS repair,
or stability for arbitrary untested bases, full spectra or direct low-level
parallel API callers outside the GUI adapter. Normal resource admission still
rejects oversized configurations. This task does not add new convergence claims.
