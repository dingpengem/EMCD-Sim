"""Final review guards; no new diffraction model or geometry prescription."""
from dataclasses import replace
import numpy as np
import pytest
from ase import Atoms
from emcd_sim.gui.geometry import Structure,Settings,geometry,elastic_model
from emcd_sim.gui.emcd_forward import ForwardSettings
from emcd_sim.gui.propagation import numerical_info
from emcd_sim.multislice_double_channeling import ProjectedFFT,incident_fields,multislice_double_channeling_response

@pytest.fixture
def prepared():
    settings=Settings(zone=(0,0,1),target=(2,0,0),voltage=200,thickness=.5,beam_cutoff=.9,potential_cutoff=1.8)
    model=elastic_model(Structure.nickel(),settings)
    grid=ProjectedFFT.build(model,grid_points=24,potential_cutoff=1.8)
    fields=incident_fields(grid,.5,depth_steps=5,slice_step_nm=.04)
    return settings,model,grid,fields

def call(model,grid,fields):
    return multislice_double_channeling_response(model,831.271,np.array([[.2,.2]]),.5,
        prepared_grid=grid,prepared_incoming=fields,depth_steps=5)

@pytest.mark.parametrize('changes',[dict(voltage=300),dict(tilt=(.1,.2))])
def test_cached_grid_cannot_mix_microscope_context(prepared,changes):
    s,model,grid,fields=prepared
    changed=elastic_model(Structure.nickel(),replace(s,**changes))
    with pytest.raises(ValueError,match='microscope energy/incident tilt'):call(changed,grid,fields)

def test_cached_grid_reciprocal_mapping_is_checked(prepared):
    s,model,grid,fields=prepared
    bad=replace(grid,g=grid.g.copy());bad.g[bad.indices(((2,0,0),))[0],1]+=.1
    with pytest.raises(ValueError,match='reciprocal coordinates'):call(model,bad,fields)

@pytest.mark.parametrize('which',['weights','interval'])
def test_cached_depth_quadrature_is_checked(prepared,which):
    s,model,grid,fields=prepared;bad=list(fields)
    if which=='weights':bad[2]=2*bad[2]
    else:bad[4]=bad[4]/2
    with pytest.raises(ValueError,match='quadrature weights|physical depth intervals'):call(model,grid,bad)

def test_large_cell_search_rejects_before_integer_overflow():
    # Previously int64 product overflowed negative and bypassed the work cap.
    huge=Structure(Atoms('Ni',cell=np.eye(3)*1e7,scaled_positions=[[0,0,0]],pbc=True))
    with pytest.raises(ValueError,match='search too large'):
        geometry(huge,Settings(zone=(0,0,1),target=(2,0,0)))

@pytest.mark.parametrize('solver',['bloch','fft-multislice','both'])
@pytest.mark.parametrize('zone',[(1,1,1),(2,2,2)])
def test_111_uncertified_scope_is_visible_for_every_solver(solver,zone):
    s=Settings(zone=zone,target=(2,-2,0),thickness=2,voltage=200,beam_cutoff=2.6,potential_cutoff=3.0)
    c=ForwardSettings(propagation=solver,channeling_model='double',grid=97)
    info=numerical_info(Structure.nickel(),s,c,check_memory=False)
    assert any('0.1094%' in w and 'not certified' in w and 'Beam/potential support' in w for w in info['numerical_warnings'])
    assert info['bw_beams']==37


def test_live_diffraction_preview_labels_ideal_basis_without_solver(tmp_path,monkeypatch):
    from PySide6 import QtWidgets
    from emcd_sim.gui.app import MainWindow
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    w=MainWindow(workspace=tmp_path/'workspace')
    try:
        def forbidden(*a,**k):raise AssertionError('Label change must not run propagation')
        monkeypatch.setattr('emcd_sim.gui.app.preview',forbidden)
        w.numerical_mode.setCurrentIndex(1);w.basis_mode.setCurrentIndex(1);w.refresh()
        assert 'Included beams: 2 (explicit ideal 000 + target two-beam basis)' in w.info.toPlainText()
        assert 'Included beams: 2 (full radial' not in w.info.toPlainText()
        assert w.last_result is None
    finally:w.close();app.processEvents()
