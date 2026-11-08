"""Compact selection of already-calculated site/element spectra."""
from pathlib import Path
from PySide6 import QtCore,QtWidgets
from .multisite_results import QUANTITIES


class MultisiteSpectraControls(QtWidgets.QWidget):
    changed = QtCore.Signal()

    def __init__(self):
        super().__init__();self.result = None
        layout = QtWidgets.QVBoxLayout(self);layout.setContentsMargins(0,0,0,0);layout.setSpacing(3)
        row = QtWidgets.QHBoxLayout();layout.addLayout(row)
        self.selection = QtWidgets.QComboBox();row.addWidget(self.selection,1)
        self.normalization = QtWidgets.QComboBox();self.normalization.addItems(['Group Contribution (n/N, additive)','Group Mean (per atom, nonadditive)'])
        layout.addWidget(self.normalization)
        self.normalization.setToolTip('Weighted group/element curves use the total selected-atom denominator. Group means are diagnostic and not additive.')
        self.quantity = QtWidgets.QComboBox()
        for label,_ in QUANTITIES:self.quantity.addItem(label)
        from .multisite_export import DEFINITIONS
        from .multisite_results import PANELS
        for i,(_,fields) in enumerate(QUANTITIES):
            fields=fields or [field for _,panel in PANELS for field in panel]
            text='\n'.join(key+': '+DEFINITIONS[key] for key,_ in fields)
            self.quantity.setItemData(i,text+'\nThe active ±M configuration and its simultaneous global reversal are complete provider states.',QtCore.Qt.ItemDataRole.ToolTipRole)
        row.addWidget(self.quantity,1)
        self.groups = QtWidgets.QListWidget();self.groups.setMaximumHeight(78);layout.addWidget(self.groups)
        self.include_total = QtWidgets.QCheckBox('Include total spectrum');layout.addWidget(self.include_total)
        self.include_total.setToolTip('Overlay the normalized total. Group means remain nonadditive; weighted groups use the total denominator.')
        self.include_total.toggled.connect(self.updated)
        self.sources = QtWidgets.QLabel();self.sources.setWordWrap(True)
        self.sources.setTextFormat(QtCore.Qt.TextFormat.PlainText);layout.addWidget(self.sources)
        for box in (self.selection,self.normalization,self.quantity):
            box.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            box.setMinimumContentsLength(12)
            box.currentIndexChanged.connect(self.updated)
        self.groups.itemChanged.connect(self.updated)

    def set_result(self, result):
        fresh=result is not self.result
        self.result = result;previous = None if fresh else self.selection.currentData()
        checked = {self.groups.item(i).data(QtCore.Qt.ItemDataRole.UserRole) for i in range(self.groups.count())
                   if self.groups.item(i).checkState() == QtCore.Qt.CheckState.Checked}
        with QtCore.QSignalBlocker(self),QtCore.QSignalBlocker(self.selection),QtCore.QSignalBlocker(self.groups):
            if fresh:
                self.normalization.setCurrentIndex(0);self.include_total.setChecked(False);checked=set()
            self.selection.clear();self.selection.addItem('Total Results',('total',None))
            for element in dict.fromkeys(g['metadata']['element'] for g in result['groups'].values()):
                self.selection.addItem('Element: '+element+' (all groups)',('element',element))
            self.groups.clear()
            for gid,entry in result['groups'].items():
                meta = entry['metadata'];source = meta['source'];label = f'{gid} · {meta["element"]} {source["edge"]}'
                excluded = result['metadata']['multisite']['channels'][gid]['omitted_by_request']
                if excluded:label += ' (excluded)'
                self.selection.addItem('Group: '+label,('group',gid))
                tooltip = f'{label}\nMDFF: {source.get("provider_identity","imported tensor")}\n{source["path"]}\n{source["source"]}'
                self.selection.setItemData(self.selection.count()-1,tooltip,QtCore.Qt.ItemDataRole.ToolTipRole)
                item = QtWidgets.QListWidgetItem(label);item.setData(QtCore.Qt.ItemDataRole.UserRole,gid)
                item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(QtCore.Qt.CheckState.Checked if not checked or gid in checked else QtCore.Qt.CheckState.Unchecked)
                item.setToolTip(tooltip);self.groups.addItem(item)
            self.selection.addItem('Group Comparison',('compare',None))
            height=max(self.groups.sizeHintForRow(0),self.groups.fontMetrics().height()+4)
            self.groups.setFixedHeight(min(78,self.groups.count()*height+2*self.groups.frameWidth()))
            index = next((i for i in range(self.selection.count()) if previous is not None
                          and tuple(self.selection.itemData(i)) == tuple(previous)),0)
            self.selection.setCurrentIndex(index)
            self.updated()

    def options(self):
        selection = self.selection.currentData() or ('total',None)
        compared = tuple(self.groups.item(i).data(QtCore.Qt.ItemDataRole.UserRole) for i in range(self.groups.count())
                         if self.groups.item(i).checkState() == QtCore.Qt.CheckState.Checked)
        normalization = 'mean' if self.normalization.currentIndex() == 1 and selection[0] in ('group','compare') else 'weighted'
        return dict(selection=selection,normalization=normalization,compared=compared,quantity=self.quantity.currentIndex(),
                    include_total=self.include_total.isChecked() and selection[0]=='compare')

    def updated(self, *_):
        mode,value = self.selection.currentData() or ('total',None)
        self.groups.setVisible(mode == 'compare');self.normalization.setVisible(mode in ('group','compare'))
        self.include_total.setVisible(mode == 'compare')
        self.normalization.setEnabled(mode in ('group','compare'))
        self.quantity.setToolTip(self.quantity.currentData(QtCore.Qt.ItemDataRole.ToolTipRole) or '')
        if self.result is not None:
            options = self.options()
            ids = ([value] if mode == 'group' else list(options['compared']) if mode == 'compare' else
                   [gid for gid,g in self.result['groups'].items() if mode == 'total' or g['metadata']['element'] == value])
            if options['include_total']:ids = list(self.result['groups'])
            descriptions = [];full = []
            for gid in ids:
                d = self.result['groups'][gid]['metadata'];source = d['source']
                channel = self.result['metadata']['multisite']['channels'][gid]
                status = 'excluded by request' if channel['omitted_by_request'] else 'modeled '+str(channel['modeled_window_ev'])+' eV'
                name = Path(source['path']).name
                if len(name)>24:name = name[:16]+'…'+Path(name).suffix
                descriptions.append(f'{gid}: {d["element"]} {source["edge"]} · MDFF {name}'+(' · EXCLUDED' if channel['omitted_by_request'] else ''))
                full.append(f'{gid} · n={d["multiplicity"]} · {source["path"]}\n{source["source"]}\n{status}')
            structural = set(self.result['model'].elastic.crystal.species)
            ionizing = {g['metadata']['element'] for g in self.result['groups'].values()}
            if structural-ionizing:descriptions.append('No ionizing channel modeled for '+', '.join(sorted(structural-ionizing))+' (elastic structure only).')
            self.sources.setText('; '.join(descriptions));self.sources.setToolTip('\n\n'.join(full))
            self.selection.setToolTip(self.sources.text()+'\n\n'+self.sources.toolTip())
        self.changed.emit()

    def normalization_note(self, result, series):
        """Compact visible caption; full definitions remain in Details/exports."""
        from .multisite_results import selection_description
        mode=self.options()['selection'][0];n=result['metadata']['multisite']['selected_atom_count']
        if mode=='total' or not series:return selection_description(result,series)
        if self.options()['normalization']=='mean':note='Group Mean: per atom within each group (not additive).'
        else:note=('Element Contribution: Σ n × group mean / N' if mode=='element' else 'Group Contribution: n × group mean / N')+f' (fixed N={n}).'
        if self.options()['include_total']:note+=f' Total normalized intensity: mean per selected atom (N={n}).'
        return note
