"""Logical-pixel layout adaptation; never calls scientific update callbacks."""
from contextlib import contextmanager
from textwrap import fill
from PySide6 import QtCore, QtWidgets
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.gridspec import GridSpec


class ResponsiveCanvas(FigureCanvasQTAgg):
    """Keep Qt's native DPI sizing; coalesce expensive resize-only renders."""
    def __init__(self, figure):
        self._inside_resize = False
        super().__init__(figure)
        self._resize_timer = QtCore.QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(120)
        self._resize_timer.timeout.connect(super().draw_idle)

    def resizeEvent(self, event):
        self._inside_resize = True
        try:
            super().resizeEvent(event)
            if hasattr(self, 'presentation'):
                self.presentation.update()
        finally:
            self._inside_resize = False

    def draw_idle(self):
        timer = getattr(self, '_resize_timer', None)
        if timer is not None:
            if self._inside_resize:
                timer.start()
                return
            timer.stop()
        super().draw_idle()

    def print_figure(self, *args, **kwargs):
        if not hasattr(self, 'presentation'):
            return super().print_figure(*args, **kwargs)
        with self.presentation.export():
            return super().print_figure(*args, **kwargs)


class FigurePresentation:
    """Reflow existing artists, never rebuild plots or resample their data."""
    def __init__(self, canvas, kind, caption):
        self.canvas, self.kind, self.caption = canvas, kind, caption
        self.title = None
        self.specs, self.labels, self.maps = [], [], []
        self.narrow = None
        canvas.presentation = self

    def capture(self):
        fig = self.canvas.figure
        self.title = fig._suptitle
        self.full_title = self.title.get_text() if self.title is not None else ''
        self.caption.setText(self.full_title)
        self.specs = [(ax, ax.get_subplotspec()) for ax in fig.axes]
        self.labels = [(ax, ax.get_ylabel()) for ax in fig.axes]
        self.maps = [ax for ax in fig.axes if ax.images] if self.kind == 'maps' else []
        self.narrow = None
        self.update()

    def original(self):
        if self.title is not None:
            self.title.set_text(self.full_title)
        for ax, spec in self.specs:
            if spec is not None:
                ax.set_subplotspec(spec)
        for ax, label in self.labels:
            ax.set_ylabel(label)

    def update(self):
        narrow = self.canvas.width() < 650
        if narrow == self.narrow or self.title is None:
            return
        self.narrow = narrow
        self.original()
        if not narrow:
            return
        first = self.full_title.split('\n')[0]
        if len(first) > 90:
            first = ' | '.join(first.split(' | ')[:3])
        self.title.set_text(first)
        if len(self.maps) == 2 and all(ax.images[0].colorbar is not None for ax in self.maps):
            grid = GridSpec(2, 2, figure=self.canvas.figure, width_ratios=[1, .05])
            for row, ax in enumerate(self.maps):
                ax.set_subplotspec(grid[row, 0])
                ax.images[0].colorbar.ax.set_subplotspec(grid[row, 1])
        for ax, label in self.labels:
            ax.set_ylabel(fill(label, width=12))

    @contextmanager
    def export(self):
        # Save full scientific context at readable dimensions, then restore
        # precisely the same on-screen artists, geometry and compact caption.
        fig = self.canvas.figure
        size = fig.get_size_inches().copy()
        self.original()
        fig.set_size_inches(max(size[0], 10), max(size[1], 8), forward=False)
        try:
            yield
        finally:
            fig.set_size_inches(size, forward=False)
            self.narrow = None
            self.update()
            self.canvas.draw_idle()


class FlowLayout(QtWidgets.QLayout):
    """A short control row that wraps instead of imposing a wide minimum."""
    def __init__(self):
        super().__init__()
        self.items = []
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(6)

    def addItem(self, item):
        self.items.append(item)

    def insertWidget(self, index, widget):
        self.addChildWidget(widget)
        self.items.insert(index, QtWidgets.QWidgetItem(widget))
        self.invalidate()

    def count(self):
        return len(self.items)

    def itemAt(self, index):
        return self.items[index] if 0 <= index < len(self.items) else None

    def takeAt(self, index):
        return self.items.pop(index) if 0 <= index < len(self.items) else None

    def expandingDirections(self):
        return QtCore.Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self.arrange(QtCore.QRect(0, 0, width, 0), False)

    def minimumSize(self):
        size = QtCore.QSize()
        for item in self.items:
            if not item.isEmpty():
                size = size.expandedTo(item.minimumSize())
        return size

    def sizeHint(self):
        return self.minimumSize()

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.arrange(rect, True)

    def arrange(self, rect, apply):
        x, y, height = rect.x(), rect.y(), 0
        for item in self.items:
            if item.isEmpty():
                continue
            size = item.sizeHint()
            width = min(size.width(), rect.width())
            if x > rect.x() and x + width > rect.right() + 1:
                x, y, height = rect.x(), y + height + self.spacing(), 0
            if apply:
                item.setGeometry(QtCore.QRect(x, y, width, size.height()))
            x += width + self.spacing()
            height = max(height, size.height())
        return y - rect.y() + height


class CollapsibleSection(QtWidgets.QWidget):
    """A presentation-only chevron header around existing widgets."""
    toggled = QtCore.Signal(bool)

    def __init__(self, title, body=None, expanded=True, parent=None):
        super().__init__(parent)
        self.header = QtWidgets.QToolButton()
        self.header.setText(title)
        self.header.setCheckable(True)
        self.header.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.header.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.body = body if body is not None else QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self.header)
        layout.addWidget(self.body, 1)
        self.header.toggled.connect(self._toggle)
        self.setChecked(expanded)
        self._toggle(expanded)

    def _toggle(self, expanded):
        self.header.setArrowType(QtCore.Qt.ArrowType.DownArrow if expanded else QtCore.Qt.ArrowType.RightArrow)
        self.body.setVisible(expanded)
        self.toggled.emit(expanded)

    def isChecked(self):
        return self.header.isChecked()

    def setChecked(self, expanded):
        self.header.setChecked(bool(expanded))

    def title(self):
        return self.header.text()


class ResponsiveLayout(QtCore.QObject):
    """Keep scientific panels side by side; collapse only optional content."""
    DEFAULT_PROPORTIONS = [30, 35, 35]

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.compact = None
        self.screen = None
        self._applying = False
        self._results_user_choice = False
        self._focus_state = None
        tabs = window.tabs
        tabs.setParent(None)
        window.results_section = CollapsibleSection('EMCD Results', tabs)
        window.results_section.setObjectName('panel_results')
        window.splitter.addWidget(window.results_section)
        self.panels = [window.splitter.widget(i) for i in range(3)]
        self.panels[0].setMinimumWidth(280)
        self.panels[1].setMinimumWidth(300)
        tabs.setMinimumWidth(280)
        self.panels[2].setMinimumWidth(300)
        for i in range(3):
            window.splitter.setCollapsible(i, False)
            window.splitter.setStretchFactor(i, self.DEFAULT_PROPORTIONS[i])
        self.proportions = self.read_proportions()
        self.browser_section = CollapsibleSection('Project Results', window.browser, expanded=True)
        self.browser_section.setObjectName('panel_projects')
        window.browser_dock.setWidget(self.browser_section)
        title = QtWidgets.QWidget()
        title.setFixedHeight(0)
        window.browser_dock.setTitleBarWidget(title)
        for group in window.findChildren(QtWidgets.QGroupBox):
            if group.isCheckable() and not group.objectName():
                ancestor = group.parentWidget()
                while ancestor is not None and not hasattr(ancestor, 'kind'):
                    ancestor = ancestor.parentWidget()
                context = getattr(ancestor, 'kind', 'settings')
                key = ''.join(c if c.isalnum() else '_' for c in group.title())
                group.setObjectName('legacy_' + context + '_' + key)
        self.restore_sections()
        window.results_section.toggled.connect(self.results_toggled)
        self.browser_section.toggled.connect(self.browser_toggled)
        self.timer = QtCore.QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(120)
        self.timer.timeout.connect(self.update_layout)
        window.installEventFilter(self)
        self.panels[2].installEventFilter(self)
        window.splitter.splitterMoved.connect(self.splitter_moved)
        window.tabs.currentChanged.connect(lambda _: self.show_panel(2))
        self.fit_screen(window.screen())
        self._initial = True
        self.update_layout()
        self._initial = False
        self.apply_proportions()

    @staticmethod
    def valid_proportions(value):
        try:
            numbers = [float(x) for x in value]
            if len(numbers) != 3 or not all(0 < x < 1e7 for x in numbers):
                raise ValueError()
            total = sum(numbers)
            return [x / total for x in numbers]
        except (TypeError, ValueError, OverflowError):
            return [.30, .35, .35]

    def read_proportions(self):
        q = self.window.ui_settings
        return self.valid_proportions(q.value('layout/proportions', q.value('splitter', self.DEFAULT_PROPORTIONS)))

    def sections(self):
        w = self.window
        # Checkable group boxes contain legacy visibility-only subsections.
        return [s for s in w.findChildren(CollapsibleSection) if s.objectName()] + [
            s for s in w.findChildren(QtWidgets.QGroupBox) if s.isCheckable() and s.objectName()]

    def restore_sections(self):
        q = self.window.ui_settings
        for section in self.sections():
            key = 'layout/sections/' + section.objectName()
            value = q.value(key)
            if str(value).lower() in ('true', 'false', '1', '0'):
                section.setChecked(str(value).lower() in ('true', '1'))
        self._results_user_choice = q.contains('layout/results_expanded')
        if self._results_user_choice:
            value = q.value('layout/results_expanded')
            if str(value).lower() in ('true', 'false', '1', '0'):
                self.window.results_section.setChecked(str(value).lower() in ('true', '1'))
            else:
                self._results_user_choice = False

    def save_preferences(self):
        q = self.window.ui_settings
        q.setValue('layout/proportions', self.proportions)
        for section in self.sections():
            q.setValue('layout/sections/' + section.objectName(), section.isChecked())
        if self._results_user_choice:
            q.setValue('layout/results_expanded', self.window.results_section.isChecked())
        else:
            q.remove('layout/results_expanded')

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Type.Resize:
            if obj is self.window:
                self._window_resized = True
            self.timer.start()
        elif obj is self.window and event.type() == QtCore.QEvent.Type.Show:
            handle = self.window.windowHandle()
            if handle and not getattr(self, '_connected', False):
                handle.screenChanged.connect(self.monitor_changed)
                self._connected = True
                self.monitor_changed(handle.screen())
        return False

    def monitor_changed(self, screen):
        if self.screen is not None:
            try:
                self.screen.availableGeometryChanged.disconnect(self.screen_changed)
                self.screen.logicalDotsPerInchChanged.disconnect(self.screen_changed)
            except RuntimeError:
                pass
        self.screen = screen
        if screen is not None:
            screen.availableGeometryChanged.connect(self.screen_changed)
            screen.logicalDotsPerInchChanged.connect(self.screen_changed)
            self.fit_screen(screen)
        self.timer.start()
        QtCore.QTimer.singleShot(200, lambda: self.fit_screen(self.screen))

    def screen_changed(self, *_):
        self.fit_screen(self.screen)
        self.timer.start()
        QtCore.QTimer.singleShot(200, lambda: self.fit_screen(self.screen))

    def fit_screen(self, screen):
        if screen is None or self.window.isMaximized():
            return
        area = screen.availableGeometry().adjusted(8, 8, -8, -8)
        w = self.window
        w.layout().invalidate()
        w.layout().activate()
        frame = w.frameGeometry().size() - w.size()
        w.resize(min(w.width(), area.width() - frame.width()), min(w.height(), area.height() - frame.height()))
        pos = w.frameGeometry().topLeft()
        w.move(max(area.left(), min(pos.x(), area.right() - w.frameGeometry().width() + 1)),
               max(area.top(), min(pos.y(), area.bottom() - w.frameGeometry().height() + 1)))

    def splitter_moved(self, *_):
        if not self._applying:
            sizes = self.window.splitter.sizes()
            if self.window.results_section.isChecked():
                self.proportions = self.valid_proportions(sizes)
            elif sum(sizes[:2]) > 0:
                remaining = 1 - self.proportions[2]
                self.proportions[:2] = [remaining * x / sum(sizes[:2]) for x in sizes[:2]]
        self.timer.start()

    def apply_proportions(self):
        self._applying = True
        try:
            total = max(1, self.window.splitter.width() - 2 * self.window.splitter.handleWidth())
            if self.window.results_section.isChecked():
                sizes = [int(total * p) for p in self.proportions]
            else:
                left = self.proportions[0] + self.proportions[1]
                sizes = [int((total - 100) * self.proportions[0] / left),
                         int((total - 100) * self.proportions[1] / left), 100]
            self.window.splitter.setSizes(sizes)
        finally:
            self._applying = False

    def results_toggled(self, expanded):
        if not self._applying:
            self._results_user_choice = True
        panel = self.window.results_section
        panel.header.setText('EMCD Results' if expanded else 'Results')
        panel.header.setToolTip('Collapse EMCD Results' if expanded else 'Expand EMCD Results')
        panel.setMinimumWidth(300 if expanded else 100)
        panel.setMaximumWidth(16777215 if expanded else 100)
        self.apply_proportions()

    def browser_toggled(self, expanded):
        dock = self.window.browser_dock
        dock.setMaximumHeight(16777215 if expanded else self.browser_section.header.sizeHint().height() + 4)
        self.window.resizeDocks([dock], [min(190, max(95, self.window.height() // 5)) if expanded else 24], QtCore.Qt.Orientation.Vertical)

    def show_panel(self, index):
        if index == 2:
            self.window.results_section.setChecked(True)
        elif index == 3:
            self.window.browser_dock.show()
            self.browser_section.setChecked(True)

    def focus_plot(self, panel):
        # Vertical focus only: Settings and Diffraction always stay visible.
        if self._focus_state is None:
            self._focus_state = (self.browser_section.isChecked(), self.window.diffraction_details.isChecked())
            self.browser_section.setChecked(False)
            if panel == 'diffraction':
                self.window.diffraction_details.setChecked(False)
        else:
            browser, details = self._focus_state
            self._focus_state = None
            self.browser_section.setChecked(browser)
            self.window.diffraction_details.setChecked(details)

    def update_layout(self):
        w = self.window
        compact = w.width() < 1500 or w.height() < 760
        if compact != self.compact:
            self.compact = compact
            if getattr(self, '_initial', False):
                if not w.ui_settings.contains('layout/sections/panel_projects'):
                    self.browser_section.setChecked(not compact)
                if compact:
                    for section in w.inputs.findChildren(CollapsibleSection):
                        if (section.title().startswith('A.') or section.title() == 'Virtual detectors') and not w.ui_settings.contains('layout/sections/' + section.objectName()):
                            section.setChecked(False)
        self._applying = True
        try:
            if not self._results_user_choice:
                w.results_section.setChecked(w.width() >= 1050)
        finally:
            self._applying = False
        panel = w.results_section
        panel.header.setText('EMCD Results' if panel.isChecked() else 'Results')
        panel.setMinimumWidth(300 if panel.isChecked() else 100)
        panel.setMaximumWidth(16777215 if panel.isChecked() else 100)
        for view in (w.maps_view, w.eels_view, w.diffraction_view, w.overview_view):
            view.set_compact(compact or panel.width() < 650)
        w.form_layout.setContentsMargins(*((4, 4, 4, 4) if compact else (9, 9, 9, 9)))
        w.browser.set_compact(compact)
        self.browser_toggled(self.browser_section.isChecked())
        if getattr(self, '_window_resized', False):
            self._window_resized = False
            self.apply_proportions()

    def reset(self):
        self.proportions = [.30, .35, .35]
        self._results_user_choice = False
        self._applying = True
        try:
            self.window.results_section.setChecked(self.window.width() >= 1050)
        finally:
            self._applying = False
        self.browser_section.setChecked(not self.compact)
        self.apply_proportions()
        self.update_layout()

    def saved_splitter_sizes(self):
        return [max(1, round(p * 1000)) for p in self.proportions]
