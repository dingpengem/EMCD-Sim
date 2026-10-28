"""Actual [017] geometry, cubic magnetization, native edges and matched elasticity."""
import unittest
from pathlib import Path
import numpy as np
from legacy_geometry import Ni017Geometry,rotated_tensor,energy_audit
from emcd_sim.xmcd_effective_mdff import effective_tensor_from_xmcd
from emcd_sim.multislice_reference import fft_multislice_ni
from emcd_sim.multislice_reference import project_fft_amplitudes
from emcd_sim.physical_elastic import excitation_errors_angstrom_inv

SOURCE='data/wien2k_ni/Ni_fm.xmcd'


class Ni017Tests(unittest.TestCase):
    def test_frame_zone_target_and_fixed_y(self):
        g=Ni017Geometry();R=g.frame
        np.testing.assert_allclose(R@R.T,np.eye(3),atol=1e-14)
        np.testing.assert_allclose(np.cross(R[0],R[1]),R[2]);self.assertAlmostEqual(np.linalg.det(R),1.)
        for h,k,l in g.beams(4.5).hkl:
            self.assertEqual(k+7*l,0);self.assertEqual(h%2,k%2);self.assertEqual(k%2,l%2)
        for d in np.arange(-2,2.1,.5):
            m=g.model(d);self.assertEqual(m.elastic.microscope.tilt_mrad_xy[1],0.)
            if d==0:self.assertAlmostEqual(excitation_errors_angstrom_inv(m.elastic)[m.elastic.beams.hkl.index((2,0,0))],0.,places=14)
        np.testing.assert_allclose(R@np.array([0.,0.,1.]),[0,-1/np.sqrt(50),7/np.sqrt(50)])

    def test_tensor_rotation_reversal_hermiticity_psd_beta(self):
        R=Ni017Geometry().frame;e=np.array([831.271,848.698])
        for beta in (.4,1.,1.7):
            c=effective_tensor_from_xmcd(SOURCE,e,eta=1,beta=beta).tensor_angstrom2_per_ev
            p=rotated_tensor(SOURCE,e,eta=1,beta=beta).tensor_angstrom2_per_ev
            n=rotated_tensor(SOURCE,e,eta=-1,beta=beta).tensor_angstrom2_per_ev
            np.testing.assert_allclose(p,np.einsum('ia,eab,jb->eij',R,c,R),atol=1e-14)
            np.testing.assert_allclose(p,p.swapaxes(-1,-2).conj(),atol=1e-14)
            np.testing.assert_allclose(np.linalg.eigvalsh(p),np.linalg.eigvalsh(c),atol=1e-14)
            self.assertGreaterEqual(np.linalg.eigvalsh(p).min(),-1e-14)
            np.testing.assert_allclose((p+n)/2,np.einsum('ia,eab,jb->eij',R,c.real,R),atol=1e-14)
            np.testing.assert_allclose((p-n)/2,np.einsum('ia,eab,jb->eij',R,1j*c.imag,R),atol=1e-14)

    @unittest.skipUnless(all(Path(SOURCE).with_suffix('.'+suffix).is_file() for suffix in ('raw1','raw2','broad1','broad2','rawxmcd','inso','injoint','inc')), 'Requires original local WIEN2k audit companions; not distributed')
    def test_verified_native_edges(self):
        a=energy_audit(SOURCE)
        self.assertEqual(a['selected_magnetic_energies_ev'],dict(L3=831.271,L2=848.698))
        self.assertAlmostEqual(a['core_splitting_ev'],17.48063828,places=7)
        self.assertLess(abs(a['predicted_L2_magnetic_energy_ev']-848.698),.002)
        self.assertLess(a['early_L3_broad1_matching_error'],2e-9)

    def test_overlay_labels_coordinates_and_data_preservation(self):
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from emcd_sim.emcd_angular_plots import decorate_reciprocal_map
        g=Ni017Geometry();m=g.model();image=np.arange(25.).reshape(5,5)
        original=image.copy();fig,ax=plt.subplots();artist=ax.imshow(image)
        decorate_reciprocal_map(ax,m,(-.2,.8,-.6,.6),target_hkl=(2,0,0),zone_axis=(0,1,7))
        self.assertIn('ZA [017]',ax.get_legend_handles_labels()[1])
        marker=next(line for line in ax.lines if line.get_label()=='ZA [017]')
        np.testing.assert_allclose([marker.get_xdata()[0],marker.get_ydata()[0]],-m.elastic.microscope.incident_k_xy)
        np.testing.assert_array_equal(artist.get_array(),original);plt.close(fig)


if __name__=='__main__':unittest.main()

def test_oriented_017_bw_fft_amplitudes():
    geo=Ni017Geometry();m=geo.model();z=np.array([0.,.001,.3,1.])
    f=fft_multislice_ni(z,tilt_mrad_xy=m.elastic.microscope.tilt_mrad_xy,grid_points=32,slice_step_nm=.01,potential_cutoff_inv_angstrom=2.2,return_amplitudes=True,projected_geometry=geo)
    psi,_=project_fft_amplitudes(f,m.elastic.beams.hkl)
    np.testing.assert_allclose(psi,m.elastic.amplitudes(z),atol=4e-6)
