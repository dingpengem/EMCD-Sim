"""Display-only acceptance. No forward solver fixtures or numerical reruns."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest, json, csv, uuid, hashlib, importlib.util
from pathlib import Path
from types import SimpleNamespace
from dataclasses import replace
from contextlib import ExitStack
from unittest.mock import patch
import numpy as np
from emcd_sim.gui.signal_normalization import *


def fixture(factor=1.):
    e=np.arange(101.,131.);sigma=factor*(1+7*np.exp(-((e-108)/2)**2)+4*np.exp(-((e-123)/2)**2))
    na,nb=.6*sigma,.4*sigma;ma=-.03*sigma;mb=.01*sigma
    s=dict(energy_ev=e,N_A=na,N_B=nb,M_A=ma,M_B=mb,I_A_plus=na+ma,I_A_minus=na-ma,I_B_plus=nb+mb,I_B_minus=nb-mb,
           D_mag=ma-mb,D_nonmag=na-nb,D_raw=na+ma-nb-mb,Sigma_ref=sigma)
    s.update(D_corrected=s['I_A_plus']-1.1*s['I_B_plus'],D_mag_processed_obs=ma-1.1*mb,D_nonmag_residual_obs=na-1.1*nb,magnetic_bias=-.1*mb)
    qx,qy=np.meshgrid(np.linspace(-1,1,7),np.linspace(-1,1,7));n=2+qx*.1;m=qy*.1
    wa=np.zeros_like(qx);wa[4,4]=1;wb=wa[::-1].copy();support=wa>0
    fields=dict(I_mag=m,I_nonmag=n,I_plus=n+m,I_minus=n-m)
    for key,v in dict(D_mag=m-m[::-1],D_nonmag=n-n[::-1],D_raw=(n+m)-(n+m)[::-1],D_corrected=(n+m)-1.1*(n+m)[::-1],D_mag_processed=m-1.1*m[::-1],D_nonmag_residual=n-1.1*n[::-1]).items():fields[key]=np.where(support,v,np.nan)
    cfg=SimpleNamespace(l3=108.,l2=122.,centers=((1/3,1/3),(1/3,-1/3)),model='xmcd',source_sha256='same',magnetization=(0,0,1),eta=1.,radius=.1,subpixels=64,window=(127,129),halfwidth=1.)
    return dict(spectra=s,config=cfg,maps={'L3':fields,'L2':{k:v.copy() for k,v in fields.items()}},qx=qx,qy=qy,weights={'A':wa,'B':wb},metadata=dict(frame=np.eye(3),reversal='crystal first',intensity_convention='relative',pair_reason='valid',alpha=1.1,source_audit=None))


class NormalizationTests(unittest.TestCase):
    def setUp(self):self.r=fixture();self.entries=[('BW',self.r,'bloch')]
    def test_01_common_even_asymmetry(self):
        d,m=normalized_spectra(self.entries,DisplaySettings(mode='asymmetry'))[0]
        np.testing.assert_allclose(d['D_mag'],-4)
        self.assertFalse(np.allclose(d['D_raw'],100*self.r['spectra']['D_raw']/(self.r['spectra']['I_A_plus']+self.r['spectra']['I_B_plus'])))
        self.assertIn('N_A(E)+N_B(E)',m['denominator'])
    def test_02_sum_not_mean_peak(self):
        p=peak_reference(self.r,'L3');d,_=normalized_spectra(self.entries,DisplaySettings(mode='peak'))[0]
        np.testing.assert_allclose(d['D_mag'],100*self.r['spectra']['D_mag']/p['value'])
        self.assertAlmostEqual(p['value'],8.,places=10)
    def test_03_peak_windows_native_axes(self):
        self.assertEqual(peak_reference(self.r,'L2')['peak_energy_ev'],123.)
        for w in ({'L3':(99,110)},{'L3':(105,120)},{'L3':(108,108.1)}):
            with self.assertRaises(ValueError):peak_reference(self.r,'L3',w)
    def test_04_fixed_full_reference_and_zoom(self):
        a,meta=normalized_spectra(self.entries,DisplaySettings(mode='peak'))[0]
        b,other=normalized_spectra(self.entries,DisplaySettings(mode='peak'), 'L2 zoom')[0]
        np.testing.assert_allclose(a['D_mag']/self.r['spectra']['D_mag'],100/meta['peak']['value'])
        self.assertEqual(meta['peak']['edge'],'L3');self.assertEqual(other['peak']['edge'],'L2')
        _,explicit=normalized_spectra(self.entries,DisplaySettings(mode='peak',peak_edge='L3'),'L2 zoom')[0];self.assertEqual(explicit['peak']['edge'],'L3')
    def test_05_negative_signs(self):
        for mode in ('peak','asymmetry'):
            d,_=normalized_spectra(self.entries,DisplaySettings(mode=mode))[0];self.assertTrue(np.all(d['D_mag']<0))
    def test_06_zero_nonfinite_and_noise(self):
        a,m=divide_percent([1,1,1,1],[0,np.nan,1e-30,1]);self.assertTrue(np.isnan(a[:3]).all());self.assertEqual(a[3],100)
        b,_=divide_percent([1e308],[1e-300]);self.assertFalse(np.isinf(b).any())
    def test_07_local_map_mask_not_zero(self):
        self.r['maps']['L3']['I_nonmag'][0,0]=1e-20
        a,meta=angular_display(self.r,'L3','I_mag','local');self.assertTrue(np.isnan(a[0,0]));self.assertEqual(meta['relative_floor'],MAP_FLOOR)
        self.assertTrue(np.isfinite(a[3,3]));self.assertEqual(a[3,3],0.)
    def test_08_paired_reflection_and_support(self):
        a,_=angular_display(self.r,'L3','D_mag','paired');self.assertEqual(np.isfinite(a).sum(),1)
        n=self.r['maps']['L3']['I_nonmag'];self.assertAlmostEqual(a[4,4],100*(2/30)/(n[4,4]+n[2,4]))
    def test_09_manual_unpaired_disabled(self):
        self.r['config'].centers=((.3,.4),(.3,-.2))
        with self.assertRaisesRegex(ValueError,'not y mirrors'):angular_display(self.r,'L3','D_mag','paired')
    def test_10_bw_ms_common_peak_preserves_amplitude(self):
        entries=self.entries+[('MS',fixture(2),'fft-multislice')];out=normalized_spectra(entries,DisplaySettings(mode='peak'))
        np.testing.assert_allclose(out[1][0]['D_mag'],2*out[0][0]['D_mag'])
        self.assertEqual(out[0][1]['peak'],out[1][1]['peak'])
    def test_11_independent_method_warning(self):
        out=normalized_spectra(self.entries+[('MS',fixture(2),'fft-multislice')],DisplaySettings(mode='peak',scope='independent'))
        np.testing.assert_allclose(out[0][0]['D_mag'],out[1][0]['D_mag']);self.assertIn('not suitable',out[1][1]['warning'])
    def test_12_saved_reference_identity(self):
        out=normalized_spectra(self.entries+[('mistilt',fixture(2),'bloch')],DisplaySettings(mode='peak',reference=1))
        self.assertEqual(out[0][1]['reference_run'],'mistilt');self.assertAlmostEqual(out[0][1]['peak']['value'],16.,places=9)
    def test_13_incompatible_models_qualitative_only(self):
        foreign=fixture();foreign['config'].model='atomic';foreign['config'].source_sha256='';foreign['metadata']['intensity_convention']='other units'
        entries=self.entries+[('atomic',foreign,'bloch')]
        with self.assertRaisesRegex(ValueError,'Shared peak disabled'):normalized_spectra(entries,DisplaySettings(mode='peak'))
        out=normalized_spectra(entries,DisplaySettings(mode='peak',scope='independent'));self.assertIn('Qualitative',out[1][1]['window_note'])
    def test_14_raw_unchanged(self):
        before={k:v.tobytes() for k,v in self.r['spectra'].items()}
        for mode in MODES:normalized_spectra(self.entries,DisplaySettings(mode=mode))
        self.assertEqual(before,{k:v.tobytes() for k,v in self.r['spectra'].items()})
    def test_15_scalar_sign_peak_and_legacy(self):
        m=percentage_metrics(self.r)['L3'];self.assertLess(m['D_mag_peak_percent'],0);self.assertAlmostEqual(m['D_mag_asymmetry_percent'],-4)
        self.assertNotEqual(m['legacy_raw_plus_sum_percent'],m['D_raw_asymmetry_percent'])
    def test_16_density_peak_maps_not_implemented(self):
        with self.assertRaisesRegex(ValueError,'units differ'):angular_display(self.r,'L3','I_mag','peak')
    def test_17_zero_peak_invalid(self):
        for key in ('N_A','N_B'):self.r['spectra'][key]=np.zeros(30)
        with self.assertRaisesRegex(ValueError,'positive'):peak_reference(self.r,'L3')
    def test_18_per_curve_mask_metadata(self):
        d,m=normalized_spectra(self.entries,DisplaySettings(mode='asymmetry'))[0]
        self.assertIn('D_mag',m['masks']);self.assertEqual(m['masks']['D_mag']['valid_count'],30)


GUI=all(importlib.util.find_spec(p) for p in ('PySide6','ase'))
SAVED=Path(__file__).resolve().parents[1]/'outputs/gui_stage_d/windows_20261016'


@unittest.skipUnless(GUI and (SAVED/'reference_project').is_dir(),'Optional GUI and existing real Stage D results required')
class SavedVisualizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6 import QtWidgets
        from emcd_sim.gui.project_io import load_project
        cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        cls.guards=ExitStack()
        for name in ('emcd_sim.physical_elastic.PhysicalElasticModel.amplitudes','emcd_sim.multislice_reference.fft_multislice_ni',
                     'emcd_sim.gui.emcd_forward.calculate','emcd_sim.gui.emcd_forward.tensors','emcd_sim.gui.propagation.propagate',
                     'emcd_sim.gui.emcd_forward.run_tensor_with_coherence','emcd_sim.single_channeling_tensor.run_tensor_with_coherence',
                     'emcd_sim.gui.stage_b.EMCDWorker.run','emcd_sim.gui.app.PreviewWorker.run'):
            cls.guards.enter_context(patch(name,side_effect=AssertionError('Forward calculation forbidden in Stage F')))
        cls.r=load_project(SAVED/'reference_project');cls.second=load_project(SAVED/'mistilt_project')
        cls.out=Path('outputs/gui_stage_f')/('tests_'+uuid.uuid4().hex);cls.out.mkdir(parents=True)
    @classmethod
    def tearDownClass(cls):cls.guards.close()
    def test_saved_modes_immutable_and_no_solver(self):
        from emcd_sim.gui.app import MainWindow
        w=MainWindow(workspace=self.out/'workspace');w.display_saved_result(self.r)
        before={method:{k:v.tobytes() for k,v in m['spectra'].items()} for method,m in self.r['methods'].items()}
        for mode in range(3):w.eels_view.normalization.mode.setCurrentIndex(mode);self.app.processEvents()
        for mode in range(3):w.maps_view.normalization.map_mode.setCurrentIndex(mode);self.app.processEvents()
        self.assertIsNone(w.worker)
        self.assertEqual(before,{method:{k:v.tobytes() for k,v in m['spectra'].items()} for method,m in self.r['methods'].items()})
        self.assertEqual(w.eels_view.normalization.settings().mode,'peak');w.close()
    def test_png_svg_and_derived_metadata(self):
        from matplotlib.figure import Figure
        from emcd_sim.gui.results import draw_eels
        from emcd_sim.gui.normalization_export import export_derived,save_figure
        from PIL import Image
        settings=DisplaySettings(mode='peak');fig=Figure(figsize=(11,9));draw_eels(fig,self.r,method='overlay',display=settings)
        save_figure(fig,self.out/'peak.png');save_figure(fig,self.out/'peak.svg')
        meta=json.loads(Image.open(self.out/'peak.png').info['Description']);self.assertEqual(meta['normalization'][0]['peak']['edge'],'L3')
        self.assertIn('nonmagnetic L3', (self.out/'peak.svg').read_text())
        entries=[(name,r,name) for name,r in self.r['methods'].items()];export_derived(entries,self.out/'derived',settings)
        with np.load(self.out/'derived/derived_and_raw.npz',allow_pickle=False) as z:
            np.testing.assert_array_equal(z['run0__raw__D_mag'],self.r['spectra']['D_mag'])
            self.assertLess(z['run0__derived__D_mag'][np.argmin(abs(self.r['spectra']['energy_ev']-831.271))],0)
    def test_saved_comparison_compatibility_and_controls(self):
        from emcd_sim.gui.compare_results import CompareResults,map_compatibility
        from emcd_sim.gui.app import MainWindow
        w=MainWindow(workspace=self.out/'compare_workspace');c=CompareResults(w,[('reference',self.r),('mistilt',self.second)])
        c.normalization.mode.setCurrentIndex(2);c.normalization.map_mode.setCurrentIndex(2);c.field.setCurrentText('Raw paired EMCD');c.redraw()
        self.assertTrue(map_compatibility(self.r,self.second,'L3','D_raw')[0]);self.assertEqual(c.normalization.settings().scope,'shared');c.close();w.close()
    def test_map_byte_preservation_and_masks(self):
        from matplotlib.figure import Figure
        from emcd_sim.gui.results import draw_maps
        before={e:{k:v.tobytes() for k,v in fs.items()} for e,fs in self.r['maps'].items()}
        for mode in ('raw','local','paired'):
            fig=Figure(figsize=(12,8));draw_maps(fig,self.r,'L3',display=DisplaySettings(map_mode=mode))
        self.assertEqual(before,{e:{k:v.tobytes() for k,v in fs.items()} for e,fs in self.r['maps'].items()})
    def test_legacy_readonly_percentage(self):
        from emcd_sim.gui.project_io import load_project
        for p in ('outputs/gui_stage_b/xmcd_20261015_234528','outputs/gui_stage_c/windows_20261016_000116/xmcd_both'):
            r=load_project(p,legacy=True);self.assertTrue(r['read_only_legacy'])
            d,meta=normalized_spectra([('legacy',r,r['method'])],DisplaySettings(mode='peak'))[0];self.assertTrue(np.isfinite(d['D_mag']).all())
    def test_stale_input_label_survives_display_change(self):
        from emcd_sim.gui.app import MainWindow
        w=MainWindow(workspace=self.out/'stale_workspace');w.display_saved_result(self.r);w.spin['tx'].setValue(-6.)
        self.assertIn('STALE',w.eels_view.label.text());w.eels_view.normalization.mode.setCurrentIndex(2)
        self.assertIn('STALE',w.eels_view.label.text());self.assertIsNone(w.worker);w.close()
    def test_cross_model_warning_and_qualitative_overlay(self):
        from emcd_sim.gui.project_io import load_project
        from emcd_sim.gui.compare_results import CompareResults,map_compatibility
        from emcd_sim.gui.app import MainWindow
        atomic=load_project(SAVED/'atomic_ms_project');w=MainWindow(workspace=self.out/'mixed_workspace')
        c=CompareResults(w,[('XMCD',self.r),('atomic',atomic)]);c.normalization.mode.setCurrentIndex(2)
        self.assertIn('Shared peak disabled',c.note.text());c.normalization.scope.setCurrentIndex(1);c.redraw()
        self.assertIn('MDFF',c.note.text());self.assertFalse(map_compatibility(self.r,atomic,'L3','I_mag')[0])
        self.assertIn('Independently normalized',c.figure._suptitle.get_text());c.close();w.close()
    def test_invalid_pair_control_disabled(self):
        from emcd_sim.gui.app import MainWindow
        bad=dict(self.r,config=replace(self.r['config'],centers=((.3,.4),(.3,-.2))))
        w=MainWindow(workspace=self.out/'unpaired_workspace');w.display_saved_result(bad)
        self.assertFalse(w.maps_view.normalization.map_mode.model().item(2).isEnabled())
        self.assertIn('not y mirrors',w.maps_view.normalization.pair_warning.text());w.close()


if __name__=='__main__':unittest.main()
