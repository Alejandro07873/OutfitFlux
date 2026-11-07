"""Animated gradient clipped to the wordmark glyphs; no raster assets needed."""
from PySide6 import QtCore, QtGui, QtWidgets as W


class AnimatedWordmark(W.QLabel):
    def __init__(self, parent=None):
        super().__init__('OutfitFlux', parent)
        self.setObjectName('Wordmark')
        self.setAccessibleName('OutfitFlux')
        self.setSizePolicy(W.QSizePolicy.Policy.Fixed, W.QSizePolicy.Policy.Preferred)
        self.phase = 0.0
        self.clock = QtCore.QElapsedTimer()
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(40)
        self.timer.timeout.connect(self.animate)

    def showEvent(self, event):
        super().showEvent(event)
        self.clock.start()
        self.timer.start()

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def animate(self):
        if self.isVisible() and not self.window().isMinimized():
            self.phase = (self.clock.elapsed() % 4800) / 4800
            self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing)
        font = self.font()
        metrics = QtGui.QFontMetricsF(font)
        baseline = (self.height() - metrics.height()) / 2 + metrics.ascent()
        letters = QtGui.QPainterPath()
        letters.addText(0, baseline, font, self.text())
        dark = getattr(self.window(), 'dark', True)
        base = QtGui.QColor('#e7efff' if dark else '#202647')
        accent = getattr(self.window(), 'theme_colors', {}).get('primary', '#0a84ff')
        width = max(1, self.width())
        center = (-0.6 + 2.2 * self.phase) * width
        gradient = QtGui.QLinearGradient(center - width * .55, 0, center + width * .55, 0)
        gradient.setColorAt(0, base)
        gradient.setColorAt(.25, QtGui.QColor(accent))
        gradient.setColorAt(.45, QtGui.QColor('#59e6ff' if dark else '#0077bc'))
        gradient.setColorAt(.53, QtGui.QColor('#ffffff' if dark else '#3e47b8'))
        gradient.setColorAt(.72, QtGui.QColor('#b894ff' if dark else '#7940c4'))
        gradient.setColorAt(1, base)
        if dark:
            glow = QtGui.QColor(accent)
            glow.setAlpha(35)
            painter.setPen(QtGui.QPen(glow, 2.2))
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            painter.drawPath(letters)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(QtGui.QBrush(gradient))
        painter.drawPath(letters)
