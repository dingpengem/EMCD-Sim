"""Interactive views of validated atomic tensors; no transition generator here."""
import numpy as np
from PySide6 import QtCore,QtWidgets
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg,NavigationToolbar2QT
from ..imported_mdff import ImportedMDFF,CONVENTION,psd_tensor,proper_frame
from .atomic_editor_model import EDITOR_TAG

CONSTRUCTION = '''How Is the MDFF Tensor T(E) Constructed?

1. Transition energies
E_n = E_Lj + Delta_E_CF(orbital) - spin_sign * magnetization_sign * Delta_ex / 2.
eg: +0.6 Delta_CF (two orbitals); t2g: -0.4 Delta_CF (three orbitals).
The degeneracy-weighted orbital-energy centroid is unchanged.

2. Complex Cartesian transition dipoles
d_n = <i|r|f>. The existing generator combines its core 2p SOC states,
Clebsch-Gordan coefficients, real cubic orbital decomposition and radial D.

3. Nonnegative transition weights
h_n is the explicitly declared orbital/spin hole weight, not electron occupancy.

4. Normalized Gaussian broadening
G_sigma(E-E_n) = exp[-(E-E_n)^2/(2 sigma^2)] / (sqrt(2*pi)*sigma).
FWHM = 2*sqrt(2*ln(2))*sigma. No experimental resolution is inferred.

5. Spectral tensor
T_ab(E) = sum_n h_n d_n,a conjugate(d_n,b) G_sigma(E-E_n).
T is a complex Hermitian 3x3 tensor, with relative per-atom Angstrom^2/eV units.
The generator explicitly constructs +M and -M states; no conjugation shortcut.
T_even=(T_plus+T_minus)/2; T_odd=(T_plus-T_minus)/2.
T_plus and T_minus must be PSD. T_odd is a signed response and need not be PSD.
An imaginary off-diagonal component alone is not a definition of magnetic oddness.

6. Connection to the detector calculation
I(E) = Re Tr[R(E) T(E)] = Re sum_ab R_ab(E) T_ba(E).
No additional complex conjugation is introduced. T describes transitions;
R contains dynamical electron propagation and detector geometry. These curves
are tensor components, not final EELS/EMCD detector spectra or an absolute cross section.

Model scope: independent-electron cubic Sc-Zn 2p->3d L2,3; local M=+z;
proper rigid orbital/spin-frame rotations. No full bands/multiplets,
noncollinear spin texture or quantitative Fe spectroscopy is established.'''


class TensorSpectrumPreview(QtWidgets.QDialog):
    MODES = ('Tensor Components','Magnetization Reversal',
        'Magnetic-Odd and Nonmagnetic-Even Components','Full 3x3 Complex Tensor')
    COMPONENTS = ('Trace/3','Txx','Txy','Txz','Tyx','Tyy','Tyz','Tzx','Tzy','Tzz')

    def __init__(self,source,parent=None):
        super().__init__(parent)
        from .provider_direction import ReversedProviderPair
        original=source.source if isinstance(source,ReversedProviderPair) else source
        if not isinstance(original,ImportedMDFF) or source.metadata.get('convention')!=CONVENTION:
            raise ValueError('Preview requires a validated source and the accepted tensor convention')
        if source.metadata.get('atomic_model')!='independent_electron_cubic_2p3d_v1':
            raise ValueError('Atomic preview requires the declared existing atomic model')
        if source.metadata.get('units')!='angstrom^2/eV' or source.metadata.get('normalization')!='per_atom_relative' or source.metadata.get('basis')!='declared_local':
            raise ValueError('Atomic preview requires declared-local relative per-atom tensor units')
        proper_frame(source.metadata['frame_to_crystal'])
        # Reuse exactly the existing finite/Hermiticity/PSD validator; never repair.
        self.plus=psd_tensor(source.energy_ev,source.plus.tensor_angstrom2_per_ev,'+M preview').tensor_angstrom2_per_ev
        self.minus=psd_tensor(source.energy_ev,source.minus.tensor_angstrom2_per_ev,'-M preview').tensor_angstrom2_per_ev
        self.even=(self.plus+self.minus)/2;self.odd=(self.plus-self.minus)/2
        self.even.setflags(write=False);self.odd.setflags(write=False)
        self.source=source;self.energy=source.energy_ev;self.is_stale=False;self.curves=[]
        self.setWindowTitle('Atomic MDFF tensor spectrum - '+source.metadata['element']+' - '+source.metadata['status'])
        self.resize(1050,740);layout=QtWidgets.QVBoxLayout(self)
        self.identity=QtWidgets.QLabel(source.metadata['element']+' | '+source.metadata['atomic_model']+' | '+source.metadata['magnetic_state']+' | '+source.metadata['status']+
            '\nDeclared LOCAL tensor components; frame_to_crystal='+str(source.metadata['frame_to_crystal'])+
            ('\nMaterial target uses the validated source −M pair member.' if isinstance(source,ReversedProviderPair) else '\nMaterial target uses the source +M pair member.')+
            '\nSource: '+source.metadata['source'].split(EDITOR_TAG)[0]+'\nSHA256 '+source.sha256)
        self.identity.setWordWrap(True);self.identity.setMaximumHeight(150);layout.addWidget(self.identity)
        self.status=QtWidgets.QLabel('CURRENT mathematically validated source; material parameters remain physically unvalidated. Relative per-atom Angstrom^2/eV.');self.status.setWordWrap(True);layout.addWidget(self.status)
        bar=QtWidgets.QHBoxLayout();layout.addLayout(bar)
        self.mode=QtWidgets.QComboBox();self.mode.addItems(self.MODES);bar.addWidget(self.mode)
        self.component=QtWidgets.QComboBox();self.component.addItems(self.COMPONENTS);bar.addWidget(self.component)
        self.part=QtWidgets.QComboBox();self.part.addItems(['Real','Imaginary','Real and imaginary']);bar.addWidget(self.part)
        self.state=QtWidgets.QComboBox();self.state.addItems(['+M','-M','Even','Odd']);bar.addWidget(self.state)
        self.figure=Figure(layout='constrained');self.canvas=FigureCanvasQTAgg(self.figure);self.ax=self.figure.subplots()
        layout.addWidget(NavigationToolbar2QT(self.canvas,self));layout.addWidget(self.canvas,1)
        note=QtWidgets.QLabel('Tensor components are not detector spectra. Im(Txy) alone does not determine the final A/B EMCD sign. Odd tensors may be indefinite; only the physical +M/-M spectral tensors require PSD.');note.setWordWrap(True);layout.addWidget(note)
        details=QtWidgets.QPushButton('How Is the MDFF Tensor T(E) Constructed?');layout.addWidget(details);details.clicked.connect(self.show_construction)
        self.mode.currentIndexChanged.connect(self.draw)
        for box in (self.component,self.part,self.state):box.currentIndexChanged.connect(self.draw)
        self.draw()

    def component_data(self,tensor):
        k=self.component.currentIndex()
        return np.trace(tensor,axis1=-2,axis2=-1)/3 if k==0 else tensor[:,(k-1)//3,(k-1)%3]

    def draw(self,*_):
        mode=self.mode.currentIndex();self.component.setEnabled(mode!=0);self.part.setEnabled(mode!=0);self.state.setEnabled(mode in (0,3))
        if mode==3 and self.component.currentIndex()==0:
            with QtCore.QSignalBlocker(self.component):self.component.setCurrentIndex(1)
        states={'+M':self.plus,'-M':self.minus,'Even':self.even,'Odd':self.odd}
        self.curves=[]
        if mode==0:
            t=states[self.state.currentText()]
            self.curves=[('Re Tr(T)/3',np.trace(t,axis1=-2,axis2=-1).real/3),('Re Tzz',t[:,2,2].real),('Im Txy',t[:,0,1].imag)]
        else:
            pairs=(('+M',self.plus),('-M',self.minus)) if mode==1 else (('Even',self.even),('Odd',self.odd)) if mode==2 else ((self.state.currentText(),states[self.state.currentText()]),)
            parts=('Real','Imaginary') if self.part.currentIndex()==2 else (self.part.currentText(),)
            for label,t in pairs:
                values=self.component_data(t)
                for part in parts:self.curves.append((label+' '+part+' '+self.component.currentText(),values.real if part=='Real' else values.imag))
        self.ax.clear()
        for name,y in self.curves:self.ax.plot(self.energy,y,label=name)
        for edge,energy in self.source.metadata['selected_ev'].items():self.ax.axvline(energy,ls=':',color='.5',label=edge+' reference')
        self.ax.set(xlabel='Declared energy loss (eV)',ylabel='Relative per-atom local tensor (Angstrom^2/eV)',title=('STALE snapshot - ' if self.is_stale else '')+self.MODES[mode],xlim=(self.energy[0],self.energy[-1]));self.ax.legend();self.canvas.draw_idle()

    def mark_stale(self,reason='Inputs or source changed'):
        already_stale=self.is_stale;self.is_stale=True
        self.status.setText('STALE SNAPSHOT: '+reason+'. Explicitly Preview the current inputs again. These curves are not the current source and cannot authorize execution.')
        self.setWindowTitle('STALE - Atomic MDFF tensor snapshot')
        if not already_stale:self.draw()

    def show_construction(self):
        d=QtWidgets.QDialog(self);d.setWindowTitle('How Is the MDFF Tensor T(E) Constructed?');d.resize(850,700)
        layout=QtWidgets.QVBoxLayout(d);text=QtWidgets.QPlainTextEdit(CONSTRUCTION);text.setReadOnly(True);layout.addWidget(text);d.show();self.construction_dialog=d
