# Generalized multislice architecture — Milestone A

Development branch: `feat/generalized-multislice`, based on reviewed local
`56526357264b2d576ae559ba85cf6bda55e4a4e3`. Main was
`236893392838ab5bc17dcf1848fd127009f2f048` at preparation. No merge, release,
version change or Windows rebuild is part of this milestone.

## End-to-end follow-up

[GUI and scientific integration evidence](GENERALIZED_MULTISLICE_EMCD_VALIDATION.md)
now exercises normal Single/Double BW/MS workflows for the five representative
orientations. An implicit `(200)` row fallback was replaced by declared-target
or actual local-x beam-support selection. GUI descriptions distinguish outgoing
channeling and ideal two-beam support correctly. The shared physical pipeline is
unchanged. [111] finer quadrature passes representative increments, while joint
raw-intensity/support sensitivity remains unresolved. Atomic 3D remains deferred.

## Final review

[Merge-readiness assessment](GENERALIZED_MULTISLICE_MERGE_READINESS.md): GO for
bounded research source support, not unrestricted quantitative certification.
Incoming/outgoing prepared FFT contexts now reject mismatched microscope/frame/
reciprocal data and depth quadrature. Large-cell work checks are overflow-safe.
These validation guards do not change valid propagation or the MDFF. [111]
certification limits are visible for every solver and equivalent zone multiples.

## Audit and scope

The reviewed branch contained validated [117] work beyond main, together with
[001]/[017] projected implementations. GUI propagation and numerical checks
selected geometry providers by zone; the default FFT path assumed a [001]
potential. The historical [017] FFT cell was rectangular and nonprimitive;
[117] used an oblique primitive cell. Sharing their propagation kernel alone
did not remove these geometry dependencies.

Atomic P1 documentation exists on main, but its geometry implementation is
absent from this source tree. `feat/atomic-3d-multislice` at
`71b068d8eedfc566ad626fe2634ae8d7c61527ac` contains structural subslicing work;
that is not an implemented atomic potential or atomic EMCD backend. It is not
silently imported into this milestone.

Milestone A now uses one structure-derived projected backend. [001], [017],
[117], [111], [710], and an additional [123] cell-covariance control use the
same algorithms. This is bounded support, not universal numerical convergence.

## Layer boundaries

| Layer | Responsibilities | Exclusions |
|---|---|---|
| `crystallography.py` | Crystal-to-local proper rotation; exact integer ZOLZ kernel and motif translation congruences; metric reduction | No GUI, projected-potential or propagation dependency |
| `projected_geometry.py` | Primitive reciprocal plane, optional explicit sampling cell, real-space dual cell, exact hkl lookup and Nyquist checks | No atomic-z potential or ionization model |
| `projected_potential.py` | Actual IAM structure factors, occupancy/Debye–Waller labels, Fourier cutoff, phase units and resource admission | No orientation presets or fitted potential factors |
| `multislice_double_channeling.py` | Existing symmetric FFT split-step, incoming fields, reduced-energy outgoing adjoint fields and existing response contraction | No BW elastic eigenmodes |
| GUI adapters | Configuration, shared frame, metadata, detector integration and saved-project guards | No zone-specific geometry provider |

`ProjectedFFT.from_potential` can prepare a field directly from geometry,
potential and microscope; it does not require a BW model. `build` is the existing
elastic-model adapter. The old name `ProjectedNiFFT` aliases the same general
implementation for callers; it is not a separate Ni algorithm.
`multislice_reference.fft_multislice_ni` remains a Ni convenience input wrapper
around the general potential and existing FFT stepper.

## Coordinates and reciprocal lattice

The rows of R are local x, y, z in crystal Cartesian coordinates:
`r_local = r_crystal @ R.T`, `g_local = R @ g_crystal`, and
`T_local = R @ T_crystal @ R.T`. Nominal z follows `[uvw] @ cell`.
A nonzero ZOLZ target defines positive local x; y completes a right-handed
orthonormal frame. Incident tilt is independent and enters the existing
kinetic/momentum-transfer convention. Magnetization remains declared in
crystal Cartesian coordinates and rotates once, including reversal.

An extended-GCD integer kernel spans `hu+kv+lw=0`. Rational translations that
permute the actual decorated motif impose exact reciprocal congruences.
Potential site labels include species, occupancy and Debye–Waller factors.
Unknown providers cannot assume chemical translations preserve their potential.
Non-translational structure-factor extinctions remain Fourier coefficients.
Higher-order targets do not remove lower-order allowed reflections.

For row generators B, `G(m,n) = [m,n] @ B @ reciprocal_cell`. No orthogonality
is assumed. The transverse real cell is the inverse transpose of the transverse
reciprocal matrix; its absolute determinant is the area in Å². The kinetic
operator uses actual Cartesian G and the existing `|G|² + 2 k_perp·G`, including
cross terms for an oblique cell. Miller signs are preserved by integer lookup.

## Potential normalization and propagation

The existing IAM Fourier convention is retained:

```text
U_G = 10 * gamma * lambda_angstrom * F_G / source_cell_volume_angstrom3
U(x,y) = sum_G U_G exp(2 pi i G·r)       [radians/nm]
T(dz) = exp(i U(x,y) dz_nm)
```

The mean elastic phase is removed as before. Source-cell volume fixes density;
changing to a primitive transverse cell introduces no extra density/area factor.
FFT coefficients are `fft(wave)/number_of_samples`. No phase fitting or
normalization of truncated amplitudes is applied. `FFTSplitStep.advance` retains
the existing symmetric K/2–V–K/2 mathematics; a negative step is its adjoint.
The explicit two-beam option still projects inside the potential exponential,
which is distinct from cropping an unrestricted propagated wave.

Single and Double use the same geometry and potential preparation. Double
retains the existing post-loss wavelength/interaction scaling and depth
contraction. All mirror directions are evaluated explicitly: no orientation
predicate supplies a presumed reflected response. This can cost more than the
old [017] mirror-reuse optimization, without changing the physical model.

## Compatibility and removal of legacy modules

Matched-sampling tests against reviewed algorithms passed before removal from
`src/emcd_sim`. Their exact sources remain under
`tests/fixtures/reviewed_geometry/`; `tests/legacy_geometry.py` loads references
only in tests. Historical reports and numerical arrays remain intact. Production
and GUI imports are checked by AST. Research scripts select configurations through
the generic `study_geometry.py`, not orientation-specific algorithms.

The [017] primitive generators are `(200),(1,7,-1)`; the historical full FFT
table used `(100),(0,7,-1)`, including exact extinctions. At fixed mesh these
are different sampling cells. New projects record explicit `fft_generators`.
Old full tables reconstruct their generators from the saved integer ordering;
the complete table is checked. Reduced-row tables are checked against their
saved row, with a structure-derived unused transverse complement. Ambiguous
recipes remain viewable but cannot silently rerun with a different cell.

Old saved structural frames are also checked against the current target-aligned
frame for every axis. A mismatch preserves saved viewing and blocks automatic
input reuse until local tilt/detector coordinates are re-entered. Changing target
can change local axes; numeric tilt and detector coordinates refer to the
currently displayed frame, not a fixed crystal Cartesian screen.
No orientation-specific production compatibility adapter remains.

## Limits and review

- Integer input components: at most 10000; bounded intermediate integer geometry.
- Translation search: 1–256 sites; reciprocal enumeration: at most 500000 candidates.
- General FFT API: even rectangular dimensions 12–512; GUI remains even square
  12–128, with the existing 121-beam interactive cap.
- Harmonics touching Nyquist or outside the requested grid cause an error;
  no silent truncation, strain or fallback to another zone.
- Existing memory/RAM admission and cancellation cover potential and incoming/
  outgoing arrays. More than 200000 split steps is explicitly rejected.
- Elastic geometry supports general cells. Bundled scattering factors and GUI
  magnetic calculations remain constrained to their existing supported Ni model.
- The MDFF, BW Hamiltonian, Coulomb factors, tensor rotation, defaults and public
  version were not refitted or changed. [111] quadrature failures remain reported.

See [validation and numerical evidence](GENERAL_ZOLZ_MULTISLICE_VALIDATION.md)
and the [Atomic 3D plan and acceptance gates](ATOMIC_3D_MULTISLICE_DEVELOPMENT.md).
