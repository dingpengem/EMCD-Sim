"""Simple/full integrated-strength drafts and real-provider spectral previews."""
import copy
import hashlib
import json
from pathlib import Path
import numpy as np
from ase.data import chemical_symbols, atomic_numbers
from PySide6 import QtCore, QtGui, QtWidgets
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from ..manual_l23 import (simple_strength,simple_parameters,strength_matrix,lorentzian,
    window_fraction,validate_model,document)
from ..mdff_orientation import axis_rotation
from ..imported_mdff import proper_frame
from .atomic_editor_model import edge_references
from .mdff_usability import ManualTensorEditor
from .responsive import CollapsibleSection

ORIGIN_PREFIX='Generic example strengths, FWHM and signed fractions; editable, not measured material properties. '


class FrameDiagram(QtWidgets.QWidget):
    def __init__(self,editor):
        super().__init__();self.editor=editor;self.setMinimumSize(180,90);self.setMaximumHeight(95)

    def paintEvent(self,event):
        p=QtGui.QPainter(self);p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        origin=QtCore.QPointF(self.width()*.4,self.height()*.65)
        try:
            frame=self.editor.frame_value();m=frame[:,2]
            if self.editor.state.currentIndex()==1:m=-m
            beam=getattr(self.editor.window.atomic_editor,'beam_crystal',np.array([0.,0.,1.]))
            beam=beam/np.linalg.norm(beam)
            for vector,label,color,offset in (([1,0,0],'x','#888',0),([0,1,0],'y','#888',0),([0,0,1],'z','#888',0),
                    (beam,'beam','#2166ac',-12),(m,'−M' if self.editor.state.currentIndex()==1 else '+M','#b35806',12)):
                v=np.array(vector);tip=origin+QtCore.QPointF((v[0]+.35*v[2])*42,-(v[1]+.3*v[2])*42)
                p.setPen(QtGui.QPen(QtGui.QColor(color),2));p.drawLine(origin,tip);p.drawEllipse(tip,2,2)
                p.drawText(tip+QtCore.QPointF(4,offset),label)
            p.setPen(QtGui.QColor('#333'));p.drawText(4,14,'Crystal Cartesian frame (schematic)')
        except ValueError:p.drawText(4,30,'Enter a valid direction / proper frame')


class ManualL23Editor(QtWidgets.QWidget):
    invalidated=QtCore.Signal()

    def __init__(self,window):
        super().__init__();self.window=window;self.loading=True;self.drafts={};self.symbol='';self.reference_note=''
        self.snapshot=None;self.is_stale=True;self.numeric_curves=[];self.heatmap_values=None
        self.material_symbols=tuple(sorted(set(window.structure.atoms.get_chemical_symbols())))
        layout=QtWidgets.QVBoxLayout(self);layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        columns=QtWidgets.QHBoxLayout();layout.addLayout(columns)
        basic=QtWidgets.QGroupBox('L2,3 spectral parameters');form=QtWidgets.QFormLayout(basic);form.setRowWrapPolicy(QtWidgets.QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setFormAlignment(QtCore.Qt.AlignmentFlag.AlignTop);form.setVerticalSpacing(4);columns.addWidget(basic,1)
        self.element=QtWidgets.QComboBox()
        for symbol in chemical_symbols[10:]:self.element.addItem(symbol)
        form.addRow('Element',self.element)
        self.reference=QtWidgets.QLabel();self.reference.setWordWrap(True);form.addRow(self.reference)
        self.parameters=QtWidgets.QTableWidget(5,2);self.parameters.setHorizontalHeaderLabels(['L3','L2'])
        self.parameters.setVerticalHeaderLabels(['Peak E (eV)','FWHM Γ (eV)','Transverse A (relative Å²)','Anisotropy r','Signed fraction p'])
        self.parameters.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch);self.parameters.setFixedHeight(186)
        self.fields={}
        tips=('Peak position of the Lorentzian profile. Independent for each edge.',
            'Full width at half maximum, in eV; not Gaussian sigma.',
            'A = N_perp, the integrated transverse tensor strength; trace is A(2+r).',
            'r = N_parallel / N_perp >= 0; no isotropy or branching ratio is imposed.',
            'p = M / N_perp, independently signed at each edge, |p| <= 1. No magnetic moment is inferred.')
        for col,key in enumerate(('L3','L2')):
            for row,name in enumerate(('energy','width','A','r','p')):
                field=QtWidgets.QLineEdit();field.setToolTip(tips[row]);field.setProperty('physical_feature',name);field.installEventFilter(self)
                self.parameters.setCellWidget(row,col,field);self.fields[key,name]=field
                field.textChanged.connect(lambda _,r=row,c=col:self.parameter_changed(r,c))
        form.addRow(self.parameters)
        self.view=QtWidgets.QComboBox();self.view.addItems(['Simple parameters','Full matrices (advanced)']);form.addRow('Strength view',self.view)
        self.representation=QtWidgets.QLabel();self.representation.setWordWrap(True);form.addRow(self.representation)
        self.direction=QtWidgets.QLineEdit('0 0 1');form.addRow('Crystal M direction',self.direction)
        self.frame_mode=QtWidgets.QComboBox();self.frame_mode.addItems(['Verified axis rotation','Explicit proper frame (advanced)']);form.addRow('Model → crystal frame',self.frame_mode)
        self.frame_diagram=FrameDiagram(self);form.addRow(self.frame_diagram)
        reset=QtWidgets.QPushButton('Reset defaults for this element');reset.clicked.connect(self.reset_defaults);form.addRow(reset)
        mapping=QtWidgets.QLabel('N⊥=A, N∥=Ar, M=Ap; A is transverse strength, not trace. Generic examples; phenomenological, not first principles or multiplets.');mapping.setWordWrap(True)
        mapping.setToolTip('Txy=+iM; trace=A(2+r). Widths, strengths and signed fractions are examples, not measured material properties. No universal L3/L2 sign or branching ratio or magnetic-moment interpretation is imposed.')
        form.insertRow(2,mapping)
        self.error=QtWidgets.QLabel();self.error.setWordWrap(True);self.error.setStyleSheet('color:#a12622');form.addRow(self.error)
        preview=QtWidgets.QGroupBox('Preview');p=QtWidgets.QVBoxLayout(preview);p.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop);columns.addWidget(preview,1)
        self.status=QtWidgets.QLabel('Numerical preview not calculated.');self.status.setWordWrap(True);p.addWidget(self.status)
        controls=QtWidgets.QHBoxLayout();p.addLayout(controls)
        self.state=QtWidgets.QComboBox();self.state.addItems(['+M','−M','Even','Odd','Reversal (+M / −M)','Even / odd'])
        self.component=QtWidgets.QComboBox();self.component.addItems(['Txy','Trace/3','Txx','Tyy','Tzz','Txz','Tyz','Tyx','Tzx','Tzy'])
        self.part=QtWidgets.QComboBox();self.part.addItems(['Imaginary','Real','Real and imaginary'])
        for widget in (self.state,self.component,self.part):controls.addWidget(widget);widget.currentIndexChanged.connect(self.draw)
        self.figure=Figure(figsize=(5,3),layout='constrained');self.canvas=FigureCanvasQTAgg(self.figure);self.canvas.setFixedHeight(260);p.addWidget(self.canvas)
        energy_row=QtWidgets.QHBoxLayout();energy_row.addWidget(QtWidgets.QLabel('Heatmaps at E (eV)'))
        self.heat_energy=QtWidgets.QDoubleSpinBox();self.heat_energy.setRange(.001,1e6);self.heat_energy.setDecimals(3);energy_row.addWidget(self.heat_energy);p.addLayout(energy_row)
        self.heat_figure=Figure(figsize=(5,1.6),layout='constrained');self.heat_canvas=FigureCanvasQTAgg(self.heat_figure);self.heat_canvas.setFixedHeight(155);p.addWidget(self.heat_canvas)
        self.coverage=QtWidgets.QLabel();self.coverage.setWordWrap(True);p.addWidget(self.coverage)
        self.advanced=CollapsibleSection('Advanced matrices, proper frame and energy window',expanded=False);layout.addWidget(self.advanced)
        advanced=QtWidgets.QVBoxLayout(self.advanced.body)
        rule=QtWidgets.QLabel('Both matrices are integrated strengths in the model frame (relative Å²). All nine cells stay editable; use 0.2-0.1i or j. Arbitrary valid matrices are retained. Reversal assumption: −M = conjugate(+M) in the fixed model frame, followed by the same proper rotation. Imaginary/off-diagonal is not by itself a general magnetic classification.');rule.setWordWrap(True);advanced.addWidget(rule)
        matrices=QtWidgets.QHBoxLayout();advanced.addLayout(matrices);self.matrices={}
        for edge in ('L3','L2'):
            box=QtWidgets.QGroupBox(edge+' integrated tensor');body=QtWidgets.QVBoxLayout(box)
            matrix=ManualTensorEditor();matrix.note.hide();matrix.canvas.hide();matrix.focus.hide()
            matrix.changed.connect(self.matrix_changed);body.addWidget(matrix);matrices.addWidget(box);self.matrices[edge]=matrix
        grid_form=QtWidgets.QFormLayout();advanced.addLayout(grid_form)
        taken=form.takeRow(self.frame_mode)
        if taken.labelItem:taken.labelItem.widget().hide()
        grid_form.addRow('Model → crystal frame',self.frame_mode)
        self.low=QtWidgets.QLineEdit();self.high=QtWidgets.QLineEdit();self.samples=QtWidgets.QSpinBox();self.samples.setRange(9,2001);self.samples.setValue(401)
        grid_form.addRow('Minimum energy (eV)',self.low);grid_form.addRow('Maximum energy (eV)',self.high);grid_form.addRow('Display source samples (analytic solver evaluation)',self.samples)
        self.frame_table=QtWidgets.QTableWidget(3,3);self.frame_table.setHorizontalHeaderLabels(['model x','model y','model z']);self.frame_table.setVerticalHeaderLabels(['crystal x','crystal y','crystal z']);self.frame_table.setFixedHeight(130)
        self.frame_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        for i in range(3):
            for j in range(3):self.frame_table.setItem(i,j,QtWidgets.QTableWidgetItem(str(int(i==j))))
        grid_form.addRow('Proper model-to-crystal frame',self.frame_table)
        self.direction.textChanged.connect(self.edited);self.frame_mode.currentIndexChanged.connect(self.edited);self.frame_table.itemChanged.connect(self.edited)
        for field in (self.low,self.high):field.textChanged.connect(self.edited)
        self.samples.valueChanged.connect(self.edited);self.heat_energy.valueChanged.connect(self.draw_heatmap)
        self.element.currentTextChanged.connect(self.change_element);self.view.currentIndexChanged.connect(self.change_view)
        self.loading=False
        symbols=set(window.structure.atoms.get_chemical_symbols());symbol=next(iter(symbols)) if len(symbols)==1 else 'Fe'
        if self.element.findText(symbol)<0:symbol='Fe'
        self.element.setCurrentText(symbol)
        if not self.symbol:self.change_element(symbol)
        self.timer=QtCore.QTimer(self);self.timer.setInterval(1000)
        self.timer.timeout.connect(self.check_source_identity);self.timer.start()

    def eventFilter(self,obj,event):
        if event.type()==QtCore.QEvent.Type.FocusIn:
            self.feature=obj.property('physical_feature');self.parameters.setToolTip(obj.toolTip());self.draw()
        return False

    def set_matrix(self,key,matrix):
        table=self.matrices[key].cells
        with QtCore.QSignalBlocker(table):
            for i in range(3):
                for j in range(3):table.item(i,j).setText(str(complex(matrix[i,j])).strip('()'))
        self.matrices[key].edited()

    def draft(self):
        return dict(fields={edge:{name:self.fields[edge,name].text() for name in ('energy','width','A','r','p')} for edge in ('L3','L2')},
            matrices={key:[[widget.cells.item(i,j).text() for j in range(3)] for i in range(3)] for key,widget in self.matrices.items()},
            direction=self.direction.text(),frame_mode=self.frame_mode.currentIndex(),frame=[[self.frame_table.item(i,j).text() for j in range(3)] for i in range(3)],
            low=self.low.text(),high=self.high.text(),samples=self.samples.value(),view=self.view.currentIndex(),reference=self.reference_note)

    def restore_draft(self,draft):
        self.loading=True
        for edge in ('L3','L2'):
            for name,value in draft['fields'][edge].items():self.fields[edge,name].setText(value)
            with QtCore.QSignalBlocker(self.matrices[edge].cells):
                for i in range(3):
                    for j in range(3):self.matrices[edge].cells.item(i,j).setText(draft['matrices'][edge][i][j])
            self.matrices[edge].edited()
        self.direction.setText(draft['direction']);self.frame_mode.setCurrentIndex(draft['frame_mode'])
        for i in range(3):
            for j in range(3):self.frame_table.item(i,j).setText(draft['frame'][i][j])
        self.low.setText(draft['low']);self.high.setText(draft['high']);self.samples.setValue(draft['samples']);self.view.setCurrentIndex(draft['view'])
        self.reference_note=draft['reference'];self.reference.setText(self.reference_note.split(' https://')[0]);self.reference.setToolTip(self.reference_note)
        self.loading=False;self.update_view();self.edited()

    def reset_defaults(self):
        try:refs=edge_references(self.symbol)
        except (ValueError,OSError) as exc:refs={};problem=str(exc)
        else:problem='No bundled elemental edge reference.'
        if refs:
            lo,hi=(refs[k]['energy_ev'] for k in ('L3','L2'));reference='Tabulated elemental peak starting energies; chemical shifts are not predicted. '+refs['L3']['url']
        else:
            lo=max(1.,.4*13.6*(atomic_numbers[self.symbol]-10)**2);hi=lo+max(1.,.02*lo)
            reference=problem+' Synthetic estimated energy scale for this element; replace with sourced peak energies.'
        fields={edge:dict(energy=str(energy),width='1.0',A='1.0',r='1.0',p='0.1' if edge=='L3' else '-0.05') for edge,energy in (('L3',lo),('L2',hi))}
        matrices={edge:[[str(complex(v)).strip('()') for v in row] for row in simple_strength(1,1,.1 if edge=='L3' else -.05)] for edge in ('L3','L2')}
        self.restore_draft(dict(fields=fields,matrices=matrices,direction='0 0 1',frame_mode=0,frame=np.eye(3,dtype=int).astype(str).tolist(),
            low=str(max(.001,lo-25)),high=str(hi+25),samples=401,view=0,reference=reference))
        with QtCore.QSignalBlocker(self.heat_energy):self.heat_energy.setValue(lo)

    def change_element(self,symbol):
        if self.loading:return
        if self.symbol:self.drafts[self.symbol]=self.draft()
        self.symbol=symbol
        if symbol in self.drafts:self.restore_draft(copy.deepcopy(self.drafts[symbol]))
        else:self.reset_defaults()

    def sync_material(self):
        symbols=tuple(sorted(set(self.window.structure.atoms.get_chemical_symbols())))
        if symbols==self.material_symbols or getattr(self.window,'_restoring',False):return
        self.material_symbols=symbols
        if len(symbols)==1 and self.element.findText(symbols[0])>=0:self.element.setCurrentText(symbols[0])

    def parameter_changed(self,row,column):
        if self.loading:return
        if row>=2 and self.view.currentIndex()==0:
            edge=('L3','L2')[column]
            try:
                matrix=simple_strength(*(float(self.fields[edge,name].text()) for name in ('A','r','p')))
                self.loading=True;self.set_matrix(edge,matrix);self.loading=False
            except ValueError as exc:self.error.setText(str(exc))
        self.edited()

    def matrix_changed(self):
        if self.loading:return
        with QtCore.QSignalBlocker(self.view):self.view.setCurrentIndex(1)
        self.update_view();self.edited()

    def update_view(self):
        full=self.view.currentIndex()==1
        general=False
        for edge in ('L3','L2'):
            for name in ('A','r','p'):self.fields[edge,name].setEnabled(not full)
            if full:
                try:values=simple_parameters(self.matrices[edge].matrix())
                except ValueError:values=None
                general=general or values is None
                if not self.simple_controls_match(edge):
                    for key,value in zip(('A','r','p'),values if values is not None else ('N/A','N/A','N/A')):
                        with QtCore.QSignalBlocker(self.fields[edge,key]):self.fields[edge,key].setText(str(value))
        self.representation.setText('General matrix retained: simple A, r, p are unavailable for this edge. No projection is applied.' if general else 'Full matrices are authoritative; simple values are read-only.' if full else '')
        self.representation.setVisible(full)
        if full:self.advanced.setChecked(True)

    def change_view(self,index):
        if self.loading:return
        if index==0:
            try:
                values={key:simple_parameters(widget.matrix()) for key,widget in self.matrices.items()}
                if any(value is None for value in values.values()):raise ValueError('General matrices cannot be represented by A, r, p. Retained unchanged in full matrix mode; no projection was applied.')
                self.loading=True
                for edge,value in values.items():
                    if not self.simple_controls_match(edge):
                        for key,v in zip(('A','r','p'),value):self.fields[edge,key].setText(str(v))
                self.loading=False
            except ValueError as exc:
                with QtCore.QSignalBlocker(self.view):self.view.setCurrentIndex(1)
                self.error.setText(str(exc));self.update_view();return
        self.update_view();self.draw()

    def simple_controls_match(self,edge):
        try:
            current=simple_strength(*(float(self.fields[edge,key].text()) for key in ('A','r','p')))
            return np.array_equal(current,self.matrices[edge].matrix())
        except ValueError:return False

    def frame_value(self):
        if self.frame_mode.currentIndex()==0:
            return axis_rotation([float(v) for v in self.direction.text().replace(',',' ').split()])
        return proper_frame([[float(self.frame_table.item(i,j).text()) for j in range(3)] for i in range(3)])

    def inputs(self):
        edges={}
        for key in ('L3','L2'):
            if self.view.currentIndex()==0:
                # Invalid simple controls must never execute an older valid matrix.
                simple_strength(*(float(self.fields[key,name].text()) for name in ('A','r','p')))
            matrix=self.matrices[key].matrix()
            edges[key]=dict(energy_ev=float(self.fields[key,'energy'].text()),fwhm_ev=float(self.fields[key,'width'].text()),real=matrix.real.tolist(),imag=matrix.imag.tolist())
        model=dict(schema=1,profile='lorentzian_full_real_domain',edges=edges,frame_to_crystal=self.frame_value().tolist(),strength_units='relative_per_atom_angstrom^2',
            origin=ORIGIN_PREFIX+self.reference_note)
        validate_model(model);lo,hi=float(self.low.text()),float(self.high.text())
        if not np.isfinite([lo,hi]).all() or not 0<lo<=edges['L3']['energy_ev']<edges['L2']['energy_ev']<=hi:raise ValueError('Positive energy window must contain both ascending L3 and L2 peaks')
        energy=np.unique(np.r_[np.linspace(lo,hi,self.samples.value()),edges['L3']['energy_ev'],edges['L2']['energy_ev']])
        return model,energy

    def document(self):
        model,energy=self.inputs();drafts=copy.deepcopy(self.drafts);drafts[self.symbol]=self.draft()
        return document(self.symbol,model,energy,dict(view='full' if self.view.currentIndex() else 'simple',drafts=drafts))

    def load_source(self,source):
        d=source.metadata;model=d['manual_l23_model'];editor=d['manual_l23_editor'];self.drafts=copy.deepcopy(editor['drafts'])
        with QtCore.QSignalBlocker(self.element):self.element.setCurrentText(d['element'])
        self.symbol=d['element'];fields={};matrices={};representable=True
        for edge in ('L3','L2'):
            value=model['edges'][edge];matrix=np.asarray(value['real'])+1j*np.asarray(value['imag']);simple=simple_parameters(matrix)
            if simple is None:representable=False;simple=(0,1,0)
            fields[edge]=dict(energy=str(value['energy_ev']),width=str(value['fwhm_ev']),**{key:str(v) for key,v in zip(('A','r','p'),simple)})
            try:
                saved_fields=editor['drafts'][self.symbol]['fields'][edge]
                if np.array_equal(simple_strength(*(float(saved_fields[key]) for key in ('A','r','p'))),matrix):
                    for key in ('A','r','p'):fields[edge][key]=saved_fields[key]
            except (ValueError,TypeError,KeyError):pass
            matrices[edge]=[[str(complex(v)).strip('()') for v in row] for row in matrix]
        frame=np.array(model['frame_to_crystal']);axis=frame[:,2]
        saved_count=editor['drafts'].get(self.symbol,{}).get('samples',401)
        if type(saved_count) is not int or not 9<=saved_count<=2001:saved_count=401
        saved=editor['drafts'].get(self.symbol,{})
        direction=' '.join(map(str,axis));frame_mode=1
        if saved.get('frame_mode')==0:
            try:
                candidate=saved['direction'];computed=axis_rotation([float(v) for v in candidate.replace(',',' ').split()])
                if np.array_equal(computed,frame):direction=candidate;frame_mode=0
            except (KeyError,ValueError,TypeError):pass
        self.restore_draft(dict(fields=fields,matrices=matrices,direction=direction,frame_mode=frame_mode,frame=frame.astype(str).tolist(),
            low=str(source.energy_ev[0]),high=str(source.energy_ev[-1]),samples=saved_count,
            view=1 if editor['view']=='full' or not representable else 0,reference=model['origin'].removeprefix(ORIGIN_PREFIX)))
        self.snapshot=None;self.is_stale=True
        with QtCore.QSignalBlocker(self.heat_energy):self.heat_energy.setValue(model['edges']['L3']['energy_ev'])

    def fingerprint(self):
        model,energy=self.inputs()
        return json.dumps(dict(element=self.symbol,model=model,bounds=energy[[0,-1]].tolist(),samples=self.samples.value()),sort_keys=True,allow_nan=False)

    def edited(self,*_):
        if self.loading:return
        explicit=self.frame_mode.currentIndex()==1;self.direction.setReadOnly(explicit)
        self.direction.setToolTip('Derived from the explicit proper frame. Switch to verified axis rotation in Advanced to edit the direction.' if explicit else 'Three crystal Cartesian components; the verified axis rotation sets a rigid model frame.')
        if explicit:
            try:
                frame=self.frame_value()
                with QtCore.QSignalBlocker(self.direction):self.direction.setText(' '.join(map(str,frame[:,2])))
            except ValueError:pass
        self.is_stale=True;self.status.setText('STALE numerical tensor — update preview for current draft.')
        try:self.inputs();self.error.clear()
        except (ValueError,TypeError) as exc:self.error.setText(str(exc))
        self.invalidated.emit();self.draw()

    def update_preview(self,source):
        self.snapshot=dict(source=source,fingerprint=self.fingerprint());self.is_stale=False
        self.status.setText('CURRENT provider-evaluated tensor density (relative Å²/eV). Profiles and integrated strengths are applied once.')
        self.heat_energy.setRange(float(source.energy_ev[0]),float(source.energy_ev[-1]));self.draw()

    def check_source_identity(self):
        if not self.isVisible() or not self.snapshot or self.is_stale:return
        source=self.snapshot['source']
        try:matches=hashlib.sha256(Path(source.path).read_bytes()).hexdigest()==source.sha256
        except OSError:matches=False
        if not matches:
            self.is_stale=True;self.status.setText('STALE — authenticated model source is missing or changed; numerical preview cannot be current.');self.draw()

    def states(self,source,energy):
        a,b=[value.tensor_angstrom2_per_ev for value in source.tensors(energy,np.eye(3),source.metadata['magnetization_crystal'])]
        return {'+M':a,'−M':b,'Even':(a+b)/2,'Odd':(a-b)/2}

    def draw(self,*_):
        if self.loading:return
        self.frame_diagram.update();self.figure.clear();profile,tensor=self.figure.subplots(2,1);self.numeric_curves=[]
        try:
            model,energy=self.inputs()
            for key,color in (('L3','#2166ac'),('L2','#b35806')):
                edge=model['edges'][key];y=lorentzian(energy,edge['energy_ev'],edge['fwhm_ev'])
                profile.plot(energy,y,label=key+' unit-area profile',color=color)
                peak=edge['energy_ev'];height=1/(np.pi*edge['fwhm_ev'])
                profile.annotate('',xy=(peak-edge['fwhm_ev']/2,height),xytext=(peak+edge['fwhm_ev']/2,height),arrowprops=dict(arrowstyle='<->',color='#e69500' if getattr(self,'feature','')=='width' else color))
                profile.axvline(peak,ls=':',color='#e69500' if getattr(self,'feature','')=='energy' else color)
            fractions=[window_fraction(energy[0],energy[-1],model['edges'][key]['energy_ev'],model['edges'][key]['fwhm_ev']) for key in ('L3','L2')]
            self.coverage.setText('Full-domain unit area; never window-renormalized. Window retains L3 %.2f%% / L2 %.2f%%; tails outside it are omitted.'%tuple(100*v for v in fractions))
        except (ValueError,TypeError):profile.text(.1,.5,'Complete valid profile / frame inputs')
        profile.set(title='Live normalized profiles (schematic)',ylabel='Profile (1/eV)')
        if profile.lines:profile.legend(fontsize=7,ncol=2)
        if self.snapshot:
            source=self.snapshot['source'];states=self.states(source,source.energy_ev);selected=self.state.currentText()
            names=('+M','−M') if selected.startswith('Reversal') else ('Even','Odd') if selected=='Even / odd' else (selected,)
            component=self.component.currentText()
            for name in names:
                values=states[name];y=np.trace(values,axis1=-2,axis2=-1)/3 if component=='Trace/3' else values[:,'xyz'.index(component[1]),'xyz'.index(component[2])]
                for part in (('Real','Imaginary') if self.part.currentIndex()==2 else (self.part.currentText(),)):
                    values=y.real if part=='Real' else y.imag;label=name+' '+part+' '+component;self.numeric_curves.append((label,values.copy()));tensor.plot(source.energy_ev,values,label=label)
            tensor.legend(fontsize=7,ncol=2)
        else:tensor.text(.1,.5,'Update numerical preview to evaluate the provider')
        tensor.set(title=('STALE — ' if self.is_stale else '')+'Provider tensor density (crystal)',ylabel='Tensor (Å²/eV)',xlabel='Energy loss (eV)')
        self.canvas.draw_idle();self.draw_heatmap()

    def draw_heatmap(self,*_):
        if self.loading:return
        self.heat_figure.clear();self.heatmap_values=None
        if self.snapshot:
            source=self.snapshot['source'];energy=self.heat_energy.value()
            if source.energy_ev[0]<=energy<=source.energy_ev[-1]:
                name=self.state.currentText();name='+M' if name.startswith('Reversal') else 'Even' if name=='Even / odd' else name
                value=self.states(source,np.array([energy]))[name][0];self.heatmap_values=value.copy()
                for ax,part,title in zip(self.heat_figure.subplots(1,2),(value.real,value.imag),('Real','Imaginary')):
                    limit=max(float(abs(part).max()),1e-300);ax.imshow(part,cmap='RdBu_r',vmin=-limit,vmax=limit)
                    ax.set(xticks=range(3),yticks=range(3),xticklabels=list('xyz'),yticklabels=list('xyz'),title=('STALE ' if self.is_stale else '')+title+' '+name)
        self.heat_canvas.draw_idle()
