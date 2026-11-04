"""Independent provider, non-FCC indexing, Qt and persistence acceptance."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from dataclasses import asdict,replace
from decimal import Decimal,localcontext
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
from ase.io import write
from emcd_sim.adaptive_scattering import adaptive_factor,coefficient_data,provenance,COEFFICIENT_SHA256
from emcd_sim.elastic_providers import ADAPTIVE,LOBATO,LEGACY,factors_for_provider
from emcd_sim.gui.geometry import Structure,Settings,geometry,elastic_model,align_bragg,indices,preview
from emcd_sim.gui.emcd_forward import material_reason
from unified_elastic_cases import cases,reciprocal_cross,analytical_frame,independent_factor,bw_ms


def test_all_118_origin_low_high_and_decimal_precision():
    for z in range(1,119):
        g=np.r_[0.,np.logspace(-160,-1,20),np.linspace(.1,36,61)]
        values=adaptive_factor(z,g)
        assert np.isfinite(values).all() and (values>0).all()
        assert values[1]==pytest.approx(values[0],rel=1e-13)
        with np.errstate(all='raise'):
            assert adaptive_factor(z,1e-200)==pytest.approx(values[0],rel=1e-13)
        a,b,dp=coefficient_data()[z]
        with localcontext() as ctx:
            ctx.prec=65
            for x,actual in zip(g[::10],values[::10]):
                s=Decimal.from_float(float(x));expected=Decimal(0)
                for aa,bb,isdp in zip(a,b,dp):
                    u=Decimal.from_float(float(bb))*s*s
                    numerator=(3+3*u+u*u) if isdp else (2+u)
                    expected+=Decimal.from_float(float(aa))*numerator/(1+u)**(3 if isdp else 2)
                assert actual==pytest.approx(float(expected),rel=2e-11,abs=1e-14)
    for x in [-1,np.nan,np.inf,36.01]:
        with pytest.raises(ValueError):adaptive_factor(28,x)
    for z in [0,119,True,'X','Ni2+']:
        with pytest.raises((ValueError,TypeError)):adaptive_factor(z,0)
    assert provenance()['coefficient_data_sha256']==COEFFICIENT_SHA256


@pytest.mark.parametrize('name',list(cases()))
def test_cif_independent_reciprocal_zone_frame_labels_and_absences(name,tmp_path):
    structure,s=cases()[name];path=tmp_path/(name+'.cif');write(path,structure.atoms)
    imported=Structure.from_cif(path)
    np.testing.assert_allclose(imported.atoms.cell.array@imported.atoms.cell.array.T,
        structure.atoms.cell.array@structure.atoms.cell.array.T,atol=1e-11)
    assert len(imported.atoms)==len(structure.atoms)
    crystal,frame,hs,g,_=geometry(imported,s)
    expected_frame=analytical_frame(imported.atoms.cell.array,s.zone,s.target)
    np.testing.assert_allclose(frame,expected_frame,atol=2e-14)
    vectors=np.asarray(hs)@reciprocal_cross(imported.atoms.cell.array)
    np.testing.assert_allclose(g,vectors@expected_frame[:2].T,atol=3e-14)
    assert all(np.dot(h,s.zone)==0 for h in hs)
    assert s.target in hs and tuple(-v for v in s.target) in hs
    model=elastic_model(imported,s);p=model.potential.original
    factors=factors_for_provider(crystal.species,s.elastic_provider)
    for h in hs:
        np.testing.assert_allclose(p.structure_factor(h),independent_factor(imported,h,factors),atol=2e-12)
        np.testing.assert_allclose(p.structure_factor(tuple(-v for v in h)),p.structure_factor(h).conjugate(),atol=2e-12)
    tilt=align_bragg(g[hs.index(s.target)],(3.,-4.),s.voltage)
    from emcd_sim.geometry import electron_wavelength_angstrom
    q=g[hs.index(s.target)];lam=electron_wavelength_angstrom(s.voltage)
    assert abs(q@q+2*(tilt*.001/lam)@q)<1e-13
    if name.startswith('bcc_fe'):
        assert (1,0,0) not in hs
        assert (1,1,0) in hs  # Correct zone law for BOTH declared zones.
    if name=='cscl':
        assert (1,0,0) in hs and (2,0,0) in hs
        mag=1/4.123
        assert p.structure_factor((1,0,0))==pytest.approx(adaptive_factor('Cs',mag)-adaptive_factor('Cl',mag))
    if name=='hex_zno':
        basis=reciprocal_cross(imported.atoms.cell.array)
        assert np.linalg.norm(basis[0])==pytest.approx(2/(np.sqrt(3)*3.2495))
        assert basis[0]@basis[1]/np.linalg.norm(basis[0])/np.linalg.norm(basis[1])==pytest.approx(.5)
    assert material_reason(imported)


@pytest.mark.parametrize('name',['bcc_fe','cscl','hex_zno','monoclinic'])
def test_non_fcc_matched_bw_ms_refinement(name):
    structure,s=cases()[name]
    coarse=bw_ms(structure,s,mesh=32 if name=='monoclinic' else 24,step=.02)
    fine=bw_ms(structure,s,mesh=48 if name=='monoclinic' else 32,step=.005)
    assert fine['max_intensity_error']<3e-6
    assert fine['max_intensity_error']<=coarse['max_intensity_error']+5e-8
    assert fine['norm_error']<2e-12 and fine['fourier_coefficient_error']<1e-12


def test_new_ni_provider_matched_bw_ms():
    from emcd_sim.scattering import IndependentAtomPotential,nickel_lobato_factor
    from emcd_sim.crystal import fcc_nickel
    from emcd_sim.elastic_providers import DEFAULT_PROVIDER
    s=Settings(zone=(0,0,1),target=(2,0,0),voltage=200,thickness=1,tilt=(0.,0.),beam_cutoff=1.4,potential_cutoff=1.4)
    assert s.elastic_provider==DEFAULT_PROVIDER==ADAPTIVE
    assert IndependentAtomPotential(fcc_nickel()).atomic_factors['Ni'] is nickel_lobato_factor
    assert IndependentAtomPotential.from_provider(fcc_nickel()).atomic_factors['Ni'](0)==adaptive_factor(28,0)
    result=bw_ms(Structure.nickel(),s,mesh=32,step=.005)
    assert result['max_intensity_error']<3e-6 and result['norm_error']<2e-12


@pytest.mark.parametrize('name',list(cases()))
def test_qt_actual_signed_spot_click_bragg_and_stale(name,tmp_path):
    from PySide6 import QtWidgets
    from matplotlib.backend_bases import MouseEvent
    from emcd_sim.gui.app import MainWindow
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    structure,s=cases()[name];w=MainWindow(workspace=tmp_path/name)
    try:
        w.numerical_mode.setCurrentIndex(1)
        w.structure=structure;w.zone.setText(' '.join(map(str,s.zone)));w.target.setText(' '.join(map(str,s.target)))
        w.set_values(dict(beam=s.beam_cutoff,potential=s.potential_cutoff,thickness=1,kv=200,tx=0,ty=0))
        w.refresh();w.show();app.processEvents();w.canvas.draw()
        assert w.run_button.isEnabled() and not w.emcd_button.isEnabled()
        hs,g=w.current[2:4];frame=analytical_frame(structure.atoms.cell.array,s.zone,s.target)
        q=np.asarray(hs)@reciprocal_cross(structure.atoms.cell.array)@frame[:2].T
        np.testing.assert_allclose(w._diffraction_spots.get_offsets(),q,atol=2e-14)
        labels={text.get_text() for text in w.ax.texts}
        assert all(str(h) in labels for h in hs)
        selected=tuple(-v for v in s.target);point=q[hs.index(selected)]
        x,y=w.ax.transData.transform(point)
        w.clicked(MouseEvent('button_press_event',w.canvas,x,y,button=1))
        assert indices(w.target.text())==selected
        w.align();sg=w.current[3][w.current[2].index(selected)]
        from emcd_sim.geometry import electron_wavelength_angstrom
        assert abs(sg@sg+2*(np.asarray(w.settings().tilt)*.001/electron_wavelength_angstrom(200))@sg)<1e-10
        w.last_result=preview(w.structure,w.settings())
        assert w.preview_is_current(w.settings())
        w.elastic_provider_box.setCurrentIndex(w.elastic_provider_box.findData(LEGACY))
        assert not w.preview_is_current(w.settings())
        w.elastic_provider_box.setCurrentIndex(w.elastic_provider_box.findData(ADAPTIVE))
        w.basis_mode.setCurrentIndex(1);assert len(w.current[2])==2
        w.basis_mode.setCurrentIndex(0)
        w.zone.setText('1 0 0');w.target.setText('0 2 0');w.refresh()
        assert w.run_button.isEnabled()
        assert all(h[0]==0 for h in w.current[2])
        assert not w.preview_is_current(w.settings())
        other=Structure.nickel();other.source='replacement CIF context'
        w.structure=other;w.refresh()
        assert not w.preview_is_current(w.settings())
        # Geometry changes cannot reuse old indexed coordinates.
        w.target.setText('0 0 0');w.refresh();assert not w.run_button.isEnabled()
    finally:
        w.close();app.processEvents()


def test_partial_unsupported_large_cell_and_legacy_low_g():
    from ase import Atoms
    from emcd_sim.legacy_atomic_factors import LegacyNeutralAtomFactors
    s=Structure(Atoms('Mo',cell=np.eye(3)*100,pbc=True))
    settings=Settings(zone=(0,0,1),target=(1,0,0),beam_cutoff=.015,potential_cutoff=.015)
    assert np.isfinite(elastic_model(s,settings).hamiltonian_nm_inv()).all()
    s.atoms.info['occupancy']={'0':{'Mo':.5}}
    assert s.elastic_reason
    unsupported=Structure(Atoms('X',cell=np.eye(3)*3,pbc=True))
    assert unsupported.elastic_reason
    huge=Structure(Atoms('Si',cell=np.eye(3)*10000,pbc=True))
    with pytest.raises(ValueError,match='search too large'):geometry(huge,Settings(zone=(0,0,1),target=(1,0,0)))
    with pytest.raises(ValueError):indices('1 0 -1 0')
    with pytest.raises(ValueError):geometry(Structure.nickel(),Settings(zone=(0,0,1),target=(0,0,1)))


def test_elastic_project_read_only_roundtrip_provider_and_historical_default(tmp_path):
    from emcd_sim.gui.project_io import save_elastic_project,load_elastic_project,settings_from_dict
    structure,s=cases()['cscl'];result=preview(structure,s)
    path=tmp_path/'elastic';save_elastic_project(result,path)
    with patch('emcd_sim.physical_elastic.PhysicalElasticModel.amplitudes',side_effect=AssertionError('solver during read')):
        restored=load_elastic_project(path)
    for k in ('amplitudes','g','beam_hkl','intensity'):np.testing.assert_array_equal(restored[k],result[k])
    assert restored['elastic_provider']['provider']==ADAPTIVE
    assert not restored['amplitudes'].flags.writeable
    historical=asdict(Settings());historical.pop('elastic_provider')
    assert settings_from_dict(historical).elastic_provider==LOBATO
    with pytest.raises(FileExistsError):save_elastic_project(result,path)
    with (path/'metadata.json').open('a') as f:f.write(' ')
    with pytest.raises(ValueError,match='checksum'):load_elastic_project(path)


def test_upstream_data_extraction_and_optional_reference_accuracy():
    import importlib.util
    root=Path(__file__).resolve().parents[1]
    archive=root/'build/unified-upstream-pin/coefficients.h5'
    reference=root/'build/unified-upstream-pin/reference/reference_dirac_fock.h5'
    if not archive.exists() or not reference.exists():pytest.skip('Pinned offline HDF5 inputs unavailable')
    h5py=pytest.importorskip('h5py')
    spec=importlib.util.spec_from_file_location('import_adaptive_coefficients',root/'scripts/research/import_adaptive_coefficients.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    from emcd_sim.adaptive_scattering import data_resource
    assert module.encoded_coefficients(archive)==data_resource('coefficients.json').read_bytes()
    with h5py.File(reference) as h:
        for name,group in h.items():
            z=int(name[1:4]);g=group['g'][:];expected=group['feg'][:]
            assert np.max(abs(adaptive_factor(z,g)-expected)/expected)<2e-4


def test_packaged_resources_and_no_upstream_runtime_dependencies(tmp_path):
    import subprocess,sys,zipfile
    from emcd_sim.adaptive_scattering import data_resource
    root=Path(__file__).resolve().parents[1]
    assert 'emcd_sim/data/adaptive_dirac_pade_2026' in (root/'packaging/emcd_gui.spec').read_text()
    archive=tmp_path/'package.zip'
    with zipfile.ZipFile(archive,'w') as z:
        for source in (root/'src/emcd_sim').glob('*.py'):
            z.write(source,'emcd_sim/'+source.name)
        for name in ('coefficients.json','provenance.json','LICENSE','NOTICE'):
            z.writestr('emcd_sim/data/adaptive_dirac_pade_2026/'+name,data_resource(name).read_bytes())
    code="import sys; sys.path.insert(0,sys.argv[1]); from emcd_sim.adaptive_scattering import adaptive_factor; print(adaptive_factor(28,0)); assert not any(n in sys.modules for n in ('h5py','scipy','sympy','adaptive_dirac_pade_scattering_factor_2026'))"
    result=subprocess.run([sys.executable,'-c',code,str(archive)],cwd=tmp_path,capture_output=True,text=True,check=True)
    assert float(result.stdout)>0


def test_emcd_project_explicit_new_and_unversioned_lobato_compatibility(tmp_path):
    import copy
    from emcd_sim.gui.emcd_forward import calculate,ForwardSettings
    from emcd_sim.gui.project_io import save_project,load_project,rerun_reason,fingerprints,elastic_provider_reason
    cfg=ForwardSettings(energy_scope='edges',grid=9,depth=9,subpixels=16,axis_declared=True,angular_maps=False,channeling_model='single',correction=False)
    for provider in (LOBATO,ADAPTIVE):
        s=Settings(zone=(0,0,1),target=(2,0,0),voltage=200,thickness=1,beam_cutoff=1.2,potential_cutoff=1.2,elastic_provider=provider)
        result=calculate(Structure.nickel(),s,cfg)
        assert result['metadata']['elastic_provider']['provider']==provider
        if provider==LOBATO:
            # Construct an old-format control in a NEW test folder, without
            # touching any historical project or numerical reference arrays.
            for method in result['methods'].values():
                method['metadata']['settings'].pop('elastic_provider')
                method['metadata'].pop('elastic_provider')
            result['metadata'].pop('elastic_provider')
        path=tmp_path/provider;save_project(result,path)
        with patch('emcd_sim.physical_elastic.PhysicalElasticModel.amplitudes',side_effect=AssertionError('solver during open')):
            opened=load_project(path)
        assert fingerprints(opened)==fingerprints(result)
        assert opened['settings'].elastic_provider==provider
        assert not elastic_provider_reason(opened)
        if provider==ADAPTIVE:
            altered=copy.copy(opened);altered['metadata']=dict(opened['metadata'],elastic_provider=dict(opened['metadata']['elastic_provider'],coefficient_data_sha256='wrong'))
            assert 'provenance mismatch' in rerun_reason(altered)


def test_qt_open_elastic_project_keeps_current_inputs_and_saved_arrays(tmp_path):
    from PySide6 import QtWidgets
    from emcd_sim.gui.app import MainWindow
    from emcd_sim.gui.project_io import save_elastic_project
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    structure,s=cases()['cscl'];result=preview(structure,s)
    path=tmp_path/'saved';save_elastic_project(result,path)
    w=MainWindow(workspace=tmp_path/'workspace')
    try:
        before=w.settings();source=w.structure.description()
        with patch.object(QtWidgets.QFileDialog,'getExistingDirectory',return_value=str(path)),patch(
                'emcd_sim.gui.geometry.elastic_model',side_effect=AssertionError('solver during open')):
            w.open_elastic_project_dialog()
        assert w.settings()==before and w.structure.description()==source
        saved=w.dialogs[-1].saved_elastic_result
        np.testing.assert_array_equal(saved['amplitudes'],result['amplitudes'])
        assert saved['elastic_provider']['provider']==ADAPTIVE
        w.dialogs[-1].close()
    finally:
        w.close();app.processEvents()
