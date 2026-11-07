from PySide6.QtCore import QThread, Signal
from services.process_service import ExportCancelled


class TaskWorker(QThread):
    result = Signal(object)
    error = Signal(str)
    progress = Signal(int, int, str)
    cancelled = Signal()

    def __init__(self, function, parent=None):
        super().__init__(parent)
        self.function = function

    def cancel(self):
        self.requestInterruption()

    def run(self):
        try:
            result = self.function(self.isInterruptionRequested, self.progress.emit)
            self.result.emit(result)
        except ExportCancelled:
            self.cancelled.emit()
        except Exception as exc:
            self.error.emit(str(exc))
