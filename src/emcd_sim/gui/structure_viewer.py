"""Standalone crystal viewer and in-memory site editor using Qt projection.

Scene geometry is independent of the camera and painting, leaving a narrow
place for future per-site visuals without involving scientific calculations.
"""
from copy import deepcopy
from html import escape
import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets

from .structure_scene import build_scene, cell_segments, site_group_color
from .site_group_editor import SiteGroupEditor


def rotation(axis, degrees):
    angle = np.deg2rad(degrees); c, s = np.cos(angle), np.sin(angle)
    return (np.array([[1, 0, 0], [0, c, -s], [0, s, c]]) if axis == 'x'
            else np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]]))


class CrystalCanvas(QtWidgets.QWidget):
    atomSelected = QtCore.Signal(int)  # Rendered index; the scene supplies ASE identity/offset.
    atomPicked = QtCore.Signal(int, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('crystal_canvas')
        self.setMinimumSize(350, 300)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.scene = None
        self.space_filling = False
        self.show_bonds = self.show_cell = self.show_axes = True
        self.group_coloring = self.show_magnetization = False
        self.highlight_group = -1
        self.selected_indices = set()
        self._press = self._last = None
        self._dragged = False
        self.reset_camera()

    def reset_camera(self):
        self.orientation = rotation('x', 25) @ rotation('y', -35)
        self.zoom = 1.
        self.pan = np.zeros(2)
        self.update()

    def set_scene(self, scene):
        self.scene = scene
        expanded = scene.cell * np.asarray(scene.repetitions)[:, None]
        corners = cell_segments(expanded).reshape(-1, 3)
        points = np.concatenate((corners, scene.positions))
        lower, upper = points.min(axis=0), points.max(axis=0)
        self.center = (lower + upper) / 2
        padding = float(scene.space_radii.max()) if len(scene.positions) else 1.
        self.extent = max(float(np.linalg.norm(upper-lower)) / 2 + padding, 1.)
        self.reset_camera()

    def project(self, points):
        p = (np.asarray(points) - self.center) @ self.orientation.T
        distance = 4 * self.extent
        perspective = distance / (distance - p[..., 2])
        scale = .85 * min(self.width(), self.height()) / (2 * self.extent) * self.zoom
        xy = p[..., :2] * (scale * perspective)[..., None]
        xy[..., 1] *= -1
        xy += np.array([self.width()/2, self.height()/2]) + self.pan
        return xy, p[..., 2], scale * perspective

    def projected_atoms(self):
        xy, depth, scale = self.project(self.scene.positions)
        radii = self.scene.space_radii if self.space_filling else self.scene.ball_radii
        return xy, depth, np.maximum(radii * scale, 2.)

    def pick_atom(self, point):
        if self.scene is None:return None
        xy, depth, radii = self.projected_atoms()
        # Frontmost rendered sphere wins, matching paint order and occlusion.
        for i in np.argsort(depth, kind='stable')[::-1]:
            if np.sum((xy[i]-point)**2) <= radii[i]**2:return int(i)
        return None

    def magnetic_segments(self):
        """Equal-length Cartesian directions, never fractional lattice vectors."""
        scene = self.scene
        selected = np.flatnonzero((scene.group_indices >= 0) & (np.linalg.norm(scene.directions,axis=1)>0))
        length = 2.2 * float(scene.space_radii.max()) if len(scene.positions) else 1.
        starts = scene.positions[selected]
        return selected, np.stack((starts, starts + length * scene.directions[selected]), axis=1)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), QtGui.QColor('#f3f6fa'))
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        if self.scene is None:return
        scene = self.scene
        if self.show_cell:
            edges = cell_segments(scene.cell * np.asarray(scene.repetitions)[:, None])
            xy, _, _ = self.project(edges)
            painter.setPen(QtGui.QPen(QtGui.QColor('#8593a6'), 1.2, QtCore.Qt.PenStyle.DashLine))
            for edge in xy:painter.drawLine(QtCore.QPointF(*edge[0]), QtCore.QPointF(*edge[1]))
        xy, depth, radii = self.projected_atoms()
        # Shortened contacts avoid drawing through atom centers. Spheres are
        # then depth-sorted; this lightweight renderer is not a surface-mesh engine.
        if self.show_bonds:
            painter.setPen(QtGui.QPen(QtGui.QColor('#718096'), 2.2))
            for i, j in scene.bonds:
                direction = xy[j]-xy[i]; length = np.linalg.norm(direction)
                if length > radii[i]+radii[j]:
                    direction /= length
                    painter.drawLine(QtCore.QPointF(*(xy[i]+direction*radii[i])),
                                     QtCore.QPointF(*(xy[j]-direction*radii[j])))
        for i in np.argsort(depth, kind='stable'):
            x, y = xy[i]; radius = radii[i]
            if x+radius<0 or y+radius<0 or x-radius>self.width() or y-radius>self.height():continue
            colors = scene.group_colors if self.group_coloring else scene.colors
            color = QtGui.QColor.fromRgbF(*map(float, colors[i]))
            gradient = QtGui.QRadialGradient(QtCore.QPointF(x-radius*.3, y-radius*.3), radius*1.4)
            gradient.setColorAt(0, color.lighter(160)); gradient.setColorAt(.55, color)
            gradient.setColorAt(1, color.darker(175))
            painter.setBrush(QtGui.QBrush(gradient)); painter.setPen(QtGui.QPen(color.darker(160), .6))
            painter.drawEllipse(QtCore.QPointF(x, y), radius, radius)
            if int(scene.indices[i]) in self.selected_indices:
                painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
                painter.setPen(QtGui.QPen(QtGui.QColor('#086dcc'), 3.))
                painter.drawEllipse(QtCore.QPointF(x, y), radius+6, radius+6)
            if self.highlight_group >= 0 and scene.group_indices[i] == self.highlight_group:
                painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
                painter.setPen(QtGui.QPen(QtGui.QColor('#121c30'), 2.5))
                painter.drawEllipse(QtCore.QPointF(x, y), radius+3, radius+3)
        if self.show_magnetization:
            selected, segments = self.magnetic_segments()
            projected, _, _ = self.project(segments)
            for i, segment in zip(selected, projected):
                start, end = segment; delta = end-start; length = np.linalg.norm(delta)
                if length < 1:continue  # Direction is nearly along the viewing axis.
                unit = delta/length; side = np.array([-unit[1], unit[0]])
                color = QtGui.QColor.fromRgbF(*map(float, scene.group_colors[i])).darker(125)
                painter.setPen(QtGui.QPen(color, 2.5)); painter.setBrush(color)
                painter.drawLine(QtCore.QPointF(*start), QtCore.QPointF(*end))
                head = min(11., length*.35)
                painter.drawPolygon(QtGui.QPolygonF([QtCore.QPointF(*p) for p in
                    (end, end-head*unit+.45*head*side, end-head*unit-.45*head*side)]))
        if self.show_axes:
            projected, _, _ = self.project(np.vstack((np.zeros(3), scene.cell)))
            for i, (label, color) in enumerate(zip('abc', ('#be3030', '#21824c', '#285ec2')), 1):
                painter.setPen(QtGui.QPen(QtGui.QColor(color), 2.))
                painter.drawLine(QtCore.QPointF(*projected[0]), QtCore.QPointF(*projected[i]))
                painter.drawText(QtCore.QPointF(*(projected[i]+np.array([5., -5.]))), label)

    def mousePressEvent(self, event):
        self._press = self._last = np.array([event.position().x(), event.position().y()])
        self._dragged = False
        event.accept()

    def mouseMoveEvent(self, event):
        if self._last is None:return
        point = np.array([event.position().x(), event.position().y()]); delta = point-self._last
        self._last = point
        if np.linalg.norm(point-self._press) > QtWidgets.QApplication.startDragDistance():self._dragged = True
        if event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            self.orientation = rotation('x', delta[1]*.5) @ rotation('y', delta[0]*.5) @ self.orientation
        elif event.buttons() & (QtCore.Qt.MouseButton.MiddleButton | QtCore.Qt.MouseButton.RightButton):
            self.pan += delta
        self.update(); event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton and self._press is not None and not self._dragged:
            index = self.pick_atom(np.array([event.position().x(), event.position().y()]))
            if index is not None:
                self.atomSelected.emit(index)
                self.atomPicked.emit(index, bool(event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier))
        self._press = self._last = None
        event.accept()

    def wheelEvent(self, event):
        self.zoom = float(np.clip(self.zoom * np.exp(event.angleDelta().y()/120 * .15), .1, 20.))
        self.update(); event.accept()


class CrystalStructureDialog(QtWidgets.QDialog):
    """A modeless snapshot viewer; only Apply retains in-memory group edits."""
    siteGroupsApplied = QtCore.Signal(object)
    magnetizationModeChanged = QtCore.Signal(str)
    globalDirectionApplied = QtCore.Signal(object)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('3D Crystal Structure Viewer')
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowType.WindowMinMaxButtonsHint)
        self.resize(1200, 780); self.setMinimumSize(750, 480)
        self._source = None; self._atoms = None
        self._site_groups = None
        self._assignment_notice = ''
        layout = QtWidgets.QVBoxLayout(self)
        self.summary = QtWidgets.QLabel(); self.summary.setWordWrap(True); layout.addWidget(self.summary)
        splitter = QtWidgets.QSplitter(); layout.addWidget(splitter, 1)
        self.view = CrystalCanvas(); splitter.addWidget(self.view)
        self.tabs = QtWidgets.QTabWidget(); self.tabs.setMinimumWidth(430); splitter.addWidget(self.tabs)
        panel = QtWidgets.QWidget(); panel.setMinimumWidth(300)
        controls = QtWidgets.QVBoxLayout(panel)
        display_scroll = QtWidgets.QScrollArea(); display_scroll.setWidgetResizable(True); display_scroll.setWidget(panel)
        self.tabs.addTab(display_scroll, 'Display / atom info')
        self.editor = SiteGroupEditor()
        if getattr(parent,'workspace',None) is not None:self.editor.mdff_workspace = parent.workspace
        self.tabs.addTab(self.editor, 'Site groups')
        splitter.setSizes([700, 500])
        self.style = QtWidgets.QComboBox(); self.style.addItems(['Ball and stick', 'Space filling'])
        form = QtWidgets.QFormLayout(); form.setRowWrapPolicy(QtWidgets.QFormLayout.RowWrapPolicy.WrapAllRows)
        controls.addLayout(form); form.addRow('Atom style', self.style)
        self.color_mode = QtWidgets.QComboBox()
        self.color_mode.addItems(['Element Colors', 'Site Group Colors'])
        form.addRow('Atom colors', self.color_mode)
        self.color_mode.currentIndexChanged.connect(self.color_mode_changed)
        self.magnetic_arrows = QtWidgets.QCheckBox('Magnetic directions (equal-length arrows)')
        controls.addWidget(self.magnetic_arrows)
        self.magnetic_arrows.toggled.connect(lambda checked:self.display_option('show_magnetization', checked))
        direction_note = QtWidgets.QLabel('Declared crystal Cartesian directions only; arrow length is not a magnetic-moment magnitude. Arrows are drawn over atoms for visibility.')
        direction_note.setWordWrap(True); controls.addWidget(direction_note)
        self.group_list = QtWidgets.QListWidget(); self.group_list.setMaximumHeight(95)
        controls.addWidget(self.group_list)
        self.group_list.currentRowChanged.connect(self.select_group)
        repeats = QtWidgets.QWidget(); row = QtWidgets.QHBoxLayout(repeats); row.setContentsMargins(0, 0, 0, 0)
        self.repeats = []
        for label in 'abc':
            row.addWidget(QtWidgets.QLabel(label))
            box = QtWidgets.QSpinBox(); box.setRange(1, 4)
            box.setMinimumWidth(max(72,box.sizeHint().width())); row.addWidget(box); self.repeats.append(box)
            box.valueChanged.connect(self.rebuild)
        form.addRow('Display repetitions', repeats)
        presets = QtWidgets.QHBoxLayout(); controls.addLayout(presets)
        for text, repetitions in [('1×1×1', 1), ('2×2×2', 2)]:
            button = QtWidgets.QPushButton(text); presets.addWidget(button)
            button.clicked.connect(lambda checked=False, n=repetitions:self.set_repetitions((n, n, n)))
        for attribute, text in [('show_bonds', 'Geometric bonds'), ('show_cell', 'Cell boundary'), ('show_axes', 'Crystal axes a, b, c')]:
            box = QtWidgets.QCheckBox(text); box.setChecked(True); controls.addWidget(box)
            box.toggled.connect(lambda checked, name=attribute:self.display_option(name, checked))
        reset = QtWidgets.QPushButton('Reset / fit view'); controls.addWidget(reset); reset.clicked.connect(self.view.reset_camera)
        help_text = QtWidgets.QLabel('Left drag: rotate · Right/middle drag: pan\nWheel: zoom · Click an atom: inspect\nBonds are geometric contacts, not bond orders.')
        help_text.setWordWrap(True); controls.addWidget(help_text)
        self.legend = QtWidgets.QLabel(); self.legend.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self.legend.setWordWrap(True); controls.addWidget(self.legend)
        controls.addWidget(QtWidgets.QLabel('Atom information'))
        self.atom_info = QtWidgets.QPlainTextEdit(); self.atom_info.setReadOnly(True)
        self.atom_info.setPlaceholderText('Click a rendered atom to inspect its original ASE identity and replica offset.')
        controls.addWidget(self.atom_info, 1)
        self.notice = QtWidgets.QLabel(); self.notice.setWordWrap(True); controls.addWidget(self.notice)
        self.dialog_buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Apply | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        self.dialog_buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply_groups)
        self.dialog_buttons.rejected.connect(self.reject); layout.addWidget(self.dialog_buttons)
        self.style.currentIndexChanged.connect(self.atom_style_changed)
        self.view.atomSelected.connect(self.inspect_atom)
        self.view.atomPicked.connect(self.pick_rendered_atom)
        self.editor.selectionChanged.connect(self.highlight_selection)
        self.editor.changed.connect(self.rebuild)
        self.editor.applied.connect(self.groups_applied)
        self.editor.modeChanged.connect(self.magnetization_mode_changed)
        self._global_direction=(0.,0.,1.)
        self.global_direction=QtWidgets.QLineEdit('0 0 1')
        self.global_direction.setToolTip('Legacy Global M in crystal Cartesian coordinates. Apply accepts; Cancel discards this input. Inactive in Local mode.')
        self.global_direction_box=QtWidgets.QWidget()
        form=QtWidgets.QFormLayout(self.global_direction_box);form.setContentsMargins(0,0,0,0)
        form.addRow('Global Material M (x y z)',self.global_direction)
        self.editor.widget().layout().insertWidget(2,self.global_direction_box)
        self.global_direction.textChanged.connect(lambda _:self.editor.pendingChanged.emit())

    @property
    def pending_global_direction(self):
        if self.editor.magnetization_mode!='global':return False
        try:return tuple(float(v) for v in self.global_direction.text().replace(',',' ').split())!=self._global_direction
        except ValueError:return True

    def set_global_direction(self,direction):
        direction=tuple(direction)
        if direction!=self._global_direction:
            self._global_direction=direction
            with QtCore.QSignalBlocker(self.global_direction):self.global_direction.setText(' '.join(f'{v:.17g}' for v in direction))
        self.global_direction.setEnabled(self.editor.magnetization_mode=='global')

    def set_structure(self, structure, force=False):
        if not force and structure is self._source:return
        replacement = self._source is not None and structure is not self._source
        self._source = structure
        atoms = getattr(structure, 'atoms', structure)
        changed_geometry = self._atoms is not None and not self._atoms == atoms
        self._assignment_notice = ''
        if self._site_groups is not None:
            try:self._site_groups.validate_structure(atoms)
            except ValueError:
                self._site_groups = None
                self._assignment_notice = 'Site-group overlay cleared: assignments do not match the current structure.'
        self._atoms = atoms.copy(); self._atoms.info = deepcopy(atoms.info)
        if (replacement or changed_geometry) and self.editor.rows():
            # Drafts have no bound Stage 1 model: never carry them to another CIF.
            if any(row[4] is None for row in self.editor.rows()):
                self._site_groups = None
                self._assignment_notice = 'Site-group drafts cleared for the replacement structure.'
        if (replacement or changed_geometry or self.editor.atoms is None
                or self.editor.accepted_site_groups is not self._site_groups):
            self.editor.set_structure(self._atoms,self._site_groups)
        else:
            self.editor.atoms = self._atoms
        if (not self.editor.rows() and not self.editor.crystallographic_provenance
                and 'crystallographic_sites' in self._atoms.info):
            self.editor.suggest_crystallographic_groups(self._atoms.info['crystallographic_sites'])
        self.atom_info.clear()
        self.rebuild()

    def set_site_groups(self, site_groups=None):
        """Read-only optional MultiSiteIonization input; no provider loading.

        Call after set_structure. None restores ordinary structural display.
        Invalid assignments leave the currently displayed configuration intact.
        """
        if self._atoms is None:
            raise ValueError('Set the displayed structure before site groups')
        from ..multisite import MultiSiteIonization
        if site_groups is not None:
            if not isinstance(site_groups, MultiSiteIonization):
                raise TypeError('Expected MultiSiteIonization or None')
            site_groups.validate_structure(self._atoms)
        self._site_groups = site_groups
        self.editor.load_groups(site_groups)
        self._assignment_notice = ''
        self.rebuild()

    def set_repetitions(self, repetitions):
        for box, count in zip(self.repeats, repetitions):
            with QtCore.QSignalBlocker(box):box.setValue(count)
        self.rebuild()

    def rebuild(self, *_):
        if self._atoms is None:return
        model = self.editor.preview_site_groups
        try:scene = build_scene(self._atoms, tuple(box.value() for box in self.repeats), model)
        except ValueError as exc:
            self.view.scene = None; self.view.update(); self.notice.setText(str(exc)); return
        rows = self.editor.rows()
        if rows:
            # Draft visualization only: no placeholder provider or executable model.
            for number, (_,_,indices,direction,reference) in enumerate(rows):
                mask = np.isin(scene.indices,indices)
                scene.group_indices[mask] = number
                scene.group_colors[mask] = site_group_color(number)
                scene.directions[mask]=0
                if direction is not None and getattr(reference,'magnetic_state',None)!='nonmagnetic':scene.directions[mask] = direction
        if self.editor.reverse_magnetization:scene.directions[:] *= -1
        camera = (self.view.orientation.copy(),self.view.zoom,self.view.pan.copy())
        had_scene = self.view.scene is not None
        self.view.set_scene(scene)
        if had_scene and self.editor.dirty:
            self.view.orientation,self.view.zoom,self.view.pan = camera
        self.atom_info.clear()
        self.summary.setText(f'{self._atoms.get_chemical_formula()} · {len(self._atoms)} original ASE atoms · '
                             f'{len(scene.positions)} displayed atoms · repetitions {scene.repetitions}')
        self.notice.setText('\n'.join(scene.notices) + ('\n'+self._source.import_warnings if getattr(self._source, 'import_warnings', '') else '') + '\n' + self._assignment_notice)
        self.group_list.clear(); self.view.highlight_group = -1
        if rows:
            self.group_list.addItem('All groups / no highlight')
            for number, (name,element,indices,_,reference) in enumerate(rows):
                suffix = ' — excluded from ionization' if name in self.editor.excluded_groups else ' — unconfigured MDFF' if reference is None else ''
                item = QtWidgets.QListWidgetItem(f'{name} ({element}, {len(indices)} atoms){suffix}')
                color = QtGui.QColor.fromRgbF(*site_group_color(number))
                icon = QtGui.QPixmap(14,14); icon.fill(color); item.setIcon(QtGui.QIcon(icon))
                self.group_list.addItem(item)
            self.group_list.setCurrentRow(0)
        self.group_list.setVisible(bool(rows))
        if not rows:
            self.color_mode.setCurrentIndex(0)
            self.magnetic_arrows.setChecked(False)
        self.color_mode.setEnabled(bool(rows))
        self.magnetic_arrows.setEnabled(bool(rows) and self.editor.magnetization_mode == 'local')
        self.update_legend()

    def select_group(self, row):
        self.view.highlight_group = row-1 if row > 0 else -1
        self.view.update()

    def color_mode_changed(self, index):
        self.view.group_coloring = index == 1
        self.update_legend(); self.view.update()

    def update_legend(self):
        scene = self.view.scene
        if scene is None:return
        if self.color_mode.currentIndex() == 1 and self.editor.rows():
            entries = [(row[0], QtGui.QColor.fromRgbF(*site_group_color(n)).name())
                       for n, row in enumerate(self.editor.rows())]
            entries.append(('Unassigned / non-ionizing', '#a6a6a6'))
            self.legend.setText(' · '.join(f'<span style="color:{color}">●</span> {escape(label)}' for label,color in entries))
            return
        colors = {symbol:QtGui.QColor.fromRgbF(*map(float, color)).name() for symbol, color in zip(scene.symbols, scene.colors)}
        self.legend.setText(' · '.join(f'<span style="color:{color}">●</span> {symbol}' for symbol, color in sorted(colors.items())))

    def atom_style_changed(self, index):
        self.view.space_filling = index == 1; self.view.update()

    def display_option(self, attribute, checked):
        if attribute == 'show_magnetization':
            checked = checked and self.editor.magnetization_mode == 'local'
        setattr(self.view, attribute, checked); self.view.update()

    def set_magnetization_mode(self, mode):
        if mode not in ('global','local'):raise ValueError('Expected global or local magnetization mode')
        self.editor.mode.setCurrentIndex(int(mode == 'local'))

    def magnetization_mode_changed(self, mode):
        if hasattr(self,'global_direction'):self.global_direction.setEnabled(mode=='global')
        self.magnetic_arrows.setEnabled(bool(self.editor.rows()) and mode == 'local')
        self.view.show_magnetization = self.magnetic_arrows.isChecked() and mode == 'local'
        self.view.update(); self.magnetizationModeChanged.emit(mode)

    def inspect_atom(self, rendered_index):
        scene = self.view.scene; i = rendered_index
        if scene is None or not 0 <= i < len(scene.positions):return
        vector = lambda values:' '.join(f'{value:.8g}' for value in values)
        occupancy = scene.occupancies[i]
        number = scene.group_indices[i]
        rows = self.editor.rows()
        row = rows[number] if 0 <= number < len(rows) else None
        assignment = (f'\nSelected ionizing group: {"Unconfigured crystallographic draft" if row[3] is None else "Yes"}\nSite-group ID / label: {row[0]}\n'
            f'Declared magnetization (crystal Cartesian unit vector): {vector(row[3]) if row[3] is not None else "Unconfigured; structural group only"}\n'
            f'MDFF provider reference: {str(row[4])[:300] if row[4] is not None else "Unconfigured — not executable"}' if row is not None
            else '\nSelected ionizing group: No (unassigned)')
        self.atom_info.setPlainText(
            f'Element: {scene.symbols[i]}\nOriginal ASE index (zero-based): {scene.indices[i]}\n'
            f'Unit-cell fractional coordinates: {vector(scene.fractional[i])}\n'
            f'Original Cartesian coordinates (Å): {vector(scene.original_positions[i])}\n'
            f'Replica translation (a,b,c): {tuple(int(n) for n in scene.offsets[i])}\n'
            f'Displayed Cartesian coordinates (Å): {vector(scene.positions[i])}\n'
            f'Occupancy metadata: {occupancy if occupancy else "Not supplied; none inferred"}' + assignment)

    @property
    def accepted_site_groups(self):
        """Stage 1 model only when all applied rows have real MDFF references."""
        return self.editor.accepted_site_groups

    def highlight_selection(self, indices):
        self.view.selected_indices = set(indices); self.view.update()
        if indices and self.view.scene is not None and not getattr(self,'_picking',False):
            matches = np.flatnonzero(self.view.scene.indices == indices[-1])
            if len(matches):self.inspect_atom(int(matches[0]))

    def pick_rendered_atom(self, rendered_index, additive):
        self._picking = True
        try:self.editor.pick_atom(int(self.view.scene.indices[rendered_index]),additive)
        finally:self._picking = False

    def groups_applied(self, model):
        self._site_groups = model
        self.rebuild(); self.siteGroupsApplied.emit(model)

    def apply_groups(self):
        def apply():
            direction=None
            if self.editor.magnetization_mode=='global':
                direction=tuple(float(v) for v in self.global_direction.text().replace(',',' ').split())
                a=np.asarray(direction)
                if a.shape!=(3,) or not np.isfinite(a).all() or np.linalg.norm(a)<1e-12:
                    raise ValueError('Global Material M requires three finite nonzero crystal Cartesian components')
            self.editor.apply()
            if direction is not None:
                self._global_direction=direction;self.globalDirectionApplied.emit(direction)
        self.editor.run_action(apply)

    def reject(self):
        self.close()

    def closeEvent(self, event):
        self.editor.cancel()
        self.global_direction.setText(' '.join(f'{v:.17g}' for v in self._global_direction))
        event.accept()
