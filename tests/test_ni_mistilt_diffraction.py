"""Elastic two-beam dominance uses saved populations without projection gains."""
import unittest
import numpy as np

from emcd_sim.multislice_emcd_reference import coherence_from_amplitudes
from emcd_sim.ni_mistilt_diffraction import two_beam_diagnostics


class TwoBeamDiagnosticsTests(unittest.TestCase):
    def test_depth_averages_and_excluded_flux_remain_unnormalized(self):
        z=np.array([0.,1.]);hkl=((0,0,0),(2,0,0),(-2,0,0))
        psi=np.array([[1,0,0],[np.sqrt(.4),np.sqrt(.3),np.sqrt(.2)]],complex)
        c=coherence_from_amplitudes(z,psi);before=psi.copy()
        result,intensity,average=two_beam_diagnostics(z,psi,c,hkl,np.array([0.,.1]))
        self.assertAlmostEqual(result['pair_exit_fraction'],.7)
        self.assertAlmostEqual(result['pair_depth_average_fraction'],.85)
        self.assertAlmostEqual(result['competing_common_depth_average_fraction'],.1)
        self.assertAlmostEqual(result['outside_common_depth_average_fraction'],.05)
        self.assertAlmostEqual(result['competing_total_max_sampled_fraction'],.3)
        np.testing.assert_array_equal(psi,before)
        self.assertAlmostEqual(intensity[-1].sum(),.9)
        self.assertAlmostEqual(average.sum(),.95)

    def test_target_pair_and_flux_checks(self):
        z=np.array([0.,1.]);psi=np.ones((2,2),complex)
        c=coherence_from_amplitudes(z,psi)
        with self.assertRaises(ValueError):
            two_beam_diagnostics(z,psi,c,((0,0,0),(-2,0,0)),np.zeros(2))
        with self.assertRaises(AssertionError):
            two_beam_diagnostics(z,psi,c,((0,0,0),(2,0,0)),np.zeros(2))


if __name__=='__main__':unittest.main()
