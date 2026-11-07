import logging
import traceback
from PySide6.QtCore import QThread, Signal

from services.game_service import prepare_game_assets

# Configurar archivo de log para cazar errores si vuelve a fallar
logging.basicConfig(
    filename='mhur_swapper.log', 
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class StartupWorker(QThread):
    progress = Signal(int, int, str)   # current, total, label
    finished_ok = Signal(object)
    error = Signal(str)

    def __init__(self, aes_key, game_path, parent=None):
        super().__init__(parent)
        self.aes_key = aes_key
        self.game_path = game_path

    def run(self):
        try:
            self.progress.emit(0, 5, "Iniciando preparación...")

            # Callback para actualizar la ventana gráfica desde el game_service
            def update_progress(current, total, label):
                self.progress.emit(current, total, label)

            result = prepare_game_assets(
                self.aes_key,
                self.game_path,
                use_cache=True,
                progress_callback=update_progress
            )

            if result.get("used_cache"):
                self.progress.emit(5, 5, "Caché validada correctamente.")
            else:
                self.progress.emit(5, 5, "Assets preparados correctamente.")

            self.finished_ok.emit(result)

        except Exception as e:
            # Grabar todo el rastreo del error en el log
            logging.error("Ocurrió un error crítico en el proceso de StartupWorker:")
            logging.error(traceback.format_exc())
            
            # Enviar la alerta a la ventana gráfica
            self.error.emit(f"{str(e)}\nRevisa el archivo mhur_swapper.log para más detalles.")