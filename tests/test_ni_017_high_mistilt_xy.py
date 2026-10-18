"""Focused geometry, mirror symmetry and checkpoint tests for [017] X/Y."""
import hashlib,json,unittest,uuid
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch
from dataclasses import replace
import numpy as np
from emcd_sim.ni_017_high_mistilt_xy import GEO,Config,scans,model,geometry_xy,setup,propagate,run,tag,SOURCE
from emcd_sim.ni_017_geometry import rotated_tensor
from emcd_sim.ni_017_mistilt import feature_windows,prepare_spectra
from emcd_sim.ni_mistilt_series import calculate_case,validate_checkpoint
from emcd_sim.ni_mistilt_eels import validate_map_integrals
from emcd_sim.multislice_reference import _projected_ni_potential


class HighMistiltTests(unittest.TestCase):
    def test_registry_special_points_and_deduplication(self):
        groups,pairs=scans();self.assertEqual([len(groups[k]) for k in ('x','y','xy')],[13,13,25]);self.assertEqual(len(pairs),43)
        b=GEO.bragg_tilt();self.assertIn((b,0),pairs);self.assertIn((-b,0),pairs)
        self.assertAlmostEqual(model(Config(),-b,0).elastic.microscope.tilt_mrad_xy[0],0.)
        g=geometry_xy(Config(),b,0,model(Config(),b,0));self.assertAlmostEqual(g['s400_inv_angstrom'],0.,places=15)
        self.assertEqual(len(set(tag(*p) for p in pairs)),43)

    def test_xy_excitation_za_and_fixed_detectors(self):
        cfg=Config();reference=model(cfg,0,0);h=reference.elastic.beams.hkl
        for x,y in [(0,30),(0,-30),(10,25),(-10,-25)]:
            m=model(cfg,x,y);g=geometry_xy(cfg,x,y,m);s=np.array(g['excitation_errors_inv_angstrom'])
            np.testing.assert_allclose([g['theta_x_mrad'],g['theta_y_mrad']],[GEO.bragg_tilt()+x,y])
            self.assertAlmostEqual(g['s200_inv_angstrom'],np.linalg.norm(m.elastic.crystal.g_vector((2,0,0)))*x*.001)
            np.testing.assert_allclose(g['coordinate_markers']['zone_axis_q_cycles_per_angstrom'],-m.elastic.microscope.incident_k_xy)
            np.testing.assert_allclose(m.elastic.reciprocal_vectors_xy,reference.elastic.reciprocal_vectors_xy)
            self.assertEqual(m.detectors,reference.detectors)
            sr=np.array(geometry_xy(cfg,0,0,reference)['excitation_errors_inv_angstrom'])
            gv=m.elastic.reciprocal_vectors_xy
            np.testing.assert_allclose(s-sr,gv@np.array([x,y])*.001,atol=1e-16)
        np.testing.assert_allclose(GEO.frame@np.array([0,0,1]),[0,-1/np.sqrt(50),7/np.sqrt(50)])

    def test_constructed_potential_and_basis_mirror(self):
        h=GEO.beams(3.2).hkl
        self.assertEqual(set(h),{(a,-b,-c) for a,b,c in h})
        u,hh,gg=_projected_ni_potential(32,200,0,2.2,projected_geometry=GEO)
        np.testing.assert_allclose(u,u[:,(-np.arange(32))%32],atol=1e-12)

    @unittest.skipUnless(all(Path(SOURCE).with_suffix('.'+suffix).is_file() for suffix in ('raw1','raw2','broad1','broad2','rawxmcd','inso','injoint','inc')), 'Requires original local WIEN2k audit companions; not distributed')
    def test_even_mirror_full_contraction_and_map_eels(self):
        cfg=replace(Config(),energy_points=83,detector_grid=9,depth_steps=12,thickness_nm=2.)
        energy,selected,*_=setup(SOURCE,cfg);results=[]
        for y in (-25.,25.):
            data,meta,rows=calculate_case(SOURCE,cfg,0.,energy,selected,model_factory=lambda c,x:model(c,x,y),
                propagator=propagate,geometry_factory=lambda c,x,m:geometry_xy(c,x,y,m),tensor_factory=rotated_tensor,edge_windows=feature_windows(cfg))
            spectra,_=prepare_spectra(data,cfg);validate_map_integrals(data,spectra);results.append(spectra)
        np.testing.assert_allclose(results[0]['D_nonmag'],-results[1]['D_nonmag'],atol=1e-12)
        for s in results:np.testing.assert_allclose(s['D_raw'],s['D_mag']+s['D_nonmag'],atol=1e-14)

    @unittest.skipUnless(all(Path(SOURCE).with_suffix('.'+suffix).is_file() for suffix in ('raw1','raw2','broad1','broad2','rawxmcd','inso','injoint','inc')), 'Requires original local WIEN2k audit companions; not distributed')
    def test_validated_resume_npz_and_source_rejection(self):
        cfg=replace(Config(),energy_points=83,detector_grid=9,depth_steps=9,thickness_nm=1.)
        # Windows sandbox ACLs do not support tempfile's private mode=0700 directory.
        with nullcontext(Path('outputs')/('test_017_xy_'+uuid.uuid4().hex)) as root:
            root.mkdir()
            run(SOURCE,root,cfg,'xy',[0.],[0.],no_plots=True,skip_convergence=True)
            checkpoint=root/'cases'/tag(0,0)/'checkpoint.npz';before=hashlib.sha256(checkpoint.read_bytes()).hexdigest()
            npz_before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*.npz')}
            with patch('emcd_sim.ni_017_high_mistilt_xy.calculate_case',side_effect=AssertionError('Unexpected rerun')):
                run(SOURCE,root,cfg,'xy',[0.],[0.],plot_only=True,no_plots=True,skip_convergence=True)
            self.assertEqual(before,hashlib.sha256(checkpoint.read_bytes()).hexdigest())
            self.assertTrue(all(hashlib.sha256(p.read_bytes()).hexdigest()==v for p,v in npz_before.items()))
            for p in root.rglob('*.npz'):
                with np.load(p,allow_pickle=False) as saved:self.assertTrue(all(a.dtype!=object for a in saved.values()))
            settings=root/'run_settings.json';d=json.loads(settings.read_text());d['signature']='invalid';settings.write_text(json.dumps(d))
            with self.assertRaises(ValueError):run(SOURCE,root,cfg,'xy',[0.],[0.],no_plots=True,skip_convergence=True)


if __name__=='__main__':unittest.main()
