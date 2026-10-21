"""Stage D persistence and scientific comparison using compact real fixtures."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest,uuid,json,threading
import importlib.util
if not all(importlib.util.find_spec(name) for name in ('ase','PySide6')):raise unittest.SkipTest('Stage D requires the optional .[gui] dependencies')
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
from contextlib import ExitStack
import numpy as np
from PySide6 import QtWidgets,QtCore
from matplotlib.figure import Figure
from emcd_sim.gui.emcd_forward import calculate,ForwardSettings,DEFAULT_SOURCE
from emcd_sim.gui.geometry import Structure,Settings
from emcd_sim.gui.project_io import *
from emcd_sim.gui.results_browser import Registry
from emcd_sim.gui.compare_results import map_compatibility,draw_saved_comparison,scalar_rows,export_comparison_data
from emcd_sim.gui.app import MainWindow
from emcd_sim.gui.results import draw_maps,draw_eels

ROOT=Path('outputs/gui_stage_d')/('tests_'+uuid.uuid4().hex)


def no_solvers():
    stack=ExitStack()
    for name in ('emcd_sim.physical_elastic.PhysicalElasticModel.amplitudes','emcd_sim.multislice_reference.fft_multislice_ni','emcd_sim.gui.emcd_forward.tensors','emcd_sim.gui.emcd_forward.calculate'):
        stack.enter_context(patch(name,side_effect=AssertionError('Forward solver called during read/compare')))
    return stack


class ProjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ROOT.mkdir(parents=True);cfg=ForwardSettings(propagation='both',axis_declared=True,source_sha256=sha256(DEFAULT_SOURCE),energy_points=17,grid=17,depth=12,subpixels=16)
        cls.result=calculate(Structure.nickel(),Settings(),cfg)
        cls.atomic=calculate(Structure.nickel(),Settings(),replace(cfg,model='atomic',propagation='fft-multislice',l3=852.7,l2=870.,correction=False))
        cls.second=calculate(Structure.nickel(),replace(Settings(),tilt=(-6.5,0)),replace(cfg,energy_points=17))
        cls.folder=ROOT/'complete';save_project(cls.result,cls.folder);save_project(cls.second,ROOT/'second_complete')
    def assert_equal(self,a,b):
        self.assertEqual(list(a['methods']),list(b['methods']))
        for name,m in a['methods'].items():
            n=b['methods'][name]
            for k in ('qx','qy','coherence','amplitudes','depth_nm'):np.testing.assert_array_equal(m[k],n[k])
            for k,v in m['spectra'].items():np.testing.assert_array_equal(v,n['spectra'][k])
            for edge,fields in m['maps'].items():
                for k,v in fields.items():np.testing.assert_array_equal(v,n['maps'][edge][k])
            self.assertEqual(m['metadata']['alpha'],n['metadata']['alpha']);np.testing.assert_array_equal(m['model'].elastic.reciprocal_vectors_xy,n['model'].elastic.reciprocal_vectors_xy)
    def test_all_four_modes_roundtrip_complex_and_structure(self):
        cases=dict(both=self.result,atomic=self.atomic)
        for name in ('bloch','fft-multislice'):
            m=self.result['methods'][name];cases[name]=dict(m,methods={name:m},comparison={},fft=self.result['fft'] if name=='fft-multislice' else {})
        for key,result in cases.items():
            path=ROOT/key;save_project(result,path)
            with no_solvers():opened=load_project(path)
            self.assert_equal(result,opened)
            self.assertTrue(np.iscomplexobj(opened['coherence']));self.assertFalse(opened['coherence'].flags.writeable)
            restored=restore_structure(opened['structure_snapshot']);np.testing.assert_array_equal(restored.atoms.cell.array,Structure.nickel().atoms.cell.array)
            np.testing.assert_array_equal(restored.atoms.get_scaled_positions(),Structure.nickel().atoms.get_scaled_positions())
            for filename in ARRAY_FILES:
                with np.load(path/filename,allow_pickle=False) as data:
                    for k in data.files:self.assertFalse(data[k].dtype.hasobject)
    def test_external_sources_missing_no_recomputation(self):
        path=ROOT/'source_copy.xmcd';path.write_bytes(DEFAULT_SOURCE.read_bytes());cfg=replace(self.result['config'],source=str(path),source_sha256=sha256(path))
        changed=dict(self.result,config=cfg,methods={n:dict(m,config=cfg,metadata=dict(m['metadata'],mdff=asdict(cfg))) for n,m in self.result['methods'].items()},metadata=dict(self.result['metadata'],mdff=asdict(cfg)))
        save_project(changed,ROOT/'missing_source');path.unlink()
        with no_solvers():opened=load_project(ROOT/'missing_source');draw_maps(Figure(figsize=(12,8),layout='constrained'),opened,'L3');draw_eels(Figure(figsize=(10,8)),opened,method='overlay')
        self.assertIn('source unavailable',rerun_reason(opened));self.assertFalse(source_status(opened)['xmcd']['available']);self.assert_equal(changed,opened)
    def test_missing_corrupt_manifest_and_shapes(self):
        for kind in ('missing','corrupt','schema','shape'):
            path=ROOT/kind;save_project(self.result,path)
            if kind=='missing':(path/'diffraction_pattern.npz').unlink()
            elif kind=='corrupt':(path/'virtual_detector_eels.npz').write_bytes(b'not npz')
            elif kind=='schema':
                m=json.loads((path/'project.json').read_text());m['schema_version']=999;(path/'project.json').write_text(json.dumps(m))
            else:
                m=json.loads((path/'project.json').read_text());m['arrays']['angular_maps.npz']['qx']['shape']=[999,999];(path/'project.json').write_text(json.dumps(m))
            with self.assertRaises(ValueError):load_project(path)
    def test_missing_cif_and_hash_verified_reconnection(self):
        from ase.io import write
        original=ROOT/'original_Ni.cif';relocated=ROOT/'relocated_Ni.cif';write(original,Structure.nickel().atoms,format='cif');relocated.write_bytes(original.read_bytes())
        structure=Structure.from_cif(original)
        result=calculate(structure,Settings(),replace(self.result['config'],propagation='bloch',grid=9,depth=4,energy_points=9))
        save_project(result,ROOT/'cif_project');original.unlink()
        with no_solvers():opened=load_project(ROOT/'cif_project')
        self.assertFalse(source_status(opened)['cif']['available']);self.assertIn('cif',rerun_reason(opened));self.assert_equal(result,opened)
        opened['source_overrides']={'cif':str(relocated)};self.assertEqual(rerun_reason(opened),'')
        opened['source_overrides']['cif']=str(DEFAULT_SOURCE);self.assertIn('mismatch',rerun_reason(opened))
    def test_atomic_save_failure_and_cancellation_preserve_existing(self):
        before=sha256(self.folder/'project.json')
        with patch('emcd_sim.gui.project_io.np.savez_compressed',side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):save_project(self.result,self.folder,replace_existing=True)
        self.assertEqual(before,sha256(self.folder/'project.json'))
        with self.assertRaises(Cancelled):save_project(self.result,self.folder,replace_existing=True,cancelled=lambda:True)
        self.assertEqual(before,sha256(self.folder/'project.json'))
        with self.assertRaises(FileExistsError):save_project(self.result,self.folder)
        self.assertEqual([],list(ROOT.glob('.complete.saving_*')))
        (self.folder/'notes.txt').write_text('User notes must survive Save')
        figures=self.folder/'figures';figures.mkdir();(figures/'README.txt').write_text('User figure attachments')
        save_project(self.result,self.folder,replace_existing=True)
        self.assertEqual((self.folder/'notes.txt').read_text(),'User notes must survive Save')
        self.assertTrue((self.folder/'figures/README.txt').exists());self.assert_equal(self.result,load_project(self.folder))
        (self.folder/'notes.txt').write_text('Notes are not physical-data integrity inputs');load_project(self.folder)
    def test_replacement_failure_rolls_back(self):
        path=ROOT/'rollback';save_project(self.result,path);before=sha256(path/'project.json');rename=Path.rename
        def fail_final(p,target):
            if '.saving_' in p.name and Path(target)==path.resolve():raise OSError('Final rename blocked')
            return rename(p,target)
        with patch.object(Path,'rename',fail_final):
            with self.assertRaises(OSError):save_project(self.second,path,replace_existing=True)
        self.assertEqual(before,sha256(path/'project.json'));load_project(path)
    def test_legacy_readonly_without_fabricated_snapshot(self):
        for source in ('outputs/gui_stage_b/xmcd_20261015_234528','outputs/gui_stage_c/windows_20261016_000116/xmcd_both'):
            source=Path(source)
            if not source.exists():continue
            before={p.name:sha256(p) for p in source.iterdir() if p.is_file()}
            with no_solvers():result=load_project(source,legacy=True)
            self.assertTrue(result['read_only_legacy']);self.assertIsNone(result['structure_snapshot']);self.assertTrue(result['project_warnings']);self.assertTrue(rerun_reason(result))
            self.assertEqual(before,{p.name:sha256(p) for p in source.iterdir() if p.is_file()})
    def test_comparison_compatibility_and_unshifted_eels(self):
        a=self.result['methods']['bloch'];b=self.second['methods']['bloch'];valid,why=map_compatibility(a,b,'L3','I_mag');self.assertTrue(valid,why)
        shifted=dict(b,qx=b['qx']+.001);self.assertFalse(map_compatibility(a,shifted,'L3','I_mag')[0])
        other=self.atomic['methods']['fft-multislice'];self.assertFalse(map_compatibility(a,other,'L3','I_mag')[0])
        before=a['spectra']['D_mag'].copy();fig=Figure(figsize=(14,10),layout='constrained');entries=[('Reference',a,'bloch'),('Mistilt',b,'bloch')]
        with no_solvers():draw_saved_comparison(fig,entries);rows=scalar_rows(entries)
        np.testing.assert_array_equal(before,a['spectra']['D_mag']);np.testing.assert_array_equal(fig.axes[3].lines[0].get_ydata(),before)
        self.assertEqual(fig.axes[0].images[0].get_clim(),fig.axes[1].images[0].get_clim())
        np.testing.assert_array_equal(fig.axes[2].images[0].get_array(),a['maps']['L3']['I_mag']-b['maps']['L3']['I_mag'])
        self.assertIn('A_raw_plus_sum',rows[0]);self.assertIn('relative_detectability_proxy',rows[0])
        export_comparison_data(entries,ROOT/'comparison_csv');self.assertTrue((ROOT/'comparison_csv/scalar_metrics.csv').exists())
    def test_registry_rename_remove_missing_path(self):
        path=ROOT/'registry.json';registry=Registry(path);record=registry.register(self.result,self.folder);before=sha256(self.folder/'project.json');registry.rename(record['id'],'User display name')
        registry=Registry(path);self.assertEqual(registry.records[0]['name'],'User display name');self.assertEqual(before,sha256(self.folder/'project.json'))
        registry.records[0]['path']=str(ROOT/'moved_project');registry.persist();self.assertEqual(len(Registry(path).records),1)
        registry.remove(record['id']);self.assertTrue(self.folder.exists());self.assertEqual(Registry(path).records,[])


class ZWorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        if not hasattr(ProjectTests,'result'):ProjectTests.setUpClass()
    def setUp(self):self.workspace=ROOT/('ui_'+uuid.uuid4().hex);self.w=MainWindow(workspace=self.workspace);self.w.error=lambda message:None
    def tearDown(self):
        if self.w.busy:self.w.cancel();self.w.worker.wait(15000);self.app.processEvents()
        self.w.close();self.app.processEvents()
    def wait_io(self):
        self.assertTrue(self.w.worker.wait(15000));self.app.processEvents();self.app.processEvents();self.assertFalse(self.w.busy)
    def test_project_selection_inputs_and_use_settings_without_solver(self):
        w=self.w;s=w.settings();row=w.browser.register(ProjectTests.second,ROOT/'second_complete',name='Tilted result')
        with no_solvers():w.display_saved_result(ProjectTests.second,row)
        self.assertEqual(s,w.settings());self.assertIn('current inputs differ',w.maps_view.label.text())
        with no_solvers():w.use_result_settings()
        np.testing.assert_allclose(w.settings().tilt,ProjectTests.second['settings'].tilt,atol=1e-9);self.assertFalse(w.busy)
        before=w.settings();w.close();w=MainWindow(workspace=self.workspace);self.w=w;w.error=lambda message:None
        self.assertEqual(len(w.browser.registry.records),1)
        self.assertEqual(w.settings().zone,Settings().zone)
    def test_threaded_open_failed_load_preserves_previous(self):
        w=self.w;w.emcd_result=ProjectTests.second
        with no_solvers():w.open_project_path(ProjectTests.folder);self.wait_io()
        self.assertTrue(w._io_success);self.assert_equal_selected(ProjectTests.result)
        valid=w.emcd_result;w.open_project_path(ROOT/'missing_project');self.wait_io();self.assertIs(w.emcd_result,valid);self.assertFalse(w._io_success)
    def assert_equal_selected(self,result):
        for key,value in result['spectra'].items():np.testing.assert_array_equal(value,self.w.emcd_result['spectra'][key])
    def test_background_save_register_compare_no_physics(self):
        w=self.w;w.emcd_result=ProjectTests.result;w.register_completed(ProjectTests.result);w.save_to_path(ROOT/('ui_save_'+uuid.uuid4().hex));self.wait_io()
        self.assertEqual(len(Registry(self.workspace/'results_index.json').records),1)
        first=w.selected_record;second=w.browser.register(ProjectTests.second,ROOT/'second_complete',name='Mistilt')
        for i in range(w.browser.table.rowCount()):
            idx=w.browser.table.model().index(i,0);w.browser.table.selectionModel().select(idx,QtCore.QItemSelectionModel.SelectionFlag.Select|QtCore.QItemSelectionModel.SelectionFlag.Rows)
        with no_solvers():w.compare_selected();self.wait_io()
        self.assertEqual(w.tabs.tabText(w.tabs.currentIndex()),'Compare saved runs');self.assertEqual(w.tabs.currentWidget().entries()[0][1]['config'].model,'xmcd')
    def test_cancel_load_keeps_completed_result(self):
        w=self.w;w.emcd_result=ProjectTests.result;entered=threading.Event();release=threading.Event()
        def blocked(*a,**k):entered.set();release.wait(5);return ProjectTests.second
        with patch('emcd_sim.gui.results_browser.load_project',blocked):
            w.open_project_path(ProjectTests.folder);self.assertTrue(entered.wait(5));w.cancel();release.set();self.wait_io()
        self.assertIs(w.emcd_result,ProjectTests.result);self.assertEqual(w.progress.value(),0)
    def test_atomic_settings_do_not_require_unused_xmcd(self):
        w=self.w;w.display_saved_result(ProjectTests.atomic)
        with no_solvers():w.use_result_settings()
        self.assertEqual(w.forward_settings().model,'atomic');self.assertIsNone(w.source_info);self.assertTrue(w.emcd_button.isEnabled());self.assertFalse(w.busy)


if __name__=='__main__':unittest.main()
