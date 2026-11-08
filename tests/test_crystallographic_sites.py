"""Structural grouping and GUI drafts; no diffraction or spectra calculated."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import numpy as np
import pytest
from ase import Atoms
from ase.build import bulk
from ase.io import write
from PySide6 import QtWidgets

from emcd_sim.crystallographic_sites import crystallographic_sites
from emcd_sim.gui.geometry import Structure, Settings
from emcd_sim.gui.structure_viewer import CrystalStructureDialog
from emcd_sim.gui.site_group_editor import validate_site_rows
from emcd_sim.gui.project_session import capture_configuration, restore_configuration
from emcd_sim.gui.project_io import save_configuration, load_configuration
from emcd_sim.gui.app import MainWindow
from emcd_sim.multisite import IonizationSiteGroup, MultiSiteIonization
from test_group_mdff import source
from emcd_sim.gui.generalized_forward import settings_for_source


CIF=Path(__file__).parent/'fixtures/Fe3O4_inverse_spinel.cif'


@pytest.fixture(scope='module')
def app():return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_spinel_import_and_independent_coordination():
    structure=Structure.from_cif(CIF);a=structure.atoms;original=a.copy()
    p=a.info['crystallographic_sites']
    assert p['status']=='ready' and p['spacegroup_number']==227 and p['setting']=='2'
    assert [(g['group_id'],g['atom_count'],g['wyckoff']) for g in p['groups']]==[
        ('Fe(A)',8,'8a'),('Fe(B)',16,'16d'),('O',32,'32e')]
    oxygen=np.flatnonzero(a.numbers==8)
    for group,coordination in zip(p['groups'][:2],(4,6)):
        assert all(a[i].symbol=='Fe' for i in group['indices'])
        assert all(np.count_nonzero(a.get_distances(i,oxygen,mic=True)<2.3)==coordination for i in group['indices'])
    assert [g['cif_label'] for g in p['groups']]==['FeA','FeB','O1']
    assert a==original


def test_permuted_input_indices_and_repeated_cell():
    a=Structure.from_cif(CIF).atoms
    shuffled=a[np.random.default_rng(91).permutation(len(a))]
    groups=crystallographic_sites(shuffled)['groups']
    oxygen=np.flatnonzero(shuffled.numbers==8)
    tetra=next(g for g in groups if g['wyckoff']=='8a')
    assert all(np.count_nonzero(shuffled.get_distances(i,oxygen,mic=True)<2.3)==4 for i in tetra['indices'])
    assert sorted(i for g in groups for i in g['indices'])==list(range(56))
    repeated=crystallographic_sites(a.repeat((2,1,1)))
    assert sorted((g['atom_count'],g['wyckoff']) for g in repeated['groups'])==[(16,'8a'),(32,'16d'),(64,'32e')]


@pytest.mark.parametrize('symbol,lattice,count',[('Ni','fcc',4),('Fe','bcc',2)])
def test_single_site_and_unchanged_positions(symbol,lattice,count,tmp_path):
    a=bulk(symbol,lattice,cubic=True);original=a.copy()
    from ase.spacegroup import Spacegroup
    a.info['spacegroup']=Spacegroup(225 if symbol=='Ni' else 229)
    p=crystallographic_sites(a)
    assert len(p['groups'])==1 and p['groups'][0]['indices']==list(range(count))
    assert not p['warnings']
    assert a==original
    assert not any('magnet' in key for key in p['groups'][0])
    cif=tmp_path/(symbol+'.cif')
    number=225 if symbol=='Ni' else 229
    cif.write_text(f'''data_single_site
_cell_length_a 3.524
_cell_length_b 3.524
_cell_length_c 3.524
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma 90
_space_group_IT_number {number}
loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
{symbol}1 {symbol} 0 0 0
''',encoding='utf-8')
    imported=Structure.from_cif(cif).atoms.info['crystallographic_sites']
    assert imported['spacegroup_number']==number and imported['setting']==''
    assert not imported['warnings']
    assert imported['groups'][0]['atom_count']==count


def test_low_symmetry_same_element_orbits_are_not_merged():
    a=Atoms('Fe3O',scaled_positions=[[.013,.127,.293],[.213,.389,.417],[.631,.719,.839],[.359,.043,.681]],
            cell=[[4.1,0,0],[.7,5.2,0],[.3,.9,6.3]],pbc=True)
    p=crystallographic_sites(a)
    assert p['spacegroup_number']==1
    assert len(p['groups'])==4
    assert len([g for g in p['groups'] if g['element']=='Fe'])==3


def test_distortion_vacancy_partial_occupancy_and_invalid_labels():
    a=bulk('Ni','fcc',cubic=True);a.positions[0]+=[.013,.021,.039]
    assert len(crystallographic_sites(a)['groups'])>1
    a=bulk('Ni','fcc',cubic=True);del a[1]
    assert sum(g['atom_count'] for g in crystallographic_sites(a)['groups'])==3
    a.info['occupancy']={'0':{'Ni':.5}}
    p=crystallographic_sites(a)
    assert p['status']=='manual' and p['groups']==[] and p['warnings']
    a=Structure.from_cif(CIF).atoms;a.info['_atom_site_type_symbol']=['Ni','Fe','O']
    p=crystallographic_sites(a)
    assert any('labels' in w for w in p['warnings'])
    assert not p['groups'][0]['cif_labels']


def test_auto_group_direction_drafts_and_manual_preservation(app):
    structure=Structure.from_cif(CIF);v=CrystalStructureDialog();v.set_structure(structure)
    e=v.editor
    try:
        assert [len(r[2]) for r in e.rows()]==[8,16,32]
        assert all(r[3] is None and r[4] is None for r in e.rows())
        assert e.magnetization_mode=='global' and e.accepted_site_groups is None
        assert not v.view.scene.directions.any()
        v.inspect_atom(int(np.flatnonzero(v.view.scene.indices==e.rows()[0][2][0])[0]))
        assert 'Unconfigured crystallographic draft' in v.atom_info.toPlainText()
        e.mode.setCurrentIndex(1);e.groups.setCurrentItem(e.groups.topLevelItem(0))
        assert e.selected_indices()==()
        e.direction.setText('1 0 0');e.update_direction()
        np.testing.assert_equal(v.view.scene.directions[np.isin(v.view.scene.indices,e.rows()[0][2])],np.tile([1,0,0],(8,1)))
        assert e.rows()[1][3] is None
        assert '8 atoms' in e.group_summary.text()
        e.apply();v.close();v.set_structure(structure,force=True)
        assert e.rows()[0][3]==(1.,0.,0.)
        e.name.setText('My manual name');e.rename_group();e.apply()
        before=e.rows();e.suggest_crystallographic_groups(structure.atoms.info['crystallographic_sites'])
        assert e.rows()==before
        e.direction.setText('0 1 0');e.update_direction();e.cancel()
        assert e.rows()==before
        while e.rows():e.delete_group()
        e.apply();v.close();v.set_structure(structure,force=True)
        assert e.rows()==()  # An accepted deletion is not undone by reopening.
    finally:v.close()


def test_gui_cif_import_and_configuration_roundtrip(app,tmp_path,monkeypatch):
    monkeypatch.setattr(QtWidgets.QFileDialog,'getOpenFileName',lambda *a,**k:(str(CIF),'cif'))
    w=MainWindow(tmp_path/'workspace');w.inspect_structure=lambda:None
    try:
        w.load_cif();e=w.structure_viewer.editor
        assert [r[0] for r in e.rows()]==['Fe(A)','Fe(B)','O']
        assert w.magnetization_mode=='global' and w.axis.isEnabled()
        state=capture_configuration(w)
        loaded=load_configuration(save_configuration(state,tmp_path/'project'))
        assert loaded['group_records']==state['group_records']
        assert loaded['metadata']['crystallographic_sites']==e.crystallographic_provenance
        restore_configuration(w,loaded)
        assert [len(r[2]) for r in e.rows()]==[8,16,32]
        assert all(r[3] is None for r in e.rows())
        assert e.groups.topLevelItem(0).text(5)=='8a'
        assert e.crystallographic_provenance['symprec_angstrom']==1e-5
        assert w.structure.atoms.info['crystallographic_sites']['setting']=='2'
        while e.rows():e.delete_group()
        e.apply()
        deleted=capture_configuration(w)
        reopened=load_configuration(save_configuration(deleted,tmp_path/'deleted-project'))
        restore_configuration(w,reopened)
        w.show_structure_viewer()
        assert e.rows()==() and reopened['group_records']==[]
        assert e.crystallographic_provenance==loaded['metadata']['crystallographic_sites']
    finally:w.project_dirty=False;w.structure_viewer.close();w.close()


@pytest.mark.parametrize('defect',['direction','frame'])
def test_invalid_mdff_apply_preserves_accepted_model(app,tmp_path,defect):
    a=bulk('Fe','bcc',cubic=True);v=CrystalStructureDialog();v.set_structure(a)
    ref=settings_for_source(source(tmp_path,'valid'))
    initial=MultiSiteIonization(a,[IonizationSiteGroup('Fe','Fe',(0,1),ref,(0,0,1),2)])
    v.set_site_groups(initial);e=v.editor;e.mode.setCurrentIndex(1);e.apply()
    try:
        if defect=='direction':e.direction.setText('1 0 0');e.update_direction()
        else:
            with pytest.raises(ValueError,match='frame_to_crystal'):
                e.set_mdff_reference('Fe',settings_for_source(source(tmp_path,'bad',defect='frame')))
        if defect=='direction':
            with pytest.raises(ValueError):e.apply()
        assert e.accepted_site_groups is initial or e.accepted_site_groups.groups==initial.groups
        e.cancel();assert e.rows()[0][3]==(0,0,1)
    finally:v.close()


def test_missing_direction_cannot_become_executable(tmp_path):
    a=bulk('Fe','bcc',cubic=True)
    assert validate_site_rows(a,[('Fe','Fe',(0,1),None,None)]) is None
    with pytest.raises(ValueError,match='direction'):
        validate_site_rows(a,[('Fe','Fe',(0,1),None,settings_for_source(source(tmp_path)))])
