"""The reciprocal geometry overlay changes artists, never physical arrays."""
import unittest
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from emcd_sim.benchmark import nickel_physical_benchmark
from emcd_sim.emcd_angular_plots import decorate_reciprocal_map


class AngularOverlayTests(unittest.TestCase):
    def test_thales_circle_and_absolute_vs_relative_tilts(self):
        za=[]
        for tilt in ((-6.61672544,15.),(-6.11672544,25.),(-8.11672544,25.)):
            model=nickel_physical_benchmark(tilt_mrad_xy=tilt)
            fig,ax=plt.subplots()
            decorate_reciprocal_map(ax,model,(-1.1,1.1,-1.1,1.1))
            circle=next(p for p in ax.patches if p.get_label()=='Thales (000)-(200)')
            g=model.elastic.crystal.g_vector((2,0,0))[:2]
            np.testing.assert_allclose(circle.center,g/2)
            self.assertAlmostEqual(circle.radius,np.linalg.norm(g)/2)
            for endpoint in (np.zeros(2),g):
                self.assertAlmostEqual(np.linalg.norm(endpoint-circle.center),circle.radius)
            za.append(-model.elastic.microscope.incident_k_xy)
            plt.close(fig)
        self.assertLess(np.linalg.norm(za[0]),np.linalg.norm(za[1]))
        self.assertLess(np.linalg.norm(za[0]),np.linalg.norm(za[2]))
        self.assertAlmostEqual(za[0][1]/za[1][1],15/25)

    def test_zero_and_nonzero_tilt_and_method_independence(self):
        for tilt in ((0.,0.),(-7.1,25.)):
            expected=None
            for _method in ('BW','MS'):
                model=nickel_physical_benchmark(tilt_mrad_xy=tilt)
                fig,ax=plt.subplots()
                physical=np.arange(81.).reshape(9,9);before=physical.copy()
                image=ax.imshow(physical)
                decorate_reciprocal_map(ax,model,(-1.1,1.1,-1.1,1.1))
                za=next(line for line in ax.lines if line.get_label()=='ZA [001]')
                xy=np.array([za.get_xdata()[0],za.get_ydata()[0]])
                np.testing.assert_allclose(xy,-model.elastic.microscope.incident_k_xy)
                if tilt==(0.,0.):np.testing.assert_array_equal(xy,[0.,0.])
                if expected is not None:np.testing.assert_array_equal(xy,expected)
                expected=xy
                np.testing.assert_array_equal(physical,before)
                np.testing.assert_array_equal(image.get_array(),before)
                plt.close(fig)

    def test_outside_zone_axis_reports_true_coordinates(self):
        model=nickel_physical_benchmark(tilt_mrad_xy=(-7.,25.))
        fig,ax=plt.subplots()
        decorate_reciprocal_map(ax,model,(-.5,.5,-.5,.5))
        self.assertTrue(any('outside view' in text.get_text() for text in ax.texts))
        self.assertFalse(any(line.get_label()=='ZA [001]' for line in ax.lines))
        plt.close(fig)


if __name__=='__main__':unittest.main()
