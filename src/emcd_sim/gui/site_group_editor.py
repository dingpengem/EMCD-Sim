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


class SiteGroupEditor(QtWidgets.QWidget):
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
        layout = QtWidgets.QVBoxLayout(self)
        self.mode = QtWidgets.QComboBox()
        self.mode.addItems(['Global Magnetization Mode', 'Local Site Magnetization Mode'])
        layout.addWidget(self.mode)
        self.mode_note = QtWidgets.QLabel(); self.mode_note.setWordWrap(True); layout.addWidget(self.mode_note)
        note = QtWidgets.QLabel('Select original atoms here or click in 3D (Ctrl+click toggles). '
            'Replicas share one original ASE index. Assignment never implies equivalence.')
        note.setWordWrap(True); layout.addWidget(note)
        self.filter = QtWidgets.QComboBox(); self.filter.addItems(['All atoms', 'Assigned atoms', 'Unassigned atoms'])
        layout.addWidget(self.filter)
        self.atom_list = QtWidgets.QListWidget()
        self.atom_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        layout.addWidget(self.atom_list, 2)
        self.selection_text = QtWidgets.QLabel('No atoms selected'); self.selection_text.setWordWrap(True)
        layout.addWidget(self.selection_text)
        self.groups = QtWidgets.QTreeWidget(); self.groups.setHeaderLabels(['Group ID', 'Element', 'ASE indices', 'MDFF'])
        self.groups.setColumnCount(6)
        self.groups.setHeaderLabels(['Group ID', 'Element', 'ASE indices', 'MDFF', 'Atoms', 'Wyckoff'])
        self.groups.header().moveSection(4,2);self.groups.header().moveSection(5,3)
        self.groups.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.groups.setRootIsDecorated(False); layout.addWidget(self.groups, 2)
        self.symmetry_note = QtWidgets.QLabel();self.symmetry_note.setWordWrap(True);layout.addWidget(self.symmetry_note)
        form = QtWidgets.QFormLayout(); layout.addLayout(form)
        self.name = QtWidgets.QLineEdit(); form.addRow('Group ID / name', self.name)
        self.group_summary = QtWidgets.QLabel('Select a group to edit its direction.');self.group_summary.setWordWrap(True)
        form.addRow(self.group_summary)
        self.direction = QtWidgets.QLineEdit('0 0 1'); form.addRow('Direction (Cartesian x y z)', self.direction)
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
        configure = QtWidgets.QPushButton('Configure MDFF for Group…');row.addWidget(configure)
        configure.clicked.connect(lambda:self.run_action(self.configure_mdff))
        recheck = QtWidgets.QPushButton('Recheck sources');row.addWidget(recheck)
        recheck.clicked.connect(self.recheck_mdff_sources)
        self.status.setWordWrap(True); layout.addWidget(self.status)
        self.atom_list.itemSelectionChanged.connect(self.emit_selection)
        self.filter.currentIndexChanged.connect(self.refresh_atoms)
        self.groups.currentItemChanged.connect(self.load_fields)
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
                      or self.reverse_magnetization != self._accepted_reversal)
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
                item = QtWidgets.QTreeWidgetItem([name, element, ', '.join(map(str,indices)),self.mdff_status(row)])
                provenance = self.crystallographic_provenance.get('groups',[])
                match = next((g for g in provenance if g['indices'] == list(indices) and g['element'] == element),None)
                item.setText(4,str(len(indices)));item.setText(5,match['wyckoff'] if match else 'Manual / edited')
                item.setToolTip(0,('Crystallographic orbit; CIF labels: '+', '.join(match['cif_labels'])) if match else 'Manual assignment')
                item.setToolTip(3,self._mdff_status.get(name,('',None,'No validated provider'))[2])
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
            self.group_summary.setText(f'Selected group: {current.text(0)} — {len(current.data(0, ROLE))} atoms. '
                + ('Magnetization unconfigured.' if direction is None else 'Direction applies to the whole group.'))

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
        self.selection_text.setText('Selected: ' + ', '.join(f'{i} {self.atoms[i].symbol}' for i in indices)
                                   if indices else 'No atoms selected')
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
        return validate_site_rows(self.atoms,rows)

    def replace_rows(self, rows, current=None):
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
        if any(row[3] is None for row in self.rows()):raise ValueError('Declare all local directions explicitly before reversing M')
        from .generalized_forward import ImportedSettings
        declared = [isinstance(row[4],ImportedSettings) for row in self.rows()]
        if any(declared):
            if not all(declared):raise ValueError('Configure all group MDFF providers before reversing their magnetic pairs')
            self.reverse_magnetization = not self.reverse_magnetization
            self.dirty = True;self.update_status();self.changed.emit();return
        self.replace_rows(tuple((name,element,indices,tuple(-v for v in direction),reference)
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

    def recheck_mdff_sources(self):
        from .group_mdff import validate_group_reference
        for row in self.rows():
            if row[4] is None:continue
            try:
                validate_group_reference(self.effective_row(row),window=self.energy_windows.get(row[0]));message = 'valid'
            except Exception as exc:message = str(exc)
            self._mdff_status[row[0]] = (row[1:4],row[4],message)
        # Refresh status cells only: never reset atom selection or current group.
        for i,row in enumerate(self.rows()):
            item = self.groups.topLevelItem(i);item.setText(3,self.mdff_status(row))
            item.setToolTip(3,self._mdff_status.get(row[0],('',None,''))[2])
        self.update_status()

    def configure_mdff(self):
        from .group_mdff import GroupMDFFDialog
        from .runtime import workspace
        row = self.effective_row(self.rows()[self.current_row()])
        if row[3] is None:raise ValueError('Declare this group\'s magnetic direction explicitly before configuring its MDFF')
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
        rows = tuple(self.effective_row(row) for row in self.rows())
        if not rows or any(not isinstance(r[4],ImportedSettings) for r in rows):return None
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
        missing = sum(row[4] is None for row in self.rows())
        undeclared = sum(row[3] is None for row in self.rows())
        prefix = 'Unapplied edits. ' if self.dirty else 'Applied in memory. '
        mode = 'Local mode. ' if self.magnetization_mode == 'local' else 'Global mode; local directions inactive. '
        if self.magnetization_mode == 'local':mode += ('All provider −M states selected. ' if self.reverse_magnetization else 'Declared +M configuration selected. ')
        invalid = sum(self.mdff_status(row) != 'Configured and valid' for row in self.rows())
        self.status.setText(mode + prefix + (f'{undeclared} group direction(s) undeclared. ' if undeclared else '') + (f'{missing} unconfigured group(s): MDFF references required; configuration is not executable.'
            if missing else ((f'{invalid} invalid/unvalidated provider(s); not ready for calculation.' if invalid else 'All group providers configured and valid. Apply before Run in the main window.')
                             if self.rows() else ('No local groups configured; local calculation unavailable.'
                                 if self.magnetization_mode == 'local' else 'No groups; ordinary CIF viewing.'))))

    def apply(self):
        from .generalized_forward import ImportedSettings
        from .group_mdff import validate_group_reference
        for name,dialog in self.mdff_dialogs.items():
            if name in {row[0] for row in self.rows()} and dialog.has_unapplied_edits():
                raise ValueError('Apply or Cancel pending MDFF edits for '+name+' before applying site groups')
        for row in self.rows():
            if isinstance(row[4],ImportedSettings):validate_group_reference(row,window=self.energy_windows.get(row[0]))
        model = self.check_rows(self.rows())
        self._accepted_rows = self.rows(); self.accepted_site_groups = self.preview_site_groups = model
        self._accepted_mode = self.magnetization_mode
        self._accepted_reversal = self.reverse_magnetization
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
