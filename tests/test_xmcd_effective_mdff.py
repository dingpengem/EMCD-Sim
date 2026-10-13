import numpy as np
import pytest
from emcd_sim.xmcd_effective_mdff import effective_tensor_from_xmcd

def test_tensor_from_xmcd(tmp_path):
    f = tmp_path / "Ni.xmcd"
    a = np.array([[850., 3., 1., 2., 4.],
                  [851., 4., 2., 2., 6.],
                  [852., 2., 2., 0., 4.]])
    np.savetxt(f, a)
    tensor = effective_tensor_from_xmcd(f)
    t = tensor.tensor_angstrom2_per_ev
    assert np.allclose(t, t.swapaxes(1, 2).conj())
    assert np.linalg.eigvalsh(t).min() >= -1e-12
    assert np.allclose(effective_tensor_from_xmcd(f, eta=0).tensor_angstrom2_per_ev[:,0,1], 0)
    assert np.allclose(effective_tensor_from_xmcd(f, eta=-1).tensor_angstrom2_per_ev[:,0,1], -t[:,0,1])
    with pytest.raises(ValueError):
        effective_tensor_from_xmcd(f, eta=5)
    with pytest.raises(ValueError):
        effective_tensor_from_xmcd(f, energy_ev=np.array([849.,850.]))
