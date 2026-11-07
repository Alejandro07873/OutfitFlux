import traceback
from PySide6.QtCore import QThread, Signal

from services.mod_service import analyze_mod_pak


class AnalyzeWorker(QThread):
    result = Signal(object)
    error = Signal(str)

    def __init__(self, file_name, parent=None):
        super().__init__(parent)
        self.file_name = file_name

    def run(self):
        try:
            # Ejecuta el análisis pesado en este hilo secundario
            res = analyze_mod_pak(self.file_name)
            self.result.emit(res)
        except Exception as e:
            self.error.emit(str(e))