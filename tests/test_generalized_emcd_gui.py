"""Normal Qt controls/workers, saved geometry and raw/relative result views."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from time import monotonic,sleep
import json,uuid
import numpy as np
import pytest
from PySide6 import QtWidgets
from emcd_sim.gui.app import MainWindow
from emcd_sim.gui.geometry import excitation
from emcd_sim.gui.project_io import save_project,load_project,fingerprints,frame_rerun_reason

CASES=[('001',(0,0,1),(2,0,0),1.8,2.2,True),
    ('017',(0,1,7),(2,0,0),2.2,2.2,False),
    ('117',(1,1,7),(2,-2,0),3.2,3.8,False),
    ('111',(1,1,1),(2,-2,0),1.8,2.2,False),
    ('710',(7,1,0),(0,0,2),2.2,2.2,False)]

@pytest.mark.parametrize('case',CASES,ids=[c[0] for c in CASES])
@pytest.mark.parametrize('channel',[0,1],ids=['single','double'])
def test_normal_gui_end_to_end(case,channel):
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    label,zone,target,beam,potential,row=case
    root=Path('outputs/generalized_multislice_emcd_validation/gui')/(label+('_double_' if channel else '_single_')+uuid.uuid4().hex)
    root.mkdir(parents=True)
    w=MainWindow(workspace=root/'workspace');errors=[];w.error=errors.append
    try:
        w.numerical_mode.setCurrentIndex(1)
        w.zone.setText(' '.join(map(str,zone)));w.target.setText(' '.join(map(str,target)))
        w.set_values(dict(kv=200,thickness=.5,tx=0,ty=0,beam=beam,potential=potential,
            grid=9,depth=9,subpixels=16,fft_grid=24,slice_step=.02,energy=9,
            window_lo=866,window_hi=882.521))
        w.row_projection.setChecked(row);w.apply_orientation();w.lock.setCurrentText('Y');w.align();w.restore_detectors()
        s=w.settings();g=w.current[3][w.current[2].index(target)]
        assert abs(float(excitation(g,s.tilt,s.voltage)))<1e-10
        assert np.allclose(g[1],0,atol=1e-13) and g[0]>0
        np.testing.assert_allclose(w.detectors,[[g[0]/2,g[0]/2],[g[0]/2,-g[0]/2]],atol=1e-12)
        w.set_values(dict(radius=.16*g[0]));w.channeling_box.setCurrentIndex(channel)
        w.declaration.setChecked(True);w.correction.setChecked(True);w.energy_scope.setCurrentIndex(0)
        w.worker_mode.setCurrentIndex(1);w.worker_count.setValue(1)
        # Both solver-only selections must remain available to normal users.
        for method in (0,1,2):
            w.propagation_box.setCurrentIndex(method);w.emcd_stale()
            assert w.emcd_button.isEnabled(),w.emcd_button.toolTip()
        w.start_preview();deadline=monotonic()+30
        while w.busy and monotonic()<deadline:app.processEvents();sleep(.01)
        assert not w.busy and w.last_result is not None and not errors,errors
        w.start_emcd();deadline=monotonic()+90
        while w.busy and monotonic()<deadline:app.processEvents();sleep(.01)
        assert not w.busy and w.run_outcome=='completed' and not errors,errors
        result=w.emcd_result;before=fingerprints(result)
        assert set(result['methods'])=={'bloch','fft-multislice'}
        assert 'no outgoing channeling' not in w.info.toPlainText()
        assert 'verified [017] FFT' not in w.info.toPlainText()
        for r in result['methods'].values():
            assert len(r['spectra']['energy_ev'])>2 and r['metadata']['alpha'] is not None
            assert r['maps']['L3']['I_plus'].shape==(9,9)
            np.testing.assert_allclose(r['spectra']['D_raw'],r['spectra']['D_mag']+r['spectra']['D_nonmag'],atol=1e-13)
            assert np.linalg.det(np.asarray(r['metadata']['frame']))>0
            assert not any(d['mirror_reuse'] for d in r['metadata']['angular_evaluation'])
        # Render actual normal result views in both display modes; data immutable.
        for view in (w.eels_view,w.maps_view):
            view.component_mode.setCurrentIndex(1);app.processEvents()
            view.component_mode.setCurrentIndex(0);app.processEvents()
        assert fingerprints(result)==before
        project=root/'project';save_project(result,project);saved=load_project(project)
        assert fingerprints(saved)==before and not frame_rerun_reason(saved)
        w.emcd_result=saved;w.use_result_settings()
        assert w.settings()==s and w.forward_settings()==saved['config']
        assert fingerprints(saved)==before
        w.maps_view.figure.savefig(root/'L3_maps.png',dpi=100)
        w.eels_view.figure.savefig(root/'eels.png',dpi=100)
        (root/'acceptance.json').write_text(json.dumps(dict(zone=zone,target=target,channeling=result['config'].channeling_model,
            methods=list(result['methods']),passed=True,qt_platform=app.platformName(),environment='Windows Python/PySide6 source GUI, not packaged EXE or clean machine'),indent=2),encoding='utf-8')
    finally:
        if w.busy:w.cancel();w.worker.wait(15000);app.processEvents()
        w.close();app.processEvents()


def test_ideal_basis_description_is_not_full_multibeam():
    from types import SimpleNamespace
    from emcd_sim.gui.results import geometry_description
    from emcd_sim.gui.geometry import Settings
    from emcd_sim.gui.emcd_forward import ForwardSettings
    from dataclasses import replace
    result=dict(settings=replace(Settings(),basis_mode='two-beam'),config=ForwardSettings())
    assert 'ideal' in geometry_description(result) and 'full finite' not in geometry_description(result)
