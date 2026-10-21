"""Full-field presentation and strict scan checkpoint checks; saved data only."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from dataclasses import replace
from pathlib import Path
import sys
import json
import numpy as np
import pytest
from emcd_sim.gui.project_io import load_project
from emcd_sim.gui.component_display import primary_angular
from runtime_fixtures import fingerprints


@pytest.fixture
def result():
    if not Path('outputs/v060_release/source_native/double_both_project').is_dir():pytest.skip('Optional saved angular references unavailable')
    return load_project('outputs/v060_release/source_native/double_both_project')


def test_apertures_and_legacy_pair_fields_do_not_limit_map(result):
    before=fingerprints(result);values,_=primary_angular(result,'L3','asymmetry')
    changed=dict(result,config=replace(result['config'],centers=((.1,.2),(-.3,.1)),radius=.01),weights={})
    changed=dict(changed,maps={e:{k:v for k,v in m.items() if not k.startswith('D_')} for e,m in changed['maps'].items()})
    after,meta=primary_angular(changed,'L3','asymmetry')
    np.testing.assert_array_equal(values['EMCD Asymmetry'],after['EMCD Asymmetry'])
    outside=(result['weights']['A']==0)&(result['weights']['B']==0)
    assert np.isfinite(after['EMCD Asymmetry'][outside]).any()
    assert 'Full-field' in meta['support'] and fingerprints(result)==before


def test_independent_point_pair_values_and_antisymmetry(result):
    q=result['qy'];ap=.6+.1*q;am=.5+.03*q
    r=dict(result,maps={'L3':dict(I_plus=ap,I_minus=am)})
    raw,_=primary_angular(r,'L3');ratio,_=primary_angular(r,'L3','asymmetry')
    np.testing.assert_allclose(raw['Magnetic paired difference'],.07*q,atol=1e-15)
    np.testing.assert_allclose(raw['Nonmagnetic paired difference'],.13*q,atol=1e-15)
    np.testing.assert_allclose(ratio['EMCD Asymmetry'],100*.2*q/1.2,atol=1e-13)
    np.testing.assert_allclose(ratio['EMCD Asymmetry'],-ratio['EMCD Asymmetry'][::-1],atol=1e-13)


def test_moving_actual_plot_overlays_preserves_pixel_values(result):
    import copy
    from matplotlib.figure import Figure
    from emcd_sim.geometry import VirtualDetector
    from emcd_sim.gui.results import draw_maps
    r=result['methods']['bloch'];model=copy.copy(r['model'])
    centers=((.12,.2),(-.25,.1));model.detectors={k:VirtualDetector(c,.02) for k,c in zip(('A','B'),centers)}
    changed=dict(r,model=model,config=replace(r['config'],centers=centers,radius=.02))
    fig=Figure(figsize=(12,7),layout='constrained');draw_maps(fig,changed,'L3',signal_mode='asymmetry')
    ax=next(a for a in fig.axes if a.images)
    original,_=primary_angular(r,'L3','asymmetry')
    np.testing.assert_array_equal(ax.images[0].get_array().filled(np.nan),original['EMCD Asymmetry'])
    for center in centers:assert any(np.allclose(p.center,center) for p in ax.patches if hasattr(p,'center'))


def test_invalid_denominators_remain_nan_without_interpolation(result):
    ap=np.ones_like(result['qx']);am=ap.copy();ap[[0,-1],0]=0
    r=dict(result,maps={'L3':dict(I_plus=ap,I_minus=am)})
    fields,_=primary_angular(r,'L3','asymmetry')
    assert np.isnan(fields['EMCD Asymmetry'][[0,-1],0]).all()
    assert fields['EMCD Asymmetry'].shape==result['qx'].shape


def test_uncomputed_or_one_sided_data_rejected(result):
    with pytest.raises(ValueError,match='not calculated'):
        primary_angular(dict(result,config=replace(result['config'],angular_maps=False)),'L3')
    q=result['qy'].copy()+.1
    with pytest.raises(ValueError,match='mirrored'):primary_angular(dict(result,qy=q),'L3')
    maps={e:dict(m) for e,m in result['maps'].items()};maps['L3']['I_plus']=maps['L3']['I_plus'].copy();maps['L3']['I_plus'][0]=np.nan
    with pytest.raises(ValueError,match='support'):primary_angular(dict(result,maps=maps),'L3')


def test_all_saved_models_solvers_and_overlays_preserve_science():
    if not Path('outputs/v060_release/source_native/double_both_project').is_dir():pytest.skip('Optional saved angular references unavailable')
    from matplotlib.figure import Figure
    from emcd_sim.gui.results import draw_maps
    for model in ('single','double'):
        for method in ('bloch','fft-multislice','both'):
            r=load_project(Path('outputs/v060_release/source_native')/(model+'_'+method+'_project'));before=fingerprints(r)
            for mode in ('raw','asymmetry'):
                fig=Figure(figsize=(12,7),layout='constrained');draw_maps(fig,r,'L3',signal_mode=mode)
                axes=[a for a in fig.axes if a.images]
                assert len(axes)==(2 if mode=='raw' else 1)
                assert 'Full-field mirrored-point EMCD' in fig._suptitle.get_text()
                assert all(a.patches for a in axes)
            assert before==fingerprints(r)
