"""Aperture flux, alias maps and raw-array preservation across detector reduction."""
from types import SimpleNamespace

import numpy as np

from emcd_sim.detector_signals import integrate_detector_block, reversal_components


def test_fractional_aperture_flux_and_selected_energy_aliases():
    qx,qy=np.meshgrid(np.arange(3)*.5,np.arange(3)*.5)
    weights={name:np.zeros((3,3)) for name in ('A','B')}
    weights['A'][0,0]=.25;weights['A'][1,1]=1.
    weights['B'][0,2]=.5;weights['B'][2,2]=.75
    support=np.logical_or(weights['A'].ravel()>0,weights['B'].ravel()>0)
    plus=np.array([[4.,8.,12.,16.],[8.,12.,16.,20.]])
    raw=dict(plus=plus.copy(),minus=plus/2)
    original={key:value.copy() for key,value in raw.items()}
    cfg=SimpleNamespace(angular_maps=True,selected_edges=(('edge',10.),('alias',10.)))
    result=integrate_detector_block(raw,cfg,np.array([10.,11.]),qx,qy,weights,support)
    np.testing.assert_array_equal(result['spectra']['I_A_plus'],[3.25,4.5])
    np.testing.assert_array_equal(result['spectra']['I_B_plus'],[4.,5.25])
    plane=np.array([[4.,0.,8.],[0.,12.,0.],[0.,0.,16.]])
    np.testing.assert_array_equal(result['maps']['edge']['I_plus'],plane)
    np.testing.assert_array_equal(result['maps']['alias']['I_plus'],plane)
    assert not np.shares_memory(result['maps']['edge']['I_plus'],result['maps']['alias']['I_plus'])
    for key in raw:np.testing.assert_array_equal(raw[key],original[key])
    s=result['spectra']
    np.testing.assert_array_equal(s['D_raw'],s['D_mag']+s['D_nonmag'])
    np.testing.assert_array_equal(s['Sigma_ref'],.75*(s['I_A_plus']+s['I_B_plus']))


def test_reversal_changes_only_odd_components_and_keeps_raw_inputs():
    energy=np.array([710.,723.])
    spectra=dict(I_A_plus=np.array([10.,20.]),I_A_minus=np.array([6.,12.]),
                 I_B_plus=np.array([8.,16.]),I_B_minus=np.array([12.,24.]))
    originals={key:value.copy() for key,value in spectra.items()}
    result=reversal_components(spectra,energy)
    reversed_inputs={key.replace('plus','STATE').replace('minus','plus').replace('STATE','minus'):value
                     for key,value in spectra.items()}
    reverse=reversal_components(reversed_inputs,energy)
    for key in ('N_A','N_B','D_nonmag','Sigma_ref'):
        np.testing.assert_array_equal(result[key],reverse[key])
    for key in ('M_A','M_B','D_mag'):
        np.testing.assert_array_equal(result[key],-reverse[key])
    assert spectra.keys()==originals.keys()
    for key in spectra:np.testing.assert_array_equal(spectra[key],originals[key])
