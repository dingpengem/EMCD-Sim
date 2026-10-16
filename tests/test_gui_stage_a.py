"""Stage A only: real geometry, CIF compatibility, coordinate events, workers."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest,uuid,threading
import importlib.util
if not all(importlib.util.find_spec(name) for name in ('ase','PySide6')):
    raise unittest.SkipTest('Stage A GUI checks require the optional .[gui] dependencies')
from pathlib import Path
from unittest.mock import patch
from dataclasses import replace
import numpy as np
from ase.io import write
from ase.build import bulk
from PySide6 import QtWidgets
from matplotlib.backend_bases import MouseEvent
from emcd_sim.gui.geometry import (Structure,Settings,orientation,indices,geometry,
    elastic_model,preview,align_bragg,excitation,za_from_tilt,tilt_from_za)
from emcd_sim.gui.app import MainWindow
from emcd_sim.ni_017_geometry import Ni017Geometry


class GeometryTests(unittest.TestCase):
    def test_benchmark_orientation_hamiltonian_and_preview(self):
        structure=Structure.nickel();cfg=Settings();m=elastic_model(structure,cfg);reference=Ni017Geometry().model().elastic
        np.testing.assert_allclose(orientation(structure.atoms.cell.array,cfg.zone),Ni017Geometry().frame,atol=1e-14)
        self.assertEqual(m.beams.hkl,reference.beams.hkl)
        np.testing.assert_allclose(m.hamiltonian_nm_inv(),reference.hamiltonian_nm_inv(),atol=1e-13)
        r=preview(structure,cfg);np.testing.assert_allclose(r['amplitudes'],reference.amplitudes(np.array([0.,30.])),atol=1e-12)
        self.assertAlmostEqual(r['intensity'].sum(),1.)
        self.assertEqual(indices('[017]',True),(0,1,7));self.assertEqual(indices('0 -2 -14',True),(0,-1,-7))
        self.assertEqual(indices('4 0 0'),(4,0,0))

    def test_actual_arbitrary_orientation_bragg_locks_and_coordinates(self):
        structure=Structure.nickel()
        for zone in [(0,0,1),(7,1,0),(1,1,1),(0,1,7)]:
            c,R,h,g,m=geometry(structure,replace(Settings(),zone=zone))
            np.testing.assert_allclose(R@R.T,np.eye(3),atol=1e-14);self.assertAlmostEqual(np.linalg.det(R),1.)
            self.assertTrue(all(np.dot(t,zone)==0 for t in h))
            self.assertTrue(all(abs(c.g_vector(t)[2])<1e-12 for t in h))
        for g,lock in [([.6,0],'Y'),([0,.4],'X'),([.4,.3],'None')]:
            t=align_bragg(g,[12,-9],200,lock);self.assertAlmostEqual(float(excitation(g,t,200)),0.,places=14)
            if lock=='Y':self.assertEqual(t[1],-9)
            if lock=='X':self.assertEqual(t[0],12)
        with self.assertRaises(ValueError):align_bragg([.6,0],[0,0],200,'X')
        for voltage in (80,200,300):
            np.testing.assert_allclose(tilt_from_za(za_from_tilt([5,-25],voltage),voltage),[5,-25])

    def test_ase_cif_import_and_material_gate(self):
        folder=Path('outputs')/('gui_cif_test_'+uuid.uuid4().hex);folder.mkdir()
        for element in ('Ni','Cu'):
            file=folder/(element+'.cif');write(file,bulk(element,'fcc',a=3.524,cubic=True))
            s=Structure.from_cif(file);self.assertEqual(s.atoms.get_chemical_formula(),element+'4');self.assertEqual(len(s.sha256),64)
            self.assertIn('Fractional positions',s.description());geometry(s,Settings())
            if element=='Cu':
                self.assertTrue(s.elastic_reason)
                with self.assertRaises(ValueError):elastic_model(s,Settings())
            else:self.assertFalse(s.elastic_reason)
        s=Structure.nickel();s.atoms.info['occupancy']={'0':{'Ni':.5}}
        self.assertTrue(s.elastic_reason)


class InteractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    def setUp(self):self.window=MainWindow();self.window.show();self.app.processEvents()
    def tearDown(self):
        if self.window.busy:self.window.cancel();self.window.worker.wait(5000);self.app.processEvents()
        self.window.close();self.app.processEvents()

    def test_zoomed_mouse_coordinates_reflection_and_stale_state(self):
        w=self.window;w.mode.setCurrentIndex(1);w.ax.set_xlim(-.4,.8);w.ax.set_ylim(-.5,.5);w.canvas.draw()
        point=np.array([.12,-.24]);x,y=w.ax.transData.transform(point)
        event=MouseEvent('button_press_event',w.canvas,x,y,button=1);w.clicked(event)
        np.testing.assert_allclose(w.settings().tilt,tilt_from_za(point,200),atol=1e-8)
        self.assertEqual(w.settings().zone,(0,1,7))
        old_detectors=w.detectors.copy();w.set_tilt([0,10]);np.testing.assert_array_equal(w.detectors,old_detectors)
        w.target.setText('-2 0 0');w.apply_orientation();w.mode.setCurrentIndex(0);w.canvas.draw()
        g=w.current[3][w.current[2].index((2,0,0))];x,y=w.ax.transData.transform(g)
        w.clicked(MouseEvent('button_press_event',w.canvas,x,y,button=1));self.assertEqual(w.settings().target,(2,0,0))
        w.lock.setCurrentText('Y');w.align();self.assertEqual(w.settings().tilt[1],10)
        self.assertAlmostEqual(float(excitation(g,w.settings().tilt,200)),0.,places=10)
        # Unapplied text must never reuse the old zone's reciprocal geometry.
        w.zone.setText('7 1 0');w.target.setText('0 0 2');w.align()
        np.testing.assert_allclose(w.current[1],orientation(w.structure.atoms.cell.array,(7,1,0)))
        self.assertIn((0,0,2),w.current[2])
        w.structure=Structure(bulk('Cu','fcc',a=3.6,cubic=True));w.refresh();self.assertFalse(w.run_button.isEnabled())
        self.assertTrue(all(not w.tabs.isTabEnabled(i) for i in (1,2,3)))

    def test_cancel_does_not_register_completed_physics(self):
        entered=threading.Event();release=threading.Event();w=self.window
        def slow_preview(structure,settings):
            entered.set();release.wait(5);return preview(structure,settings)
        with patch('emcd_sim.gui.app.preview',slow_preview):
            w.start_preview();self.assertTrue(entered.wait(5));self.assertFalse(w.inputs.isEnabled())
            w.cancel();release.set();self.assertTrue(w.worker.wait(5000));self.app.processEvents()
        self.assertIsNone(w.last_result);self.assertEqual(w.history,[]);self.assertFalse(w.busy)

    def test_worker_failure_is_not_success(self):
        w=self.window;messages=[];w.error=messages.append
        with patch('emcd_sim.gui.app.preview',side_effect=ValueError('Focused failure check')):
            w.start_preview();self.assertTrue(w.worker.wait(5000));self.app.processEvents()
        self.assertEqual(messages,['Focused failure check']);self.assertEqual(w.run_outcome,'failed')
        self.assertEqual(w.progress.value(),0);self.assertEqual(w.history,[]);self.assertFalse(w.busy)


if __name__=='__main__':unittest.main()
