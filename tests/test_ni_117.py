"""Focused [117] indexing, orientation, tensor, FFT and parity checks."""
from dataclasses import replace
import numpy as np
import pytest
from emcd_sim.ni_117_geometry import Ni117Geometry
from emcd_sim.ni_017_geometry import Ni017Geometry
from emcd_sim.gui.geometry import Structure, Settings, geometry, orientation, indices, excitation, align_bragg, elastic_model
from emcd_sim.gui.emcd_forward import ForwardSettings, calculate, tensors
from emcd_sim.gui.project_io import save_project, load_project, fingerprints, settings_from_dict
from emcd_sim.multislice_double_channeling import ProjectedNiFFT, incident_fields
from emcd_sim.mirror_parity import row_mirror_diagnostics


def settings(mode='full', **kwargs):
    return replace(Settings(zone=(1,1,7),target=(2,-2,0),voltage=200,
        tilt=(Ni117Geometry().bragg_tilt(),0),thickness=2,beam_cutoff=3.2,potential_cutoff=3.8,basis_mode=mode),**kwargs)


def config(**kwargs):
    g=np.sqrt(8)/3.524
    return replace(ForwardSettings(axis_declared=True,propagation='both',energy_scope='edges',grid=9,
        depth=17,subpixels=8,fft_grid=24,slice_step=.04,centers=((g/2,g/2),(g/2,-g/2)),
        radius=.16*g,correction=False,worker_mode='manual',parallel_workers=1),**kwargs)


def test_negative_indices_handedness_metric_and_bragg():
    geo=Ni117Geometry();s=settings();c,R,h,g,m=geometry(Structure.nickel(),s)
    assert indices('(2,-2,0)')==indices('(2,−2,0)')==(2,-2,0)
    np.testing.assert_allclose(R,geo.frame,atol=1e-15)
    np.testing.assert_allclose(np.cross(R[0],R[1]),R[2],atol=1e-15)
    assert np.linalg.det(R)==pytest.approx(1)
    assert c.is_allowed(s.target) and np.dot(s.target,s.zone)==0
    assert (2,2,0) not in h and s.target in h
    np.testing.assert_allclose(g[h.index(s.target)],[np.sqrt(8)/3.524,0],atol=1e-15)
    assert excitation(g[h.index(s.target)],s.tilt,200)==pytest.approx(0,abs=1e-15)
    np.testing.assert_allclose(align_bragg(g[h.index(s.target)],(0,0),200),s.tilt,atol=1e-14)
    assert excitation(g[h.index(s.target)],(s.tilt[0]+.2,0),200)==pytest.approx(.0002*np.sqrt(8)/3.524)


@pytest.mark.parametrize('cutoff',[3.2,3.8,4.6,5.4,6.2])
def test_complete_fcc_zolz_and_oblique_fft(cutoff):
    geo=Ni117Geometry();s=settings(beam_cutoff=cutoff)
    c,R,h,g,_=geometry(Structure.nickel(),s)
    assert h==geo.beams(cutoff).hkl
    assert all(sum(a*b for a,b in zip(v,(1,1,7)))==0 and c.is_allowed(v) for v in h)
    hh,gg=geo.harmonics(32,cutoff);lookup={tuple(v):i for i,v in enumerate(hh)}
    np.testing.assert_allclose(gg[[lookup[v] for v in h]],g,atol=1e-14)
    # A true 2D field includes the long transverse reciprocal direction.
    assert any(abs(v[1])>1 for v in g)
    with pytest.raises(ValueError):geo.harmonics(12,6.2)


def test_existing_frames_and_old_project_default_are_preserved():
    cell=Structure.nickel().atoms.cell.array
    np.testing.assert_array_equal(orientation(cell,(0,0,1)),np.eye(3))
    np.testing.assert_allclose(orientation(cell,(0,1,7)),Ni017Geometry().frame,atol=1e-15)
    assert settings_from_dict(dict(zone=[0,1,7],target=[2,0,0])).basis_mode=='full'
    with pytest.raises(ValueError):geometry(Structure.nickel(),settings('two-beam',target=(2,2,0)))


def test_old_117_frame_cannot_silently_reinterpret_saved_tilts():
    from emcd_sim.gui.project_io import structure_snapshot,frame_rerun_reason
    structure=Structure.nickel();cell=structure.atoms.cell.array
    z=np.array([1.,1.,7.]);z/=np.linalg.norm(z)
    x=cell[0]-cell[0].dot(z)*z;x/=np.linalg.norm(x)
    old=np.stack((x,np.cross(z,x),z))
    result=dict(settings=settings(),metadata=dict(frame=old.tolist()),structure_snapshot=structure_snapshot(structure))
    assert 'earlier local frame' in frame_rerun_reason(result)
    result['metadata']['frame']=Ni117Geometry().frame.tolist()
    assert frame_rerun_reason(result)==''


@pytest.mark.parametrize('frame',[None,[[1,0]],[[float('nan')]*3]*3,'invalid'])
def test_missing_or_invalid_saved_117_frame_blocks_input_reuse(frame):
    from emcd_sim.gui.project_io import structure_snapshot,frame_rerun_reason
    result=dict(settings=settings(),metadata=dict(frame=frame),structure_snapshot=structure_snapshot(Structure.nickel()))
    assert frame_rerun_reason(result)
    result['settings']=replace(result['settings'],zone=(0,1,7))
    assert frame_rerun_reason(result)==''


@pytest.mark.parametrize('solver',['bloch','fft-multislice','both'])
def test_117_cutoff_and_sampling_warnings_apply_to_all_solvers(solver):
    from emcd_sim.gui.propagation import numerical_info
    structure=Structure.nickel();s=settings(potential_cutoff=2.5)
    cfg=config(propagation=solver,grid=33)
    info=numerical_info(structure,s,cfg,check_memory=False)
    assert 'no off-row' in info['potential_support_warning']
    assert any('0.2296' in w for w in info['numerical_warnings'])
    assert not numerical_info(structure,replace(s,potential_cutoff=6.2),replace(cfg,grid=97),check_memory=False)['numerical_warnings']
    assert not numerical_info(structure,replace(s,basis_mode='two-beam'),cfg,check_memory=False)['potential_support_warning']


def test_automatic_unsupported_orientation_fails_without_mesh_retries():
    from unittest.mock import patch
    from emcd_sim.gui.numerical_settings import resolve_parameters
    with patch('emcd_sim.gui.propagation.numerical_info',side_effect=ValueError('Unsupported FFT zone; no automatic fallback.')) as check:
        with pytest.raises(ValueError,match='no automatic fallback'):
            resolve_parameters(Structure.nickel(),settings(zone=(1,1,1)),config())
    assert check.call_count==1


def test_crystal_magnetization_rotation_psd_and_reversal():
    R=Ni117Geometry().frame;plus,minus=tensors(config(),np.array([831.271,848.698]),R)
    np.testing.assert_allclose(R@np.array([0,0,1]),[0,-2/np.sqrt(102),7/np.sqrt(51)])
    t=plus.tensor_angstrom2_per_ev
    np.testing.assert_allclose(t,t.conj().transpose(0,2,1),atol=1e-15)
    np.testing.assert_allclose(minus.tensor_angstrom2_per_ev,t.conj(),atol=1e-15)
    assert np.linalg.eigvalsh(t).min()>=-1e-15


def test_explicit_two_beam_fft_is_closed_unitary_and_independent():
    s=settings('two-beam');elastic=elastic_model(Structure.nickel(),s)
    grid=ProjectedNiFFT.build(elastic,grid_points=24,potential_cutoff=s.potential_cutoff,
        projected_geometry=Ni117Geometry(),retained_hkl=elastic.beams.hkl)
    fields,z,*_=incident_fields(grid,2,depth_steps=17,slice_step_nm=.02)
    keep=np.zeros(grid.g.shape[0],bool);keep[grid.indices(elastic.beams.hkl)]=True
    np.testing.assert_array_equal(fields[:,~keep],0)
    np.testing.assert_allclose(np.sum(abs(fields)**2,axis=1),1,atol=1e-12)
    np.testing.assert_allclose(fields[:,keep],elastic.amplitudes(z),atol=2e-6)
    # For this cutoff the ideal target kick is independently built from FFT U.
    assert grid.g[grid.retained_indices[1],0]>0


def test_mirror_diagnostics_do_not_force_antisymmetry():
    q=np.linspace(-1,1,9);x,y=np.meshgrid(q,q)
    stats,parts=row_mirror_diagnostics(x,y,dict(magnetic=y+.2,nonmagnetic=1+x*x+y*y,total=1+y))
    assert stats['magnetic']['even_fraction']>0
    assert stats['nonmagnetic']['odd_fraction']==0
    np.testing.assert_allclose(parts['magnetic__mirror_even']+parts['magnetic__mirror_odd'],y+.2)
    with pytest.raises(ValueError):row_mirror_diagnostics(x,y+.1,dict(magnetic=y))


def test_independent_analytical_thales_control(tmp_path,monkeypatch):
    import importlib.util
    from pathlib import Path
    path=Path(__file__).resolve().parents[1]/'scripts/ni_117_root_cause.py'
    spec=importlib.util.spec_from_file_location('ni117_control',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    monkeypatch.setattr(module,'OUT',tmp_path)
    stats=module.analytical_control()
    assert stats['hermitian'] and stats['minimum_eigenvalue']>0
    assert stats['magnetic_mirror_residual']<1e-12
    assert stats['nonmagnetic_mirror_residual']<1e-12
    assert stats['reversal_odd_residual']==0
    # Mirror relation does not imply uniform magnitude along the circle.
    assert stats['magnetic_upper_arc_max']>2*stats['magnetic_upper_arc_min']>0


def test_checkpoint_reuse_allows_only_verified_ownership_change():
    import importlib.util
    from pathlib import Path
    spec=importlib.util.spec_from_file_location('ni117_validation',Path(__file__).resolve().parents[1]/'scripts/ni_117_emcd_validation.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    old=dict(settings={'thickness':8},physics_sha256={'multislice_double_channeling.py':'old','other.py':'same'})
    new=dict(settings={'thickness':8},physics_sha256={'multislice_double_channeling.py':'new','other.py':'same'})
    proof=dict(bitwise_equal=True,arrays_compared=52,prior_kernel_sha256='old',final_kernel_sha256='new')
    assert module.compatible_identity(old,new,proof)
    assert not module.compatible_identity(old,new,{})
    assert not module.compatible_identity(old,dict(new,settings={'thickness':12}),proof)
    assert not module.compatible_identity(old,dict(new,physics_sha256={'multislice_double_channeling.py':'new','other.py':'changed'}),proof)


def test_outgoing_energy_carrier_and_projected_split_order():
    from scipy.linalg import expm
    from emcd_sim.double_channeling import outgoing_elastic
    s=settings('two-beam',tilt=(Ni117Geometry().bragg_tilt()+.2,.1))
    elastic=elastic_model(Structure.nickel(),s);loss=831.271;q=(.4,.35)
    outgoing=outgoing_elastic(elastic,q,loss)
    assert outgoing.microscope.acceleration_kv==pytest.approx(200-loss/1000)
    np.testing.assert_allclose(outgoing.microscope.incident_k_xy,elastic.microscope.incident_k_xy+q)
    grid=ProjectedNiFFT.build(elastic,grid_points=24,potential_cutoff=s.potential_cutoff,
        projected_geometry=Ni117Geometry(),retained_hkl=elastic.beams.hkl)
    initial=np.zeros(grid.g.shape[0],complex);initial[0]=1
    exact=expm(2j*outgoing.hamiltonian_nm_inv())@np.array([1,0])
    errors=[]
    for step in (.01,.005):
        value=grid.plan(loss,q).advance(initial,int(2/step),step)
        assert np.sum(abs(value)**2)==pytest.approx(1,abs=1e-12)
        errors.append(np.linalg.norm(value[grid.retained_indices]-exact))
    assert errors[1]<.3*errors[0] and errors[1]<1e-6
    initial[grid.retained_indices]=[.7+.1j,.2-.3j]
    before=initial.copy();grid.plan(loss,q).advance(initial,2,.01)
    np.testing.assert_array_equal(initial,before)


@pytest.mark.parametrize('mode',['two-beam','full'])
@pytest.mark.parametrize('channeling',['single','double'])
def test_bw_ms_raw_parity_detectors_and_project(mode,channeling,tmp_path):
    r=calculate(Structure.nickel(),settings(mode),config(channeling_model=channeling))
    for method in r['methods'].values():
        assert method['metadata']['magnetization_crystal']==[0,0,1]
        assert abs(method['metadata']['s_target'])<1e-14
        assert not any(row['mirror_reuse'] for row in method['metadata']['angular_evaluation'])
        np.testing.assert_allclose(method['weights']['A'][::-1],method['weights']['B'],atol=1e-15)
        stats,_=row_mirror_diagnostics(method['qx'],method['qy'],dict(magnetic=method['maps']['L3']['I_mag'],nonmagnetic=method['maps']['L3']['I_nonmag']))
        assert stats['magnetic']['even_fraction']>.005  # Correct crystal [001] has local My != 0.
        assert stats['nonmagnetic']['odd_fraction']<1e-10
    difference=r['comparison']['edges']['L3']['detector']['A_mag']['absolute']*100
    assert difference<(1e-4 if mode=='two-beam' else .01)
    if mode=='two-beam':assert r['fft']['summary']['max_excluded_population']<1e-13
    save_project(r,tmp_path/'saved')
    reopened=load_project(tmp_path/'saved')
    assert reopened['settings'].basis_mode==mode
    assert fingerprints(reopened)==fingerprints(r)


def test_gui_target_basis_and_crystal_axis_restore_without_solver(tmp_path):
    import os
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    from unittest.mock import patch
    from pathlib import Path
    from PySide6 import QtWidgets,QtGui,QtCore
    from matplotlib import get_data_path
    from emcd_sim.gui.app import MainWindow
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    if not QtGui.QFontDatabase.families():
        font=QtGui.QFontDatabase.addApplicationFont(str(Path(get_data_path())/'fonts/ttf/DejaVuSans.ttf'))
        app.setFont(QtGui.QFont(QtGui.QFontDatabase.applicationFontFamilies(font)[0],9))
    with patch('emcd_sim.gui.stage_b.EMCDWorker.start',side_effect=AssertionError('GUI must not solve')),patch('emcd_sim.gui.app.PreviewWorker.start',side_effect=AssertionError('GUI must not solve')):
        w=MainWindow(tmp_path/'workspace')
        try:
            w.zone.setText('1 1 7');w.target.setText('2 -2 0');w.apply_orientation()
            w.lock.setCurrentText('Y');w.align()
            assert w.settings().target==(2,-2,0) and w.settings().zone==(1,1,7)
            assert abs(excitation(w.current[3][w.current[2].index((2,-2,0))],w.settings().tilt,w.settings().voltage))<1e-13
            w.restore_detectors();np.testing.assert_allclose(w.detectors[0],[w.detectors[1,0],-w.detectors[1,1]],atol=1e-13)
            w.basis_mode.setCurrentIndex(1)
            assert w.settings().basis_mode=='two-beam' and w.current[2]==((0,0,0),(2,-2,0))
            np.testing.assert_allclose(w.forward_settings().magnetization,(0,0,1))
            w.propagation_box.setCurrentIndex(2)
            assert not w._numerical_error
            w.reset_reference()
            assert w.settings().basis_mode=='full' and w.settings().zone==(0,1,7)
        finally:
            w.close();app.processEvents()
