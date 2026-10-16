"""Individual exports preserve raw spectra, reversal parity and undefined values."""
import unittest
import numpy as np
from emcd_sim.ni_mistilt_eels import case_name,prepare_spectra
from emcd_sim.ni_mistilt_series import MistiltConfig
from emcd_sim.xmcd_postedge_normalization import analyze_postedge_spectra


class IndividualEELSTests(unittest.TestCase):
    def test_case_names(self):
        self.assertEqual([case_name(d) for d in (-2.,-1.5,0.,.5,2.)],
            ['case_m2p0','case_m1p5','case_0p0_exact_bragg','case_p0p5','case_p2p0'])

    def test_reversal_correction_and_validity_without_peak_scaling(self):
        e=np.linspace(823.625,882.521,241)
        n=2+.002*(e-e[0]);m=.03*np.sin((e-e[0])/4)
        a,b,c,d=n+m,.8*n-m,n-m,.8*n+m
        # A zero-intensity sample is physical but its asymmetry is undefined.
        a[0]=b[0]=c[0]=d[0]=0.
        analysis=analyze_postedge_spectra(e,a,b,c,d,windows=((878.,882.),)).spectra
        keys=('I_A_plus','I_B_plus','I_A_minus','I_B_minus','D_raw','D_mag','D_nonmag',
              'D_corrected','D_mag_processed_obs','D_nonmag_residual_obs')
        data={'energy_ev':e,'alpha':np.repeat(analysis['alpha_obs'][0],2)}
        for k in keys:
            v=analysis[k][0] if analysis[k].ndim==2 else analysis[k]
            data['spectra__'+k]=np.stack([v,v])
        result,checks=prepare_spectra(data,MistiltConfig())
        np.testing.assert_array_equal(result['I_A_plus'][0],a)
        np.testing.assert_array_equal(result['I_B_plus'][0],b)
        self.assertTrue(result['valid_intensity'][:,0].all())
        self.assertTrue(np.isnan(result['magnetic_asymmetry'][:,0]).all())
        self.assertFalse(result['valid_magnetic_asymmetry'][:,0].any())
        np.testing.assert_allclose(result['D_raw'],result['D_mag']+result['D_nonmag'])
        np.testing.assert_allclose(result['D_corrected'],result['D_mag_processed_obs']+result['D_nonmag_residual_obs'],atol=1e-14)
        self.assertEqual(checks[0]['undefined_counts']['valid_magnetic_asymmetry'],1)


if __name__=='__main__':unittest.main()
