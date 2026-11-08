# Phase 2 proposal — Group magnetization and MDFF consistency

**Proposal only. Not implemented or approved by Phase 1.**

## Why Apply currently rejects a changed direction

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
   A future **individual** group reversal should explicitly select/swap that
   group's physical pair and persist its selection; changing its axis text to
   the opposite sign is not currently an equivalent API operation.
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

## Small proposed GUI/data changes

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
