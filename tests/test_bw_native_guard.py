"""Windows BW executor isolation without changing process-wide BLAS settings."""
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import threading,time
import pytest
from emcd_sim.gui import channeling
from emcd_sim.cancellation import Cancelled


def test_worker_policy_only_changes_windows_bw(monkeypatch):
    monkeypatch.setattr(channeling,'sys',SimpleNamespace(platform='win32'))
    for n in (21,27,51):
        assert channeling.worker_count(n,'bloch')==1
        assert channeling.worker_count(n,'fft-multislice')==4
    monkeypatch.setattr(channeling,'sys',SimpleNamespace(platform='linux'))
    assert channeling.worker_count(27,'bloch')==4


def test_independent_windows_bw_executors_never_overlap(monkeypatch):
    monkeypatch.setattr(channeling,'sys',SimpleNamespace(platform='win32'))
    active=0;peak=0;barrier=threading.Barrier(4)
    def work(_):
        nonlocal active,peak
        barrier.wait()
        with channeling.bw_executor_guard('bloch',lambda:False):
            active+=1;peak=max(active,peak);time.sleep(.01);active-=1
    with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(work,range(4)))
    assert peak==1 and not channeling._windows_bw_lock.locked()


def test_waiting_cancel_does_not_release_other_owner(monkeypatch):
    monkeypatch.setattr(channeling,'sys',SimpleNamespace(platform='win32'))
    channeling._windows_bw_lock.acquire()
    try:
        with pytest.raises(Cancelled):
            with channeling.bw_executor_guard('bloch',lambda:True):pytest.fail('Cancelled request entered')
        assert channeling._windows_bw_lock.locked()
        with channeling.bw_executor_guard('fft-multislice',lambda:False):pass
    finally:channeling._windows_bw_lock.release()


def test_guard_releases_on_error_and_early_cancel(monkeypatch):
    monkeypatch.setattr(channeling,'sys',SimpleNamespace(platform='win32'))
    with pytest.raises(ValueError):
        with channeling.bw_executor_guard('bloch',lambda:False):raise ValueError('native wrapper error')
    with pytest.raises(Cancelled):
        with channeling.bw_executor_guard('bloch',lambda:True):pass
    assert not channeling._windows_bw_lock.locked()


def test_gui_resource_rejection_remains_responsive(tmp_path,monkeypatch):
    from unittest.mock import Mock
    from PySide6 import QtCore,QtWidgets
    from emcd_sim.gui.app import MainWindow
    import emcd_sim.gui.propagation as propagation
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window=MainWindow(workspace=tmp_path/'workspace')
    try:
        window.model_box.setCurrentIndex(1);window.numerical_mode.setCurrentIndex(1)
        window.spin['beam'].setValue(3.)
        before=window.numerical_snapshot();errors=[];window.error=errors.append
        factory=Mock();monkeypatch.setattr('emcd_sim.gui.stage_b.EMCDWorker',factory)
        def reject(*args,**kwargs):raise ValueError('Memory admission rejected: selected budget 2048 MiB')
        monkeypatch.setattr(propagation,'numerical_info',reject)
        window.start_emcd()
        assert errors and '2048 MiB' in errors[-1] and not factory.called
        assert not window.busy and window.inputs.isEnabled() and window.numerical_snapshot()==before
        ticks=[];QtCore.QTimer.singleShot(0,lambda:ticks.append(True));app.processEvents()
        assert ticks
    finally:window.close();app.processEvents()


def test_worker_logs_inputs_and_last_stage_without_changing_results(monkeypatch,caplog):
    import logging
    from dataclasses import replace
    from emcd_sim.gui.stage_b import EMCDWorker
    from emcd_sim.gui.geometry import Structure,Settings
    from emcd_sim.gui.emcd_forward import ForwardSettings
    expected=object()
    def calculate(structure,settings,cfg,progress,cancelled):
        progress('outgoing eigenproblem diagnostic');return expected
    monkeypatch.setattr('emcd_sim.gui.stage_b.calculate',calculate)
    worker=EMCDWorker(Structure.nickel(),replace(Settings(),beam_cutoff=3.),ForwardSettings(source='C:/private/user_sample.xmcd'))
    result=[];worker.result.connect(result.append)
    with caplog.at_level(logging.INFO,logger='emcd_sim.gui'):worker.run()
    assert result==[expected]
    assert any("'beam_cutoff': 3.0" in line for line in caplog.messages)
    assert 'Calculation stage: outgoing eigenproblem diagnostic' in caplog.messages
    assert 'C:/private/user_sample.xmcd' not in '\n'.join(caplog.messages)
