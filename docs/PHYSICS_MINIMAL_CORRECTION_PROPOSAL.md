# Minimal physics correction proposal — approval required

Source: local `main`, `a77f7455f5fe57dad6bae5d948477b2390433bb0`.
**Proposed only. Production kernels have not been changed.**
See [all 15 regression failures, including exact messages](PHYSICS_REGRESSION_FAILURE_REVIEW.md)
and [the original audit](PHYSICS_MATRIX_IMPLEMENTATION_AUDIT.md).

## Regression disposition

None of the 15 baseline assertions fails in either disputed physics operation.
Nine are full-process RSS/test-isolation failures (the original 12-case input
test passes in a fresh process). One is a genuine byte-provenance mismatch
despite exactly equal numerical source arrays. Five are stale assertions after
the approved 2 nm default/editable-widget change. The six non-resource failures
reproduced independently: 6 failed in 72.35 s. All inspected production and
existing-test hashes still match the pre-audit snapshot. Nothing was suppressed
or given a weaker tolerance. The complete baseline remains 558 passed,
15 failed, 2 skipped; isolated passes do not make it an all-green run.

## 1. Forward-Born derivation with fixed documented conventions

Use fast-electron waves `exp(+i k.r)`, an incoming **ket** and an outgoing
**bra**, `Q=k_out-k_in`, and `d_na=<i|r_a|f_n>`. Write the localized target
coordinate as `R_u+x`. Translating the Coulomb interaction in the fast-electron
matrix element gives

```
integral dr exp(-i k_out.r) V(r-R_u-x) exp(+i k_in.r)
    = V_tilde(Q) exp(-i Q.R_u) exp(-i Q.x),
<f_n|exp(-i Q.x)|i> = -i sum_a Q_a d_na* + O(Q²).
```

The common `-i` and omitted common Coulomb prefactor cancel in squared
amplitudes, not the conjugation of d. With `A_gh=a_g [U_out(t-z)]_0h`,
`K_gh,a=Q_gh,a/Q_gh²`, and `p_gh(u)=exp(-i Q_gh.R_u)`, define

```
v_a(z,u) = sum_gh A_gh(z) K_gh,a p_gh(u),
amplitude_n = sum_a v_a d_na*,
T_ab(E) = sum_n w_n d_na d_nb* G(E-E_n),
R_ab = average_u integral dz v_a v_b*,
I(E) = sum_n w_n average_u integral dz |sum_a v_a d_na*|² G
     = Re sum_ab R_ab T_ba = Re Tr(R T).
```

Production currently uses `Re sum_ab R_ab T_ab`. A global reversal of Q
changes a common dipole sign and cannot replace the missing conjugation.
Changing the definition of imported d would be a different schema/provider
proposal, not a minimal correction under the user's fixed convention.

The proper-MDFF API can remain
`S(Q,Q')=Q_a T_ab Q'_b`. The forward path product above multiplies
`S(Q',Q)`, with ordered fast coefficients held fixed. One can equivalently
swap both path indices and conjugate the coefficient product; swapping only
the MDFF or only one elastic field is not equivalent. This is why symbolic
resemblance to a published S definition is insufficient. The inspected
[Rusz author manuscript](https://arxiv.org/pdf/0704.1407), Eqs. (3–5),
(17–18), and the explicit target final-state bra in
[Negi et al., Methods, Eqs. (1–2)](https://www.nature.com/articles/s41598-018-22234-8.pdf)
are convention references; the calculation here fixes the bra/ket and
transfer choices explicitly rather than asserting interchangeable index labels.

### Every production contraction affected

| Route / entry | Actual contraction requiring change | Action |
|---|---|---|
| Single BW: `run_tensor_single_channeling` → `run_tensor_with_coherence` | `single_channeling_tensor._tensor_angular_maps.project`, line 57 | Use `ba` in the Cartesian contraction for both real-even and imaginary-odd parts. |
| Single MS: FFT coherence → `run_tensor_with_coherence`; GUI `channeling.contract` Single branch | Same `_tensor_angular_maps` | Same one fix; no second transpose at caller. |
| Double BW: `double_channeling_response` → spectrum/map callers | `double_channeling.intensities_from_response`, line 225 | Response contraction `...ab,ba`. R construction and incoming/outgoing propagation stay unchanged, except the independent site-phase correction below. |
| Double MS: `multislice_double_channeling_response` → shared spectrum caller | Same `intensities_from_response`; GUI `channeling.contract`, line 159 | Shared fix reaches both methods; GUI caller unchanged. |
| Double BW angular wrapper | `_run_tensor_double_channeling`, lines 267–268 | Both separate even/odd map contractions `pab,ba`; spectra alone are insufficient. |
| Double MS angular wrapper | `run_tensor_multislice_double_channeling`, lines 390–391 | Same even/odd map fix. |
| Public Cartesian helper | `double_channeling.contract_cartesian`, line 81 | `...a,ba,...b`, consistent with the shared response API. |
| Explicit forward target-mode route | `multislice_double_channeling.forward_event_amplitudes`, lines 131–132 | Use `transition_modes(T).conj()` as the excitation modes. |

The source-wide search found no additional active tensor/intensity contraction.
`mdff_tensor.dipole_tensor_from_transitions`, `DipoleTensor.mdff`, source RP/LP
columns, eta/beta, tensor rotation, and `R_ab=v_a v_b*` remain unchanged.
Tensor previews and traces are not scattering contractions and must not be
sign-flipped as a substitute.

### Is a transpose sufficient?

**For R-based intensities, yes; for the complete API, no.** Keep the existing
factorization contract `T=L L^dagger`. Forward excitation requires columns
`L*`, since `L* L^T=T^T`, and
`sum_mode |v.L*|² = sum_ab R_ab T_ba`. Conjugate L **once at the forward-event
caller**, not in `transition_modes` globally, and not together with K, a or
the exit bra. The principal MS response solver does not propagate target
modes; its existing `transition_modes(T)` call is PSD validation and needs no
factor change. Retain that PSD check and its roundoff tolerance.

## 2. Atomic-site phase derivation and free-exit reduction

For ZOLZ paths with `Q=2*pi*(q_detector+h-g,q_z)`, discard only the
site-specific phase common to all paths at that independent event:

```
exp(-i Q.R_u)
  = common_detector_and_qz_phase(u) * exp(+2*pi*i*(g-h).u).
```

That common phase cancels within each event's intensity before the incoherent
site average. It is not a license to sum sites coherently or remove relative
Bragg phases. Integer Miller indices are contracted with fractional u;
orientation rotation is already contained in the reciprocal geometry.

In Single, `h=0`; the pair factor is
`exp(+2*pi*i*(g-g').u)`, exactly the current
`single_channeling_tensor.fcc_site_phase_matrix`. **Leave Single site phases
unchanged.** Double's `equivalent_site_phases` currently uses `h-g` and must
use `g-h`. The helper is shared by BW Double and MS Double, so correct it once.
Retain modulo-one grouping, multiplicity weights and incoherent averaging.
No potential-Fourier, Hamiltonian or propagation sign changes are proposed.

### Independent nontrivial-site validation of the proposed formulas

`tests/test_physics_correction_proposal.py` uses two unequal synthetic sites,
complex Hermitian incoming H, independent free outgoing H, complex target
dipoles, a closed Pauli propagator and 128-node Gauss quadrature. It evaluates
prospective formulas locally, without monkeypatching production functions.
The Single calculation receives an explicitly transposed test tensor only
to evaluate the proposed algebra with the unchanged kernel.

| Computation | Integrated intensity (a.u.) |
|---|---:|
| Independent direct forward-Born target sum | 0.9324430655720030 |
| Proposed Single formula | 0.9324430655720032 |
| Proposed free-outgoing Double formula, both corrections | 0.9324430655720031 |
| Double with contraction correction only | 0.6791938126637971 |
| Double with phase correction only | 1.0133887100108265 |
| Unchanged Double formula | 0.9957971830517018 |

Agreement criterion: `rtol=2e-13`, `atol=1e-14`. Four additional tests
separate the two corrections, verify L-conjugation, and test origin covariance
with rephased complex incoming **and** outgoing Hamiltonians, plus forward
event-to-exit intensity against an explicit DFT matrix with a complex kernel.
**5 proposal tests passed**. The combined audit/proposal run recorded
**18 passed, 2 strict XFAILs**; both unchanged-production convention failures
remain unresolved. Evidence: `build/physics-matrix-audit/review/focused.log/.xml`.
These are synthetic kernel controls, not general-material production support
or evidence that the pending production patch already passes.

## 3. Proposed diff — not applied

Only three production files need algorithmic changes. The exact unified diff
is `build/physics-matrix-audit/review/PROPOSED_ONLY_physics_corrections.patch`.
It changes no elastic generator, q_z, MDFF provider, detector integration,
memory admission, worker policy, numerical setting or propagation algorithm.
The full diff is reproduced at the end of this document. Read-only
`git apply --check` passes against the current source; the patch preserves
the existing per-file newline conventions and was **not applied**.

| Independent current failing test | Correction it isolates |
|---|---|
| `test_physics_matrix_audit::test_microscopic_born_dipole_conjugation` | Transposed R–T contraction: 0 must become 4. |
| `test_physics_matrix_audit::test_nontrivial_site_phase_single_double_reduction` | Reverse Double amplitude site phase; pair max error 1.97730349 must vanish. |
| New proposal free-exit/direct-target tests | Both corrections must reach Single/Double coherently, not cancel by accident at trivial FCC sites. |
| New factorization/forward-mode test | `L*` is required for forward amplitudes while `L L^dagger=T` remains the factor API. |

After approval, remove the two strict XFAIL markers only when the actual
production tests pass unmasked. Turn prospective formula tests into direct
production-route checks: stop passing T.T into the corrected Single kernel,
use the corrected site helper, and exercise the real forward-event caller.
Update existing algebra tests that intentionally encode `v.d` to independent
`v.d*` references with unchanged tolerances. In particular audit
`test_double_channeling_foundation.py`,
`test_multislice_double_channeling.py`, and the old-convention direct-sum
audit test. Keep historical computations explicitly labeled; do not change
reference arrays wholesale to match new outputs.

## 4. Expected physical and Ni [017] impact

For the **contraction-only correction** at a fixed response and a tensor model
obeying `T(-M)=T(+M)*`, reversal-even `N=(I+ + I-)/2` stays fixed and
reversal-odd `M=(I+ - I-)/2` changes sign. Both raw states exchange, not their
physical magnetization labels. Therefore `D_mag=M_A-M_B` and `D_flip_A=2*M_A`
change sign, `D_nonmag=N_A-N_B` and `N_A+N_B` stay fixed. Magnetic-only
percentage reverses sign; raw A/B becomes `D_nonmag-D_mag`. Total plus-state
PRB has a different denominator and generally does not merely change sign.

For **nontrivial site phases**, the phase correction changes R itself: both
N and M may change. Do not promise unchanged nonmagnetic intensity for
arbitrary sites. For conventional FCC Ni sites and allowed reflections all
relative site phases are unity, so the phase correction leaves the existing
[017] calculation unchanged up to roundoff; the combined expected change is
then the tensor-transpose sign reversal.

Frozen 300 kV [017] L3/L2 examples, exact Bragg X, Y=0, crystal M along [001],
eta=beta=1, from the completed study (no rerun):

| t (nm) | Edge / native energy (eV) | Existing D_mag (a.u.) | Proposed D_mag | Existing → proposed magnetic-only % |
|---:|---|---:|---:|---|
| 10 | L3 / 831.271 | -0.0115377679051673 | +0.0115377679051673 | -14.109209 → +14.109209 |
| 10 | L2 / 848.698 | +0.0125365233784439 | -0.0125365233784439 | +22.848524 → -22.848524 |
| 30 | L3 / 831.271 | -0.00667320933467483 | +0.00667320933467483 | -2.594191 → +2.594191 |
| 30 | L2 / 848.698 | +0.00724940229147986 | -0.00724940229147986 | +4.200008 → -4.200008 |

Eight rows including Y=+15 mrad, all four raw detector states, N/M,
percentage-point changes and PRB are saved in
`build/physics-matrix-audit/review/ni017_L3_L2_expected_impact.csv`.
These are exact algebraic predictions for a fixed tensor convention and eta,
not new corrected Ni simulations or the separate 200 kV benchmark. Relative
L3/L2 opposition is preserved. Signs depend on geometry and may cross zero;
this is not a universal assertion that L3 is positive everywhere. Absolute
experimental magnetic handedness remains uncalibrated for the effective
XMCD source. Do not compensate by silently changing eta, RP/LP or M axes.

## 5. Acceptance gates after explicit approval

1. All four actual routes (Single/Double × BW/MS) match independently constructed
   forward-target sums on small complex models. The two original failures pass
   unmasked at `atol=1e-14`; proposed free-exit controls retain
   `rtol=2e-13`, `atol=1e-14`. No expected-failure waiver for corrected kernels.
2. Factorized forward propagation, dense tensor contraction and independent
   target-mode sums agree for complex K and d, arbitrary per-transition phase,
   non-real elastic couplings, independent beam bases and nontrivial sites.
   Site origin covariance and free-outgoing Double→Single reduction pass.
3. Map totals equal separate N+M maps for both reversal states, and aperture
   spectra equal integrated raw maps before percentages. Positive total
   intensities, Hermitian PSD T/R, reversal identities and valid physical
   mirror controls pass at their existing tolerances. No mirrored display
   construction is used as physical proof.
4. Reuse bounded saved Ni references. For FCC sites, even spectra/maps agree
   with baseline, odd ones agree with its negative, and plus/minus states
   exchange at existing comparison tolerances. Explicitly compare signed raw
   values, N/M, raw A/B, magnetic-only % and PRB pp. Preserve all original
   arrays and provenance; mark the new contraction convention in future
   metadata/documents so projects are not silently reinterpreted.
5. Existing BW/MS, depth/slice/grid/basis checks retain thresholds; no
   certification at untested thicknesses. Existing [111] and detector-grid
   convergence failures remain disclosed. Agreement of corrected solvers
   cannot validate the physical Ni MDFF.
6. Run the complete practical suite in a clean process after reviewed test
   maintenance. Resolve the 15 baseline test/provenance/isolation issues with
   explicit evidence, not suppression, higher memory budgets or looser
   tolerances. Compare legacy configurations using matched explicit inputs;
   preserve legitimate over-budget rejection. Full regression acceptance
   requires zero unexplained failures; the six inherited failures are not
   automatically waived by this physics proposal. Optional companion-data
   skips must remain named and distinguished from passes.
7. Recheck all 323 protected files / 204 production checkpoints, the 19
   pre-existing user files, version and unrelated edits. No changed physical
   defaults, source spectrum, data regeneration, release or packaging in the
   correction. Review the diff and observed changes before any integration.

**Approval requested only for the proposed coordinated correction.** No
production patch has been applied; none of the inherited regression failures
has been hidden or repaired by changing science or numerical thresholds.

## Exact proposed production diff (not applied)

```diff
--- a/src/emcd_sim/single_channeling_tensor.py
+++ b/src/emcd_sim/single_channeling_tensor.py
@@ -54,7 +54,8 @@
     weighted_coherence = coherence * site_phase
 
     def project(part: np.ndarray) -> np.ndarray:
-        mdff = np.einsum("...ia,ab,...jb->...ij", angular_q, part, angular_q, optimize=True)
+        # Forward excitation uses d*=<f|r|i>, hence S(Q_j,Q_i).
+        mdff = np.einsum("...ia,ba,...jb->...ij", angular_q, part, angular_q, optimize=True)
         return np.real(np.einsum("ij,...ij->...", weighted_coherence,
                                   mdff / denominator, optimize=True))
 
--- a/src/emcd_sim/double_channeling.py
+++ b/src/emcd_sim/double_channeling.py
@@ -77,8 +77,8 @@
 
 
 def contract_cartesian(vectors, tensor):
-    """v T v*, matching existing d=<core|r|final>, T=d d* convention."""
-    return np.einsum('...a,ab,...b->...', vectors, tensor, vectors.conj()).real
+    """v T^T v*, for forward excitation with d=<core|r|final>."""
+    return np.einsum('...a,ba,...b->...', vectors, tensor, vectors.conj()).real
 
 
 def depth_response(incoming, outgoing, kernel, thickness_nm, *, method='analytic', depth_steps=257, cancelled=None):
@@ -152,7 +152,8 @@
     This removes repeated evaluations for equivalent FCC sites without dropping
     independent events or changing their incoherent per-atom normalization.
     """
-    delta=np.asarray(outgoing_hkl)[None,:,:]-np.asarray(incoming_hkl)[:,None,:]
+    # exp(-i Q.R), dropping only the common detector/longitudinal phase.
+    delta=np.asarray(incoming_hkl)[:,None,:]-np.asarray(outgoing_hkl)[None,:,:]
     cycles=np.remainder(np.einsum('ghc,sc->sgh',delta,np.asarray(positions)),1.)
     if not len(cycles):raise ValueError('At least one core site required')
     unique,counts=np.unique(cycles,axis=0,return_counts=True)
@@ -222,7 +223,7 @@
         raise ValueError('Finite Hermitian dipole tensor required')
     if np.linalg.eigvalsh(t).min() < -1e-12*max(np.linalg.norm(t), 1e-30):
         raise ValueError('Dipole tensor must be positive semidefinite')
-    return np.einsum('...ab,ab->...', response, t).real
+    return np.einsum('...ab,ba->...', response, t).real
 
 
 
@@ -264,8 +265,8 @@
             spectra[k][ie]=(total[masks[k]].sum() if integration_mode=='binary'
                             else (total*weights[k]).sum())*(q[1]-q[0])**2
         if ie==selected:
-            even=np.einsum('pab,ab->p',response,t.real).real.reshape(qx.shape)
-            odd=np.einsum('pab,ab->p',response,1j*t.imag).real.reshape(qx.shape)
+            even=np.einsum('pab,ba->p',response,t.real).real.reshape(qx.shape)
+            odd=np.einsum('pab,ba->p',response,1j*t.imag).real.reshape(qx.shape)
     return SimulationResult(tensor.energy_ev,qx,qy,even,odd,spectra,masks,None,
         thickness_nm,0.,model.chiral_groups,weights,integration_mode,aperture_subpixels)
 
--- a/src/emcd_sim/multislice_double_channeling.py
+++ b/src/emcd_sim/multislice_double_channeling.py
@@ -128,7 +128,8 @@
     kernel[g,h,a] includes Coulomb factor and a single site's phase. Return
     complex exit amplitudes per independent target mode (never summed coherently).
     """
-    modes=transition_modes(tensor)
+    # T=L L^dagger is unchanged; excitation amplitudes use L*.
+    modes=transition_modes(tensor).conj()
     scattered=np.einsum('g,gha,af->fh',incoming,kernel,modes,optimize=True)
     full=np.zeros((3,outgoing_plan.size),complex)
     full[:,outgoing_indices]=scattered
@@ -387,7 +388,7 @@
                 spectra[k][i]=(total[masks[k]].sum() if integration_mode=='binary' else
                     (total*weights[k]).sum())*(q[1]-q[0])**2
             if i==selected:
-                even=np.einsum('pab,ab->p',response,t.real).real.reshape(qx.shape)
-                odd=np.einsum('pab,ab->p',response,1j*t.imag).real.reshape(qx.shape)
+                even=np.einsum('pab,ba->p',response,t.real).real.reshape(qx.shape)
+                odd=np.einsum('pab,ba->p',response,1j*t.imag).real.reshape(qx.shape)
         return SimulationResult(tensor.energy_ev,qx,qy,even,odd,spectra,masks,None,thickness_nm,
             0.,model.chiral_groups,weights,integration_mode,aperture_subpixels)
```
