"""Independent reversal decomposition and explicit denominator conventions."""
import importlib.util
from pathlib import Path
import numpy as np

spec=importlib.util.spec_from_file_location('audit',Path(__file__).parents[1]/'scripts/audit_ni_thickness.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)


def test_known_reversal_states_keep_denominators_distinct():
    raw=np.array([[12.,7.,8.,9.]])
    c=audit.components(raw)
    np.testing.assert_array_equal(c['D_mag'],[3.])
    np.testing.assert_array_equal(c['D_nonmag'],[2.])
    np.testing.assert_array_equal(c['D_raw'],[5.])
    np.testing.assert_allclose(c['A_raw_plus'],[500/19])
    np.testing.assert_allclose(c['A_raw_even'],[500/18])
    np.testing.assert_allclose(c['A_raw_even'],c['A_mag']+c['A_nonmag'])


def test_reversal_parity_zero_boundary_and_no_mutation():
    raw=np.array([[0.,0.,0.,0.],[12.,7.,8.,9.]])
    original=raw.copy();c=audit.components(raw);r=audit.components(raw[:,[2,3,0,1]])
    np.testing.assert_array_equal(raw,original)
    np.testing.assert_array_equal(c['D_mag'],-r['D_mag'])
    np.testing.assert_array_equal(c['D_nonmag'],r['D_nonmag'])
    assert np.isnan(c['A_raw_plus'][0]) and np.isnan(c['R_contam'][0])


def test_contamination_is_not_capped():
    c=audit.components(np.array([[101.,1.,99.,1.]]))
    assert c['R_contam'][0]==99
