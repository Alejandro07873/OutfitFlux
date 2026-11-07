"""Shared Qt helpers for the Studio shell."""
from PySide6 import QtCore, QtWidgets as W


def label(text, name=None):
    widget = W.QLabel(text)
    widget.setWordWrap(True)
    if name:
        widget.setObjectName(name)
    return widget


class StudioBase(W.QMainWindow):
    def set_target(self):
        item = self.grid.currentItem()
        if item and not item.isHidden():
            self.target = item.data(QtCore.Qt.ItemDataRole.UserRole)
            self.update_summary()
