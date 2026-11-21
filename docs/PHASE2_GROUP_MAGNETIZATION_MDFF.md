# Group magnetization and MDFF consistency

## Current development Global XMCD workflow

Import the CIF, then open Material → 3D Structure Viewer → Site groups. Set
Global Material M and open Configure MDFF in Global context. Source entry or
Browse automatically checks the five-column file and native energy range.
Element/edge labels describe the editing context; suggested native peaks are
not authoritative source assignments. Confirm RP−LP about Material +M and the
displayed L3/L2 assignments beside the source controls. The visible relative
reference default is 1 after source-max normalization, not an absolute cross
section. Provenance and honest model limitations are generated when optional
overrides are blank; parsing never establishes physical material calibration.

MDFF **Done** validates and returns the parent draft without accepting Material.
Viewer **Apply and Close** accepts direction and provider together. Cancel
discards unaccepted changes. Continue downward through the existing Settings
sections; new projects use editable general numerical defaults, including
2.5/2.0 Å⁻¹ beam/potential cutoffs, without claiming convergence. Saved numerical
choices remain intact. Save/Open retains the accepted generalized provider.

Saved historical Ni configurations preserve the original adapter and v0.8
behavior internally. Reference-Ni choices are not ordinary configuration inputs;
new source-backed configurations are not restricted to the 3.524 Å reference cell.
This workflow is in development source/new local candidates only. Previously
accepted candidate artifacts remain unchanged. magCIF and general tensor
rotation remain future work.

## Local group workflow

In Site groups choose Local Site Magnetization Mode, select the group, and
declare its crystal-Cartesian direction with Update direction. Configure MDFF
must show that group's context and read-only target. It does not require an
initial outer Apply or an accepted Global provider. XMCD file selection checks
format/range and suggests native L3/L2 selections; confirm the actual convention
and assignments. Element/edge describe the editing context, not file metadata.
Relative reference 1 is a defined relative scale, not absolute calibration.
Optional source details have generated honest defaults. Atomic uses its visible
element-specific reference energies, full frame and electronic parameters; these
remain approximate/synthetic unless independently calibrated.

Preview checks and displays the draft without accepting Material. An unchanged
preview does not reset scientific confirmations. Done returns a ready group
draft; Apply and Close accepts the groups together. Cancel preserves previous
accepted settings. Source changes still require review, and full tensor-frame,
species, reversal and coverage checks remain enforced. M alone never supplies
an anisotropic frame. Save/Open retains accepted group/provider settings.

Select declared edge samples for a small diagnostic, or deliberately request
full modeled-source coverage. The Local workload label reports actual energy
and pixel counts; full coverage on a 97×97 grid is much more work than two
samples on 9×9. No numerical convergence or calibrated material accuracy is
implied, and no source tails or automatic intensity calibration are introduced.

**Bounded compatible-direction binding is implemented. General tensor rotation
and the broader follow-on proposals below remain unimplemented.**

## Implemented bounded workflow

Group Apply prepares every prospective direction/provider binding before
accepting any of them. Existing provider tensor interfaces are tried unchanged.
An opposite source axis can select the minus member only when the source has
already supplied a validated `explicit_pair_shared_even` physical pair.
`ImportedSettings.pair_reversed` defaults to false for old configurations and
is saved through the existing project configuration. It records this selection
independently of the global reversal flag.

The preparation adapter calls the original provider at its native axis and
exchanges the complete physical pair. Source bytes, identity, declared axis,
`frame_to_crystal`, energy support and amplitudes remain unchanged. Reversed
binding provenance separately identifies the original and effective directions.
`ImportedMDFF.tensors()` and its axis/frame/PSD checks are unchanged.

Failed Apply retains the accepted model and leaves the requested draft visible.
Its error identifies the group, requested direction and source axis/frame and
points to that group's MDFF Editor. Cancel recovers accepted state. Save rejects
unapplied direction/provider or reversal changes on a configured local model;
it cannot silently promote a failed draft to accepted state. Unconfigured
structural drafts remain saveable and do not become calculation-ready.

Successful changes recreate the affected cached MDFF editor from its accepted
source when needed. If reversal is accepted in that editor, its displayed pair
is refreshed too. Other groups retain their own binding. Save/Open preserves
the selection and recalculation uses it. An unchanged XMCD source retains its
original axis declaration. A reversed analytical Manual source can remain in
the existing imported-source view to avoid reconstructing a different model.

Focused checks cover full-pair selection (including real reversal-odd entries),
rollback, Cancel, editor refresh, XMCD declarations, and one small restored GUI
calculation. Native Windows source-GUI Apply/Save/Open/recalculation is checked
separately. Broad source-guard verification remains incomplete; no new pin
maintenance, full regression or release acceptance is claimed.

## Original rejection and retained validation boundary

`SiteGroupEditor.update_direction()` changes the selected Qt draft row and its
arrows. It deliberately does not change the provider. `apply()` calls
`group_mdff.validate_group_reference()`, which resolves the acknowledged source
through `mdff_providers.load_site_group_provider()` and checks it at its required
energy bounds. `ImportedMDFF.tensors()` requires the normalized requested group
axis to match the source's declared `magnetization_crystal` to 1e-10. It also
uses the independent proper orthonormal `frame_to_crystal`. A new group direction
alone cannot satisfy that source declaration.

Thus changing Fe(A) from -z to +x with an unchanged -z source fails before
`_accepted_rows` / `accepted_site_groups` are replaced. Cancel recovers the
accepted configuration. This protects physical consistency; changing this check
to accept arbitrary axes would hide a real scientific mismatch.

## Preserve two distinct operations

1. **Physical reversal:** the current Local-mode `Flip all local M` selects all
   providers' explicitly supplied minus states using `reverse_magnetization`.
   It retains the native group axes and tensor frames and reverses the displayed
   arrows. Complete physical +M/-M tensors, not imaginary parts or conjugation,
   define the reversal. Even/odd tensors may be expressed as
   `(T_plus+T_minus)/2` and `(T_plus-T_minus)/2`; the odd part need not be purely
   imaginary. Reusing this validated pair is appropriate for a pure reversal.
   The bounded individual-group binding now persists that explicit physical-pair
   selection. It does not rewrite or conjugate the source tensors.
2. **Arbitrary direction change:** a direction supplies two degrees of freedom,
   not a full anisotropic frame. The user must provide the full proper rotation
   or a newly calculated/measured MDFF consistent with the new direction. A
   spin-only change with crystal-fixed anisotropy is not generally a rigid
   rotation of the complete tensor. It needs a declared provider model; do not
   rotate every tensor merely because M changed.

For an explicitly justified rigid-frame rotation U, existing local tensors with
frame F would have crystal tensors `U F T F^T U^T`, for **both** physical states;
the microscope transform C gives `(C U F) T (C U F)^T`. Require orthonormality and
determinant +1. Retain the same energy samples and amplitudes. Crystal-Cartesian
sources require their identity-frame rule to be respected: either explicit
transformed numerical tensors and a new declaration, or an explicitly declared
local source with the new full frame. This is a proposed input operation, not
new scattering physics or material calibration.

## Sampling in the current development workflow

After CIF import, explicit Local M/MDFF configuration, Done and Viewer Apply and
Close, use **Shared Calculation Settings → Inelastic and Angular Sampling**.
Energy sampling and angular output are independent:

- **Entire energy range — uniform sampling** is the new-project default: 241
  requested points across each declared modeled source range, with selected
  energies inserted exactly. For the Ni example this gives 243 actual samples.
- **All native source energies** retains source samples (4,329 for the supplied
  Ni XMCD file). The uniform-count field is hidden; the actual count is shown.
- **Selected energies only** evaluates the declared energies, without inventing
  a continuous spectrum or unsupported tails.
- **Full angular maps at selected energies** is enabled by default. Single
  Channeling evaluates the complete angular grid at those energies and exactly
  the nonzero fractional-detector support elsewhere. Turning maps off retains
  detector spectra. **Full angular field at every energy (advanced)** explicitly
  restores the broader evaluation; only selected maps are retained.

Single Channeling shares incoming propagation/coherence, weights, group phases,
provider tensor pairs and the fixed reciprocal basis. Energy-dependent qz and
Coulomb factors still use each actual loss. Raw work remains in bounded energy
blocks. Source amplitudes and per-ionizing-atom normalization are unchanged.
Saved native/full-field configurations retain those choices on Open; new
defaults do not silently migrate historical calculations. These changes are
development source only and do not update earlier accepted EXEs. Double
Channeling optimization and scientific convergence are not acceptance claims
of this Single Channeling task.

## Broader follow-on proposal (not implemented)

- Keep the selected-group/count summary and group-level direction controls.
  Label pending directions clearly. On a mismatch, link the existing
  **Configure MDFF for Group** action and state that the accepted configuration
  is unchanged. Do not offer a silent Global M fallback.
- Separate a reversal selection from arbitrary-direction editing. Only expose
  reversal where an independently validated physical pair is available.
- For arbitrary changes, retain source editing/replacement as the conservative
  default. An optional rigid rotation needs an explicit model assumption and
  complete frame confirmation; do not infer the remaining frame angle from M.
- Prepare prospective rows/provider declarations together; validate every source,
  frame, axis, window and structure assignment before atomically replacing the
  accepted configuration. Failure leaves accepted rows, sources and amplitudes
  intact. Reuse current managed-source/portable-attachment identity mechanisms.
- Persist accepted group axes, full frames, physical-pair selections, source
  provenance and incomplete editor drafts distinctly. Save/Open must not turn
  an invalid draft into an executable provider. Revalidate on rerun, while saved
  result arrays remain viewable if external sources are missing or stale.

## Proposed acceptance checks

Use Fe(A)/Fe(B) with explicit PSD pairs: group-wide editing without atom picking;
global and independent physical reversal; confirmed full-frame rotations and
round trips; unchanged reference amplitudes/windows; Apply failure rollback;
Cancel and Save/Open of accepted versus incomplete state; no Global M override.
Exercise anisotropic tensors and reversal-odd real components so conjugation or
alignment shortcuts cannot appear correct by accident. Scientific validation,
contraction conventions and historical numerical references remain unchanged.
