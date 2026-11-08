"""Compact editors over the existing authenticated MDFF providers."""
import hashlib
import json
from pathlib import Path
import re
import numpy as np
from PySide6 import QtCore, QtWidgets
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from .responsive import CollapsibleSection


def complex_cell(text):
    value = text.strip().lower().replace('i', 'j')
    if not re.fullmatch(r'[+\-0-9.ej]+', value):
        raise ValueError('Use a real number or a complex number, e.g. 0.2-0.1i')
    try:
        z = complex(value)
    except ValueError as exc:
        raise ValueError('Malformed number: '+text) from exc
    if not np.isfinite([z.real, z.imag]).all():
        raise ValueError('Every entry must be finite')
    return z


class ManualTensorEditor(QtWidgets.QWidget):
    changed = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.external = False
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.note = QtWidgets.QLabel('Constant tensor across the declared energy interval; no peaks or spectral profile are inferred.\nCrystal Cartesian x/y/z; per-atom relative Å²/eV. Initial example: I/3, trace = 1.\nEdit all nine entries: real 0.2 or complex 0.2-0.1i (j also accepted).\nSynthetic reversal assumption: −M = conjugate(+M); even = Re(T), odd = i Im(T). Off-diagonal does not mean magnetic.')
        self.note.setWordWrap(True); self.layout.addWidget(self.note)
        self.note.setMinimumHeight(100);self.note.setMaximumHeight(120)
        self.cells = QtWidgets.QTableWidget(3,3)
        self.cells.setHorizontalHeaderLabels(list('xyz')); self.cells.setVerticalHeaderLabels(list('xyz'))
        self.cells.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.cells.setFixedHeight(135)
        for i in range(3):
            for j in range(3):
                self.cells.setItem(i,j,QtWidgets.QTableWidgetItem('0.3333333333333333' if i==j else '0'))
        self.layout.addWidget(self.cells)
        self.error = QtWidgets.QLabel(); self.error.setWordWrap(True); self.layout.addWidget(self.error)
        self.figure = Figure(figsize=(5,2), layout='constrained'); self.canvas = FigureCanvasQTAgg(self.figure); self.canvas.setFixedHeight(200); self.layout.addWidget(self.canvas)
        self.focus = QtWidgets.QLabel('Select a cell: row a, column b gives T_ab in I = Re Tr(RT).'); self.focus.setWordWrap(True); self.layout.addWidget(self.focus)
        self.focus.setMinimumHeight(42);self.error.setMinimumHeight(42)
        for label in (self.note,self.focus,self.error):label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,QtWidgets.QSizePolicy.Policy.Maximum)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,QtWidgets.QSizePolicy.Policy.Maximum)
        self.cells.currentCellChanged.connect(self.highlight)
        self.cells.itemChanged.connect(self.edited)
        self.edited()

    def matrix(self):
        a = np.empty((3,3),complex)
        for i in range(3):
            for j in range(3):
                try: a[i,j] = complex_cell(self.cells.item(i,j).text())
                except ValueError as exc: raise ValueError(f'{"xyz"[i]}{"xyz"[j]}: {exc}') from exc
        scale = max(float(abs(a).max()), 1e-300)
        if abs(a-a.T.conj()).max() > 1e-10*scale:
            raise ValueError('Tensor must be Hermitian: T_ab = conjugate(T_ba), with real diagonal entries. Both cells remain editable.')
        if np.linalg.eigvalsh(a).min() < -1e-12*scale:
            raise ValueError('Tensor must be positive semidefinite. Adjust entries; no eigenvalues are clipped.')
        return a

    def edited(self, *_):
        self.external = False
        try:
            a = self.matrix(); self.error.setText('Valid Hermitian, positive semidefinite draft.')
            self.error.setStyleSheet('color:#225e42')
            self.figure.clear()
            for ax, values, title in zip(self.figure.subplots(1,2), (a.real,a.imag), ('Real T','Imaginary T')):
                limit=max(float(abs(values).max()),1e-15)
                ax.imshow(values,cmap='RdBu_r',vmin=-limit,vmax=limit)
                ax.set(xticks=range(3),yticks=range(3),xticklabels=list('xyz'),yticklabels=list('xyz'),title=title,xlabel='column',ylabel='row')
                for i in range(3):
                    for j in range(3): ax.text(j,i,f'{values[i,j]:.3g}',ha='center',va='center',color='black',bbox=dict(facecolor='white',alpha=.75,edgecolor='none'))
            self.canvas.draw_idle()
        except ValueError as exc:
            self.error.setStyleSheet('color:#a12622')
            self.error.setText(str(exc)+' Previous valid source retained; this draft cannot calculate.')
            self.figure.suptitle('STALE heatmaps — invalid draft'); self.canvas.draw_idle()
        self.changed.emit()

    def highlight(self, row, col, *_):
        if row>=0 and col>=0:
            self.focus.setText(f'T_{"xyz"[row]}{"xyz"[col]} couples Cartesian {"xyz"[row]} and {"xyz"[col]} dipole components. Magnetic oddness is defined by reversal, not by position in this matrix.')
            from matplotlib.patches import Rectangle
            for ax in self.figure.axes:
                for patch in list(ax.patches):patch.remove()
                ax.add_patch(Rectangle((col-.5,row-.5),1,1,fill=False,edgecolor='#e69500',linewidth=3))
            self.canvas.draw_idle()

    def document(self, element, edge, energies, axis):
        from ..imported_mdff import CONVENTION
        a = self.matrix(); lo,hi=energies
        if not np.isfinite([lo,hi]).all() or not 0<lo<hi: raise ValueError('Require positive ascending L3 / L2 energies')
        energy=[max(.001,lo-10),lo,hi,hi+10]
        def packed(t):
            values=np.repeat(t[None],4,axis=0)
            return dict(real=values.real.tolist(),imag=values.imag.tolist())
        return dict(schema=1,element=element,edge=edge,energy_ev=energy,selected_ev=dict(L3=lo,L2=hi),
            units='angstrom^2/eV',normalization='per_atom_relative',basis='crystal_cartesian',frame_to_crystal=np.eye(3).tolist(),
            magnetic_state='uniform_fm',magnetization_crystal=list(axis),reversal='explicit_pair_shared_even',
            source='Manual constant tensor editor; synthetic editable example; reversal by declared conjugation ansatz',
            validity='Constant within declared interval only; no extrapolation, measured spectrum, or material calibration. Reversal ansatz is an explicit model assumption.',
            status='synthetic',convention=CONVENTION,T_plus=packed(a),T_minus=packed(a.conj()),T_even=packed(a.real),manual_constant_editor=1)

    def persist(self, workspace, document):
        from ..imported_mdff import ImportedMDFF
        raw=(json.dumps(document,sort_keys=True,allow_nan=False)+'\n').encode()
        folder=Path(workspace)/'manual_tensors'; folder.mkdir(parents=True,exist_ok=True)
        path=folder/(hashlib.sha256(raw).hexdigest()+'.json')
        if path.exists():
            if path.read_bytes()!=raw: raise ValueError('Managed source identity mismatch')
        else:
            with path.open('xb') as stream: stream.write(raw)
        return ImportedMDFF.load(path,hashlib.sha256(raw).hexdigest())


class AtomicSchematic(QtWidgets.QWidget):
    def __init__(self, editor):
        super().__init__(editor); self.editor=editor; self.key='l3'
        layout=QtWidgets.QVBoxLayout(self);layout.setContentsMargins(0,0,0,0)
        self.reversal=QtWidgets.QComboBox();self.reversal.addItems(['Show +M','Show −M']);layout.addWidget(self.reversal);self.reversal.currentIndexChanged.connect(self.draw)
        self.figure=Figure(figsize=(5,2.4),layout='constrained');self.canvas=FigureCanvasQTAgg(self.figure);self.canvas.setFixedHeight(225);layout.addWidget(self.canvas)
        self.explain=QtWidgets.QLabel();self.explain.setWordWrap(True);layout.addWidget(self.explain)
        for key,field in editor.fields.items(): field.installEventFilter(self);field.setProperty('physical_key',key)
        for table,key in ((editor.holes,'holes'),(editor.frame,'frame')):
            for row in range(table.rowCount()):
                for col in range(table.columnCount()):
                    widget=table.cellWidget(row,col);widget.setProperty('physical_key',key);widget.installEventFilter(self)

    def eventFilter(self,obj,event):
        if event.type()==QtCore.QEvent.Type.FocusIn:
            self.key=obj.property('physical_key');self.draw()
            if hasattr(self.editor,'hole_figure'):
                for ax in self.editor.hole_figure.axes:
                    for spine in ax.spines.values():spine.set_color('#e69500' if self.key=='holes' else '#333')
                self.editor.hole_canvas.draw_idle()
        return False

    def draw(self,*_):
        from .atomic_editor_help import PLAIN_LANGUAGE
        e=self.editor
        fingerprint=(self.key,self.reversal.currentIndex(),tuple(e.fields[k].text() for k in ('l3','l2','sigma','cf','exchange')),
            repr(e.table_values(e.frame)),repr(getattr(e,'beam_crystal',None)))
        if fingerprint==getattr(self,'_fingerprint',None):return
        self._fingerprint=fingerprint
        self.explain.setText(PLAIN_LANGUAGE.get(self.key,'Rigid local-to-crystal frame sets the magnetization direction.'))
        self.figure.clear();energy,frame=self.figure.subplots(1,2)
        try:
            e=self.editor;lo,hi,sigma=(float(e.fields[k].text()) for k in ('l3','l2','sigma'))
            if not np.isfinite([lo,hi,sigma]).all() or not 0<lo<hi or sigma<=0:raise ValueError()
            x=np.linspace(lo-5*sigma,hi+5*sigma,240)
            energy.plot(x,np.exp(-.5*((x-lo)/sigma)**2),color='#2166ac',label='L3');energy.plot(x,np.exp(-.5*((x-hi)/sigma)**2),color='#b35806',label='L2')
            for v,label in ((lo,'2p3/2 → 3d'),(hi,'2p1/2 → 3d')):
                energy.annotate(label,xy=(v,.9),xytext=(v,.35),rotation=90,ha='center',fontsize=8,arrowprops=dict(arrowstyle='->',color='#d95f02' if self.key in ('l3','l2','sigma') else '#555'))
            energy.set(xlabel='Energy loss (eV)',yticks=[],title=f'Schematic • σ={sigma:g} eV');energy.legend(fontsize=7)
            r=np.array(e.table_values(e.frame),float)
            m=np.array(e.owner.material_direction() if hasattr(e.owner,'material_direction') else r[:,2],float)
            m=m/np.linalg.norm(m)*(1 if self.reversal.currentIndex()==0 else -1)
            # Beam supplied in crystal Cartesian coordinates by the main window.
            beam=getattr(e,'beam_crystal',np.array([0.,0.,1.])); beam=beam/np.linalg.norm(beam)
            project=lambda v:(v[0]+.4*v[2],v[1]+.3*v[2])
            for vector,label,color in (([1,0,0],'x','#888'),([0,1,0],'y','#888'),([0,0,1],'z','#888'),(beam,'beam','#2166ac'),(m,'+M' if self.reversal.currentIndex()==0 else '−M','#b35806')):
                u,v=project(np.array(vector));frame.annotate('',xy=(u,v),xytext=(0,0),arrowprops=dict(arrowstyle='->',color=color))
                offset=.25 if label=='beam' else -.2 if label in ('+M','−M') else 0
                frame.text(u*1.25,v*1.25+offset,label,color=color,fontsize=8)
            angle=np.degrees(np.arccos(np.clip(m@beam/np.linalg.norm(m),-1,1)))
            frame.set(xlim=(-1.4,1.4),ylim=(-1.4,1.4),title=f'Crystal target • M/beam {angle:.1f}°');frame.set_aspect('equal');frame.axis('off')
        except (ValueError,TypeError):energy.text(.1,.5,'Complete valid energies / frame');frame.axis('off')
        self.canvas.draw_idle()


def compact_atomic(editor):
    """Move existing controls without duplicating their scientific state."""
    e=editor
    e.use_editor.setChecked(True);e.use_editor.hide()
    main=QtWidgets.QGroupBox('Main parameters');form=QtWidgets.QFormLayout(main);form.setRowWrapPolicy(QtWidgets.QFormLayout.RowWrapPolicy.WrapLongRows)
    def move(widget,label):
        old=widget.parentWidget().layout()
        if isinstance(old,QtWidgets.QFormLayout):
            taken=old.takeRow(widget)
            if taken.labelItem and taken.labelItem.widget():taken.labelItem.widget().hide()
        elif old:old.removeWidget(widget)
        form.addRow(label,widget)
    move(e.element,'Element');move(e.fields['l3'],'L3 reference (eV)');move(e.fields['l2'],'L2 reference (eV)');move(e.fields['sigma'],'Gaussian σ (eV)')
    e.saved_model_notice=QtWidgets.QLabel();e.saved_model_notice.setWordWrap(True);e.saved_model_notice.hide();form.addRow(e.saved_model_notice)
    e.main_error=QtWidgets.QLabel();e.main_error.setWordWrap(True);e.main_error.setStyleSheet('color:#a12622');form.addRow(e.main_error)
    e.direction=QtWidgets.QLineEdit('0 0 1');e.direction.setReadOnly(True)
    e.direction.setToolTip('Target M is set through Material → 3D Structure Viewer → Site Groups. The complete Atomic orbital/spin frame remains explicit.')
    form.addRow('Material target M (read-only)',e.direction)
    reset=QtWidgets.QPushButton('Reset defaults');reset.clicked.connect(e.reset_defaults);form.addRow(reset)
    notice=QtWidgets.QLabel('Cubic independent-electron 2p → 3d L2,3 model. Elemental edge references + generic synthetic electronic defaults; editable, not a material fit.');notice.setWordWrap(True);form.addRow(notice)
    e.layout.insertWidget(0,main)
    advanced=CollapsibleSection('Advanced parameters',expanded=False);e.advanced_parameters=advanced;advanced_layout=QtWidgets.QVBoxLayout(advanced.body)
    for key,section in e.sections.items():
        e.layout.removeWidget(section);advanced_layout.addWidget(section);section.setChecked(False)
    e.sections['A'].hide()
    e.hole_figure=Figure(figsize=(5,1.5),layout='constrained');e.hole_canvas=FigureCanvasQTAgg(e.hole_figure);e.hole_canvas.setFixedHeight(160)
    e.sections['D'].body.layout().addRow(e.hole_canvas)
    e.layout.addWidget(advanced)
    preview=QtWidgets.QGroupBox('Preview');p=QtWidgets.QVBoxLayout(preview)
    e.schematic=AtomicSchematic(e);p.addWidget(e.schematic)
    e.sections['I'].body.layout().removeWidget(e.preview_button)
    e.preview_button.hide()
    e.layout.addWidget(preview)
    e.preview_state=QtWidgets.QLabel('Numerical spectrum not calculated.');e.preview_state.setWordWrap(True);p.addWidget(e.preview_state)
    e.spectrum_figure=Figure(figsize=(5,1.8),layout='constrained');e.spectrum_canvas=FigureCanvasQTAgg(e.spectrum_figure);e.spectrum_canvas.setFixedHeight(140);p.addWidget(e.spectrum_canvas)
    details=QtWidgets.QPushButton('Detailed components / even and odd');p.addWidget(details)
    details.clicked.connect(lambda: e.preview_dialog.show() if getattr(e,'preview_dialog',None) else e.preview())
    e.schematic.canvas.setFixedHeight(180)
    e.layout.removeWidget(main);e.layout.removeWidget(advanced);e.layout.removeWidget(preview)
    columns=QtWidgets.QWidget();columns_layout=QtWidgets.QHBoxLayout(columns);columns_layout.setContentsMargins(0,0,0,0)
    left=QtWidgets.QWidget();left_layout=QtWidgets.QVBoxLayout(left);left_layout.setContentsMargins(0,0,0,0);left_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
    left_layout.addWidget(main);left_layout.addWidget(advanced)
    columns_layout.addWidget(left,1);columns_layout.addWidget(preview,1);columns_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
    p.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
    main.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,QtWidgets.QSizePolicy.Policy.Maximum)
    advanced.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,QtWidgets.QSizePolicy.Policy.Maximum)
    e.layout.addWidget(columns);e.layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
    for section in e.sections.values():section.body.layout().setFormAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
    e.reset_defaults()


def configuration_dialog(window):
    """Dedicated roomy workspace using the same live provider controls."""
    w=window
    if hasattr(w,'mdff_dialog'):
        w.mdff_dialog.show();w.mdff_dialog.raise_();return
    dialog=QtWidgets.QDialog(w);dialog.setWindowTitle('MDFF configuration');dialog.resize(1120,800)
    outer=QtWidgets.QVBoxLayout(dialog)
    material=QtWidgets.QGroupBox('Material');row=QtWidgets.QHBoxLayout(material)
    button=QtWidgets.QPushButton('Open CIF…');button.clicked.connect(w.load_cif);row.addWidget(button)
    w.mdff_material=QtWidgets.QLabel(w.structure_label.text());w.mdff_material.setWordWrap(True);row.addWidget(w.mdff_material,1);outer.addWidget(material)
    model=QtWidgets.QGroupBox('Model');form=QtWidgets.QFormLayout(model)
    for widget,label in ((w.model_box,'MDFF model'),(w.model_description,'')):
        old=widget.parentWidget().layout()
        if isinstance(old,QtWidgets.QFormLayout):old.takeRow(widget)
        form.addRow(label,widget)
    old=w.axis.parentWidget().layout()
    if isinstance(old,QtWidgets.QFormLayout):old.takeRow(w.axis)
    w.axis.hide()  # Compatibility/restoration mirror, never a second editor.
    w.mdff_material_direction=QtWidgets.QLabel();w.mdff_material_direction.setWordWrap(True)
    form.addRow(w.mdff_material_direction)
    w.magnetization_mode_note=QtWidgets.QLabel();w.magnetization_mode_note.setWordWrap(True)
    form.addRow(w.magnetization_mode_note);w.sync_magnetization_mode()
    outer.addWidget(model)
    old=w.mdff_stack.parentWidget().layout()
    if isinstance(old,QtWidgets.QFormLayout):old.takeRow(w.mdff_stack)
    scroll=QtWidgets.QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(w.mdff_stack);outer.addWidget(scroll,1)
    bar=QtWidgets.QHBoxLayout();outer.addLayout(bar)
    preview=QtWidgets.QPushButton('Update numerical preview');preview.clicked.connect(w.preview_mdff);bar.addWidget(preview)
    run=QtWidgets.QPushButton('Calculate EMCD / EELS');run.clicked.connect(w.start_emcd);bar.addWidget(run)
    close=QtWidgets.QPushButton('Done');close.clicked.connect(dialog.hide);bar.addWidget(close)
    def model_visibility(index):
        w.refresh_material_direction()
        w.model_description.setText((
            'XMCD-constrained tensor: requires a declared XAS/XMCD spectrum and its conventions.',
            'Atomic ionization: approximate cubic 2p to 3d transitions from editable electronic parameters.',
            'Manual tensor: constant coefficients or phenomenological L2,3 spectral strengths.')[index])
    w.mdff_stack.currentChanged.connect(model_visibility);model_visibility(w.model_box.currentIndex())
    w.mdff_refresh_model=model_visibility
    w.manual_model.currentIndexChanged.connect(lambda _:model_visibility(w.model_box.currentIndex()))
    w.mdff_dialog=dialog;w.mdff_scroll=scroll;dialog.show()
