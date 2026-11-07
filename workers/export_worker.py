from PySide6.QtCore import QThread, Signal

from services.export_service import (
    export_mod_to_skin,
    export_mod_to_many_skins,
    ExportCancelled,
)


class ExportWorker(QThread):
    progress = Signal(int, int, str)   # current, total, label
    result = Signal(object)            # dict
    error = Signal(str)

    def __init__(
        self,
        mode,
        mod_file,
        target_record=None,
        output_path=None,
        selected_records=None,
        output_dir=None,
        current_record=None,
        parent=None,
    ):
        super().__init__(parent)
        self.mode = mode
        self.mod_file = mod_file
        self.target_record = target_record
        self.output_path = output_path
        self.selected_records = selected_records or []
        self.output_dir = output_dir
        self.current_record = current_record
        self._cancel_requested = False

    def cancel(self):
        self._cancel_requested = True

    def is_cancelled(self):
        return self._cancel_requested

    def run(self):
        try:
            if self.mode == "single":
                if not self.target_record or not self.output_path:
                    raise RuntimeError("Single export worker is missing required data.")

                skin_name = self.target_record.get("display_name", "Skin")
                self.progress.emit(0, 0, f"Exporting {skin_name}...")

                final_export_path = export_mod_to_skin(
                    mod_file=self.mod_file,
                    selected_skin=self.target_record["skin_path"],
                    output_path=self.output_path,
                    is_cancelled_callback=self.is_cancelled,
                )

                self.result.emit({
                    "mode": "single",
                    "record": self.target_record,
                    "output_path": final_export_path,
                    "cancelled": False,
                })
                return

            if self.mode == "batch":
                if not self.selected_records or not self.output_dir:
                    raise RuntimeError("Batch export worker is missing required data.")

                def progress_callback(index, total, record):
                    self.progress.emit(
                        max(index - 1, 0),
                        total,
                        f"Exporting {index}/{total}: {record['display_name']}"
                    )

                result = export_mod_to_many_skins(
                    mod_file=self.mod_file,
                    selected_records=self.selected_records,
                    output_dir=self.output_dir,
                    current_record=self.current_record,
                    progress_callback=progress_callback,
                    is_cancelled_callback=self.is_cancelled,
                )

                self.result.emit({
                    "mode": "batch",
                    "result": result,
                })
                return

            raise RuntimeError(f"Unknown export worker mode: {self.mode}")

        except ExportCancelled:
            if self.mode == "single":
                self.result.emit({
                    "mode": "single",
                    "record": self.target_record,
                    "output_path": None,
                    "cancelled": True,
                })
            else:
                self.result.emit({
                    "mode": "batch",
                    "result": {
                        "completed": [],
                        "failed": [],
                        "cancelled": True,
                        "total": len(self.selected_records),
                    },
                })
        except Exception as e:
            self.error.emit(str(e))