"""Audit does not confer quantitative credentials on a test dataset."""
import json
import numpy as np
import pytest
from emcd_sim.mdff_tensor import TransitionDataset
from emcd_sim.ni_data_audit import audit_metallic_ni_transitions
from emcd_sim.ni_local_mdff import ni_local_transitions


def sample_provenance(**changes):
    data = dict(material="Ni", phase="fcc_metal", absorber="Ni", edges=["L3", "L2"],
                method="spin-polarized all-electron DFT", code="SOURCE_NOT_YET_VERIFIED",
                code_version="external", core_spin_orbit=True, spin_polarized=True,
                data_type="complex_length_gauge_dipoles", dipole_convention="<i|r|f>",
                dipole_units="angstrom", complex_phase_preserved=True,
                weights_definition="k weights times final-state vacancies", core_state_definition="2p j resolved",
                k_point_definition="explicit mesh and weights", reference_url="https://example.org/not_a_real_source",
                citation="TEST_CASE_NOT_PHYSICS_VALIDATION", input_description="generated test transition")
    data.update(changes)
    return data


def dataset_file(tmp_path, source="MOCK_TEST_ONLY_CONSISTENT_FORMAT"):
    ds=TransitionDataset(np.array([852.7,870.]), np.array([[1,1j,0],[1,-1j,0]],complex),
                         np.array([0.2,0.4]),np.array(["L3","L2"]),np.array(["Ni1","Ni1"]),source)
    f=tmp_path/"transitions.npz";ds.save_npz(f);return f


def meta_file(tmp_path, **kw):
    f=tmp_path/"provenance.json";f.write_text(json.dumps(sample_provenance(**kw)),encoding="utf-8");return f


def test_audit_checks_schema_but_never_claims_physics_validation(tmp_path):
    info=audit_metallic_ni_transitions(dataset_file(tmp_path),meta_file(tmp_path))
    assert info["transition_count"]==2
    assert len(info["input_sha256"])==64
    assert info["quantitative_Ni_certified"] is False
    assert "NOT_physics_validated" in info["status"]


def test_rejects_nio_instead_of_metal(tmp_path):
    with pytest.raises(ValueError,match="fcc_metal"):
        audit_metallic_ni_transitions(dataset_file(tmp_path),meta_file(tmp_path,phase="NiO"))


def test_rejects_unpolarized_or_missing_core_soc(tmp_path):
    with pytest.raises(ValueError,match="core_spin_orbit"):
        audit_metallic_ni_transitions(dataset_file(tmp_path),meta_file(tmp_path,core_spin_orbit=False))


def test_rejects_intensity_instead_of_complex_transition(tmp_path):
    with pytest.raises(ValueError,match="data_type"):
        audit_metallic_ni_transitions(dataset_file(tmp_path),meta_file(tmp_path,data_type="ELNES_intensity"))


def test_rejects_non_dft_dataset_even_with_misleading_metadata(tmp_path):
    ds=ni_local_transitions()
    p=tmp_path/"local.npz";ds.save_npz(p)
    with pytest.raises(ValueError,match="illustrative/non-DFT"):
        audit_metallic_ni_transitions(p,meta_file(tmp_path))


def test_rejects_loss_of_complex_phase(tmp_path):
    p=dataset_file(tmp_path)
    with np.load(p,allow_pickle=False) as f:
        data={k:f[k] for k in f.files}
    data["dipoles_angstrom"]=data["dipoles_angstrom"].real.astype(complex)
    np.savez_compressed(p,**data)
    with pytest.raises(ValueError,match="imaginary"):
        audit_metallic_ni_transitions(p,meta_file(tmp_path))
