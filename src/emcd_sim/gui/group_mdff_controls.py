"""Native energy-selection controls for the group MDFF dialog (no physics)."""
import numpy as np
from PySide6 import QtCore, QtWidgets


class EnergySpinBox(QtWidgets.QDoubleSpinBox):
    def textFromValue(self, value):
        return f'{value:.12f}'.rstrip('0').rstrip('.')


def energy_box(value=1.):
    box = EnergySpinBox();box.setRange(.001,1e6);box.setDecimals(12);box.setValue(value)
    return box


class EdgeSelections(QtWidgets.QWidget):
    changed = QtCore.Signal()

    def __init__(self):
        super().__init__();self.loading = False
        layout = QtWidgets.QVBoxLayout(self);layout.setContentsMargins(0,0,0,0)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,QtWidgets.QSizePolicy.Policy.Maximum)
        self.table = QtWidgets.QTableWidget(0,2);self.table.setHorizontalHeaderLabels(['Edge','Energy (eV)'])
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.setMaximumHeight(120);layout.addWidget(self.table)
        row = QtWidgets.QHBoxLayout();layout.addLayout(row)
        for label,action in [('Add edge',lambda:self.add('K',1.)),('Remove edge',self.remove)]:
            button = QtWidgets.QPushButton(label);row.addWidget(button);button.clicked.connect(action)
        self.table.itemChanged.connect(self.emit_changed)

    def emit_changed(self, *_):
        if not self.loading:self.changed.emit()

    def add(self, name, value):
        previous = self.loading;self.loading = True
        row = self.table.rowCount();self.table.insertRow(row)
        self.table.setItem(row,0,QtWidgets.QTableWidgetItem(name))
        box = energy_box(value);self.table.setCellWidget(row,1,box)
        box.valueChanged.connect(self.emit_changed);self.loading = previous;self.emit_changed()

    def remove(self):
        if self.table.currentRow() >= 0:self.table.removeRow(self.table.currentRow());self.emit_changed()

    def rows(self):
        return [(self.table.item(i,0).text(),self.table.cellWidget(i,1).value()) for i in range(self.table.rowCount())]

    def set_rows(self, rows):
        self.loading = True;self.table.setRowCount(0)
        for name,value in rows:self.add(name,value)
        self.loading = False;self.changed.emit()

    def selected(self):
        rows = self.rows()
        if not rows or len({name for name,_ in rows}) != len(rows):raise ValueError('Select unique named core edges')
        return dict(rows)


class EnergySelection(QtWidgets.QWidget):
    changed = QtCore.Signal()

    def __init__(self, low=700., high=740., native=False):
        super().__init__();self.native = native;self.loading = False
        layout = QtWidgets.QFormLayout(self);layout.setContentsMargins(0,0,0,0)
        layout.setFormAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,QtWidgets.QSizePolicy.Policy.Maximum)
        self.source_bounds = QtWidgets.QCheckBox('Use full validated source coverage');self.source_bounds.setChecked(native)
        if native:layout.addRow(self.source_bounds)
        self.low = energy_box(low);self.high = energy_box(high)
        row = QtWidgets.QWidget();bar = QtWidgets.QHBoxLayout(row);bar.setContentsMargins(0,0,0,0)
        for label,widget in [('Min (eV)',self.low),('Max (eV)',self.high)]:bar.addWidget(QtWidgets.QLabel(label));bar.addWidget(widget)
        layout.addRow(row)
        self.kind = QtWidgets.QComboBox()
        self.kind.addItems((['Native source samples'] if native else [])+['Uniform samples','Selected energies'])
        layout.addRow('Sampling',self.kind)
        self.count = QtWidgets.QSpinBox();self.count.setRange(2,4096);self.count.setValue(9)
        layout.addRow('Number of samples',self.count)
        self.custom = QtWidgets.QWidget();custom_layout = QtWidgets.QVBoxLayout(self.custom);custom_layout.setContentsMargins(0,0,0,0)
        self.table = QtWidgets.QTableWidget(0,1);self.table.setHorizontalHeaderLabels(['Energy (eV), ascending order'])
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.setMaximumHeight(100);custom_layout.addWidget(self.table)
        buttons = QtWidgets.QHBoxLayout();custom_layout.addLayout(buttons)
        for label,action in [('Add energy',lambda:self.add_energy(self.low.value())),('Remove energy',self.remove_energy)]:
            button = QtWidgets.QPushButton(label);buttons.addWidget(button);button.clicked.connect(action)
        layout.addRow(self.custom)
        for box in (self.low,self.high,self.count):box.valueChanged.connect(self.emit_changed)
        self.kind.currentIndexChanged.connect(self.refresh);self.source_bounds.toggled.connect(self.refresh)
        self.refresh()

    def emit_changed(self, *_):
        if not self.loading:self.changed.emit()

    def refresh(self, *_):
        automatic = self.native and self.source_bounds.isChecked()
        self.low.setEnabled(not automatic);self.high.setEnabled(not automatic)
        self.count.setVisible(self.kind.currentText() == 'Uniform samples')
        self.layout().labelForField(self.count).setVisible(self.count.isVisibleTo(self))
        self.custom.setVisible(self.kind.currentText() == 'Selected energies');self.emit_changed()

    def add_energy(self, value):
        row = self.table.rowCount();self.table.insertRow(row);box = energy_box(value)
        self.table.setCellWidget(row,0,box);box.valueChanged.connect(self.emit_changed);self.emit_changed()

    def remove_energy(self):
        if self.table.currentRow() >= 0:self.table.removeRow(self.table.currentRow());self.emit_changed()

    def state(self):
        return dict(low=self.low.value(),high=self.high.value(),kind=self.kind.currentIndex(),count=self.count.value(),
            automatic=self.source_bounds.isChecked(),energies=[self.table.cellWidget(i,0).value() for i in range(self.table.rowCount())])

    def restore(self, state):
        self.loading = True
        self.low.setValue(state['low']);self.high.setValue(state['high']);self.count.setValue(state['count'])
        self.kind.setCurrentIndex(state['kind']);self.source_bounds.setChecked(state['automatic'])
        self.table.setRowCount(0)
        for energy in state['energies']:self.add_energy(energy)
        self.loading = False;self.refresh()

    def values(self, source_energy=None):
        bounds = ((float(source_energy[0]),float(source_energy[-1])) if self.native and self.source_bounds.isChecked()
                  else (self.low.value(),self.high.value()))
        if bounds[0] > bounds[1]:raise ValueError('Require ascending energy bounds')
        mode = self.kind.currentText()
        if mode == 'Native source samples':
            samples = np.unique(np.r_[bounds,source_energy[(source_energy>=bounds[0]) & (source_energy<=bounds[1])]])
        elif mode == 'Uniform samples':samples = np.linspace(*bounds,self.count.value())
        else:samples = [self.table.cellWidget(i,0).value() for i in range(self.table.rowCount())]
        return bounds,tuple(samples)
