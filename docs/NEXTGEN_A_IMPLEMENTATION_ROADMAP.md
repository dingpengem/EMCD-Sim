# Next-Gen A: implementation roadmap and bounded B specification

Date: 2026-11-21. **Design only; Next-Gen B has not begun.**
Read with the [architecture audit](NEXTGEN_A_ARCHITECTURE_READINESS.md),
[physical model](NEXTGEN_A_DEPTH_STEM_PHYSICS_DESIGN.md) and
[measured baseline](NEXTGEN_A_PERFORMANCE_BASELINE.md).

## Decision and immediate scope

Evolve responsibilities incrementally, retaining today's flat kernel package
and public `emcd_sim.forward_pipeline.calculate` interface. Start B with one
small experimental CPU orchestration module, not a repository-wide package
migration. Add a package only when a coherent responsibility has multiple
implementations worth grouping. Package moves do not solve probe coherence,
event depth, array semantics or memory residency.

The smallest high-value scientific step is an **explicit, ordered real-potential
slice stack with one or two independently localized core-loss events**, and
direct/adjoint detector evaluation. It makes a presently implicit physical
assumption testable. Merely returning the present projected depth integrand is
a useful separate diagnostic, but cannot be labeled a localized 3D specimen
calculation. Do not make that diagnostic a prerequisite for the independent
prototype if it would require changing protected kernels.

Immediately before B, agree the units/frames/event measure, independent dense
reference and tiny result contract below. Reuse existing transport and source
validation. Defer GUI controls, full ASE slice generation, historical imports,
large result schemas, GPU abstraction and bulk module moves.

## Proposed interfaces, not production classes

Names here describe responsibilities; they are not newly exported interfaces.
Each request has a versioned physical-model identifier and validated explicit
inputs. Avoid a universal settings object spanning materials, probes, storage
and scheduling.

| Interface | Meaning; inputs → outputs; dimensions / units / frame | Ownership, mutability and memory | Reuse and required independent checks |
|---|---|---|---|
| `SliceSpecimen` | Ordered elastic medium and event geometry. `z_edges(Nz+1)` nm, slice generators `(Nz,Fy,Fx)` nm⁻¹, transverse cell `(2,2)` Å, voltage and declared interaction scaling → energy-specific transport plans. Later an explicit adapter converts 3D atom positions/potentials to this representation. Wave axes follow the declared dual cell. | Validated immutable input view/copy, caller retains source; calculation owns worker-local plans. Can stream slices; do not require all energy transmissions resident. | `FFTSplitStep`, `ProjectedGeometry`; independent Fourier/dense generator check, noncommuting order, unitary/vacuum limits, Å/nm and energy scaling. |
| `IncidentState` / future `ProbeSpecification` | Coherent boundary coefficients `(batch,Fy,Fx)` complex128 plus energy, carrier cycles/Å, explicit norm/cell measure. Probe specification adds convergence aperture, phase/aberrations, defocus and source-mixture weights → incident complex fields. Nominal microscope frame. | Input specification immutable; calculated fields owned by execution context. Batch bounded; no global mutable wavefield. Partial coherence is an explicitly weighted ensemble. | Current plane boundary and FFT convention; independent analytic aperture/defocus/translation phase, Parseval, plane-wave limit and two-component interference. |
| `ScanSpecification` | `positions(P,2)` Å in a named transverse frame, optional raster `(Ny,Nx)` index map/trajectory and batching → position batches. Positions are coordinates, not new material configurations. | Immutable position list; scheduler owns iterator/progress, not the wave physics. Flat list supports sparse/nonrectangular scans. | No current genuine scan API. Test coordinate/order preservation, translations, periodic wrap only when requested, batch/order invariance. |
| `LocalInteractionSet` | Event boundary/depth, transverse site position, occupancy, tensor/source/frame and energy eV → local complex transition actions and independent target-channel weights. Tensor `(E,3,3)`; a small dense reference may use `(mode,Fout,Fin)`, while production applies compact operators. | Declared event inputs immutable; source validator owns cached host tensors, context owns prepared actions. Do not materialize a full operator for every probe/depth/detector. | `transition_modes`, dipole kernels, declared MDFF providers and explicit magnetic pair handling. Check dense PSD contraction, conjugation, site incoherence, reversal and frame covariance. |
| `PropagationState` | Handoff of coefficients, current boundary/depth, energy, basis/FFT layout, normalization, physical model and residency → next state. No ambiguous intensity-only state. | Context owns mutable workspace; public snapshots/read-only views have stated lifetime. Retain histories only by policy; expose no stale reused buffer as a completed result. | Existing complex coefficients and plan primitives. Check batch equivalence, direct/adjoint identity, no input mutation and live-memory bound. |
| `DetectorResponse` | Fixed laboratory/reference-frame coordinates, aperture/pixel weights, measure and energy response → raw detector intensities/density traces. Scalar reductions `(probe,energy,detector)` or selected `(qy,qx)` maps, with units explicit. | Specification immutable, weights reusable/read-only; reduction buffers are batch-owned. Do not move detector with each incident angular component. | `VirtualDetector`, fractional weights and `integrate_detector_block`. Check full-aperture norm, fractional area, fixed-detector coherent limit and physically applicable symmetry. |
| `ScientificResultBlock` | Data arrays with named dimensions, coordinates/units, norm, model/method, source provenance, validity and completion. Examples `(probe,energy,detector,magnetic_state)` or optional `(event,probe,energy,detector)`; depth is not total thickness. | Completed block immutable after transfer to sink. Bounded NumPy block on CPU first; storage adapter owns persistence. Complex fields are explicit diagnostics. | Existing spectrum/map/result metadata inform adapters, not an unlabeled dictionary dump. Check reduction from raw parents, NaN masks, axis order, lossless I/O and batch assembly. |
| `ExecutionContext` / later `ComputeBackend` | Dtype, device/array residency, workspace budget, worker policy, cancel/progress → transport/contract/reduce operations and completed blocks. Contains no material defaults or physical approximations. | Context owns plans/workspaces/native-thread policy; host/device upload/download explicit. Per-device caches bounded and invalidated by input identity/shape/dtype/energy/frame. | Current NumPy/native/resource services first. Check no implicit transfer, deterministic scientific batch equivalence, cancellation cleanup and process/device memory accounting. |

All names, fields and shapes above need narrow validation errors. Unsupported
complex absorption, nonlocal excitation, invalid tensor/frame, missing event
normalization, source energy outside support or device/dtype combination must
raise an explicit limitation/error. No silent physical-model/material fallback.
Current neutral settings and project loading remain usable; new objects do not
inherit every legacy GUI/numerical setting.

Illustrative signatures:

```python
# Existing API stays unchanged and remains the production entry point.
calculate(structure, settings, cfg, *, sites=None, energy_ev=None, ...)

# Proposed experimental B API: CPU, plane entrance, no GUI/storage dependency.
evaluate_local_events(specimen, incident, interactions, detectors, *,
                      energies_ev, retain_event_contributions=False,
                      execution=None) -> ScientificResultBlock

# Later shared orchestration; not three separate parallel/CB/STEM kernels.
iter_response_blocks(specimen, illumination, interactions, detectors, *,
                     scan=None, energies_ev, batch_policy,
                     execution) -> Iterator[ScientificResultBlock]
write_blocks(blocks, result_sink)  # storage is separate from calculation
```

The new path must share linear transport, local interaction and detector
primitives with current calculations wherever the physical model is the same.
Distinct physical approximations have explicit labels and consistent contracts;
they are not hidden branches selected by material name. Integration into
`calculate` is a later additive, validated adapter, not an immediate API break.

## Minimal Next-Gen B: concrete implementation specification

**B1 scope.** Non-GUI CPU, float64/complex128, coherent plane entrance,
single localized independent dipole event, real/Hermitian elastic slices,
post-loss outgoing transport, fixed detector, explicit event-resolved and summed
relative intensities. Start with 2–3 slices and 1–2 interface events on 4²–8²
periodic transverse grids. At most two losses and three Cartesian transition
modes per event. Supply synthetic sinusoidal slice generators directly in
nm⁻¹ with explicit energy scaling; this is a declared model input, not a
pretend atom-derived 3D potential. Use finite relative units with declared
event occupancy. Do not claim quantitative material predictions.

**Physical calculation.** Propagate the incident state to an event interface;
apply the local Cartesian transition operator with a full PSD complex tensor;
propagate each independent final mode through the remaining ordered slices at
`E_in-E_loss`; apply a positive detector weight; sum mode intensities and
independent events. Also evaluate the reciprocal detector amplitude using the
adjoint ordered product. Keep incoming/outgoing energies and Fourier norm
explicit. An event inside a slice, complex absorption or coherent intersite
excitation remains an explicit unsupported condition in B1.

**Reuse.** Call `FFTSplitStep`, `propagate_slices`, `transition_modes` and
`forward_event_amplitudes` without modifying their protected source. Reuse
existing detector/tensor validation where its assumptions match. If a required
primitive cannot be reused without an identity change, stop and propose that
specific scientific change separately; do not copy the kernel into a new file.

**Candidate edits after B authorization.** One new small
`src/emcd_sim/depth_events.py` experimental orchestrator with narrowly scoped
input/result definitions; `tests/test_depth_events.py` and a small independent
dense reference; one headless example plus physics documentation. Split a
package only when justified by a second coherent implementation. Existing
`forward_pipeline.py` need not change for B1. `projected_potential.py` and
`structure_geometry.py` need no changes until a separate B2 atom-to-slice
adapter is scientifically specified. No GUI or project schema changes for B1.

### Independent B acceptance cases

| Case | Independent reference and assertion | Failure prevented |
|---|---|---|
| Ordered two-state system | Analytic Pauli-matrix exponentials for two noncommuting Hermitian generators, independently multiplied in physical order | Same-kernel self-reference or accidentally commuting slices |
| Tiny Fourier grid | Explicit DFT matrix plus dense SciPy `expm` of each full generator, with grid/step refinement against split-step transport | FFT sign/norm, kinetic/potential placement and split-step error |
| Direct vs reciprocal event | Independently formed dense `U_after J U_before`; compare complex detected amplitudes, not only their squared norm | Wrong adjoint, missing conjugation or reversed order |
| Event movement | Place the same event at distinct interfaces in nonuniform slices; independently predict different intensities/phases where expected | Merely attaching depth labels to an integrated signal |
| Tensor factorization | Dense full-complex Hermitian PSD MDFF versus three independent transition modes, with rank-one and full-rank tensors | Dominant-mode shortcut, missing imaginary/real-odd terms, wrong `L` conjugation |
| Independent sites | Two identical independent target events give `2*I`, not coherent `4*I`; unequal weights/permutations preserved | Incorrect intersite coherence or double-counted density/occupancy |
| Energy and detector | Independently constructed outgoing generator at reduced energy; detector full-aperture and restricted-aperture cases | Reusing incoming energy or moving the aperture with illumination |
| Mathematical invariants | Norm/Parseval for real transport; Hermitian/PSD responses; zero event set → zero; correct continuum zero-measure limit where that model is used | Artificial renormalization, nonpositive response, invalid zero-thickness assertion for a fixed discrete event |
| Current limiting case | Repeated projected slices, plane incidence, matching event quadrature/support/norm compare to existing complete direct-depth/adjoint fixture | Unintentional disagreement under identical assumptions |
| Negative controls | The independent reference detects intentionally wrong product order, phase conjugation and incoherent/coherent site reduction in test-only alternatives | Tests passing because their observable cannot see the intended error |

Use amplitude/tensor comparisons at parent scale with error budgets derived from
float64 roundoff, operator norms and split-step convergence, not universal
bitwise equality or values selected only after a pass. Check shapes, dtype,
coordinates, NaN masks and lossless serialization exactly. For cancellation-
sensitive magnetic differences compare to meaningful parent intensities and the
existing numerical-contract rationale. Preserve the current references and
tolerances. A finite-grid dense reference should be independently assembled;
calling the production propagator twice is not independent validation.

**Execution bound.** The first B reference matrix must fit comfortably below
128 MiB of additional arrays, cap dense references at 64 coefficients, use one
BLAS thread and bounded batches. Set an owned-job timeout no greater than
120 s for the tiny acceptance group; if it exceeds the bound, inspect the cause
instead of increasing it repeatedly. Record setup, calculation, memory and
normalization. No absolute speedup target is justified before a B calculation
exists. A convergence sequence and absence of unbounded all-events/all-detectors
allocation are performance acceptance; the present noisy Ni timings are not a
pass/fail time threshold for different physics.

**B1 GO:** the independent cases pass, event displacement is physically
observable, direct/adjoint complex amplitudes agree, normalization is explicit,
protected source remains intact, and memory/cancellation is bounded. **Stop**
if event density/source normalization is ambiguous, the order/phase reference
disagrees, retained support is insufficient, or real-potential adjoint assumptions
are violated. No STEM or quantitative-material label follows from B1 GO.

**B2 scope, separately justified:** connect an atom-resolved 3D slice-potential
builder and local atom events to B1, derive units and longitudinal discretization,
and converge real specimen examples. This prerequisite precedes claims of
material-resolved localized depth contrast. It is scientific development, not
an architecture refactor.

## Later generations and dependency order

| Generation | Prerequisite / affected responsibility | Delivered capability / independent reference | Performance and GO/stop criteria | Compatibility risk |
|---|---|---|---|---|
| B1/B2: depth CPU | Explicit slice/event/result contracts; new orchestrator; later potential/site adapter | Ordered localized event transport; analytic/dense references, then independently validated atom-to-slice model | Bounded tiny CPU matrix and convergence; stop on ambiguous event normalization or order/adjoint mismatch | Additive experimental entry; no historical schema or pinned-source edits |
| C: coherent probe | B transport/events; incident-state boundary and full momentum-support contract | Aperture/aberration probe, phase-coherent angular components; analytic vacuum aperture/defocus, two-component interference, matched plane-wave limit | Probe/support/supercell convergence and correct norm; stop if retained Bragg support misses aperture physics | Preserve plane API; explicit illumination kind instead of changing legacy plane semantics |
| D: real-space scan | C plus physical position coordinates, iterator/scheduler, reduced blocks and **bounded chunked storage before large scans** | Position-dependent response; translations, symmetry under valid assumptions, batch/permutation invariance; matched external nonmagnetic core-loss case | Peak workspace depends on tile size, not total positions; no fake independent-tilt scan; stop if probe and specimen frames drift | New result/schema version only for new dimensions; schema-1 loads unchanged |
| E: measured GPU | Validated CPU workload and resident backend boundary; transport/FFT/contract/reduce adapters | Same selected physical model on an accelerator; CPU plus independent small references | Record transfers, peak device/host memory, warmup and stable larger-workload speed; no GO merely for CuPy import success | Device/backend/dtype metadata explicit; preserve CPU/default precision and saved CPU projects |
| F: HPC studies | Stable batch API, storage completion semantics and per-worker context | Distributed independent positions/parameters with resumable output | Independent single-process comparison, scheduler-order invariance, bounded per-worker memory and interruption recovery | Explicit schema/provenance compatibility; no process-global allocator assumptions across nodes |

Chunked storage is moved forward from E because dense scan output is already
hundreds of GiB without any GPU. C and small D can begin with in-memory bounded
blocks; the large D milestone cannot. Do not wait for distributed execution to
define named axes, completion and cancellation semantics.

## Safeguards and acceptance handoff

Preserve the three existing whole-file scientific pins, independent historical
references, saved-source identity, formal release inventories and current
numerical contracts. Source moves/import rewrites can change authentication
even when equations do not change. Historical project compatibility belongs in
the loading/schema layer and does not justify retaining every obsolete name.
Never mutate an old project to reinterpret its plane-wave data as a scan.

Before any future promoted production path, run affected mathematical and
behavioral tests first, then the existing source-equivalence/project-compatibility
mechanisms required by the touched surfaces. A new Windows release needs the
project's existing native acceptance process; neither this design nor B1 bypasses
it. No new arbitrary hashes, frozen reference layers or gates are proposed here.

Next-Gen A acceptance record: actual source traced; depth/CB/scan gaps identified;
memory/storage/backend boundaries quantified; 29 bounded CPU cases recorded;
eight targeted existing tests passed; current sources/references/build unchanged;
four requested reports and separate benchmark tooling committed locally on the
new branch. No new scientific model, full regression, EXE build, push, merge,
tag or publication occurred. **GO applies to completing A and proposing B as a
separate implementation task, not to a new scientific or release capability.**
