"""Focused Stage B real-kernel, source, atomic reversal and Qt lifecycle checks."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest,uuid,threading,importlib.util
if not all(importlib.util.find_spec(n) for n in ('ase','PySide6')):raise unittest.SkipTest('Install .[gui] for desktop checks')
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PySide6 import QtWidgets
from emcd_sim.gui.emcd_forward import *
from emcd_sim.gui.app import MainWindow
from emcd_sim.gui.geometry import orientation
from emcd_sim.elastic import depth_coherence
from legacy_geometry import Ni017Geometry,rotated_tensor
from emcd_sim.ni_local_mdff import ni_local_transitions
from emcd_sim.mdff_tensor import dipole_tensor_from_transitions
from emcd_sim.single_channeling_tensor import run_tensor_with_coherence


class ForwardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.structure=Structure.nickel();cls.settings=Settings(beam_cutoff=2.2,potential_cutoff=2.2,voltage=200,tilt=(-7.116725439974256,0))
        cls.cfg=ForwardSettings(energy_points=17,grid=17,depth=12,subpixels=16,axis_declared=True)
        cls.result=calculate(cls.structure,cls.settings,cls.cfg)
    def test_source_native_and_independent_import_validation(self):
        info=inspect_source(DEFAULT_SOURCE)
        self.assertEqual(info['selected'],dict(L3=831.271,L2=848.698))
        folder=Path('outputs')/('gui_b_source_'+uuid.uuid4().hex);folder.mkdir();path=folder/'independent.txt'
        source=load_wien2k_xmcd(DEFAULT_SOURCE);e=source.energy_ev-100
        np.savetxt(path,np.column_stack((e,source.right,source.left,source.right-source.left,source.right+source.left)))
        info=inspect_source(path);self.assertIsNone(info['audit']);self.assertAlmostEqual(info['selected']['L3'],731.271)
        cfg=replace(self.cfg,source=str(path),l3=731.271,l2=748.698,axis_declared=False)
        with self.assertRaises(ValueError):tensors(cfg,energy_grid(cfg),np.eye(3))
        with self.assertRaises(ValueError):energy_grid(replace(cfg,l3=831.271))
        with self.assertRaises(ValueError):energy_grid(replace(cfg,source_sha256='bad'))
        np.savetxt(path,np.ones((5,4)))
        with self.assertRaises(ValueError):inspect_source(path)
    def test_rotation_reversal_and_psd(self):
        R=orientation(self.structure.atoms.cell.array,(0,1,7));e=np.array([831.271,848.698])
        p,m=tensors(self.cfg,e,R)
        np.testing.assert_allclose(p.tensor_angstrom2_per_ev,rotated_tensor(DEFAULT_SOURCE,e).tensor_angstrom2_per_ev,atol=1e-15)
        np.testing.assert_allclose(m.tensor_angstrom2_per_ev,p.tensor_angstrom2_per_ev.conj(),atol=1e-15)
        self.assertGreaterEqual(np.linalg.eigvalsh(p.tensor_angstrom2_per_ev).min(),-1e-15)
        np.testing.assert_allclose(R@np.array([0,0,1]),[0,-1/np.sqrt(50),7/np.sqrt(50)])
    def test_atomic_transition_level_exchange_and_holes(self):
        config=NiLocalConfig(exchange_split_ev=.7,eg_up_holes=.13,eg_down_holes=.61,t2g_up_holes=.27,t2g_down_holes=.72)
        p,m=[ni_local_transitions(config,magnetization_sign=s) for s in (1,-1)]
        # Same fixed quantum amplitudes and transition ordering, opposite exchange
        # energy shifts about each edge/orbital centroid; spin holes swap.
        np.testing.assert_array_equal(p.dipoles_angstrom,m.dipoles_angstrom)
        self.assertTrue(np.allclose(abs(p.energy_ev-m.energy_ev),.7))
        for up,down in ((.13,.61),(.27,.72)):
            np.testing.assert_allclose(m.weights[p.weights==up],down);np.testing.assert_allclose(m.weights[p.weights==down],up)
        e=np.linspace(845,879,99);a,b=[dipole_tensor_from_transitions(t,e,.8).tensor_angstrom2_per_ev for t in (p,m)]
        np.testing.assert_allclose(b,a.conj(),rtol=1e-12,atol=1e-18)
        np.testing.assert_allclose(a,a.swapaxes(-1,-2).conj(),atol=1e-18)
        self.assertGreaterEqual(np.linalg.eigvalsh(a).min(),-1e-18)
        cfg=replace(self.cfg,model='atomic',atomic=config,l3=config.l3_ev,l2=config.l2_ev,correction=False)
        result=calculate(self.structure,self.settings,cfg)
        for key in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus'):self.assertGreaterEqual(result['spectra'][key].min(),-1e-18)
    def test_coherence_core_contraction_map_integrals_and_parity(self):
        r=self.result;e=r['spectra']['energy_ev'];model=r['model']
        np.testing.assert_allclose(r['coherence'],depth_coherence(model.elastic,30,12),atol=1e-15)
        core=run_tensor_with_coherence(model,rotated_tensor(DEFAULT_SOURCE,e),r['coherence'],thickness_nm=30,grid_size=17,reference_energy_ev=self.cfg.l3,integration_mode='fractional',aperture_subpixels=16)
        np.testing.assert_allclose(core.chiral_spectrum('A'),r['spectra']['I_A_plus'],rtol=1e-13)
        dq2=(r['qx'][0,1]-r['qx'][0,0])**2
        for edge,energy in (('L3',self.cfg.l3),('L2',self.cfg.l2)):
            i=int(np.argmin(abs(e-energy)));m=r['maps'][edge]
            for d in ('A','B'):
                for sign in ('plus','minus'):
                    self.assertAlmostEqual(float(np.sum(m['I_'+sign]*r['weights'][d])*dq2),r['spectra']['I_'+d+'_'+sign][i],places=14)
        s=r['spectra'];np.testing.assert_allclose(s['D_raw'],s['D_mag']+s['D_nonmag'],atol=1e-16)
    def test_manual_apertures_and_invalid_correction(self):
        cfg=replace(self.cfg,centers=((.2,.3),(.4,-.2)),window=(900.,910.))
        r=calculate(self.structure,self.settings,cfg)
        self.assertIsNone(r['metadata']['alpha']);self.assertIn('disabled',r['metadata']['correction_reason'])
        self.assertNotIn('D_raw',r['maps']['L3']);self.assertIn('D_raw',r['spectra'])
        self.assertFalse(np.allclose(r['spectra']['I_A_plus'],self.result['spectra']['I_A_plus']))
    def test_export_no_pickle_and_no_plot_mutation(self):
        r=self.result;before={edge:{k:v.copy() for k,v in m.items()} for edge,m in r['maps'].items()}
        folder=Path('outputs')/('gui_b_export_'+uuid.uuid4().hex);export_result(r,folder)
        for name in ('angular_maps','virtual_detector_eels'):
            with np.load(folder/(name+'.npz'),allow_pickle=False) as f:
                for key in f.files:self.assertNotEqual(f[key].dtype.kind,'O')
        for edge,m in before.items():
            for key,v in m.items():np.testing.assert_array_equal(v,r['maps'][edge][key])
        self.assertTrue((folder/'L3_angular_maps.png').exists())
    def test_gates_and_memory(self):
        changed=Structure.nickel();changed.atoms.cell*=1.1;self.assertTrue(material_reason(changed))
        with self.assertRaisesRegex(ValueError,'512 MiB'):calculate(self.structure,Settings(beam_cutoff=6.5),replace(self.cfg,grid=97,memory_budget_mib=512))


class WorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    def setUp(self):self.w=MainWindow(workspace=Path('outputs')/('stage_b_worker_'+uuid.uuid4().hex));self.w.declaration.setChecked(True);self.w.error=lambda s:None
    def tearDown(self):
        if self.w.busy:self.w.cancel();self.w.worker.wait(5000);self.app.processEvents()
        self.w.close();self.app.processEvents()
    def test_cancel_and_failed_not_completed(self):
        entered=threading.Event();release=threading.Event();w=self.w
        def blocked(*args,**kwargs):entered.set();release.wait(5);return {'not':'registered'}
        with patch('emcd_sim.gui.stage_b.calculate',blocked):
            w.start_emcd();self.assertTrue(entered.wait(5));w.cancel();release.set();self.assertTrue(w.worker.wait(5000));self.app.processEvents()
        self.assertIsNone(w.emcd_result);self.assertFalse(w.busy);self.assertEqual(w.progress.value(),0)
        with patch('emcd_sim.gui.stage_b.calculate',side_effect=ValueError('Failure check')):
            w.start_emcd();self.assertTrue(w.worker.wait(5000));self.app.processEvents()
        self.assertIsNone(w.emcd_result);self.assertEqual(w.run_outcome,'failed');self.assertEqual(w.progress.value(),0)
    def test_snapshot_stale_and_model_switch_geometry(self):
        w=self.w;s=w.settings();w.model_box.setCurrentIndex(1);self.assertEqual(w.settings(),s)
        self.assertEqual(w.spin['atomic_l3_ev'].value(),852.7);self.assertFalse(w.correction.isChecked())
        r=ForwardTests.result;w.emcd_result=r;w.maps_view.result=r;w.eels_view.result=r
        original_tilt=r['settings'].tilt
        w.spin['tx'].setValue(-8);self.assertIn('STALE',w.eels_view.label.text());self.assertEqual(r['settings'].tilt,original_tilt)

    def test_real_worker_display_and_detector_recalculation(self):
        w=self.w;w.numerical_mode.setCurrentIndex(1)
        w.set_values(dict(beam=2.2,energy=17,grid=17,depth=12,subpixels=16));w.refresh()
        w.start_emcd();self.assertTrue(w.worker.wait(15000));self.app.processEvents()
        self.assertEqual(w.run_outcome,'completed');self.assertTrue(w.tabs.isTabEnabled(2))
        old=w.emcd_result['spectra']['I_A_plus'].copy();w.spin['ax'].setValue(.4)
        self.assertIn('STALE',w.eels_view.label.text())
        w.start_emcd();self.assertTrue(w.worker.wait(15000));self.app.processEvents()
        self.assertEqual(w.run_outcome,'completed');self.assertFalse(np.allclose(old,w.emcd_result['spectra']['I_A_plus']))
        self.assertNotIn('D_raw',w.emcd_result['maps']['L3']);self.assertFalse(w.busy)


if __name__=='__main__':unittest.main()
