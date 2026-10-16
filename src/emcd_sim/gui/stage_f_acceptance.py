"""Opt-in visualization acceptance using saved projects, never a solver."""
from pathlib import Path
from contextlib import ExitStack
from unittest.mock import patch
import hashlib,json,sys,traceback
import numpy as np
from PySide6 import QtCore,QtWidgets
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from .signal_normalization import DisplaySettings, normalized_spectra, angular_display, percentage_metrics
from .normalization_export import export_derived,save_figure
from .project_io import load_project
from .runtime import build_info


FORWARD_PATHS=('emcd_sim.physical_elastic.PhysicalElasticModel.amplitudes','emcd_sim.multislice_reference.fft_multislice_ni',
    'emcd_sim.gui.emcd_forward.calculate','emcd_sim.gui.emcd_forward.tensors','emcd_sim.gui.propagation.propagate',
    'emcd_sim.gui.emcd_forward.run_tensor_with_coherence','emcd_sim.single_channeling_tensor.run_tensor_with_coherence',
    'emcd_sim.gui.stage_b.EMCDWorker.run','emcd_sim.gui.app.PreviewWorker.run')


def fingerprints(result):
    arrays={}
    for name,r in result['methods'].items():
        arrays.update({name+'__'+k:v for k,v in dict(r['spectra'],coherence=r['coherence'],amplitudes=r['amplitudes'],qx=r['qx'],qy=r['qy']).items()})
        arrays.update({name+'__'+e+'__'+k:v for e,fields in r['maps'].items() for k,v in fields.items()})
        arrays.update({name+'__weight_'+k:v for k,v in r['weights'].items()})
    return {key:hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest() for key,a in arrays.items()}


def run(output,project,comparison):
    from .app import MainWindow
    from .compare_results import CompareResults
    from ..emcd_angular_plots import decorate_reciprocal_map
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    source_files={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for folder in (project,comparison) for p in Path(folder).iterdir() if p.is_file()}
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([]);w=MainWindow(workspace=output/'workspace');w.resize(1700,1050);w.show()
    report=dict(build=build_info(),forward_calls=0,project=str(project),comparison=str(comparison));guards=ExitStack();mocks=[]
    for name in FORWARD_PATHS:mocks.append(guards.enter_context(patch(name,side_effect=AssertionError('Forward calculation forbidden during Stage F'))))
    def fail(message):
        report['error']=message;(output/'failure.json').write_text(json.dumps(report,indent=2));app.exit(2)
    sys.excepthook=lambda typ,value,tb:fail(''.join(traceback.format_exception(typ,value,tb)));w.error=fail
    def finish():
        report['forward_calls']=sum(m.call_count for m in mocks);assert report['forward_calls']==0
        assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest for p,digest in source_files.items())
        assert fingerprints(w.emcd_result)==report['original_arrays'];report['original_arrays_unchanged']=True;report['project_files_unchanged']=True
        (output/'acceptance.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8');w.close();app.quit()
    def capture():w.grab().save(str(output/'stage_f_emcd_percentage.png'));finish()
    def inspect():
        if w.busy:QtCore.QTimer.singleShot(100,inspect);return
        r=w.emcd_result;report['original_arrays']=fingerprints(r);second=load_project(comparison)
        w.browser.registry.register(second,comparison,'+1 mrad x mistilt');w.browser.refresh()
        methods=list(r['methods']);report['methods']=methods;report['metrics']={name:percentage_metrics(m) for name,m in r['methods'].items()}
        eels=w.eels_view;maps=w.maps_view
        for mode in range(3):
            eels.normalization.mode.setCurrentIndex(mode)
            for zoom in range(3):eels.choice.setCurrentIndex(zoom);eels.redraw()
        eels.choice.setCurrentIndex(0);eels.normalization.mode.setCurrentIndex(2);eels.normalization.peak_edge.setCurrentIndex(1);eels.redraw()
        save_figure(eels.figure,output/'eels_l3_peak.png');save_figure(eels.figure,output/'eels_l3_peak.svg')
        eels.normalization.peak_edge.setCurrentIndex(2);eels.redraw();save_figure(eels.figure,output/'eels_l2_peak.png')
        eels.normalization.peak_edge.setCurrentIndex(1)
        w.tabs.setCurrentWidget(eels);app.processEvents();w.grab().save(str(output/'native_eels_controls.png'))
        for mode in range(3):maps.normalization.map_mode.setCurrentIndex(mode);maps.redraw()
        save_figure(maps.figure,output/'paired_maps.png');save_figure(maps.figure,output/'paired_maps.svg')
        entries=[(name,m,name) for name,m in r['methods'].items()]
        settings=DisplaySettings(mode='peak',map_mode='paired')
        export_derived(entries,output/'derived_bw_ms',settings)
        c=CompareResults(w,[('Exact Bragg',r),('+1 mrad x',second)]);w.tabs.addTab(c,'Saved percentage comparison');c.normalization.mode.setCurrentIndex(2)
        c.normalization.map_mode.setCurrentIndex(2);c.field.setCurrentText('Raw paired EMCD');c.redraw()
        save_figure(c.figure,output/'saved_comparison.png');save_figure(c.figure,output/'saved_comparison.svg')
        export_derived(c.entries(),output/'derived_saved_comparison',c.normalization.settings())
        # A native Qt acceptance tab combines the same derived map/spectrum
        # arrays for an actual window capture. No synthetic images or physics.
        widget=QtWidgets.QWidget();layout=QtWidgets.QVBoxLayout(widget)
        layout.addWidget(QtWidgets.QLabel('Stage F | saved Ni [017] | fixed BW nonmagnetic L3 peak; paired angular percentages use local even A+B'))
        fig=Figure(figsize=(13,8),layout='constrained');grid=fig.add_gridspec(2,2);m=r['methods'].get('bloch',r);h=m['config'].halfwidth;extent=(-h,h,-h,h)
        mapmeta=[]
        for j,(key,title) in enumerate((('D_mag','Magnetic odd paired angular asymmetry'),('D_nonmag','Nonmagnetic paired angular asymmetry'))):
            value,meta=angular_display(m,'L3',key,'paired');mapmeta.append(meta);ax=fig.add_subplot(grid[0,j]);finite=abs(value[np.isfinite(value)]);limit=max(float(finite.max()) if finite.size else 0.,1e-12)
            from matplotlib import colormaps
            im=ax.imshow(value,origin='lower',extent=extent,cmap=colormaps['RdBu_r'].with_extremes(bad='#c8c8c8'),vmin=-limit,vmax=limit)
            decorate_reciprocal_map(ax,m['model'],extent,target_hkl=m['settings'].target,zone_axis=m['settings'].zone);ax.set_title(title,fontsize=9);fig.colorbar(im,ax=ax,shrink=.8).set_label('%')
        ax=fig.add_subplot(grid[1,:]);normalized=normalized_spectra(entries,settings)
        for (label,m,name),(values,meta) in zip(entries,normalized):
            for i,key in enumerate(('D_mag','D_nonmag','D_raw','D_corrected')):
                if key in values:ax.plot(m['spectra']['energy_ev'],values[key],label=label+' '+key,color='C'+str(i),ls='-' if name=='bloch' else '--')
        ax.axhline(0,color='.6',lw=.6);ax.set(xlabel='Native saved energy loss (eV)',ylabel='% of nonmagnetic L3 EELS peak');ax.legend(ncols=4,fontsize=7);ax.grid(alpha=.15)
        peak=normalized[0][1]['peak'];fig.suptitle('Stored results only | P_L3 = max(N_A+N_B) = %.7g, window %.3f–%.3f eV\nGrey map pixels: undefined / outside A support; corrected difference is not purely magnetic.'%(peak['value'],*peak['window_ev']),fontsize=10)
        fig._emcd_display_metadata=dict(spectra=[meta for _,meta in normalized],maps=mapmeta,derived_visualization_only=True)
        canvas=FigureCanvasQTAgg(fig);layout.addWidget(canvas,1);w.tabs.addTab(widget,'Percentage acceptance');w.tabs.setCurrentWidget(widget);w.splitter.setSizes([0,0,sum(w.splitter.sizes())]);w.browser_dock.hide();canvas.draw()
        save_figure(fig,output/'percentage_dashboard.png');save_figure(fig,output/'percentage_dashboard.svg')
        QtCore.QTimer.singleShot(700,capture)
    w.project_ready.connect(lambda:QtCore.QTimer.singleShot(150,inspect));QtCore.QTimer.singleShot(300,lambda:w.open_project_path(project))
    QtCore.QTimer.singleShot(600000,lambda:app.exit(3));code=app.exec();guards.close();return code
