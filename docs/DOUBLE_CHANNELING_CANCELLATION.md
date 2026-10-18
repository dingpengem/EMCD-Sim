# Double-channeling cancellation

## Root cause (inspection before changes)

At baseline `7bebdce4303bc7d517e826c9e0c91e8418f3f55b`, Cancel is
enabled during computation and calls QThread.requestInterruption directly.
It does not depend on a queued slot in the busy worker's event loop. Physics
already runs off the GUI thread. The missing checkpoints are inside numerical
work: BW detector batches enter pixel/eigensystem/depth contractions without
polling, MS outgoing depth loops and FFT slice loops do not poll, and incoming
MS preparation can also run without polling. ThreadPoolExecutor.map then
waits for these active calls before returning to the energy-level checks.
The existing final-result guards help prevent publication but cannot shorten
these computational stages. Both mode also prepares incoming fields before
contracting individual solvers.

Single native eigensolves, FFTs and NumPy contractions cannot be interrupted
cooperatively mid-call. Polling must occur at their boundaries. No physical
parameter or normalization change is needed.

## Fix and source acceptance

Changed runtime files: `cancellation.py`, `double_channeling.py`,
`multislice_double_channeling.py`, and GUI `stage_b.py`, `app.py`,
`channeling.py`, `emcd_forward.py`, `propagation.py`. Focused support is in
`gui/cancellation_acceptance.py`, `tests/test_double_cancellation.py` and
`scripts/verify_cancellation_acceptance.py`; installation, quick-start, user
and acceptance documentation identify the replacement build.

One persistent `threading.Event` on EMCDWorker is set directly by the GUI.
The Qt interruption flag remains mirrored for existing worker compatibility;
the Event also survives thread exit so a queued result cannot escape a late
cancellation. The existing dedicated Cancelled condition is now shared with
kernels through `emcd_sim.cancellation`. Optional cancellation callbacks keep
all existing solver calls valid. No unsafe termination or GUI event pumping
was added to kernels.

Checkpoints cover energy and detector batches, BW pixels, incoming setup,
analytical/numerical depth-contraction boundaries, MS incoming/outgoing slices,
ionization depths and site contractions. All active pool tasks observe the
same event and unwind their memory reservations before the GUI returns idle.
Pending pool calls reject work at entry. Both mode now completes BW before preparing incoming MS fields, so cancellation
prevents the second solver from starting at all. Prepared fields from the
active solver are discarded, not published. Arithmetic, summation ordering, precision,
cutoffs, grids, tensor and normalization are unchanged.

The GUI shows `Cancelling...` immediately, ignores old queued progress and
suppresses cancelled result/error callbacks. It finishes as `Calculation
cancelled.`, distinct from completion/failure, and retains the last completed
arrays and browser entry. No partial result is exported or registered.
Energy checkpoints retain the existing provenance-validated, completed-energy
semantics; cancellation is checked before writing a newly completed energy.
Previously valid checkpoints are not removed.

Source validation at native Windows 150% scaling passes. The final source
run's worst request-to-idle latency was **0.6073 s**; an earlier source run's
worst was **0.7435 s**. Controlled runs insert a reproducible **180 ms** work
block at a real kernel boundary, then request Cancel through the actual
button. Uninstrumented BW and MS cases also run. These are explicitly small
package/dispatch profiles, not new converged production benchmarks: Ni [017],
200 kV, 2 nm, beam0.9, potential1.8, FFT24, depth17, grid9,
subpixels16, 11 actual full-range energy samples including locked anchors.

Covered cases: BW full-spectrum depth work, MS outgoing propagation, MS
ionization depth, Both before any incoming MS setup, late completion, repeated Cancel,
Single Channeling, uninstrumented BW and MS, queued result after worker exit,
restart, browser integrity, saved-project integrity and memory-reservation
cleanup. A 10 ms GUI timer continues ticking during controlled cancellation.
Request, acknowledgement, worker-stop and GUI-idle monotonic timestamps are
saved per case. The queued-result race deliberately withholds GUI event
processing and is excluded from latency claims.

Focused tests: **42 unique tests pass** (8 new kernel/regression tests and
34 existing GUI/double/full-energy/component tests). A final affected subset
of 16 tests also passes after adding incoming-setup checks. Initial new-test
fixture errors (missing [017] FFT orientation and invalid five-sample GUI
request) were corrected before acceptance. Direct response and complete
small-profile spectra/maps are **bitwise identical** to baseline kernels for
BW/MS/Both, including raw intensities, decomposition and PRB percentages.
No production thickness or voltage scans were rerun.

Evidence: `outputs/cancellation_acceptance/source_sequential/acceptance.json`,
`kernel_tests.xml`, `focused_regression.xml` and
`final_kernel_checkpoint_tests.xml`, `final_focused_regression.xml` and
`both_sequential_test.xml`. Completed BW/MS project arrays and source
hashes are retained there for exact frozen comparison. Generated datasets are
local acceptance artifacts, not committed reference replacements.

## Native-operation limitation and release handling

A single NumPy/SciPy eigensolve, optimized einsum, matrix multiply, FFT, or
analytical phase/integral construction is not interruptible mid-call. Checks
surround those operations without changing numerical ordering. Oversized
individual calls or heavy system load can exceed the measured latency;
there is **no unconditional 1-2 second guarantee**. Thread-pool shutdown waits
for every active call to reach its next checkpoint, safely releasing arrays.
Allocator-retained RSS is not evidence of an active memory reservation.

The old RC under `build/windows-beta-rc-20261018/` is preserved and **does not
contain this fix**. It must not be presented as cancellation-certified.
The final replacement repeats active BW/MS/Both cancellation, responsiveness,
cleanup, restart, saved-result integrity and matched source/frozen scientific
comparison. Independent clean-machine acceptance remains untested.


## Replacement frozen RC acceptance

**PASS: cancellation fix accepted for local Beta RC use.** Application version
remains **0.4.5**, with build source
`9937d3b820e4225fdf06b7f3ed33c7083d0f35ea`. Final runtime sources were fixed
before this build and their hashes are checked against its manifest. Source
GUI tests preceded the source commit; their dirty-tree provenance records
that fact. No uncommitted runtime change is part of this final candidate.
The working tree still contains unrelated, preserved user scientific files.

The ZIP was extracted to a fresh temporary directory outside the repository.
The extracted EXE ran with a Windows-system-only PATH, without Python/Conda
activation, using isolated LOCALAPPDATA/workspace to protect existing user
state. Native `windows` Qt platform and **150% scaling (DPR1.5)** were used,
without a simulated scale environment. This is acceptance on the development
host, **not an independently tested clean machine**.

| Active cancellation case | Source request-to-idle (s) | Frozen request-to-idle (s) |
| --- | ---: | ---: |
| bw_full | 0.291524 | 0.247749 |
| ms_outgoing | 0.579006 | 0.292975 |
| ms_depth | 0.607271 | 0.292552 |
| both_first | 0.379076 | 0.336708 |
| near_completion | 0.311602 | 0.272307 |
| repeat_cancel | 0.263031 | 0.235931 |
| single | 0.284340 | 0.227595 |
| bw_uninstrumented | 0.129710 | 0.060197 |
| ms_uninstrumented | 0.308799 | 0.141428 |

Controlled cases use 180 ms work blocks; the two uninstrumented cases contain
no artificial delay. Source final worst request-to-idle is **0.607272 s**;
frozen final worst is **0.336708 s**. The worst over all source acceptance
iterations was **0.743492 s**. Frozen worst worker-stop latency is
**0.180328 s**. Timestamped request/acknowledgement/stop/idle records and
GUI timer counts are in `frozen_native/acceptance.json` and `latency.csv`.
These measurements certify the tested profiles, not arbitrary workloads.

Frozen outcomes: **PASS** for BW depth/full-energy cancellation, MS outgoing
propagation and ionization depth, Both before any MS preparation, late
completion, repeated Cancel, legacy Single, queued completion after thread
exit, successful restart, restored controls and memory-reservation cleanup.
No cancelled result entered the browser or replaced the preceding result.
Original saved projects reopened with identical array hashes; newly completed
BW and MS projects also passed checksummed save/open. The final restarted
MS GUI screenshot `frozen_native/restarted.png` was visually inspected.
Normal scrolling and completed status are visible; no GUI layout redesign
was included.

Completed source/frozen **BW and MS arrays are bitwise identical**: raw A/B
four-state EELS, raw/percentage magnetic and nonmagnetic components, PRB,
amplitudes and coherence. Full maps additionally match pre-fix kernels in the
focused source regression tests. No empirical scaling or numerical-threshold
change was used. The final integrity audit verified **1,692 protected
scientific files unchanged**, exact extracted-file/manifest checksums, runtime
source hashes matching the build manifest, and the original RC ZIP unchanged.

Local artifacts:

- EXE: `build/windows-beta-rc-cancel-final-20261018/dist/EMCD-Sim/EMCD-Sim.exe`
- ZIP: `build/windows-beta-rc-cancel-final-20261018/EMCD-Sim-0.4.5-Beta-RC-Cancellation-Fix-Windows.zip`
- Manifest: `build/windows-beta-rc-cancel-final-20261018/build_manifest.json`
- Checksums: sibling `SHA256SUMS.txt`, plus per-file checksums in the app folder.
- Acceptance: `outputs/cancellation_acceptance/frozen_native/acceptance.json`
- Integrity/comparison: `outputs/cancellation_acceptance/verification.json`

ZIP size: **108,689,021 bytes** (103.65 MiB). ZIP SHA256:

```text
309438c4a049773a6e99948477c8d52051cd8f1de632a762c795656e6c5a2216
```

EXE SHA256:

```text
812e010974e22a2ca541198d64ff174a21627d749d313e2915bac9f27bcef693
```

The development intermediate `build/windows-beta-rc-cancel-20261018/` is marked
**NOT FOR DISTRIBUTION**. Only the `cancel-final` candidate above has final
runtime provenance and frozen acceptance. All prior candidates are preserved.
The replacement remains unsigned; semantic version, physics limitations and
experimental-calibration caveats are unchanged. No push, publication or tag.

**NOT TESTED:** independent clean machine/VM, other native display scales,
and a latency bound for production-sized or arbitrarily enlarged calculations.
