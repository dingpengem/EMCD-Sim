"""Focused Stage C: genuine oriented FFT waves, shared MDFF, GUI and exports."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest,uuid,threading,importlib.util
if not all(importlib.util.find_spec(n) for n in ('ase','PySide6')):raise unittest.SkipTest('Install .[gui] for desktop checks')
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
import numpy as np
from matplotlib.figure import Figure
from PySide6 import QtWidgets
from emcd_sim.gui.emcd_forward import *
from emcd_sim.gui.propagation import numerical_info,error_pair
from emcd_sim.gui.results import draw_maps,draw_eels,draw_diffraction
from emcd_sim.gui.app import MainWindow
from emcd_sim.ni_017_geometry import Ni017Geometry
from emcd_sim.multislice_reference import fft_multislice_ni,_projected_ni_potential
from emcd_sim.multislice_emcd_reference import project_fft_amplitudes,coherence_from_amplitudes


class PropagationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.structure=Structure.nickel();cls.settings=Settings();cls.cfg=ForwardSettings(propagation='both',energy_points=17,grid=17,depth=12,subpixels=16,axis_declared=True)
        cls.result=calculate(cls.structure,cls.settings,cls.cfg)
    def test_actual_oriented_potential_and_common_projection(self):
        r=self.result;geo=Ni017Geometry();u,hkl,g=_projected_ni_potential(32,200,0,2.2,geo)
        np.testing.assert_allclose(geo.crystal.lattice_angstrom,r['model'].elastic.crystal.lattice_angstrom,atol=1e-14)
        coefficients=np.fft.fft2(u).ravel()/32**2;lookup={tuple(h):i for i,h in enumerate(hkl)}
        # Off-diagonal finite BW Hamiltonian is the exact same IAM coefficient.
        H=r['model'].elastic.hamiltonian_nm_inv();common=r['model'].elastic.beams.hkl
        for i,a in enumerate(common):
            for j,b in enumerate(common):
                if i!=j:
                    delta=tuple(x-y for x,y in zip(a,b))
                    expected=coefficients[lookup[delta]] if delta in lookup else 0
                    self.assertAlmostEqual(abs(H[i,j]-expected),0,places=12)
        self.assertTrue(np.all(hkl[:,1]+7*hkl[:,2]==0));self.assertIn((1,7,-1),lookup)
        fft=fft_multislice_ni(r['depth_nm'],acceleration_kv=200,tilt_mrad_xy=self.settings.tilt,grid_points=32,slice_step_nm=.04,potential_cutoff_inv_angstrom=2.2,return_amplitudes=True,projected_geometry=geo)
        psi,out=project_fft_amplitudes(fft,common)
        np.testing.assert_array_equal(psi,r['methods']['fft-multislice']['amplitudes'])
        np.testing.assert_array_equal(out,r['fft']['excluded_intensity'])
        np.testing.assert_allclose(np.sum(abs(psi)**2,axis=1)+out,fft.intensity.sum(axis=1),atol=1e-15)
        self.assertGreater(out.max(),1e-9);self.assertFalse(r['fft']['summary']['renormalized'])
        np.testing.assert_array_equal(psi,fft.amplitudes[:,[lookup[h] for h in common]])
    def test_tensor_reuse_once_and_bw_legacy(self):
        self.assertEqual(ForwardSettings('atomic').model,'atomic')
        cfg=replace(self.cfg,energy_points=9,grid=9,depth=8)
        with patch('emcd_sim.gui.emcd_forward.tensors',wraps=tensors) as build:
            both=calculate(self.structure,self.settings,cfg)
            self.assertEqual(build.call_count,1)
        bw=calculate(self.structure,self.settings,replace(cfg,propagation='bloch'))
        for k,v in bw['spectra'].items():np.testing.assert_array_equal(v,both['methods']['bloch']['spectra'][k])
        self.assertIs(both['spectra'],both['methods']['bloch']['spectra'])
        self.assertEqual(both['methods']['bloch']['config'],both['methods']['fft-multislice']['config'])
    def test_coherences_spectra_parity_and_map_integrals(self):
        r=self.result
        for name,m in r['methods'].items():
            C=m['coherence'];np.testing.assert_allclose(C,C.conj().T,atol=1e-15);self.assertGreaterEqual(np.linalg.eigvalsh(C).min(),-1e-15)
            np.testing.assert_array_equal(C,coherence_from_amplitudes(m['depth_nm'],m['amplitudes']))
            s=m['spectra'];np.testing.assert_allclose(s['D_raw'],s['D_mag']+s['D_nonmag'],atol=1e-16)
            for edge,energy in (('L3',self.cfg.l3),('L2',self.cfg.l2)):
                i=int(np.argmin(abs(s['energy_ev']-energy)));dq2=(m['qx'][0,1]-m['qx'][0,0])**2
                for d in ('A','B'):
                    for sign in ('plus','minus'):
                        integral=np.sum(m['maps'][edge]['I_'+sign]*m['weights'][d])*dq2
                        self.assertAlmostEqual(float(integral),s['I_'+d+'_'+sign][i],places=14)
        np.testing.assert_array_equal(r['methods']['bloch']['weights']['A'],r['methods']['fft-multislice']['weights']['A'])
        self.assertLess(r['comparison']['coherence']['l2_relative'],2e-4)
        self.assertLess(r['comparison']['edges']['L3']['maps']['I_mag']['l2_relative'],.002)
        self.assertIsNone(r['comparison']['edges']['L3']['detector']['D_nonmag']['relative'])
        self.assertIsNone(error_pair([0],[1e-20],1e-10)['l2_relative'])
    def test_ms_only_atomic_reversal_and_manual_detectors(self):
        cfg=replace(self.cfg,model='atomic',propagation='both',l3=852.7,l2=870.,energy_points=9,grid=9,depth=8,centers=((.2,.3),(.4,-.2)),correction=False)
        r=calculate(self.structure,self.settings,cfg)
        for m in r['methods'].values():
            self.assertNotIn('D_raw',m['maps']['L3']);s=m['spectra'];np.testing.assert_allclose(s['D_raw'],s['D_mag']+s['D_nonmag'],atol=1e-19)
            self.assertGreater(np.max(abs(s['D_mag'])),1e-10)
            for k in ('I_A_plus','I_B_plus','I_A_minus','I_B_minus'):self.assertGreaterEqual(s[k].min(),-1e-20)
        with patch('emcd_sim.physical_elastic.PhysicalElasticModel.amplitudes',side_effect=AssertionError('BW called in MS-only')):
            ms=calculate(self.structure,self.settings,replace(cfg,propagation='fft-multislice'))
        for k,v in ms['spectra'].items():np.testing.assert_array_equal(v,r['methods']['fft-multislice']['spectra'][k])
    def test_reject_orientation_fft_coverage_and_memory(self):
        with self.assertRaisesRegex(ValueError,'017'):calculate(self.structure,replace(self.settings,zone=(0,0,1)),self.cfg)
        for cfg in (replace(self.cfg,fft_grid=13),replace(self.cfg,fft_grid=12),replace(self.cfg,slice_step=0)):
            with self.assertRaises(ValueError):calculate(self.structure,self.settings,cfg)
        self.assertEqual(numerical_info(self.structure,self.settings,self.cfg)['fft_harmonics'],1024)
        with self.assertRaisesRegex(ValueError,'512 MiB'):numerical_info(self.structure,self.settings,replace(self.cfg,grid=97,memory_budget_mib=512,propagation='bloch'),hkl=tuple(range(100)))
    def test_shared_scales_difference_maps_and_export(self):
        r=self.result;figs=[Figure(figsize=(14,9),layout='constrained') for _ in range(3)]
        for f,name in zip(figs,('bloch','fft-multislice','difference')):draw_maps(f,r,'L3',name,field='I_mag')
        self.assertEqual(figs[0].axes[0].images[0].get_clim(),figs[1].axes[0].images[0].get_clim())
        np.testing.assert_array_equal(figs[2].axes[0].images[0].get_array(),r['methods']['bloch']['maps']['L3']['I_mag']-r['methods']['fft-multislice']['maps']['L3']['I_mag'])
        draw_eels(figs[0],r,method='overlay');self.assertEqual(len([x for x in figs[0].axes[0].lines if 'Detector A' in x.get_label()]),2)
        draw_diffraction(figs[1],r,'fft-multislice',True)
        root=Path('outputs')/('gui_c_export_'+uuid.uuid4().hex);export_result(r,root,advanced=True)
        for name in ('angular_maps','virtual_detector_eels','diffraction_pattern'):
            with np.load(root/(name+'.npz'),allow_pickle=False) as f:
                self.assertEqual(f['method_labels'].tolist(),['bloch','fft-multislice'])
                for k in f.files:self.assertNotEqual(f[k].dtype.kind,'O')
        self.assertTrue((root/'bw_ms_comparison.png').exists());self.assertTrue((root/'comparison_metadata.json').exists())


class ZGUIStageCTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        if not hasattr(PropagationTests,'result'):PropagationTests.setUpClass()
    def setUp(self):self.w=MainWindow(workspace=Path('outputs')/('stage_c_worker_'+uuid.uuid4().hex));self.w.declaration.setChecked(True);self.w.error=lambda s:None
    def tearDown(self):
        if self.w.busy:self.w.cancel();self.w.worker.wait(10000);self.app.processEvents()
        self.w.close();self.app.processEvents()
    def test_method_controls_and_completed_view_switching(self):
        w=self.w;s=w.settings();self.assertEqual(w.forward_settings().propagation,'bloch');w.propagation_box.setCurrentIndex(2)
        self.assertEqual(w.settings(),s);self.assertEqual(w.forward_settings().fft_grid,32)
        r=PropagationTests.result;w.emcd_result=r
        for view in (w.maps_view,w.eels_view,w.diffraction_view,w.overview_view):view.set_result(r)
        self.assertEqual(w.maps_view.method.count(),3);w.maps_view.method.setCurrentIndex(2);self.assertEqual(w.maps_view.method.currentData(),'difference')
        self.assertEqual(w.eels_view.method.currentData(),'bloch');w.eels_view.method.setCurrentIndex(2)
        self.assertEqual(w.eels_view.method.currentData(),'overlay');w.diffraction_view.choice.setCurrentIndex(1)
        w.spin['grid'].setValue(17);w.zone.setText('0 0 1');w.refresh();self.assertFalse(w.emcd_button.isEnabled());self.assertIn('017',w.emcd_button.toolTip())
        w.propagation_box.setCurrentIndex(0);self.assertTrue(w.emcd_button.isEnabled())
    def test_cancel_partial_comparison_preserves_prior_result_and_failure(self):
        w=self.w;prior=PropagationTests.result;w.emcd_result=prior;w.propagation_box.setCurrentIndex(2)
        entered=threading.Event();release=threading.Event()
        def blocked(*args):entered.set();release.wait(5);return {'partial':True}
        with patch('emcd_sim.gui.stage_b.calculate',blocked):
            w.start_emcd();self.assertTrue(entered.wait(5));w.cancel();release.set();self.assertTrue(w.worker.wait(10000));self.app.processEvents()
        self.assertIs(w.emcd_result,prior);self.assertEqual(w.progress.value(),0)
        with patch('emcd_sim.gui.stage_b.calculate',side_effect=ValueError('FFT failure')):
            w.start_emcd();self.assertTrue(w.worker.wait(5000));self.app.processEvents()
        self.assertIs(w.emcd_result,prior);self.assertEqual(w.run_outcome,'failed')
    def test_real_cancellation_between_bw_and_ms_contracts(self):
        events=[]
        def progress(stage):events.append(stage)
        with self.assertRaises(Cancelled):calculate(Structure.nickel(),Settings(),replace(PropagationTests.cfg,energy_points=9,grid=9),progress,lambda:any('Calculating fft-multislice EELS' in x for x in events))
        self.assertTrue(any('Calculating bloch EELS' in x for x in events))


if __name__=='__main__':unittest.main()
