"""Compact PRB readout; changing these controls never redraws or runs physics."""
from PySide6 import QtCore, QtWidgets
from .prb_benchmark import benchmark_readout, data_origin, LIMITATION, REFERENCE


class PRBBenchmarkControls(QtWidgets.QGroupBox):
    changed = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__('PRB 2007 Benchmark', parent)
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
                record = benchmark_readout(result, windows=self.windows, **self.options())
                record['solver'] = name
                self.records.append(record)
                energy = record['evaluation_energy_ev']
                lines.append(f'{name}: {record["selected_edge"]} relative dichroism: {fmt(record["prb_relative_dichroism_percent"])}; '
                             +('evaluation energy undefined' if energy is None else f'E={energy:.6f} eV'))
                lines.append('Diagnostics only: magnetic '+fmt(record['magnetic_only_percent'])+'; even imbalance '+fmt(record['nonmagnetic_imbalance_percent']))
                if record['undefined_reason']:
                    lines.append('Undefined: '+record['undefined_reason'])
            except (ValueError, KeyError) as exc:
                self.errors.append(dict(solver=name, undefined_reason=str(exc)))
                lines.append(name+': undefined — '+str(exc))
        if self.records:
            r = self.records[0]
            lines.extend([f'Thickness: {r["thickness_nm"]:.1f} nm | {r["accelerating_voltage_kv"]:g} kV',
                          'Diffraction condition: '+r['diffraction_condition'],
                          f'Detector A/B: {r["detector_centres_cycles_per_angstrom"]} cycles/Å; radius {r["aperture_radius_cycles_per_angstrom"]:.7g} cycles/Å',
                          'Comparison: normalization only; not a physical Figure 5 reproduction.'])
            if tuple(r['nominal_zone_axis']) != (0, 0, 1):
                lines.append('Geometry mismatch: current '+str(r['nominal_zone_axis'])+' versus literature [001] systematic-row vicinity.')
        self.summary.setText('\n'.join(lines) or 'No compatible original detector spectra.')
        self.changed.emit()
