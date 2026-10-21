"""Ni core-SOC angular momentum reference, NOT a DFT benchmark."""
import json
import subprocess
import sys
from dataclasses import replace

import numpy as np
import pytest

from emcd_sim.mdff_tensor import dipole_tensor_from_transitions, TransitionDataset
from emcd_sim.ni_local_mdff import core_spinor_amplitude, ni_2p_to_3d_dipole
from emcd_sim.transition_csv import import_transition_csv


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
