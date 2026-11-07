"""Consistent costume cards with undimmed artwork and readable identity."""
from PySide6 import QtCore, QtGui, QtWidgets as W


class SkinDelegate(W.QStyledItemDelegate):
    def __init__(self, window):
        super().__init__(window.grid)
        self.window = window
        self.pixmaps = {}

    def paint(self, painter, option, index):
        record = index.data(QtCore.Qt.ItemDataRole.UserRole)
        if not record:
            return
        dark = self.window.dark
        colors = self.window.theme_colors
        selected = bool(option.state & W.QStyle.StateFlag.State_Selected)
        current = bool(self.window.source and record['skin_path'] == self.window.source['skin_path'])
        hover = bool(option.state & W.QStyle.StateFlag.State_MouseOver)
        rect = QtCore.QRectF(option.rect).adjusted(4, 4, -4, -4)
        painter.save()
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        bg = colors['card']
        if hover:
            bg = colors['hover']
        if selected or current:
            bg = colors['active']
        painter.setBrush(QtGui.QColor(bg))
        painter.setPen(QtGui.QPen(QtGui.QColor(colors['primary'] if selected or current else colors['border']), 2 if selected else 1))
        painter.drawRoundedRect(rect, 22, 22)
        image_rect = rect.adjusted(13, 12, -13, -59)
        path = record.get('image', '')
        if path:
            if path not in self.pixmaps:
                self.pixmaps[path] = QtGui.QPixmap(path)
            pixmap = self.pixmaps[path]
            if not pixmap.isNull():
                scaled = pixmap.scaled(image_rect.size().toSize(), QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)
                painter.drawPixmap(int(image_rect.center().x() - scaled.width()/2), int(image_rect.center().y() - scaled.height()/2), scaled)
        else:
            painter.setPen(QtGui.QColor('#9aaac1' if dark else '#68788f'))
            painter.drawText(image_rect, QtCore.Qt.AlignmentFlag.AlignCenter, 'Sin miniatura')
        font = QtGui.QFont('Segoe UI', 9)
        font.setWeight(QtGui.QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(QtGui.QColor('#f3f7ff' if dark else '#172536'))
        name_rect = QtCore.QRectF(rect.left()+12, rect.bottom()-53, rect.width()-24, 25)
        name = painter.fontMetrics().elidedText(record['name'], QtCore.Qt.TextElideMode.ElideRight, int(name_rect.width()))
        painter.drawText(name_rect, QtCore.Qt.AlignmentFlag.AlignCenter, name)
        font.setPointSize(8)
        font.setWeight(QtGui.QFont.Weight.Normal)
        painter.setFont(font)
        painter.setPen(QtGui.QColor('#a8b7ca' if dark else '#64738a'))
        painter.drawText(QtCore.QRectF(rect.left()+8, rect.bottom()-28, rect.width()-16, 18), QtCore.Qt.AlignmentFlag.AlignCenter, record['id'])
        if current:
            badge = QtCore.QRectF(rect.left()+10, rect.top()+10, 66, 23)
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(QtGui.QColor(colors['primary']))
            painter.drawRoundedRect(badge, 8, 8)
            painter.setPen(QtGui.QColor('white'))
            painter.drawText(badge, QtCore.Qt.AlignmentFlag.AlignCenter, 'Current' if self.window.preferences.get('language') == 'en' else 'Actual')
        elif selected:
            circle = QtCore.QRectF(rect.right()-28, rect.top()+10, 19, 19)
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(QtGui.QColor(colors['primary']))
            painter.drawEllipse(circle)
            painter.setPen(QtGui.QPen(QtGui.QColor('white'), 2))
            painter.drawLine(circle.topLeft()+QtCore.QPointF(5,10), circle.topLeft()+QtCore.QPointF(8,13))
            painter.drawLine(circle.topLeft()+QtCore.QPointF(8,13), circle.topLeft()+QtCore.QPointF(14,6))
        painter.restore()
