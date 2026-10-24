"""Compact display-only controls shared by live and saved result viewers."""
from .responsive import FlowLayout
from PySide6 import QtWidgets, QtCore
from .signal_normalization import DisplaySettings, MODES, MAP_MODES, default_windows, peak_reference, validate_pair


class NormalizationControls(QtWidgets.QWidget):
    changed=QtCore.Signal()
    def __init__(self,parent,maps=False,saved=False):
        super().__init__(parent);self.result=None;self.saved=saved;self.show_maps=maps
        layout=QtWidgets.QVBoxLayout(self);layout.setContentsMargins(0,0,0,0)
        row=FlowLayout();layout.addLayout(row)
        row.addWidget(QtWidgets.QLabel('Intensity Display'))
        self.mode=QtWidgets.QComboBox()
        for key,title in MODES.items():self.mode.addItem(title,key)
        row.addWidget(self.mode)
        self.peak_edge=QtWidgets.QComboBox()
        for title,key in [('Auto: Full/L3 -> L3; L2 -> L2','Auto'),('Peak reference: L3','L3'),('Peak reference: L2','L2')]:self.peak_edge.addItem(title,key)
        row.addWidget(self.peak_edge)
        self.scope=QtWidgets.QComboBox();self.scope.addItem('Shared reference peak','shared');self.scope.addItem('Per-run peak reference' if saved else 'Per-method peaks (presentation only)','independent');row.addWidget(self.scope)
        self.reference=QtWidgets.QComboBox();row.addWidget(self.reference);self.reference.setVisible(saved)
        maprow=FlowLayout();layout.addLayout(maprow)
        self.map_mode=QtWidgets.QComboBox()
        for key,title in MAP_MODES.items():self.map_mode.addItem(title,key)
        self.map_mode.setVisible(maps);maprow.addWidget(self.map_mode)
        self.scale=QtWidgets.QComboBox();self.scale.addItems(['Shared color scale','Independent color scales']);self.scale.setVisible(maps);maprow.addWidget(self.scale)
        self.mode.setVisible(not maps or saved)
        tip='P_edge = max in selected native-energy window [N_A+N_B], not the mean of detectors. One fixed summed-detector peak for every curve over the entire plot. Asymmetry = 100 D / (N_A+N_B). No background subtraction or energy shift.'
        self.setToolTip(tip);self.scope.setToolTip('Shared peak uses BW when available. Independent peaks can conceal intensity/amplitude differences; raw solver metrics never use them.')
        toggle=QtWidgets.QToolButton();toggle.setText('Peak windows (native eV)');toggle.setCheckable(True);toggle.setVisible(not maps or saved);layout.addWidget(toggle)
        self.advanced=QtWidgets.QWidget();layout.addWidget(self.advanced);self.advanced.hide();toggle.toggled.connect(self.advanced.setVisible)
        form=QtWidgets.QGridLayout(self.advanced);self.windows={}
        for i,edge in enumerate(('L3','L2')):
            form.addWidget(QtWidgets.QLabel(edge+' start / end'),i,0);controls=[]
            for j in (1,2):
                spin=QtWidgets.QDoubleSpinBox();spin.setRange(-1e6,1e6);spin.setDecimals(6);form.addWidget(spin,i,j);spin.valueChanged.connect(lambda *_:self.find_peaks());controls.append(spin)
            self.windows[edge]=controls
        auto=QtWidgets.QPushButton('Auto-detect peaks in windows');reset=QtWidgets.QPushButton('Reset source/model defaults');form.addWidget(auto,2,0,1,2);form.addWidget(reset,2,2)
        self.info=QtWidgets.QLabel();self.info.setWordWrap(True);form.addWidget(self.info,3,0,1,3)
        self.pair_warning=QtWidgets.QLabel();self.pair_warning.setWordWrap(True);layout.addWidget(self.pair_warning)
        auto.clicked.connect(self.find_peaks);reset.clicked.connect(self.reset)
        for control in (self.mode,self.peak_edge,self.scope,self.reference,self.map_mode,self.scale):control.currentIndexChanged.connect(self.updated)
        self.updated()

    def updated(self,*_):
        peak=self.mode.currentData()=='peak';self.peak_edge.setVisible(peak);self.scope.setVisible(peak);self.reference.setVisible(peak and self.saved)
        self.changed.emit()

    def set_result(self,result,labels=None):
        if self.result is result:return
        self.result=result;self.reference.blockSignals(True);self.reference.clear();self.reference.addItems(labels or ['BW when available']);self.reference.blockSignals(False);self.reset()
        try:validate_pair(result,'L3');reason=''
        except ValueError as exc:reason=str(exc)
        self.map_mode.model().item(2).setEnabled(not bool(reason));self.map_mode.model().item(2).setToolTip(reason)
        self.pair_warning.setText(reason if self.show_maps else '')
        if reason and self.map_mode.currentData()=='paired':self.map_mode.setCurrentIndex(0)

    def reset(self):
        if self.result is None:return
        try:
            windows=default_windows(self.result)
            for edge,controls in self.windows.items():
                for control,value in zip(controls,windows[edge]):control.blockSignals(True);control.setValue(value);control.blockSignals(False)
            self.find_peaks()
        except ValueError as exc:self.info.setText(str(exc))
        self.changed.emit()

    def find_peaks(self):
        if self.result is None:return
        try:
            values=[peak_reference(self.result,e,self.settings().windows) for e in ('L3','L2')]
            self.info.setText('; '.join(f"{p['edge']}: P={p['value']:.7g} at {p['peak_energy_ev']:.6g} eV" for p in values))
        except ValueError as exc:self.info.setText('Undefined: '+str(exc))
        self.changed.emit()

    def settings(self):
        return DisplaySettings(mode=self.mode.currentData(),peak_edge=self.peak_edge.currentData(),
            windows={edge:tuple(c.value() for c in controls) for edge,controls in self.windows.items()},
            scope=self.scope.currentData(),reference=max(self.reference.currentIndex(),0),map_mode=self.map_mode.currentData(),shared_scale=self.scale.currentIndex()==0)
