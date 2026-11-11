"""Resource presentation only; allocation stays in the existing resource policy."""
from PySide6 import QtCore,QtWidgets


def hardware_text(hw):
    name=hw.get('chip') or f"{hw.get('architecture') or 'CPU'} (model unavailable)"
    cores=f"{hw['logical_cores']} logical cores" if hw.get('logical_cores') else 'Logical core count unavailable'
    if hw.get('performance_cores') is not None and hw.get('efficiency_cores') is not None:
        cores+=f" ({hw['performance_cores']}P + {hw['efficiency_cores']}E)"
    else:cores+='; P/E topology unavailable'
    ram=f"{hw['physical_memory_mib']/1024:g} GiB RAM" if hw.get('physical_memory_mib') else 'Physical RAM unavailable'
    return name+'\n'+cores+' · '+ram


def workers_text(counts):
    return ' · '.join(('BW' if key=='bloch' else 'MS')+f' {value}' for key,value in counts.items())


def memory_text(value):
    return f'{value/1024:.2f} GiB ({value:,} MiB)' if value>=1024 else f'{value:,} MiB'


class ComputeResourcesPanel(QtWidgets.QWidget):
    def __init__(self,w):
        super().__init__();self.owner=w;self.preview=None;self.finalized=None
        keep={w.worker_mode,w.worker_count,w.memory_mode,w.memory_budget,w.memory_label}
        form=w.shared_resources_group.layout()
        while form.rowCount():
            row=form.takeRow(0)
            for item in (row.labelItem,row.fieldItem):
                widget=item.widget() if item is not None else None
                if widget is not None and widget not in keep:widget.hide();widget.deleteLater()
        body=QtWidgets.QVBoxLayout(self);body.setContentsMargins(0,0,0,0);body.setSpacing(8)
        def label(text=''):
            value=QtWidgets.QLabel(text);value.setWordWrap(True);value.setTextFormat(QtCore.Qt.TextFormat.PlainText)
            value.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,QtWidgets.QSizePolicy.Policy.Preferred)
            return value
        self.hardware=label(hardware_text(w.startup_resources.get('hardware',{})));body.addWidget(self.hardware)
        controls=QtWidgets.QFormLayout();controls.setFieldGrowthPolicy(QtWidgets.QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        controls.setRowWrapPolicy(QtWidgets.QFormLayout.RowWrapPolicy.WrapLongRows);controls.setVerticalSpacing(8);body.addLayout(controls)
        w.worker_mode.setItemText(0,'Auto');w.worker_mode.setItemText(1,'Manual')
        w.memory_mode.setItemText(0,'Auto');w.memory_mode.setItemText(1,'Manual')
        controls.addRow('CPU workers',w.worker_mode)
        self.cpu_auto=label('Effective workers: Pending');controls.addRow(self.cpu_auto)
        self.cpu_manual=QtWidgets.QWidget();row=QtWidgets.QHBoxLayout(self.cpu_manual);row.setContentsMargins(0,0,0,0)
        row.addWidget(label('Requested workers'));row.addWidget(w.worker_count,1);controls.addRow(self.cpu_manual)
        controls.addRow('Memory budget',w.memory_mode)
        self.memory_auto=label('Effective budget: Pending');controls.addRow(self.memory_auto)
        self.memory_manual=QtWidgets.QWidget();row=QtWidgets.QHBoxLayout(self.memory_manual);row.setContentsMargins(0,0,0,0)
        row.addWidget(label('Requested budget'))
        self.memory_request=QtWidgets.QSpinBox();self.memory_request.setRange(1,2147483647);self.memory_request.setSuffix(' MiB')
        self.memory_request.setKeyboardTracking(False);row.addWidget(self.memory_request,1);controls.addRow(self.memory_manual)
        w.memory_budget.setParent(self);w.memory_budget.hide()  # Existing saved-value interface.
        title=label('Current calculation estimate');font=title.font();font.setBold(True);title.setFont(font);body.addWidget(title)
        self.estimate=label();body.addWidget(self.estimate)
        self.notice=label();self.notice.hide();body.addWidget(self.notice)
        body.addWidget(w.resource_estimate);w.resource_estimate.header.setText('Resource details')
        form.addRow(self)
        w.worker_mode.currentIndexChanged.connect(self.sync_modes);w.memory_mode.currentIndexChanged.connect(self.sync_modes)
        w.memory_budget.currentIndexChanged.connect(self.sync_modes)
        self.memory_request.valueChanged.connect(self.edit_memory)
        self.sync_modes();self.present(None,None,'Configure and Apply Material / MDFF to estimate resources.')

    def sync_modes(self,*_):
        w=self.owner;cpu_auto=w.worker_mode.currentIndex()==0;memory_auto=w.memory_mode.currentIndex()==0
        self.cpu_auto.setVisible(cpu_auto);self.cpu_manual.setVisible(not cpu_auto)
        self.memory_auto.setVisible(memory_auto);self.memory_manual.setVisible(not memory_auto)
        w.worker_count.setEnabled(not cpu_auto);w.memory_budget.setEnabled(not memory_auto)
        with QtCore.QSignalBlocker(self.memory_request):self.memory_request.setValue(w.memory_budget.currentData())
        self.memory_request.setEnabled(not memory_auto)

    def edit_memory(self,value):
        self.owner.restore_memory_budget(value);self.sync_modes();self.owner.emcd_stale()

    def present(self,cfg,info,reason='',*,final=False):
        self.sync_modes();w=self.owner
        backend=('BW','MS','BW / MS')[w.propagation_box.currentIndex()]+' '+('Single','Double')[w.channeling_box.currentIndex()]+' Channeling'
        if info is None:
            self.cpu_auto.setText('Effective workers: Pending')
            self.memory_auto.setText('Effective budget: Pending')
            status='Unavailable' if cfg is not None else 'Pending'
            self.estimate.setText(f'Backend: {backend}\nEstimated peak memory: Pending\nAdmission: {status}\n'+(reason or 'Complete the scientific configuration.'))
        else:
            counts=info['execution']['effective_workers'];budget=info['memory_budget_mib']
            self.cpu_auto.setText('Effective workers: '+workers_text(counts))
            self.memory_auto.setText('Effective budget: '+memory_text(budget))
            status='Insufficient resources' if info.get('rejected') else 'Unavailable' if reason or info['execution']['blocked'] else 'Ready'
            self.estimate.setText(f'Backend: {backend}\nEstimated peak memory: {info["estimated_process_peak_mib"]:.1f} MiB\nAdmission: {status}'+ (' — finalized at Run' if final else '')+('\n'+reason if reason else ''))
        snapshot=dict(config=cfg,info=info,reason=reason)
        if final:
            old=self.preview;self.finalized=snapshot
            text='Run allocation: '+workers_text(info['execution']['effective_workers'])+' workers; budget '+memory_text(info['memory_budget_mib'])+'.'
            if old and old['info']:
                prior=old['info']
                if prior['execution']['effective_workers']!=info['execution']['effective_workers'] or prior['memory_budget_mib']!=info['memory_budget_mib']:
                    text+=' Refreshed from preview: '+workers_text(prior['execution']['effective_workers'])+f"; {prior['memory_budget_mib']:,} MiB."
                else:text+=' Matches preview.'
            self.run_allocation_text=text
            self.notice.setText(text);self.notice.show()
        else:self.preview=snapshot

    def completed(self,result):
        execution=result['metadata']['execution'];budget=result['config'].memory_budget_mib
        self.notice.setText('Completed run: '+workers_text(execution['effective_workers'])+' workers; budget '+memory_text(budget)+'.\n'+getattr(self,'run_allocation_text',''))
        self.notice.show()
