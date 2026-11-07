import time
import numpy as np
from ase.build import bulk
from PySide6 import QtWidgets
from emcd_sim.gui.app import MainWindow
from emcd_sim.gui.geometry import Structure
from emcd_sim.gui.project_io import save_project,load_project
from single_element_helpers import write_source


def test_imported_gui_worker_restore_and_missing_source(tmp_path,monkeypatch):
    monkeypatch.setenv('EMCD_GUI_WORKSPACE',str(tmp_path/'workspace'))
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    w=MainWindow();errors=[];w.error=errors.append
    try:
        w.numerical_mode.setCurrentIndex(1)
        w.structure=Structure(bulk('Fe','bcc',a=2.866,cubic=True),'Synthetic BCC Fe')
        w.zone.setText('0 0 1');w.target.setText('1 1 0')
        w.set_values(dict(kv=200,tx=-5,ty=7,thickness=.2,beam=.6,potential=1.2,grid=9,depth=9,subpixels=8,halfwidth=.7,radius=.12))
        w.model_box.setCurrentIndex(2);w.manual_model.setCurrentIndex(0);w.constant_input_mode.setCurrentIndex(1)
        assert not w.emcd_button.isEnabled()
        p=write_source(tmp_path/'tensor.json');w.imported_path.setText(str(p));w.validate_imported_mdff()
        assert w.imported_info is not None and not w.emcd_button.isEnabled()
        w.imported_declaration.setChecked(True);w.energy_scope.setCurrentIndex(1);w.angular_maps.setChecked(True)
        w.detectors=np.array([[.2,.2],[.2,-.2]]);w.sync_detectors();w.correction.setChecked(False);w.refresh();w.emcd_stale()
        assert w.emcd_button.isEnabled(),w.emcd_button.toolTip()
        assert w.forward_settings().ionizing_element=='Fe'
        w.start_emcd();limit=time.monotonic()+90
        while w.busy and time.monotonic()<limit:app.processEvents();time.sleep(.01)
        assert not w.busy and not errors,errors
        assert w.emcd_result['metadata']['scientific_status']=='SYNTHETIC TEST ONLY'
        save_project(w.emcd_result,tmp_path/'project');w.emcd_result=load_project(tmp_path/'project');w.use_result_settings()
        assert not errors and w.model_box.currentIndex()==2 and w.forward_settings().ionizing_element=='Fe'
        np.testing.assert_array_equal(w.emcd_result['spectra']['energy_ev'],[710,723])
        p.unlink();w.emcd_result=load_project(tmp_path/'project');w.use_result_settings();w.emcd_stale()
        assert not w.emcd_button.isEnabled() and w.imported_info is None
        assert w.emcd_result['spectra']['I_A_plus'].size==2
        # Selecting a Ni provider must reapply its original conservative eligibility gate.
        from emcd_sim.gui.emcd_forward import DEFAULT_SOURCE
        w.model_box.setCurrentIndex(0);w.source_path.setText(str(DEFAULT_SOURCE));w.validate_xmcd(show_error=False)
        w.emcd_stale();assert not w.emcd_button.isEnabled()
        assert 'Ni' in w.emcd_button.toolTip()
    finally:
        if w.busy:w.cancel();w.worker.wait(15000)
        for dialog in w.dialogs:dialog.close()
        w.close();app.processEvents()
