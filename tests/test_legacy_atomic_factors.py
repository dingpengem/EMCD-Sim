"""Real-table integration tests; external data never enter the source tree."""
import os
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from emcd_sim.legacy_atomic_factors import (LegacyNeutralAtomFactors, atomic_number,
    SOURCE_POTENTIAL_SCALE, MOTT_MIN_STL, TABLE_ENVIRONMENT, factors_for_elastic_species)
from emcd_sim.scattering import IndependentAtomPotential, FourierCutoffPotential, nickel_lobato_factor
from emcd_sim.crystal import Crystal, fcc_nickel
from emcd_sim.elastic import BeamSet
from emcd_sim.geometry import Microscope, electron_wavelength_angstrom
from emcd_sim.physical_elastic import PhysicalElasticModel


@pytest.fixture
def table():
    path=os.environ.get(TABLE_ENVIRONMENT)
    if not path:
        pytest.skip(f'Set {TABLE_ENVIRONMENT} to the reviewed external table')
    return LegacyNeutralAtomFactors.from_file(path)


def test_ase_periodic_table_lookup():
    pytest.importorskip('ase')
    assert atomic_number('H')==1 and atomic_number('Ni')==28
    assert atomic_number('Cf')==98 and atomic_number(np.int64(55))==55
    for invalid in [0,99,'Es','X','Ni2+','28','ni',True,np.bool_(False),28.0]:
        with pytest.raises((ValueError,TypeError)):
            atomic_number(invalid)


def test_unconfigured_non_ni_does_not_change_default_or_enable_materials(monkeypatch):
    monkeypatch.delenv(TABLE_ENVIRONMENT,raising=False)
    assert factors_for_elastic_species(('Ni',))['Ni'] is nickel_lobato_factor
    with pytest.raises(ValueError,match=TABLE_ENVIRONMENT):
        factors_for_elastic_species(('Cu',))


def test_missing_configured_file_is_diagnostic_and_ni_still_runs(tmp_path,monkeypatch):
    path=tmp_path/'absent-scattering.py'
    monkeypatch.setenv(TABLE_ENVIRONMENT,str(path))
    with pytest.raises(ValueError,match='Legacy neutral-atom elastic provider cannot read') as error:
        factors_for_elastic_species(('Cs','Cl'))
    assert TABLE_ENVIRONMENT in str(error.value)
    assert str(path) in str(error.value) and 'not bundled' in str(error.value)
    crystal=fcc_nickel()
    factors=factors_for_elastic_species(crystal.species)
    assert factors['Ni'] is nickel_lobato_factor
    model=PhysicalElasticModel(crystal,Microscope(200),BeamSet(),
        IndependentAtomPotential(crystal,atomic_factors=factors))
    np.testing.assert_allclose((abs(model.amplitudes(np.array([9.])))**2).sum(),1,atol=1e-13)


def test_hash_failure_precedes_execution_without_requiring_table(tmp_path):
    path=tmp_path/'unreviewed.py'
    path.write_text("raise RuntimeError('must not execute unreviewed code')\n",encoding='utf-8')
    with pytest.raises(ValueError,match='SHA256'):
        LegacyNeutralAtomFactors.from_file(path)


def test_gui_missing_provider_keeps_geometry_and_ni_available(tmp_path,monkeypatch):
    pytest.importorskip('ase')
    from emcd_sim.gui.geometry import Structure,Settings,elastic_model,geometry
    path=tmp_path/'absent.py'
    monkeypatch.setenv(TABLE_ENVIRONMENT,str(path))
    cu=Structure.nickel();cu.atoms.set_chemical_symbols(['Cu']*4)
    assert TABLE_ENVIRONMENT in cu.elastic_reason_for('legacy-atomicscatfact-neutral-v1')
    settings=Settings(beam_cutoff=2.2,elastic_provider='legacy-atomicscatfact-neutral-v1')
    geometry(cu,settings)  # Geometry-only CIF inspection must remain possible.
    with pytest.raises(ValueError,match=TABLE_ENVIRONMENT):elastic_model(cu,settings)
    ni=Structure.nickel()
    assert not ni.elastic_reason
    assert np.isfinite(elastic_model(ni,replace(settings,elastic_provider='nickel-lobato-2014')).hamiltonian_nm_inv()).all()


def test_reviewed_file_hash_required(table,tmp_path):
    path=tmp_path/'altered.py'
    path.write_bytes(Path(table.source_path).read_bytes()+b'\n')
    with pytest.raises(ValueError,match='SHA256'):
        LegacyNeutralAtomFactors.from_file(path)


def test_all_elements_nodes_limits_and_both_scaling_branches(table):
    m=table._module
    for z in range(1,99):
        limit=3. if z==1 else 12.
        mott=m._METHOD[z-1]==2
        dense=(np.r_[0.,np.linspace(2*MOTT_MIN_STL,limit,257)] if mott else np.linspace(0,limit,257))
        f=table.factor(z,dense)
        assert np.isfinite(f).all() and (f>=0).all()
        for i,stl in enumerate(m._STL):
            if stl>limit/2:continue
            if mott and 0<stl<MOTT_MIN_STL:
                with pytest.raises(ValueError,match='unsupported positive STL'):table.factor(z,2*stl)
                continue
            if m._METHOD[z-1]==2:
                if m._XF[z-1][i]<0:continue
                expected=(m._EF[z-1][0] if stl==0 else
                    (1.145896/SOURCE_POTENTIAL_SCALE)*(z-m._XF[z-1][i])/stl**2)
            else:
                expected=m._EF[z-1][i]
                if expected<0:continue
            assert table.factor(z,2*stl)==pytest.approx(expected,rel=2e-10,abs=3e-10)
        with pytest.raises(ValueError):table.factor(z,np.nextafter(limit,np.inf))
        for invalid in [-1.,np.nan,np.inf]:
            with pytest.raises(ValueError):table.factor(z,invalid)
    assert table.factor(1,0)==pytest.approx(.529)
    assert table.factor(28,0)==pytest.approx(6.569)


def test_no_reinterpolation_or_marker_replacement(table,monkeypatch):
    m=table._module
    # Missing H entries at STL=.01,.02,.03 must be skipped by source cubic.
    for g in [.005,.02,.04,.06,.07,.15,.43,.73,2.99]:
        assert table.factor(1,g)==m.elastic_atomic_scattering_factor(1,g/2)/SOURCE_POTENTIAL_SCALE
    # Treat a rejected (-2) entry exactly like a missing (-1) entry, without
    # changing the external file. Restore module data after this isolated check.
    a=[list(row) for row in m._EF];a[0][1]=-2.
    before=table.factor(1,.02)
    monkeypatch.setattr(m,'_EF',tuple(tuple(row) for row in a))
    assert table.factor(1,.02)==before


def test_ni_provider_comparison_is_not_an_equivalence_claim(table):
    g=np.array([0.,2/3.524,1.,2.])
    legacy=table.factor('Ni',g);lobato=nickel_lobato_factor(g)
    assert np.isfinite(legacy).all()
    assert not np.allclose(legacy,lobato,rtol=1e-5,atol=0)
    # Supplying the external table never replaces the default Ni mapping.
    potential=IndependentAtomPotential(fcc_nickel())
    assert potential.atomic_factors['Ni'] is nickel_lobato_factor


def test_all_44_mott_rows_reject_unreliable_positive_values_and_preserve_origin(table):
    m=table._module
    zs=[z for z in range(1,99) if m._METHOD[z-1]==2]
    assert len(zs)==44
    for z in zs:
        origin=m.elastic_atomic_scattering_factor(z,0)/SOURCE_POTENTIAL_SCALE
        assert table.factor(z,0)==origin
        for stl in [np.nextafter(0.,1.),1e-200,1e-12,1e-5,1e-4,.001,.01,.02,.03,np.nextafter(MOTT_MIN_STL,0.)]:
            # Test g directly as well, so the smallest positive float does
            # not disappear through STL=g/2 before the domain check.
            g=stl*2
            with pytest.raises(ValueError,match='unsupported positive STL'):table.factor(z,g)
        with pytest.raises(ValueError,match='unsupported positive STL'):table.factor(z,np.nextafter(0.,1.))
        for stl in [MOTT_MIN_STL,np.nextafter(MOTT_MIN_STL,np.inf),.05,.1,1.,6.]:
            assert table.factor(z,2*stl)==m.elastic_atomic_scattering_factor(z,stl)/SOURCE_POTENTIAL_SCALE
    # The original source remains unchanged, including the independently
    # confirmed Mo failure; only the adapter rejects the unsupported inputs.
    assert m.elastic_atomic_scattering_factor(42,1e-5)<0
    with pytest.raises(ZeroDivisionError):m.elastic_atomic_scattering_factor(42,1e-200)


def test_large_mott_supercell_nonzero_vectors_are_not_replaced_by_origin(table):
    crystal=Crystal(np.eye(3)*100,np.array([[0.,0,0]]),('Mo',))
    potential=IndependentAtomPotential(crystal,atomic_factors=table.atomic_factors(crystal.species))
    assert np.isfinite(potential.structure_factor((0,0,0)))
    with pytest.raises(ValueError,match='unsupported positive STL'):
        potential.structure_factor((1,0,0))
    with pytest.raises(ValueError,match='unsupported positive STL'):
        BeamSet.zolz(crystal,.1,25,potential=potential)


def test_independent_all_mott_interval_audit(table):
    import importlib.util
    path=Path(__file__).resolve().parents[1]/'scripts/research/audit_legacy_mott.py'
    spec=importlib.util.spec_from_file_location('audit_legacy_mott',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    report=module.audit(table)
    assert report['mott_element_count']==44
    assert report['common_minimum_positive_stl']==MOTT_MIN_STL==.04
    assert all(r['last_inconsistent_interval_end']<=MOTT_MIN_STL for r in report['records'])
    assert max(r['max_relative_error_vs_80_digit_reference'] for r in report['records'])<1e-9


def test_real_cscl_diffraction_and_fcc_extinctions(table):
    crystal=Crystal(np.eye(3)*4.1,np.array([[0.,0,0],[.5,.5,.5]]),('Cs','Cl'))
    potential=IndependentAtomPotential(crystal,atomic_factors=table.atomic_factors(crystal.species))
    expected=table.factor('Cs',1/4.1)-table.factor('Cl',1/4.1)
    assert abs(expected)>1e-4
    assert potential.structure_factor((1,0,0))==pytest.approx(expected)
    beams=BeamSet.zolz(crystal,.55,49,potential=potential)
    assert (1,0,0) in beams.hkl
    model=PhysicalElasticModel(crystal,Microscope(200),beams,potential)
    h=model.hamiltonian_nm_inv()
    np.testing.assert_allclose(h,h.conj().T,atol=1e-14)
    amplitudes=model.amplitudes(np.array([0.,1.,3.]))
    np.testing.assert_allclose((abs(amplitudes)**2).sum(axis=1),1,atol=2e-14)
    assert abs(amplitudes[-1,beams.hkl.index((1,0,0))])**2>1e-8
    fcc=replace(fcc_nickel(),species=('Cu',)*4)
    p=IndependentAtomPotential(fcc,atomic_factors=table.atomic_factors(fcc.species))
    assert (1,0,0) not in BeamSet.zolz(fcc,1.,25,potential=p).hkl


@pytest.mark.parametrize('symbols,positions,a,target,cutoff',[
    (('Cs','Cl'),[[0,0,0],[.5,.5,.5]],4.1,(1,0,0),.55),
    (('Cu',)*4,[[0,0,0],[0,.5,.5],[.5,0,.5],[.5,.5,0]],3.615,(2,0,0),.85),
    (('Mo','Mo'),[[0,0,0],[.5,.5,.5]],3.147,(2,0,0),.85),
])
def test_real_table_bloch_multislice_matched_potential(table,symbols,positions,a,target,cutoff):
    from emcd_sim.projected_geometry import ProjectedGeometry
    from emcd_sim.projected_potential import prepare_projected_potential,potential_site_labels
    from emcd_sim.multislice_double_channeling import FFTSplitStep
    crystal=Crystal(np.eye(3)*a,np.array(positions,float),symbols)
    potential=IndependentAtomPotential(crystal,atomic_factors=table.atomic_factors(symbols))
    geometry=ProjectedGeometry.from_oriented(crystal,(0,0,1),target,labels=potential_site_labels(potential))
    projected=prepare_projected_potential(geometry,potential,200.,24,cutoff)
    assert np.isrealobj(projected.phase_nm_inv)
    prefactor=10*(1+200000/510998.95)*electron_wavelength_angstrom(200)/potential.cell_volume_angstrom3
    coefficients=np.fft.fft2(projected.phase_nm_inv)/24**2
    for i,h in enumerate(projected.hkl):
        if 0<np.linalg.norm(crystal.g_vector(h))<=cutoff:
            assert coefficients.flat[i]==pytest.approx(prefactor*potential.structure_factor(tuple(h)),abs=1e-14)
    beam_cutoff=1.6 if symbols==('Cs','Cl') else 2.2
    beams=BeamSet.zolz(crystal,beam_cutoff,401,potential=potential)
    bw=PhysicalElasticModel(crystal,Microscope(200),beams,FourierCutoffPotential(potential,cutoff))
    g=projected.reciprocal_xy
    kinetic=(-10*np.pi*electron_wavelength_angstrom(200)*(g*g).sum(axis=1)).reshape(24,24)
    plan=FFTSplitStep(projected.phase_nm_inv,kinetic)
    c=np.zeros(24**2,complex);c[0]=1
    fine=plan.advance(c,200,.005)
    coarse=plan.advance(c,100,.01)
    bw_wave=bw.amplitudes(np.array([1.]))[0]
    indices={tuple(h):i for i,h in enumerate(projected.hkl)}
    matched=np.array([indices[h] for h in beams.hkl])
    fine_error=np.max(abs(abs(fine[matched])**2-abs(bw_wave)**2))
    coarse_error=np.max(abs(abs(coarse[matched])**2-abs(bw_wave)**2))
    assert fine_error<2e-6
    assert fine_error<=coarse_error+1e-10
    np.testing.assert_allclose(np.sum(abs(fine)**2),1,atol=1e-12)


def test_gui_elastic_cif_and_inelastic_restrictions_remain_separate(table,tmp_path,monkeypatch):
    from ase import Atoms
    from ase.io import write
    from emcd_sim.gui.geometry import Structure,Settings,elastic_model,preview
    from emcd_sim.gui.emcd_forward import material_reason
    monkeypatch.setenv(TABLE_ENVIRONMENT,table.source_path)
    atoms=Atoms('CsCl',scaled_positions=[[0,0,0],[.5,.5,.5]],cell=np.eye(3)*4.1,pbc=True)
    path=tmp_path/'cscl.cif';write(path,atoms)
    s=Structure.from_cif(path)
    assert not s.elastic_reason
    settings=Settings(zone=(0,0,1),target=(1,0,0),tilt=(0.,0.),beam_cutoff=.55,potential_cutoff=.55,thickness=1.,elastic_provider='legacy-atomicscatfact-neutral-v1')
    model=elastic_model(s,settings)
    assert (1,0,0) in model.beams.hkl
    result=preview(s,settings)
    assert result['elastic_provider']['source_sha256']==table.source_sha256
    assert material_reason(s)
    # Same cell and positions as Ni but different atoms must STILL fail MDFF.
    impostor=Structure.nickel();impostor.atoms.set_chemical_symbols(['Cu']*4)
    assert not impostor.elastic_reason and material_reason(impostor)
    assert not material_reason(Structure.nickel())
    for occupancy in [{'Cs':.5},{'Cs':.5,'Cl':.5},{'Cs':float('nan')}]:
        s.atoms.info['occupancy']={'0':occupancy}
        assert s.elastic_reason


def test_configured_desktop_elastic_button_and_missing_file_gate(table,tmp_path,monkeypatch):
    monkeypatch.setenv('QT_QPA_PLATFORM','offscreen')
    pytest.importorskip('PySide6')
    from PySide6 import QtWidgets
    from emcd_sim.gui.app import MainWindow
    from emcd_sim.gui.geometry import Structure
    from emcd_sim.gui.emcd_forward import material_reason
    monkeypatch.setenv(TABLE_ENVIRONMENT,table.source_path)
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window=MainWindow(workspace=tmp_path/'desktop')
    try:
        window.elastic_provider_box.setCurrentIndex(window.elastic_provider_box.findData('legacy-atomicscatfact-neutral-v1'))
        window.set_values(dict(beam=2.2,potential=2.2))
        window.structure=Structure.nickel()
        window.structure.atoms.set_chemical_symbols(['Cu']*4)
        window.refresh()
        assert window.run_button.isEnabled()
        assert material_reason(window.structure)
        monkeypatch.setenv(TABLE_ENVIRONMENT,str(tmp_path/'missing.py'))
        window.refresh()
        assert not window.run_button.isEnabled()
        assert TABLE_ENVIRONMENT in window.structure_label.text()
        window.structure=Structure.nickel();window.refresh()
        window.elastic_provider_box.setCurrentIndex(window.elastic_provider_box.findData('nickel-lobato-2014'))
        assert window.run_button.isEnabled() and not material_reason(window.structure)
    finally:
        window.close();app.processEvents()
