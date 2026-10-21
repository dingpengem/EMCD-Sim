"""Shared current regression fixtures; no CLI, research scan or stored-data rewrite."""
from dataclasses import dataclass
from pathlib import Path
import hashlib,json
import numpy as np
from PySide6 import QtWidgets
from emcd_sim.mdff_tensor import DipoleTensor,TransitionDataset
from emcd_sim.single_channeling_tensor import run_tensor_single_channeling
from emcd_sim.xmcd_effective_mdff import effective_tensor_from_xmcd
from emcd_sim.gui.runtime import LABEL,build_info

def release_controls(window, app):
    """Exercise the actual release widgets without starting a worker."""
    assert window.cancel_button.text()=='Cancel' and not window.cancel_button.isEnabled()
    assert window.numerical_mode.currentIndex()==0
    window.model_box.setCurrentIndex(1)
    for index in (0,1,2):
        window.propagation_box.setCurrentIndex(index)
        assert not window._numerical_error
        assert ('FFT grid' in window.numerical_values.text())==(index!=0)
    window.numerical_mode.setCurrentIndex(1)
    window.spin['depth'].setValue(33)
    manual=window.numerical_snapshot()
    window.numerical_mode.setCurrentIndex(0)
    window.numerical_mode.setCurrentIndex(1)
    assert window.numerical_snapshot()==manual
    assert not window.ms_settings_group.isHidden()
    window.propagation_box.setCurrentIndex(0)
    assert window.ms_settings_group.isHidden()
    window.ax.set(xlim=(-.3,.7),ylim=(-.2,.8))
    limits=(window.ax.get_xlim(),window.ax.get_ylim())
    window.basis_view_button.click()
    assert window.basis_view_button.text()=='Restore previous view'
    window.basis_view_button.click()
    assert (window.ax.get_xlim(),window.ax.get_ylim())==limits
    assert window.spin['grid'].value()==97 and window.memory_budget.currentData()==2048
    independent=tuple(window.spin[k].value() for k in ('fft_grid','subpixels','halfwidth'))
    for i,n in enumerate((33,97,193)):
        window.angular_resolution.setCurrentIndex(i)
        assert window.spin['grid'].value()==n
        assert independent==tuple(window.spin[k].value() for k in ('fft_grid','subpixels','halfwidth'))
    window.spin['grid'].setValue(65)
    assert window.angular_resolution.currentText()=='Custom'
    window.memory_budget.setCurrentIndex(window.memory_budget.findData(512))
    window.new_project()
    assert window.numerical_mode.currentIndex()==0
    assert window.spin['grid'].value()==97 and window.memory_budget.currentData()==2048
    # Show the same provenance text as the application's About action.
    box=QtWidgets.QMessageBox(window);box.setWindowTitle(LABEL)
    box.setText(json.dumps(build_info(),indent=2));box.show();app.processEvents()
    assert build_info()['application_version'] in box.text()
    box.close()
    return dict(presets=[33,97,193],custom=65,new_project_grid=97,
        new_project_memory_mib=2048,independent_fft_subpixels=True,about_provenance=True,
        automatic_manual_roundtrip=True,method_visibility=True,reversible_basis_view=True,
        cancellation_control_present=True)

FORWARD_PATHS=('emcd_sim.physical_elastic.PhysicalElasticModel.amplitudes','emcd_sim.multislice_reference.fft_multislice_ni',
    'emcd_sim.gui.emcd_forward.calculate','emcd_sim.gui.emcd_forward.tensors','emcd_sim.gui.propagation.propagate',
    'emcd_sim.single_channeling_tensor.run_tensor_with_coherence','emcd_sim.single_channeling_tensor.run_tensor_with_coherence',
    'emcd_sim.gui.stage_b.EMCDWorker.run','emcd_sim.gui.app.PreviewWorker.run')

def fingerprints(result):
    arrays={}
    for name,r in result['methods'].items():
        arrays.update({name+'__'+k:v for k,v in dict(r['spectra'],coherence=r['coherence'],amplitudes=r['amplitudes'],qx=r['qx'],qy=r['qy']).items()})
        arrays.update({name+'__'+e+'__'+k:v for e,fields in r['maps'].items() for k,v in fields.items()})
        arrays.update({name+'__weight_'+k:v for k,v in r['weights'].items()})
    return {key:hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest() for key,a in arrays.items()}

def toy_transitions() -> TransitionDataset:
    """Synthetic mathematical chirality example, NOT Ni DFT or experimental data."""
    # A complex in-plane dipole represents a circular/helicity-sensitive mode.
    # L3 and L2 are assigned opposite handedness only to exercise the algebra.
    return TransitionDataset(
        energy_ev=np.array([852.7, 870.0, 852.7, 870.0]),
        dipoles_angstrom=np.array([[1,1j,0],[1,-1j,0],[0,0,.65],[0,0,.45]],complex),
        weights=np.array([1,.5,.3,.3]),
        edge=np.array(["L3","L2","L3","L2"]),
        site=np.array(["Ni_demo"]*4),
        source="SYNTHETIC toy transitions: NOT computed from Ni wavefunctions",
    )

def normalized_signal(numerator, denominator, rtol=1e-12):
    """NaN below rtol times the peak denominator; return validity explicitly."""
    denominator = np.asarray(denominator, dtype=float)
    threshold = rtol * np.max(np.abs(denominator))
    valid = np.isfinite(denominator) & (denominator > threshold)
    return np.divide(numerator, denominator, out=np.full_like(denominator, np.nan),
                     where=valid), valid

def parity_spectra(plus, minus):
    """Use physical aperture groups and a common reversal-even denominator."""
    if not np.array_equal(plus.energy_ev, minus.energy_ev):
        raise ValueError('Reversal energy grids must match')
    a, b = plus.chiral_spectrum('A'), plus.chiral_spectrum('B')
    c, d = minus.chiral_spectrum('A'), minus.chiral_spectrum('B')
    dp, dm = a-b, c-d
    sp, sm = a+b, c+d
    odd, even, ref = (dp-dm)/2, (dp+dm)/2, (sp+sm)/2
    rawp, vp = normalized_signal(dp, sp)
    rawm, vm = normalized_signal(dm, sm)
    ao, valid = normalized_signal(odd, ref)
    ae, _ = normalized_signal(even, ref)
    return dict(energy_ev=plus.energy_ev, I_A_plus=a, I_B_plus=b,
                I_A_minus=c, I_B_minus=d, delta_plus=dp, delta_minus=dm,
                delta_odd=odd, delta_even=even, sigma_plus=sp, sigma_minus=sm,
                sigma_ref=ref, A_raw_plus=rawp, A_raw_minus=rawm,
                A_odd=ao, A_even=ae, valid=valid,
                valid_raw_plus=vp, valid_raw_minus=vm)

@dataclass
class ReversalResult:
    spectra: dict
    maps: dict
    tensor_sources: tuple[str, str]

def run_xmcd_reversal(model, xmcd_file, energy_ev=None, *, eta=1., beta=1.,
                      thickness_nm=30., grid_size=65, depth_steps=64,
                      l3_energy_ev=852.7, l2_energy_ev=870.,
                      integration_mode="binary", aperture_subpixels=64):
    """Pair +/-eta on the identical model, grid and source normalization.

    Only the effective imaginary antisymmetric tensor changes. This operation
    is not a prescription for reversal of an arbitrary external DFT tensor.
    """
    tensors = [effective_tensor_from_xmcd(xmcd_file, energy_ev, eta=sign*eta,
                                         beta=beta) for sign in (1, -1)]
    options = dict(thickness_nm=thickness_nm, grid_size=grid_size,
                   depth_steps=depth_steps, integration_mode=integration_mode,
                   aperture_subpixels=aperture_subpixels)
    plus, minus = [run_tensor_single_channeling(model, t, **options,
                        reference_energy_ev=l3_energy_ev) for t in tensors]
    maps = {}
    for edge, reference in [('L3', l3_energy_ev), ('L2', l2_energy_ev)]:
        index = int(np.argmin(abs(tensors[0].energy_ev-reference)))
        selected = float(tensors[0].energy_ev[index])
        if edge == 'L3':
            rp, rm = plus, minus
        else:
            # Two adjacent samples satisfy DipoleTensor's energy-grid contract.
            start = min(index, len(tensors[0].energy_ev)-2)
            subset = [DipoleTensor(t.energy_ev[start:start+2],
                        t.tensor_angstrom2_per_ev[start:start+2], t.source) for t in tensors]
            rp, rm = [run_tensor_single_channeling(model, t, **options,
                        reference_energy_ev=selected) for t in subset]
        ip = rp.nonmag_map_at_l3 + rp.magnetic_map_at_l3
        im = rm.nonmag_map_at_l3 + rm.magnetic_map_at_l3
        maps[edge] = dict(energy_ev=selected, qx_inv_angstrom=rp.qx_angstrom_inv,
                         qy_inv_angstrom=rp.qy_angstrom_inv,
                         I_plus=ip, I_minus=im, I_odd=(ip-im)/2, I_even=(ip+im)/2)
    return ReversalResult(parity_spectra(plus, minus), maps,
                          tuple(t.source for t in tensors))

def _compare_spots(bloch_hkl, bloch_intensity, fft_hkl, fft_intensity) -> float:
    b = {tuple(h): float(v) for h, v in zip(bloch_hkl, bloch_intensity)}
    f = {tuple(h): float(v) for h, v in zip(fft_hkl, fft_intensity)}
    return 0.5*sum(abs(b.get(k, 0.) - f.get(k, 0.)) for k in b.keys() | f.keys())

def diffraction_preset(name,crystal,acceleration_kv=200,max_beams=25):
    from types import SimpleNamespace
    from emcd_sim.elastic import BeamSet
    from emcd_sim.physical_elastic import bragg_tilt_mrad
    if name=='zone-axis':
        beams=BeamSet.zolz(crystal,1.2,max_beams);tilt=(0.,0.)
    elif name=='two-beam':
        beams=BeamSet(((0,0,0),(2,0,0)));tilt=(-bragg_tilt_mrad(crystal,(2,0,0),acceleration_kv),25.)
    else:
        beams=BeamSet.systematic_row(3)
        tilt=(-bragg_tilt_mrad(crystal,(2,0,0),acceleration_kv) if name=='near-2bc' else 0.,25.)
    return SimpleNamespace(beams=beams,tilt_mrad_xy=tilt)
