"""Roundoff comparisons for the fixed historical Bloch regression fixtures.

See docs/SCIENTIFIC_NUMERICAL_CONTRACT_REVIEW.md, sections D-F. These are
arithmetic comparison envelopes, not discretization errors or physics accuracy
claims. Unchanged arrays and undefined-value masks are still compared exactly.
"""
import numpy as np


def gamma(operations):
    """Standard binary64 rounding accumulation factor, with u = eps/2."""
    nu = operations * np.finfo(np.float64).eps / 2
    return nu / (1 - nu)


def bloch_roundoff(beam_count, depth_count, pixel_count=0):
    """Two equivalent evaluation routes in the investigated small-basis cases.

    A complex beam-pair contraction uses a 4*n*n+8 real accumulation budget.
    Include two n-term complex field formations (4*n+8 each), the quadratic
    response, depth/detector reductions, and eight final scaling operations.
    Count both routes. Independent propagation/Decimal checks in the review
    support this fixture-scoped envelope; it is not a general eigensolver bound.
    """
    amplitude = 4*beam_count**2 + 8 + 2*(4*beam_count + 8)
    return gamma(2*(2*amplitude + depth_count + pixel_count + 8))


def assert_roundoff(actual, expected, allowance, *, label=''):
    """Elementwise absolute budget; retain shape, dtype and nonfinite values."""
    actual, expected = np.asarray(actual), np.asarray(expected)
    assert actual.shape == expected.shape, label+' shape'
    assert actual.dtype == expected.dtype, label+' dtype'
    finite = np.isfinite(expected)
    np.testing.assert_array_equal(actual[~finite], expected[~finite], err_msg=label)
    bound = np.broadcast_to(allowance, expected.shape)[finite]
    assert np.all(np.isfinite(bound) & (bound >= 0)), label+' invalid budget'
    # nextafter implements <=, including exact zero, using assert_array_less.
    np.testing.assert_array_less(abs(actual[finite]-expected[finite]),
                                 np.nextafter(bound, np.inf), err_msg=label)


def linear_signal_scale(spectra, key):
    """Absolute parent intensity of a raw or linear reversal observable."""
    ap, bp, am, bm = [abs(spectra[k]) for k in
        ('I_A_plus', 'I_B_plus', 'I_A_minus', 'I_B_minus')]
    if key.startswith('I_'):
        return abs(spectra[key])
    if key in ('N_A', 'M_A'):
        return (ap+am)/2
    if key in ('N_B', 'M_B'):
        return (bp+bm)/2
    if key in ('D_mag', 'D_nonmag', 'Sigma_ref'):
        return (ap+bp+am+bm)/2
    if key == 'D_raw':
        return ap+bp
    raise KeyError(key)


def _percentage_allowance(spectra, key, relative_budget):
    if key == 'prb_relative_dichroism_percent':
        denominator = spectra['I_A_plus'] + spectra['I_B_plus']
        parent = abs(spectra['I_A_plus']) + abs(spectra['I_B_plus'])
    elif key in ('magnetic_only_percent', 'nonmagnetic_imbalance_percent'):
        denominator = spectra['Sigma_ref']
        parent = linear_signal_scale(spectra, 'Sigma_ref')
    else:
        raise KeyError(key)
    error = relative_budget*parent
    defined = np.isfinite(spectra[key])
    assert np.all(abs(denominator[defined]) > error[defined])
    # Propagate numerator/denominator error before the factor 100; include
    # rounding of the two divisions and percentage multiplications.
    with np.errstate(divide='ignore', invalid='ignore'):
        return (100*(error + abs(spectra[key]/100)*error)
                / (abs(denominator)-error) + gamma(4)*abs(spectra[key]))


def assert_bloch_observables(actual, expected, cfg):
    """Compare only historical optimized Bloch outputs, including all maps."""
    budget = bloch_roundoff(expected['amplitudes'].shape[-1], cfg.depth, cfg.grid**2)
    x, y = actual['spectra'], expected['spectra']
    assert x.keys() == y.keys()
    for key in y:
        if key == 'energy_ev':
            np.testing.assert_array_equal(x[key], y[key])
        else:
            allowance = (_percentage_allowance(y, key, budget) if key.endswith('_percent')
                         else budget*linear_signal_scale(y, key))
            assert_roundoff(x[key], y[key], allowance, label='Bloch spectrum '+key)
    assert actual['maps'].keys() == expected['maps'].keys()
    count = len(y)
    for edge, fields in expected['maps'].items():
        parents = (abs(fields['I_plus'])+abs(fields['I_minus']))/2
        scales = dict(I_plus=abs(fields['I_plus']), I_minus=abs(fields['I_minus']),
                      I_mag=parents, I_nonmag=parents)
        # Paired fields copy/mirror the calculated maps before taking spatial
        # differences; retain their exact NaN support and propagate both parents.
        p,m=abs(fields['I_plus']),abs(fields['I_minus'])
        scales.update(I_A_plus=p,I_B_plus_paired=p[::-1],I_A_minus=m,
                      I_B_minus_paired=m[::-1],D_raw=p+p[::-1],
                      D_mag=parents+parents[::-1],D_nonmag=parents+parents[::-1])
        assert actual['maps'][edge].keys() == fields.keys()
        for key, value in fields.items():
            assert_roundoff(actual['maps'][edge][key], value, budget*scales[key],
                            label='Bloch map '+edge+'/'+key)
            count += 1
    return count
