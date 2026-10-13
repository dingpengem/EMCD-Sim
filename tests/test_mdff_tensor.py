"""Focused physics checks for a transition-derived *dipole* MDFF."""
import json
import subprocess
import sys
import numpy as np
import pytest

from emcd_sim.mdff_tensor import (
    TransitionDataset, dipole_tensor_from_transitions, cycles_to_angular_q,
)
from emcd_sim.mdff_reference import toy_transitions


def test_mdff_hermitian_psd_and_conjugate_symmetry():
    data = toy_transitions()
    result = dipole_tensor_from_transitions(data, np.linspace(848,875,101), 0.9)
    t = result.tensor_angstrom2_per_ev
    assert np.allclose(t,t.swapaxes(-1,-2).conj(),atol=1e-13)
    assert np.linalg.eigvalsh(t).min() >= -1e-13
    q = np.array([.3,-.2,.5]); qp=np.array([.1,.4,.2])
    assert np.allclose(result.mdff(q,qp),result.mdff(qp,q).conj())
    assert result.mdff(q,q).real.min() >= -1e-14


def test_chirality_flips_under_complex_conjugation():
    data=toy_transitions()
    flipped=TransitionDataset(data.energy_ev,data.dipoles_angstrom.conj(),data.weights,
                               data.edge,data.site,"Toy magnetization reversed")
    grid=np.array([852.7,870.])
    x=dipole_tensor_from_transitions(data,grid,.6)
    y=dipole_tensor_from_transitions(flipped,grid,.6)
    assert np.allclose(x.tensor_angstrom2_per_ev.real,y.tensor_angstrom2_per_ev.real)
    assert np.allclose(x.tensor_angstrom2_per_ev.imag,-y.tensor_angstrom2_per_ev.imag)
    assert x.tensor_angstrom2_per_ev[0,0,1].imag < 0
    assert x.tensor_angstrom2_per_ev[1,0,1].imag > 0


def test_transition_weight_and_site_selection():
    data=toy_transitions(); energy=np.array([852.7,870.])
    l3=dipole_tensor_from_transitions(data,energy,1.0,edge="L3",site="Ni_demo")
    all_=dipole_tensor_from_transitions(data,energy,1.0)
    assert np.trace(all_.tensor_angstrom2_per_ev[0]).real >= np.trace(l3.tensor_angstrom2_per_ev[0]).real
    with pytest.raises(ValueError,match="No transitions"):
        dipole_tensor_from_transitions(data,energy,1.0,site="unknown")


def test_npz_roundtrip_and_unit_convention(tmp_path):
    ds=toy_transitions()
    p=tmp_path/"Ni toy transitions.npz"
    ds.save_npz(p)
    loaded=TransitionDataset.load_npz(p)
    assert np.array_equal(loaded.dipoles_angstrom,ds.dipoles_angstrom)
    assert np.allclose(cycles_to_angular_q(np.array([1.,0,0])),[2*np.pi,0,0])
    with np.load(p,allow_pickle=False) as f:
        contents={k:f[k] for k in f.files}
    contents['convention']=np.array('wrong')
    np.savez(tmp_path/'wrong.npz',**contents)
    with pytest.raises(ValueError,match="convention"):
        TransitionDataset.load_npz(tmp_path/'wrong.npz')


def test_reject_invalid_amplitudes_and_weights():
    ds=toy_transitions()
    w=ds.weights.copy();w[0]=-1
    with pytest.raises(ValueError, match="nonnegative"):
        TransitionDataset(ds.energy_ev,ds.dipoles_angstrom,w,ds.edge,ds.site,"test")
    d=ds.dipoles_angstrom.copy();d[0,1]=np.nan
    with pytest.raises(ValueError, match="finite"):
        TransitionDataset(ds.energy_ev,d,ds.weights,ds.edge,ds.site,"test")


def test_reference_cli_writes_portable_outputs(tmp_path):
    out=tmp_path/"Ni MDFF demo"
    result=subprocess.run([sys.executable,"-m","emcd_sim.mdff_reference","--toy",
        "--output",str(out)],capture_output=True,text=True,timeout=90,check=True)
    metadata=json.loads((out/"metadata.json").read_text(encoding="utf-8"))
    assert metadata["toy"] and metadata["quantitative_Ni"] is False
    assert (out/"mdff_tensor.png").exists() and (out/"mdff_tensor.npz").exists()
    assert "quantitative_Ni" in result.stdout
