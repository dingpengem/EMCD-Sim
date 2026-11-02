# Physics correction main reconciliation: final acceptance

**GO for the validated, uncommitted reconciliation candidate and a later approved
clean-worktree integration. Actual main remains unchanged and dirty.** No commit,
actual-main merge, push, tag, release, version change, Windows build or Stage4.2
research simulation was performed. Existing bounded regression controls ran.

## 1. State and exact repair

Candidate branch: `reconciliation/forward-born-user-work`, worktree
`C:/Users/peng863/EMCD-Sim/build/physics-correction-main-reconciliation`.
HEAD remains preview merge `dabf61886e4432afa8e5692097b9d8903879b1fe`; correction ancestor remains
`5347f4473dc6057dadb97e102aa26aca7ba7214e`. Actual main remains
`a77f7455f5fe57dad6bae5d948477b2390433bb0` in the original dirty worktree. No new commit exists here.
Cached `origin/main` has not been refreshed during this repair; fetch and
inspect remote divergence before any later integration.

The repair copies verified CRLF bytes into **only this candidate's package
input**, from both trusted correction/preview worktrees. Their raw hashes
matched the already committed package manifest before use. No input was
invented or reconstructed and no numerical value changed. Neither registered
input hash, the provenance manifest, `.gitattributes`, source guard nor any
physics kernel was edited.

## 2. Provenance root cause: blob storage versus representation

Two distinct registered inputs must not be conflated:

| Contract | Immutable raw SHA256 |
|---|---|
| Original full-benchmark historical fixture | `a0e28ea6423b6c7832bb3cce6d69d71aa59336a221baeee3d2556b49ba501283` |
| Separately registered canonical package input | `bb9bdd478d54cc8de60403409f4d90e63deb11a64891bbac6754f867be14deda` |

The failure concerned the **package copy**, not corruption of the original
historical fixture. The old package Git blob contained LF, while the previously
validated worktrees retained CRLF. Git does not rewrite an existing worktree
file merely because an attributes rule is added. The new `-text` rule prevented
conversion but could not fix a blob already stored as LF. A fresh checkout
therefore materialized the LF blob and failed the manifest's CRLF identity.

Observed configuration: system `core.autocrlf=true` from Git's system config;
`core.safecrlf` unset. `git check-attr` reports `text: unset` for both byte-identified
inputs. The existing `-text` rules are unchanged. No Git configuration was changed.

| Package stage | Git blob OID | Raw SHA256 |
|---|---|---|
| Existing HEAD/index blob, still unmodified in real index | `ef70d1767f12ae0d228692989697ca8920bd0573` | `4fd517af3e54db94588a76b7a6ed9c2f9a1b745cd8fe52b9fca0f87fc4938db3` |
| Pre-repair fresh worktree (LF) | same bytes as old blob | `4fd517af3e54db94588a76b7a6ed9c2f9a1b745cd8fe52b9fca0f87fc4938db3` |
| Repaired candidate / disposable index blob (CRLF) | `da46623569735ae9f18396d9f00e843f23d37404` | `bb9bdd478d54cc8de60403409f4d90e63deb11a64891bbac6754f867be14deda` |

The historical fixture's unchanged Git OID is
`1289239f8309d8b44b54d0108bc61eddd9987f30`, with its original historical SHA256.
The candidate blob OID is confirmed by actual disposable Git indexes and fresh
`checkout-index` output, not only by computing a prospective hash. The real
repository index and HEAD still contain the old blob because staging/committing
is prohibited. A later selective commit must record the repaired blob above.
The line-ending repair appears as 4329 removed/added lines in a normal text diff;
this is intentional exact-byte preservation, not a spectral modification.

`tests/test_input_checkout_provenance.py` adds two regression cases. Each uses
a disposable repository, stages the real candidate input and original fixture
under the real attributes, reads the index blob, and checks out into a new
empty directory. Both `core.autocrlf=true` and `false` pass with `safecrlf=true`.
Both stored/checked-out SHA256 values match the immutable manifest exactly.
Only the temporary non-provenance attributes copy gets CRLF to satisfy safecrlf;
the input bytes are copied unchanged. No temporary or real commits are made.

Numeric arrays also compare exactly and the old/new package text differs only
in CRLF/LF. That is supplementary evidence of unchanged values; raw-byte
SHA256 remains the provenance contract. Logs and four actual index/checkout
samples are retained in `provenance_repair.json` and `checkout_samples.json`.

## 3. Two audit-test reconciliations

These are updated convention diagnostics and stale pre-correction expectations,
not competing physical requirements. Every test/helper function name survives;
there are no complementary omitted cases requiring a combined active file.
Both validated files are retained **byte-for-byte unchanged** from the preview.
The originals remain untouched in the original worktree and preserved snapshots.

The two independent Born/site-phase reproduction bodies are AST-identical to
their historical versions. Their old strict XFAIL decorators stay removed in
the active validated files. Old same-index / unconjugated-mode / opposite-phase
diagnostics are replaced by physically corrected expectations, while explicit
wrong-convention disagreement controls are retained. No assertion is removed
to obtain green status and no tolerance is increased. The site-phase check now
asserts corrected equality at atol=1e-14 instead of asserting the old discrepancy
exceeds 0.1; this is a change of expected behavior, not a relaxed tolerance.

### `tests/test_physics_matrix_audit.py`

Decision: Retain validated tests unchanged. Historical diagnostics of uncorrected behavior are stale under the approved correction, not complementary physical requirements. All function/test cases retained; original versions preserved verbatim outside active discovery.

Existing tolerance keywords retained. Audit adds atol=1e-14 for corrected site-phase equality, replacing the stale assertion that old discrepancy exceeds 0.1.

<details>
<summary>Original user audit versus validated active test (already present before this repair)</summary>

```diff
--- original/test_physics_matrix_audit.py
+++ validated/test_physics_matrix_audit.py
@@ -1,296 +1,294 @@
-"""Independent audit controls; expected failures identify UNCORRECTED physics.
-
-No reference arrays are regenerated. Closed Pauli exponentials and explicit
-DFT matrices are references, not wrappers around another production solver.
-Run with --runxfail to expose the two blocking convention reproductions.
-"""
-from types import SimpleNamespace
-
-import numpy as np
-import pytest
-from numpy.testing import assert_allclose
-
-from emcd_sim.double_channeling import (
-    BlochStates, depth_response, dipole_kernel, intensities_from_response,
-    equivalent_site_phases,
-)
-from emcd_sim.mdff_tensor import (
-    TransitionDataset, dipole_tensor_from_transitions, DipoleTensor,
-)
-from emcd_sim.multislice_double_channeling import FFTSplitStep
-from emcd_sim.single_channeling_tensor import fcc_site_phase_matrix
-
-
-def exp2(h, z):
-    """Independent exact exponential of a complex Hermitian 2x2 matrix."""
-    center = np.trace(h).real / 2
-    a = h - center * np.eye(2)
-    omega = np.sqrt(np.trace(a @ a).real / 2)
-    return np.exp(1j * center * z) * (
-        np.cos(omega * z) * np.eye(2) + 1j * z * np.sinc(omega * z / np.pi) * a
-    )
-
-
-def matrices():
-    return (np.array([[.013, .11 + .04j], [.11 - .04j, -.021]]),
-            np.array([[-.017, .083 - .03j], [.083 + .03j, .032]]))
-
-
-def model_data():
-    hi, ho = matrices()
-    q = np.array([[[.21, .3, -.1], [.77, .3, -.1]],
-                  [[-.35, .3, -.1], [.21, .3, -.1]]])
-    # Independent rad/Angstrom kernel, not dipole_kernel as reference.
-    angular = 2 * np.pi * q
-    k = angular / np.sum(angular**2, axis=-1)[..., None]
-    d = np.array([[1, .3j, .2], [.4 - .2j, .6, .1j]])
-    weights = np.array([.7, 1.3])
-    tensor = sum(w * np.outer(v, v.conj()) for w, v in zip(weights, d))
-    return hi, ho, k, d, weights, tensor
-
-
-def reference_response(hi, ho, k, thickness, order=96):
-    """Independent numerical depth quadrature of coherent event amplitudes."""
-    x, w = np.polynomial.legendre.leggauss(order)
-    result = np.zeros((3, 3), complex)
-    for z, weight in zip((x + 1) * thickness / 2, w * thickness / 2):
-        a = exp2(hi, z)[:, 0]
-        bra = exp2(ho, thickness - z)[0, :]
-        v = sum(a[g] * bra[h] * k[g, h] for g in range(2) for h in range(2))
-        result += weight * np.outer(v, v.conj())
-    return result
-
-
-@pytest.mark.parametrize('thickness', [0., 1e-7, .3, 17.])
-def test_independent_analytic_depth_response(thickness):
-    """Solver implementation: complex eigenvectors, thin/zero and finite depth."""
-    hi, ho, k, _, _, _ = model_data()
-    expected = reference_response(hi, ho, k, thickness)
-    actual = depth_response(BlochStates.solve(hi), BlochStates.solve(ho), k, thickness)
-    assert_allclose(actual, expected, rtol=2e-12, atol=2e-15)
-
-
-def test_direct_transition_sum_same_index_algebra_and_phase():
-    """Algebra only: production's V=sum K*d, NOT microscopic Born validation."""
-    hi, ho, k, d, weights, tensor = model_data()
-    x, w = np.polynomial.legendre.leggauss(96)
-    direct = 0.
-    for z, weight in zip((x + 1) * 8.5, w * 8.5):
-        a = exp2(hi, z)[:, 0]
-        bra = exp2(ho, 17 - z)[0]
-        for dn, wn in zip(d, weights):
-            transition = np.array([[sum(k[g, h, j] * dn[j] for j in range(3))
-                                    for g in range(2)] for h in range(2)])
-            direct += weight * wn * abs(bra @ transition @ a)**2
-    r = depth_response(BlochStates.solve(hi), BlochStates.solve(ho), k, 17.)
-    assert_allclose(intensities_from_response(r, tensor), direct, rtol=2e-13)
-    assert direct > 0
-    phased = d * np.exp(1j * np.array([.4, -.7]))[:, None]
-    assert_allclose(sum(w * np.outer(v, v.conj()) for w, v in zip(weights, phased)), tensor)
-    # A matrix trace contracts transposed indices and is generally different.
-    assert abs(np.trace(r @ tensor).real - direct) > 1e-4
-
-
-@pytest.mark.xfail(strict=True, reason='BORN_CONJUGATION: d=<i|r|f> requires conjugate(d) in forward target excitation; approval required')
-def test_microscopic_born_dipole_conjugation():
-    """Physics: forward Born amplitude uses <f|exp(-i Q.r)|i>.
-
-    For Q=k_out-k_in, its dipole term is -i Q.d*, independent of
-    the common -i phase. A one-event complex example distinguishes signs.
-    """
-    d = np.array([1., 1j, 0.])
-    transfers = np.array([[1., 0., 0.], [0., 1., 0.]])
-    path_amplitudes = np.array([1., 1j])
-    reference = abs(sum(c * np.dot(q, d.conj())
-                        for c, q in zip(path_amplitudes, transfers)))**2
-    v = path_amplitudes @ transfers
-    actual = intensities_from_response(np.outer(v, v.conj()), np.outer(d, d.conj()))
-    assert_allclose(actual, reference, rtol=0, atol=1e-14)
-
-
-def synthetic_site():
-    hkl = ((0, 0, 0), (2, 0, 0))
-    positions = np.array([[.137, .081, .019]])
-    crystal = SimpleNamespace(fractional_positions=positions, species=('Ni',))
-    model = SimpleNamespace(elastic=SimpleNamespace(crystal=crystal, beams=SimpleNamespace(hkl=hkl)))
-    return model, hkl, positions
-
-
-@pytest.mark.xfail(strict=True, reason='SITE_PHASE: free-outgoing DC phase is conjugate of SC phase for nontrivial sites; approval required')
-def test_nontrivial_site_phase_single_double_reduction():
-    """Physics/conventions: synthetic kernel-level control, no material claim."""
-    model, hkl, positions = synthetic_site()
-    sc = fcc_site_phase_matrix(model)
-    phases, weights = equivalent_site_phases(hkl, ((0, 0, 0),), positions)
-    dc = sum(w * np.outer(p[:, 0], p[:, 0].conj()) for p, w in zip(phases, weights))
-    assert_allclose(sc, dc, rtol=0, atol=1e-14)
-
-
-def test_site_phase_discrepancy_is_not_a_global_phase():
-    """Diagnostic algebra: quantify preserved discrepancy without endorsing it."""
-    model, hkl, positions = synthetic_site()
-    sc = fcc_site_phase_matrix(model)
-    phases, _ = equivalent_site_phases(hkl, ((0, 0, 0),), positions)
-    dc = np.outer(phases[0, :, 0], phases[0, :, 0].conj())
-    assert_allclose(sc, dc.conj(), atol=1e-14)
-    a = np.array([1., .5j])
-    k = np.array([[1., .2, .1], [.3, 1., .2]])
-    t = np.eye(3)
-    expected = sum(a[i] * a[j].conjugate() * sc[i, j] * (k[i] @ t @ k[j])
-                   for i in range(2) for j in range(2)).real
-    v = sum(a[i] * phases[0, i, 0] * k[i] for i in range(2))
-    actual = (v @ t @ v.conj()).real
-    assert abs(expected - actual) > .1
-
-
-def test_transition_gram_mdff_units_positivity():
-    """Algebra/units: independent Gaussian Gram sum and proper MDFF."""
-    _, _, _, d, w, _ = model_data()
-    dataset = TransitionDataset(np.array([800., 802.]), d, w,
-        np.array(['L3', 'L3']), np.array(['Ni1', 'Ni1']), 'synthetic audit')
-    energy = np.array([799., 801., 803.]); sigma = .7
-    result = dipole_tensor_from_transitions(dataset, energy, sigma)
-    expected = np.array([sum(wn * np.outer(dn, dn.conj()) *
-        np.exp(-.5 * ((e - en) / sigma)**2) / (sigma * np.sqrt(2 * np.pi))
-        for en, dn, wn in zip(dataset.energy_ev, d, w)) for e in energy])
-    assert_allclose(result.tensor_angstrom2_per_ev, expected, atol=1e-15)
-    assert np.linalg.eigvalsh(expected).min() > -1e-14
-    q = np.array([[.2, .3, -.1], [-.4, .2, -.1]])
-    s = result.mdff(q[:, None], q[None, :])
-    assert_allclose(s, s.swapaxes(1, 2).conj(), atol=1e-15)
-    assert np.diagonal(s, axis1=1, axis2=2).real.min() >= 0
-    assert_allclose(result.mdff(2*q[:, None], 2*q[None, :]), 4*s)
-    assert_allclose(dipole_kernel(q), q / (2*np.pi*np.sum(q*q, axis=1)[:, None]))
-    assert_allclose(dipole_kernel(2*q), dipole_kernel(q)/2)
-
-
-def test_exit_bra_independent_bases_and_boundary_indices():
-    """Solver: rectangular transition kernel; no incoming/outgoing basis reuse."""
-    hi, ho = matrices(); ho = np.diag([.021, -.013, .04]).astype(complex)
-    incoming, outgoing = BlochStates.solve(hi, 1), BlochStates.solve(ho, 2)
-    z = 1.7
-    assert_allclose(incoming.ket(z), exp2(hi, z)[:, 1], atol=1e-15)
-    assert_allclose(outgoing.ket(-z).conj(), [0, 0, np.exp(.04j*z)], atol=1e-15)
-    rng = np.random.default_rng(581)
-    k = rng.normal(size=(2, 3, 3)) + 1j*rng.normal(size=(2, 3, 3))
-    x, w = np.polynomial.legendre.leggauss(64); ref = np.zeros((3, 3), complex)
-    for zi, wi in zip((x+1)*2, w*2):
-        a = exp2(hi, zi)[:, 1]
-        bra = np.array([0, 0, np.exp(.04j*(4-zi))])
-        v = sum(a[g]*bra[h]*k[g, h] for g in range(2) for h in range(3))
-        ref += wi*np.outer(v, v.conj())
-    assert_allclose(depth_response(incoming, outgoing, k, 4.), ref, atol=3e-14)
-    so = BlochStates.solve(matrices()[1])
-    assert_allclose(so.ket(-z).conj(), exp2(matrices()[1], z)[0], atol=1e-15)
-
-
-def test_degenerate_modes_and_unsupported_complex_eigenvalues():
-    """Solver domain: complex eigenvectors allowed; absorption not implemented."""
-    hi = np.eye(2)*.03 + np.array([[0, 1e-14j], [-1e-14j, 0]])
-    ho = np.eye(2)*-.07
-    k = model_data()[2]
-    assert_allclose(depth_response(BlochStates.solve(hi), BlochStates.solve(ho), k, 4.),
-                    reference_response(hi, ho, k, 4.), atol=2e-15)
-    with pytest.raises(ValueError, match='Hermitian'):
-        BlochStates.solve(np.diag([.1+.01j, .2]))
-
-
-def test_reversal_detector_algebra_integrate_before_percentage():
-    """Algebra: no mirror symmetry presumed for arbitrary geometries."""
-    from emcd_sim.geometry import VirtualDetector
-    q = np.linspace(-1, 1, 17); x, y = np.meshgrid(q, q)
-    na, ma = 2 + x*x + .2*y, .1 + .03*x - .02*y
-    plus, minus = na + ma, na - ma
-    odd, even = (plus-minus)/2, (plus+minus)/2
-    t = model_data()[-1]; r = np.outer([1, 1j, .2], np.conj([1, 1j, .2]))
-    assert_allclose(intensities_from_response(r, t)+intensities_from_response(r, t.conj()),
-                    2*intensities_from_response(r, t.real))
-    values=[]; aperture_weights=[]
-    for center in ((.25, .3), (.25, -.3)):
-        w = VirtualDetector(center, .2).integration_weights(x, y, mode='fractional', subpixels=32)
-        aperture_weights.append(w)
-        assert np.min(w) >= 0 and np.max(w) <= 1
-        integrate = lambda a: float(np.sum(w*a)*(q[1]-q[0])**2)
-        values.append((integrate(even), integrate(odd), integrate(plus), integrate(minus)))
-    assert_allclose(aperture_weights[0], aperture_weights[1][::-1], atol=0, rtol=0)
-    (a, m, ap, am), (b, n, bp, bm) = values
-    assert_allclose((ap-am)/2, m)
-    assert_allclose(ap-bp, (m-n)+(a-b))
-    assert_allclose(100*(ap-bp)/(a+b), 100*(m-n)/(a+b)+100*(a-b)/(a+b))
-    assert a > 0 and b > 0
-    from emcd_sim.gui.component_display import reversal_signals
-    actual, _ = reversal_signals(np.array([ap]), np.array([bp]), np.array([am]), np.array([bm]))
-    assert_allclose(actual['D_mag'], [m-n])
-    assert_allclose(actual['D_nonmag'], [a-b])
-    assert_allclose(actual['D_raw'], [ap-bp])
-    assert_allclose(actual['magnetic_only_percent'], [100*(m-n)/(a+b)])
-    assert_allclose(actual['nonmagnetic_asymmetry_percent'], [100*(a-b)/(a+b)])
-    assert_allclose(actual['emcd_asymmetry_percent'], [100*(ap-bp)/(ap+bp)])
-
-
-def test_fft_against_independent_dense_exponential_step_convergence():
-    """Convergence/solver: explicit DFT and Hermitian 2x2 continuum generator."""
-    u = np.array([.31, -.13]); kinetic = np.array([-.07, .12])
-    f = np.array([[1, 1], [1, -1]])/np.sqrt(2)
-    h = np.diag(kinetic) + f @ np.diag(u) @ f.T
-    initial = np.array([1., 0.], complex); thickness = 3.
-    expected = exp2(h, thickness) @ initial
-    errors=[]
-    plan=FFTSplitStep(u, kinetic)
-    for n in (12, 24, 48):
-        actual=plan.advance(initial, n, thickness/n)
-        errors.append(np.linalg.norm(actual-expected))
-        assert_allclose(plan.advance(actual, n, -thickness/n), initial, atol=2e-14)
-    assert errors[1] < errors[0]/3.9 and errors[2] < errors[1]/3.9
-
-
-def test_depth_quadrature_converges_independently_of_fft():
-    """Convergence: refine depth only, separate from propagation splitting."""
-    hi, ho, k, *_ = model_data()
-    si, so = BlochStates.solve(hi), BlochStates.solve(ho)
-    ref = reference_response(hi, ho, k, 17.)
-    errors = [np.linalg.norm(depth_response(si, so, k, 17., method='numerical', depth_steps=n)-ref)
-              for n in (33, 65, 129)]
-    assert errors[1] < errors[0]/3.9 and errors[2] < errors[1]/3.9
-
-
-def test_small_fft_double_event_intensity_independent_reference():
-    """Solver/convergence: independent DFT Hamiltonians and forward events.
-
-    Fix depth for split-step refinement; then fix the propagation subdivision
-    while refining depth. No shared production tensor-contraction reference.
-    """
-    f = np.array([[1, 1], [1, -1]])/np.sqrt(2)
-    ui, di = np.array([.31, -.13]), np.array([-.07, .12])
-    uo, do = np.array([-.17, .26]), np.array([.08, -.11])
-    hi, ho = np.diag(di)+f@np.diag(ui)@f.T, np.diag(do)+f@np.diag(uo)@f.T
-    _, _, k, d, weights, tensor = model_data()
-    ref = np.sum(reference_response(hi, ho, k, 3.)*tensor).real
-    def run(depth, subdivisions):
-        z = np.linspace(0, 3., depth); dz = z[1]-z[0]
-        pi, po = FFTSplitStep(ui, di), FFTSplitStep(uo, do)
-        values = []
-        for j in range(depth):
-            incoming = pi.advance(np.array([1, 0], complex), j*subdivisions, dz/subdivisions)
-            signal = 0.
-            for dn, wn in zip(d, weights):
-                scattered = np.array([sum(incoming[g]*np.dot(k[g, h], dn) for g in range(2))
-                                      for h in range(2)])
-                exit_wave = po.advance(scattered, (depth-1-j)*subdivisions, dz/subdivisions)
-                signal += wn*abs(exit_wave[0])**2
-            values.append(signal)
-        return dz*(sum(values[1:-1])+(values[0]+values[-1])/2)
-    # Depth quadrature is independent of the split-step approximation.
-    depth_errors=[abs(run(n, 2)-ref) for n in (17, 33, 65)]
-    assert depth_errors[1] < depth_errors[0]/3.8
-    assert depth_errors[2] < depth_errors[1]/3.8
-    assert abs(run(65, 2)-ref)/ref < 1e-4
-    # At fixed depth compare with the exact propagator, same trapezoidal rule.
-    z = np.linspace(0, 3., 17); exact=[]
-    for zi in z:
-        a = exp2(hi, zi)[:, 0]; bra = exp2(ho, 3.-zi)[0]
-        v = sum(a[g]*bra[h]*k[g, h] for g in range(2) for h in range(2))
-        exact.append(sum(wn*abs(np.dot(v, dn))**2 for dn, wn in zip(d, weights)))
-    trap=(z[1]-z[0])*(sum(exact[1:-1])+(exact[0]+exact[-1])/2)
-    errors=[abs(run(17, n)-trap) for n in (1, 2, 4)]
-    assert errors[1] < errors[0]/3.9 and errors[2] < errors[1]/3.9
+"""Independent audit controls for the approved forward-Born correction.
+
+No reference arrays are regenerated. Closed Pauli exponentials and explicit
+DFT matrices are references, not wrappers around another production solver.
+The two original reproduction bodies are preserved; neither has XFAIL.
+"""
+from types import SimpleNamespace
+
+import numpy as np
+import pytest
+from numpy.testing import assert_allclose
+
+from emcd_sim.double_channeling import (
+    BlochStates, depth_response, dipole_kernel, intensities_from_response,
+    equivalent_site_phases,
+)
+from emcd_sim.mdff_tensor import (
+    TransitionDataset, dipole_tensor_from_transitions, DipoleTensor,
+)
+from emcd_sim.multislice_double_channeling import FFTSplitStep
+from emcd_sim.single_channeling_tensor import fcc_site_phase_matrix
+
+
+def exp2(h, z):
+    """Independent exact exponential of a complex Hermitian 2x2 matrix."""
+    center = np.trace(h).real / 2
+    a = h - center * np.eye(2)
+    omega = np.sqrt(np.trace(a @ a).real / 2)
+    return np.exp(1j * center * z) * (
+        np.cos(omega * z) * np.eye(2) + 1j * z * np.sinc(omega * z / np.pi) * a
+    )
+
+
+def matrices():
+    return (np.array([[.013, .11 + .04j], [.11 - .04j, -.021]]),
+            np.array([[-.017, .083 - .03j], [.083 + .03j, .032]]))
+
+
+def model_data():
+    hi, ho = matrices()
+    q = np.array([[[.21, .3, -.1], [.77, .3, -.1]],
+                  [[-.35, .3, -.1], [.21, .3, -.1]]])
+    # Independent rad/Angstrom kernel, not dipole_kernel as reference.
+    angular = 2 * np.pi * q
+    k = angular / np.sum(angular**2, axis=-1)[..., None]
+    d = np.array([[1, .3j, .2], [.4 - .2j, .6, .1j]])
+    weights = np.array([.7, 1.3])
+    tensor = sum(w * np.outer(v, v.conj()) for w, v in zip(weights, d))
+    return hi, ho, k, d, weights, tensor
+
+
+def reference_response(hi, ho, k, thickness, order=96):
+    """Independent numerical depth quadrature of coherent event amplitudes."""
+    x, w = np.polynomial.legendre.leggauss(order)
+    result = np.zeros((3, 3), complex)
+    for z, weight in zip((x + 1) * thickness / 2, w * thickness / 2):
+        a = exp2(hi, z)[:, 0]
+        bra = exp2(ho, thickness - z)[0, :]
+        v = sum(a[g] * bra[h] * k[g, h] for g in range(2) for h in range(2))
+        result += weight * np.outer(v, v.conj())
+    return result
+
+
+@pytest.mark.parametrize('thickness', [0., 1e-7, .3, 17.])
+def test_independent_analytic_depth_response(thickness):
+    """Solver implementation: complex eigenvectors, thin/zero and finite depth."""
+    hi, ho, k, _, _, _ = model_data()
+    expected = reference_response(hi, ho, k, thickness)
+    actual = depth_response(BlochStates.solve(hi), BlochStates.solve(ho), k, thickness)
+    assert_allclose(actual, expected, rtol=2e-12, atol=2e-15)
+
+
+def test_direct_transition_sum_same_index_algebra_and_phase():
+    """Forward Born algebra: excitation V=sum K*d*."""
+    hi, ho, k, d, weights, tensor = model_data()
+    x, w = np.polynomial.legendre.leggauss(96)
+    direct = 0.
+    for z, weight in zip((x + 1) * 8.5, w * 8.5):
+        a = exp2(hi, z)[:, 0]
+        bra = exp2(ho, 17 - z)[0]
+        for dn, wn in zip(d, weights):
+            transition = np.array([[sum(k[g, h, j] * dn[j].conjugate() for j in range(3))
+                                    for g in range(2)] for h in range(2)])
+            direct += weight * wn * abs(bra @ transition @ a)**2
+    r = depth_response(BlochStates.solve(hi), BlochStates.solve(ho), k, 17.)
+    assert_allclose(intensities_from_response(r, tensor), direct, rtol=2e-13)
+    assert direct > 0
+    phased = d * np.exp(1j * np.array([.4, -.7]))[:, None]
+    assert_allclose(sum(w * np.outer(v, v.conj()) for w, v in zip(weights, phased)), tensor)
+    # The historical same-index contraction is generally different.
+    assert abs(np.sum(r * tensor).real - direct) > 1e-4
+
+
+def test_microscopic_born_dipole_conjugation():
+    """Physics: forward Born amplitude uses <f|exp(-i Q.r)|i>.
+
+    For Q=k_out-k_in, its dipole term is -i Q.d*, independent of
+    the common -i phase. A one-event complex example distinguishes signs.
+    """
+    d = np.array([1., 1j, 0.])
+    transfers = np.array([[1., 0., 0.], [0., 1., 0.]])
+    path_amplitudes = np.array([1., 1j])
+    reference = abs(sum(c * np.dot(q, d.conj())
+                        for c, q in zip(path_amplitudes, transfers)))**2
+    v = path_amplitudes @ transfers
+    actual = intensities_from_response(np.outer(v, v.conj()), np.outer(d, d.conj()))
+    assert_allclose(actual, reference, rtol=0, atol=1e-14)
+
+
+def synthetic_site():
+    hkl = ((0, 0, 0), (2, 0, 0))
+    positions = np.array([[.137, .081, .019]])
+    crystal = SimpleNamespace(fractional_positions=positions, species=('Ni',))
+    model = SimpleNamespace(elastic=SimpleNamespace(crystal=crystal, beams=SimpleNamespace(hkl=hkl)))
+    return model, hkl, positions
+
+
+def test_nontrivial_site_phase_single_double_reduction():
+    """Physics/conventions: synthetic kernel-level control, no material claim."""
+    model, hkl, positions = synthetic_site()
+    sc = fcc_site_phase_matrix(model)
+    phases, weights = equivalent_site_phases(hkl, ((0, 0, 0),), positions)
+    dc = sum(w * np.outer(p[:, 0], p[:, 0].conj()) for p, w in zip(phases, weights))
+    assert_allclose(sc, dc, rtol=0, atol=1e-14)
+
+
+def test_site_phase_discrepancy_is_not_a_global_phase():
+    """Corrected site phases give the same free-outgoing intensity."""
+    model, hkl, positions = synthetic_site()
+    sc = fcc_site_phase_matrix(model)
+    phases, _ = equivalent_site_phases(hkl, ((0, 0, 0),), positions)
+    dc = np.outer(phases[0, :, 0], phases[0, :, 0].conj())
+    assert_allclose(sc, dc, atol=1e-14)
+    a = np.array([1., .5j])
+    k = np.array([[1., .2, .1], [.3, 1., .2]])
+    t = np.eye(3)
+    expected = sum(a[i] * a[j].conjugate() * sc[i, j] * (k[i] @ t @ k[j])
+                   for i in range(2) for j in range(2)).real
+    v = sum(a[i] * phases[0, i, 0] * k[i] for i in range(2))
+    actual = (v @ t @ v.conj()).real
+    assert_allclose(expected, actual, atol=1e-14)
+
+
+def test_transition_gram_mdff_units_positivity():
+    """Algebra/units: independent Gaussian Gram sum and proper MDFF."""
+    _, _, _, d, w, _ = model_data()
+    dataset = TransitionDataset(np.array([800., 802.]), d, w,
+        np.array(['L3', 'L3']), np.array(['Ni1', 'Ni1']), 'synthetic audit')
+    energy = np.array([799., 801., 803.]); sigma = .7
+    result = dipole_tensor_from_transitions(dataset, energy, sigma)
+    expected = np.array([sum(wn * np.outer(dn, dn.conj()) *
+        np.exp(-.5 * ((e - en) / sigma)**2) / (sigma * np.sqrt(2 * np.pi))
+        for en, dn, wn in zip(dataset.energy_ev, d, w)) for e in energy])
+    assert_allclose(result.tensor_angstrom2_per_ev, expected, atol=1e-15)
+    assert np.linalg.eigvalsh(expected).min() > -1e-14
+    q = np.array([[.2, .3, -.1], [-.4, .2, -.1]])
+    s = result.mdff(q[:, None], q[None, :])
+    assert_allclose(s, s.swapaxes(1, 2).conj(), atol=1e-15)
+    assert np.diagonal(s, axis1=1, axis2=2).real.min() >= 0
+    assert_allclose(result.mdff(2*q[:, None], 2*q[None, :]), 4*s)
+    assert_allclose(dipole_kernel(q), q / (2*np.pi*np.sum(q*q, axis=1)[:, None]))
+    assert_allclose(dipole_kernel(2*q), dipole_kernel(q)/2)
+
+
+def test_exit_bra_independent_bases_and_boundary_indices():
+    """Solver: rectangular transition kernel; no incoming/outgoing basis reuse."""
+    hi, ho = matrices(); ho = np.diag([.021, -.013, .04]).astype(complex)
+    incoming, outgoing = BlochStates.solve(hi, 1), BlochStates.solve(ho, 2)
+    z = 1.7
+    assert_allclose(incoming.ket(z), exp2(hi, z)[:, 1], atol=1e-15)
+    assert_allclose(outgoing.ket(-z).conj(), [0, 0, np.exp(.04j*z)], atol=1e-15)
+    rng = np.random.default_rng(581)
+    k = rng.normal(size=(2, 3, 3)) + 1j*rng.normal(size=(2, 3, 3))
+    x, w = np.polynomial.legendre.leggauss(64); ref = np.zeros((3, 3), complex)
+    for zi, wi in zip((x+1)*2, w*2):
+        a = exp2(hi, zi)[:, 1]
+        bra = np.array([0, 0, np.exp(.04j*(4-zi))])
+        v = sum(a[g]*bra[h]*k[g, h] for g in range(2) for h in range(3))
+        ref += wi*np.outer(v, v.conj())
+    assert_allclose(depth_response(incoming, outgoing, k, 4.), ref, atol=3e-14)
+    so = BlochStates.solve(matrices()[1])
+    assert_allclose(so.ket(-z).conj(), exp2(matrices()[1], z)[0], atol=1e-15)
+
+
+def test_degenerate_modes_and_unsupported_complex_eigenvalues():
+    """Solver domain: complex eigenvectors allowed; absorption not implemented."""
+    hi = np.eye(2)*.03 + np.array([[0, 1e-14j], [-1e-14j, 0]])
+    ho = np.eye(2)*-.07
+    k = model_data()[2]
+    assert_allclose(depth_response(BlochStates.solve(hi), BlochStates.solve(ho), k, 4.),
+                    reference_response(hi, ho, k, 4.), atol=2e-15)
+    with pytest.raises(ValueError, match='Hermitian'):
+        BlochStates.solve(np.diag([.1+.01j, .2]))
+
+
+def test_reversal_detector_algebra_integrate_before_percentage():
+    """Algebra: no mirror symmetry presumed for arbitrary geometries."""
+    from emcd_sim.geometry import VirtualDetector
+    q = np.linspace(-1, 1, 17); x, y = np.meshgrid(q, q)
+    na, ma = 2 + x*x + .2*y, .1 + .03*x - .02*y
+    plus, minus = na + ma, na - ma
+    odd, even = (plus-minus)/2, (plus+minus)/2
+    t = model_data()[-1]; r = np.outer([1, 1j, .2], np.conj([1, 1j, .2]))
+    assert_allclose(intensities_from_response(r, t)+intensities_from_response(r, t.conj()),
+                    2*intensities_from_response(r, t.real))
+    values=[]; aperture_weights=[]
+    for center in ((.25, .3), (.25, -.3)):
+        w = VirtualDetector(center, .2).integration_weights(x, y, mode='fractional', subpixels=32)
+        aperture_weights.append(w)
+        assert np.min(w) >= 0 and np.max(w) <= 1
+        integrate = lambda a: float(np.sum(w*a)*(q[1]-q[0])**2)
+        values.append((integrate(even), integrate(odd), integrate(plus), integrate(minus)))
+    assert_allclose(aperture_weights[0], aperture_weights[1][::-1], atol=0, rtol=0)
+    (a, m, ap, am), (b, n, bp, bm) = values
+    assert_allclose((ap-am)/2, m)
+    assert_allclose(ap-bp, (m-n)+(a-b))
+    assert_allclose(100*(ap-bp)/(a+b), 100*(m-n)/(a+b)+100*(a-b)/(a+b))
+    assert a > 0 and b > 0
+    from emcd_sim.gui.component_display import reversal_signals
+    actual, _ = reversal_signals(np.array([ap]), np.array([bp]), np.array([am]), np.array([bm]))
+    assert_allclose(actual['D_mag'], [m-n])
+    assert_allclose(actual['D_nonmag'], [a-b])
+    assert_allclose(actual['D_raw'], [ap-bp])
+    assert_allclose(actual['magnetic_only_percent'], [100*(m-n)/(a+b)])
+    assert_allclose(actual['nonmagnetic_asymmetry_percent'], [100*(a-b)/(a+b)])
+    assert_allclose(actual['emcd_asymmetry_percent'], [100*(ap-bp)/(ap+bp)])
+
+
+def test_fft_against_independent_dense_exponential_step_convergence():
+    """Convergence/solver: explicit DFT and Hermitian 2x2 continuum generator."""
+    u = np.array([.31, -.13]); kinetic = np.array([-.07, .12])
+    f = np.array([[1, 1], [1, -1]])/np.sqrt(2)
+    h = np.diag(kinetic) + f @ np.diag(u) @ f.T
+    initial = np.array([1., 0.], complex); thickness = 3.
+    expected = exp2(h, thickness) @ initial
+    errors=[]
+    plan=FFTSplitStep(u, kinetic)
+    for n in (12, 24, 48):
+        actual=plan.advance(initial, n, thickness/n)
+        errors.append(np.linalg.norm(actual-expected))
+        assert_allclose(plan.advance(actual, n, -thickness/n), initial, atol=2e-14)
+    assert errors[1] < errors[0]/3.9 and errors[2] < errors[1]/3.9
+
+
+def test_depth_quadrature_converges_independently_of_fft():
+    """Convergence: refine depth only, separate from propagation splitting."""
+    hi, ho, k, *_ = model_data()
+    si, so = BlochStates.solve(hi), BlochStates.solve(ho)
+    ref = reference_response(hi, ho, k, 17.)
+    errors = [np.linalg.norm(depth_response(si, so, k, 17., method='numerical', depth_steps=n)-ref)
+              for n in (33, 65, 129)]
+    assert errors[1] < errors[0]/3.9 and errors[2] < errors[1]/3.9
+
+
+def test_small_fft_double_event_intensity_independent_reference():
+    """Solver/convergence: independent DFT Hamiltonians and forward events.
+
+    Fix depth for split-step refinement; then fix the propagation subdivision
+    while refining depth. No shared production tensor-contraction reference.
+    """
+    f = np.array([[1, 1], [1, -1]])/np.sqrt(2)
+    ui, di = np.array([.31, -.13]), np.array([-.07, .12])
+    uo, do = np.array([-.17, .26]), np.array([.08, -.11])
+    hi, ho = np.diag(di)+f@np.diag(ui)@f.T, np.diag(do)+f@np.diag(uo)@f.T
+    _, _, k, d, weights, tensor = model_data()
+    ref = np.sum(reference_response(hi, ho, k, 3.)*tensor.T).real
+    def run(depth, subdivisions):
+        z = np.linspace(0, 3., depth); dz = z[1]-z[0]
+        pi, po = FFTSplitStep(ui, di), FFTSplitStep(uo, do)
+        values = []
+        for j in range(depth):
+            incoming = pi.advance(np.array([1, 0], complex), j*subdivisions, dz/subdivisions)
+            signal = 0.
+            for dn, wn in zip(d, weights):
+                scattered = np.array([sum(incoming[g]*np.dot(k[g, h], dn.conj()) for g in range(2))
+                                      for h in range(2)])
+                exit_wave = po.advance(scattered, (depth-1-j)*subdivisions, dz/subdivisions)
+                signal += wn*abs(exit_wave[0])**2
+            values.append(signal)
+        return dz*(sum(values[1:-1])+(values[0]+values[-1])/2)
+    # Depth quadrature is independent of the split-step approximation.
+    depth_errors=[abs(run(n, 2)-ref) for n in (17, 33, 65)]
+    assert depth_errors[1] < depth_errors[0]/3.8
+    assert depth_errors[2] < depth_errors[1]/3.8
+    assert abs(run(65, 2)-ref)/ref < 1e-4
+    # At fixed depth compare with the exact propagator, same trapezoidal rule.
+    z = np.linspace(0, 3., 17); exact=[]
+    for zi in z:
+        a = exp2(hi, zi)[:, 0]; bra = exp2(ho, 3.-zi)[0]
+        v = sum(a[g]*bra[h]*k[g, h] for g in range(2) for h in range(2))
+        exact.append(sum(wn*abs(np.dot(v, dn.conj()))**2 for dn, wn in zip(d, weights)))
+    trap=(z[1]-z[0])*(sum(exact[1:-1])+(exact[0]+exact[-1])/2)
+    errors=[abs(run(17, n)-trap) for n in (1, 2, 4)]
+    assert errors[1] < errors[0]/3.9 and errors[2] < errors[1]/3.9
```

</details>

### `tests/test_physics_correction_proposal.py`

Decision: Retain validated tests unchanged. Historical diagnostics of uncorrected behavior are stale under the approved correction, not complementary physical requirements. All function/test cases retained; original versions preserved verbatim outside active discovery.

All tolerance keywords unchanged.

<details>
<summary>Original user audit versus validated active test (already present before this repair)</summary>

```diff
--- original/test_physics_correction_proposal.py
+++ validated/test_physics_correction_proposal.py
@@ -1,158 +1,158 @@
-"""Prospective correction checks ONLY: no production function is patched.
-
-The proposed phases/transposes are explicit test inputs or local expressions.
-Passing validates the proposal algebra, not the unchanged production kernels.
-"""
-from types import SimpleNamespace
-
-import numpy as np
-from numpy.testing import assert_allclose
-
-from emcd_sim.double_channeling import BlochStates, depth_response, equivalent_site_phases
-from emcd_sim.multislice_double_channeling import (
-    transition_modes, FFTSplitStep, forward_event_amplitudes,
-)
-from emcd_sim.single_channeling_tensor import _tensor_angular_maps, fcc_site_phase_matrix
-from emcd_sim.geometry import characteristic_qz_angstrom_inv
-
-
-def exp2(h, z):
-    center = np.trace(h).real/2
-    a = h-center*np.eye(2)
-    omega = np.sqrt(np.trace(a@a).real/2)
-    return np.exp(1j*center*z)*(np.cos(omega*z)*np.eye(2)
-        + 1j*z*np.sinc(omega*z/np.pi)*a)
-
-
-def case():
-    hi = np.array([[.013, .11+.04j], [.11-.04j, -.021]])
-    ho = np.diag([.017, -.03]).astype(complex)
-    hkl = np.array([[0,0,0], [2,0,0]])
-    positions = np.array([[.137,.081,.019], [.219,.043,.11]])
-    g = np.array([[0.,0.], [.57,0.]])
-    q = np.array([.23,.31]); energy = 831.271; voltage = 200.
-    qz = -characteristic_qz_angstrom_inv(energy,voltage)
-    transfer = np.concatenate((q[None,None,:]+g[None,:,:]-g[:,None,:],
-                              np.full((2,2,1),qz)),axis=-1)
-    angular = 2*np.pi*transfer
-    kernel = angular/np.sum(angular**2,axis=-1)[...,None]
-    dipoles = np.array([[1.,.3j,.2], [.4-.2j,.6,.1j]])
-    weights = np.array([.7,1.3])
-    tensor = sum(w*np.outer(d,d.conj()) for w,d in zip(weights,dipoles))
-    model = SimpleNamespace(elastic=SimpleNamespace(
-        crystal=SimpleNamespace(fractional_positions=positions,species=('Ni','Ni')),
-        beams=SimpleNamespace(hkl=tuple(map(tuple,hkl))),
-        reciprocal_vectors_xy=g,microscope=SimpleNamespace(acceleration_kv=voltage)))
-    return hi,ho,hkl,positions,kernel,dipoles,weights,tensor,model,q,energy
-
-
-def measurements():
-    hi,ho,hkl,sites,k,d,w,t,model,q,e = case(); thickness = 7.
-    x,weights = np.polynomial.legendre.leggauss(128)
-    coherence = np.zeros((2,2),complex); direct=0.
-    for z,wz in zip((x+1)*thickness/2,weights*thickness/2):
-        a = exp2(hi,z)[:,0]
-        coherence += wz*np.outer(a,a.conj())/thickness
-        for site in sites:
-            phase = np.exp(2j*np.pi*(hkl@site))
-            for dn,wn in zip(d,w):
-                amplitude = sum(a[g]*phase[g]*np.dot(k[g,0],dn.conj()) for g in range(2))
-                direct += wz*wn*abs(amplitude)**2/len(sites)
-    phase_single = fcc_site_phase_matrix(model)
-    # Explicit proposed response transpose through inputs, without altering SC.
-    ev,od = _tensor_angular_maps(model,t.T,e,coherence,phase_single,
-                                np.array([q[0]]),np.array([q[1]]))
-    proposed_single = thickness*(ev[0]+od[0])
-    current_r = np.zeros((3,3),complex); proposed_r=current_r.copy()
-    phases,site_weights=equivalent_site_phases(hkl,hkl,sites)
-    for phase,weight in zip(phases,site_weights):
-        current_r += weight*depth_response(BlochStates.solve(hi),BlochStates.solve(ho),
-                                           k*phase[...,None],thickness)
-    # Independent construction from physical positions; not current helper.conj.
-    delta = hkl[:,None,:]-hkl[None,:,:]
-    for site in sites:
-        proposed_phase=np.exp(2j*np.pi*(delta@site))
-        proposed_r += depth_response(BlochStates.solve(hi),BlochStates.solve(ho),
-                                     k*proposed_phase[...,None],thickness)/len(sites)
-    return dict(direct=direct,proposed_single=proposed_single,
-        proposed_double=np.sum(proposed_r*t.T).real,
-        contraction_only=np.sum(current_r*t.T).real,
-        phase_only=np.sum(proposed_r*t).real,
-        current_double=np.sum(current_r*t).real)
-
-
-def test_proposed_nontrivial_site_free_exit_limit_matches_born():
-    """Physics proposal: true complex-site SC/DC reduction with independent H."""
-    values=measurements()
-    assert_allclose(values['proposed_single'],values['direct'],rtol=2e-13,atol=1e-14)
-    assert_allclose(values['proposed_double'],values['direct'],rtol=2e-13,atol=1e-14)
-
-
-def test_both_corrections_are_required_for_complex_sites_and_dipoles():
-    """Physics/algebra: isolate phase-only from contraction-only correction."""
-    values=measurements()
-    for key in ('current_double','contraction_only','phase_only'):
-        assert abs(values[key]-values['direct']) > 1e-4
-
-
-def test_transition_factor_is_unchanged_but_forward_modes_are_conjugated():
-    """Algebra: L* L^T=T^T; do not conjugate K, fast fields or factor twice."""
-    *_, t, model, q, energy = case()
-    d = case()[5]; w=case()[6]
-    l = transition_modes(t)
-    v = np.array([.21+.13j, -.32+.17j, .11-.07j])
-    direct = sum(wn*abs(np.dot(v,dn.conj()))**2 for wn,dn in zip(w,d))
-    assert_allclose(l@l.conj().T,t,atol=1e-14)
-    assert_allclose(l.conj()@l.T,t.T,atol=1e-14)
-    assert_allclose(np.sum(abs(v@l.conj())**2),direct,rtol=2e-14)
-    assert_allclose(np.sum(np.outer(v,v.conj())*t.T).real,direct,rtol=2e-14)
-    assert abs(np.sum(abs(v@l)**2)-direct) > 1e-4
-
-
-def test_site_origin_covariance_under_rephased_elastic_coefficients():
-    """Physics proposal: pure origin shift, not movement within fixed potential."""
-    hi,ho,hkl,sites,k,d,w,t,*_=case()
-    ho=np.array([[-.017,.083-.03j],[.083+.03j,.032]])
-    shift=np.array([.173,-.031,.07]); thickness=4.; z=1.2
-    # Coordinates r'=r-shift; potential and waves transform with the basis.
-    diagonal=np.diag(np.exp(2j*np.pi*(hkl@shift)))
-    shifted_hi=diagonal@hi@diagonal.conj().T
-    shifted_ho=diagonal@ho@diagonal.conj().T
-    a=exp2(hi,z)[:,0]; bra=exp2(ho,thickness-z)[0]
-    shifted_a=exp2(shifted_hi,z)[:,0]
-    shifted_bra=exp2(shifted_ho,thickness-z)[0]
-    for site in sites:
-        delta=hkl[:,None,:]-hkl[None,:,:]
-        phase=np.exp(2j*np.pi*(delta@site))
-        shifted_phase=np.exp(2j*np.pi*(delta@(site-shift)))
-        v=np.einsum('g,h,gha,gh->a',a,bra,k,phase)
-        shifted_v=np.einsum('g,h,gha,gh->a',shifted_a,shifted_bra,k,shifted_phase)
-        assert_allclose(shifted_v,v,atol=2e-15)
-
-
-def test_proposed_forward_mode_use_with_complex_kernel_and_exit():
-    """Prospective solver check: direct dipoles and explicit DFT exit matrix.
-
-    Passing T* to the UNCHANGED helper tests the proposed conjugated-mode
-    intensity algebra only. After an approved patch the caller must pass T.
-    """
-    d=case()[5]; weights=case()[6]; t=case()[7]
-    incoming=np.array([.8+.2j,-.1+.3j]);rng=np.random.default_rng(593)
-    kernel=rng.normal(size=(2,3,3))+.2j*rng.normal(size=(2,3,3))
-    u=np.array([.2,-.1,.4,.05]);kinetic=np.array([.04,-.03,.09,.1])
-    n=4;indices=np.array([0,1,3]);dz=.03;count=20
-    points=np.arange(n);f=np.exp(-2j*np.pi*points[:,None]*points[None,:]/n)/np.sqrt(n)
-    half=np.diag(np.exp(.5j*dz*kinetic))
-    step=half@f@np.diag(np.exp(1j*dz*u))@f.conj().T@half
-    exit_matrix=np.linalg.matrix_power(step,count)
-    direct=0.
-    for dn,wn in zip(d,weights):
-        scattered=np.zeros(n,complex)
-        for j,h in enumerate(indices):
-            scattered[h]=sum(incoming[g]*np.dot(kernel[g,j],dn.conj()) for g in range(2))
-        direct += wn*abs((exit_matrix@scattered)[0])**2
-    plan=FFTSplitStep(u,kinetic);slices=[(plan,dz)]*count
-    current=forward_event_amplitudes(incoming,kernel,t,plan,slices,indices)
-    candidate=forward_event_amplitudes(incoming,kernel,t.conj(),plan,slices,indices)
-    assert_allclose(np.sum(abs(candidate)**2),direct,rtol=2e-13,atol=1e-14)
-    assert abs(np.sum(abs(current)**2)-direct)>1e-4
+"""Approved correction controls: production paths vs independent references.
+
+The proposed phases/transposes are explicit test inputs or local expressions.
+Current production uses the approved contractions and forward amplitudes.
+"""
+from types import SimpleNamespace
+
+import numpy as np
+from numpy.testing import assert_allclose
+
+from emcd_sim.double_channeling import BlochStates, depth_response, equivalent_site_phases, intensities_from_response
+from emcd_sim.multislice_double_channeling import (
+    transition_modes, FFTSplitStep, forward_event_amplitudes,
+)
+from emcd_sim.single_channeling_tensor import _tensor_angular_maps, fcc_site_phase_matrix
+from emcd_sim.geometry import characteristic_qz_angstrom_inv
+
+
+def exp2(h, z):
+    center = np.trace(h).real/2
+    a = h-center*np.eye(2)
+    omega = np.sqrt(np.trace(a@a).real/2)
+    return np.exp(1j*center*z)*(np.cos(omega*z)*np.eye(2)
+        + 1j*z*np.sinc(omega*z/np.pi)*a)
+
+
+def case():
+    hi = np.array([[.013, .11+.04j], [.11-.04j, -.021]])
+    ho = np.diag([.017, -.03]).astype(complex)
+    hkl = np.array([[0,0,0], [2,0,0]])
+    positions = np.array([[.137,.081,.019], [.219,.043,.11]])
+    g = np.array([[0.,0.], [.57,0.]])
+    q = np.array([.23,.31]); energy = 831.271; voltage = 200.
+    qz = -characteristic_qz_angstrom_inv(energy,voltage)
+    transfer = np.concatenate((q[None,None,:]+g[None,:,:]-g[:,None,:],
+                              np.full((2,2,1),qz)),axis=-1)
+    angular = 2*np.pi*transfer
+    kernel = angular/np.sum(angular**2,axis=-1)[...,None]
+    dipoles = np.array([[1.,.3j,.2], [.4-.2j,.6,.1j]])
+    weights = np.array([.7,1.3])
+    tensor = sum(w*np.outer(d,d.conj()) for w,d in zip(weights,dipoles))
+    model = SimpleNamespace(elastic=SimpleNamespace(
+        crystal=SimpleNamespace(fractional_positions=positions,species=('Ni','Ni')),
+        beams=SimpleNamespace(hkl=tuple(map(tuple,hkl))),
+        reciprocal_vectors_xy=g,microscope=SimpleNamespace(acceleration_kv=voltage)))
+    return hi,ho,hkl,positions,kernel,dipoles,weights,tensor,model,q,energy
+
+
+def measurements():
+    hi,ho,hkl,sites,k,d,w,t,model,q,e = case(); thickness = 7.
+    x,weights = np.polynomial.legendre.leggauss(128)
+    coherence = np.zeros((2,2),complex); direct=0.
+    for z,wz in zip((x+1)*thickness/2,weights*thickness/2):
+        a = exp2(hi,z)[:,0]
+        coherence += wz*np.outer(a,a.conj())/thickness
+        for site in sites:
+            phase = np.exp(2j*np.pi*(hkl@site))
+            for dn,wn in zip(d,w):
+                amplitude = sum(a[g]*phase[g]*np.dot(k[g,0],dn.conj()) for g in range(2))
+                direct += wz*wn*abs(amplitude)**2/len(sites)
+    phase_single = fcc_site_phase_matrix(model)
+    # Actual corrected Single kernel, using the original tensor unchanged.
+    ev,od = _tensor_angular_maps(model,t,e,coherence,phase_single,
+                                np.array([q[0]]),np.array([q[1]]))
+    proposed_single = thickness*(ev[0]+od[0])
+    current_r = np.zeros((3,3),complex); proposed_r=current_r.copy()
+    phases,site_weights=equivalent_site_phases(hkl,hkl,sites)
+    for phase,weight in zip(phases,site_weights):
+        current_r += weight*depth_response(BlochStates.solve(hi),BlochStates.solve(ho),
+                                           k*phase.conj()[...,None],thickness)
+    # Independent construction from physical positions; not current helper.conj.
+    delta = hkl[:,None,:]-hkl[None,:,:]
+    for site in sites:
+        proposed_phase=np.exp(2j*np.pi*(delta@site))
+        proposed_r += depth_response(BlochStates.solve(hi),BlochStates.solve(ho),
+                                     k*proposed_phase[...,None],thickness)/len(sites)
+    return dict(direct=direct,proposed_single=proposed_single,
+        proposed_double=intensities_from_response(proposed_r,t),
+        contraction_only=np.sum(current_r*t.T).real,
+        phase_only=np.sum(proposed_r*t).real,
+        current_double=np.sum(current_r*t).real)
+
+
+def test_proposed_nontrivial_site_free_exit_limit_matches_born():
+    """Physics proposal: true complex-site SC/DC reduction with independent H."""
+    values=measurements()
+    assert_allclose(values['proposed_single'],values['direct'],rtol=2e-13,atol=1e-14)
+    assert_allclose(values['proposed_double'],values['direct'],rtol=2e-13,atol=1e-14)
+
+
+def test_both_corrections_are_required_for_complex_sites_and_dipoles():
+    """Physics/algebra: isolate phase-only from contraction-only correction."""
+    values=measurements()
+    for key in ('current_double','contraction_only','phase_only'):
+        assert abs(values[key]-values['direct']) > 1e-4
+
+
+def test_transition_factor_is_unchanged_but_forward_modes_are_conjugated():
+    """Algebra: L* L^T=T^T; do not conjugate K, fast fields or factor twice."""
+    *_, t, model, q, energy = case()
+    d = case()[5]; w=case()[6]
+    l = transition_modes(t)
+    v = np.array([.21+.13j, -.32+.17j, .11-.07j])
+    direct = sum(wn*abs(np.dot(v,dn.conj()))**2 for wn,dn in zip(w,d))
+    assert_allclose(l@l.conj().T,t,atol=1e-14)
+    assert_allclose(l.conj()@l.T,t.T,atol=1e-14)
+    assert_allclose(np.sum(abs(v@l.conj())**2),direct,rtol=2e-14)
+    assert_allclose(np.sum(np.outer(v,v.conj())*t.T).real,direct,rtol=2e-14)
+    assert abs(np.sum(abs(v@l)**2)-direct) > 1e-4
+
+
+def test_site_origin_covariance_under_rephased_elastic_coefficients():
+    """Physics proposal: pure origin shift, not movement within fixed potential."""
+    hi,ho,hkl,sites,k,d,w,t,*_=case()
+    ho=np.array([[-.017,.083-.03j],[.083+.03j,.032]])
+    shift=np.array([.173,-.031,.07]); thickness=4.; z=1.2
+    # Coordinates r'=r-shift; potential and waves transform with the basis.
+    diagonal=np.diag(np.exp(2j*np.pi*(hkl@shift)))
+    shifted_hi=diagonal@hi@diagonal.conj().T
+    shifted_ho=diagonal@ho@diagonal.conj().T
+    a=exp2(hi,z)[:,0]; bra=exp2(ho,thickness-z)[0]
+    shifted_a=exp2(shifted_hi,z)[:,0]
+    shifted_bra=exp2(shifted_ho,thickness-z)[0]
+    for site in sites:
+        delta=hkl[:,None,:]-hkl[None,:,:]
+        phase=np.exp(2j*np.pi*(delta@site))
+        shifted_phase=np.exp(2j*np.pi*(delta@(site-shift)))
+        v=np.einsum('g,h,gha,gh->a',a,bra,k,phase)
+        shifted_v=np.einsum('g,h,gha,gh->a',shifted_a,shifted_bra,k,shifted_phase)
+        assert_allclose(shifted_v,v,atol=2e-15)
+
+
+def test_proposed_forward_mode_use_with_complex_kernel_and_exit():
+    """Prospective solver check: direct dipoles and explicit DFT exit matrix.
+
+    The actual helper receives T; T* below represents the historical wrong
+    excitation convention and must disagree with the independent reference.
+    """
+    d=case()[5]; weights=case()[6]; t=case()[7]
+    incoming=np.array([.8+.2j,-.1+.3j]);rng=np.random.default_rng(593)
+    kernel=rng.normal(size=(2,3,3))+.2j*rng.normal(size=(2,3,3))
+    u=np.array([.2,-.1,.4,.05]);kinetic=np.array([.04,-.03,.09,.1])
+    n=4;indices=np.array([0,1,3]);dz=.03;count=20
+    points=np.arange(n);f=np.exp(-2j*np.pi*points[:,None]*points[None,:]/n)/np.sqrt(n)
+    half=np.diag(np.exp(.5j*dz*kinetic))
+    step=half@f@np.diag(np.exp(1j*dz*u))@f.conj().T@half
+    exit_matrix=np.linalg.matrix_power(step,count)
+    direct=0.
+    for dn,wn in zip(d,weights):
+        scattered=np.zeros(n,complex)
+        for j,h in enumerate(indices):
+            scattered[h]=sum(incoming[g]*np.dot(kernel[g,j],dn.conj()) for g in range(2))
+        direct += wn*abs((exit_matrix@scattered)[0])**2
+    plan=FFTSplitStep(u,kinetic);slices=[(plan,dz)]*count
+    current=forward_event_amplitudes(incoming,kernel,t.conj(),plan,slices,indices)
+    candidate=forward_event_amplitudes(incoming,kernel,t,plan,slices,indices)
+    assert_allclose(np.sum(abs(candidate)**2),direct,rtol=2e-13,atol=1e-14)
+    assert abs(np.sum(abs(current)**2)-direct)>1e-4
```

</details>

## 4. Guide and remaining collisions

The isolated USER_GUIDE retains **all original user bytes verbatim as a prefix**,
including policy v5, 2 nm default, editability/override notes and the original
range typography. Only the appended physics note is refined to state
`d_a=<i|r_a|f>`, `T=d d^dagger`, `I=Re Tr(RT)`, conjugated forward modes `L*`,
and Double site phase `exp(+2*pi*i*(g-h).u)`. The general tensor is the weighted
transition sum. The note distinguishes corrected source from untouched historical
results/Windows builds and retains convergence caveats. No unrelated guide
content is rewritten; the original main guide is untouched.

| Original collision | Initial classification | Final disposition |
|---|---|---|
| `docs/PHYSICS_CONVENTIONS_AND_SOURCE_MAP.md` | content-equivalent | original unchanged; validated copy retained |
| `docs/PHYSICS_MATRIX_IMPLEMENTATION_AUDIT.md` | content-equivalent | original unchanged; validated copy retained |
| `docs/PHYSICS_MINIMAL_CORRECTION_PROPOSAL.md` | byte-identical | original unchanged; validated copy retained |
| `docs/PHYSICS_REGRESSION_FAILURE_REVIEW.md` | byte-identical | original unchanged; validated copy retained |
| `docs/PHYSICS_VALIDATION_RESULTS.md` | content-equivalent | original unchanged; validated copy retained |
| `tests/test_physics_correction_proposal.py` | different | original unchanged; validated copy retained |
| `tests/test_physics_matrix_audit.py` | different | original unchanged; validated copy retained |

The two identical and three line-ending-only documents remain unchanged on
both sides. No exact-byte-provenance file was normalized. The eighth noncolliding
local audit script remains untracked in its original worktree and is excluded
from the candidate. Full original/candidate hashes and comparisons remain in
`outputs/physics_main_reconciliation/reconciliation_manifest.json` and snapshots.
There is no unresolved scientific assertion conflict. Original dirty files are
still present; avoiding their overwrite requires the clean-main workflow below.

## 5. Validation

| Scope | Passed | Failed/errors | Skipped |
|---|---:|---:|---:|
| provenance | 7 | 0 | 0 |
| affected | 20 | 0 | 0 |
| focused | 59 | 0 | 0 |
| gui | 19 | 0 | 0 |
| docs | 9 | 0 | 0 |
| Complete fresh process 1 | 602 | 0 | 2 |
| Complete fresh process 2 | 602 | 0 | 2 |

Overlapping counts are not summed. The full suite includes the two new checkout
tests, explaining the increase from 600 to 602 passing cases. Both complete
rounds use separate fresh processes with the same source/test fingerprint:
`7e77a5ccf81d4e08b82d042ae66395f48e174dcf8a33bcb8e505d82c319e52ed`. Wall times: 1031.23 and
906.69 seconds. The broader frozen candidate hash list
also includes the repaired input, attributes and guide and remains unchanged.
No failure was suppressed, XFAILed or hidden by weakening a test or input hash.
The previous 58-pass/1-provenance-failure evidence remains unchanged as history.

Expected skips in both rounds:

- `tests.test_ni_017.Ni017Tests::test_verified_native_edges`: Requires original local WIEN2k audit companions; not distributed
- `tests.test_ni_117_final_symmetry::test_wien2k_axis_is_independent_of_gui_default`: Optional local WIEN2k companion audit; original files are not distributed with the package

GUI/resource lifecycle observations:

```json
[
  {
    "run": 1,
    "windows_destroyed": 105,
    "max_remaining_mainwindows": 0,
    "max_post_teardown_rss_mib": 312.1875
  },
  {
    "run": 2,
    "windows_destroyed": 105,
    "max_remaining_mainwindows": 0,
    "max_post_teardown_rss_mib": 313.04296875
  }
]
```

RSS values are post-teardown samples, not peak-memory measurements. Real memory
admission remains active. Qt/Matplotlib deprecation and constrained-layout
warnings remain in logs; no native Windows EXE acceptance is inferred.

All **32 saved BW/MS comparisons** pass unchanged raw-relative <=0.1% and PRB
<=0.01 pp thresholds by reading/recomputing saved observables, without solver
calls or historical writes. Max discrepancies remain 0.01749585% raw and
0.005387449 pp PRB. In the saved 300 kV Ni [017], 30 nm/+15 mrad case,
Double BW L3 remains +1.7099%
magnetic-only and -2.9371% conventional A/B. Existing scientific convergence,
XMCD-effective versus genuine DFT-MDFF, absolute handedness/energy calibration,
projected IAM/frozen q_z/finite-ZOLZ and detector-grid limitations remain.
No full Stage4.2 scientific reconvergence or SNR calibration is claimed.

Preservation verification passed: **323 protected files including 204 production
checkpoints**, **9756 historical files**, **19 original scientific files**, all
eight original main untracked files, the original user guide, and all 12
pre-existing worktrees' HEADs/statuses/user hashes. The 53 production Python
files are unchanged; the versioned source guard and both manifests are unchanged.

| Kernel | Unchanged canonical SHA256 |
|---|---|
| `src/emcd_sim/single_channeling_tensor.py` | `ac8a150fd370615b74886aeb81564a2fdd6b15e3d5da94e58ea1982afba8610d` |
| `src/emcd_sim/double_channeling.py` | `5b641bc918250b6402f4bcf6c31c1f3fec1425714098a1c99ed04e321b7ef06b` |
| `src/emcd_sim/multislice_double_channeling.py` | `f7cc80b8de0898123813d6f1a284519df3790516ffa5660634bfccc838c437c5` |

## 6. Exact uncommitted file boundary and evidence

Tracked modifications relative to preview:

```text
data/wien2k_ni/Ni_fm.xmcd
docs/USER_GUIDE.md
```

Untracked review/test files:

```text
docs/PHYSICS_CORRECTION_MAIN_RECONCILIATION.md
docs/PHYSICS_CORRECTION_MAIN_RECONCILIATION_FINAL.md
tests/test_input_checkout_provenance.py
```

The older reconciliation report is preserved unchanged, with its dated NO-GO
and failure evidence. This final report supersedes that disposition. There are
no other proposed source/test/data files; generated logs, copied historical
fixtures, original snapshots and helper scripts remain ignored under outputs.
No original user research/tool files are proposed for Git inclusion.

Evidence: `outputs/physics_main_reconciliation_final/` holds candidate hashes,
original/repaired blob hashes, exact audit diffs, Git-checkout samples, targeted
JUnit/logs, preservation proof and final manifest. Complete-suite logs/JUnit
and fingerprints are under
`outputs/physics_correction_final_integration/reconciliation_final_v1_run1/`
and `reconciliation_final_v1_run2/`. Scientific revalidation is beside those.

Reproduction commands (PYTHONPATH=src, PYTHONDONTWRITEBYTECODE=1,
QT_QPA_PLATFORM=offscreen, OPENBLAS_NUM_THREADS=OMP_NUM_THREADS=1):

```powershell
python -B -m pytest tests/test_physics_source_guard.py tests/test_input_checkout_provenance.py -q -p no:cacheprovider
python -B -m pytest tests/test_physics_matrix_audit.py tests/test_physics_correction_proposal.py -q -p no:cacheprovider
python -B scripts/run_final_physics_regressions.py --rounds 2 --tag reconciliation_final_v1
python -B scripts/revalidate_final_physics.py
python -B outputs/physics_main_reconciliation_final/verify_preservation.py
```

The exact 59-test command and GUI subsets are recorded in `targeted_runs.json`.

## 7. Precise next integration steps: for approval, not executed

Content/provenance reconciliation is accepted. **Actual main cannot be advanced
safely inside its current dirty worktree.** A future source commit is still
required; the old HEAD blob is not repaired until the candidate is committed.
Do not push the current main or describe it as containing this repair.

After separate approval, use two focused commits in this reconciliation branch:

```powershell
# In build/physics-correction-main-reconciliation, after reviewing these exact diffs:
if ((git branch --show-current) -ne 'reconciliation/forward-born-user-work') { throw 'Wrong candidate branch' }
if (git diff --cached --name-only) { throw 'Index must be empty before selective staging' }
git add -- data/wien2k_ni/Ni_fm.xmcd tests/test_input_checkout_provenance.py
git diff --cached --stat
# Verify staged data OID equals da46623569735ae9f18396d9f00e843f23d37404:
git rev-parse :data/wien2k_ni/Ni_fm.xmcd
git commit -m "fix(provenance): preserve registered XMCD bytes across checkouts"
git add -- docs/USER_GUIDE.md docs/PHYSICS_CORRECTION_MAIN_RECONCILIATION.md docs/PHYSICS_CORRECTION_MAIN_RECONCILIATION_FINAL.md
git commit -m "docs: reconcile user guide and physics integration readiness"
```

Require success and review the index before **each** commit. Do not stage all
files, scientific outputs or personal audit tools. Verify committed data OID
and exact hashes, source/test candidate identity and clean status afterward.
No historical file/user-work commit is needed or proposed; retain that work
as original dirty files and preservation snapshots.

Then, only after confirming the baseline hashes/status have not changed, use
this file-preserving branch/worktree transition. It switches the original dirty
worktree to a newly named preservation branch at **the identical HEAD**, leaving
all user bytes in place. It does not update a checked-out main ref by force:

```powershell
# All following steps require separate approval and success checks.
git -C C:/Users/peng863/EMCD-Sim/build/physics-correction-main-reconciliation fetch origin main
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
$aheadBehind = git -C C:/Users/peng863/EMCD-Sim/build/physics-correction-main-reconciliation rev-list --left-right --count main...origin/main
if ($LASTEXITCODE -ne 0 -or $aheadBehind -notmatch '^0\s+0$') { throw 'Review remote divergence first' }
$originalHead = git -C C:/Users/peng863/EMCD-Sim/build/source-cleanup-integration rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or $originalHead -ne 'a77f7455f5fe57dad6bae5d948477b2390433bb0') { throw 'Original HEAD changed' }
if (Test-Path -LiteralPath C:/Users/peng863/EMCD-Sim/build/physics-correction-clean-main) { throw 'Clean-main path already exists' }
# Verify user hashes first. The new preservation branch name must not exist:
git -C C:/Users/peng863/EMCD-Sim/build/source-cleanup-integration switch -c preserve/main-user-work-before-physics
if ($LASTEXITCODE -ne 0) { throw 'Preservation branch switch failed; stop' }
# Verify unchanged original file hashes/status; main is now not checked out there.
# The following clean-main path must not exist; Git must refuse any collision:
git -C C:/Users/peng863/EMCD-Sim worktree add C:/Users/peng863/EMCD-Sim/build/physics-correction-clean-main main
if ($LASTEXITCODE -ne 0) { throw 'Clean main checkout failed; stop' }
$targetStatus = git -C C:/Users/peng863/EMCD-Sim/build/physics-correction-clean-main status --porcelain
if ($LASTEXITCODE -ne 0 -or $targetStatus) { throw 'Main target is not clean' }
# Require clean target and understood history, then a normal history-preserving merge:
git -C C:/Users/peng863/EMCD-Sim/build/physics-correction-clean-main merge --no-ff reconciliation/forward-born-user-work -m "Merge validated forward-Born correction and provenance reconciliation"
```

Never continue past a failed precondition/command. The same-HEAD preservation
branch switch has no tree delta and the clean-main worktree starts empty, so
neither operation needs to overwrite the dirty original files. Preserve both
worktrees, all branches and snapshots. If remote history changes, a name/path
already exists, user hashes change, or any conflict touches physics/provenance,
stop for review rather than force or guess. Post-merge verify exact source/input
identity and focused/provenance checks in the actual new main worktree. No
reset, forced checkout, blind stash, deletion or checked-out-ref update is used.

These are proposed future actions only. No commit, actual-main merge or remote
mutation occurred. Windows packaging and Stage4.2 execution remain separate
tasks requiring approval and their own acceptance; no tag/release/build is ready
merely from source-suite success.
