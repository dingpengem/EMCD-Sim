"""Compact resource controls; numerical_info owns allocation/admission."""
from PySide6 import QtCore,QtWidgets
from .hardware_resources import hardware_snapshot
from .memory_budget import DEFAULT_BUDGET_MIB
from .parallel_resources import MAX_WORKERS


class ComputeResourcesPanel(QtWidgets.QWidget):
    changed=QtCore.Signal()

    def __init__(self,parent=None):
        super().__init__(parent)
        self.info=None
        form=QtWidgets.QVBoxLayout(self);form.setContentsMargins(0,0,0,0)
        form.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetMinimumSize)
        self.hardware=QtWidgets.QLabel();self.hardware.setWordWrap(True);form.addWidget(self.hardware)
        def controls():
            body=QtWidgets.QWidget();rows=QtWidgets.QFormLayout(body);rows.setContentsMargins(0,0,0,0)
            rows.setRowWrapPolicy(QtWidgets.QFormLayout.RowWrapPolicy.WrapLongRows);form.addWidget(body)
            return rows
        cpu=controls()
        self.worker_mode=QtWidgets.QComboBox();self.worker_mode.addItems(['Auto (recommended)','Manual'])
        self.worker_count=QtWidgets.QSpinBox();self.worker_count.setRange(1,MAX_WORKERS);self.worker_count.setValue(1)
        self.worker_count.setAccessibleName('Requested CPU workers')
        cpu.addRow('CPU Workers',self.worker_mode);cpu.addRow('Requested workers',self.worker_count)
        self.worker_caption=cpu.labelForField(self.worker_count)
        self.workers=QtWidgets.QLabel('Effective workers: Pending');self.workers.setWordWrap(True);form.addWidget(self.workers)
        memory=controls()
        self.memory_mode=QtWidgets.QComboBox();self.memory_mode.addItems(['Auto (recommended)','Manual'])
        self.memory_budget=QtWidgets.QSpinBox();self.memory_budget.setRange(1,2**31-1)
        self.memory_budget.setValue(DEFAULT_BUDGET_MIB);self.memory_budget.setSuffix(' MiB')
        self.memory_budget.setAccessibleName('Requested memory budget (MiB)')
        self.memory_budget.setToolTip('Total process-peak budget. Manual values are never raised automatically; scientific settings are unchanged.')
        memory.addRow('Memory Budget',self.memory_mode);memory.addRow('Requested memory budget',self.memory_budget)
        self.memory_caption=memory.labelForField(self.memory_budget)
        self.budget=QtWidgets.QLabel('Effective memory budget: Pending');self.budget.setWordWrap(True);form.addWidget(self.budget)
        self.estimate=QtWidgets.QLabel('Current Calculation Estimate\nAdmission: Pending')
        self.estimate.setWordWrap(True);form.addWidget(self.estimate)
        self.explanation=QtWidgets.QLabel();self.explanation.setWordWrap(True)
        self.explanation.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse);form.addWidget(self.explanation)
        self.blas=QtWidgets.QLabel();self.blas.setWordWrap(True);form.addWidget(self.blas)
        for widget in (self.worker_mode,self.memory_mode):widget.currentIndexChanged.connect(self._changed)
        for widget in (self.worker_count,self.memory_budget):widget.valueChanged.connect(self.changed)
        self._labels=(self.hardware,self.workers,self.budget,self.estimate,self.explanation,self.blas)
        self._sync();self.refresh_hardware()

    def _fit_labels(self):
        # Nested forms in a scroll area can shrink word-wrapped rows below
        # their height-for-width hint. Reserve the actual readable height.
        for label in self._labels:
            label.setMinimumHeight(max(label.fontMetrics().height(),label.heightForWidth(max(1,label.width()))))

    def resizeEvent(self,event):
        super().resizeEvent(event)
        self._fit_labels()

    def _sync(self):
        for mode,field,label in ((self.worker_mode,self.worker_count,self.worker_caption),
                                 (self.memory_mode,self.memory_budget,self.memory_caption)):
            manual=mode.currentIndex()==1;field.setVisible(manual);label.setVisible(manual);field.setEnabled(manual)

    def _changed(self,*_):self._sync();self.changed.emit()

    def settings(self):
        return dict(worker_mode=('automatic','manual')[self.worker_mode.currentIndex()],parallel_workers=self.worker_count.value(),
            memory_mode=('automatic','manual')[self.memory_mode.currentIndex()],memory_budget_mib=self.memory_budget.value(),
            resource_allocation=None)

    def restore(self,cfg):
        worker=getattr(cfg,'worker_mode','automatic');memory=getattr(cfg,'memory_mode','manual')
        if worker not in ('automatic','manual') or memory not in ('automatic','manual'):
            raise ValueError('Saved resource modes must be Auto or Manual; settings were not replaced')
        for value in (cfg.parallel_workers,cfg.memory_budget_mib):
            if type(value) is not int or not 1<=value<=2**31-1:
                raise ValueError('Saved resource requests must be positive integer values; settings were not clamped')
        with QtCore.QSignalBlocker(self.worker_mode),QtCore.QSignalBlocker(self.worker_count),QtCore.QSignalBlocker(self.memory_mode),QtCore.QSignalBlocker(self.memory_budget):
            self.worker_mode.setCurrentIndex(0 if worker=='automatic' else 1);self.worker_count.setValue(cfg.parallel_workers)
            self.memory_mode.setCurrentIndex(0 if memory=='automatic' else 1);self.memory_budget.setValue(cfg.memory_budget_mib)
        self._sync()

    def refresh_hardware(self,state=None):
        try:
            state=hardware_snapshot() if state is None else state
            cores=state.get('physical_cores');logical=state.get('logical_processors')
            ram=state.get('installed_ram_mib',state.get('total_ram_mib'))
            self.hardware.setText('CPU: '+state.get('cpu_model','Model unavailable')+'\nCPU: '+
                (str(cores)+' physical cores' if cores is not None else 'Physical cores unavailable')+
                ' / '+str(logical)+' available logical processors\nRAM: '+(f'{ram/1024:.1f} GiB installed' if ram is not None else 'Unavailable'))
            details=[]
            if state.get('hybrid'):details.append('Hybrid core classes: '+str(state['efficiency_classes'])+' (higher class = faster core).')
            if state.get('affinity_restricted'):details.append('Process CPU restrictions are applied.')
            details.extend(state.get('notes',[]))
            details.append(f"Available physical RAM: {state['available_ram_mib']:.1f} MiB; process RSS: {state['process_rss_mib']:.1f} MiB.")
            if 'commit_available_mib' in state:details.append(f"Available process commit: {state['commit_available_mib']:.1f} MiB.")
            self.hardware.setToolTip('\n'.join(details))
        except (OSError,ValueError,KeyError) as exc:
            self.hardware.setText('Hardware/resource measurement unavailable: '+str(exc))
        self._fit_labels()

    def pending(self,reason):
        self.info=None
        self.refresh_hardware();self.workers.setText('Effective workers: Pending')
        self.budget.setText('Effective memory budget: Pending');self.estimate.setText('Current Calculation Estimate\nAdmission: Pending')
        self.explanation.setText(str(reason));self.blas.clear()
        self._fit_labels()

    def show_estimate(self,cfg,info):
        self.info=info
        self.refresh_hardware(info['hardware'])
        execution=info['execution'];names={'bloch':'BW','fft-multislice':'MS'}
        counts=', '.join(names.get(method,method)+' '+str(value) for method,value in execution['effective_workers'].items())
        self.workers.setText('Effective workers: '+counts)
        budget=info['memory_budget_mib'];self.budget.setText(f'Effective memory budget: {budget} MiB ({budget/1024:.2f} GiB)')
        backend='/'.join(names.get(method,method) for method in execution['effective_workers'])
        admission='Insufficient' if execution['blocked'] else 'Ready'
        self.estimate.setText(f'Current Calculation Estimate\nBackend: {backend} — {cfg.channeling_model.title()}\n'
            f"Beams: {info['bw_beams']}; energies: {info['energy_samples']}; grid: {cfg.grid}×{cfg.grid}\n"
            f"Estimated peak process memory: {info['estimated_process_peak_mib']:.1f} MiB\nAdmission: {admission}")
        if execution['blocked']:explanation=' '.join(execution['messages'])
        elif cfg.channeling_model=='single':explanation='Single Channeling has one outer worker. Scientific sampling is unchanged.'
        else:explanation='Auto considers available cores, detector task size and live memory. More workers are not always faster.'
        self.explanation.setText(explanation)
        self.explanation.setToolTip('\n'.join(execution['messages'])+'\n'+info['memory_note']+
            f"\nCurrent RSS: {info['process_rss_mib']:.1f} MiB; additional allocation: {info['additional_allocation_mib']:.1f} MiB.")
        native=execution['native'];runtimes=native.get('runtimes',[])
        counts=', '.join(str(row['threads']) for row in runtimes) if runtimes else str(native.get('threads') or 'Unavailable')
        self.blas.setText('BLAS: '+('1 thread per runtime during Run (verified on entry).' if native.get('automatic_thread_control') else 'Automatic control unavailable; review admission.')+' Current: '+counts+'.')
        self.blas.setToolTip('GUI thread, calculation QThread and outer detector workers are distinct from native BLAS threads.\n'+str(runtimes))
        self._fit_labels()
