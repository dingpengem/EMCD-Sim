"""Real Qt preparation controls; synthetic parameters never certify Fe spectroscopy."""
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pytest
from ase import Atoms
from ase.io import read, write
from PySide6 import QtWidgets
from emcd_sim.gui.app import MainWindow
from emcd_sim.gui.geometry import Structure
from emcd_sim.gui.atomic_editor import FIELDS
from emcd_sim.gui.atomic_editor_model import (CAPABILITY, MAX_SAMPLES, capability_reason,
    crystal_elements, edge_references, explicit_grid, persist_document, read_document, validate_document)
from emcd_sim.atomic_ionization import export_atomic_parameters, ORBITALS

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT/'docs/examples/synthetic_fe_atomic_parameters.json'


@pytest.fixture
def window(tmp_path):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    w = MainWindow(tmp_path/'workspace'); w.errors = []; w.error = w.errors.append
    yield w, app
    if w.busy: w.cancel(); w.worker.wait(15000)
    for dialog in w.dialogs: dialog.close()
    if hasattr(w.atomic_editor, 'preview_dialog'): w.atomic_editor.preview_dialog.close()
    w.close(); app.processEvents()


def iron(w):
    w.structure = Structure.from_cif(ROOT/'tests/fixtures/alpha_Fe_bcc_Im-3m.cif')
    w.model_box.setCurrentIndex(1); w.numerical_mode.setCurrentIndex(1)
    w.zone.setText('0 0 1'); w.target.setText('1 1 0'); w.set_values(dict(beam=1.05)); w.refresh()


def demo(w):
    iron(w); w.atomic_editor.load_document(DEMO); return w.atomic_editor


def wait_gui(w, app):
    import time
    deadline = time.monotonic() + 90
    while w.busy and time.monotonic() < deadline:
        app.processEvents(); time.sleep(.01)
    assert not w.busy, 'GUI worker did not finish'
    if w.worker: assert w.worker.wait(5000)
    app.processEvents()


@pytest.mark.parametrize('browser_mapping', ['empty', 'missing', 'different_bytes'])
def test_gui_reopens_relocated_editor_source_without_original(window, tmp_path, browser_mapping):
    from emcd_sim.gui.forward_pipeline import calculate
    from emcd_sim.gui.geometry import Settings
    from emcd_sim.gui.project_io import save_project, source_status
    w, app = window; e = demo(w); e.generate()
    cfg = replace(w.atomic_provider_info, propagation='both', energy_scope='edges',
        grid=9, depth=5, subpixels=4, halfwidth=.7, radius=.12, centers=((.2,.2),(.2,-.2)),
        fft_grid=16, slice_step=.01, correction=False, worker_mode='manual', parallel_workers=1)
    settings = Settings(zone=(0,0,1),target=(1,1,0),voltage=200,thickness=.2,tilt=(-5,7),beam_cutoff=.6,potential_cutoff=1.2)
    original = Path(cfg.source); original_bytes = original.read_bytes()
    reference = calculate(w.structure, settings, cfg)
    folder = tmp_path/'original-project'; save_project(reference, folder)
    record = w.browser.register(reference, folder)
    relocated = tmp_path/'relocated-project'; folder.rename(relocated); original.unlink()
    mapping = {} if browser_mapping == 'empty' else {'mdff': str(original)}
    if browser_mapping == 'different_bytes':
        other = tmp_path/'unrelated.json'; other.write_bytes(b'{"not":"the accepted source"}')
        mapping = {'mdff': str(other)}
    record['source_overrides'] = mapping
    w.open_project_path(relocated, record=record, relocated=True); wait_gui(w, app)
    assert not w.errors and w.run_outcome == 'completed', w.errors
    portable = relocated/'atomic_input.json'
    assert portable.read_bytes() == original_bytes
    assert hashlib.sha256(portable.read_bytes()).hexdigest() == cfg.source_sha256
    assert Path(source_status(w.emcd_result)['mdff']['path']) == portable
    assert source_status(w.emcd_result)['mdff']['verified']
    w.use_result_settings()
    assert w.atomic_provider_info and w.atomic_declaration.isChecked()
    assert Path(w.forward_settings().source) == portable
    w.start_emcd(); wait_gui(w, app)
    assert not w.errors and w.run_outcome == 'completed', w.errors
    for method in reference['methods']:
        for key, value in reference['methods'][method]['spectra'].items():
            np.testing.assert_array_equal(value, w.emcd_result['methods'][method]['spectra'][key])
    # GUI open must reject altered portable bytes and preserve the current result.
    current = w.emcd_result; portable.write_bytes(original_bytes+b' ')
    w.open_project_path(relocated, record=record); wait_gui(w, app)
    assert w.run_outcome == 'failed' and w.emcd_result is current
    assert any('Missing or corrupted project file: atomic_input.json' in error for error in w.errors)


def test_gui_rejects_conflicting_loader_source_identity(window, tmp_path):
    from types import SimpleNamespace
    w, app = window
    accepted = tmp_path/'accepted.json'; accepted.write_bytes(b'accepted input')
    changed = tmp_path/'changed.json'; changed.write_bytes(b'different scientific input')
    cfg = SimpleNamespace(model='atomic',provider_schema=1,source=str(accepted),
        source_sha256=hashlib.sha256(accepted.read_bytes()).hexdigest())
    conflicting = dict(config=cfg,source_overrides=dict(mdff=str(changed)),structure_snapshot=None)
    with patch('emcd_sim.gui.results_browser.load_project',return_value=conflicting):
        w.open_project_path(tmp_path/'project',legacy=True); wait_gui(w, app)
    assert w.run_outcome == 'failed' and w.emcd_result is None
    assert any('Conflicting verified project source identity: mdff' in error for error in w.errors)


@pytest.mark.parametrize('claim_edit', ['value', 'element', 'edge', 'reference_hash', 'parameter_only', 'human_label', 'edge_human_label'])
def test_imported_edge_claim_matches_visible_provenance_and_roundtrip(window, tmp_path, claim_edit):
    from emcd_sim.gui.atomic_editor_model import EDITOR_TAG
    w, _ = window; e = demo(w); e.apply_references(confirm=False)
    doc = e.document(); source, _, encoded = doc['parameters']['source'].partition(EDITOR_TAG)
    trace = json.loads(encoded)
    if claim_edit == 'value':doc['parameters']['edge_energies_ev'][0] = 709.3
    elif claim_edit == 'element':trace['edge_origins']['l3']['element'] = 'Co'
    elif claim_edit == 'edge':trace['edge_origins']['l3']['edge'] = 'L2'
    elif claim_edit == 'reference_hash':trace['edge_origins']['l3']['subset_sha256'] = '0'*64
    elif claim_edit == 'parameter_only':trace['edge_origins'].pop('l3')
    elif claim_edit == 'human_label':
        trace['edge_origins']['l3'] = dict(origin='imported')
        trace['parameter_origins']['l3']['origin'] = 'Tabulated elemental reference'
    else:
        trace['edge_origins']['l3']['origin'] = 'Tabulated elemental reference'
        trace['parameter_origins']['l3']['origin'] = 'imported_physical_source'
    doc['parameters']['source'] = source+EDITOR_TAG+json.dumps(trace)
    path = tmp_path/'claimed.json'; path.write_text(json.dumps(doc),encoding='utf-8')
    e.load_document(path)
    assert float(e.fields['l3'].text()) == doc['parameters']['edge_energies_ev'][0]
    assert e.origins['l3']['origin'] == 'imported_override_unverified'
    assert e.parameter_origins['l3']['origin'] == 'imported_override_unverified'
    assert 'override' in e.origin_labels['l3'].text().lower()
    assert 'Tabulated elemental reference' not in e.origin_labels['l3'].text()
    assert 'override' in e.fields['l3'].toolTip().lower()
    exported = tmp_path/'roundtrip.json'
    with patch.object(QtWidgets.QFileDialog,'getSaveFileName',return_value=(str(exported),'')):e.export_dialog()
    e.load_document(exported)
    assert e.parameter_origins['l3']['origin'] == e.origins['l3']['origin'] == 'imported_override_unverified'
    assert 'override' in e.origin_labels['l3'].text().lower()
    assert e.parameter_origins['l2']['origin'] == 'tabulated_reference'


def test_manual_edge_provenance_labels_switching_and_preview_invalidation(window):
    w, _ = window; e = demo(w); e.apply_references(confirm=False)
    assert e.fields['l3'].text() == '708.1' and e.fields['l2'].text() == '721.1'
    assert all('Tabulated elemental reference' in e.origin_labels[k].text() for k in ('l3','l2'))
    assert 'Tabulated elemental reference' in e.fields['l3'].toolTip()
    e.preview(); w.atomic_declaration.setChecked(True); old = e.preview_dialog
    e.fields['l3'].setText('709.3')
    assert e.origins['l3']['origin'] == 'manual' and e.parameter_origins['l3']['origin'] == 'user_entered'
    assert 'User-entered / overridden' in e.origin_labels['l3'].text()
    assert 'User-entered / overridden' in e.fields['l3'].toolTip()
    assert old.is_stale and not e.validated_path and not w.atomic_declaration.isChecked()
    e.element.setCurrentIndex(e.element.findData('Co'))
    assert e.fields['l3'].text() == '778.6' and 'Tabulated elemental reference' in e.origin_labels['l3'].text()
    e.element.setCurrentIndex(e.element.findData('Fe'))
    assert e.fields['l3'].text() == '709.3' and 'User-entered / overridden' in e.origin_labels['l3'].text()


def test_capability_and_element_identity_are_separate():
    from ase.data import chemical_symbols
    assert CAPABILITY['elements'] == tuple(chemical_symbols[21:31])
    assert ORBITALS == ('z2', 'x2_y2', 'xy', 'xz', 'yz')
    assert not capability_reason('Fe')
    assert 'unavailable' in capability_reason('O')
    assert 'L2,3' in capability_reason('Fe', 'K')


def test_unified_starting_choices_have_no_material_electronic_defaults(window):
    w, _ = window; iron(w); e = w.atomic_editor
    assert e.parameter_origins['element']['origin'] == 'cif_derived'
    assert e.parameter_origins['l3']['origin'] == 'tabulated_reference'
    assert e.parameter_origins['sigma']['origin'] == 'numerical_starting'
    assert e.parameter_origins['frame']['origin'] == 'coordinate_starting'
    assert e.fields['samples'].text() == '201'
    assert float(e.fields['emin'].text()) == 698.1
    assert all(not e.fields[k].text() for k in ('cf','exchange','radial'))
    assert all(not e.holes.cellWidget(i,j).text() for i in range(5) for j in range(2))
    assert set(e.fields) <= set(e.info_buttons)
    e.info_buttons['exchange'].click()
    assert e.field_detail_dialog.isVisible()
    e.field_detail_dialog.close()


def test_preview_generates_only_on_explicit_action_and_marks_stale(window):
    w, app = window; e = demo(w)
    assert not e.validated_path
    e.preview()
    assert not w.errors, w.errors
    p = e.preview_dialog
    assert p.isVisible() and not p.is_stale
    assert not w.atomic_declaration.isChecked()
    np.testing.assert_array_equal(p.curves[0][1], np.trace(p.plus,axis1=-2,axis2=-1).real/3)
    with patch.object(e,'generate',side_effect=AssertionError('No generation per edit')):
        e.fields['cf'].setText('1.25'); app.processEvents()
    assert p.is_stale and 'STALE' in p.status.text()
    assert not e.validated_path and not w.atomic_declaration.isChecked()


@pytest.mark.parametrize('mode', [1,2,3])
def test_interactive_tensor_modes_show_actual_components(window, mode):
    w, _ = window; e = demo(w); e.preview(); p = e.preview_dialog
    np.testing.assert_array_equal(p.even,(p.plus+p.minus)/2)
    np.testing.assert_array_equal(p.odd,(p.plus-p.minus)/2)
    p.mode.setCurrentIndex(mode); p.part.setCurrentIndex(2)
    for k in range(1,10):
        p.component.setCurrentIndex(k); i,j=divmod(k-1,3)
        states=(p.plus,p.minus) if mode==1 else (p.even,p.odd) if mode==2 else (p.plus,)
        assert len(p.curves)==2*len(states)
        for n,t in enumerate(states):
            np.testing.assert_array_equal(p.curves[n*2][1],t[:,i,j].real)
            np.testing.assert_array_equal(p.curves[n*2+1][1],t[:,i,j].imag)
    assert not p.odd.flags.writeable


def test_preview_rejects_bad_units_and_non_psd_physical_tensor(window):
    from emcd_sim.gui.tensor_spectrum_preview import TensorSpectrumPreview
    from emcd_sim.mdff_providers import load_provider
    from emcd_sim.gui.generalized_forward import settings_for_provider
    w, _ = window; e = demo(w); e.generate()
    source=load_provider(settings_for_provider(e.validated_path,'atomic'))
    bad=replace(source,metadata=dict(source.metadata,units='unknown'))
    with pytest.raises(ValueError,match='units'):TensorSpectrumPreview(bad)
    negative=replace(source.plus,tensor_angstrom2_per_ev=-source.plus.tensor_angstrom2_per_ev)
    with pytest.raises(ValueError,match='positive semidefinite'):
        TensorSpectrumPreview(replace(source,plus=negative))
    # The signed odd response is never passed through the physical PSD check.
    assert 'need not be PSD' in __import__('emcd_sim.gui.tensor_spectrum_preview',fromlist=['CONSTRUCTION']).CONSTRUCTION


def test_pending_external_json_cannot_silently_reuse_editor_fields(window):
    w, _ = window; e = demo(w); e.preview(); p=e.preview_dialog
    w.atomic_parameter_path.setText('missing-new-source.json')
    assert e.external_source_pending and p.is_stale
    e.preview()
    assert not e.validated_path and not w.atomic_provider_info
    assert 'newly selected external JSON' in e.status.text()


def test_per_parameter_provenance_roundtrip(window):
    w, _ = window; e = demo(w)
    e.fields['radial'].setText('.05')
    e.set_parameter_citation('radial','Explicit synthetic radial test')
    e.generate(); assert e.validated_path
    path=e.validated_path; e.load_document(path)
    assert e.parameter_origins['radial']==dict(origin='user_entered',citation='Explicit synthetic radial test')
    assert 'Origin:' in e.origin_labels['radial'].text()


def test_independent_reference_rows_and_provenance():
    # Fixed upstream raw-eV entries, independently distinct from the synthetic fixture.
    refs = edge_references('Fe')
    assert refs['L3']['energy_ev'] == 708.1 and refs['L2']['energy_ev'] == 721.1
    assert refs['L3']['units'] == 'eV' and refs['L3']['license'] == 'BSD-3-Clause'
    assert refs['L3']['upstream_commit'] == 'f7a4a5cd8eb6d48bb5f496553ac479c2dd42674f'
    assert 'data/edges.dat' in refs['L3']['url']
    assert json.loads(DEMO.read_text())['parameters']['edge_energies_ev'] == [710., 723.]
    assert edge_references('O') == {}
    assert edge_references('Zn')['L2']['energy_ev'] == 1042.8


@pytest.mark.parametrize('filename', ['edges_subset.dat', 'provenance.json'])
def test_reference_data_or_provenance_tamper_is_rejected(tmp_path, monkeypatch, filename):
    import emcd_sim.gui.atomic_editor_model as m
    root = tmp_path/'data/edge_references_v1'; root.mkdir(parents=True)
    for p in (ROOT/'src/emcd_sim/data/edge_references_v1').iterdir():
        if p.is_file(): (root/p.name).write_bytes(p.read_bytes())
    (root/filename).write_bytes((root/filename).read_bytes()+b'changed')
    monkeypatch.setattr(m, 'files', lambda _: tmp_path)
    with pytest.raises(ValueError, match='checksum'): edge_references('Fe')


def test_exact_bcc_cif_catalog():
    atoms = read(ROOT/'tests/fixtures/alpha_Fe_bcc_Im-3m.cif')
    d = crystal_elements(atoms)
    assert len(d) == 1 and d[0]['symbol'] == 'Fe' and d[0]['atomic_number'] == 26
    assert d[0]['count'] == 2 and d[0]['site_indices'] == (0,1)


def test_mixed_occupancy_annotations_are_not_lost_or_normalized():
    atoms=Atoms('Fe',cell=np.eye(3)*3,pbc=True);atoms.set_array('spacegroup_kinds',np.array([4]))
    atoms.info['occupancy']={'4':{'Fe':.6,'Ni':.4,'O':0.}}
    catalog={x['symbol']:x for x in crystal_elements(atoms)}
    assert set(catalog)=={'Fe','Ni'}
    assert catalog['Ni']['site_indices']==(0,) and catalog['Ni']['site_occupancy_weights']=={0:.4}
    assert catalog['Fe']['site_occupancy_weights']=={0:.6}


@pytest.mark.parametrize('formula,counts', [('Fe3O4', {'Fe':3,'O':4}), ('NiFe2O4', {'Ni':1,'Fe':2,'O':4})])
def test_multielement_cif_checkboxes_never_enable_multiple_groups(window, tmp_path, formula, counts):
    w, _ = window
    cif = ROOT/'tests/fixtures/atomic_editor'/(formula+'.cif')
    with patch.object(QtWidgets.QFileDialog,'getOpenFileName',return_value=(str(cif),'')): w.load_cif()
    e = w.atomic_editor
    assert set(e.element_boxes) == set(counts)
    assert {x['symbol']:x['count'] for x in crystal_elements(w.structure.atoms)} == counts
    for box in e.element_boxes.values(): box.setChecked(True)
    e.load_document(DEMO); e.generate(); w.atomic_declaration.setChecked(True); w.model_box.setCurrentIndex(1)
    w.emcd_stale(); assert not w.emcd_button.isEnabled()
    assert 'element' in w.emcd_button.toolTip().lower() or 'sites' in w.emcd_button.toolTip().lower() or 'Manual' in w.emcd_button.toolTip()


def test_required_physical_definitions_and_blank_material_inputs(window):
    w, _ = window; iron(w); e = w.atomic_editor
    assert set(e.sections) == set('ABCDEFGHI')
    assert set(e.fields) <= set(FIELDS)
    assert e.fields['l3'].text() == '708.1' and e.fields['l2'].text() == '721.1'
    assert all(not e.fields[k].text() for k in ('cf','exchange','radial','source','radial_source'))
    assert e.frame_mode.currentIndex() == 1
    assert e.fields['sigma'].text() == '1.0'
    assert e.parameter_origins['sigma']['origin'] == 'numerical_starting'
    assert all(not e.holes.cellWidget(i,j).text() for i in range(5) for j in range(2))
    assert all('Units:' in field.toolTip() and 'Provenance:' in field.toolTip() for field in e.fields.values())
    assert e.holes.rowCount() == 5 and 'electron occupation' in e.holes.toolTip()


def test_editor_generation_exact_tensor_equivalence_and_checksum(window, tmp_path):
    w, _ = window; e = demo(w); e.generate()
    assert w.atomic_provider_info is not None and e.validated_path
    assert not w.atomic_declaration.isChecked()
    doc, digest = read_document(e.validated_path)
    assert digest == w.atomic_provider_info.source_sha256 == e.validated_sha256
    a = export_atomic_parameters(DEMO, tmp_path/'original.json')
    b = export_atomic_parameters(e.validated_path, tmp_path/'edited.json')
    for sign in ('plus','minus'):
        np.testing.assert_array_equal(getattr(a,sign).tensor_angstrom2_per_ev, getattr(b,sign).tensor_angstrom2_per_ev)
    assert Path(e.validated_path).parent == w.workspace/'atomic_inputs'
    w.atomic_declaration.setChecked(True); assert w.forward_settings().ionizing_element == 'Fe'
    e.preview(); assert e.preview_dialog.isVisible()


def test_manual_fields_not_external_json_are_sufficient(window):
    w, _ = window; iron(w); e = w.atomic_editor
    # Populate controls individually; no import/load_document call.
    values = dict(l3='708.1',l2='721.1',cf='1',exchange='.5',radial='.04',sigma='.9',
        emin='700',emax='730',samples='121',source='Synthetic manual UI software test',
        radial_source='Synthetic integral; not fitted Fe',assumptions='Cubic independent electron; synthetic',validity='No material accuracy claim')
    for k,v in values.items(): e.fields[k].setText(v)
    for i in range(5):
        for j in range(2): e.holes.cellWidget(i,j).setText('.2' if j == 0 else '.6')
    e.frame_mode.setCurrentIndex(1); e.scientific_status.setCurrentText('synthetic'); e.generate()
    assert e.validated_path and w.atomic_provider_info
    assert e.active and not w.atomic_declaration.isChecked()


@pytest.mark.parametrize('key,value', [('radial_source',''),('radial','0'),('sigma','0'),('cf','-1'),('exchange','-1'),('l3','800'),('samples','4097'),('emin','720'),('source','')])
def test_invalid_explicit_parameters_do_not_leave_stale_source(window, key, value):
    w, _ = window; e = demo(w); e.generate(); w.atomic_declaration.setChecked(True)
    e.fields[key].setText(value)
    assert e.validated_path is None and w.atomic_provider_info is None and not w.atomic_declaration.isChecked()
    e.generate(); assert w.atomic_provider_info is None and 'blocked' in e.status.text().lower()


@pytest.mark.parametrize('edit', ['holes','reflection','nonorthogonal'])
def test_invalid_holes_and_frames_rejected(window, edit):
    w, _ = window; e = demo(w)
    if edit == 'holes': e.holes.cellWidget(3,1).setText('1.1')
    else:
        e.frame_mode.setCurrentIndex(2)
        e.frame.cellWidget(0,0).setText('-1' if edit == 'reflection' else '.9')
    e.generate(); assert not e.validated_path and w.atomic_provider_info is None


def test_element_drafts_do_not_transfer_or_restore_validation(window):
    w, _ = window; e = demo(w); e.generate()
    e.element.setCurrentIndex(e.element.findData('Co'))
    assert not e.fields['cf'].text() and not e.fields['radial'].text() and not e.fields['source'].text()
    assert e.fields['l3'].text() == '778.6' and not e.validated_path
    e.element.setCurrentIndex(e.element.findData('Fe'))
    assert e.fields['cf'].text() == '1.1' and e.fields['radial'].text() == '0.04'
    assert not e.validated_path and not w.atomic_provider_info


def test_overrides_and_tabulated_replace_confirmation(window):
    w, _ = window; e = demo(w); e.fields['l3'].setText('709.2')
    assert e.origins['l3']['origin'] == 'manual'
    with patch.object(QtWidgets.QMessageBox, 'question', return_value=QtWidgets.QMessageBox.StandardButton.No): e.apply_references()
    assert e.fields['l3'].text() == '709.2'
    with patch.object(QtWidgets.QMessageBox, 'question', return_value=QtWidgets.QMessageBox.StandardButton.Yes): e.apply_references()
    assert e.fields['l3'].text() == '708.1' and e.origins['l3']['origin'] == 'tabulated'


def test_missing_references_and_unsupported_element(window, monkeypatch):
    w, _ = window; e = w.atomic_editor
    monkeypatch.setattr('emcd_sim.gui.atomic_editor.edge_references', lambda _: {})
    e.element.setCurrentIndex(e.element.findData('Cr')); assert not e.fields['l3'].text()
    assert 'explicitly sourced' in e.edge_status.text()
    e.element.setCurrentIndex(e.element.findData('O')); assert not e.generate_button.isEnabled()
    e.generate(); assert not e.validated_path and 'unavailable' in e.status.text()


def test_energy_grid_and_gaussian_semantics(window, tmp_path):
    w, _ = window; e = demo(w)
    assert 'FWHM' in e.fields['sigma'].toolTip()
    raw = json.loads(DEMO.read_text()); raw['energy_ev'].pop(10)
    p = tmp_path/'irregular.json'; p.write_text(json.dumps(raw)); e.load_document(p)
    assert e.document()['energy_ev'] == raw['energy_ev']
    e.fields['sigma'].setText('1'); assert e.document()['energy_ev'] == raw['energy_ev']
    e.fields['emax'].setText('732'); assert e.document()['energy_ev'][-1] == 732
    e.fields['samples'].setText('2.5')
    with pytest.raises(ValueError, match='integer'): e.document()


def test_strict_json_export_import_and_manual_provenance_roundtrip(window, tmp_path):
    w, _ = window; e = demo(w); e.fields['l3'].setText('709')
    target = tmp_path/'manual.json'
    with patch.object(QtWidgets.QFileDialog,'getSaveFileName',return_value=(str(target),'')): e.export_dialog()
    doc, _ = read_document(target); e.load_document(target)
    assert e.origins['l3']['origin'] == 'manual' and e.document() == doc
    original = target.read_bytes()
    with patch.object(QtWidgets.QFileDialog,'getSaveFileName',return_value=(str(target),'')), patch.object(QtWidgets.QMessageBox,'question',return_value=QtWidgets.QMessageBox.StandardButton.No): e.export_dialog()
    assert target.read_bytes() == original


def test_cif_change_invalidates_source_and_keeps_per_element_drafts(window):
    w, _ = window; e = demo(w); e.generate(); w.atomic_declaration.setChecked(True)
    w.structure = Structure(Atoms('Fe', cell=np.eye(3)*3, pbc=True), 'Another Fe crystal'); w.refresh()
    assert not w.atomic_provider_info and not w.atomic_declaration.isChecked() and e.fields['radial'].text() == '0.04'


def test_rotated_frame_derived_axis_and_top_level_consistency(window, tmp_path):
    w, _ = window; e = demo(w); e.frame_mode.setCurrentIndex(2)
    rotation = [[1,0,0],[0,0,-1],[0,1,0]]
    for i in range(3):
        for j in range(3): e.frame.cellWidget(i,j).setText(str(rotation[i][j]))
    e.generate(); assert w.atomic_provider_info
    assert tuple(map(float,w.axis.text().split())) == (0,-1,0)
    w.atomic_declaration.setChecked(True); assert w.forward_settings().magnetization == (0,-1,0)
    w.axis.setText('0 0 1')
    with pytest.raises(ValueError): w.forward_settings()


def test_empty_missing_and_unwritable_sources_are_actionable(window, tmp_path):
    w, _ = window; w.atomic_parameter_path.clear(); w.validate_atomic_parameters()
    assert 'empty' in w.atomic_provider_status.text()
    with pytest.raises(ValueError, match='empty'): read_document('')
    with pytest.raises(ValueError, match='missing'): read_document(tmp_path/'missing.json')
    doc = json.loads(DEMO.read_text())
    with pytest.raises(ValueError, match='workspace'): persist_document('', doc)
    p = tmp_path/'not_a_directory'; p.write_text('preserve')
    with pytest.raises(OSError): persist_document(p, doc)
    assert p.read_text() == 'preserve'


def test_managed_source_tamper_never_overwritten(window):
    w, _ = window; e = demo(w); e.generate(); p = Path(e.validated_path)
    raw = p.read_bytes(); p.write_bytes(raw+b' '); e.preview()
    assert e.validated_path is None and 'checksum' in e.status.text().lower() and w.atomic_provider_info is None
    e.generate(); assert 'will not be overwritten' in e.status.text()
    assert p.read_bytes() == raw+b' '


def test_historical_ni_is_not_silently_migrated(window):
    w, _ = window
    assert not w.atomic_editor.active and not w.atomic_parameter_path.text()
    assert not w.legacy_atomic_section.isChecked()
    w.model_box.setCurrentIndex(1)
    cfg = w.forward_settings()
    assert not hasattr(cfg,'provider_schema') and cfg.atomic.l3_ev == 852.7
    w.atomic_editor.fields['radial'].setText('.04')
    with pytest.raises(ValueError, match='unvalidated edits'): w.forward_settings()


def test_imported_energy_override_cannot_claim_original_table_value(window, tmp_path):
    w, _ = window; e = demo(w)
    with patch.object(QtWidgets.QMessageBox,'question',return_value=QtWidgets.QMessageBox.StandardButton.Yes): e.apply_references()
    doc = e.document(); doc['parameters']['edge_energies_ev'][0] = 709.3
    p = tmp_path/'override.json'; p.write_text(json.dumps(doc)); e.load_document(p)
    assert e.origins['l3']['origin'] == 'imported_override_unverified'
    assert e.fields['l3'].text() == '709.3'


def test_packaged_installation_is_never_a_managed_workspace(tmp_path, monkeypatch):
    import sys
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, '_MEIPASS', str(tmp_path/'install/_internal'), raising=False)
    monkeypatch.setattr(sys, 'executable', str(tmp_path/'install/EMCD-Sim.exe'))
    with pytest.raises(ValueError, match='installation'): persist_document(tmp_path/'install', json.loads(DEMO.read_text()))
    assert not (tmp_path/'install/atomic_inputs').exists()


@pytest.mark.parametrize('channel', ['single','double'])
def test_editor_bw_ms_equivalence_and_portable_project(window, tmp_path, channel):
    from emcd_sim.gui.forward_pipeline import calculate
    from emcd_sim.gui.generalized_forward import settings_for_provider
    from emcd_sim.gui.geometry import Settings
    from emcd_sim.gui.project_io import save_project, load_project, source_status
    w, _ = window; e = demo(w); e.generate()
    cfg = replace(w.atomic_provider_info, propagation='both', channeling_model=channel, energy_scope='edges',
        grid=9, depth=5, subpixels=4, halfwidth=.7, radius=.12, centers=((.2,.2),(.2,-.2)),
        fft_grid=16, slice_step=.01, correction=False, worker_mode='manual', parallel_workers=1)
    settings = Settings(zone=(0,0,1),target=(1,1,0),voltage=200,thickness=.2,tilt=(-5,7),beam_cutoff=.6,potential_cutoff=1.2)
    original = replace(cfg, source=str(DEMO), source_sha256=hashlib.sha256(DEMO.read_bytes()).hexdigest())
    a = calculate(w.structure, settings, cfg); b = calculate(w.structure, settings, original)
    assert set(a['methods']) == {'bloch','fft-multislice'}
    for method in a['methods']:
        for key, value in a['methods'][method]['spectra'].items(): np.testing.assert_array_equal(value,b['methods'][method]['spectra'][key])
    if channel=='double':Path(cfg.source).unlink()  # Completed result's exact embedded input survives source loss.
    folder=tmp_path/'portable';save_project(a,folder)
    attachment=json.loads((folder/'project.json').read_text())['atomic_parameter_source']
    assert hashlib.sha256((folder/attachment['path']).read_bytes()).hexdigest() == cfg.source_sha256
    if Path(cfg.source).exists():Path(cfg.source).unlink()
    opened=load_project(folder); assert source_status(opened)['mdff']['verified']
    w.emcd_result=opened;w.use_result_settings()
    assert w.atomic_provider_info and w.atomic_editor.active and w.atomic_declaration.isChecked()
    assert w.atomic_provider_info.source_sha256 == cfg.source_sha256
    np.testing.assert_array_equal(w.atomic_editor.document()['parameters']['spin_resolved_holes'],json.loads(DEMO.read_text())['parameters']['spin_resolved_holes'])
    p=folder/attachment['path'];p.write_bytes(p.read_bytes()+b' ')
    with pytest.raises(ValueError, match='Missing or corrupted project file'): load_project(folder)


def test_synthetic_banner_and_sources_remain_visible_after_edit(window):
    w, _ = window; e = demo(w); e.fields['cf'].setText('1.2')
    assert 'SYNTHETIC SOFTWARE TEST' in e.validity_banner.text()
    assert 'Fe SPECTROSCOPY' in e.validity_banner.text()
    assert e.fields['source'].text() in e.validity_banner.text()
    assert e.fields['validity'].text() in e.validity_banner.text()


def test_source_path_edit_invalidates_editor_preview(window):
    w, _ = window; e = demo(w); e.generate()
    w.atomic_parameter_path.setText('changed.json')
    assert not e.validated_path and not w.atomic_provider_info and not w.atomic_declaration.isChecked()


def test_old_managed_source_cannot_be_overwritten_by_export(window):
    w, _ = window; e = demo(w); e.generate(); p=Path(e.validated_path); raw=p.read_bytes()
    e.fields['cf'].setText('2')
    with patch.object(QtWidgets.QFileDialog,'getSaveFileName',return_value=(str(p),'')), patch.object(QtWidgets.QMessageBox,'question',return_value=QtWidgets.QMessageBox.StandardButton.Yes): e.export_dialog()
    assert p.read_bytes()==raw and 'immutable' in e.status.text()


@pytest.mark.parametrize('count',[float('inf'),float('nan'),True,2.5,4097])
def test_invalid_grid_count_is_rejected_without_allocation(count):
    with pytest.raises(ValueError,match='integer'): explicit_grid(700,730,count)
