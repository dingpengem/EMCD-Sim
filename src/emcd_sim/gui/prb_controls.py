"""Compact PRB readout; changing these controls never redraws or runs physics."""
from PySide6 import QtCore, QtWidgets
from .prb_benchmark import benchmark_readout, data_origin, LIMITATION, REFERENCE


class PRBBenchmarkControls(QtWidgets.QGroupBox):
    changed = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__('EMCD Asymmetry', parent)
        self.result = None
        self.records = []
        self.errors = []
        self.context_key = None
        layout = QtWidgets.QVBoxLayout(self)
        row = QtWidgets.QHBoxLayout()
        layout.addLayout(row)
        self.selection = QtWidgets.QComboBox()
        self.selection.addItem('L3 white-line peak (raw A+B)', 'l3-peak')
        self.selection.addItem('Current selected energy', 'selected')
        row.addWidget(self.selection)
        row = QtWidgets.QHBoxLayout()
        layout.addLayout(row)
        row.addWidget(QtWidgets.QLabel('Energy (native eV)'))
        self.energy = QtWidgets.QDoubleSpinBox()
        self.energy.setRange(0, 1e6)
        self.energy.setDecimals(6)
        self.energy.setKeyboardTracking(False)
        row.addWidget(self.energy)
        self.fixed = QtWidgets.QCheckBox('Keep energy across results')
        self.fixed.setToolTip('Use one requested energy across saved thicknesses; never reselect each white-line peak. Exact sampled energy is reported.')
        row.addWidget(self.fixed)
        self.summary = QtWidgets.QLabel('Load or complete a result to evaluate.')
        self.summary.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        toggle = QtWidgets.QToolButton()
        toggle.setText('Diagnostics definitions / Figure 5(c) reference')
        toggle.setCheckable(True)
        layout.addWidget(toggle)
        details = QtWidgets.QLabel('Primary: 100 (A+M − B+M)/(A+M + B+M). No post-edge correction.\n'
            'Diagnostics: 100 (M_A−M_B)/(N_A+N_B) and 100 (N_A−N_B)/(N_A+N_B), from original reversals.\n'
            +REFERENCE+'\n'+LIMITATION)
        details.setWordWrap(True)
        details.hide()
        layout.addWidget(details)
        toggle.toggled.connect(details.setVisible)
        self.selection.currentIndexChanged.connect(self.recompute)
        self.energy.valueChanged.connect(self.recompute)
        self.fixed.toggled.connect(self.fix_energy)
        self.energy.setEnabled(False)

    def set_context(self, result, method, windows, selected_energy):
        self.result, self.method, self.windows = result, method, windows
        key = (id(result), selected_energy)
        if key != self.context_key and not self.fixed.isChecked():
            with QtCore.QSignalBlocker(self.energy):
                self.energy.setValue(selected_energy)
        self.context_key = key
        self.recompute()

    def fix_energy(self, checked):
        if checked:
            current = next((r['evaluation_energy_ev'] for r in self.records if r.get('evaluation_energy_ev') is not None), self.energy.value())
            with QtCore.QSignalBlocker(self.energy):
                self.energy.setValue(current)
            with QtCore.QSignalBlocker(self.selection):
                self.selection.setCurrentIndex(1)
        self.recompute()

    def options(self):
        return dict(selection=self.selection.currentData(),
                    energy_ev=self.energy.value() if self.selection.currentData() == 'selected' else None,
                    origin=data_origin(self.result) if self.result is not None else None,
                    project_path=self.result.get('project_path') if self.result is not None else None)

    def recompute(self, *_):
        self.energy.setEnabled(self.selection.currentData() == 'selected')
        if self.result is None:
            return
        if self.fixed.isChecked() and self.selection.currentData() != 'selected':
            with QtCore.QSignalBlocker(self.selection):
                self.selection.setCurrentIndex(1)
            self.energy.setEnabled(True)
        methods = self.result.get('methods', {self.result.get('method', 'bloch'): self.result})
        chosen = methods if self.method == 'overlay' else {self.method: methods[self.method]} if self.method in methods else {}
        self.records, self.errors = [], []
        lines = []
        fmt = lambda value: 'undefined' if value is None else f'{value:+.4f} %'
        for name, result in chosen.items():
            try:
                from .component_display import readouts
                lines.append(name+' | '+readouts(result)[1])
                record = benchmark_readout(result, windows=self.windows, **self.options())
                record['solver'] = name
                self.records.append(record)
                energy = record['evaluation_energy_ev']
                same=energy is not None and any(abs(energy-v)<1e-9 for v in (result['config'].l3,result['config'].l2))
                lines.append('Evaluation: '+('undefined' if energy is None else f'{energy:.6f} eV')+('' if same else '; EMCD Asymmetry '+fmt(record['prb_relative_dichroism_percent'])))
                if record['undefined_reason']:
                    lines.append('Undefined: '+record['undefined_reason'])
            except (ValueError, KeyError) as exc:
                self.errors.append(dict(solver=name, undefined_reason=str(exc)))
                lines.append(name+': undefined — '+str(exc))
        self.summary.setText('\n'.join(lines) or 'No compatible original detector spectra.')
        self.changed.emit()
