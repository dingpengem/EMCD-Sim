"""Focused [710] reciprocal geometry, independent wave and legacy checks."""
import unittest
import numpy as np
from emcd_sim.ni_710_geometry import Ni710Geometry
from emcd_sim.diffraction import excitation_errors_angstrom_inv
from emcd_sim.multislice_reference import fft_multislice_ni,_projected_ni_potential
from emcd_sim.multislice_emcd_reference import project_fft_amplitudes


class Ni710Tests(unittest.TestCase):
    def test_frame_and_real_hkl(self):
        g=Ni710Geometry();np.testing.assert_allclose(g.frame@g.frame.T,np.eye(3),atol=1e-14)
        self.assertAlmostEqual(np.linalg.det(g.frame),1.)
        np.testing.assert_allclose(np.cross(g.frame[0],g.frame[1]),g.frame[2])
        np.testing.assert_allclose(g.frame[2],np.array([7,1,0])/np.sqrt(50))
        self.assertAlmostEqual(g.crystal.g_vector((0,0,2))[2],0.)
        self.assertGreater(abs(g.crystal.g_vector((2,0,0))[2]),.1)
        for h,k,l in g.beams(4.5).hkl:
            self.assertEqual(7*h+k,0);self.assertEqual(h%2,l%2)
        m=g.model();i=m.elastic.beams.hkl.index((0,0,2))
        self.assertAlmostEqual(excitation_errors_angstrom_inv(m.elastic)[i],0.,places=14)
        for dx in np.arange(-2,2.1,.5):
            tilted=g.model(dx);self.assertEqual(tilted.elastic.microscope.tilt_mrad_xy[1],0.)
            np.testing.assert_allclose(tilted.detectors['A'].center_q_xy,m.detectors['A'].center_q_xy)
        zero=g.model(-g.bragg_tilt())
        np.testing.assert_array_equal(zero.elastic.microscope.incident_k_xy,[0.,0.])

    def test_full_basis_mirror_and_selected_emcd_integration(self):
        from emcd_sim.ni_710_mistilt import Config,initial,model,propagate,geometry
        from emcd_sim.ni_mistilt_series import calculate_case
        from emcd_sim.ni_mistilt_eels import prepare_spectra,validate_map_integrals
        cfg=Config(thickness_nm=1.,depth_steps=8,detector_grid=17,energy_points=81)
        source='data/wien2k_ni/Ni_fm.xmcd';energy,selected,*_=initial(source,cfg)
        m=model(cfg,0.);hkl=m.elastic.beams.hkl;mirror=[hkl.index((-h,-k,l)) for h,k,l in hkl]
        H=m.elastic.hamiltonian_nm_inv()
        np.testing.assert_allclose(H,H[np.ix_(mirror,mirror)],atol=1e-12)
        d,meta,rows=calculate_case(source,cfg,0.,energy,selected,model_factory=model,
            propagator=propagate,geometry_factory=geometry,target_key='s002_inv_angstrom')
        spectra,_=prepare_spectra(d,cfg)
        self.assertLess(validate_map_integrals(d,spectra),1e-12)
        np.testing.assert_allclose(spectra['D_nonmag'],0.,atol=1e-14)
        np.testing.assert_allclose(spectra['D_raw'],spectra['D_mag']+spectra['D_nonmag'],atol=1e-14)
        self.assertIn('s002_inv_angstrom',meta['geometry'])
        self.assertNotIn('s200_inv_angstrom',meta['geometry'])

    def test_oriented_potential_and_independent_short_wave(self):
        g=Ni710Geometry();m=g.model();z=np.array([0.,.001,.3,1.])
        f=fft_multislice_ni(z,tilt_mrad_xy=m.elastic.microscope.tilt_mrad_xy,grid_points=32,
            slice_step_nm=.005,potential_cutoff_inv_angstrom=2.2,return_amplitudes=True,projected_geometry=g)
        p,out=project_fft_amplitudes(f,m.elastic.beams.hkl)
        np.testing.assert_allclose(p,m.elastic.amplitudes(z),atol=4e-6)
        self.assertLess(out.max(),1e-7);self.assertLess(f.norm_error,1e-12)
        j=m.elastic.beams.hkl.index((0,0,2));coupling=m.elastic.hamiltonian_nm_inv()[j,0].real
        self.assertAlmostEqual(p[1,j].imag/(coupling*z[1]),1.,places=5)
        # Every mesh represents the same physical potential Fourier coefficient.
        values=[]
        for n in (16,32,64):
            u,hkl,xy=_projected_ni_potential(n,200.,0.,2.2,g)
            coeff=(np.fft.fft2(u)/n**2).reshape(-1)
            values.append(coeff[np.flatnonzero(np.all(hkl==[1,-7,1],axis=1))[0]])
        np.testing.assert_allclose(values,values[0],atol=1e-14)
        self.assertGreater(abs(values[0]),0.)
        with self.assertRaises(ValueError):g.harmonics(16,3.2)

    def test_zone_axis_and_thales_and_plot_purity(self):
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from emcd_sim.emcd_angular_plots import decorate_reciprocal_map
        g=Ni710Geometry();m=g.model();fig,ax=plt.subplots();data=np.arange(81.).reshape(9,9);before=data.copy()
        im=ax.imshow(data);decorate_reciprocal_map(ax,m,(-1,1,-1,1),target_hkl=(0,0,2),zone_axis=(7,1,0))
        star=next(l for l in ax.lines if l.get_label()=='ZA [710]')
        np.testing.assert_allclose([star.get_xdata()[0],star.get_ydata()[0]],-m.elastic.microscope.incident_k_xy)
        circle=next(p for p in ax.patches if p.get_label()=='Thales (000)-(002)')
        gg=m.elastic.crystal.g_vector((0,0,2))[:2]
        np.testing.assert_allclose(circle.center,gg/2);self.assertAlmostEqual(circle.radius,np.linalg.norm(gg)/2)
        np.testing.assert_array_equal(im.get_array(),before);np.testing.assert_array_equal(data,before);plt.close(fig)


if __name__=='__main__':unittest.main()
