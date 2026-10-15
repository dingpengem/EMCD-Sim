"""Focused magnetic parity, geometry grouping and output checks."""
from dataclasses import replace
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from emcd_sim.xmcd_geometry_decomposition import (
    A, B, GeometryDecompositionConfig, compare_geometry_results,
    magnetic_contribution_metrics, run_geometry_decomposition,
)


@pytest.fixture
def xmcd(tmp_path):
    path = tmp_path/'synthetic.xmcd'
    e = np.array([837.,852.7,870.,882.])
    rp,lp = np.array([1.,3.,2.,1.]),np.array([1.,2.,3.,1.])
    np.savetxt(path,np.column_stack((e,rp,lp,rp-lp,rp+lp)))
    return path


def test_contribution_metrics():
    m = magnetic_contribution_metrics([0.,1.,0.,1.,1e-15], [0.,0.,1.,1e-15,1e-15], 1.)
    np.testing.assert_array_equal(m['valid_f_mag'],[False,True,True,True,False])
    np.testing.assert_array_equal(m['valid_R_mag_nonmag'],[False,False,True,False,False])
    assert np.isnan(m['f_mag'][0]) and np.isnan(m['f_mag'][-1])
    assert m['f_mag'][1] == 1 and m['f_mag'][2] == 0
    assert m['R_mag_nonmag'][2] == 0
    pair = magnetic_contribution_metrics(-3.,4.,10.)
    assert pair['f_mag'] == pytest.approx(3/7)
    assert pair['R_mag_nonmag'] == pytest.approx(.75)
    assert not magnetic_contribution_metrics(np.nan,1.,1.)['valid_f_mag']


def test_reversal_geometry_and_maps(xmcd):
    config = GeometryDecompositionConfig(cutoff=.75,grid=17,steps=3,
        thickness_nm=3.,finer_grid=None,l2_energy_ev=870.)
    plus = run_geometry_decomposition(xmcd,config)
    minus = run_geometry_decomposition(xmcd,replace(config,eta=-1))
    zero = run_geometry_decomposition(xmcd,replace(config,eta=0))
    assert len(plus.metadata['energy_grid_ev']) == 2
    for p,m,z in zip(plus.records,minus.records,zero.records):
        assert p['Delta_mag'] == pytest.approx(-m['Delta_mag'],abs=1e-13)
        assert p['A_mag'] == pytest.approx(-m['A_mag'],abs=1e-13)
        assert p['Delta_nonmag'] == pytest.approx(m['Delta_nonmag'],abs=1e-13)
        assert p['A_nonmag'] == pytest.approx(m['A_nonmag'],abs=1e-13)
        assert p['delta_plus'] == pytest.approx(p['Delta_mag']+p['Delta_nonmag'],abs=1e-13)
        assert z['Delta_mag'] == pytest.approx(0,abs=1e-14)
        assert z['A_mag'] == pytest.approx(0,abs=1e-14)
        assert p['Sigma_ref'] == pytest.approx((p['sigma_plus']+p['sigma_minus'])/2)
        x,y,zz = [r.maps[p['map_file']] for r in (plus,minus,zero)]
        np.testing.assert_allclose(x['I_mag'],-y['I_mag'],atol=1e-13)
        np.testing.assert_allclose(x['I_nonmag'],y['I_nonmag'],atol=1e-13)
        np.testing.assert_allclose(x['I_plus'],x['I_mag']+x['I_nonmag'],atol=1e-13)
        np.testing.assert_allclose(zz['I_mag'],0,atol=1e-14)
        for q in ('qx_inv_angstrom','qy_inv_angstrom'):
            np.testing.assert_array_equal(x[q],next(iter(plus.maps.values()))[q])
        assert x['energy_ev'] == (852.7 if p['edge']=='L3' else 870.)
        assert x['I_plus'].min() >= -1e-8
    for edge in ('L3','L2'):
        two = next(r for r in plus.records if r['group']==A and r['condition']=='two-beam' and r['edge']==edge)
        near = next(r for r in plus.records if r['group']==A and r['condition']=='near-2bc' and r['edge']==edge)
        for k in ('A_raw_plus','A_raw_minus','A_mag','A_nonmag','Sigma_ref','Delta_mag','Delta_nonmag'):
            assert two[k] == pytest.approx(near[k],abs=1e-13)
        np.testing.assert_array_equal(plus.maps[two['map_file']]['I_mag'],plus.maps[near['map_file']]['I_mag'])
    truncated = [r for r in plus.records if r['group']==B]
    assert all(r['beam_count']==2 and r['basis_kind']=='two-beam-truncated' for r in truncated)
    assert all(r['beam_count']==5 for r in plus.records if r['group']==A)
    sym = next(g for g in plus.metadata['geometries'].values() if g['condition']=='symmetric-3bc')
    assert sym['chiral_groups'] == {'A':('RU','LD'),'B':('RD','LU')}
    assert set(sym['detectors']) == {'RU','RD','LU','LD'}
    assert plus.metadata['source_peak_N'] == 2.5
    sources = [g['tensor_sources'] for g in plus.metadata['geometries'].values()]
    assert all(s==sources[0] for s in sources)
    for run_id,g in plus.metadata['geometries'].items():
        sample = plus.maps[next(r['map_file'] for r in plus.records if r['run_id']==run_id)]
        for det in g['detectors'].values():
            qx,qy = sample['qx_inv_angstrom'],sample['qy_inv_angstrom']
            x,y = det['center_q_xy']
            assert det['grid_points'] == np.count_nonzero((qx-x)**2+(qy-y)**2 <= det['radius_q']**2)
    assert all(c['identical_physical_inputs'] for c in plus.metadata['comparisons']['coincident_geometries'])
    assert plus.metadata['comparisons']['grid_status'] == 'not-checked'


def test_grid_sensitivity_status():
    # Exercise the comparison policy independently of any predicted Ni value.
    base = dict(run_id='base',group=A,condition='near-2bc',edge='L3',sampling_role='baseline',
                grid=65,A_raw_plus=.1,A_raw_minus=.1,A_mag=.01,A_nonmag=.09,Sigma_ref=1.)
    fine = dict(base,run_id='fine',sampling_role='finer-grid',grid=97,A_mag=.02)
    result = compare_geometry_results([base,fine],{})
    assert result['grid_status'] == 'unresolved'
    assert result['grid_refinement'][0]['sensitive']['A_mag']
    fine['A_mag'] = base['A_mag']
    result = compare_geometry_results([base,fine],{})
    assert result['grid_status'] == 'limited-grid-agreement-for-tested-geometry-only'
    fine['A_mag'] = np.nan
    assert compare_geometry_results([base,fine],{})['grid_status'] == 'unresolved'


def test_input_validation(xmcd):
    config = GeometryDecompositionConfig(grid=17,steps=3,finer_grid=None)
    for kwargs in ({'cutoff':-1.},{'steps':1},{'conditions':()}, {'finer_grid':17}, {'eta':np.nan}):
        with pytest.raises(ValueError):
            run_geometry_decomposition(xmcd,replace(config,**kwargs))
    with pytest.raises(ValueError,match='cap'):
        run_geometry_decomposition(xmcd,replace(config,max_beams=8))


def test_integration_cli_and_provenance(tmp_path):
    # One selected-energy workflow, five baseline cases and one refinement.
    source = Path(__file__).resolve().parents[1]/'data/wien2k_ni/Ni_fm.xmcd'
    output = tmp_path/'Ni geometry paths with spaces'
    done = subprocess.run([sys.executable,'-m','emcd_sim.xmcd_geometry_decomposition',
        '--xmcd-file',str(source),'--output',str(output)],
        capture_output=True,text=True,check=True,timeout=180)
    assert 'Grid check:' in done.stdout
    meta = json.loads((output/'geometry_metadata.json').read_text(encoding='utf-8'))
    assert meta['xmcd_sha256'] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert meta['python_version'] == sys.version.split()[0]
    assert meta['software_commit']
    assert all(meta[k] is False for k in ('absolute_cross_section','outgoing_channeling','quantitative_Ni','beam_basis_converged'))
    assert meta['config']['grid']==65 and meta['config']['steps']==64
    assert meta['config']['finer_grid']==97
    assert len(meta['energy_grid_ev'])==2
    assert meta['selected_energies_ev']['L3'] in meta['energy_grid_ev']
    with (output/'geometry_comparison.csv').open(encoding='utf-8',newline='') as f:
        rows = list(csv.DictReader(f))
    assert len(rows)==6
    with np.load(output/'geometry_comparison.npz',allow_pickle=False) as data:
        for i,r in enumerate(rows):
            g = meta['geometries'][r['run_id']]
            assert json.loads(r['detectors_json']) == g['detectors']
            assert json.loads(r['beam_hkl_json']) == g['beam_hkl']
            assert float(r['A_mag']) == data['A_mag'][i]
            assert float(r['energy_ev']) == data['energy_ev'][i] == meta['selected_energies_ev']['L3']
            assert int(r['beam_count']) == len(g['beam_hkl'])
            assert float(r['tilt_y_mrad']) == g['tilt_mrad_xy'][1]
            assert {'Delta_mag','Delta_nonmag','Sigma_ref','f_mag','R_mag_nonmag',
                    'valid','valid_f_mag','valid_R_mag_nonmag'} <= set(data.files)
            with np.load(output/r['map_file'],allow_pickle=False) as m:
                assert m['I_mag'].shape == (int(r['grid']),int(r['grid']))
                np.testing.assert_array_equal(m['beam_hkl'],g['beam_hkl'])
                np.testing.assert_allclose(m['I_plus'],m['I_mag']+m['I_nonmag'],atol=1e-13)
                assert m['depth_steps']==64
            assert all(d['grid_points']>0 for d in g['detectors'].values())
    assert len(meta['comparisons']['grid_refinement'])==1
    assert all(c['identical_physical_inputs'] for c in meta['comparisons']['coincident_geometries'])
    assert len(meta['comparisons']['truncation_reference'])==1
    for name in ('magnetic_odd_maps.png','nonmagnetic_even_maps.png',
                 'geometry_asymmetry_comparison.png','magnetic_contribution_comparison.png'):
        assert (output/name).stat().st_size>1000
    print(f'Reference output: {output}')
