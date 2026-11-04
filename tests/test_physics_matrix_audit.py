"""Independent audit controls for the approved forward-Born correction.

No reference arrays are regenerated. Closed Pauli exponentials and explicit
DFT matrices are references, not wrappers around another production solver.
The two original reproduction bodies are preserved; neither has XFAIL.
"""
from types import SimpleNamespace

import numpy as np
import pytest
from numpy.testing import assert_allclose

from emcd_sim.double_channeling import (
    BlochStates, depth_response, dipole_kernel, intensities_from_response,
    equivalent_site_phases,
)
from emcd_sim.mdff_tensor import (
    TransitionDataset, dipole_tensor_from_transitions, DipoleTensor,
)
from emcd_sim.multislice_double_channeling import FFTSplitStep
from emcd_sim.single_channeling_tensor import historical_ni_site_phase_matrix


def exp2(h, z):
    """Independent exact exponential of a complex Hermitian 2x2 matrix."""
    center = np.trace(h).real / 2
    a = h - center * np.eye(2)
    omega = np.sqrt(np.trace(a @ a).real / 2)
    return np.exp(1j * center * z) * (
        np.cos(omega * z) * np.eye(2) + 1j * z * np.sinc(omega * z / np.pi) * a
    )


def matrices():
    return (np.array([[.013, .11 + .04j], [.11 - .04j, -.021]]),
            np.array([[-.017, .083 - .03j], [.083 + .03j, .032]]))


def model_data():
    hi, ho = matrices()
    q = np.array([[[.21, .3, -.1], [.77, .3, -.1]],
                  [[-.35, .3, -.1], [.21, .3, -.1]]])
    # Independent rad/Angstrom kernel, not dipole_kernel as reference.
    angular = 2 * np.pi * q
    k = angular / np.sum(angular**2, axis=-1)[..., None]
    d = np.array([[1, .3j, .2], [.4 - .2j, .6, .1j]])
    weights = np.array([.7, 1.3])
    tensor = sum(w * np.outer(v, v.conj()) for w, v in zip(weights, d))
    return hi, ho, k, d, weights, tensor


def reference_response(hi, ho, k, thickness, order=96):
    """Independent numerical depth quadrature of coherent event amplitudes."""
    x, w = np.polynomial.legendre.leggauss(order)
    result = np.zeros((3, 3), complex)
    for z, weight in zip((x + 1) * thickness / 2, w * thickness / 2):
        a = exp2(hi, z)[:, 0]
        bra = exp2(ho, thickness - z)[0, :]
        v = sum(a[g] * bra[h] * k[g, h] for g in range(2) for h in range(2))
        result += weight * np.outer(v, v.conj())
    return result


@pytest.mark.parametrize('thickness', [0., 1e-7, .3, 17.])
def test_independent_analytic_depth_response(thickness):
    """Solver implementation: complex eigenvectors, thin/zero and finite depth."""
    hi, ho, k, _, _, _ = model_data()
    expected = reference_response(hi, ho, k, thickness)
    actual = depth_response(BlochStates.solve(hi), BlochStates.solve(ho), k, thickness)
    assert_allclose(actual, expected, rtol=2e-12, atol=2e-15)


def test_direct_transition_sum_same_index_algebra_and_phase():
    """Forward Born algebra: excitation V=sum K*d*."""
    hi, ho, k, d, weights, tensor = model_data()
    x, w = np.polynomial.legendre.leggauss(96)
    direct = 0.
    for z, weight in zip((x + 1) * 8.5, w * 8.5):
        a = exp2(hi, z)[:, 0]
        bra = exp2(ho, 17 - z)[0]
        for dn, wn in zip(d, weights):
            transition = np.array([[sum(k[g, h, j] * dn[j].conjugate() for j in range(3))
                                    for g in range(2)] for h in range(2)])
            direct += weight * wn * abs(bra @ transition @ a)**2
    r = depth_response(BlochStates.solve(hi), BlochStates.solve(ho), k, 17.)
    assert_allclose(intensities_from_response(r, tensor), direct, rtol=2e-13)
    assert direct > 0
    phased = d * np.exp(1j * np.array([.4, -.7]))[:, None]
    assert_allclose(sum(w * np.outer(v, v.conj()) for w, v in zip(weights, phased)), tensor)
    # The historical same-index contraction is generally different.
    assert abs(np.sum(r * tensor).real - direct) > 1e-4


def test_microscopic_born_dipole_conjugation():
    """Physics: forward Born amplitude uses <f|exp(-i Q.r)|i>.

    For Q=k_out-k_in, its dipole term is -i Q.d*, independent of
    the common -i phase. A one-event complex example distinguishes signs.
    """
    d = np.array([1., 1j, 0.])
    transfers = np.array([[1., 0., 0.], [0., 1., 0.]])
    path_amplitudes = np.array([1., 1j])
    reference = abs(sum(c * np.dot(q, d.conj())
                        for c, q in zip(path_amplitudes, transfers)))**2
    v = path_amplitudes @ transfers
    actual = intensities_from_response(np.outer(v, v.conj()), np.outer(d, d.conj()))
    assert_allclose(actual, reference, rtol=0, atol=1e-14)


def synthetic_site():
    hkl = ((0, 0, 0), (2, 0, 0))
    positions = np.array([[.137, .081, .019]])
    crystal = SimpleNamespace(fractional_positions=positions, species=('Ni',))
    model = SimpleNamespace(elastic=SimpleNamespace(crystal=crystal, beams=SimpleNamespace(hkl=hkl)))
    return model, hkl, positions


def test_nontrivial_site_phase_single_double_reduction():
    """Physics/conventions: synthetic kernel-level control, no material claim."""
    model, hkl, positions = synthetic_site()
    sc = historical_ni_site_phase_matrix(model)
    phases, weights = equivalent_site_phases(hkl, ((0, 0, 0),), positions)
    dc = sum(w * np.outer(p[:, 0], p[:, 0].conj()) for p, w in zip(phases, weights))
    assert_allclose(sc, dc, rtol=0, atol=1e-14)


def test_site_phase_discrepancy_is_not_a_global_phase():
    """Corrected site phases give the same free-outgoing intensity."""
    model, hkl, positions = synthetic_site()
    sc = historical_ni_site_phase_matrix(model)
    phases, _ = equivalent_site_phases(hkl, ((0, 0, 0),), positions)
    dc = np.outer(phases[0, :, 0], phases[0, :, 0].conj())
    assert_allclose(sc, dc, atol=1e-14)
    a = np.array([1., .5j])
    k = np.array([[1., .2, .1], [.3, 1., .2]])
    t = np.eye(3)
    expected = sum(a[i] * a[j].conjugate() * sc[i, j] * (k[i] @ t @ k[j])
                   for i in range(2) for j in range(2)).real
    v = sum(a[i] * phases[0, i, 0] * k[i] for i in range(2))
    actual = (v @ t @ v.conj()).real
    assert_allclose(expected, actual, atol=1e-14)


def test_transition_gram_mdff_units_positivity():
    """Algebra/units: independent Gaussian Gram sum and proper MDFF."""
    _, _, _, d, w, _ = model_data()
    dataset = TransitionDataset(np.array([800., 802.]), d, w,
        np.array(['L3', 'L3']), np.array(['Ni1', 'Ni1']), 'synthetic audit')
    energy = np.array([799., 801., 803.]); sigma = .7
    result = dipole_tensor_from_transitions(dataset, energy, sigma)
    expected = np.array([sum(wn * np.outer(dn, dn.conj()) *
        np.exp(-.5 * ((e - en) / sigma)**2) / (sigma * np.sqrt(2 * np.pi))
        for en, dn, wn in zip(dataset.energy_ev, d, w)) for e in energy])
    assert_allclose(result.tensor_angstrom2_per_ev, expected, atol=1e-15)
    assert np.linalg.eigvalsh(expected).min() > -1e-14
    q = np.array([[.2, .3, -.1], [-.4, .2, -.1]])
    s = result.mdff(q[:, None], q[None, :])
    assert_allclose(s, s.swapaxes(1, 2).conj(), atol=1e-15)
    assert np.diagonal(s, axis1=1, axis2=2).real.min() >= 0
    assert_allclose(result.mdff(2*q[:, None], 2*q[None, :]), 4*s)
    assert_allclose(dipole_kernel(q), q / (2*np.pi*np.sum(q*q, axis=1)[:, None]))
    assert_allclose(dipole_kernel(2*q), dipole_kernel(q)/2)


def test_exit_bra_independent_bases_and_boundary_indices():
    """Solver: rectangular transition kernel; no incoming/outgoing basis reuse."""
    hi, ho = matrices(); ho = np.diag([.021, -.013, .04]).astype(complex)
    incoming, outgoing = BlochStates.solve(hi, 1), BlochStates.solve(ho, 2)
    z = 1.7
    assert_allclose(incoming.ket(z), exp2(hi, z)[:, 1], atol=1e-15)
    assert_allclose(outgoing.ket(-z).conj(), [0, 0, np.exp(.04j*z)], atol=1e-15)
    rng = np.random.default_rng(581)
    k = rng.normal(size=(2, 3, 3)) + 1j*rng.normal(size=(2, 3, 3))
    x, w = np.polynomial.legendre.leggauss(64); ref = np.zeros((3, 3), complex)
    for zi, wi in zip((x+1)*2, w*2):
        a = exp2(hi, zi)[:, 1]
        bra = np.array([0, 0, np.exp(.04j*(4-zi))])
        v = sum(a[g]*bra[h]*k[g, h] for g in range(2) for h in range(3))
        ref += wi*np.outer(v, v.conj())
    assert_allclose(depth_response(incoming, outgoing, k, 4.), ref, atol=3e-14)
    so = BlochStates.solve(matrices()[1])
    assert_allclose(so.ket(-z).conj(), exp2(matrices()[1], z)[0], atol=1e-15)


def test_degenerate_modes_and_unsupported_complex_eigenvalues():
    """Solver domain: complex eigenvectors allowed; absorption not implemented."""
    hi = np.eye(2)*.03 + np.array([[0, 1e-14j], [-1e-14j, 0]])
    ho = np.eye(2)*-.07
    k = model_data()[2]
    assert_allclose(depth_response(BlochStates.solve(hi), BlochStates.solve(ho), k, 4.),
                    reference_response(hi, ho, k, 4.), atol=2e-15)
    with pytest.raises(ValueError, match='Hermitian'):
        BlochStates.solve(np.diag([.1+.01j, .2]))


def test_reversal_detector_algebra_integrate_before_percentage():
    """Algebra: no mirror symmetry presumed for arbitrary geometries."""
    from emcd_sim.geometry import VirtualDetector
    q = np.linspace(-1, 1, 17); x, y = np.meshgrid(q, q)
    na, ma = 2 + x*x + .2*y, .1 + .03*x - .02*y
    plus, minus = na + ma, na - ma
    odd, even = (plus-minus)/2, (plus+minus)/2
    t = model_data()[-1]; r = np.outer([1, 1j, .2], np.conj([1, 1j, .2]))
    assert_allclose(intensities_from_response(r, t)+intensities_from_response(r, t.conj()),
                    2*intensities_from_response(r, t.real))
    values=[]; aperture_weights=[]
    for center in ((.25, .3), (.25, -.3)):
        w = VirtualDetector(center, .2).integration_weights(x, y, mode='fractional', subpixels=32)
        aperture_weights.append(w)
        assert np.min(w) >= 0 and np.max(w) <= 1
        integrate = lambda a: float(np.sum(w*a)*(q[1]-q[0])**2)
        values.append((integrate(even), integrate(odd), integrate(plus), integrate(minus)))
    assert_allclose(aperture_weights[0], aperture_weights[1][::-1], atol=0, rtol=0)
    (a, m, ap, am), (b, n, bp, bm) = values
    assert_allclose((ap-am)/2, m)
    assert_allclose(ap-bp, (m-n)+(a-b))
    assert_allclose(100*(ap-bp)/(a+b), 100*(m-n)/(a+b)+100*(a-b)/(a+b))
    assert a > 0 and b > 0
    from emcd_sim.gui.component_display import reversal_signals
    actual, _ = reversal_signals(np.array([ap]), np.array([bp]), np.array([am]), np.array([bm]))
    assert_allclose(actual['D_mag'], [m-n])
    assert_allclose(actual['D_nonmag'], [a-b])
    assert_allclose(actual['D_raw'], [ap-bp])
    assert_allclose(actual['magnetic_only_percent'], [100*(m-n)/(a+b)])
    assert_allclose(actual['nonmagnetic_asymmetry_percent'], [100*(a-b)/(a+b)])
    assert_allclose(actual['emcd_asymmetry_percent'], [100*(ap-bp)/(ap+bp)])


def test_fft_against_independent_dense_exponential_step_convergence():
    """Convergence/solver: explicit DFT and Hermitian 2x2 continuum generator."""
    u = np.array([.31, -.13]); kinetic = np.array([-.07, .12])
    f = np.array([[1, 1], [1, -1]])/np.sqrt(2)
    h = np.diag(kinetic) + f @ np.diag(u) @ f.T
    initial = np.array([1., 0.], complex); thickness = 3.
    expected = exp2(h, thickness) @ initial
    errors=[]
    plan=FFTSplitStep(u, kinetic)
    for n in (12, 24, 48):
        actual=plan.advance(initial, n, thickness/n)
        errors.append(np.linalg.norm(actual-expected))
        assert_allclose(plan.advance(actual, n, -thickness/n), initial, atol=2e-14)
    assert errors[1] < errors[0]/3.9 and errors[2] < errors[1]/3.9


def test_depth_quadrature_converges_independently_of_fft():
    """Convergence: refine depth only, separate from propagation splitting."""
    hi, ho, k, *_ = model_data()
    si, so = BlochStates.solve(hi), BlochStates.solve(ho)
    ref = reference_response(hi, ho, k, 17.)
    errors = [np.linalg.norm(depth_response(si, so, k, 17., method='numerical', depth_steps=n)-ref)
              for n in (33, 65, 129)]
    assert errors[1] < errors[0]/3.9 and errors[2] < errors[1]/3.9


def test_small_fft_double_event_intensity_independent_reference():
    """Solver/convergence: independent DFT Hamiltonians and forward events.

    Fix depth for split-step refinement; then fix the propagation subdivision
    while refining depth. No shared production tensor-contraction reference.
    """
    f = np.array([[1, 1], [1, -1]])/np.sqrt(2)
    ui, di = np.array([.31, -.13]), np.array([-.07, .12])
    uo, do = np.array([-.17, .26]), np.array([.08, -.11])
    hi, ho = np.diag(di)+f@np.diag(ui)@f.T, np.diag(do)+f@np.diag(uo)@f.T
    _, _, k, d, weights, tensor = model_data()
    ref = np.sum(reference_response(hi, ho, k, 3.)*tensor.T).real
    def run(depth, subdivisions):
        z = np.linspace(0, 3., depth); dz = z[1]-z[0]
        pi, po = FFTSplitStep(ui, di), FFTSplitStep(uo, do)
        values = []
        for j in range(depth):
            incoming = pi.advance(np.array([1, 0], complex), j*subdivisions, dz/subdivisions)
            signal = 0.
            for dn, wn in zip(d, weights):
                scattered = np.array([sum(incoming[g]*np.dot(k[g, h], dn.conj()) for g in range(2))
                                      for h in range(2)])
                exit_wave = po.advance(scattered, (depth-1-j)*subdivisions, dz/subdivisions)
                signal += wn*abs(exit_wave[0])**2
            values.append(signal)
        return dz*(sum(values[1:-1])+(values[0]+values[-1])/2)
    # Depth quadrature is independent of the split-step approximation.
    depth_errors=[abs(run(n, 2)-ref) for n in (17, 33, 65)]
    assert depth_errors[1] < depth_errors[0]/3.8
    assert depth_errors[2] < depth_errors[1]/3.8
    assert abs(run(65, 2)-ref)/ref < 1e-4
    # At fixed depth compare with the exact propagator, same trapezoidal rule.
    z = np.linspace(0, 3., 17); exact=[]
    for zi in z:
        a = exp2(hi, zi)[:, 0]; bra = exp2(ho, 3.-zi)[0]
        v = sum(a[g]*bra[h]*k[g, h] for g in range(2) for h in range(2))
        exact.append(sum(wn*abs(np.dot(v, dn.conj()))**2 for dn, wn in zip(d, weights)))
    trap=(z[1]-z[0])*(sum(exact[1:-1])+(exact[0]+exact[-1])/2)
    errors=[abs(run(17, n)-trap) for n in (1, 2, 4)]
    assert errors[1] < errors[0]/3.9 and errors[2] < errors[1]/3.9
