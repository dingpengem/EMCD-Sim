"""Independent hand-calculated references for presentation-only signals."""
import numpy as np
from emcd_sim.gui.component_display import reversal_signals,components,exported_spectra,migrate_display_state


def test_independent_mixed_signal_example():
    s,_=reversal_signals(.65,.45,.55,.55)
    np.testing.assert_allclose([s[k] for k in ('D_mag','D_nonmag','D_raw')],[.1,.1,.2])
    np.testing.assert_allclose(s['emcd_asymmetry_percent'],100*.2/1.1)
    np.testing.assert_allclose(s['magnetic_only_percent'],100*.1/1.1)
    np.testing.assert_allclose(s['D_raw'],s['D_mag']+s['D_nonmag'])


def test_zero_even_difference_still_has_distinct_denominators():
    s,_=reversal_signals(.8,.6,.2,.4)
    assert abs(s['D_nonmag'])<1e-15
    np.testing.assert_allclose(s['emcd_asymmetry_percent'],100*.2/1.4)
    np.testing.assert_allclose(s['magnetic_only_percent'],20)


def test_signed_invalid_and_near_zero():
    s,_=reversal_signals([.45,0,1e-20,np.nan],[.65,0,1e-20,.3],[.55,0,0,.3],[.55,0,0,.3])
    np.testing.assert_allclose(s['emcd_asymmetry_percent'][0],-100*.2/1.1)
    assert np.isnan(s['emcd_asymmetry_percent'][1:]).all()
    np.testing.assert_allclose(s['D_mag'][0],-.1)


def test_legacy_components_alias_and_input_preservation():
    s=dict(I_A_plus=np.array([.65,.8]),I_B_plus=np.array([.45,.6]),
        I_A_minus=np.array([.55,.2]),I_B_minus=np.array([.55,.4]))
    before={k:v.copy() for k,v in s.items()}
    raw,_=components(s);total,_=components(s,'asymmetry');legacy,_=components(s,'relative');out=exported_spectra(s)
    assert list(raw)==['Magnetic','Nonmagnetic'] and list(total)==['EMCD Asymmetry']
    np.testing.assert_array_equal(out['emcd_asymmetry_percent'],out['prb_relative_dichroism_percent'])
    np.testing.assert_array_equal(legacy['Magnetic'],out['magnetic_only_percent'])
    for k,v in before.items():np.testing.assert_array_equal(s[k],v)


def test_legacy_relative_preference_is_never_reinterpreted_as_total():
    original=dict(component_mode='relative',locked=True,energy_ev=831.4778,advanced=False)
    state,notes=migrate_display_state(original)
    assert state['component_mode']=='raw' and state['advanced'] and state['component_diagnostic']=='relative'
    assert state['locked'] and state['energy_ev']==831.4778 and notes
    assert original['component_mode']=='relative'
    state,notes=migrate_display_state(dict(signal_display_schema=2,component_mode='asymmetry',map_signal_mode='asymmetry'))
    assert state['component_mode']=='asymmetry' and state['map_signal_mode']=='asymmetry' and not notes
