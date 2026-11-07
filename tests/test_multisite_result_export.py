"""CSV round trips of stored multi-site arrays; no numerical solver calls."""
import csv
import json
import os
import sys
from copy import deepcopy

import numpy as np
import pytest
from PySide6 import QtCore, QtWidgets, QtTest

from emcd_sim.crystal import Crystal
from emcd_sim.gui.emcd_forward import ForwardSettings
from emcd_sim.gui.multisite_export import export_multisite_spectra
from emcd_sim.gui.multisite_results import SPECTRAL_KEYS
from test_multisite_result_selection import app, view, select, stored_result


def export_result(kind='Fe3O4', omit=False):
    result = stored_result(kind,omit)
    crystal = result['model'].elastic.crystal
    result['model'].elastic.crystal = Crystal(np.eye(3)*8.4,
        np.arange(len(crystal.species)*3).reshape(-1,3)/24,crystal.species)
    offset = 0
    for group in result['groups'].values():
        count = group['metadata']['multiplicity']
        group['metadata']['indices'] = tuple(range(offset,offset+count));offset += count
    result['metadata'].update(software_version='test-version',software_commit='stored-calculation-commit',
                              numerics={'beam_count':13,'depth_nodes':9})
    return result


def read(root):
    with (root/'spectra.csv').open(encoding='utf-8',newline='') as stream:rows = list(csv.DictReader(stream))
    return rows,json.loads((root/'metadata.json').read_text(encoding='utf-8'))


@pytest.mark.parametrize('kind',['Fe3O4','FeNi'])
def test_csv_weighted_groups_total_precision_and_metadata(tmp_path,kind):
    result = export_result(kind);before = deepcopy(result['groups'])
    rows,meta = read(export_multisite_spectra(result,tmp_path/'selected',selection=('compare',None),
        compared=tuple(result['groups']),include_total=True,quantity=6))
    n = result['metadata']['multisite']['selected_atom_count']
    for ie,energy in enumerate(result['spectra']['energy_ev']):
        at_energy = [row for row in rows if float(row['energy_ev'])==energy]
        total = next(row for row in at_energy if row['series_kind']=='total')
        for key in SPECTRAL_KEYS:
            assert float(total[key]) == result['spectra'][key][ie]
            parts = [float(row[key]) for row in at_energy if row['series_kind']=='group' and row[key]!='']
            np.testing.assert_allclose(sum(parts),float(total[key]),rtol=1e-14)
        assert int(total['global_denominator']) == n
        for row in at_energy:
            if row['series_kind']!='group':continue
            group = result['groups'][row['series_id']]
            active = result['metadata']['multisite']['channels'][row['series_id']]['active_energy_mask'][ie]
            for key in SPECTRAL_KEYS:
                expected = group['metadata']['multiplicity']/n*group['spectra'][key][ie]
                assert (float(row[key]) == expected) if active else row[key]==''
    assert meta['software_version']=='test-version'
    assert meta['calculation_metadata']['software_commit']=='stored-calculation-commit'
    assert meta['calculation_config']['l3'] is None  # Unset settings are standard JSON null, not NaN.
    assert meta['structure']['species']==list(result['model'].elastic.crystal.species)
    assert meta['series'][0]['global_denominator']==n
    assert meta['selection']['displayed_quantity']=='Magnetic A−B'
    for gid,group in result['groups'].items():
        assert meta['groups'][gid]['source']==group['metadata']['source']
        assert meta['groups'][gid]['indices']==list(group['metadata']['indices'])
        assert meta['groups'][gid]['magnetization_crystal']==list(group['metadata']['magnetization_crystal'])
        for key in SPECTRAL_KEYS:np.testing.assert_array_equal(group['spectra'][key],before[gid]['spectra'][key])


@pytest.mark.parametrize('mode',['mean','weighted','element','total'])
def test_export_modes_preserve_components_and_source_amplitudes(tmp_path,mode):
    result = export_result()
    selection = ('element','Fe') if mode=='element' else ('total',None) if mode=='total' else ('group','Fe(B)')
    rows,meta = read(export_multisite_spectra(result,tmp_path/mode,selection=selection,normalization=mode))
    expected = result['spectra'] if mode in ('element','total') else result['groups']['Fe(B)']['spectra']
    factor = 2/3 if mode=='weighted' else 1.
    for key in SPECTRAL_KEYS:
        np.testing.assert_array_equal([float(row[key]) for row in rows],factor*expected[key])
    for row in rows:
        values = {key:float(row[key]) for key in SPECTRAL_KEYS}
        for detector in ('A','B'):
            assert values['N_'+detector] == pytest.approx((values['I_'+detector+'_plus']+values['I_'+detector+'_minus'])/2)
            assert values['M_'+detector] == pytest.approx((values['I_'+detector+'_plus']-values['I_'+detector+'_minus'])/2)
        assert values['D_raw'] == pytest.approx(values['D_mag']+values['D_nonmag'])
        assert values['D_mag'] != pytest.approx(values['D_raw'])
    assert ('nonadditive' in rows[0]['normalization']) == (mode=='mean')
    assert meta['groups']['Fe(B)']['source']['units']=='angstrom^2/eV'


def test_excluded_and_gap_samples_are_blank_but_calculated_zero_is_numeric(tmp_path):
    result = export_result('FeNi',omit=True)
    # Retain a requested energy between the two disjoint windows, with no modeled channel.
    for spectra in [result['spectra'],*(g['spectra'] for g in result['groups'].values())]:
        for key in ('energy_ev',*SPECTRAL_KEYS):spectra[key] = np.insert(spectra[key],3,780. if key=='energy_ev' else 0.)
        spectra['M_A'][0] = 0.
    for channel in result['metadata']['multisite']['channels'].values():channel['active_energy_mask'].insert(3,False)
    rows,meta = read(export_multisite_spectra(result,tmp_path/'coverage',selection=('compare',None),
        compared=('Fe','Ni'),include_total=True))
    for row in rows:
        if row['series_id']=='Ni':
            assert row['coverage_state']=='excluded' and row['I_A_plus']==''
            assert json.loads(row['excluded_group_ids'])==['Ni']
        if float(row['energy_ev'])==780.:
            assert row['I_A_plus']=='' and row['M_A']==''
            assert row['coverage_state'] in ('unmodeled','excluded')
        if row['series_id']=='Total' and float(row['energy_ev'])==710.:
            assert row['M_A']=='0.0' and row['coverage_state']=='modeled'
            assert json.loads(row['active_group_ids'])==['Fe']
            assert json.loads(row['excluded_group_ids'])==['Ni']
            assert row['global_denominator']=='2'  # Exclusion does not renormalize to Fe alone.
    assert meta['spectrum_kind']=='modeled_partial_core_edge_spectrum'
    assert 'not physical zero' in meta['coverage']['note']


def test_gui_exports_selected_method_comparison_without_recalculation(view,monkeypatch,tmp_path):
    result = export_result();other = deepcopy(result)
    for spectra in [other['spectra'],*(g['spectra'] for g in other['groups'].values())]:
        for key in SPECTRAL_KEYS:spectra[key] *= 2
    result = dict(result,methods={'bloch':result,'fft-multislice':other})
    view.set_result(result);select(view,'compare');view.multisite_controls.include_total.setChecked(True)
    view.multisite_controls.quantity.setCurrentIndex(6);view.method.setCurrentIndex(1)
    assert len(view.figure.axes[0].lines)==3
    monkeypatch.setattr(QtWidgets.QFileDialog,'getExistingDirectory',lambda *a,**k:str(tmp_path))
    view.export_button.click()
    rows,meta = read(next(tmp_path.glob('multisite_*')))
    total = [row for row in rows if row['series_kind']=='total']
    np.testing.assert_array_equal([float(row['D_mag']) for row in total],other['spectra']['D_mag'])
    assert meta['method']=='fft-multislice' and meta['selection']['include_total']
    view.multisite_controls.normalization.setCurrentIndex(1)
    assert 'not additive' in view.multisite_banner.text() and 'Total normalized' in view.multisite_banner.text()
    # A cancelled destination or empty comparison creates no export.
    monkeypatch.setattr(QtWidgets.QFileDialog,'getExistingDirectory',lambda *a,**k:'')
    view.export_button.click();assert len(list(tmp_path.iterdir()))==1


def test_legacy_ni_gui_export_still_routes_to_existing_exporter(view,monkeypatch,tmp_path):
    result = export_result();result['config'] = ForwardSettings(model='atomic',l3=710,l2=723,energy_scope='full',angular_maps=False,correction=False)
    result['model'].elastic.crystal = Crystal(np.eye(3)*3.52,np.zeros((4,3)),('Ni',)*4)
    view.owner.maps_view = type('MapView',(),{'component_mode':view.component_mode})()
    view.set_result(result);calls = []
    monkeypatch.setattr(QtWidgets.QFileDialog,'getExistingDirectory',lambda *a,**k:str(tmp_path))
    monkeypatch.setattr('emcd_sim.gui.emcd_forward.export_result',lambda *args,**kwargs:calls.append((args,kwargs)))
    view.export_button.click()
    assert len(calls)==1 and calls[0][0][0] is result
    assert calls[0][1]['component_mode']==view.component_mode.currentData()
    assert view.export_button.isEnabled() and view.multisite_controls.isHidden()


def test_empty_comparison_does_not_create_folder(tmp_path):
    with pytest.raises(ValueError,match='Select at least one'):
        export_multisite_spectra(export_result(),tmp_path/'empty',selection=('compare',None))
    assert not (tmp_path/'empty').exists()


@pytest.mark.skipif(sys.platform!='win32' or os.environ.get('QT_QPA_PLATFORM')!='windows',reason='Explicit native Windows selection/export check')
def test_native_windows_comparison_csv_export(view,app,monkeypatch,tmp_path):
    assert app.platformName()=='windows'
    view.set_result(export_result());view.window().show();app.processEvents()
    assert QtTest.QTest.qWaitForWindowExposed(view.window().windowHandle(),3000)
    select(view,'group','Fe(B)');view.multisite_controls.normalization.setCurrentIndex(1)
    select(view,'element','Fe');select(view,'compare');view.multisite_controls.normalization.setCurrentIndex(0)
    view.multisite_controls.quantity.setCurrentIndex(6);app.processEvents()
    checkbox = view.multisite_controls.include_total
    QtTest.QTest.mouseClick(checkbox,QtCore.Qt.MouseButton.LeftButton,pos=QtCore.QPoint(10,checkbox.height()//2))
    QtTest.QTest.mouseClick(view.details_toggle,QtCore.Qt.MouseButton.LeftButton);app.processEvents()
    assert view.export_button.isVisible() and view.export_button.isEnabled()
    monkeypatch.setattr(QtWidgets.QFileDialog,'getExistingDirectory',lambda *a,**k:str(tmp_path))
    QtTest.QTest.mouseClick(view.export_button,QtCore.Qt.MouseButton.LeftButton);app.processEvents()
    rows,meta = read(next(tmp_path.glob('multisite_*')))
    assert {row['series_id'] for row in rows}=={'Fe(A)','Fe(B)','Total'}
    assert len(view.figure.axes[0].lines)==3 and meta['selection']['include_total']
    assert all(row['coverage_state']=='modeled' for row in rows)
    view.details_toggle.setChecked(False);app.processEvents();view.canvas.draw()
    if os.environ.get('EMCD_VIEWER_CHECK_IMAGE'):view.window().grab().save(os.environ['EMCD_VIEWER_CHECK_IMAGE'])
