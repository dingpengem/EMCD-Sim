"""Wheel protection on parameter controls, leaving canvases and lists alone."""
from PySide6 import QtCore, QtGui, QtWidgets


class ParameterWheelGuard(QtCore.QObject):
    def eventFilter(self,control,event):
        if event.type()!=QtCore.QEvent.Type.Wheel:return False
        if isinstance(control,QtWidgets.QComboBox) and control.view().isVisible():return False
        parent=control.parentWidget()
        while parent is not None:
            if isinstance(parent,QtWidgets.QAbstractScrollArea):
                viewport=parent.viewport()
                forwarded=QtGui.QWheelEvent(QtCore.QPointF(viewport.mapFromGlobal(event.globalPosition().toPoint())),
                    event.globalPosition(),event.pixelDelta(),event.angleDelta(),event.buttons(),event.modifiers(),
                    event.phase(),event.inverted(),event.source(),event.pointingDevice())
                QtWidgets.QApplication.sendEvent(viewport,forwarded)
                break
            parent=parent.parentWidget()
        event.accept()
        return True


def protect_parameter_wheels(root):
    """Install on this form's controls; call again after adding dynamic fields."""
    controls=root.findChildren(QtWidgets.QAbstractSpinBox)+root.findChildren(QtWidgets.QComboBox)
    for control in controls:
        if getattr(control,'_parameter_wheel_guard',None) is None:
            guard=ParameterWheelGuard(control);control.installEventFilter(guard)
            control._parameter_wheel_guard=guard
