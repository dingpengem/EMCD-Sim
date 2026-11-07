"""Exact reported CIF, real Qt controls and elastic worker; no MDFF model claim."""
import hashlib
import ast
import json
import math
import os
import subprocess
import time
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import numpy as np
import pytest

pytest.importorskip('PySide6')
pytest.importorskip('ase')
from PySide6 import QtWidgets
from emcd_sim.gui.app import MainWindow
from emcd_sim.gui.geometry import Structure, Settings, geometry

CIF=Path(__file__).parent/'fixtures/alpha_Fe_bcc_Im-3m.cif'
CIF_SHA='e841d08df6ba5a2860385397a85da36856568d19e72250e1bebaa37885f595df'

@pytest.fixture
def window(tmp_path):
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    w=MainWindow(workspace=tmp_path/'workspace');w.errors=[];w.error=w.errors.append
    yield w,app
    if w.worker:
        w.worker.requestInterruption();w.worker.wait(10000);app.processEvents()
    for d in w.dialogs:d.close()
    w.close();app.processEvents()

def load_exact(w):
    with patch.object(QtWidgets.QFileDialog,'getOpenFileName',return_value=(str(CIF),'')):
        w.load_cif()

def wait_preview(w,app):
    w.start_preview();deadline=time.monotonic()+20
    while w.busy and time.monotonic()<deadline:app.processEvents();time.sleep(.01)
    assert not w.busy
    assert not w.errors
    assert w.run_outcome=='completed'
    assert w.worker.wait(5000)

def test_exact_cif_structure_and_reciprocal_selection():
    assert hashlib.sha256(CIF.read_bytes()).hexdigest()==CIF_SHA
    s=Structure.from_cif(CIF);a=s.atoms
    assert a.get_chemical_symbols()==['Fe','Fe']
    assert a.info['spacegroup'].no==229
    np.testing.assert_allclose(a.cell.cellpar(),[2.8665]*3+[90.]*3,atol=1e-12)
    np.testing.assert_allclose(a.get_scaled_positions(),[[0,0,0],[.5,.5,.5]],atol=1e-14)
    _,r,h,g,_=geometry(s,Settings(zone=(0,0,1),target=(1,1,0),voltage=200,thickness=1,tilt=(0,0),beam_cutoff=1.05,potential_cutoff=1.05))
    assert len(h)==13 and (1,1,0) in h and (1,0,0) not in h
    assert all(sum(x)%2==0 and x[2]==0 for x in h)
    np.testing.assert_allclose(np.linalg.norm(g[h.index((1,1,0))]),np.sqrt(2)/2.8665,atol=1e-14)

def test_direct_import_retains_settings_and_explains_manual_guard(window):
    w,app=window;before=w.settings();load_exact(w)
    assert w.settings()==before
    assert w.numerical_mode.currentText()=='Automatic'
    assert w.run_button.isEnabled()
    assert 'displayed settings unchanged' in w.run_button.toolTip()
    assert 'not independently convergence-validated' in w.run_button.toolTip()
    assert 'Ni presets are not transferred' in w.statusBar().currentMessage()
    assert w._numerical_error and not w.emcd_button.isEnabled()
    assert w.ax.get_title()!='Invalid configuration — no current plot'
    assert not w.errors
    wait_preview(w,app)
    assert w.settings()==before
    h=list(map(tuple,w.last_result['beam_hkl']))
    assert (1,0,0) not in h and (2,0,0) in h and w.settings().zone==(0,1,7)

@pytest.mark.parametrize('cutoff,count',[(1.05,13),(2.5,81),(3.0,113),(3.2,137)])
def test_bcc_001_counts_from_independent_parity_and_reciprocal_radius(cutoff,count):
    # Independent BCC selection: h+k+l even; [001] requires l=0.
    bound=math.ceil(2.8665*cutoff)
    expected={(h,k,0) for h in range(-bound,bound+1) for k in range(-bound,bound+1)
              if (h+k)%2==0 and math.hypot(h,k)/2.8665<=cutoff+1e-10}
    assert len(expected)==count
    s=Structure.from_cif(CIF);cfg=Settings(zone=(0,0,1),target=(2,0,0),beam_cutoff=cutoff)
    if count>121:
        with pytest.raises(ValueError,match='137 beams exceed the interactive limit 121'):geometry(s,cfg)
    else:
        assert set(geometry(s,cfg)[2])==expected

def test_zone_only_after_import_explains_beam_limit_without_changing_settings(window):
    w,app=window;load_exact(w)
    before=w.settings();w.zone.setText('0 0 1');w.apply_orientation()
    assert w.settings().target==(2,0,0)
    assert w.settings().beam_cutoff==before.beam_cutoff==3.2
    assert w.numerical_mode.currentText()=='Automatic'
    assert w.ax.get_title()=='Beam limit exceeded — no current plot'
    assert '137 beams exceed the interactive limit 121' in w.selection.text()
    assert 'Select Manual (Advanced)' in w.selection.text()
    assert '137 beams' in w.ax.texts[0].get_text()
    assert not w.run_button.isEnabled()
    with pytest.raises(ValueError,match='137 beams exceed'):geometry(w.structure,w.settings())
    w.numerical_mode.setCurrentIndex(1)
    assert w.settings().beam_cutoff==3.2  # Manual mode alone must not coarsen.
    w.set_values(dict(beam=1.05))
    w.target.setText('1 1 0');w.apply_orientation()
    assert w.settings().target==(1,1,0)
    assert w.settings().potential_cutoff==before.potential_cutoff
    assert w.settings().voltage==before.voltage and w.settings().thickness==before.thickness
    assert w.run_button.isEnabled() and (1,1,0) in w.current[2]
    wait_preview(w,app)
    assert w.preview_is_current(w.settings())

@pytest.mark.parametrize('beam_cutoff,beam_count',[(1.05,13),(3.0,113)])
def test_requested_fe_settings_actual_worker_and_default_ni(window,beam_cutoff,beam_count):
    w,app=window
    wait_preview(w,app)
    assert w.preview_is_current(w.settings())
    load_exact(w);w.numerical_mode.setCurrentIndex(1)
    w.zone.setText('0 0 1');w.target.setText('1 1 0')
    w.row_projection.setChecked(False);w.basis_mode.setCurrentIndex(0)
    w.set_values(dict(kv=200,thickness=1,tx=0,ty=0,beam=beam_cutoff,potential=1.05))
    w.refresh();wait_preview(w,app)
    h=list(map(tuple,w.last_result['beam_hkl']))
    assert len(h)==beam_count and (1,1,0) in h and (1,0,0) not in h
    assert w.ax.get_title()=='Elastic diffraction — exit intensities'
    assert np.isfinite(w.last_result['intensity']).all()
    np.testing.assert_allclose(w.last_result['intensity'].sum(),1.,atol=2e-14)
    assert w.last_result['elastic_provider']['provider']=='adaptive-dirac-pade-2026'

@pytest.mark.parametrize('model',[0,1,2])
def test_unsupported_fe_mdff_never_blocks_valid_elastic_or_applies_presets(window,model):
    w,app=window;load_exact(w);before=w.settings();numbers=w.numerical_snapshot()
    w.model_box.setCurrentIndex(model);w.refresh()
    assert w.numerical_mode.currentIndex()==0
    assert w._numerical_error and not w.emcd_button.isEnabled()
    assert w.run_button.isEnabled()
    # The elastic worker must not enter MDFF preparation or its forward solver.
    with patch('emcd_sim.mdff_providers.prepare_provider',side_effect=AssertionError('MDFF used for elastic preview')):
        wait_preview(w,app)
    assert w.settings()==before and w.numerical_snapshot()==numbers
    assert w._numerical_error and not w.emcd_button.isEnabled()
    assert (1,0,0) not in list(map(tuple,w.last_result['beam_hkl']))

@pytest.mark.parametrize('mode',[0,1])
def test_unsupported_elastic_provider_points_are_labeled_not_diffraction(window,mode):
    w,app=window
    w.elastic_provider_box.setCurrentIndex(w.elastic_provider_box.findData('nickel-lobato-2014'))
    load_exact(w);w.numerical_mode.setCurrentIndex(mode);w.refresh()
    assert w.settings().zone==(0,1,7) and (1,0,0) in w.current[2]
    assert 'elastic provider unavailable' in w.ax.get_title()
    assert 'Unfiltered reciprocal-lattice points' in w._diffraction_spots.get_label()
    assert 'not intensity-calculated reflections' in w.info.toPlainText()
    assert not w.run_button.isEnabled() and w.last_result is None
    w.start_preview()
    assert len(w.errors)==1 and 'Ni Lobato provider supports only Ni' in w.errors[0]
    assert 'Declared MDFF' not in w.errors[0]
    w.errors.clear()
    w.elastic_provider_box.setCurrentIndex(w.elastic_provider_box.findData('adaptive-dirac-pade-2026'))
    assert (1,0,0) not in w.current[2] and w.run_button.isEnabled()
    wait_preview(w,app)
    assert (1,0,0) not in list(map(tuple,w.last_result['beam_hkl']))

@pytest.mark.parametrize('zone,target,cutoff,reason',[
    ('0 0 0','2 0 0',1.05,'zone direction'),
    ('0 1 7','1 1 0',1.05,'selected ZOLZ plane'),
    ('0 0 1','2 0 0',.1,'No nonzero ZOLZ reflections'),
    ('0 0 1','2 0 0',3.2,'137 beams exceed'),
])
def test_mdff_independence_does_not_bypass_elastic_validation(window,zone,target,cutoff,reason):
    w,app=window;load_exact(w)
    w.zone.setText(zone);w.target.setText(target);w.set_values(dict(beam=cutoff));before=w.numerical_snapshot()
    w.refresh();assert not w.run_button.isEnabled()
    assert 'Manual (Advanced)' in w.selection.text()
    w.start_preview()
    assert w.errors and reason in w.errors[-1]
    assert 'Declared MDFF' not in w.errors[-1]
    assert w.last_result is None and not w.busy and w.numerical_snapshot()==before

def test_completed_fe_preview_and_stale_geometry_are_distinguished(window):
    w,app=window;load_exact(w);wait_preview(w,app)
    assert w.preview_is_current(w.settings())
    assert w.ax.get_title()=='Elastic diffraction — exit intensities'
    assert w._diffraction_spots.get_array() is not None
    w.set_values(dict(thickness=w.settings().thickness+1));w.refresh()
    assert not w.preview_is_current(w.settings())
    assert w.ax.get_title()=='Current reciprocal geometry — no current intensities'
    assert w._diffraction_spots.get_array() is None
    assert not w.emcd_button.isEnabled()

def test_candidate_review_attests_only_two_gui_methods_without_relabeling_baseline():
    root=Path(__file__).resolve().parents[1]
    raw=(root/'docs/acceptance/bcc-fe-gui-reviewed-diff.json').read_bytes()
    review=json.loads(raw)
    assert review['baseline_commit']=='cdd5dc3efa43e4f3874e011aa1cfc98f80cf46dd'
    assert review['authorized_methods']==['refresh','start_preview']
    from unit_source_snapshots import load_gui_scope
    _,baseline=load_gui_scope()
    # Authenticate current composed sources before querying the retained BCC candidate.
    from unit_source_snapshots import assert_reviewed_current_sources
    from physics_source_guard import assert_registered_sources
    from mdff_usability_source_scope import load_scope
    assert_reviewed_current_sources();assert_registered_sources()
    _,parents=load_scope()
    candidate=parents['src/emcd_sim/gui/app.py']
    canonical=lambda b:b.decode('utf-8-sig').replace('\r\n','\n').encode()
    assert hashlib.sha256(canonical(baseline)).hexdigest()==review['baseline_canonical_sha256']
    assert hashlib.sha256(canonical(candidate)).hexdigest()==review['candidate_canonical_sha256']
    def mask(b):
        tree=ast.parse(canonical(b))
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='MainWindow')
        for node in cls.body:
            if isinstance(node,ast.FunctionDef) and node.name in review['authorized_methods']:node.body=[ast.Pass()]
        return ast.dump(tree,include_attributes=False)
    assert mask(candidate)==mask(baseline)
    assert review['historical_identity_checks_against_candidate']=='expected mismatch; not waived or relabeled as passing'
