"""Shared three-model workspace; controllers retain provider construction."""
from PySide6 import QtCore,QtWidgets


class MDFFWorkspace(QtWidgets.QDialog):
    def showEvent(self,event):
        from .parameter_wheel import protect_parameter_wheels
        protect_parameter_wheels(self)
        super().showEvent(event)

    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWindowTitle('MDFF Configuration')
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowType.WindowMinMaxButtonsHint)
        area=QtWidgets.QApplication.primaryScreen().availableGeometry()
        self.resize(min(1120,area.width()-50),min(760,area.height()-50))
        self.outer=QtWidgets.QVBoxLayout(self)
        self._window=None;self._context_id=None

    def mount_editor(self,material,model,pages,target,description=None):
        box=QtWidgets.QGroupBox('Material and Editing Context');form=QtWidgets.QFormLayout(box)
        self.material_label=QtWidgets.QLabel(material);self.material_label.setWordWrap(True);form.addRow(self.material_label)
        self.context_selector=QtWidgets.QComboBox();form.addRow('MDFF editing context',self.context_selector)
        self.context_selector.addItem('Current context');self.context_selector.setEnabled(False)
        self.outer.addWidget(box)
        box=QtWidgets.QGroupBox('Model');form=QtWidgets.QFormLayout(box)
        form.addRow('MDFF model',model)
        if description is not None:form.addRow(description)
        form.addRow(target);self.outer.addWidget(box)
        scroll=QtWidgets.QScrollArea();scroll.setWidgetResizable(True)
        body=QtWidgets.QWidget();self.science_layout=QtWidgets.QVBoxLayout(body)
        self.science_layout.addWidget(pages);scroll.setWidget(body);self.outer.addWidget(scroll,1)
        self.scroll=scroll
        self.context_selector.currentIndexChanged.connect(self.switch_context)

    def set_context_choices(self,window,group_id=None):
        self._window=window;self._context_id=group_id
        self.material_label.setText(window.structure_label.text())
        with QtCore.QSignalBlocker(self.context_selector):
            self.context_selector.clear();self.context_selector.addItem('Global Material configuration',None)
            viewer=getattr(window,'structure_viewer',None)
            for row in viewer.editor.rows() if viewer is not None else ():self.context_selector.addItem('Site group: '+row[0],row[0])
            self.context_selector.setCurrentIndex(self.context_selector.findData(group_id))
        self.context_selector.setEnabled(True)

    def switch_context(self,index):
        if self._window is None:return
        target=self.context_selector.itemData(index)
        if target==self._context_id:return
        if not self.confirm_context_exit():
            with QtCore.QSignalBlocker(self.context_selector):self.context_selector.setCurrentIndex(self.context_selector.findData(self._context_id))
            return
        self.hide();self._window.open_mdff_context(target)

    def confirm_context_exit(self):
        if self.has_unapplied_edits():
            answer=QtWidgets.QMessageBox.question(self,'Unapplied MDFF edits',
                'Apply these MDFF edits, discard them, or cancel the context switch?',
                QtWidgets.QMessageBox.StandardButton.Apply | QtWidgets.QMessageBox.StandardButton.Discard | QtWidgets.QMessageBox.StandardButton.Cancel,
                QtWidgets.QMessageBox.StandardButton.Cancel)
            if answer==QtWidgets.QMessageBox.StandardButton.Apply:
                ok=self.apply_configuration() is not None
            elif answer==QtWidgets.QMessageBox.StandardButton.Discard:
                self.reject();ok=True
            else:ok=False
            return ok
        return True
