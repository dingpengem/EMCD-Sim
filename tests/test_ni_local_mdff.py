"""Reference identities for NON-DFT local 2p->3d MDFF; no Ni calibration claim."""
import json
import subprocess
import sys
from dataclasses import replace

import numpy as np
import pytest

from emcd_sim.ni_local_mdff import (
    BOHR_ANGSTROM, NiLocalConfig, cubic_orbital_coefficients,
    hydrogenic_radial_dipole_angstrom, ni_local_transitions,
)
from emcd_sim.mdff_tensor import dipole_tensor_from_transitions, TransitionDataset


def test_hydrogenic_radial_normalization_and_analytic_integral():
    zp, zd = 25., 9.
    r = np.linspace(0, 12, 120001)
    ap, ad = zp/BOHR_ANGSTROM, 2*zd/(3*BOHR_ANGSTROM)
    rp = ap**2.5/np.sqrt(24) * r * np.exp(-ap*r/2)
    rd = ad**3.5/np.sqrt(720) * r*r * np.exp(-ad*r/2)
    assert np.trapezoid(rp*rp*r*r, r) == pytest.approx(1, abs=1e-7)
    assert np.trapezoid(rd*rd*r*r, r) == pytest.approx(1, abs=1e-7)
    numeric = np.trapezoid(rp*rd*r**3, r)
    assert hydrogenic_radial_dipole_angstrom(zp,zd) == pytest.approx(numeric, rel=1e-7)


def test_real_cubic_orbitals_orthonormal():
    vectors = np.stack(list(cubic_orbital_coefficients().values()))
    assert np.allclose(vectors @ vectors.conj().T, np.eye(5), atol=1e-14)


def _tensor(cfg):
    ds = ni_local_transitions(cfg)
    assert set(ds.edge)=={'L3','L2'}
    t = dipole_tensor_from_transitions(ds,np.linspace(847,876,117),0.6)
    assert np.linalg.eigvalsh(t.tensor_angstrom2_per_ev).min() >= -1e-12
    return t.tensor_angstrom2_per_ev


def test_spin_reversal_zero_crystal_field_and_exchange():
    cfg = NiLocalConfig(crystal_field_10dq_ev=0,exchange_split_ev=0,
                        eg_up_holes=.1, t2g_up_holes=.1,
                        eg_down_holes=.6, t2g_down_holes=.6)
    reverse=replace(cfg,eg_up_holes=.6,t2g_up_holes=.6,
                    eg_down_holes=.1,t2g_down_holes=.1)
    a,b=_tensor(cfg),_tensor(reverse)
    assert np.allclose(a.real,b.real,atol=1e-12)
    assert np.allclose(a.imag,-b.imag,atol=1e-12)
    assert np.max(np.abs(a.imag)) > 1e-7


def test_zero_spin_polarization_no_chiral_signal():
    c=NiLocalConfig(eg_up_holes=.4,eg_down_holes=.4,
                    t2g_up_holes=.4,t2g_down_holes=.4,exchange_split_ev=0)
    tensor=_tensor(c)
    assert np.max(np.abs(tensor.imag)) < 1e-12


def test_moment_direction_not_assumed_from_spin_exchange():
    cfg=NiLocalConfig()
    ds=ni_local_transitions(cfg)
    assert 'NON_DFT' in ds.source
    assert len(ds.energy_ev)>10
    assert np.ptp(ds.energy_ev[ds.edge=='L3'])>0
    with pytest.raises(ValueError):
        ni_local_transitions(replace(cfg,eg_up_holes=1.01))
    with pytest.raises(ValueError):
        hydrogenic_radial_dipole_angstrom(0,10)


def test_npz_roundtrip_and_cli_windows_safe(tmp_path):
    ds=ni_local_transitions()
    p=tmp_path/'Ni local transitions.npz'
    ds.save_npz(p)
    assert np.allclose(TransitionDataset.load_npz(p).dipoles_angstrom,ds.dipoles_angstrom)
    target=tmp_path/'Ni local test with spaces'
    r=subprocess.run([sys.executable,'-m','emcd_sim.ni_local_mdff',
                      '--output',str(target)],check=True,capture_output=True,text=True,timeout=90)
    summary=json.loads(r.stdout)
    assert summary['quantitative_Ni'] is False
    meta=json.loads((target/'metadata.json').read_text(encoding='utf-8'))
    assert not meta['is_dft'] and not meta['is_atomic_multiplet']
    assert (target/'mdff_tensor.png').is_file()


def test_tabulated_atomic_hf_radial_provider():
    from emcd_sim.ni_local_mdff import radial_dipole_from_table
    zp,zd=25.,9.
    r=np.linspace(0,8,160001)
    ap,ad=zp/BOHR_ANGSTROM,2*zd/(3*BOHR_ANGSTROM)
    rp=ap**2.5/np.sqrt(24)*r*np.exp(-ap*r/2)
    rd=ad**3.5/np.sqrt(720)*r*r*np.exp(-ad*r/2)
    ref=hydrogenic_radial_dipole_angstrom(zp,zd)
    assert radial_dipole_from_table(r,2*rp,4*rd) == pytest.approx(ref,rel=1e-7)
    assert radial_dipole_from_table(r,2*rp,-4*rd) == pytest.approx(-ref,rel=1e-7)
    with pytest.raises(ValueError,match="ascending"):
        radial_dipole_from_table(r[::-1],rp,rd)


def test_radial_csv_cli(tmp_path):
    r=np.linspace(0,8,3001)
    ap,ad=25/BOHR_ANGSTROM,2*9/(3*BOHR_ANGSTROM)
    rp=ap**2.5/np.sqrt(24)*r*np.exp(-ap*r/2)
    rd=ad**3.5/np.sqrt(720)*r*r*np.exp(-ad*r/2)
    f=tmp_path/'Radial waves.csv'
    np.savetxt(f,np.column_stack((r,rp,rd)),delimiter=',',header='radius_angstrom,R_2p,R_3d',comments='')
    output=tmp_path/'With external radial'
    subprocess.run([sys.executable,'-m','emcd_sim.ni_local_mdff',
                    '--radial-table',str(f),'--output',str(output)],
                   check=True,timeout=90,capture_output=True,text=True)
    m=json.loads((output/'metadata.json').read_text())
    assert m['radial_source']=='tabulated_full_R'
    assert m['radial_dipole_angstrom'] == pytest.approx(hydrogenic_radial_dipole_angstrom(25,9),rel=1e-5)
