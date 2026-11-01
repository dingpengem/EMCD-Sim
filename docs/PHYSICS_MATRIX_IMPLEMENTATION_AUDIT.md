# MDFF and channeling implementation audit

Date: 2026-11-01. Audited local `main`:
`a77f7455f5fe57dad6bae5d948477b2390433bb0`.

**Acceptance: NO-GO for declaring the microscopic complex-transition baseline
verified.** Two independently reproduced convention discrepancies require
review. No physics fix, default/GUI change, commit, push, merge, release or
Windows build was performed. Existing Ni outputs remain historical results
under their original conventions, not corrected predictions.

Follow-up review: [exact inventory and diagnosis of all 15 regression failures](PHYSICS_REGRESSION_FAILURE_REVIEW.md)
and [final coordinated correction proposal with unapplied diffs](PHYSICS_MINIMAL_CORRECTION_PROPOSAL.md).
The follow-up leaves the production baseline unchanged; it adds five
prospective controls and explicitly tests both native L3 and L2 sign predictions.

## Repository and baseline

The original checkout remains `feat/generalized-multislice` at `1604bb9` with
19 pre-existing scientific files. Work was performed in the newer `main`
worktree `build/source-cleanup-integration`; its only initial tracked change
was the user's `docs/USER_GUIDE.md` edit. The local remote-tracking `origin/main`
also resolved to `a77f745`; no fetch was performed, so live GitHub equality is
not claimed. Baseline fingerprints and test logs are stored separately in
`build/physics-matrix-audit/`. Protected 323 files, including 204 production
checkpoints, match the previous protected manifest. The 19 user files match
their prior hashes. No checkpoints were recomputed or overwritten.

The [source map](PHYSICS_CONVENTIONS_AND_SOURCE_MAP.md) records the inspected
functions, units, assumptions and literature access limitations. The supplied
derivation filename was not found. Published equation references are tied to
the accessible author manuscript/PDF, not guessed from titles.

## 1. Forward target amplitude versus documented dipole convention

This derivation is an independent Fourier/operator check, not an assumption
that two superficially similar MDFF equations use the same index ordering.
Take the implemented fast-electron plane waves `exp(+i k.r)` and
`Q=k_out-k_in`. For Coulomb coupling `1/|r-R-x|`, integrate the fast coordinate:

```
integral dr exp(-i k_out.r) V(r-R-x) exp(+i k_in.r)
    proportional to exp(-i Q.(R+x))/Q².
```

The target excitation therefore contains

```
<f|exp(-i Q.x)|i> = -i sum_a Q_a <f|x_a|i> + ...
                         = -i sum_a Q_a d_a* + ...,
d_a = <i|x_a|f>.
```

With the forward incoming ket and exit bra held fixed, the physical dipole
amplitude is proportional to `sum_a v_a d_a*`. Consequently, for
`R_ab=v_a v_b*` and the declared `T_ab=d_a d_b*`, the contraction is
`sum_ab R_ab T_ba = Tr(R T)`. Production instead computes
`sum_ab R_ab T_ab = Tr(R T^T)` and corresponds to `sum_a v_a d_a`.
Both expressions are positive for PSD tensors; positivity cannot choose them.
A global sign reversal of all Q does not repair a relative conjugation.

The [Rusz manuscript](https://arxiv.org/pdf/0704.1407), Eq. (5), defines its
MDFF with `<i|exp(+i q.r)|f>` and Eq. (17) supplies explicit diffraction
coefficients. The transfer labels and coefficient ordering must be carried
together; importing Eq. (5) alone is insufficient. [Negi et al., Methods,
Eqs. (1–2)](https://www.nature.com/articles/s41598-018-22234-8.pdf) explicitly
includes the target final-state bra in the excitation operator. Neither
comparison validates an arbitrary RP/LP-to-M sign assignment.

Minimal reproduction: `d=(1,i,0)`, two real Cartesian kernels `ex,ey`, fast
path amplitudes `(1,i)`. Production gives `|1+i*i|²=0`; the forward target
excitation gives `|1+i*(-i)|²=4`. This is a deliberately synthetic complex
transition, not a quantitative Ni scattering prediction. Run the unmasked
test command in the validation report to obtain the failure.

### Proposed correction, not implemented

Two alternatives require a convention decision:

1. Keep the declared import convention `d=<i|r|f>`, change every contraction
   consistently to the transposed tensor, and conjugate the explicit target
   modes used by forward-event propagation. Affected paths include
   `contract_cartesian`, `intensities_from_response`,
   `_tensor_angular_maps`, both solver wrappers' even/odd maps, and
   `forward_event_amplitudes`. `DipoleTensor.mdff` can retain its stated
   definition provided all transfer-pair ordering is explicit.
2. Preserve the numerical contractions by defining actual imported target
   amplitudes as `<f|r|i>`. This requires a new explicit schema/conversion,
   provider and polarization audit; changing documentation alone would
   incorrectly reinterpret existing `d=<i|r|f>` datasets. It is not an
   automatically safe fix.

Do not refit eta or swap source RP/LP columns to hide the discrepancy.
An absolute magnetic-sign decision needs a known polarization/helicity reference
and the WIEN2k amplitude/export convention. The effective XMCD source does not
provide those complex amplitudes, so this diagnosis does **not** establish that
every existing experimental magnetic label is reversed.

## 2. Site-phase inconsistency in Single versus Double

For one core site at fractional `u`, inspected Single uses
`P_gg'=exp(+2*pi*i*(g-g').u)`. Double uses amplitude phase
`p_gh=exp(+2*pi*i*(h-g).u)`. With no outgoing scattering only `h=0`
contributes, giving Double pair phase
`p_g0 p_g'0*=exp(-2*pi*i*(g-g').u)`: the conjugate of Single.

Use `g=(000),(200)`, `u=(.137,.081,.019)`, incoming amplitudes `(1,.5i)`,
Cartesian kernels `(1,.2,.1),(.3,1,.2)` and `T=identity`. Single is
`0.8184010927362846`; free-exit Double is `1.8465989072637155`.
This also affects nonmagnetic intensity, so it is independent of the first
finding. The site is synthetic and exercises kernel algebra only; no new
material support is claimed.

The forward Coulomb factor above gives site phase `exp(-i Q.R)`, suggesting
`exp(+2*pi*i*(g-h).u)` for the Double kernel (its detector-common phase cancels).
The minimal proposed patch reverses the sign in `equivalent_site_phases`,
shared by BW and MS. It needs explicit approval because it is a physics-phase
change. It must be validated with nontrivial phases, origin covariance,
complex elastic coefficients and the full approved transfer convention.

For the conventional FCC Ni sites and FCC-allowed integer reflections,
`exp(2*pi*i*hkl.u)=1`. Thus the phase-only correction should leave existing
[001]/[017]/[117] references unchanged apart from roundoff. Passing those
references alone cannot validate the site sign.

## 3. Expected effect on Ni [017] references

These are **algebraic predictions for the tensor-transpose alternative**, not
corrected calculations or an approved relabeling of magnetization. For a fixed
response, tensor conjugation exchanges `I_plus` and `I_minus`, preserves N,
reverses M, `D_flip` and `D_mag`, and preserves `D_nonmag` and `N_A+N_B`.
Raw A/B contrast becomes `D_nonmag-D_mag`. PRB's plus-state denominator also
changes, so PRB need not simply change sign.

Four frozen L3 examples from the completed 300 kV [017] study are exported in
`build/physics-matrix-audit/ni017_hypothetical_conjugation.csv`, without solver
calls. At 10 nm, Bragg X and Y=0, raw `D_mag=-0.0115377679051673` would become
`+0.0115377679051673` a.u.; magnetic percentage would move from `-14.109209`
to `+14.109209` (difference `28.218417` percentage points). At 30 nm, Bragg X
and Y=+15 mrad, `D_nonmag=-0.0110755534167145` stays fixed while `D_mag`
changes from `-0.00410274672819705` to positive; PRB would move from
`-6.259951%` to `-2.937059%`, not to its opposite sign. Source hashes and
all four raw A/B values are in the audit evidence. These examples are not
the separate 200 kV production benchmark.

## 4. Confirmed behavior and limitations

Independent small-model tests confirm complex-Hermitian incoming propagation,
the reciprocal exit bra, independent rectangular incoming/outgoing bases,
analytic depth integration including degeneracy, Gaussian Gram tensor algebra,
proper-MDFF units, detector/reversal identities, and FFT split-step/depth
convergence. Existing tests additionally cover finite Ni BW/MS comparisons and
free-outgoing reduction with trivial FCC phases. They validate implementations
under the current target convention; they cannot settle that convention.

`DipoleTensor` construction accepts a finite Hermitian but indefinite supplied
tensor. The transition factory guarantees PSD, and Double/MS validate it;
the Single path lacks an equivalent tensor-level PSD gate. This validation
gap is documented, not patched during the physics stop. No absorption is
supported: complex eigenvectors are tested, complex eigenvalues are rejected
by the Hermitian solver. The frozen q_z, projected IAM, continuous event-depth
average, finite path support and uncalibrated XMCD-effective MDFF remain
approximations. Existing [111] and detector-grid convergence failures remain
failures; no new convergence thresholds were introduced.

## 5. Review, validation and rollback proposal

Stop before any production phase/conjugation patch. First review both minimal
reproductions and choose a complete target/MDFF/transfer convention. Then use
an isolated branch/worktree, implement the approved minimal change, remove
the corresponding strict expected-failure markers, and run the independent
controls plus the practical regression suite. Compare raw four-state spectra,
N/M components and percentages against the frozen baseline, classifying
intentional sign changes explicitly. Preserve old arrays; never regenerate
them merely to obtain a pass. Add a nontrivial-site origin-covariance control
before claiming the phase fix verified. Rollback consists of discarding that
isolated patch; the current audit leaves every production source unchanged.

Only after that gate: specify genuine DFT complex transition data with site,
core j/mj, band, k/weights, occupations, energies, Cartesian axes, magnetization,
operator units, bra/ket convention and WIEN2k build provenance. Verify gauge
and transition-product invariance, PSD and independent amplitude contractions
before coupling to channeling. Do not infer complex dipoles from intensity-only
XMCD/symmat files or convert momentum to length gauge without an operator/SOC
audit. No DFT calculation or tensor reconstruction was started.
