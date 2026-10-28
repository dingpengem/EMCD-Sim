"""Deterministic configuration selection. Never propagates waves or evaluates MDFF."""
from dataclasses import replace, asdict
import json
import numpy as np
from PySide6 import QtCore, QtWidgets
from .geometry import geometry, excitation
from .emcd_forward import material_reason, ForwardSettings


POLICY = 'automatic-starting-v3'
NUMERICAL_KEYS = ('beam','potential','fft_grid','depth','slice_step','grid','subpixels','halfwidth','energy')


def resolve_parameters(structure, settings, cfg):
    """Return actual values and provenance, without admission or scientific solves.

    Reference matching is deliberately restricted to the documented native-edge,
    exact-Bragg [017] representative points. Other cases use released starting
    defaults. Even reference matches are not claims about full-field convergence.
    """
    values = dict(beam=3.2,potential=2.5,fft_grid=32,depth=64,slice_step=.04,
                  grid=97,subpixels=64,halfwidth=1.,energy=241,memory_budget_mib=2048)
    centers=((1/3.524,1/3.524),(1/3.524,-1/3.524))
    # Native-source identity is explicit; a filename/material resemblance is insufficient.
    reference = (not material_reason(structure) and settings.zone==(0,1,7)
        and settings.target==(2,0,0) and not cfg.systematic_row
        and abs(settings.voltage-200)<1e-9 and settings.thickness in (8.,12.,30.,100.)
        and abs(settings.b_factor)<1e-12 and abs(settings.tilt[1])<1e-9
        and abs(float(excitation(np.array([2/3.524,0]),settings.tilt,settings.voltage)))<1e-10
        and cfg.model=='xmcd' and cfg.axis_declared
        and cfg.radial is None
        and cfg.source_sha256==REFERENCE_SOURCE_SHA256
        and np.allclose(cfg.magnetization,(0,0,1),rtol=0,atol=1e-12)
        and cfg.eta==cfg.beta==1 and abs(cfg.l3-831.4778)<1e-6 and abs(cfg.l2-848.698)<1e-6
        and np.allclose(cfg.centers,centers,rtol=0,atol=1e-8) and abs(cfg.radius-.0908059024)<1e-8)
    if reference:values.update(beam=4.6,potential=6.2,fft_grid=48,depth=257)
    resolved=replace(settings,beam_cutoff=values['beam'],potential_cutoff=values['potential'])
    hkl=geometry(structure,resolved,systematic_row=cfg.systematic_row)[2]
    if cfg.propagation!='bloch':
        from .propagation import numerical_info
        # Start with the released/reference mesh; never shrink it. A two-index
        # guard band below adds a margin to exact geometry-specific support.
        last=''
        for mesh in range(values['fft_grid'],129,2):
            candidate=replace(cfg,fft_grid=mesh,depth=values['depth'],slice_step=values['slice_step'])
            try:
                numerical_info(structure,resolved,candidate,hkl=hkl,check_memory=False)
                from .propagation import projected_geometry_for
                crystal=geometry(structure,resolved,systematic_row=cfg.systematic_row)[0]
                projected_geometry_for(resolved,crystal,cfg.fft_generators).harmonics(mesh-4,max(resolved.beam_cutoff,resolved.potential_cutoff))
                values['fft_grid']=mesh;break
            except ValueError as exc:
                last=str(exc)
                if ('no automatic fallback' in last or 'supports verified' in last
                        or 'requires the verified' in last or 'frames differ' in last):raise
        else:raise ValueError('Automatic FFT setup unavailable for the selected cutoffs and geometry. Review Advanced Numerical Settings. '+last)
    return values,dict(policy=POLICY,source='Matching reference configuration' if reference else 'Automatic starting configuration',
        status='Automatic settings do not guarantee numerical convergence.' if reference else 'Automatic starting settings — convergence not established.',
        reference='docs/DOUBLE_CHANNELING_UNIFORM_BASIS.md' if reference else None,
        scope='Representative native-edge detector observables only; no full-field/full-spectrum certification.',
        physical_settings=asdict(resolved),propagation=cfg.propagation,channeling_model=cfg.channeling_model)


# Filled from the archived uniform-basis provenance, never from a mutable live file.
REFERENCE_SOURCE_SHA256 = 'a0e28ea6423b6c7832bb3cce6d69d71aa59336a221baeee3d2556b49ba501283'


class NumericalSettingsUI:
    def setup_numerical_mode(self, form):
        self.numerical_mode=QtWidgets.QComboBox();self.numerical_mode.addItems(['Automatic','Manual (Advanced)'])
        form.insertRow(0,'Numerical Settings',self.numerical_mode)
        self.numerical_status=QtWidgets.QLabel();self.numerical_status.setWordWrap(True);form.insertRow(1,self.numerical_status)
        self.numerical_details=QtWidgets.QGroupBox('View Numerical Parameters');self.numerical_details.setCheckable(True);self.numerical_details.setChecked(False)
        outer=QtWidgets.QVBoxLayout(self.numerical_details);self.numerical_values=QtWidgets.QLabel();self.numerical_values.setWordWrap(True);self.numerical_values.hide();outer.addWidget(self.numerical_values)
        self.numerical_details.toggled.connect(self.numerical_values.setVisible);form.insertRow(2,self.numerical_details)
        self._manual_numerics=None;self._numerical_cache=None;self._numerical_error=None;self.numerical_provenance={}
        self.numerical_mode.currentIndexChanged.connect(self.change_numerical_mode)
        self.apply_numerical_visibility()

    def numerical_snapshot(self):
        return dict({key:self.spin[key].value() for key in NUMERICAL_KEYS},memory_budget_mib=self.memory_budget.currentData())

    def set_numerical_values(self, values):
        self.set_values({k:v for k,v in values.items() if k in NUMERICAL_KEYS})
        with QtCore.QSignalBlocker(self.memory_budget):self.memory_budget.setCurrentIndex(self.memory_budget.findData(values['memory_budget_mib']))
        with QtCore.QSignalBlocker(self.angular_resolution):self.sync_angular_resolution()

    def apply_numerical_visibility(self):
        manual=self.numerical_mode.currentIndex()==1
        for group in (self.shared_elastic_group,self.shared_sampling_group):
            group.setVisible(manual);group.presentation_section.setVisible(manual)
        self.shared_resources_group.setVisible(True)
        self.shared_resources_group.presentation_section.setVisible(True)
        for key in NUMERICAL_KEYS:self.spin[key].setEnabled(manual)
        self.memory_budget.setEnabled(True);self.angular_resolution.setEnabled(manual)
        self.numerical_details.setVisible(not manual)
        self.sync_solver_controls()

    def change_numerical_mode(self, index):
        self._restore_auto_once=False
        if index==0:
            self._manual_numerics=self.numerical_snapshot();self._numerical_cache=None
        else:
            if self._manual_numerics:self.set_numerical_values(self._manual_numerics)
            self._numerical_error=None
        self.apply_numerical_visibility();self.refresh()

    def resolve_numerical_ui(self):
        if not hasattr(self,'numerical_mode') or getattr(self,'_restoring',False):return False
        before=self.numerical_snapshot()
        try:
            if self.numerical_mode.currentIndex()==0:
                # Source validation is separate from configuration selection.
                cfg=ForwardSettings(propagation=['bloch','fft-multislice','both'][self.propagation_box.currentIndex()],
                    fft_generators=self.saved_fft_generators(),
                    channeling_model=('single','double')[self.channeling_box.currentIndex()],systematic_row=self.row_projection.isChecked(),
                    model=('xmcd','atomic')[self.model_box.currentIndex()],source_sha256=(self.source_info or {}).get('sha256','') if self.validated_path==self.source_path.text() else '',
                    axis_declared=self.declaration.isChecked(),magnetization=tuple(float(x) for x in self.axis.text().replace(',',' ').split()),
                    eta=self.spin['eta'].value(),beta=self.spin['beta'].value(),l3=self.spin['xl3'].value(),l2=self.spin['xl2'].value(),
                    radial=self.spin['radial'].value() if self.radial_override.isChecked() else None,
                    centers=tuple(tuple(p) for p in self.detectors),radius=self.spin['radius'].value())
                s=self.settings()
                atoms=self.structure.atoms
                key=json.dumps(dict(settings=asdict(replace(s,beam_cutoff=0,potential_cutoff=0)),cfg=asdict(cfg),
                    cell=atoms.cell.array.tolist(),positions=atoms.get_scaled_positions().tolist(),species=atoms.get_chemical_symbols(),
                    occupancy=atoms.info.get('occupancy',{})),sort_keys=True)
                if getattr(self,'_restore_auto_once',False):
                    self._numerical_cache=key;self._restore_auto_once=False
                elif key!=self._numerical_cache:
                    values,provenance=resolve_parameters(self.structure,s,cfg)
                    values['memory_budget_mib']=self.memory_budget.currentData()
                    self.set_numerical_values(values);self.numerical_provenance=provenance;self._numerical_cache=key
                self.numerical_status.setText(self.numerical_provenance['source']+'\n'+self.numerical_provenance['status'])
            else:
                self.numerical_provenance=dict(source='Manual configuration',policy=None)
                self.numerical_status.setText('Manual configuration')
            self._numerical_error=None
            values=self.numerical_snapshot()
            labels=dict(beam='Beam / MDFF cutoff (Å⁻¹)',potential='Potential cutoff (Å⁻¹)',fft_grid='FFT grid',depth='Depth nodes',slice_step='Max slice step (nm)',grid='Angular grid',subpixels='Aperture boundary subpixels',halfwidth='Map halfwidth (Å⁻¹)',energy='Energy sampling points',memory_budget_mib='Memory budget (MiB)')
            lines=[f'{labels[k]}: {v} x {v}' if k in ('grid','fft_grid') else f'{labels[k]}: {v}' for k,v in values.items() if k not in ('fft_grid','slice_step') or self.propagation_box.currentIndex()!=0]
            self.numerical_values.setText('\n'.join(lines)+'\nAutomatic settings do not guarantee numerical convergence.')
        except Exception as exc:
            self._numerical_error=str(exc);self._numerical_cache=None
            self.numerical_status.setText('Numerical settings unavailable: '+str(exc));self.numerical_values.setText('Unavailable for current inputs; previous valid values retained.')
        return before!=self.numerical_snapshot()

    def numerical_selection_snapshot(self):
        return dict(mode='automatic' if self.numerical_mode.currentIndex()==0 else 'manual',actual=self.numerical_snapshot(),
                    manual_overrides=self._manual_numerics,provenance=self.numerical_provenance)

    def restore_numerical_selection(self, metadata):
        saved=metadata.get('numerical_selection',{})
        with QtCore.QSignalBlocker(self.numerical_mode):self.numerical_mode.setCurrentIndex(0 if saved.get('mode')=='automatic' else 1)
        self._manual_numerics=saved.get('manual_overrides');self._numerical_cache=None
        self.numerical_provenance=saved.get('provenance',dict(source='Manual configuration',policy=None))
        self._restore_auto_once=saved.get('mode')=='automatic'
        self.apply_numerical_visibility()
