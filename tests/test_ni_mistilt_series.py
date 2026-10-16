"""Focused geometry, checkpoint and shared-map checks for the mistilt driver."""
from dataclasses import replace
import unittest
from unittest.mock import patch
import numpy as np

from emcd_sim.ni_mistilt_series import (MistiltConfig, model_for_offset, geometry_record,
                                      setup, validate_checkpoint, safe_ratio, calculate_case)
from emcd_sim.multislice_reference import fft_multislice_ni
from emcd_sim.postedge_emcd_maps import paired_geometry, paired_maps, integrate_paired


class MistiltSeriesTests(unittest.TestCase):
    def test_nine_absolute_tilts_s200_and_fixed_geometry(self):
        cfg=MistiltConfig();records=[];detectors=[]
        np.testing.assert_array_equal(cfg.offsets(),np.arange(-2.,2.1,.5))
        for d in cfg.offsets():
            model=model_for_offset(cfg,d);r=geometry_record(cfg,d,model);records.append(r)
            detectors.append(r['detectors'])
            self.assertEqual(r['theta_y_mrad'],25.)
            np.testing.assert_allclose(r['coordinate_markers']['zone_axis_q_cycles_per_angstrom'],
                                       -model.elastic.microscope.incident_k_xy)
        self.assertAlmostEqual(records[4]['theta_x_mrad'],-7.116725439974256,places=12)
        self.assertAlmostEqual(records[2]['theta_x_mrad'],-8.116725439974256,places=12)
        self.assertAlmostEqual(records[4]['s200_inv_angstrom'],0.,places=14)
        self.assertLess(records[0]['s200_inv_angstrom'],0.)
        self.assertGreater(records[-1]['s200_inv_angstrom'],0.)
        self.assertEqual(len({r['coordinate_markers']['zone_axis_q_cycles_per_angstrom'][1] for r in records}),1)
        self.assertTrue(all(d==detectors[0] for d in detectors))
        self.assertTrue(all(r['thales_center_q_xy']==records[0]['thales_center_q_xy'] for r in records))
        self.assertTrue(all(r['thales_radius_inv_angstrom']==records[0]['thales_radius_inv_angstrom'] for r in records))

    def test_pairing_parity_and_processing_do_not_change_intrinsic_maps(self):
        model=model_for_offset(MistiltConfig(),0.)
        q=np.linspace(-1,1,33);qx,qy=np.meshgrid(q,q)
        g=paired_geometry(model,qx,qy);p=3+.2*qy;m=3-.2*qy
        p0,m0=p.copy(),m.copy()
        a=paired_maps(p,m,.9,g);b=paired_maps(m,p,.9,g)
        np.testing.assert_allclose(a['I_mag'],-b['I_mag'])
        np.testing.assert_allclose(a['I_nonmag'],b['I_nonmag'])
        np.testing.assert_allclose(a['D_corrected'],a['D_mag_processed']+a['D_nonmag_residual'])
        expected=np.sum(p*g['weights_A'])*g['dq2']-.9*np.sum(p*g['weights_B'])*g['dq2']
        self.assertAlmostEqual(integrate_paired(a['D_corrected'],g),expected,places=14)
        np.testing.assert_array_equal(p,p0);np.testing.assert_array_equal(m,m0)

    def test_source_selection_memory_and_configuration_guards(self):
        cfg=MistiltConfig();energy,selected,meta=setup('data/wien2k_ni/Ni_fm.xmcd',cfg)
        for e in selected.values():self.assertIn(e,energy)
        self.assertAlmostEqual(selected['L3'],852.698,places=6)
        self.assertAlmostEqual(selected['L2'],870.004,places=6)
        self.assertLess(meta['pair_array_memory_estimate_mib'],cfg.max_kernel_mib)
        for bad in (replace(cfg,step_mrad=0),replace(cfg,step_mrad=.3)):
            with self.assertRaises(ValueError):bad.offsets()
        with self.assertRaisesRegex(ValueError,'memory limit'):
            setup('data/wien2k_ni/Ni_fm.xmcd',replace(cfg,max_kernel_mib=.01))
        with self.assertRaisesRegex(ValueError,'mismatch'):
            validate_checkpoint({},dict(signature='wrong',geometry={}),meta['signature'],0.)
        self.assertTrue(np.isnan(safe_ratio(1.,0.,1e-10)))

    def test_small_case_matched_geometry_and_map_eels_reconstruction(self):
        cfg=MistiltConfig(start_mrad=0.,stop_mrad=0.,thickness_nm=1.,beam_cutoff=1.4,
            fft_grid=16,slice_step_nm=.02,depth_steps=8,detector_grid=17,energy_points=81)
        source='data/wien2k_ni/Ni_fm.xmcd';energy,selected,provenance=setup(source,cfg)
        with patch('emcd_sim.ni_mistilt_series.fft_multislice_ni',wraps=fft_multislice_ni) as fft_call:
            data,meta,rows=calculate_case(source,cfg,0.,energy,selected)
        self.assertEqual(fft_call.call_count,1)
        passed=fft_call.call_args.kwargs
        self.assertEqual(passed['tilt_mrad_xy'],model_for_offset(cfg,0.).elastic.microscope.tilt_mrad_xy)
        self.assertEqual(passed['potential_cutoff_inv_angstrom'],cfg.potential_cutoff)
        self.assertEqual(passed['acceleration_kv'],cfg.acceleration_kv)
        np.testing.assert_allclose(fft_call.call_args.args[0],np.linspace(0,cfg.thickness_nm,cfg.depth_steps))
        self.assertLess(meta['coherence_relative_error'],1e-3)
        self.assertLess(meta['fft_norm_error'],1e-12)
        self.assertEqual(data['map__I_mag'].shape,(2,2,17,17))
        meta.update(signature=provenance['signature'])
        validate_checkpoint(data,meta,provenance['signature'],0.)
        altered={**data,'spectra__D_mag':data['spectra__D_mag']+1.}
        with self.assertRaises(AssertionError):validate_checkpoint(altered,meta,provenance['signature'],0.)
        # Processed contrast remains exactly the sum of processed odd/even terms.
        np.testing.assert_allclose(data['spectra__D_corrected'],
            data['spectra__D_mag_processed_obs']+data['spectra__D_nonmag_residual_obs'],atol=1e-13)


if __name__=='__main__':unittest.main()
