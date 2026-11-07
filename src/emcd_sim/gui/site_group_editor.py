"""Transient site-group form state; executable groups use the Stage 1 model.

Missing MDFF references remain None in Qt item data, never synthetic providers.
The applied form snapshot also retains incomplete rows for the later MDFF UI.
"""
import numpy as np
from PySide6 import QtCore, QtWidgets

from ..multisite import IonizationSiteGroup, MultiSiteIonization, _ordered_atoms


ROLE = QtCore.Qt.ItemDataRole.UserRole


class SiteGroupEditor(QtWidgets.QWidget):
    changed = QtCore.Signal()
    selectionChanged = QtCore.Signal(object)
    applied = QtCore.Signal(object)  # None means no executable configuration.
    modeChanged = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.atoms = None
        self.accepted_site_groups = None
        self.preview_site_groups = None
        self._accepted_rows = ()
        self.dirty = False
        self._accepted_mode = 'global'
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
        self.groups.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.groups.setRootIsDecorated(False); layout.addWidget(self.groups, 2)
        form = QtWidgets.QFormLayout(); layout.addLayout(form)
        self.name = QtWidgets.QLineEdit(); form.addRow('Group ID / name', self.name)
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
        self.dirty = self.rows() != self._accepted_rows or self.magnetization_mode != self._accepted_mode
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
        with QtCore.QSignalBlocker(self.groups):
            self.groups.clear()
            for name, element, indices, direction, reference in rows:
                item = QtWidgets.QTreeWidgetItem([name, element, ', '.join(map(str,indices)),
                    'Unconfigured' if reference is None else 'Reference supplied'])
                item.setData(0, ROLE, tuple(indices)); item.setData(1, ROLE, tuple(direction))
                # A tuple keeps arbitrary Python references intact; a bare dict
                # is otherwise converted to a copied QVariantMap by Qt.
                item.setData(2, ROLE, (reference,)); self.groups.addTopLevelItem(item)
        self.refresh_atoms()
        if rows:
            self.groups.setCurrentItem(self.groups.topLevelItem(0))
        else:
            self.name.clear(); self.direction.setText('0 0 1')

    def set_structure(self, atoms, groups=None):
        self.atoms = atoms
        self.load_groups(groups)

    def load_groups(self, groups):
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
            self.direction.setText(' '.join(f'{v:.8g}' for v in current.data(1, ROLE)))

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
        if not rows:return None
        _ordered_atoms(self.atoms)  # Same ordered/full-occupancy rules as Stage 1.
        names = set(); assigned = set(); complete = []
        for name, element, indices, direction, reference in rows:
            if not name.strip() or name in names:raise ValueError('Group IDs must be nonempty and unique')
            names.add(name)
            if not indices:raise ValueError('Groups need at least one atom; delete an empty group instead')
            if len(set(indices)) != len(indices) or assigned.intersection(indices):
                raise ValueError('Duplicate assignments: remove atoms from their current group first')
            if any(i < 0 or i >= len(self.atoms) or self.atoms[i].symbol != element for i in indices):
                raise ValueError('Each group must contain valid original indices of one element')
            assigned.update(indices)
            vector = np.asarray(direction)
            if vector.shape != (3,) or not np.isfinite(vector).all() or not np.any(vector):
                raise ValueError('A finite nonzero magnetization direction is required')
            if reference is not None:
                complete.append(IonizationSiteGroup(name,element,indices,reference,direction,len(indices)))
        # Complete rows are always checked by the actual model, even alongside drafts.
        model = MultiSiteIonization(self.atoms,complete) if complete else None
        return model if len(complete) == len(rows) else None

    def replace_rows(self, rows, current=None):
        self.preview_site_groups = self.check_rows(rows)
        self.restore_rows(rows); self.dirty = True
        if current is not None and current < self.groups.topLevelItemCount():
            self.groups.setCurrentItem(self.groups.topLevelItem(current))
        self.update_status(); self.changed.emit()

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
        rows[row] = (self.name.text().strip(),) + rows[row][1:]
        self.replace_rows(rows,row)

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
        self.replace_rows(tuple((name,element,indices,tuple(-v for v in direction),reference)
            for name,element,indices,direction,reference in self.rows()), self.current_row())

    def set_mdff_reference(self, group_id, reference):
        """Handoff for the later MDFF interface; no provider creation/evaluation."""
        rows = list(self.rows())
        row = next((i for i,r in enumerate(rows) if r[0] == group_id),None)
        if row is None:raise ValueError('Unknown site-group ID')
        rows[row] = rows[row][:4] + (reference,)
        self.replace_rows(rows,row)

    def update_status(self):
        missing = sum(row[4] is None for row in self.rows())
        prefix = 'Unapplied edits. ' if self.dirty else 'Applied in memory. '
        mode = 'Local mode. ' if self.magnetization_mode == 'local' else 'Global mode; local directions inactive. '
        self.status.setText(mode + prefix + (f'{missing} unconfigured group(s): MDFF references required; configuration is not executable.'
            if missing else ('References supplied; source and tensor-frame validation belongs to the MDFF interface.'
                             if self.rows() else ('No local groups configured; local calculation unavailable.'
                                 if self.magnetization_mode == 'local' else 'No groups; ordinary CIF viewing.'))))

    def apply(self):
        model = self.check_rows(self.rows())
        self._accepted_rows = self.rows(); self.accepted_site_groups = self.preview_site_groups = model
        self._accepted_mode = self.magnetization_mode
        self.dirty = False; self.update_status(); self.applied.emit(model)
        return model

    def cancel(self):
        self.preview_site_groups = self.accepted_site_groups
        self.restore_rows(self._accepted_rows); self.dirty = False
        self.mode.setCurrentIndex(int(self._accepted_mode == 'local'))
        self.update_status(); self.changed.emit()
