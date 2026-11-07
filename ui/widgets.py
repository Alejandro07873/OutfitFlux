from PySide6 import QtWidgets, QtCore, QtGui

class HoverFrame(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)
        self.setProperty("hovered", False)

    def enterEvent(self, event):
        self.setProperty("hovered", True)
        self._refresh_style()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setProperty("hovered", False)
        self._refresh_style()
        super().leaveEvent(event)

    def _refresh_style(self):
        style = self.style()
        style.unpolish(self)
        style.polish(self)
        self.update()


# --- NUEVO: CLASE PARA LA NOTIFICACIÓN FLOTANTE (TOAST) ---
class ToastNotification(QtWidgets.QWidget):
    def __init__(self, title, message, parent=None, duration=3000):
        super().__init__(parent)
        # FramelessWindowHint y ToolTip lo hacen flotante y sin bordes de Windows
        self.setWindowFlags(QtCore.Qt.WindowType.ToolTip | QtCore.Qt.WindowType.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.duration = duration

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Diseño visual del cartelito
        self.container = QtWidgets.QFrame(self)
        self.container.setObjectName("ToastContainer")
        self.container.setStyleSheet("""
            QFrame#ToastContainer {
                background-color: #2b3341;
                border: 1px solid #31b86b; /* Borde verde de éxito */
                border-radius: 8px;
            }
            QLabel#ToastTitle {
                color: #31b86b; /* Texto verde */
                font-weight: bold;
                font-size: 14px;
            }
            QLabel#ToastMessage {
                color: #e5e7eb; /* Texto blanco suave */
                font-size: 12px;
            }
        """)
        
        container_layout = QtWidgets.QVBoxLayout(self.container)
        container_layout.setContentsMargins(16, 12, 16, 12)
        container_layout.setSpacing(4)

        self.title_label = QtWidgets.QLabel(title)
        self.title_label.setObjectName("ToastTitle")
        self.msg_label = QtWidgets.QLabel(message)
        self.msg_label.setObjectName("ToastMessage")
        self.msg_label.setWordWrap(True)

        container_layout.addWidget(self.title_label)
        container_layout.addWidget(self.msg_label)

        layout.addWidget(self.container)

        # Configuración de Animación (Desvanecimiento)
        self.opacity_anim = QtCore.QPropertyAnimation(self, b"windowOpacity")
        self.opacity_anim.setDuration(300) # 300 ms en aparecer/desaparecer

        # Temporizador para cerrarlo automáticamente
        self.timer = QtCore.QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide_toast)

    def show_toast(self):
        # Calcular posición: Esquina inferior derecha de la ventana padre
        if self.parent():
            parent_geo = self.parent().geometry()
            global_pos = self.parent().mapToGlobal(QtCore.QPoint(0, 0))
            x = global_pos.x() + parent_geo.width() - self.width() - 30
            y = global_pos.y() + parent_geo.height() - self.height() - 30
            self.move(x, y)

        # Inicia invisible
        self.setWindowOpacity(0.0)
        self.show()

        # Anima de invisible a visible
        self.opacity_anim.setStartValue(0.0)
        self.opacity_anim.setEndValue(1.0)
        self.opacity_anim.start()

        # Arranca el temporizador para cerrarse
        self.timer.start(self.duration)

    def hide_toast(self):
        # Anima de visible a invisible, y luego lo destruye
        self.opacity_anim.setStartValue(1.0)
        self.opacity_anim.setEndValue(0.0)
        self.opacity_anim.finished.connect(self.close)
        self.opacity_anim.start()

    # Función rápida para llamar al toast desde otros archivos
    @staticmethod
    def show_success(title, message, parent=None, duration=3000):
        toast = ToastNotification(title, message, parent, duration)
        toast.adjustSize()
        toast.show_toast()
        return toast