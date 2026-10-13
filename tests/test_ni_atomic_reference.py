"""Ni core-SOC angular momentum reference, NOT a DFT benchmark."""
import json
import subprocess
import sys
from dataclasses import replace

import numpy as np
import pytest

from emcd_sim.mdff_tensor import dipole_tensor_from_transitions, TransitionDataset
from emcd_sim.ni_atomic_reference import (
    NiAtomicReferenceConfig, ni_atomic_transitions, core_spinor_amplitude,
    ni_2p_to_3d_dipole,
)
from emcd_sim.transition_csv import import_transition_csv


def _tensor(cfg):
    ds = ni_atomic_transitions(cfg)
    return dipole_tensor_from_transitions(ds, np.array([852.7, 870.0]), .6)


def test_core_soc_spinors_are_normalized():
    for j2 in (1, 3):
        for mj2 in range(-j2,j2+1,2):
            probabilities = [core_spinor_amplitude(j2,mj2,ms2)**2 for ms2 in (1,-1)]
            assert sum(probabilities) == pytest.approx(1.0)


def test_electric_dipole_selection_rule():
    # j=3/2, mj=3/2 is the pure ml=+1,spin=up core state.
    assert np.allclose(ni_2p_to_3d_dipole(3,3,-2,1),0)
    assert np.linalg.norm(ni_2p_to_3d_dipole(3,3,2,1)) > 0
    # spin-down is absent in the stretched core state.
    assert np.allclose(ni_2p_to_3d_dipole(3,3,2,-1),0)


def test_unpolarized_model_has_zero_chirality():
    t = _tensor(NiAtomicReferenceConfig(spin_up_hole_weight=.3,spin_down_hole_weight=.3))
    assert np.allclose(t.tensor_angstrom2_per_ev.imag,0,atol=1e-14)
    assert np.linalg.eigvalsh(t.tensor_angstrom2_per_ev).min() >= -1e-13


def test_spin_reversal_flips_chiral_but_not_nonmagnetic():
    p = _tensor(NiAtomicReferenceConfig(spin_up_hole_weight=.1,spin_down_hole_weight=.6)).tensor_angstrom2_per_ev
    m = _tensor(NiAtomicReferenceConfig(spin_up_hole_weight=.6,spin_down_hole_weight=.1)).tensor_angstrom2_per_ev
    assert np.allclose(p.real,m.real,rtol=1e-12,atol=1e-12)
    assert np.allclose(p.imag,-m.imag,rtol=1e-12,atol=1e-12)
    assert abs(p[0,0,1].imag) > 1e-4
    assert p[0,0,1].imag * p[1,0,1].imag < 0  # L3 and L2 chirality opposite


def test_core_statistical_branch_ratio_and_radial_scale():
    cfg=NiAtomicReferenceConfig(spin_up_hole_weight=.3,spin_down_hole_weight=.3)
    t=_tensor(cfg).tensor_angstrom2_per_ev
    assert np.trace(t[0]).real / np.trace(t[1]).real == pytest.approx(2, rel=1e-10)
    t2=_tensor(replace(cfg,radial_dipole_angstrom=2)).tensor_angstrom2_per_ev
    assert np.allclose(t2,4*t)


def test_atomic_dataset_has_explicit_unverified_provenance(tmp_path):
    dataset=ni_atomic_transitions()
    assert set(dataset.edge)=={"L3","L2"}
    assert set(dataset.site)=={"Ni_atomic_angular"}
    assert "NOT_DFT" in dataset.source
    path=tmp_path/"atomic transitions.npz"
    dataset.save_npz(path)
    loaded=TransitionDataset.load_npz(path)
    assert np.allclose(loaded.dipoles_angstrom,dataset.dipoles_angstrom)


def test_reject_invalid_config():
    with pytest.raises(ValueError):
        ni_atomic_transitions(NiAtomicReferenceConfig(spin_up_hole_weight=1.2))
    with pytest.raises(ValueError):
        ni_atomic_transitions(NiAtomicReferenceConfig(radial_dipole_angstrom=0))


def test_portable_csv_import_and_conjugation(tmp_path):
    path=tmp_path/"transitions with spaces.csv"
    path.write_text("energy_ev,dx_re,dx_im,dy_re,dy_im,dz_re,dz_im,weight,edge,site\n"
                    "852.7,1,2,3,4,0,0,0.2,L3,Ni1\n",encoding="utf-8")
    a=import_transition_csv(path,source="calculated reference",amplitude_order="initial_bra")
    b=import_transition_csv(path,source="calculated reference",amplitude_order="final_bra")
    assert a.dipoles_angstrom[0,0]==1+2j
    assert np.allclose(a.dipoles_angstrom,b.dipoles_angstrom.conj())
    assert a.weights[0]==pytest.approx(.2)
    assert "calculated reference" in a.source


def test_csv_invalid_fields_rejected(tmp_path):
    p=tmp_path/"bad.csv";p.write_text("energy_ev,weight\n850,.2\n")
    with pytest.raises(ValueError,match="requires columns"):
        import_transition_csv(p,source="x")
    with pytest.raises(ValueError,match="nonempty"):
        import_transition_csv(p,source="")


def test_cli_atomic_and_csv_run_on_platform(tmp_path):
    directory=tmp_path/"Ni atomic demo"
    proc=subprocess.run([sys.executable,"-m","emcd_sim.ni_atomic_reference",
        "--output",str(directory)],capture_output=True,text=True,check=True,timeout=90)
    assert json.loads(proc.stdout)["quantitative_ni"] is False
    metadata=json.loads((directory/"metadata.json").read_text(encoding="utf-8"))
    assert metadata["not_dft"]
    assert (directory/"ni_atomic_tensor.png").exists()
    assert (directory/"ni_atomic_tensor.npz").exists()
