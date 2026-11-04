import hashlib,json
import numpy as np
import pytest
from emcd_sim.generalized_xmcd import export_declared_xmcd
from emcd_sim.imported_mdff import CONVENTION
from emcd_sim.atomic_ionization import dipole_2p_to_3d,AtomicMaterialParameters,transitions_for_material
from emcd_sim.ni_local_mdff import ni_2p_to_3d_dipole,NiLocalConfig


def test_declared_element_xmcd_source_without_ni_calibration(tmp_path):
    e=np.linspace(704,730,17);n=.2+np.exp(-((e-710)/2)**2)+.5*np.exp(-((e-723)/2)**2);m=.05*np.exp(-((e-710)/2)**2)
    path=tmp_path/'synthetic_fe.xmcd';np.savetxt(path,np.column_stack([e,n+m,n-m,2*m,2*n]))
    declaration=dict(element='Fe',edge='L2,3',selected_ev=dict(L3=710,L2=723),magnetization_crystal=[1,0,0],
        handedness='RP_minus_LP_in_declared_axis',eta=1.,beta=.8,normalization='source_max_nonmagnetic',convention=CONVENTION,
        source='Original synthetic Fe-labelled XAS/XMCD software fixture',validity='Not measured/DFT; software test only',status='synthetic',
        source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),reference_tensor_scale_angstrom2_per_ev=.3,
        magnetic_state='uniform_fm',reversal_assumption='axisymmetric_XMCD_odd_shared_XAS')
    source=export_declared_xmcd(path,declaration,tmp_path/'tensor.json')
    np.testing.assert_array_equal(source.energy_ev,e)
    assert source.metadata['element']=='Fe' and source.metadata['selected_ev']==dict(L3=710,L2=723)
    assert 'anisotropy' in source.metadata['validity']
    ts=source.tensors([710,723],np.eye(3),[1,0,0]);assert np.linalg.eigvalsh(ts[0].tensor_angstrom2_per_ev).min()>0
    # A z-axis source rotated to crystal x has its chiral yz block, not xy.
    assert abs(ts[0].tensor_angstrom2_per_ev[0,1,2].imag)>0
    assert abs(ts[0].tensor_angstrom2_per_ev[0,0,1].imag)<1e-15
    with pytest.raises(ValueError,match='existing'):export_declared_xmcd(path,declaration,tmp_path/'tensor.json')
    for key in ('element','selected_ev','source_sha256','reference_tensor_scale_angstrom2_per_ev','reversal_assumption'):
        bad=dict(declaration);bad.pop(key)
        with pytest.raises(ValueError,match='incomplete'):export_declared_xmcd(path,bad,tmp_path/'bad.json')
    bad=dict(declaration,reversal_assumption='conjugate_any_tensor')
    with pytest.raises(ValueError,match='reversal'):export_declared_xmcd(path,bad,tmp_path/'bad.json')


def test_atomic_math_shared_ni_defaults_unchanged_and_non_ni_disabled():
    assert dipole_2p_to_3d is ni_2p_to_3d_dipole
    assert (NiLocalConfig().l3_ev,NiLocalConfig().zeff_2p)==(852.7,25.)
    p=AtomicMaterialParameters('Fe',(710.,723.),.03,(.2,.6),.3,.8,1.,'Hypothetical explicit parameters; NOT validated Fe')
    with pytest.raises(ValueError,match='not implemented/validated'):transitions_for_material(p)
