"""Declared synthetic research inputs, not measured/fitted Fe constants."""
from dataclasses import asdict, replace
import hashlib,json
from pathlib import Path
import numpy as np
import pytest
from emcd_sim.atomic_ionization import (AtomicMaterialParameters, ORBITALS,
    transitions_for_material, export_atomic_parameters, dipole_2p_to_3d)
from emcd_sim.ni_local_mdff import (NiLocalConfig, ni_local_transitions,
    hydrogenic_radial_dipole_angstrom, core_spinor_amplitude)
from emcd_sim.mdff_tensor import dipole_tensor_from_transitions


def synthetic_parameters():
    return AtomicMaterialParameters(element='Fe',atomic_number=26,edge_energies_ev=(710.,723.),
        radial_integral_angstrom=.04,crystal_field_basis='real_cubic_eg_t2g',crystal_field_ev=1.1,
        exchange_ev=.6,spin_resolved_holes=((.1,.7),(.2,.6),(.3,.5),(.2,.8),(.4,.6)),
        magnetization_local=(0,0,1),frame_to_crystal=((1,0,0),(0,1,0),(0,0,1)),broadening_ev=.9,
        source='EMCD-Sim original SYNTHETIC research fixture; every number chosen for software testing, NOT Fe spectroscopy',
        radial_source='Synthetic .04 Angstrom effective integral, no atomic calculation or material fit',
        validity='SYNTHETIC NON-Ni DEMONSTRATION ONLY; no physical comparisons or quantitative Fe EMCD',status='synthetic')


def parameter_file(path,p=None):
    d=dict(schema=1,kind='atomic_2p3d',parameters=asdict(p or synthetic_parameters()),energy_ev=np.linspace(702,731,117).tolist())
    path.write_text(json.dumps(d),encoding='utf-8')
    return path


@pytest.mark.parametrize('sign',[1,-1])
@pytest.mark.parametrize('cfg',[NiLocalConfig(),NiLocalConfig(crystal_field_10dq_ev=1.2,exchange_split_ev=.37,eg_up_holes=0,t2g_down_holes=.8)])
def test_exact_ni_events_and_tensors(cfg,sign):
    p=replace(synthetic_parameters(),element='Ni',atomic_number=28,edge_energies_ev=(cfg.l3_ev,cfg.l2_ev),
        radial_integral_angstrom=hydrogenic_radial_dipole_angstrom(cfg.zeff_2p,cfg.zeff_3d),
        crystal_field_ev=cfg.crystal_field_10dq_ev,exchange_ev=cfg.exchange_split_ev,
        spin_resolved_holes=tuple((getattr(cfg,('eg' if o in ('z2','x2_y2') else 't2g')+'_up_holes'),
            getattr(cfg,('eg' if o in ('z2','x2_y2') else 't2g')+'_down_holes')) for o in ORBITALS))
    old=ni_local_transitions(cfg,magnetization_sign=sign);new=transitions_for_material(p,magnetization_sign=sign)
    for name in ('energy_ev','dipoles_angstrom','weights','edge'):
        np.testing.assert_array_equal(getattr(old,name),getattr(new,name))
    e=np.linspace(840,882,121)
    np.testing.assert_array_equal(dipole_tensor_from_transitions(old,e,.8).tensor_angstrom2_per_ev,
        dipole_tensor_from_transitions(new,e,.8).tensor_angstrom2_per_ev)


def test_angular_algebra_independent_sphere_quadrature():
    # Integrate Y_1m* Cartesian n Y_2m on sphere independently of the CG table.
    from scipy.special import sph_harm_y
    z,w=np.polynomial.legendre.leggauss(24);phi=np.arange(48)*2*np.pi/48
    theta=np.arccos(z)[:,None];az=phi[None,:]
    n=np.stack(np.broadcast_arrays(np.sin(theta)*np.cos(az),np.sin(theta)*np.sin(az),np.cos(theta)),axis=-1)
    for j in (1,3):
        for mj in range(-j,j+1,2):
            for spin in (-1,1):
                ml=(mj-spin)//2
                cg=core_spinor_amplitude(j,mj,spin)
                for m in range(-2,3):
                    expected=np.zeros(3,complex) if abs(ml)>1 else cg*np.einsum('ij,ijk,i->k',
                        sph_harm_y(1,ml,theta,az).conj()*sph_harm_y(2,m,theta,az),n,w)*2*np.pi/48
                    np.testing.assert_allclose(dipole_2p_to_3d(j,mj,m,spin),expected,atol=2e-15,rtol=1e-13)
    for j in (1,3):
        for mj in range(-j,j+1,2):
            assert sum(core_spinor_amplitude(j,mj,s)**2 for s in (-1,1))==pytest.approx(1)


def test_psd_reversal_strength_and_radial_scaling():
    p=synthetic_parameters();e=np.linspace(695,738,5001)
    a,b=[dipole_tensor_from_transitions(transitions_for_material(p,magnetization_sign=s),e,p.broadening_ev).tensor_angstrom2_per_ev for s in (1,-1)]
    np.testing.assert_allclose(a,a.conj().swapaxes(1,2),atol=1e-18)
    assert np.linalg.eigvalsh(a).min()>-1e-18
    np.testing.assert_allclose(b,a.conj(),atol=2e-18)
    assert abs(a.imag).max()>1e-6
    t=transitions_for_material(p)
    strength=np.sum(t.weights*np.sum(abs(t.dipoles_angstrom)**2,axis=1))
    assert np.trapezoid(np.trace(a,axis1=1,axis2=2).real,e)==pytest.approx(strength,rel=1e-12)
    full=transitions_for_material(replace(p,spin_resolved_holes=((1.,1.),)*5))
    assert np.sum(full.weights*np.sum(abs(full.dipoles_angstrom)**2,axis=1))==pytest.approx(4*p.radial_integral_angstrom**2)
    doubled=transitions_for_material(replace(p,radial_integral_angstrom=2*p.radial_integral_angstrom))
    np.testing.assert_array_equal(doubled.dipoles_angstrom,2*t.dipoles_angstrom)
    reversed_p=replace(p,exchange_ev=p.exchange_ev,spin_resolved_holes=tuple(pair[::-1] for pair in p.spin_resolved_holes))
    # Spin-symmetric holes AND zero exchange remove the magnetic signal.
    nm=replace(p,exchange_ev=0,spin_resolved_holes=((.5,.5),)*5)
    ta,tb=[dipole_tensor_from_transitions(transitions_for_material(nm,magnetization_sign=s),e,nm.broadening_ev).tensor_angstrom2_per_ev for s in (1,-1)]
    np.testing.assert_array_equal(ta,tb)


@pytest.mark.parametrize('changes',[
    dict(element='Co',atomic_number=26),dict(element='O',atomic_number=8),dict(edge_energies_ev=(723,710)),
    dict(radial_integral_angstrom=0),dict(radial_integral_angstrom=float('inf')),dict(broadening_ev=0),
    dict(exchange_ev=-1),dict(crystal_field_basis='invented'),dict(spin_resolved_holes=((.5,.5),)),
    dict(spin_resolved_holes=((0,0),)*5),dict(spin_resolved_holes=((1.1,.5),)*5),dict(magnetization_local=(1,0,0)),
    dict(frame_to_crystal=((-1,0,0),(0,1,0),(0,0,1))),dict(source=''),dict(radial_source=''),dict(status='validated')])
def test_reject_unsupported(changes):
    with pytest.raises(ValueError):transitions_for_material(replace(synthetic_parameters(),**changes))


def test_export_provenance_and_no_overwrite(tmp_path):
    path=parameter_file(tmp_path/'params.json');raw=path.read_bytes()
    out=tmp_path/'tensor.json';source=export_atomic_parameters(path,out)
    assert source.metadata['atomic_parameter_sha256']==hashlib.sha256(raw).hexdigest()
    assert source.metadata['atomic_parameter_source_utf8'].encode()==raw
    assert source.metadata['status']=='synthetic'
    with pytest.raises(FileExistsError):export_atomic_parameters(path,out)
    path.write_text('{}')
    from emcd_sim.imported_mdff import ImportedMDFF
    assert ImportedMDFF.load(out,source.sha256).sha256==source.sha256
    out.write_bytes(out.read_bytes()+b' ')
    with pytest.raises(ValueError,match='checksum'):ImportedMDFF.load(out,source.sha256)


@pytest.mark.parametrize('channel',['single','double'])
def test_atomic_fe_bw_ms_project(tmp_path,channel):
    from ase.build import bulk
    from emcd_sim.gui.geometry import Structure,Settings
    from emcd_sim.gui.generalized_forward import calculate,settings_for_source
    from emcd_sim.gui.project_io import save_project,load_project,source_status
    source=export_atomic_parameters(parameter_file(tmp_path/'params.json'),tmp_path/'tensor.json')
    cfg=settings_for_source(source.path,energy_scope='edges',grid=9,depth=9,subpixels=8,fft_grid=16,slice_step=.01,
        halfwidth=.7,centers=((.2,.2),(.2,-.2)),radius=.12,propagation='both',channeling_model=channel,worker_mode='manual',parallel_workers=1)
    result=calculate(Structure(bulk('Fe','bcc',a=2.866,cubic=True),'Synthetic Fe atomic software demonstration'),
        Settings(zone=(0,0,1),target=(1,1,0),tilt=(-5,7),voltage=200,thickness=.2,beam_cutoff=.6,potential_cutoff=1.2),cfg)
    for method,v in result['methods'].items():
        assert v['metadata']['scientific_status']=='SYNTHETIC TEST ONLY'
        for key in ('I_A_plus','I_A_minus','I_B_plus','I_B_minus'):
            assert np.isfinite(v['spectra'][key]).all() and np.min(v['spectra'][key])>=0
    comparison=result['comparison']['spectra']['I_A_plus']['l2_relative']
    assert comparison<.015
    print('ATOMIC_FE',channel,'BW_MS_I_A_PLUS_L2_RELATIVE',comparison)
    save_project(result,tmp_path/'project');opened=load_project(tmp_path/'project')
    assert source_status(opened)['mdff']['verified']
    np.testing.assert_array_equal(opened['spectra']['D_mag'],result['spectra']['D_mag'])
    assert opened['config'].source_sha256==source.sha256


def test_rigid_frame_and_tamper_rejection(tmp_path):
    from emcd_sim.imported_mdff import ImportedMDFF
    p=synthetic_parameters();frame=((0,0,1),(0,1,0),(-1,0,0))
    source=export_atomic_parameters(parameter_file(tmp_path/'rotated.json',replace(p,frame_to_crystal=frame)),tmp_path/'tensor.json')
    local=source.plus.tensor_angstrom2_per_ev
    rotated=source.tensors(source.energy_ev,np.eye(3),(1,0,0))[0].tensor_angstrom2_per_ev
    np.testing.assert_allclose(rotated,np.einsum('ia,eab,jb->eij',np.array(frame),local,np.array(frame)),atol=1e-18)
    with pytest.raises(ValueError,match='axis'):source.tensors([710,723],np.eye(3),(0,0,1))
    d=json.loads(Path(source.path).read_bytes())
    for mutation in ('checksum','parameters','tensor','model','frame'):
        bad=json.loads(json.dumps(d))
        if mutation=='checksum':bad['atomic_parameter_sha256']='0'*64
        if mutation=='parameters':bad['atomic_parameters']['exchange_ev']=.4
        if mutation=='tensor':
            for key in ('T_plus','T_minus','T_even'):
                bad[key]['real']=(2*np.array(bad[key]['real'])).tolist();bad[key]['imag']=(2*np.array(bad[key]['imag'])).tolist()
        if mutation=='model':bad['atomic_model']='unknown'
        if mutation=='frame':bad['frame_to_crystal']=np.eye(3).tolist()
        path=tmp_path/(mutation+'.json');path.write_text(json.dumps(bad))
        with pytest.raises(ValueError):ImportedMDFF.load(path)


def test_atomic_gui_generation_restoration_and_legacy_gate(tmp_path,monkeypatch):
    from PySide6 import QtWidgets
    from ase.build import bulk
    from emcd_sim.gui.app import MainWindow
    from emcd_sim.gui.geometry import Structure
    from emcd_sim.gui.project_io import save_project,load_project
    import time
    monkeypatch.setenv('EMCD_GUI_WORKSPACE',str(tmp_path/'workspace'))
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    w=MainWindow();errors=[];w.error=errors.append
    p=parameter_file(tmp_path/'parameters.json');output=tmp_path/'generated.json'
    monkeypatch.setattr(QtWidgets.QFileDialog,'getOpenFileName',lambda *a,**k:(str(p),''))
    monkeypatch.setattr(QtWidgets.QFileDialog,'getSaveFileName',lambda *a,**k:(str(output),''))
    try:
        w.numerical_mode.setCurrentIndex(1)
        w.structure=Structure(bulk('Fe','bcc',a=2.866,cubic=True),'Synthetic atomic Fe software test')
        w.zone.setText('0 0 1');w.target.setText('1 1 0')
        w.set_values(dict(kv=200,tx=-5,ty=7,thickness=.2,beam=.6,potential=1.2,grid=9,depth=9,subpixels=8,halfwidth=.7,radius=.12))
        w.model_box.setCurrentIndex(2);w.generate_atomic_tensor()
        assert w.imported_info is not None
        assert 'APPROXIMATE ATOMIC MODEL' in w.imported_status.text() and 'SYNTHETIC' in w.imported_status.text()
        assert not w.imported_declaration.isChecked()
        w.imported_declaration.setChecked(True);w.energy_scope.setCurrentIndex(1);w.angular_maps.setChecked(True)
        w.detectors=np.array([[.2,.2],[.2,-.2]]);w.sync_detectors();w.correction.setChecked(False);w.refresh();w.emcd_stale()
        assert w.emcd_button.isEnabled(),w.emcd_button.toolTip()
        w.start_emcd();limit=time.monotonic()+90
        while w.busy and time.monotonic()<limit:app.processEvents();time.sleep(.01)
        assert not w.busy and not errors,errors
        assert w.emcd_result['metadata']['imported_mdff']['atomic_parameters']['atomic_number']==26
        save_project(w.emcd_result,tmp_path/'project');w.emcd_result=load_project(tmp_path/'project');w.use_result_settings()
        assert w.imported_info.metadata['atomic_model']=='independent_electron_cubic_2p3d_v1'
        p.unlink()  # Embedded original parameters are sufficient; tensor is the rerun source.
        w.validate_imported_mdff(expected_sha256=w.emcd_result['config'].source_sha256)
        assert w.imported_info is not None
        output.unlink();w.emcd_result=load_project(tmp_path/'project');w.use_result_settings();w.emcd_stale()
        assert not w.emcd_button.isEnabled() and w.imported_info is None
        w.model_box.setCurrentIndex(1);w.emcd_stale();assert not w.emcd_button.isEnabled()
    finally:
        if w.busy:w.cancel();w.worker.wait(15000)
        for dialog in w.dialogs:dialog.close()
        w.close();app.processEvents()



def test_core_soc_eigenstates_independent_operator():
    # Independent L.S operator in |ml,ms> product basis (hbar=1).
    basis=[(ml,s) for ml in (-1,0,1) for s in (-1,1)]
    h=np.diag([ml*s/2 for ml,s in basis])
    for i,(ml,s) in enumerate(basis):
        if ml<1 and s==1:
            j=basis.index((ml+1,-1));h[i,j]=h[j,i]=np.sqrt(2-ml*(ml+1))/2
    vectors=[]
    for two_j,eigen in ((1,-1.),(3,.5)):
        for mj in range(-two_j,two_j+1,2):
            v=np.array([core_spinor_amplitude(two_j,mj,s) if 2*ml+s==mj else 0 for ml,s in basis])
            np.testing.assert_allclose(h@v,eigen*v,atol=2e-16)
            vectors.append(v)
    np.testing.assert_allclose(np.array(vectors)@np.array(vectors).T,np.eye(6),atol=3e-16)


def test_small_radial_explicit_rejection_and_parameter_schema(tmp_path):
    for r in (1e-20,np.nextafter(0.,1.)):
        with pytest.raises(ValueError,match='threshold|nonzero'):transitions_for_material(replace(synthetic_parameters(),radial_integral_angstrom=r))
    p=tmp_path/'invalid.json'
    for document in ([],{},dict(schema=1,kind='atomic_2p3d',parameters={},energy_ev=[710,723])):
        p.write_text(json.dumps(document))
        with pytest.raises(ValueError):export_atomic_parameters(p,tmp_path/'no-output.json')
        assert not (tmp_path/'no-output.json').exists()


def test_atomic_scope_guard_rejects_mutations():
    from single_element_source_guard import assert_current_extension,ROOT
    for path in ('src/emcd_sim/atomic_ionization.py','src/emcd_sim/imported_mdff.py','src/emcd_sim/gui/imported_tensor_ui.py'):
        with pytest.raises(AssertionError,match='Unregistered physics change'):
            assert_current_extension({path:(ROOT/path).read_bytes()+b'\n# mutation\n'})
