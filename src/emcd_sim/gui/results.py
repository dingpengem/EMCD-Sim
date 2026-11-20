"""Qt result widgets over prepared data and the shared presentation functions."""
import numpy as np
from matplotlib.figure import Figure

from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
from .responsive import ResponsiveCanvas as FigureCanvasQTAgg
from PySide6 import QtWidgets,QtCore

from .normalization_controls import NormalizationControls
from ..mdff_edges import selected_samples

from . import result_presentation as presentation


from .responsive import FlowLayout, CollapsibleSection, FigurePresentation


class ResultsView(QtWidgets.QWidget):
    def __init__(self,parent,kind):
        super().__init__();self.owner=parent;self.kind=kind;self.result=None;self.proxies=[]
        outer=QtWidgets.QVBoxLayout(self);outer.setContentsMargins(0,0,0,0)
        self.scroll=QtWidgets.QScrollArea();self.scroll.setWidgetResizable(True);self.scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        content=QtWidgets.QWidget();self.scroll.setWidget(content);outer.addWidget(self.scroll)
        layout=QtWidgets.QVBoxLayout(content);self.label=QtWidgets.QLabel('No completed EMCD calculation.');self.label.setWordWrap(True);layout.addWidget(self.label)
        row=FlowLayout();layout.addLayout(row)
        if kind=='maps':
            self.map_scope=QtWidgets.QComboBox();self.map_scope.setAccessibleName('Angular result scope')
            for title,key in [('Total Results','total'),('Group Contribution (n/N)','weighted'),('Group Mean (per atom)','mean')]:self.map_scope.addItem(title,key)
            self.map_scope.hide();row.addWidget(self.map_scope);self.map_scope.currentIndexChanged.connect(self.update_map_choices)
        self.choice=QtWidgets.QComboBox();self.choice.addItems([] if kind=='maps' else (['Exit intensity','Depth average'] if kind=='diffraction' else ['Full spectrum']));row.addWidget(self.choice)
        if kind=='maps':
            self.choice.setAccessibleName('Angular group / energy')
            for box in (self.map_scope,self.choice):
                box.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon);box.setMinimumContentsLength(16)
        self.method=QtWidgets.QComboBox();row.addWidget(self.method);self.method.currentIndexChanged.connect(self.update_map_choices if kind=='maps' else self.redraw)
        self.choice.setVisible(kind!='comparison');self.method.setVisible(kind!='comparison')
        self.field=QtWidgets.QComboBox();self.field.addItem('All six fields',None)
        for title,key in [('Magnetic odd','I_mag'),('Magnetic paired','D_mag'),('Nonmagnetic paired','D_nonmag'),('Nonmagnetic even','I_nonmag'),('Total +M','I_plus'),('Raw paired A-B','D_raw'),('Corrected paired A-B','D_corrected'),('Residual even','D_nonmag_residual')]:self.field.addItem(title,key)
        self.field.setVisible(kind=='maps');self.field.currentTextChanged.connect(self.redraw)
        self.component_mode=QtWidgets.QComboBox()
        from .component_display import MODES
        for key,title in MODES.items():self.component_mode.addItem(title,key)
        self.signal_label=QtWidgets.QLabel('Signal Display');self.signal_label.setVisible(kind in ('eels','maps'));row.addWidget(self.signal_label)
        self.component_mode.setVisible(kind in ('eels','maps'));row.addWidget(self.component_mode);self.component_mode.currentIndexChanged.connect(self.redraw)
        maximize=QtWidgets.QPushButton('Maximize / restore results');row.addWidget(maximize);maximize.clicked.connect(self.maximize)
        if kind=='eels':
            from .result_presentation import MultisiteSpectraControls
            self.multisite_controls=MultisiteSpectraControls();self.multisite_controls.hide()
            layout.addWidget(self.multisite_controls);self.multisite_controls.changed.connect(self.redraw)
        self.advanced=QtWidgets.QGroupBox('Advanced Diagnostics — legacy displays');self.advanced.setCheckable(True);self.advanced.setChecked(False);layout.addWidget(self.advanced)
        self.advanced_body=QtWidgets.QWidget();outer=QtWidgets.QVBoxLayout(self.advanced);outer.addWidget(self.advanced_body);self.advanced_body.hide();advanced_layout=QtWidgets.QVBoxLayout(self.advanced_body)
        self.advanced.toggled.connect(self.advanced_body.setVisible);self.advanced.toggled.connect(self.redraw);self.advanced.setVisible(kind!='diffraction')
        self.normalization=NormalizationControls(self,maps=kind=='maps');self.normalization.setVisible(kind!='diffraction');advanced_layout.addWidget(self.normalization);self.normalization.changed.connect(self.redraw)
        advanced_layout.addWidget(self.field)
        self.component_diagnostic=QtWidgets.QComboBox();self.component_diagnostic.addItem('Legacy diagnostics','legacy');self.component_diagnostic.addItem('Magnetic-only / Nonmagnetic Asymmetry (%)','relative');self.component_diagnostic.setToolTip('Magnetic-reversal-odd detector difference, normalized by reversal-even intensity.');self.component_diagnostic.setVisible(kind=='eels');advanced_layout.addWidget(self.component_diagnostic);self.component_diagnostic.currentIndexChanged.connect(self.redraw)
        self.display_note=QtWidgets.QLabel();self.display_note.setWordWrap(True);layout.addWidget(self.display_note)
        if kind=='eels':
            from .prb_controls import PRBBenchmarkControls
            self.prb_benchmark=PRBBenchmarkControls(self);self.benchmark_section=CollapsibleSection('PRB benchmark controls',self.prb_benchmark,expanded=False);self.benchmark_section.setObjectName('benchmark_panel');layout.addWidget(self.benchmark_section)
            self.prb_readout=self.prb_benchmark.summary
            self.prb_benchmark.changed.connect(self.update_prb_metadata)
        export=QtWidgets.QPushButton('Export derived NPZ/CSV + metadata');export.setVisible(kind!='diffraction');layout.addWidget(export);export.clicked.connect(self.export_derived)
        self.export_button=export
        self.figure=Figure(layout='constrained');self.canvas=FigureCanvasQTAgg(self.figure)
        self.navigation=NavigationToolbar2QT(self.canvas,self)
        self.canvas.setMinimumSize(280,160)
        # EELS legend rows grow the canvas minimum height. Ignoring its size
        # hint lets Qt's scroll content under-report that height at high DPI,
        # leaving the final legend rows unreachable even at maximum scroll.
        self.canvas.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Minimum if kind=='eels' else QtWidgets.QSizePolicy.Policy.Ignored)
        self.multisite_banner=QtWidgets.QLabel();self.multisite_banner.setWordWrap(True);self.multisite_banner.hide()
        layout.addWidget(self.multisite_banner);layout.addWidget(self.canvas,1)
        self.details_section=CollapsibleSection('Display details / diagnostics / export',expanded=False);self.details_section.setObjectName('results_details_'+kind);self.details_toggle=self.details_section.header;self.details_body=self.details_section.body;details=QtWidgets.QVBoxLayout(self.details_body);details.setContentsMargins(0,0,0,0)
        for widget in (self.label,self.advanced,self.display_note,export):
            layout.removeWidget(widget);details.addWidget(widget)
        if kind=='eels':
            self.multisite_controls.layout().removeWidget(self.multisite_controls.sources)
            details.addWidget(self.multisite_controls.sources)
        self.full_caption=QtWidgets.QLabel();self.full_caption.setWordWrap(True);self.full_caption.setTextFormat(QtCore.Qt.TextFormat.PlainText);details.addWidget(self.full_caption)
        details.addWidget(self.navigation)
        self.navigation.setMinimumWidth(0)
        self.navigation.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored,QtWidgets.QSizePolicy.Policy.Fixed)
        self.presentation=FigurePresentation(self.canvas,kind,self.full_caption)
        layout.insertWidget(1,self.details_section)
        self.choice.currentTextChanged.connect(self.redraw);self.canvas.mpl_connect('pick_event',self.pick)
    def set_compact(self,compact):
        focused=getattr(self,'_focused',False)
        self.details_section.setVisible(True)
        if hasattr(self,'prb_benchmark'):
            self.prb_benchmark.set_compact(compact)
            self.benchmark_section.setVisible(not focused and (self.result is None or self.result['config'].model!='multisite'))
    def maximize(self):
        w=self.owner
        w.responsive.show_panel(2);self._focused=not getattr(self,'_focused',False);self.set_compact(w.responsive.compact);w.responsive.focus_plot('results')
    def set_result(self,result):
        fresh=result is not self.result
        self.result=result
        # The application supplies its metadata-aware figure export action.
        # Keep the standard Matplotlib action only in standalone views.
        if any(action.text()=='Export Figure…' for action in self.navigation.actions()):
            standard=getattr(self.navigation,'_actions',{}).get('save_figure')
            if standard is not None:self.navigation.removeAction(standard)
        multisite=result['config'].model=='multisite'
        if self.kind=='eels':
            self.multisite_controls.setVisible(multisite);self.choice.setVisible(True)
            self.signal_label.setVisible(True)
            self.multisite_controls.sources.setVisible(multisite)
            if multisite:self.multisite_controls.set_result(result)
            else:self.multisite_controls.result=None
        self.multisite_banner.setVisible(multisite)
        if multisite:
            sites=result['metadata']['multisite']
            self.multisite_banner.setText('Complete-crystal incoming elastic intensity; per incident electron.' if self.kind=='diffraction' else
                f'Modeled partial core-edge · mean per selected ionizing atom (N={sites["selected_atom_count"]}).')
        self.advanced.setVisible(not multisite);self.component_mode.setVisible(self.kind in ('eels','maps'))
        self.field.setVisible(self.kind=='maps' and not multisite)
        self.export_button.setEnabled(True)
        self.export_button.setText(('Export selected spectra CSV + metadata' if self.kind=='eels' else 'Export saved arrays + metadata') if multisite else 'Export derived NPZ/CSV + metadata')
        self.export_button.setToolTip(('All spectral components for the selected series; unsupported samples are blank and labeled. Metadata is written automatically.' if self.kind=='eels' else 'Original saved total/group arrays, coverage, normalization and source metadata; no recalculation.') if multisite else '')
        if self.kind=='eels':self.benchmark_section.setVisible(not multisite)
        if self.kind=='maps':
            self.map_scope.setVisible(multisite)
            if multisite:
                from .multisite_results import angular_choices
                available=bool(angular_choices(result,True))
                for i in (1,2):self.map_scope.model().item(i).setEnabled(available)
                if fresh or not available:
                    with QtCore.QSignalBlocker(self.map_scope):self.map_scope.setCurrentIndex(0)
            else:
                with QtCore.QSignalBlocker(self.map_scope):self.map_scope.setCurrentIndex(0)
        elif self.kind=='eels':
            from .multisite_results import total_energy_samples
            energies=total_energy_samples(result,maps_only=False)
            with QtCore.QSignalBlocker(self.choice):
                self.choice.clear();self.choice.addItem(presentation.spectral_coverage_label(result))
                for sample in energies:
                    unique=sum(s['edge_label']==sample['edge_label'] for s in energies)==1
                    self.choice.addItem((sample['edge_label'] if unique else sample['label'])+' zoom',sample['energy_ev'])
        if not multisite:self.normalization.set_result(result)
        from .propagation import METHOD_NAMES
        options=list(result.get('methods',{result.get('method','bloch'):result}))
        if len(options)==2 and not multisite:options.append('difference' if self.kind in ('maps','diffraction') else 'overlay')
        self.method.blockSignals(True);self.method.clear()
        for key in options:self.method.addItem(METHOD_NAMES.get(key,'BW / MS overlay'),key)
        if self.kind=='eels':self.choice.setItemText(0,presentation.spectral_coverage_label(result))
        self.method.blockSignals(False)
        if self.kind=='maps':self.update_map_choices(redraw=False,preserve=not fresh)
        self.redraw()
    def map_result(self):
        return self.result.get('methods',{}).get(self.method.currentData(),self.result)
    def update_map_choices(self,*_,redraw=True,preserve=True):
        if self.result is None:return
        from .multisite_results import angular_choices,energy_sample_index
        current=self.map_result();previous=self.map_options() if preserve else {}
        with QtCore.QSignalBlocker(self.choice):
            self.choice.clear()
            samples=dict(selected_samples(current['config']))
            for label,data in angular_choices(current,self.map_scope.currentData()!='total' and current['config'].model=='multisite'):
                self.choice.addItem(label,data)
                energy=float(current['spectra']['energy_ev'][energy_sample_index(current,samples[data[1]])])
                self.choice.setItemData(self.choice.count()-1,energy,QtCore.Qt.ItemDataRole.UserRole+1)
                aliases=[key for key,value in samples.items() if value==energy]
                self.choice.setItemData(self.choice.count()-1,'Saved energy: '+repr(energy)+' eV\nSample aliases: '+', '.join(aliases),QtCore.Qt.ItemDataRole.ToolTipRole)
            # Changing scope preserves the energy, but never merges different groups.
            target_gid=previous.get('group_id') if self.map_scope.currentData()!='total' else None
            index=next((i for i in range(self.choice.count()) if self.choice.itemData(i)[0]==target_gid and self.choice.itemData(i,QtCore.Qt.ItemDataRole.UserRole+1)==previous.get('energy_ev')),-1)
            if index<0 and target_gid is None and previous.get('energy_ev') is not None:
                index=next((i for i in range(self.choice.count()) if self.choice.itemData(i,QtCore.Qt.ItemDataRole.UserRole+1)==previous['energy_ev']),-1)
            if index>=0 or previous.get('energy_ev') is not None:self.choice.setCurrentIndex(index)
        self.choice.setToolTip('Select the actual saved group and energy. Total Results uses total maps; the spectra selector is independent. Only modeled, saved group maps are listed.')
        if redraw:self.redraw()
    def map_options(self):
        selection=self.choice.currentData() or (None,None)
        return dict(scope=self.map_scope.currentData(),group_id=selection[0],edge=selection[1],
            energy_ev=self.choice.currentData(QtCore.Qt.ItemDataRole.UserRole+1),method=self.method.currentData())
    def restore_map_options(self,options):
        if not options:return
        from .multisite_results import energy_sample_index
        method=options.get('method',self.method.currentData());mi=self.method.findData(method)
        if mi>=0:
            with QtCore.QSignalBlocker(self.method):self.method.setCurrentIndex(mi)
        index=self.map_scope.findData(options.get('scope','total'))
        available=index>=0 and self.map_scope.model().item(index).isEnabled() and mi>=0
        with QtCore.QSignalBlocker(self.map_scope):self.map_scope.setCurrentIndex(index if available else 0)
        self.update_map_choices(redraw=False)
        current=self.map_result();energy=options.get('energy_ev')
        if energy is None:energy=dict(selected_samples(current['config'])).get(options.get('edge'))
        try:energy=float(current['spectra']['energy_ev'][energy_sample_index(current,energy)]) if energy is not None else None
        except ValueError:energy=None
        index=next((i for i in range(self.choice.count()) if self.choice.itemData(i)[0]==options.get('group_id') and self.choice.itemData(i,QtCore.Qt.ItemDataRole.UserRole+1)==energy),-1) if available and energy is not None else -1
        self.choice.setCurrentIndex(index)
        self.redraw()
        if index<0:self.display_note.setText('Saved angular scope/energy is unavailable. Choose an available selection explicitly; no substitute was selected.')
    def restore_zoom(self,label,energy=None):
        from .multisite_results import energy_sample_index
        if energy is None and label and label.endswith(' zoom'):
            energy=dict(selected_samples(self.result['config'])).get(label.removesuffix(' zoom'))
        if energy is not None:
            try:energy=float(self.result['spectra']['energy_ev'][energy_sample_index(self.result,energy)])
            except ValueError:energy=None
            index=self.choice.findData(energy) if energy is not None else -1
        else:index=self.choice.findText(label or '')
        with QtCore.QSignalBlocker(self.choice):self.choice.setCurrentIndex(max(0,index))
        return 'Saved spectral zoom unavailable; showing the actual calculated range.' if index<0 and label and label.endswith(' zoom') else ''
    def redraw(self,*_):
        if self.result is None:return
        method=self.method.currentData() or self.result.get('method','bloch')
        if self.result['config'].model=='multisite' and self.kind in ('eels','comparison'):
            from .multisite_results import description
            options=self.multisite_controls.options() if self.kind=='eels' else {}
            self.proxies=(presentation.draw_eels(self.figure,self.result,self.choice.currentText(),method,component_mode=self.component_mode.currentData(),zoom_energy=self.choice.currentData(),**options)
                if self.kind=='eels' else presentation.draw_multisite_panel(self.figure,self.result,method,self.kind,self.choice.currentText(),**options))
            if self.kind=='eels':
                from .multisite_results import spectral_series,selection_description
                current=self.result.get('methods',{}).get(method,self.result)
                series=spectral_series(current,options['selection'],options['normalization'],options['compared'],options['include_total'])
                sites=current['metadata']['multisite']
                self.multisite_banner.setText(self.multisite_controls.normalization_note(current,series))
                self.multisite_banner.setToolTip(selection_description(current,series)+'\n'+description(current))
                self.display_note.setText(selection_description(current,series)+'\n'+description(current))
                self.component_mode.setEnabled(options['quantity']==0)
            else:self.display_note.setText(description(self.result))
            if self.figure._suptitle is not None:self.figure._suptitle.set_wrap(True)
            self.presentation.capture();self.canvas.draw_idle();return
        display=self.normalization.settings()
        advanced=self.advanced.isChecked() and self.result['config'].model!='multisite'
        self.component_mode.setEnabled(not advanced)
        try:
            if self.kind=='maps':
                local=self.result['config'].model=='multisite'
                option=self.map_options()
                if option['edge'] is None:raise ValueError('No saved angular energy is selected')
                if local and option['scope']!='total' and option['group_id'] is None:raise ValueError('No modeled group angular maps were saved')
                presentation.draw_maps(self.figure,self.result,option['edge'],method,self.field.currentData() if advanced else None,display if advanced else None,
                    signal_mode=self.component_mode.currentData(),group_id=option['group_id'],normalization=option['scope'])
                if local:
                    gid=option['group_id'];n=self.result['metadata']['multisite']['selected_atom_count']
                    note=(f'Total Results: mean per selected ionizing atom (N={n}).' if gid is None else
                        f'{gid}: '+('Group Mean per atom (nonadditive).' if option['scope']=='mean' else f'Group Contribution: n/N × group mean (fixed N={n}).'))
                    self.multisite_banner.setText(note)
                    state='reversed configuration' if self.result['metadata']['multisite']['global_reversal'] else 'declared configuration'
                    self.multisite_banner.setToolTip(note+' '+state+(f'; crystal M={self.result["groups"][gid]["metadata"]["magnetization_crystal"]}' if gid is not None else '')+'; minus exchanges all provider pairs.')
            elif self.kind=='diffraction':presentation.draw_diffraction(self.figure,self.result,method,self.choice.currentIndex()==1)
            elif self.kind=='comparison':presentation.draw_comparison(self.figure,self.result,display)
            else:
                relative=advanced and self.component_diagnostic.currentData()=='relative'
                self.proxies=presentation.draw_eels(self.figure,self.result,self.choice.currentText(),method,display if advanced and not relative else None,component_mode='relative' if relative else self.component_mode.currentData(),diagnostics=advanced and not relative,zoom_energy=self.choice.currentData())
            from .component_display import TOOLTIPS
            self.component_mode.setToolTip(TOOLTIPS[self.component_mode.currentData()])
            self.display_note.setText('Display only; simulation arrays unchanged. '+('Explicit advanced diagnostics.' if advanced else TOOLTIPS[self.component_mode.currentData()]))
            if self.kind=='maps' and not advanced:
                note='Full-field mirrored-point EMCD; actual saved qy-reflected samples, independent of detector outlines. Includes possible nonmagnetic diffraction asymmetry.'
                self.component_mode.setToolTip(note);self.display_note.setText(note)
        except (ValueError,KeyError) as exc:
            self.figure.clear();self.figure.subplots().text(.05,.6,'Normalization unavailable: '+str(exc),wrap=True);self.display_note.setText(str(exc));self.figure._emcd_display_metadata=dict(unavailable=str(exc),derived_visualization_only=True)
        if self.kind=='eels' and hasattr(self.owner,'comparison'):self.owner.comparison.setPlainText(presentation.comparison_text(self.result,display.windows))
        if self.kind=='eels':
            selected=self.choice.currentData()
            if selected is None:selected=next((value for _,value in selected_samples(self.result['config']) if np.isfinite(value)),float(self.result['spectra']['energy_ev'][0]))
            self.prb_benchmark.set_context(self.result,method,display.windows,selected)
        if self.figure._suptitle is not None:self.figure._suptitle.set_wrap(True)
        self.presentation.capture()
        self.canvas.draw_idle()
    def update_prb_metadata(self):
        metadata=getattr(self.figure,'_emcd_display_metadata',{})
        metadata['prb_2007_benchmark']=dict(values=self.prb_benchmark.records,undefined=self.prb_benchmark.errors)
        self.figure._emcd_display_metadata=metadata
        records=self.prb_benchmark.records
        text='PRB benchmarks / controls'
        if len(records)==1:
            value=records[0]['prb_relative_dichroism_percent'];energy=records[0]['evaluation_energy_ev']
            if value is not None and energy is not None:text=f'PRB {value:+.4f}% at {energy:.4f} eV'
        self.benchmark_section.header.setText(text);self.benchmark_section.header.setToolTip(self.prb_benchmark.compact_summary.text())
    def export_derived(self):
        from .normalization_export import export_derived
        from pathlib import Path
        from datetime import datetime
        multisite=self.result is not None and self.result['config'].model=='multisite'
        parent=QtWidgets.QFileDialog.getExistingDirectory(self,'Spectra export parent (new folder)' if multisite else 'Derived visualization export parent (new folder)')
        if parent and self.result is not None:
            try:
                if multisite:
                    if self.kind!='eels':
                        from .project_io import save_project
                        state=dict(self.result.get('display_state',{}),angular_selection=self.map_options(),map_signal_mode=self.component_mode.currentData())
                        save_project(dict(self.result,display_state=state),Path(parent)/datetime.now().strftime('multisite_%Y%m%d_%H%M%S_%f'))
                        return
                    from .result_export import export_multisite_spectra
                    export_multisite_spectra(self.result,Path(parent)/datetime.now().strftime('multisite_%Y%m%d_%H%M%S_%f'),
                        method=self.method.currentData() or self.result.get('method','bloch'),**self.multisite_controls.options())
                    return
                if not self.advanced.isChecked() or (self.kind=='eels' and self.component_diagnostic.currentData()=='relative'):
                    from .result_export import export_result
                    export_result(self.result,Path(parent)/datetime.now().strftime('emcd_%Y%m%d_%H%M%S_%f'),component_mode='relative' if self.advanced.isChecked() and self.kind=='eels' else self.owner.eels_view.component_mode.currentData(),map_signal_mode=self.owner.maps_view.component_mode.currentData())
                    return
                from .prb_benchmark import data_origin
                entries=[(name,dict(r,prb_data_origin=data_origin(self.result),prb_project_path=self.result.get('project_path')),name) for name,r in self.result.get('methods',{self.result.get('method','bloch'):self.result}).items()]
                options=self.prb_benchmark.options() if self.kind=='eels' else None
                export_derived(entries,Path(parent)/datetime.now().strftime('derived_%Y%m%d_%H%M%S_%f'),self.normalization.settings(),self.choice.currentText(),prb_options=options)
            except (ValueError,OSError) as exc:self.owner.error(str(exc))
    def pick(self,event):
        for proxy,target in self.proxies:
            if event.artist is proxy:
                lines=target if isinstance(target,tuple) else (target,)
                visible=not any(line.get_visible() for line in lines)
                for line in lines:line.set_visible(visible)
                for artist,other in self.proxies:
                    if other is target:artist.set_alpha(1 if visible else .2)
                self.canvas.draw_idle();return
