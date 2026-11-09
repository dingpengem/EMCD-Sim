"""Transient site-group form state; executable groups use the Stage 1 model.

Missing MDFF references remain None in Qt item data, never synthetic providers.
The applied form snapshot also retains incomplete rows for the later MDFF UI.
"""
import numpy as np
from PySide6 import QtCore, QtWidgets

from ..multisite import IonizationSiteGroup, MultiSiteIonization, _ordered_atoms


ROLE = QtCore.Qt.ItemDataRole.UserRole


def validate_site_rows(atoms, rows):
    """Shared validation of editor drafts; only complete rows form a Stage 1 model."""
    if not rows:return None
    _ordered_atoms(atoms)
    names = set();assigned = set();complete = []
    for name,element,indices,direction,reference in rows:
        if not name.strip() or name in names:raise ValueError('Group IDs must be nonempty and unique')
        names.add(name)
        if not indices:raise ValueError('Groups need at least one atom; delete an empty group instead')
        if len(set(indices))!=len(indices) or assigned.intersection(indices):
            raise ValueError('Duplicate assignments: remove atoms from their current group first')
        if any(isinstance(i,bool) or not isinstance(i,(int,np.integer)) or i<0 or i>=len(atoms) or atoms[i].symbol!=element for i in indices):
            raise ValueError('Each group must contain valid original indices of one element')
        assigned.update(indices)
        if direction is None and getattr(reference,'magnetic_state',None)=='nonmagnetic':
            # This is the source's declared compatibility/reference axis, not
            # an inferred Material magnetization. The structural row stays None.
            direction=reference.magnetization
        if direction is None:
            if reference is not None:raise ValueError('Declare a magnetic direction before binding an MDFF provider')
            continue  # Structural draft only: no magnetic direction is inferred.
        vector = np.asarray(direction)
        if vector.shape!=(3,) or not np.isfinite(vector).all() or not np.any(vector):
            raise ValueError('A finite nonzero magnetization direction is required')
        if reference is not None:
            complete.append(IonizationSiteGroup(name,element,indices,reference,direction,len(indices)))
    model = MultiSiteIonization(atoms,complete) if complete else None
    return model if len(complete)==len(rows) else None


class SiteGroupEditor(QtWidgets.QScrollArea):
    changed = QtCore.Signal()
    selectionChanged = QtCore.Signal(object)
    applied = QtCore.Signal(object)  # None means no executable configuration.
    modeChanged = QtCore.Signal(str)
    pendingChanged = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.atoms = None
        self.accepted_site_groups = None
        self.preview_site_groups = None
        self._accepted_rows = ()
        self.dirty = False
        self._accepted_mode = 'global'
        self.reverse_magnetization = self._accepted_reversal = False
        self.mdff_dialogs = {};self.energy_windows = {};self._mdff_status = {}
        self._accepted_mdff = ({},{},{},{})
        self.crystallographic_provenance = {}
        self.excluded_groups=set();self._accepted_excluded=set()
        self.setWidgetResizable(True);self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        body=QtWidgets.QWidget();self.setWidget(body)
        layout = QtWidgets.QVBoxLayout(body)
        self.mode = QtWidgets.QComboBox()
        self.mode.addItems(['Global Magnetization Mode', 'Local Site Magnetization Mode'])
        layout.addWidget(self.mode)
        self.mode_note = QtWidgets.QLabel(); self.mode_note.setWordWrap(True); layout.addWidget(self.mode_note)
        note = QtWidgets.QLabel('Select original atoms here or click in 3D (Ctrl+click toggles). '
            'Replicas share one original ASE index. Check a group to include its ionization contribution; '
            'unchecked atoms remain in the elastic structure. Assignment never implies equivalence.')
        note.setWordWrap(True); layout.addWidget(note)
        self.filter = QtWidgets.QComboBox(); self.filter.addItems(['All atoms', 'Assigned atoms', 'Unassigned atoms'])
        layout.addWidget(self.filter)
        self.atom_list = QtWidgets.QListWidget()
        self.atom_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.atom_list.setMinimumHeight(72);self.atom_list.setMaximumHeight(110)
        layout.addWidget(self.atom_list)
        self.selection_text = QtWidgets.QLabel('Individual atoms for assignment/removal: none. Use the group table to edit a whole group.'); self.selection_text.setWordWrap(True)
        layout.addWidget(self.selection_text)
        self.groups = QtWidgets.QTreeWidget(); self.groups.setHeaderLabels(['Group ID', 'Element', 'ASE indices', 'MDFF'])
        self.groups.setColumnCount(6)
        self.groups.setHeaderLabels(['Ionize / Group ID', 'Element', 'ASE indices', 'MDFF', 'Atoms', 'Wyckoff'])
        self.groups.header().moveSection(4,2);self.groups.header().moveSection(5,3)
        self.groups.header().moveSection(self.groups.header().visualIndex(3),4)
        self.groups.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Interactive)
        self.groups.header().setStretchLastSection(False)
        for column,width in enumerate((125,60,220,155,50,70)):self.groups.setColumnWidth(column,width)
        self.groups.setMinimumHeight(155)
        self.groups.setAlternatingRowColors(True)
        self.groups.setRootIsDecorated(False); layout.addWidget(self.groups, 2)
        self.symmetry_note = QtWidgets.QLabel();self.symmetry_note.setWordWrap(True);layout.addWidget(self.symmetry_note)
        form = QtWidgets.QFormLayout(); layout.addLayout(form)
        self.name = QtWidgets.QLineEdit(); form.addRow('Group ID / name', self.name)
        self.group_summary = QtWidgets.QLabel('Select a group to edit its direction.');self.group_summary.setWordWrap(True)
        self.group_summary.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,QtWidgets.QSizePolicy.Policy.Minimum)
        form.addRow(self.group_summary)
        self.direction = QtWidgets.QLineEdit('0 0 1'); form.addRow('Direction (Cartesian x y z)', self.direction)
        self.direction.textChanged.connect(self.refresh_group_summary)
        direction_note = QtWidgets.QLabel('Direction only, normalized on update. This does not define a complete anisotropic MDFF tensor frame.')
        direction_note.setWordWrap(True); layout.addWidget(direction_note)
        self.buttons = {}
        for actions in [(('Create from selection',self.create_group),('Assign selection',self.assign_selected)),
                        (('Rename',self.rename_group),('Update direction',self.update_direction)),
                        (('Remove selected atoms',self.remove_selected),('Delete group',self.delete_group)),
                        (('Flip all local M',self.flip_all),)]:
            row = QtWidgets.QHBoxLayout(); layout.addLayout(row)
            for label, action in actions:
                button = QtWidgets.QPushButton(label); row.addWidget(button); self.buttons[label] = button
                button.clicked.connect(lambda checked=False, fn=action:self.run_action(fn))
        self.status = QtWidgets.QLabel('No site groups. Ordinary CIF viewing remains available.')
        row = QtWidgets.QHBoxLayout();layout.addLayout(row)
        configure = QtWidgets.QPushButton('Configure MDFF…');row.addWidget(configure)
        configure.clicked.connect(lambda:self.run_action(self.open_mdff_editor))
        recheck = QtWidgets.QPushButton('Recheck sources');row.addWidget(recheck)
        recheck.clicked.connect(self.recheck_mdff_sources)
        self.status.setWordWrap(True); layout.addWidget(self.status)
        self.status.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,QtWidgets.QSizePolicy.Policy.Minimum)
        self.status.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.atom_list.itemSelectionChanged.connect(self.emit_selection)
        self.filter.currentIndexChanged.connect(self.refresh_atoms)
        self.groups.currentItemChanged.connect(self.load_fields)
        self.groups.itemChanged.connect(self.participation_changed)
        self.mode.currentIndexChanged.connect(self.mode_changed)
        self.mode_changed()

    @property
    def magnetization_mode(self):
        return 'local' if self.mode.currentIndex() == 1 else 'global'

    def mode_changed(self, *_):
        local = self.magnetization_mode == 'local'
        self.direction.setEnabled(local)
        self.buttons['Update direction'].setEnabled(local)
        self.buttons['Flip all local M'].setEnabled(local)
        self.mode_note.setText('Global magnetization is locked while site-specific magnetization is enabled.'
            if local else 'Legacy Global M is active. Local directions are retained but inactive; edit them in Local mode.')
        self.dirty = (self.rows() != self._accepted_rows or self.magnetization_mode != self._accepted_mode
                      or self.reverse_magnetization != self._accepted_reversal
                      or self.excluded_groups!=self._accepted_excluded)
        self.update_status(); self.modeChanged.emit(self.magnetization_mode)

    def run_action(self, action):
        try:action()
        except (ValueError, TypeError) as exc:self.status.setText(str(exc))

    def rows(self):
        """Qt form values, not an alternative executable site-group model."""
        return tuple((item.text(0), item.text(1), item.data(0, ROLE),
                      item.data(1, ROLE), item.data(2, ROLE)[0]) for item in
                     (self.groups.topLevelItem(i) for i in range(self.groups.topLevelItemCount())))

    def restore_rows(self, rows):
        provenance = self.crystallographic_provenance
        self.symmetry_note.setText((f"Crystallographic grouping only: {provenance.get('international','undetermined')}; "
            f"symprec={provenance.get('symprec_angstrom')} Å. No magnetic order inferred. "
            +' '.join(provenance.get('warnings',[]))) if provenance else '')
        with QtCore.QSignalBlocker(self.groups):
            self.groups.clear()
            for name, element, indices, direction, reference in rows:
                row = (name,element,indices,direction,reference)
                display,detail=self.mdff_display(row)
                item = QtWidgets.QTreeWidgetItem([name, element, ', '.join(map(str,indices)),display])
                item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(0,QtCore.Qt.CheckState.Unchecked if name in self.excluded_groups else QtCore.Qt.CheckState.Checked)
                item.setToolTip(1,'Checked groups participate in ionization. Unchecked groups remain in the complete elastic crystal. Missing MDFF never excludes a checked group automatically.')
                item.setToolTip(2,', '.join(map(str,indices)))
                provenance = self.crystallographic_provenance.get('groups',[])
                match = next((g for g in provenance if g['indices'] == list(indices) and g['element'] == element),None)
                item.setText(4,str(len(indices)));item.setText(5,match['wyckoff'] if match else 'Manual / edited')
                item.setToolTip(0,('Crystallographic orbit; CIF labels: '+', '.join(match['cif_labels'])) if match else 'Manual assignment')
                item.setToolTip(3,detail)
                item.setData(0, ROLE, tuple(indices)); item.setData(1, ROLE, None if direction is None else tuple(direction))
                # A tuple keeps arbitrary Python references intact; a bare dict
                # is otherwise converted to a copied QVariantMap by Qt.
                item.setData(2, ROLE, (reference,)); self.groups.addTopLevelItem(item)
        self.refresh_atoms()
        if rows:
            self.groups.setCurrentItem(self.groups.topLevelItem(0))
        else:
            self.name.clear(); self.direction.setText('0 0 1')
            self.group_summary.setText('Select a group to edit its direction.')

    def set_structure(self, atoms, groups=None):
        self.atoms = atoms
        self.load_groups(groups)

    def load_groups(self, groups):
        self.crystallographic_provenance = {}
        self.requested_energy_ev=None;self.omitted_site_groups=set()
        self.excluded_groups=set();self._accepted_excluded=set()
        self.portable_references={}
        self.reverse_magnetization = self._accepted_reversal = False
        for dialog in self.mdff_dialogs.values():dialog.close();dialog.deleteLater()
        self.mdff_dialogs = {};self.energy_windows = {};self._mdff_status = {}
        self._accepted_mdff = ({},{},{},{})
        self.accepted_site_groups = groups
        self.preview_site_groups = groups
        self._accepted_rows = tuple((g.group_id,g.element,g.indices,g.magnetization,g.mdff_reference)
                                    for g in groups.groups) if groups is not None else ()
        self.restore_rows(self._accepted_rows)
        self._accepted_mode = self.magnetization_mode
        self.dirty = False; self.update_status()

    def current_row(self):
        index = self.groups.indexOfTopLevelItem(self.groups.currentItem())
        if index < 0:raise ValueError('Select a group first')
        return index

    def load_fields(self, current, previous=None):
        if current is not None:
            self.name.setText(current.text(0))
            direction = current.data(1, ROLE)
            self.direction.setText('' if direction is None else ' '.join(f'{v:.8g}' for v in direction))
        self.refresh_group_summary()

    def refresh_group_summary(self, *_):
        """Present existing row/snapshot/status values without validating or editing them."""
        current=self.groups.currentItem()
        if current is None:
            self.group_summary.setText('Select a group to edit its direction.');return
        name=current.text(0);indices=current.data(0,ROLE);direction=current.data(1,ROLE)
        reference=current.data(2,ROLE)[0]
        accepted=next((r for r in self._accepted_rows if r[0]==name),None)
        inactive=self.magnetization_mode=='global'
        vector=lambda m:('Unconfigured' if m is None else ' '.join(f'{v:.8g}' for v in m))+(' (inactive)' if inactive else '')
        lines=[f'Selected group: {name} — {len(indices)} '+('atom' if len(indices)==1 else 'atoms'),
               'Accepted M: '+(vector(accepted[3]) if accepted is not None else 'Not yet applied')]
        if accepted is None or direction!=accepted[3]:lines.append('Draft M (unapplied): '+vector(direction))
        text=self.direction.text().strip();staged='' if direction is None else ' '.join(f'{v:.8g}' for v in direction)
        if text!=staged:lines.append('Input M (not staged): '+(text or '(empty)')+'; use Update direction.')
        row=(name,current.text(1),indices,direction,reference)
        label='MDFF draft' if accepted is not None and reference!=accepted[4] else 'MDFF'
        display,detail=self.mdff_display(row)
        lines.append(label+': '+display)
        lines.append(detail)
        if reference is not None:lines.append('Source pair member: '+('−M' if getattr(reference,'pair_reversed',False) else '+M'))
        self.group_summary.setText('\n'.join(lines))

    def suggest_crystallographic_groups(self, provenance):
        """Initialize structural drafts only; never overwrite a user's rows or M."""
        if self.rows():return
        self.crystallographic_provenance = provenance
        if provenance.get('status') != 'ready':
            self.status.setText('Automatic grouping unavailable; use manual assignment. '+' '.join(provenance.get('warnings',[])))
            return
        rows = tuple((g['group_id'],g['element'],tuple(g['indices']),None,None) for g in provenance['groups'])
        self.check_rows(rows);self._accepted_rows = rows;self.restore_rows(rows)
        self.dirty = False;self.update_status()

    def selected_indices(self):
        return tuple(sorted(item.data(ROLE) for item in self.atom_list.selectedItems()))

    def select_indices(self, indices):
        wanted = set(indices)
        with QtCore.QSignalBlocker(self.atom_list):
            for i in range(self.atom_list.count()):
                item = self.atom_list.item(i); item.setSelected(item.data(ROLE) in wanted)
        self.emit_selection()

    def pick_atom(self, index, additive=False):
        # Make a picked atom visible even if the current assignment filter hid it.
        selected = set(self.selected_indices()) if additive else set()
        if additive and index in selected:selected.remove(index)
        else:selected.add(index)
        self.filter.setCurrentIndex(0)
        self.select_indices(selected)

    def emit_selection(self):
        indices = self.selected_indices()
        if indices:
            assigned = [n for n,row in enumerate(self.rows()) if indices[-1] in row[2]]
            if assigned:self.groups.setCurrentItem(self.groups.topLevelItem(assigned[0]))
        self.selection_text.setText('Individual atoms for assignment/removal: ' + ', '.join(f'{i} {self.atoms[i].symbol}' for i in indices)
                                   if indices else 'Individual atoms for assignment/removal: none. Use the group table to edit a whole group.')
        self.selectionChanged.emit(indices)

    def refresh_atoms(self, *_):
        selected = self.selected_indices()
        assigned = {i:name for name,_,indices,_,_ in self.rows() for i in indices}
        with QtCore.QSignalBlocker(self.atom_list):
            self.atom_list.clear()
            if self.atoms is not None:
                for atom in self.atoms:
                    if self.filter.currentIndex() == 1 and atom.index not in assigned:continue
                    if self.filter.currentIndex() == 2 and atom.index in assigned:continue
                    item = QtWidgets.QListWidgetItem(f'{atom.index}: {atom.symbol} — {assigned.get(atom.index,"Unassigned")}')
                    item.setData(ROLE,atom.index); self.atom_list.addItem(item)
        self.select_indices(selected)

    def parsed_direction(self):
        try:direction = np.asarray([float(x) for x in self.direction.text().replace(',',' ').split()])
        except ValueError:raise ValueError('Enter three finite nonzero Cartesian direction components') from None
        if direction.shape != (3,) or not np.isfinite(direction).all() or not np.any(direction):
            raise ValueError('Enter three finite nonzero Cartesian direction components')
        direction /= np.max(np.abs(direction)); direction /= np.linalg.norm(direction)
        return tuple(map(float,direction))

    def check_rows(self, rows):
        validate_site_rows(self.atoms,rows)  # Structural checks include excluded rows.
        return validate_site_rows(self.atoms,self.participating_rows(rows))

    def participating_rows(self,rows=None):
        return tuple(row for row in (self.rows() if rows is None else rows) if row[0] not in self.excluded_groups)

    def participation_changed(self,item,column):
        if column!=0:return
        name=item.text(0)
        if item.checkState(0)==QtCore.Qt.CheckState.Checked:self.excluded_groups.discard(name)
        else:self.excluded_groups.add(name)
        self.preview_site_groups=self.check_rows(self.rows());self.dirty=True
        self.update_status();self.changed.emit()

    def replace_rows(self, rows, current=None):
        self.excluded_groups.intersection_update(r[0] for r in rows)
        self.preview_site_groups = self.check_rows(rows)
        self.restore_rows(rows); self.dirty = True
        if current is not None and current < self.groups.topLevelItemCount():
            self.groups.setCurrentItem(self.groups.topLevelItem(current))
        self.update_status(); self.changed.emit()
        by_name = {r[0]:r for r in rows}
        for name,dialog in self.mdff_dialogs.items():
            if name in by_name:dialog.set_context(by_name[name]);dialog.setEnabled(True)
            else:dialog.hide();dialog.setEnabled(False)

    def create_group(self):
        indices = self.selected_indices()
        if not indices:raise ValueError('Select atoms first')
        rows = self.rows() + ((self.name.text().strip(),self.atoms[indices[0]].symbol,
                              indices,self.parsed_direction(),None),)
        self.replace_rows(rows,len(rows)-1)

    def assign_selected(self):
        row = self.current_row(); rows = list(self.rows()); name,element,indices,direction,reference = rows[row]
        selected = self.selected_indices()
        if not selected:raise ValueError('Select atoms first')
        rows[row] = (name,element,tuple(sorted(set(indices).union(selected))),direction,reference)
        self.replace_rows(rows,row)

    def remove_selected(self):
        row = self.current_row(); rows = list(self.rows()); name,element,indices,direction,reference = rows[row]
        remaining = tuple(i for i in indices if i not in self.selected_indices())
        rows[row] = (name,element,remaining,direction,reference)
        self.replace_rows(rows,row)

    def delete_group(self):
        row = self.current_row(); rows = list(self.rows()); del rows[row]
        self.replace_rows(rows,min(row,len(rows)-1) if rows else None)

    def rename_group(self):
        row = self.current_row(); rows = list(self.rows())
        previous = rows[row][0]
        if previous in self.excluded_groups:
            self.excluded_groups.remove(previous);self.excluded_groups.add(self.name.text().strip())
        rows[row] = (self.name.text().strip(),) + rows[row][1:]
        self.replace_rows(rows,row)
        name = rows[row][0]
        for mapping in (self.mdff_dialogs,self.energy_windows,self._mdff_status):
            if previous in mapping:mapping[name] = mapping.pop(previous)
        if name in self.mdff_dialogs:
            self.mdff_dialogs[name].set_context(rows[row]);self.mdff_dialogs[name].setEnabled(True)

    def update_direction(self):
        if self.magnetization_mode != 'local':raise ValueError('Enable Local Site Magnetization Mode to edit local directions')
        row = self.current_row(); rows = list(self.rows()); name,element,indices,_,reference = rows[row]
        rows[row] = (name,element,indices,self.parsed_direction(),reference)
        self.replace_rows(rows,row)

    def flip_all(self):
        """Reverse every declared local direction, never conjugate a tensor.

        MDFF binding must select the provider's physical reversal pair later.
        Reference objects and full tensor frames are intentionally untouched.
        """
        if self.magnetization_mode != 'local':raise ValueError('Enable Local Site Magnetization Mode first')
        if not self.rows():raise ValueError('Declare local site groups before reversing M')
        if any(row[3] is None and getattr(row[4],'magnetic_state',None)!='nonmagnetic' for row in self.participating_rows()):raise ValueError('Declare all participating magnetic directions explicitly before reversing M')
        from .generalized_forward import ImportedSettings
        declared = [isinstance(row[4],ImportedSettings) for row in self.participating_rows()]
        if any(declared):
            if not all(declared):raise ValueError('Configure all group MDFF providers before reversing their magnetic pairs')
            self.reverse_magnetization = not self.reverse_magnetization
            self.dirty = True;self.update_status();self.changed.emit();return
        self.replace_rows(tuple((name,element,indices,tuple(-v for v in direction) if direction is not None and name not in self.excluded_groups else direction,reference)
            for name,element,indices,direction,reference in self.rows()), self.current_row())

    def set_mdff_reference(self, group_id, reference):
        """Handoff for the later MDFF interface; no provider creation/evaluation."""
        rows = list(self.rows())
        row = next((i for i,r in enumerate(rows) if r[0] == group_id),None)
        if row is None:raise ValueError('Unknown site-group ID')
        rows[row] = rows[row][:4] + (reference,)
        self.replace_rows(rows,row)

    def mdff_status(self, row):
        from .generalized_forward import ImportedSettings
        if row[4] is None:return 'Incomplete'
        if not isinstance(row[4],ImportedSettings):return 'Unvalidated reference'
        context,reference,message = self._mdff_status.get(row[0],(None,None,''))
        if context != row[1:4] or reference is not row[4]:return 'Needs validation'
        return 'Configured and valid' if message == 'valid' else 'Invalid / stale'

    def mdff_display(self,row,*,group_context=False):
        """Scope presentation only; mdff_status remains the validation status."""
        actual=self.mdff_status(row);requirements=[]
        if row[3] is None and getattr(row[4],'magnetic_state',None)!='nonmagnetic':requirements.append('Declare a local magnetization direction.')
        if row[4] is None:requirements.append('Configure and validate this group’s MDFF provider.')
        elif actual!='Configured and valid':
            message=self._mdff_status.get(row[0],('',None,''))[2]
            requirements.append(message if message and message!='valid' else actual+'. Recheck or validate this group’s MDFF source.')
        detail=' '.join(requirements) or 'Group provider configured and valid.'
        if row[0] in self.excluded_groups:
            detail='Local participation: excluded / elastic-only. '+detail
        if self.magnetization_mode=='global' and not group_context:
            return 'Inactive — Global mode','This local configuration is not used by the current Global calculation. '+detail
        if row[0] in self.excluded_groups:
            return 'Excluded — elastic only','MDFF is not required while this group is excluded from local ionization. '+detail
        if actual=='Configured and valid' and not requirements:return actual,detail
        return ('Incomplete' if actual=='Incomplete' else 'Incomplete — '+actual.lower()),detail

    def recheck_mdff_sources(self):
        from .group_mdff import validate_group_reference
        for row in self.rows():
            if row[4] is None:continue
            try:
                validate_group_reference(self.effective_row(row),window=self.energy_windows.get(row[0]));message = 'valid'
            except Exception as exc:message = str(exc)
            self._mdff_status[row[0]] = (row[1:4],row[4],message)
        # Refresh status cells only: never reset atom selection or current group.
        self.update_status()

    def configure_mdff(self):
        from .group_mdff import GroupMDFFDialog
        from .runtime import workspace
        row = self.effective_row(self.rows()[self.current_row()])
        dialog = self.mdff_dialogs.get(row[0])
        if dialog is None:
            dialog = GroupMDFFDialog(row,getattr(self,'mdff_workspace',None) or workspace(),self)
            dialog.commit = lambda cfg,window,d=dialog:self.accept_mdff(d,cfg,window)
            dialog.draftChanged.connect(self.pendingChanged)
            self.mdff_dialogs[row[0]] = dialog
        elif dialog.reference is not None and row[4] is not None and dialog.reference.source!=row[4].source and not dialog.has_unapplied_edits():
            with QtCore.QSignalBlocker(dialog):dialog.restore_reference(row[4])
            dialog._applied_snapshot=dialog.snapshot()
        self.recheck_mdff_sources()
        if self.mdff_status(row) == 'Invalid / stale':
            dialog.status.setText('Invalid / stale source: '+self._mdff_status[row[0]][2])
        dialog.open_draft(row)
        return dialog

    def open_mdff_editor(self):
        if hasattr(self,'mdff_opener'):
            group=self.rows()[self.current_row()][0] if self.magnetization_mode=='local' and self.current_row()>=0 else None
            return self.mdff_opener(group)
        return self.configure_mdff()

    def accept_mdff(self, dialog, cfg, window):
        from .group_mdff import validate_group_reference
        row = next((r for r in self.rows() if r[0] == dialog.row[0]),None)
        if row is None:raise ValueError('The site group was removed')
        validate_group_reference(row,cfg,window)
        self.energy_windows[row[0]] = window
        self.requested_energy_ev=None
        if hasattr(self,'omitted_site_groups'):self.omitted_site_groups.discard(row[0])
        self._mdff_status[row[0]] = (row[1:4],cfg,'valid')
        self.set_mdff_reference(row[0],cfg)

    @property
    def validated_site_groups(self):
        from .generalized_forward import ImportedSettings
        from .group_mdff import validate_group_reference
        rows = tuple(self.effective_row(row) for row in self.participating_rows())
        if not rows:raise ValueError('Select at least one participating ionization group')
        for row in rows:
            if not isinstance(row[4],ImportedSettings):raise ValueError('Enabled group '+row[0]+': configure and validate its MDFF provider')
        for row in rows:validate_group_reference(row,window=self.energy_windows.get(row[0]))
        return self.check_rows(rows)

    def effective_row(self,row):
        """Rebase only a byte-identical project attachment, never a provider/M."""
        from dataclasses import replace
        saved=getattr(self,'portable_references',{}).get(row[0]);reference=row[4]
        if saved and reference is not None and reference.source_sha256==saved[0]:
            return row[:4]+(replace(reference,source=saved[1]),)
        return row

    def update_status(self):
        with QtCore.QSignalBlocker(self.groups):
            for i,row in enumerate(self.rows()):
                display,detail=self.mdff_display(row)
                item=self.groups.topLevelItem(i);item.setText(3,display);item.setToolTip(3,detail)
        missing = sum(row[4] is None for row in self.participating_rows())
        undeclared = sum(row[3] is None and getattr(row[4],'magnetic_state',None)!='nonmagnetic' for row in self.participating_rows())
        prefix = 'Unapplied edits. Apply to accept; Cancel to discard. ' if self.dirty else 'Applied in memory. '
        mode = 'Local mode. ' if self.magnetization_mode == 'local' else 'Global mode; local directions inactive. '
        if self.magnetization_mode == 'local':mode += ('All provider −M states selected. ' if self.reverse_magnetization else 'Declared +M configuration selected. ')
        invalid = sum(self.mdff_status(row) != 'Configured and valid' for row in self.participating_rows())
        self.status.setText(mode + prefix + (f'{undeclared} group direction(s) undeclared. ' if undeclared else '') + (f'{missing} unconfigured group(s): MDFF references required; local configuration is not executable.'
            if missing else ((f'{invalid} invalid/unvalidated provider(s); not ready for calculation.' if invalid else 'All group providers configured and valid.')
                             if self.rows() else ('No local groups configured; local calculation unavailable.'
                                 if self.magnetization_mode == 'local' else 'No groups; ordinary CIF viewing.'))))
        self.status.setText(self.status.text()+f' Ionization: {sum(len(r[2]) for r in self.participating_rows())} selected atoms; {len(self.excluded_groups)} structural group(s) excluded, retained for elastic scattering.')
        if self.magnetization_mode=='global':
            self.status.setText('Global mode. '+prefix+'Local group settings are inactive; they do not determine Global MDFF readiness. Configure Global MDFF in the Global editor context. Local assignments are retained.')
        self.refresh_group_summary()

    def apply(self):
        from .generalized_forward import ImportedSettings
        from .group_mdff import bind_group_direction
        for name,dialog in self.mdff_dialogs.items():
            if name in {row[0] for row in self.participating_rows()} and dialog.has_unapplied_edits():
                raise ValueError('Apply or Cancel pending MDFF edits for '+name+' before applying site groups')
        rows = tuple(self.effective_row(row) for row in self.rows())
        prospective = tuple(row if row[0] in self.excluded_groups else row[:4]+(bind_group_direction(row,self.energy_windows.get(row[0])),) for row in rows)
        model = self.check_rows(prospective)
        # Commit only after every group has validated. Recreate a changed group's
        # cached editor from its accepted source next time, avoiding stale +M fields.
        for old,row in zip(rows,prospective):
            if isinstance(row[4],ImportedSettings):
                self._mdff_status[row[0]]=(row[1:4],row[4],'valid')
            if old[4] != row[4] and row[0] in self.mdff_dialogs:
                dialog=self.mdff_dialogs.pop(row[0]);dialog.close();dialog.deleteLater()
        self.restore_rows(prospective)
        self._accepted_rows = self.rows(); self.accepted_site_groups = self.preview_site_groups = model
        self._accepted_mode = self.magnetization_mode
        self._accepted_reversal = self.reverse_magnetization
        self._accepted_excluded=set(self.excluded_groups)
        names = {r[0] for r in self.rows()}
        for name in list(self.mdff_dialogs):
            if name not in names:
                dialog = self.mdff_dialogs.pop(name);dialog.close();dialog.deleteLater()
                self.energy_windows.pop(name,None);self._mdff_status.pop(name,None)
        self._accepted_mdff = (dict(self.mdff_dialogs),dict(self.energy_windows),dict(self._mdff_status),
                              {name:dialog.snapshot() for name,dialog in self.mdff_dialogs.items()})
        self.dirty = False; self.update_status(); self.applied.emit(model)
        return model

    def cancel(self):
        self.excluded_groups=set(self._accepted_excluded)
        dialogs,windows,status,snapshots = self._accepted_mdff
        for dialog in self.mdff_dialogs.values():
            dialog.hide()
            if dialog not in dialogs.values():dialog.deleteLater()
        self.mdff_dialogs = dict(dialogs);self.energy_windows = dict(windows);self._mdff_status = dict(status)
        for name,dialog in self.mdff_dialogs.items():
            dialog.restore_snapshot(snapshots[name])
            row = next((r for r in self._accepted_rows if r[0] == name),None)
            if row is not None:
                dialog.set_context(row);dialog.reference = row[4]
                dialog.window = windows.get(name);dialog.setEnabled(True)
                dialog._applied_snapshot = dialog.snapshot()
        self.preview_site_groups = self.accepted_site_groups
        self.reverse_magnetization = self._accepted_reversal
        self.restore_rows(self._accepted_rows); self.dirty = False
        self.mode.setCurrentIndex(int(self._accepted_mode == 'local'))
        self.update_status(); self.changed.emit()
