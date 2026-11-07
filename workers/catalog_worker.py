from PySide6.QtCore import QThread, Signal

from services.catalog_web_service import merge_web_catalog_into_local
from services.skin_id_map_service import rebuild_skin_id_map_file, load_skin_id_map


class CatalogWorker(QThread):
    progress = Signal(int, int, str)   # current, total, label
    result = Signal(object)
    error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        try:
            total = 3

            self.progress.emit(0, total, "Rebuilding skin ID map...")
            map_result = rebuild_skin_id_map_file()
            internal_name_map = load_skin_id_map()

            self.progress.emit(1, total, "Updating English catalog...")
            en_result = merge_web_catalog_into_local(
                language="en",
                internal_name_map=internal_name_map,
            )

            self.progress.emit(2, total, "Updating Spanish catalog...")
            es_result = merge_web_catalog_into_local(
                language="es",
                internal_name_map=internal_name_map,
            )

            self.progress.emit(3, total, "Catalog update complete.")

            self.result.emit({
                "map_result": map_result,
                "en_result": en_result,
                "es_result": es_result,
            })

        except Exception as e:
            self.error.emit(str(e))