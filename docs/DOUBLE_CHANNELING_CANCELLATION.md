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
there is **no unconditional 1?2 second guarantee**. Thread-pool shutdown waits
for every active call to reach its next checkpoint, safely releasing arrays.
Allocator-retained RSS is not evidence of an active memory reservation.

The old RC under `build/windows-beta-rc-20261018/` is preserved and **does not
contain this fix**. It must not be presented as cancellation-certified.
After source validation a new isolated RC must repeat active BW/MS/Both
cancellation, responsiveness, cleanup, restart, saved-result integrity and
matched source/frozen scientific-array comparison. Independent clean-machine
acceptance remains untested. Package results are recorded below after testing.
