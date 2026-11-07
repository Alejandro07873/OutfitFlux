import os
from PySide6 import QtWidgets, QtCore, QtGui

from services.mod_service import cleanup_mod_workspace
from workers.catalog_worker import CatalogWorker
from workers.analyze_worker import AnalyzeWorker
from ui.theme import current_theme_name
from ui.widgets import ToastNotification
from ui.settings_dialog import SettingsDialog
from services.i18n_service import tr

class ChooseModFileWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.parent_window = parent
        self.catalog_worker = None
        self.catalog_progress_dialog = None
        self.analyze_worker = None  
        
        self.setAcceptDrops(True)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(34, 34, 34, 34)
        root.setSpacing(18)

        root.addStretch(1)

        row = QtWidgets.QHBoxLayout()
        row.addStretch(1)

        self.card = QtWidgets.QFrame()
        self.card.setObjectName("HeroCard")
        self.card.setMaximumWidth(780)

        card_layout = QtWidgets.QVBoxLayout(self.card)
        card_layout.setContentsMargins(28, 28, 28, 28)
        card_layout.setSpacing(14)

        top_row = QtWidgets.QHBoxLayout()
        top_row.addStretch()

        self.theme_button = QtWidgets.QPushButton("")
        self.theme_button.setObjectName("GhostButton")
        self.theme_button.clicked.connect(self.toggle_theme)
        top_row.addWidget(self.theme_button)
        
        self.settings_button = QtWidgets.QPushButton("⚙️")
        self.settings_button.setObjectName("GhostButton")
        self.settings_button.clicked.connect(self.open_settings)
        top_row.addWidget(self.settings_button)

        self.title_label = QtWidgets.QLabel(tr("app_title"))
        self.title_label.setObjectName("TitleLabel")
        self.title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.subtitle_label = QtWidgets.QLabel(tr("app_subtitle"))
        self.subtitle_label.setObjectName("SubtitleLabel")
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.status_card = QtWidgets.QFrame()
        self.status_card.setObjectName("SectionCard")
        status_layout = QtWidgets.QVBoxLayout(self.status_card)
        status_layout.setContentsMargins(14, 12, 14, 12)
        
        self.status_label = QtWidgets.QLabel(tr("ready_drop"))
        self.status_label.setObjectName("StatusLabel")
        self.status_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        status_layout.addWidget(self.status_label)

        self.button = QtWidgets.QPushButton(tr("btn_choose_mod"))
        self.button.setObjectName("AccentButton")
        self.button.clicked.connect(self.open_file_dialog)

        self.update_catalog_button = QtWidgets.QPushButton(tr("btn_update_catalog"))
        self.update_catalog_button.clicked.connect(self.update_catalog)

        self.hint_label = QtWidgets.QLabel(tr("tip_catalog"))
        self.hint_label.setObjectName("MutedLabel")
        self.hint_label.setWordWrap(True)
        self.hint_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        card_layout.addLayout(top_row)
        card_layout.addWidget(self.title_label)
        card_layout.addWidget(self.subtitle_label)
        card_layout.addSpacing(6)
        card_layout.addWidget(self.status_card)
        card_layout.addSpacing(6)
        card_layout.addWidget(self.button)
        card_layout.addWidget(self.update_catalog_button)
        card_layout.addWidget(self.hint_label)

        row.addWidget(self.card)
        row.addStretch(1)

        root.addLayout(row)
        root.addStretch(1)

        self.refresh_theme_ui(current_theme_name(QtWidgets.QApplication.instance()))

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent):
        if self.analyze_worker is not None:
            event.ignore()
            return

        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and urls[0].toLocalFile().lower().endswith('.pak'):
                event.accept()
                self.card.setStyleSheet("QFrame#HeroCard { border: 2px dashed #2d7dff; background-color: #2b3341; }")
                self.status_label.setText(tr("status_drop"))
                return
        event.ignore()

    def dragLeaveEvent(self, event: QtGui.QDragLeaveEvent):
        if self.analyze_worker is None:
            self.card.setStyleSheet("")
            self.status_label.setText(tr("ready_drop"))

    def dropEvent(self, event: QtGui.QDropEvent):
        self.card.setStyleSheet("")
        if self.analyze_worker is not None:
            return

        urls = event.mimeData().urls()
        if urls:
            file_name = urls[0].toLocalFile()
            if file_name.lower().endswith('.pak'):
                self.process_mod_file(file_name)

    def refresh_theme_ui(self, theme_name=None):
        theme_name = (theme_name or "dark").lower()
        if theme_name == "light":
            self.theme_button.setText(tr("btn_switch_dark"))
        else:
            self.theme_button.setText(tr("btn_switch_light"))

    def toggle_theme(self):
        if self.parent_window and hasattr(self.parent_window, "toggle_theme"):
            self.parent_window.toggle_theme()
    
    def open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec():
            if self.parent_window and hasattr(self.parent_window, "restart_app"):
                self.parent_window.restart_app()

    def show_error(self, title, text):
        QtWidgets.QMessageBox.critical(self, title, text)

    def show_warning(self, title, text):
        QtWidgets.QMessageBox.warning(self, title, text)

    def show_info(self, title, text):
        QtWidgets.QMessageBox.information(self, title, text)

    def open_file_dialog(self):
        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open File",
            "",
            "PAK files (*.pak*)"
        )

        if not file_name:
            if self.analyze_worker is None:
                self.status_label.setText(tr("status_selection_cancelled"))
            return

        self.process_mod_file(file_name)
        
    def process_mod_file(self, file_name):
        if self.analyze_worker is not None:
            return

        self.status_label.setText(tr("status_analyzing"))
        self.button.setEnabled(False)
        self.update_catalog_button.setEnabled(False)
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.CursorShape.WaitCursor)

        self.analyze_worker = AnalyzeWorker(file_name, parent=self)
        self.analyze_worker.result.connect(lambda res: self.on_analyze_result(res, file_name))
        self.analyze_worker.error.connect(self.on_analyze_error)
        self.analyze_worker.finished.connect(self.analyze_worker.deleteLater)
        self.analyze_worker.start()

    def _reset_ui_after_analyze(self):
        self.analyze_worker = None
        self.button.setEnabled(True)
        self.update_catalog_button.setEnabled(True)
        QtWidgets.QApplication.restoreOverrideCursor()

    def on_analyze_error(self, error_text):
        self._reset_ui_after_analyze()
        cleanup_mod_workspace()
        self.status_label.setText(tr("err_analysis_failed"))
        self.show_error("Mod analysis error", f"{tr('err_analysis_failed')}\n\n{error_text}")

    def on_analyze_result(self, result, file_name):
        self._reset_ui_after_analyze()

        if not result["valid"]:
            cleanup_mod_workspace()
            self.status_label.setText(tr("status_invalid"))
            self.show_warning(tr("err_invalid_mod_title"), result["error_message"])
            return

        selected_character = result["detected_character"]
        current_skin_name = result["current_skin_name_internal"]

        if not selected_character:
            cleanup_mod_workspace()
            self.status_label.setText(tr("err_char_detection_failed"))
            self.show_warning(
                tr("err_char_not_detected"),
                tr("err_msg_char_not_detected")
            )
            return

        self.status_label.setText(
            tr("status_detected").format(selected_character, current_skin_name)
        )

        self.parent_window.viewSkinsList(
            selected_character,
            file_name,
            current_skin_name=current_skin_name
        )

    def close_catalog_progress_dialog(self):
        if self.catalog_progress_dialog is not None:
            try:
                self.catalog_progress_dialog.close()
            except Exception:
                pass
            self.catalog_progress_dialog = None

    def on_catalog_progress(self, current, total, label):
        dialog = self.catalog_progress_dialog
        if dialog is None:
            return

        dialog.setMaximum(max(total, 1))
        dialog.setValue(current)
        if self.catalog_progress_dialog is not None:
            self.catalog_progress_dialog.setLabelText(label)
        QtWidgets.QApplication.processEvents()

    def on_catalog_error(self, error_text):
        self.close_catalog_progress_dialog()
        self.catalog_worker = None
        self.update_catalog_button.setEnabled(True)
        self.status_label.setText(tr("err_catalog_failed"))

        self.show_error(
            tr("err_catalog_error"),
            tr("err_msg_catalog").format(error_text)
        )

    def on_catalog_result(self, payload):
        self.close_catalog_progress_dialog()
        self.catalog_worker = None
        self.update_catalog_button.setEnabled(True)

        map_result = payload.get("map_result", {})
        en_result = payload.get("en_result", {})
        es_result = payload.get("es_result", {})

        self.status_label.setText(tr("msg_catalog_success"))

        msg = tr("msg_mapped").format(map_result.get('characters_found', 0), map_result.get('mapped_entries', 0))
        ToastNotification.show_success(tr("title_catalog_updated"), msg, parent=self.window())

    def update_catalog(self):
        if self.catalog_worker is not None:
            self.show_warning(
                tr("warn_catalog_running"),
                tr("warn_msg_catalog_running")
            )
            return

        self.update_catalog_button.setEnabled(False)
        self.status_label.setText(tr("status_updating_catalog"))

        self.catalog_progress_dialog = QtWidgets.QProgressDialog(
            tr("status_prep_catalog"),
            None,
            0,
            3,
            self
        )
        self.catalog_progress_dialog.setWindowTitle(tr("win_updating_catalog"))
        self.catalog_progress_dialog.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        self.catalog_progress_dialog.setMinimumDuration(0)
        self.catalog_progress_dialog.setValue(0)
        self.catalog_progress_dialog.show()

        self.catalog_worker = CatalogWorker(parent=self)
        self.catalog_worker.progress.connect(self.on_catalog_progress)
        self.catalog_worker.result.connect(self.on_catalog_result)
        self.catalog_worker.error.connect(self.on_catalog_error)
        self.catalog_worker.finished.connect(self.catalog_worker.deleteLater)
        self.catalog_worker.start()