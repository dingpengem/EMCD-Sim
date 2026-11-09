"""Source and tensor views using the calculation pipeline's MDFF provider."""
import hashlib
import io
from pathlib import Path
import numpy as np
from PySide6 import QtCore, QtWidgets
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from .responsive import CollapsibleSection


class XMCDPreview(QtWidgets.QGroupBox):
    COMPONENTS=('Txy','Txx','Tyy','Tzz','Txz','Tyz','Tyx','Tzx','Tzy','Trace/3')

    def __init__(self, window):
        super().__init__('Preview — source data and provider tensor')
        self.window=window;self.snapshot=None;self.input_snapshot=None;self.is_stale=True;self.curves=[]
        layout=QtWidgets.QVBoxLayout(self);layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.status=QtWidgets.QLabel('Select and validate the XAS/XMCD source in the main XMCD input.');self.status.setWordWrap(True);layout.addWidget(self.status)
        row=QtWidgets.QHBoxLayout();layout.addLayout(row)
        update=QtWidgets.QPushButton('Update preview');update.clicked.connect(self.update_preview);row.addWidget(update)
        self.state=QtWidgets.QComboBox();self.state.addItems(['+M','−M','Even','Odd','Reversal (+M / −M)','Even / odd'])
        self.component=QtWidgets.QComboBox();self.component.addItems(self.COMPONENTS)
        self.part=QtWidgets.QComboBox();self.part.addItems(['Real and imaginary','Real','Imaginary'])
        bar=QtWidgets.QHBoxLayout();layout.addLayout(bar)
        for label,box in (('State',self.state),('Component',self.component),('Part',self.part)):
            column=QtWidgets.QVBoxLayout();column.addWidget(QtWidgets.QLabel(label));column.addWidget(box);bar.addLayout(column)
            box.currentIndexChanged.connect(self.draw)
        self.figure=Figure(figsize=(5,4),layout='constrained');self.canvas=FigureCanvasQTAgg(self.figure);self.canvas.setFixedHeight(315);layout.addWidget(self.canvas)
        self.identity=QtWidgets.QLabel('Crystal Cartesian components. Input spectra and calculated tensor values have different scales.');self.identity.setWordWrap(True);layout.addWidget(self.identity)
        note=QtWidgets.QLabel('Effective axisymmetric model; not full ab-initio MDFF. Even/odd compare +M and −M.');note.setWordWrap(True);layout.addWidget(note)
        note.setToolTip('Even = (+M + −M)/2; odd = (+M − −M)/2. Off-diagonal entries alone do not define magnetic oddness.')
        self.timer=QtCore.QTimer(self);self.timer.setInterval(1000)
        self.timer.timeout.connect(lambda:self.invalidate_if_changed() if self.isVisible() else None);self.timer.start()
        self.draw()

    def fingerprint(self):
        w=self.window
        path=w.source_path.text()
        try:digest=hashlib.sha256(Path(path).read_bytes()).hexdigest()
        except (OSError,ValueError):digest='missing'
        try:axis=tuple(w.material_direction())
        except (ValueError,TypeError):axis='invalid Material direction'
        return (path,digest,w.validated_path,(w.source_info or {}).get('sha256'),axis,w.source_conventions_confirmed(),
            w.explicit_xmcd.isChecked(),tuple(w.spin[k].value() for k in ('eta','beta','xl3','xl2')),
            tuple(field.text() for field in (w.xmcd_element,w.xmcd_edge,w.xmcd_selected,w.xmcd_provenance,w.xmcd_validity,w.xmcd_scale)),
            w.xmcd_status.currentText(),tuple(w.structure.atoms.get_chemical_symbols()))

    def invalidate_if_changed(self):
        if self.snapshot is not None and self.fingerprint()!=self.snapshot['fingerprint']:
            if not self.is_stale:
                self.is_stale=True
                self.status.setText('STALE numerical preview — source, declarations or tensor settings changed. Update preview; previous curves are a snapshot.')
                self.draw()

    def update_preview(self):
        w=self.window
        self.snapshot=None;self.input_snapshot=None
        try:
            from .emcd_forward import ForwardSettings
            from ..wien2k_xmcd import load_wien2k_xmcd
            from ..mdff_providers import prepare_provider
            start=self.fingerprint()
            if not w.source_info or w.validated_path!=w.source_path.text():
                raise ValueError('Select and validate a matching five-column XAS/XMCD source in this editing context.')
            source=load_wien2k_xmcd(w.source_path.text())
            if source.source_sha256!=w.source_info['sha256']:raise ValueError('Source checksum changed. Validate the selected source again.')
            raw=Path(w.source_path.text()).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=source.source_sha256:raise ValueError('Source checksum changed during input loading.')
            input_columns=np.loadtxt(io.BytesIO(raw),comments='#',ndmin=2)
            self.input_snapshot=dict(energy=source.energy_ev.copy(),input_columns=input_columns.copy())
            axis=w.material_direction()
            base=ForwardSettings(model='xmcd',source=w.source_path.text(),source_sha256=source.source_sha256,
                magnetization=axis,axis_declared=w.source_conventions_confirmed(),eta=w.spin['eta'].value(),beta=w.spin['beta'].value(),
                l3=w.spin['xl3'].value(),l2=w.spin['xl2'].value())
            if not base.axis_declared:raise ValueError('Acknowledge this context\'s source conventions and native edge assignments before tensor preview. Material target M is set in the 3D Viewer.')
            cfg=w.declared_provider_settings(base)
            provider=prepare_provider(cfg)
            # The historical adapter has no source element field: its existing
            # material gate prevents bundled Ni data being used for another element.
            if not provider.declared:
                reason=provider.material_reason(w.structure)
                if reason:raise ValueError(reason+' Select matching XAS/XMCD data and explicit material declarations.')
            plus,minus=provider.tensors(source.energy_ev,np.eye(3))
            provider.revalidate_source()
            if self.fingerprint()!=start:raise ValueError('Inputs changed during preview; update again.')
            a=plus.tensor_angstrom2_per_ev.copy();b=minus.tensor_angstrom2_per_ev.copy()
            unit='Relative per-atom Å²/eV' if provider.declared else 'Relative effective tensor (source-normalized)'
            self.snapshot=dict(fingerprint=start,config=cfg,energy=source.energy_ev.copy(),input=source,input_columns=input_columns.copy(),
                states={'+M':a,'−M':b,'Even':(a+b)/2,'Odd':(a-b)/2},unit=unit)
            self.is_stale=False
            self.status.setText('CURRENT source data and provider-generated tensor. Display controls select this authenticated snapshot.')
            element=getattr(cfg,'ionizing_element','Ni')
            self.identity.setText(f'{element} | crystal Cartesian x/y/z\n{unit}')
            self.identity.setToolTip(f'Source: {cfg.source}\nSHA256 {source.source_sha256}')
            self.draw()
        except Exception as exc:
            self.is_stale=True
            self.status.setText('Preview unavailable: '+str(exc)+' Check this context\'s Material direction, native edge selections and source declarations. Valid input curves, when available, are source data only.')
            self.draw()

    def draw(self,*_):
        if self.snapshot is not None and self.fingerprint()!=self.snapshot['fingerprint']:
            self.is_stale=True
            if not self.status.text().startswith('Preview unavailable:'):
                self.status.setText('STALE numerical preview — update for current source and settings.')
        self.figure.clear();inputs,tensor=self.figure.subplots(2,1);self.curves=[]
        source=self.snapshot or self.input_snapshot
        if source is not None:
            e=source['energy'];prefix='STALE — ' if self.is_stale and self.snapshot is not None else ''
            for label,column in (('RP (input)',1),('LP (input)',2),('XAS (input: RP + LP)',4),('XMCD (input: RP − LP)',3)):
                inputs.plot(e,source['input_columns'][:,column],label=label)
            inputs.set(title=prefix+'Input source spectra',ylabel='Source intensity (a.u.)');inputs.legend(fontsize=7,ncol=2)
            inputs.set(xlabel='Energy loss (eV)',xlim=(e[0],e[-1]))
        else:
            inputs.text(.5,.5,'Select and validate the source in this XMCD context',ha='center',va='center',transform=inputs.transAxes,wrap=True)
            inputs.set_axis_off()
        if self.snapshot is None:
            tensor.text(.5,.5,'Tensor preview blocked — see the message above.\nComplete this context\'s source, edge, scale and magnetic declarations.',ha='center',va='center',transform=tensor.transAxes,wrap=True)
            tensor.set_axis_off()
        else:
            s=self.snapshot;e=s['energy'];prefix='STALE — ' if self.is_stale else ''
            selected=self.state.currentText()
            states=('+M','−M') if selected.startswith('Reversal') else ('Even','Odd') if selected=='Even / odd' else (selected,)
            name=self.component.currentText()
            for state in states:
                values=s['states'][state]
                v=np.trace(values,axis1=-2,axis2=-1)/3 if name=='Trace/3' else values[:,'xyz'.index(name[1]),'xyz'.index(name[2])]
                for part in (('Real','Imaginary') if self.part.currentIndex()==0 else (self.part.currentText(),)):
                    y=v.real if part=='Real' else v.imag;label=f'{state} {part} {name}'
                    self.curves.append((label,y.copy()));tensor.plot(e,y,label=label)
            tensor.set(title=prefix+'Calculated provider tensor (crystal)',ylabel='Tensor (relative)');tensor.legend(fontsize=7,ncol=2)
            for ax in (inputs,tensor):ax.set(xlabel='Energy loss (eV)',xlim=(e[0],e[-1]))
        self.canvas.draw_idle()


def install_xmcd_preview(window,panel,form):
    """Keep source selection and a preview visible; collapse specialist declarations."""
    inputs=QtWidgets.QGroupBox('XMCD input and main parameters');inputs.setLayout(form)
    form.setRowWrapPolicy(QtWidgets.QFormLayout.RowWrapPolicy.WrapLongRows)
    form.setFormAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
    advanced=CollapsibleSection('Advanced source declarations',expanded=False);detail=QtWidgets.QFormLayout(advanced.body)
    detail.setRowWrapPolicy(QtWidgets.QFormLayout.RowWrapPolicy.WrapLongRows)
    for widget in (window.xmcd_selected,window.xmcd_provenance,window.xmcd_validity,window.xmcd_status):
        taken=form.takeRow(widget)
        if taken.labelItem:detail.addRow(taken.labelItem.widget(),widget)
        else:detail.addRow(widget)
    form.addRow(advanced)
    window.xmcd_preview=XMCDPreview(window)
    layout=QtWidgets.QHBoxLayout(panel);layout.setContentsMargins(0,0,0,0);layout.addWidget(inputs,2);layout.addWidget(window.xmcd_preview,3)
    layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
