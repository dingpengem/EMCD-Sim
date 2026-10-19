"""Focused memory admission and sequential scan cleanup; no large allocations."""
from dataclasses import replace
from unittest.mock import patch
import gc
import importlib.util
from pathlib import Path
import weakref

import numpy as np
import pytest
from emcd_sim.gui import memory_budget as memory
from emcd_sim.gui.emcd_forward import ForwardSettings
from emcd_sim.gui.geometry import Settings, Structure
from emcd_sim.gui.propagation import numerical_info
from emcd_sim.gui.project_io import config_from_dict

SNAPSHOT = dict(available_ram_mib=32768., process_rss_mib=64.)


@pytest.mark.parametrize('budget', memory.BUDGETS_MIB)
def test_supported_budgets_and_512_compatibility(budget):
    info = memory.assess_memory(100., budget, dense_mib=50., snapshot=SNAPSHOT)
    assert info['memory_budget_mib'] == budget
    assert info['estimated_process_peak_mib'] == 317.


def test_larger_dense_kernel_admitted_only_with_larger_budget():
    cfg = ForwardSettings(propagation='bloch',grid=33)
    assert cfg.memory_budget_mib == config_from_dict({}).memory_budget_mib == 2048
    with patch.object(memory, 'memory_snapshot', return_value=SNAPSHOT):
        info = numerical_info(Structure.nickel(), Settings(), cfg, hkl=tuple(range(100)))
        assert info['dense_working_estimate_mib'] > 512
        assert info['estimated_process_peak_mib'] > info['estimated_working_mib']
        assert info['estimated_working_mib'] > info['dense_working_estimate_mib']
        with pytest.raises(ValueError, match='selected budget 512 MiB'):
            numerical_info(Structure.nickel(), Settings(), replace(cfg, memory_budget_mib=512), hkl=tuple(range(100)))


def test_available_ram_and_invalid_measurement_fail_closed():
    with pytest.raises(ValueError, match='50% of currently available RAM'):
        memory.assess_memory(800, 8192, snapshot=dict(available_ram_mib=1000, process_rss_mib=64))
    with patch.object(memory, 'memory_snapshot', side_effect=OSError('unavailable')):
        with pytest.raises(ValueError, match='Cannot verify'):
            memory.assess_memory(1)
    with pytest.raises(ValueError, match='budget must be'):
        memory.assess_memory(1, 3072, snapshot=SNAPSHOT)


def test_concurrent_reservations_and_cleanup_on_errors():
    with patch.object(memory, 'memory_snapshot', return_value=SNAPSHOT):
        with memory.reserve_memory(200):
            assert memory.assess_memory(10)['concurrent_calculations'] == 1
            with pytest.raises(ValueError, match='1 active calculation'):
                with memory.reserve_memory(300, 512):
                    pytest.fail('Concurrent excess must be rejected')
        assert memory.assess_memory(10)['concurrent_calculations'] == 0
        for failure in (RuntimeError('cancel'), MemoryError('allocation')):
            with pytest.raises((RuntimeError, ValueError)):
                with memory.reserve_memory(100):
                    raise failure
            assert memory.assess_memory(10)['concurrent_calculations'] == 0


def test_scan_checkpoint_keeps_no_wavefields_or_coherences(tmp_path):
    spec = importlib.util.spec_from_file_location('thickness_study', Path(__file__).resolve().parents[1]/'scripts/ni_017_thickness_scan.py')
    study = importlib.util.module_from_spec(spec); spec.loader.exec_module(study)
    (tmp_path/'checkpoints').mkdir()
    case = {m: dict(raw=np.full((2, 4), .55), amplitudes=np.ones((64, 27), complex),
        coherence=np.eye(27, dtype=complex), actual_thickness_nm=2.) for m in study.METHODS}
    refs = [weakref.ref(v) for d in case.values() for v in d.values() if isinstance(v, np.ndarray)]
    compact = study.checkpoint_case(tmp_path, 2., case, {})
    del case
    gc.collect()
    assert all(ref() is None for ref in refs)
    for d in compact.values():
        assert 'amplitudes' not in d and 'coherence' not in d
        assert d['raw'].dtype == np.float64
        np.testing.assert_array_equal(d['raw'], np.full((2, 4), .55))
    with np.load(tmp_path/'checkpoints/t002.npz', allow_pickle=False) as saved:
        assert not any('amplitudes' in k or 'coherence' in k for k in saved.files)


def test_real_system_memory_measurement():
    state = memory.memory_snapshot()
    assert state['available_ram_mib'] > 0 and state['process_rss_mib'] > 0


def test_gui_budget_selector_and_start_admission(tmp_path, monkeypatch):
    monkeypatch.setenv('QT_QPA_PLATFORM', 'offscreen')
    from PySide6 import QtWidgets
    from emcd_sim.gui.app import MainWindow
    from emcd_sim.gui.emcd_forward import calculate
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    with patch.object(memory, 'memory_snapshot', return_value=SNAPSHOT):
        w = MainWindow(workspace=tmp_path/'workspace')
        assert w.memory_budget.currentData() == 2048
        for i, budget in enumerate(memory.BUDGETS_MIB):
            w.memory_budget.setCurrentIndex(i)
            assert w.forward_settings().memory_budget_mib == budget
        w.close()
    # A RAM change after UI preview is checked again at calculation entry.
    with patch.object(memory, 'memory_snapshot', return_value=dict(available_ram_mib=100, process_rss_mib=64)):
        with patch('emcd_sim.gui.emcd_forward._calculate') as engine:
            with pytest.raises(ValueError, match='currently available RAM'):
                calculate(Structure.nickel(), Settings(), ForwardSettings())
            engine.assert_not_called()
