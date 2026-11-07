"""Standalone, read-only crystal viewer using Qt software 3D projection.

Scene geometry is independent of the camera and painting, leaving a narrow
place for future per-site visuals without involving scientific calculations.
"""
from copy import deepcopy
import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets

from .structure_scene import build_scene, cell_segments


def rotation(axis, degrees):
    angle = np.deg2rad(degrees); c, s = np.cos(angle), np.sin(angle)
    return (np.array([[1, 0, 0], [0, c, -s], [0, s, c]]) if axis == 'x'
            else np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]]))


class CrystalCanvas(QtWidgets.QWidget):
    atomSelected = QtCore.Signal(int)  # Rendered index; the scene supplies ASE identity/offset.

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('crystal_canvas')
        self.setMinimumSize(350, 300)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.scene = None
        self.space_filling = False
        self.show_bonds = self.show_cell = self.show_axes = True
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
            color = QtGui.QColor.fromRgbF(*map(float, scene.colors[i]))
            gradient = QtGui.QRadialGradient(QtCore.QPointF(x-radius*.3, y-radius*.3), radius*1.4)
            gradient.setColorAt(0, color.lighter(160)); gradient.setColorAt(.55, color)
            gradient.setColorAt(1, color.darker(175))
            painter.setBrush(QtGui.QBrush(gradient)); painter.setPen(QtGui.QPen(color.darker(160), .6))
            painter.drawEllipse(QtCore.QPointF(x, y), radius, radius)
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
            if index is not None:self.atomSelected.emit(index)
        self._press = self._last = None
        event.accept()

    def wheelEvent(self, event):
        self.zoom = float(np.clip(self.zoom * np.exp(event.angleDelta().y()/120 * .15), .1, 20.))
        self.update(); event.accept()


class CrystalStructureDialog(QtWidgets.QDialog):
    """A modeless snapshot viewer: closing never writes into the simulation."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('3D Crystal Structure Viewer')
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowType.WindowMinMaxButtonsHint)
        self.resize(1200, 780); self.setMinimumSize(750, 480)
        self._source = None; self._atoms = None
        layout = QtWidgets.QVBoxLayout(self)
        self.summary = QtWidgets.QLabel(); self.summary.setWordWrap(True); layout.addWidget(self.summary)
        splitter = QtWidgets.QSplitter(); layout.addWidget(splitter, 1)
        self.view = CrystalCanvas(); splitter.addWidget(self.view)
        panel = QtWidgets.QWidget(); panel.setMinimumWidth(300)
        controls = QtWidgets.QVBoxLayout(panel); splitter.addWidget(panel); splitter.setSizes([850, 320])
        self.style = QtWidgets.QComboBox(); self.style.addItems(['Ball and stick', 'Space filling'])
        form = QtWidgets.QFormLayout(); form.setRowWrapPolicy(QtWidgets.QFormLayout.RowWrapPolicy.WrapAllRows)
        controls.addLayout(form); form.addRow('Atom style', self.style)
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
        close = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.close); layout.addWidget(close)
        self.style.currentIndexChanged.connect(self.atom_style_changed)
        self.view.atomSelected.connect(self.inspect_atom)

    def set_structure(self, structure, force=False):
        if not force and structure is self._source:return
        self._source = structure
        atoms = getattr(structure, 'atoms', structure)
        self._atoms = atoms.copy(); self._atoms.info = deepcopy(atoms.info)
        self.atom_info.clear()
        self.rebuild()

    def set_repetitions(self, repetitions):
        for box, count in zip(self.repeats, repetitions):
            with QtCore.QSignalBlocker(box):box.setValue(count)
        self.rebuild()

    def rebuild(self, *_):
        if self._atoms is None:return
        try:scene = build_scene(self._atoms, tuple(box.value() for box in self.repeats))
        except ValueError as exc:
            self.view.scene = None; self.view.update(); self.notice.setText(str(exc)); return
        self.view.set_scene(scene); self.atom_info.clear()
        self.summary.setText(f'{self._atoms.get_chemical_formula()} · {len(self._atoms)} original ASE atoms · '
                             f'{len(scene.positions)} displayed atoms · repetitions {scene.repetitions}')
        self.notice.setText('\n'.join(scene.notices) + ('\n'+self._source.import_warnings if getattr(self._source, 'import_warnings', '') else ''))
        colors = {symbol:QtGui.QColor.fromRgbF(*map(float, color)).name() for symbol, color in zip(scene.symbols, scene.colors)}
        self.legend.setText(' · '.join(f'<span style="color:{color}">●</span> {symbol}' for symbol, color in sorted(colors.items())))

    def atom_style_changed(self, index):
        self.view.space_filling = index == 1; self.view.update()

    def display_option(self, attribute, checked):
        setattr(self.view, attribute, checked); self.view.update()

    def inspect_atom(self, rendered_index):
        scene = self.view.scene; i = rendered_index
        if scene is None or not 0 <= i < len(scene.positions):return
        vector = lambda values:' '.join(f'{value:.8g}' for value in values)
        occupancy = scene.occupancies[i]
        self.atom_info.setPlainText(
            f'Element: {scene.symbols[i]}\nOriginal ASE index (zero-based): {scene.indices[i]}\n'
            f'Unit-cell fractional coordinates: {vector(scene.fractional[i])}\n'
            f'Original Cartesian coordinates (Å): {vector(scene.original_positions[i])}\n'
            f'Replica translation (a,b,c): {tuple(int(n) for n in scene.offsets[i])}\n'
            f'Displayed Cartesian coordinates (Å): {vector(scene.positions[i])}\n'
            f'Occupancy metadata: {occupancy if occupancy else "Not supplied; none inferred"}')
