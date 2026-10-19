"""Verify actual complete scans, integrated observables and the conditional gate."""
from pathlib import Path
import csv,json,hashlib,subprocess
import numpy as np
import pytest
from numpy.testing import assert_allclose
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/ni_double_channeling_full_benchmark'
pytestmark=pytest.mark.skipif(not (OUT/'study_metadata.json').exists(),reason='Full benchmark outputs are not complete')


def test_complete_thickness_data_and_integral_based_percentages():
    for zone in ('001','017'):
        with np.load(OUT/zone/'results.npz',allow_pickle=False) as f:
            assert_allclose(f['thickness_nm'],np.arange(0,101,2),atol=0,rtol=0)
            assert f['raw'].shape==(51,4,2,4)
            assert f['raw'].dtype==np.float64 and np.isfinite(f['raw']).all()
            assert f['raw'].min()>=0
            assert_allclose(f['raw'][0],0,atol=0,rtol=0)
            rows=list(csv.DictReader((OUT/zone/'results.csv').open()))
            assert len(rows)==408
            for row in rows:
                t=float(row['thickness_nm']);im=list(f['method_labels']).index(row['method'])
                ie=0 if row['edge']=='L3' else 1
                raw=f['raw'][int(t/2),im,ie]
                exported=np.array([float(row[k]) for k in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus')])
                assert_allclose(raw,exported,atol=0,rtol=0)
                if t==0:
                    assert np.isnan(float(row['prb_relative_dichroism_percent']))
                else:
                    ap,bp,am,bm=raw
                    assert_allclose(float(row['prb_relative_dichroism_percent']),100*(ap-bp)/(ap+bp),rtol=1e-12)
                    assert_allclose(float(row['D_mag']),((ap-am)-(bp-bm))/2,atol=1e-15)
                    assert_allclose(float(row['D_even']),((ap+am)-(bp+bm))/2,atol=1e-15)


def test_orientation_source_reproduction_and_preservation():
    meta=json.loads((OUT/'study_metadata.json').read_text())
    for zone in ('001','017'):
        m=meta['geometries'][zone]
        assert m['eta']==m['beta']==1
        assert m['energies_ev']==[831.4778,848.698]
        assert_allclose(m['projected_ZA_q_cycles_per_angstrom'],
            -np.asarray(m['tilt_mrad'])*.001/m['wavelength_angstrom'],atol=1e-14)
        if zone=='017':
            assert len(m['hkl'])==27
            assert all(h[1]+7*h[2]==0 for h in m['hkl'])
            assert any(h[1]!=0 for h in m['hkl'])
            assert_allclose(m['magnetization_local'],[0,-1/np.sqrt(50),7/np.sqrt(50)],atol=1e-14)
    rows=list(csv.DictReader((OUT/'reference_reproduction.csv').open()))
    assert len(rows)==8
    assert max(float(x['max_raw_absolute']) for x in rows)<1e-14
    original=json.loads((OUT/'provenance.json').read_text())
    for mapping in original['previous_hashes'].values():
        for path,digest in mapping.items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest
    assert hashlib.sha256((ROOT/'data/wien2k_ni/Ni_fm.xmcd').read_bytes()).hexdigest()==original['source_sha256']


def test_gate_reports_unrun_work_and_never_invents_voltage_results():
    gate=json.loads((OUT/'convergence_gate.json').read_text())
    controls=list(csv.DictReader((OUT/'convergence.csv').open()))
    pp=max(abs(float(x['prb_change_pp'])) for x in controls)
    raw=max(float(x['raw_max_relative']) for x in controls)
    expected=pp<=gate['tolerances']['max_prb_change_pp'] and raw<=gate['tolerances']['max_raw_relative']
    assert expected==gate['passed']
    assert_allclose(pp,gate['maximum_prb_change_pp'])
    if not gate['passed']:
        assert gate['additional_voltages']=='not run' and gate['gui']=='not integrated'
        assert (OUT/'figure_6_voltage_comparison_NOT_RUN.txt').exists()
        changed=subprocess.check_output(['git','diff','--name-only',
            json.loads((OUT/'provenance.json').read_text())['base_commit'],
            'f97e16c495097c27363c8b29938c254825ff7364','--','src/emcd_sim/gui'],text=True)
        assert changed.strip()==''
