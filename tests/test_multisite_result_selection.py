"""Stored intensity fixtures only: selection must never run a simulation."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from copy import deepcopy
from dataclasses import asdict
from types import SimpleNamespace
import sys

import numpy as np
import pytest
from matplotlib.figure import Figure
from PySide6 import QtCore,QtWidgets,QtTest

from emcd_sim.gui.emcd_forward import ForwardSettings
from emcd_sim.gui.forward_pipeline import MultiSiteForwardSettings
from emcd_sim.gui.geometry import Settings
from emcd_sim.gui.multisite_results import SPECTRAL_KEYS,spectral_series,covered_segments,draw_totals
from emcd_sim.gui.results import ResultsView


def spectra(energy,scale=1.,sign=1.,mask=None):
    x = np.arange(len(energy),dtype=float)
    na = scale*(3+x);nb = scale*(2+.5*x)
    ma = sign*scale*(.12-.02*x);mb = sign*scale*(-.03+.01*x)
    values = dict(energy_ev=energy.copy(),I_A_plus=na+ma,I_A_minus=na-ma,I_B_plus=nb+mb,I_B_minus=nb-mb,
        N_A=na,N_B=nb,M_A=ma,M_B=mb,D_raw=na+ma-nb-mb,D_mag=ma-mb,D_nonmag=na-nb,Sigma_ref=na+nb)
    if mask is not None:
        for key in SPECTRAL_KEYS:values[key] = np.where(mask,values[key],0.)
    return values


def stored_result(kind='Fe3O4',omit=False):
    energy = np.array([710.,716.,723.]) if kind=='Fe3O4' else np.array([710.,716.,723.,850.,856.,863.])
    species = ('Fe','Fe','Fe','O','O','O','O') if kind=='Fe3O4' else ('Fe','Ni')
    specs = [('Fe(A)','Fe',1,1.,-1.),('Fe(B)','Fe',2,4.,1.)] if kind=='Fe3O4' else [('Fe','Fe',1,1.,1.),('Ni','Ni',1,9.,1.)]
    count = sum(item[2] for item in specs);groups = {};channels = {}
    for gid,element,n,scale,sign in specs:
        mask = np.ones(len(energy),bool) if kind=='Fe3O4' else ((energy<800) if element=='Fe' else (energy>800))
        excluded = omit and gid == specs[-1][0]
        bounds = [float(energy[mask][0]),float(energy[mask][-1])]
        if excluded:mask[:] = False
        source = dict(element=element,edge='L2,3',units='angstrom^2/eV',normalization='per_atom_relative',
            path=gid+'.json',source='Synthetic stored intensities for UI tests; no physical spectrum prediction',
            status='synthetic',frame_to_crystal=np.eye(3).tolist())
        groups[gid] = dict(spectra=spectra(energy,scale,sign,mask),metadata=dict(element=element,multiplicity=n,
            indices=tuple(range(n)),normalization='mean_per_selected_atom',contribution_weight=n/count,
            magnetization_crystal=(0,0,sign),source=source))
        channels[gid] = dict(element=element,edge='L2,3',modeled_window_ev=None if excluded else bounds,
            active_energy_mask=mask.tolist(),omitted_by_request=excluded)
    total = dict(energy_ev=energy.copy())
    for key in SPECTRAL_KEYS:total[key] = sum(g['metadata']['multiplicity']/count*g['spectra'][key] for g in groups.values())
    settings = Settings(zone=(0,0,1),target=(2,0,0))
    cfg = MultiSiteForwardSettings(energy_scope='full',angular_maps=False,selected_edges=(('L3',710.),('L2',723.)))
    return dict(config=cfg,settings=settings,spectra=total,groups=groups,method='bloch',maps={},
        model=SimpleNamespace(elastic=SimpleNamespace(crystal=SimpleNamespace(species=species))),
        metadata=dict(structure='Synthetic stored result',settings=asdict(settings),solver='bloch Single Channeling',
            scientific_status='SYNTHETIC TEST ONLY',limitations='Stored synthetic intensity fixture, no new physics calculation',
            alpha=None,pair_reason='Fixture only',correction_reason='Disabled',
            multisite=dict(selected_atom_count=count,global_reversal=False,channels=channels)))


@pytest.mark.parametrize('kind',['Fe3O4','FeNi'])
def test_weighted_groups_elements_total_and_original_amplitudes(kind):
    result = stored_result(kind);before = deepcopy(result['groups']);n = result['metadata']['multisite']['selected_atom_count']
    groups = spectral_series(result,('compare',None),compared=tuple(result['groups']))
    for key in SPECTRAL_KEYS:
        np.testing.assert_allclose(sum(g['spectra'][key] for g in groups),result['spectra'][key],rtol=1e-14)
        elements = [spectral_series(result,('element',element))[0] for element in set(g['metadata']['element'] for g in result['groups'].values())]
        np.testing.assert_allclose(sum(e['spectra'][key] for e in elements),result['spectra'][key],rtol=1e-14)
    for gid,original in result['groups'].items():
        mean = spectral_series(result,('group',gid),'mean')[0]
        weighted = spectral_series(result,('group',gid),'weighted')[0]
        for key in SPECTRAL_KEYS:
            np.testing.assert_array_equal(mean['spectra'][key],original['spectra'][key])
            np.testing.assert_allclose(weighted['spectra'][key],original['metadata']['multiplicity']/n*mean['spectra'][key])
            np.testing.assert_array_equal(original['spectra'][key],before[gid]['spectra'][key])
    assert n == (3 if kind=='Fe3O4' else 2)  # O remains elastic-only, never in the Fe denominator.


def test_parity_and_detector_differences_remain_distinct():
    result = stored_result()
    for selection in [('total',None),('element','Fe'),('group','Fe(B)')]:
        s = spectral_series(result,selection)[0]['spectra']
        for detector in ('A','B'):
            np.testing.assert_allclose(s['N_'+detector],(s['I_'+detector+'_plus']+s['I_'+detector+'_minus'])/2)
            np.testing.assert_allclose(s['M_'+detector],(s['I_'+detector+'_plus']-s['I_'+detector+'_minus'])/2)
        np.testing.assert_allclose(s['D_raw'],s['I_A_plus']-s['I_B_plus'])
        np.testing.assert_allclose(s['D_mag'],s['M_A']-s['M_B'])
        np.testing.assert_allclose(s['D_nonmag'],s['N_A']-s['N_B'])
        assert not np.allclose(s['D_raw'],s['D_mag'])


def test_disjoint_windows_exclusions_and_actual_plot_samples():
    result = stored_result('FeNi');energy = result['spectra']['energy_ev']
    assert len(covered_segments(result,energy)) == 2
    figure = Figure()
    draw_totals(figure,result,'bloch','eels','',selection=('group','Fe'),quantity=1)
    for line in figure.axes[0].lines:np.testing.assert_array_equal(line.get_xdata(),energy[:3])
    draw_totals(figure,result,'bloch','eels','',selection=('total',None),quantity=1)
    assert len(figure.axes[0].lines) == 4  # Two A/B curves, each broken into two native windows.
    assert all(np.max(line.get_xdata())<800 or np.min(line.get_xdata())>800 for line in figure.axes[0].lines)
    omitted = stored_result('FeNi',omit=True)
    draw_totals(figure,omitted,'bloch','eels','',selection=('group','Ni'),quantity=4)
    assert not figure.axes[0].lines
    assert 'not physical zero' in figure.axes[0].texts[0].get_text()
    assert spectral_series(omitted,('group','Fe'))[0]['scale'] == .5


@pytest.fixture(scope='module')
def app():return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def view(app,monkeypatch):
    def forbidden(*args,**kwargs):pytest.fail('Result selection invoked a numerical calculation')
    for name in ('calculate','calculate_multisite'):
        monkeypatch.setattr('emcd_sim.gui.forward_pipeline.'+name,forbidden)
        monkeypatch.setattr('emcd_sim.gui.stage_b.'+name,forbidden)
    owner = QtWidgets.QMainWindow();owner.resize(1100,900);owner.dialogs=[]
    owner.comparison = QtWidgets.QPlainTextEdit();owner.error=forbidden
    owner.responsive=SimpleNamespace(show_panel=lambda *a:None,compact=False,focus_plot=lambda *a:None)
    widget = ResultsView(owner,'eels');owner.eels_view=widget;owner.setCentralWidget(widget)
    yield widget
    owner.close();owner.deleteLater();app.processEvents()


def select(view, mode, value=None):
    box = view.multisite_controls.selection
    index = next((i for i in range(box.count()) if tuple(box.itemData(i)) == (mode,value)),-1)
    assert index >= 0;box.setCurrentIndex(index)


@pytest.mark.parametrize('quantity',[0,1])
def test_legend_click_hides_complete_curve_and_survives_reflow_export(view,tmp_path,quantity):
    result=stored_result('FeNi');before=deepcopy(result['spectra'])
    view.set_result(result);select(view,'compare')
    include=next(box for box in view.multisite_controls.findChildren(QtWidgets.QCheckBox)
                 if box.text()=='Include total spectrum')
    include.setChecked(True);view.multisite_controls.quantity.setCurrentIndex(quantity)
    # Total spans two disjoint modeled windows. One legend entry must control
    # BOTH segments, while independent group/state curves stay untouched.
    proxy,target=next((p,t) for p,t in view.proxies if isinstance(t,tuple) and len(t)==2)
    label=next(p for p,t in view.proxies if t is target and hasattr(p,'get_text'))
    other=next(t for p,t in view.proxies if t is not target)
    from matplotlib.backend_bases import MouseEvent
    def click(artist):
        view.canvas.draw()
        box=artist.get_window_extent(view.canvas.get_renderer())
        view.figure.pick(MouseEvent('button_press_event',view.canvas,(box.x0+box.x1)/2,(box.y0+box.y1)/2,button=1))
    click(proxy)
    assert all(not line.get_visible() for line in target)
    assert all(line.get_visible() for line in other)
    assert proxy.get_alpha()==label.get_alpha()==.2
    view.presentation.reflow(900)
    view.canvas.print_figure(tmp_path/'hidden_curve.png')
    assert all(not line.get_visible() for line in target)
    assert proxy.get_alpha()==label.get_alpha()==.2
    click(label)
    assert all(line.get_visible() for line in target)
    assert proxy.get_alpha()==label.get_alpha()==1
    assert len(view.presentation.specs)==(2 if quantity==0 else 1)
    for key,value in before.items():np.testing.assert_array_equal(result['spectra'][key],value)


def test_gui_switching_means_comparison_elements_and_methods_without_recalculation(view):
    result = stored_result();before = deepcopy(result['spectra']);view.set_result(result)
    controls = view.multisite_controls
    assert 'Total normalized intensity' in view.multisite_banner.text() and 'N=3' in view.multisite_banner.text()
    assert 'O' in controls.sources.text() and 'elastic structure only' in controls.sources.text()
    select(view,'group','Fe(B)');controls.quantity.setCurrentIndex(1)
    np.testing.assert_allclose(view.figure.axes[0].lines[0].get_ydata(),2/3*result['groups']['Fe(B)']['spectra']['I_A_plus'])
    controls.normalization.setCurrentIndex(1)
    assert 'not additive' in view.multisite_banner.text()
    np.testing.assert_array_equal(view.figure.axes[0].lines[0].get_ydata(),result['groups']['Fe(B)']['spectra']['I_A_plus'])
    select(view,'element','Fe')
    assert not controls.normalization.isEnabled()
    np.testing.assert_allclose(view.figure.axes[0].lines[0].get_ydata(),result['spectra']['I_A_plus'])
    select(view,'compare');controls.normalization.setCurrentIndex(0);controls.quantity.setCurrentIndex(6)
    assert len(view.figure.axes[0].lines) == 2
    assert 'MDFF' in controls.sources.text() and 'Fe(A)' in controls.sources.text()
    controls.groups.item(1).setCheckState(QtCore.Qt.CheckState.Unchecked)
    assert len(view.figure.axes[0].lines) == 1
    controls.groups.item(0).setCheckState(QtCore.Qt.CheckState.Unchecked)
    assert not view.figure.axes[0].lines
    assert 'No comparison groups selected' in view.multisite_banner.text()
    for key in SPECTRAL_KEYS:np.testing.assert_array_equal(result['spectra'][key],before[key])
    # Changing solver chooses its stored arrays, preserving the selected group.
    other = deepcopy(result)
    for key in SPECTRAL_KEYS:
        other['spectra'][key] *= 2
        for group in other['groups'].values():group['spectra'][key] *= 2
    result = dict(result,methods={'bloch':result,'fft-multislice':other})
    view.set_result(result);select(view,'group','Fe(A)');controls.normalization.setCurrentIndex(0)
    view.method.setCurrentIndex(1)
    np.testing.assert_allclose(view.figure.axes[0].lines[0].get_ydata(),other['groups']['Fe(A)']['spectra']['D_mag']/3)


def test_legacy_ni_view_remains_the_existing_two_panel_view(view):
    result = stored_result();result['config']=ForwardSettings(model='atomic',l3=710,l2=723,energy_scope='full',angular_maps=False,correction=False)
    result['model'].elastic.crystal.species=('Ni',)*4
    view.set_result(result)
    assert view.multisite_controls.isHidden() and view.multisite_banner.isHidden()
    assert len(view.figure.axes) == 2
    np.testing.assert_array_equal(next(line for line in view.figure.axes[0].lines if line.get_label()=='Detector A').get_ydata(),result['spectra']['I_A_plus'])
    assert view.component_mode.isVisibleTo(view)


def test_results_polish_defaults_relevance_and_exports(view):
    result=stored_result();view.navigation.addAction('Export Figure…')
    view.set_result(result);controls=view.multisite_controls
    assert controls.selection.currentText()=='Total Results'
    assert controls.groups.isHidden() and controls.normalization.isHidden() and controls.include_total.isHidden()
    assert controls.sources.parent() is view.details_body
    assert not controls.sources.isVisibleTo(view) and 'MDFF' in controls.selection.toolTip()
    assert 'I_A_plus' in controls.quantity.toolTip() and 'D_mag' in controls.quantity.toolTip()
    assert sum(a.text()=='Export Figure…' for a in view.navigation.actions())==1
    assert getattr(view.navigation,'_actions',{})['save_figure'] not in view.navigation.actions()
    select(view,'group','Fe(B)');controls.normalization.setCurrentIndex(1)
    assert 'Group Mean' in view.multisite_banner.text() and 'not additive' in view.multisite_banner.text()
    assert not controls.normalization.isHidden() and controls.groups.isHidden()
    view.set_result(result)  # Redrawing the same run preserves its chosen view.
    assert controls.options()['selection'][0]=='group' and controls.options()['normalization']=='mean'
    view.set_result(deepcopy(result))  # A different run starts with total results.
    assert controls.options()['selection']==('total',None) and controls.options()['normalization']=='weighted'
    select(view,'compare');assert not controls.groups.isHidden() and controls.groups.height()<78
    controls.quantity.setCurrentIndex(4)
    assert '(I_A_plus - I_A_minus)/2' in controls.quantity.toolTip()
    view._focused=True;view.set_compact(True)
    assert not view.details_section.isHidden()  # Metadata and exports stay reachable when maximized.


def test_shared_primary_total_components_and_display_restoration(view):
    result=stored_result('FeNi');before=deepcopy(result['spectra']);view.set_result(result)
    assert len(view.figure.axes)==2
    assert not view.choice.isHidden() and not view.component_mode.isHidden()
    # Actual modeled samples only: no line joins the unsupported Fe/Ni gap.
    for ax in view.figure.axes:
        for line in ax.lines:
            if not line.get_label().startswith('_'):
                energy=line.get_xdata()
                assert np.max(energy)<800 or np.min(energy)>800
    from emcd_sim.gui.component_display import components
    expected=components(result['spectra'],'asymmetry')[0]['EMCD Asymmetry']
    view.component_mode.setCurrentIndex(1)
    curves=[line for line in view.figure.axes[1].lines if line.get_color()=='C2']
    np.testing.assert_array_equal(np.concatenate([line.get_ydata() for line in curves]),expected)
    controls=view.multisite_controls;select(view,'compare');controls.include_total.setChecked(True)
    controls.groups.item(1).setCheckState(QtCore.Qt.CheckState.Unchecked)
    options=controls.options();controls.set_result(deepcopy(result));controls.restore_options(options)
    assert controls.options()==options
    for key,value in before.items():np.testing.assert_array_equal(result['spectra'][key],value)


def test_shared_tabs_and_saved_map_export(view,monkeypatch,tmp_path):
    from emcd_sim.gui.stage_b import StageB
    tabs=QtWidgets.QTabWidget()
    for _ in range(4):tabs.addTab(QtWidgets.QWidget(),'')
    for result in (stored_result(),dict(config=ForwardSettings())):
        StageB.sync_result_capabilities(SimpleNamespace(tabs=tabs),result)
        assert tabs.tabText(1)=='EMCD Angular Maps' and tabs.tabText(3)=='Magnetic / Nonmagnetic'
    widget=ResultsView(view.owner,'maps');result=stored_result();widget.set_result(result)
    assert widget.export_button.isEnabled()
    saved=[]
    monkeypatch.setattr(QtWidgets.QFileDialog,'getExistingDirectory',lambda *a:str(tmp_path))
    monkeypatch.setattr('emcd_sim.gui.project_io.save_project',lambda r,p:saved.append((r,p)))
    widget.export_derived()
    assert len(saved)==1 and saved[0][0]['maps'] is result['maps'] and saved[0][1].parent==tmp_path
    assert saved[0][0]['display_state']['angular_selection']==widget.map_options()
    widget.deleteLater()


@pytest.mark.parametrize('normalization,identical',[('weighted',False),('mean',True)])
def test_angular_group_energy_binding_matches_image_arrays(view,monkeypatch,normalization,identical):
    from dataclasses import replace
    from emcd_sim.gui.multisite_results import angular_group_view
    result=stored_result();keys=('Fe(A):L3','Fe(B):L2')
    result['config']=replace(result['config'],angular_maps=True,selected_edges=((keys[0],710.),(keys[1],723.)))
    qx,qy=np.meshgrid([-1.,0.,1.],[-1.,0.,1.]);result.update(qx=qx,qy=qy)
    result['model'].elastic.crystal.g_vector=lambda hkl:np.array([1.,0.,0.])
    monkeypatch.setattr('emcd_sim.gui.results.decorate_reciprocal_map',lambda *a,**k:None)
    for index,(gid,group) in enumerate(result['groups'].items()):
        group['metadata']['source']['selected_ev']={'L3':710.,'L2':723.};group['maps']={}
        for e,key in enumerate(keys):
            base=10+qx*qx+(0 if identical else (index+e+1)*.1*qy)
            odd=(.2 if identical else .1*(1+2*index+e))*qy
            group['maps'][key]=dict(I_plus=base+odd,I_minus=base-odd,I_mag=odd,I_nonmag=base)
    result['maps']={key:{field:sum(g['metadata']['multiplicity']/3*g['maps'][key][field] for g in result['groups'].values())
                        for field in ('I_plus','I_minus','I_mag','I_nonmag')} for key in keys}
    original=deepcopy(result['groups']);widget=ResultsView(view.owner,'maps');widget.set_result(result)
    widget.map_scope.setCurrentIndex(widget.map_scope.findData(normalization));images=[];limits=[]
    for gid,key in [('Fe(A)',keys[0]),('Fe(B)',keys[1]),('Fe(A)',keys[0])]:
        index=next((i for i in range(widget.choice.count()) if tuple(widget.choice.itemData(i))==(gid,key)),-1)
        assert index>=0;widget.choice.setCurrentIndex(index);widget.redraw()
        fields=original[gid]['maps'][key];scale=1. if normalization=='mean' else original[gid]['metadata']['multiplicity']/3
        odd=(fields['I_plus']-fields['I_minus'])/2;expected=scale*(odd-odd[::-1])
        image=widget.figure.axes[0].images[0];np.testing.assert_allclose(image.get_array(),expected,rtol=1e-13,atol=1e-14)
        assert widget.figure._emcd_display_metadata['group_id']==gid
        assert widget.figure._emcd_display_metadata['energy_ev']==dict(result['config'].selected_edges)[key]
        images.append(np.array(image.get_array()));limits.append(image.get_clim())
    np.testing.assert_array_equal(images[0],images[2]);assert limits[0]==limits[1]==limits[2]
    if identical:np.testing.assert_array_equal(images[0],images[1])  # Never force physical differences.
    options=widget.map_options();widget.map_scope.setCurrentIndex(0);widget.restore_map_options(options);assert widget.map_options()==options
    widget.component_mode.setCurrentIndex(1)
    fields=original['Fe(A)']['maps'][keys[0]];ap=fields['I_plus']
    np.testing.assert_allclose(widget.figure.axes[0].images[0].get_array(),100*(ap-ap[::-1])/(ap+ap[::-1]))
    for gid,g in original.items():
        for edge,fields in g['maps'].items():
            for key,value in fields.items():np.testing.assert_array_equal(value,result['groups'][gid]['maps'][edge][key])
    widget.deleteLater()


@pytest.mark.skipif(sys.platform!='win32' or os.environ.get('QT_QPA_PLATFORM')!='windows',reason='Explicit native Windows result selection check')
def test_native_windows_group_element_comparison(view,app):
    assert app.platformName() == 'windows'
    view.window().resize(480,780)  # Match a narrow Results panel, not a full-width plot.
    view.navigation.addAction('Export Figure…')
    result = stored_result();view.set_result(result);view.window().show();app.processEvents()
    assert QtTest.QTest.qWaitForWindowExposed(view.window().windowHandle(),3000)
    controls = view.multisite_controls
    if os.environ.get('EMCD_VIEWER_CHECK_IMAGE'):
        view.canvas.draw();view.window().grab().save(os.environ['EMCD_VIEWER_CHECK_IMAGE']+'_total.png')
    select(view,'group','Fe(B)');controls.normalization.setCurrentIndex(1)
    assert 'not additive' in view.multisite_banner.text()
    select(view,'element','Fe');assert 'fixed N=3' in view.multisite_banner.text()
    select(view,'compare');controls.normalization.setCurrentIndex(0);controls.quantity.setCurrentIndex(6)
    app.processEvents()
    item = controls.groups.item(1);rect = controls.groups.visualItemRect(item)
    assert not rect.isEmpty()
    option = QtWidgets.QStyleOptionViewItem();option.initFrom(controls.groups)
    controls.groups.itemDelegate().initStyleOption(option,controls.groups.indexFromItem(item))
    option.rect = rect
    indicator = controls.groups.style().subElementRect(QtWidgets.QStyle.SubElement.SE_ItemViewItemCheckIndicator,option,controls.groups)
    point = indicator.center()
    QtTest.QTest.mouseClick(controls.groups.viewport(),QtCore.Qt.MouseButton.LeftButton,pos=point)
    assert item.checkState() == QtCore.Qt.CheckState.Unchecked and len(view.figure.axes[0].lines) == 1
    QtTest.QTest.mouseClick(controls.groups.viewport(),QtCore.Qt.MouseButton.LeftButton,pos=point)
    assert item.checkState() == QtCore.Qt.CheckState.Checked
    app.processEvents();QtTest.QTest.qWait(150);view.canvas.draw()
    assert len(view.figure.axes[0].lines) == 2
    assert 'fixed N=3' in view.multisite_banner.text()
    if os.environ.get('EMCD_VIEWER_CHECK_IMAGE'):view.window().grab().save(os.environ['EMCD_VIEWER_CHECK_IMAGE']+'_groups.png')
    # Same production view, legacy Ni arrays and unchanged two-panel presentation.
    ni=stored_result();ni['config']=ForwardSettings(model='atomic',l3=710,l2=723,energy_scope='full',angular_maps=False,correction=False)
    ni['model'].elastic.crystal.species=('Ni',)*4
    view.set_result(ni);app.processEvents();view.canvas.draw()
    assert len(view.figure.axes)==2 and controls.sources.isHidden()
    if os.environ.get('EMCD_VIEWER_CHECK_IMAGE'):view.window().grab().save(os.environ['EMCD_VIEWER_CHECK_IMAGE']+'_ni.png')
