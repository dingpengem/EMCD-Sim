"""Nested real samples, detector quadrature, NaNs and strict source recovery."""
import importlib.util,sys
from pathlib import Path
import hashlib
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
import angular_map_convergence as maps
import audit_historical_ms_source as historical


def test_exact_historical_hash_recovery():
    assert hashlib.sha256(historical.recovered_source()).hexdigest()==historical.EXPECTED
    assert not historical.legacy_hash_compatible('src/emcd_sim/multislice_double_channeling.py','incorrect')
    assert not historical.legacy_hash_compatible('src/emcd_sim/geometry.py',historical.EXPECTED)


def test_real_physics_source_drift_is_rejected(monkeypatch):
    original=Path.read_bytes
    def changed(path):
        value=original(path)
        if path.as_posix()==historical.PATH:
            value=value.replace(b'qz=-characteristic_qz_angstrom_inv',b'qz=characteristic_qz_angstrom_inv')
        return value
    monkeypatch.setattr(Path,'read_bytes',changed)
    with pytest.raises(AssertionError,match='Default numerical path changed'):
        historical.legacy_hash_compatible(historical.PATH,historical.EXPECTED)


def test_mirror_fields_zero_and_invalid_denominator():
    q=np.linspace(-.5,.5,33);x,y=np.meshgrid(q,q)
    plus=1+.2*y;minus=1-.2*y
    f=maps.fields(plus,minus)
    np.testing.assert_allclose(f['D_mag'],.4*y,atol=1e-15)
    np.testing.assert_array_equal(f['D_nonmag'],0)
    np.testing.assert_allclose(f['asymmetry'],-f['asymmetry'][::-1],atol=1e-14)
    assert np.isnan(maps.fields(plus*0,minus*0)['asymmetry']).all()


def test_partial_atomic_chunks_do_not_restart_completed_directions():
    import uuid
    folder=maps.ROOT/('test_atomic_'+uuid.uuid4().hex);folder.mkdir(parents=True)
    try:
        np.savez_compressed(folder/'chunk_0000.npz',indices=np.array([2]),response=np.ones((1,3,3),complex),seconds=1.,signature=np.array('known'))
        (folder/'chunk_0001.temporary.npz').write_bytes(b'incomplete')
        cache,seconds=maps.cache_read(folder,'known')
        assert list(cache)==[2] and seconds==1.
        with pytest.raises(AssertionError):maps.cache_read(folder,'different')
    finally:
        for path in folder.iterdir():path.unlink()
        folder.rmdir()


def test_actual_nested_maps_and_detector_intensity_integration():
    available=[(m,n) for m in ('bw','ms') for n in (33,97,193) if (maps.ROOT/f'{m}_{n}.npz').exists()]
    if not available:pytest.skip('Optional convergence outputs not yet available')
    import json
    for method,n in available:
        with np.load(maps.ROOT/f'{method}_{n}.npz',allow_pickle=False) as f:
            assert f['I_plus'].shape==(n,n) and f['I_plus'].dtype==np.float64
            np.testing.assert_array_equal(f['qy'],-f['qy'][::-1])
            d=json.loads(str(f['detector_json']))
            np.testing.assert_allclose(d['A_raw'],100*(d['I_A_plus']-d['I_B_plus'])/(d['I_A_plus']+d['I_B_plus']),rtol=1e-14)
            np.testing.assert_allclose(d['D_mag']+d['D_nonmag'],d['I_A_plus']-d['I_B_plus'],atol=1e-15)
            if n==193:
                with np.load(maps.ROOT/f'{method}_97.npz',allow_pickle=False) as low:
                    np.testing.assert_array_equal(low['I_plus'],f['I_plus'][::2,::2])
