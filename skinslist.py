import json
import os
from pathlib import Path

from PySide6 import QtWidgets, QtGui, QtCore

from workers.export_worker import ExportWorker
from util import CHARACTER_DIR
from services.mod_service import cleanup_mod_workspace
from services.catalog_service import get_skin_display_data
from services.filename_service import build_output_filename
from ui.widgets import HoverFrame, ToastNotification
from ui.theme import current_theme_name
from services.config_service import load_config
from services.i18n_service import tr


class SkinsList(QtWidgets.QScrollArea):
    def __init__(self, character, mod_file, parent=None, current_skin_name=None):
        super().__init__(parent)

        self.parent_window = parent
        self.character = character
        self.mod_file = mod_file
        self.current_skin_name = current_skin_name or self.detect_current_mod_skin()

        self.current_lang = load_config().get("language", "en")

        self.all_skin_records = []
        self.rendered_cards = []
        self.export_worker = None
        self.export_progress_dialog = None

        self.setWidgetResizable(True)
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)

        self.root_widget = QtWidgets.QWidget()
        self.root_layout = QtWidgets.QVBoxLayout(self.root_widget)
        self.root_layout.setContentsMargins(20, 20, 20, 20)
        self.root_layout.setSpacing(14)

        self.header_card = QtWidgets.QFrame()
        self.header_card.setObjectName("HeroCard")
        self.header_layout = QtWidgets.QVBoxLayout(self.header_card)
        self.header_layout.setContentsMargins(20, 20, 20, 20)
        self.header_layout.setSpacing(10)

        self.header_top_row = QtWidgets.QHBoxLayout()
        self.header_top_row.setSpacing(8)

        self.header_text_col = QtWidgets.QVBoxLayout()
        self.header_text_col.setSpacing(4)

        self.title_label = QtWidgets.QLabel(f"{self.character} {tr('label_costumes')}")
        self.title_label.setObjectName("TitleLabel")

        self.subtitle_label = QtWidgets.QLabel(tr("skins_list_subtitle"))
        self.subtitle_label.setObjectName("SubtitleLabel")
        self.subtitle_label.setWordWrap(True)

        self.header_text_col.addWidget(self.title_label)
        self.header_text_col.addWidget(self.subtitle_label)

        self.theme_button = QtWidgets.QPushButton("")
        self.theme_button.setObjectName("GhostButton")
        self.theme_button.clicked.connect(self.toggle_theme)

        self.header_top_row.addLayout(self.header_text_col, 1)
        self.header_top_row.addWidget(self.theme_button, 0, QtCore.Qt.AlignmentFlag.AlignTop)

        self.header_layout.addLayout(self.header_top_row)

        self.active_mod_card = QtWidgets.QFrame()
        self.active_mod_card.setObjectName("SectionCard")
        self.active_mod_layout = QtWidgets.QHBoxLayout(self.active_mod_card)
        self.active_mod_layout.setContentsMargins(18, 14, 18, 14)
        self.active_mod_layout.setSpacing(12)

        self.active_mod_icon = QtWidgets.QLabel("📦")
        self.active_mod_icon.setStyleSheet("font-size: 18pt;")
        self.active_mod_icon.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.active_mod_label = QtWidgets.QLabel(tr("loading_info"))
        self.active_mod_label.setWordWrap(True)
        self.active_mod_label.setStyleSheet("font-size: 11pt;")

        self.active_mod_layout.addWidget(self.active_mod_icon)
        self.active_mod_layout.addWidget(self.active_mod_label, 1)

        self.toolbar_card = QtWidgets.QFrame()
        self.toolbar_card.setObjectName("SectionCard")
        self.toolbar_layout = QtWidgets.QVBoxLayout(self.toolbar_card)
        self.toolbar_layout.setContentsMargins(16, 16, 16, 16)
        self.toolbar_layout.setSpacing(10)

        self.controls_row = QtWidgets.QHBoxLayout()
        self.controls_row.setSpacing(8)

        self.back_button = QtWidgets.QPushButton(tr("btn_back"))
        self.back_button.clicked.connect(self.go_back)

        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText(tr("search_placeholder"))
        self.search_input.textChanged.connect(self.apply_filters)

        self.order_combo = QtWidgets.QComboBox()
        self.order_combo.addItem(tr("label_id"), "skin_id")
        self.order_combo.addItem(tr("label_real_name"), "real_name")
        self.order_combo.addItem(tr("label_internal_name"), "internal_name")
        self.order_combo.currentIndexChanged.connect(self.apply_filters)

        self.filter_combo = QtWidgets.QComboBox()
        self.filter_combo.addItem(tr("filter_all"), "all")
        self.filter_combo.addItem(tr("filter_unknown"), "unknown")
        self.filter_combo.addItem(tr("filter_current"), "current")
        self.filter_combo.currentIndexChanged.connect(self.apply_filters)

        self.select_visible_button = QtWidgets.QPushButton(tr("btn_select_visible"))
        self.select_visible_button.clicked.connect(self.select_visible_records)

        self.clear_selected_button = QtWidgets.QPushButton(tr("btn_clear_selected"))
        self.clear_selected_button.clicked.connect(self.clear_selected_records)

        self.export_selected_button = QtWidgets.QPushButton(tr("btn_export_selected"))
        self.export_selected_button.setObjectName("AccentButton")
        self.export_selected_button.clicked.connect(self.export_selected_batch)

        self.controls_row.addWidget(self.back_button, 0)
        self.controls_row.addWidget(self.search_input, 1)
        self.controls_row.addWidget(self.order_combo, 0)
        self.controls_row.addWidget(self.filter_combo, 0)
        self.controls_row.addWidget(self.select_visible_button, 0)
        self.controls_row.addWidget(self.clear_selected_button, 0)
        self.controls_row.addWidget(self.export_selected_button, 0)

        self.summary_label = QtWidgets.QLabel("")
        self.summary_label.setObjectName("SummaryLabel")

        self.toolbar_layout.addLayout(self.controls_row)
        self.toolbar_layout.addWidget(self.summary_label)

        self.cards_widget = QtWidgets.QWidget()
        self.cards_layout = QtWidgets.QGridLayout(self.cards_widget)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(12)

        self.root_layout.addWidget(self.header_card)
        self.root_layout.addWidget(self.active_mod_card)
        self.root_layout.addWidget(self.toolbar_card)
        self.root_layout.addWidget(self.cards_widget, 1)

        self.setWidget(self.root_widget)

        self.load_skin_records()
        self.update_active_mod_card()
        self.apply_filters()
        self.refresh_theme_ui(current_theme_name(QtWidgets.QApplication.instance()))

    def update_active_mod_card(self):
        mod_name = os.path.basename(self.mod_file)
        current_record = self.get_current_skin_record()

        if current_record:
            skin_display = current_record["display_name"]
            internal = current_record["internal_name"]
            text = f"<b>{tr('lbl_loaded_mod')}:</b> {mod_name} &nbsp;&nbsp;|&nbsp;&nbsp; <b>{tr('lbl_replaces')}:</b> {skin_display} ({internal})"
        else:
            skin_name = self.current_skin_name or tr("lbl_unknown")
            text = f"<b>{tr('lbl_loaded_mod')}:</b> {mod_name} &nbsp;&nbsp;|&nbsp;&nbsp; <b>{tr('lbl_replaces')}:</b> {skin_name}"

        self.active_mod_label.setText(text)

    def refresh_theme_ui(self, theme_name=None):
        theme_name = (theme_name or "dark").lower()
        if theme_name == "light":
            self.theme_button.setText(tr("btn_switch_dark"))
        else:
            self.theme_button.setText(tr("btn_switch_light"))

    def toggle_theme(self):
        if self.parent_window and hasattr(self.parent_window, "toggle_theme"):
            self.parent_window.toggle_theme()

    def load_skin_records(self):
        self.all_skin_records.clear()

        skins_data = self.load_skins_data(self.character)

        for skin in skins_data:
            skin_id = str(skin[0]["Value"])
            skin_path = skin[1]["Value"]["AssetPath"]["AssetName"].partition("Character/")[2].partition(".")[0]
            internal_name = skin[1]["Value"]["AssetPath"]["AssetName"].partition("Mesh/")[2].partition(".")[0]

            display_data = get_skin_display_data(
                character=self.character,
                internal_name=internal_name,
                skin_id=skin_id,
            )

            en_name = display_data.get("display_name", internal_name)
            es_name = display_data.get("display_name_es", internal_name)

            record = {
                "character": self.character,
                "skin_id": skin_id,
                "skin_path": skin_path,
                "internal_name": internal_name,
                "display_name": es_name if self.current_lang == "es" else en_name,
                "display_name_es": es_name,
                "aliases": display_data.get("aliases", []),
                "description": display_data.get("description", ""),
                "source_url": display_data.get("source_url", ""),
                "is_known": bool(display_data.get("is_known", False)),
                "is_unknown": not bool(display_data.get("is_known", False)),
                "is_current": (
                    internal_name.casefold() == self.current_skin_name.casefold()
                    if self.current_skin_name else False
                ),
                "is_selected": False,
                "thumbnail_path": self.find_skin_thumbnail(self.character, skin_id),
            }

            self.all_skin_records.append(record)

    def clear_cards(self):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self.rendered_cards.clear()

    def get_filtered_records(self):
        search_text = self.search_input.text().strip().casefold()
        filter_mode = self.filter_combo.currentData()
        order_mode = self.order_combo.currentData()

        filtered = []

        for record in self.all_skin_records:
            if filter_mode == "unknown" and record["is_known"]:
                continue
            if filter_mode == "current" and not record["is_current"]:
                continue

            haystack_parts = [
                record["display_name"],
                record["display_name_es"],
                record["internal_name"],
                record["skin_id"],
                record["description"],
                " ".join(record["aliases"]),
            ]
            haystack = " ".join(str(x or "") for x in haystack_parts).casefold()

            if search_text and search_text not in haystack:
                continue

            filtered.append(record)

        if order_mode == "real_name":
            filtered.sort(key=lambda r: (r["display_name"].casefold(), r["internal_name"].casefold()))
        elif order_mode == "internal_name":
            filtered.sort(key=lambda r: r["internal_name"].casefold())
        elif order_mode == "skin_id":
            filtered.sort(key=lambda r: r["skin_id"])

        return filtered

    def apply_filters(self):
        filtered = self.get_filtered_records()
        self.render_cards(filtered)

        selected_count = sum(1 for r in self.all_skin_records if r["is_selected"])
        unknown_count = sum(1 for r in self.all_skin_records if r.get("is_unknown", False))

        self.summary_label.setText(
            tr("lbl_summary").format(len(filtered), len(self.all_skin_records), selected_count, unknown_count)
        )

    def render_cards(self, records):
        self.clear_cards()

        max_columns = 4
        row = 0
        column = 0

        for record in records:
            card = self.create_skin_card(record)
            self.cards_layout.addWidget(card, row, column)
            self.rendered_cards.append(card)

            column += 1
            if column >= max_columns:
                column = 0
                row += 1

        self.cards_layout.setRowStretch(row + 1, 1)

    def load_skins_data(self, character):
        json_path = os.path.join(CHARACTER_DIR, character, f"PA_{character}.json")
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Character JSON not found: {json_path}")

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        exports = data["Exports"][0]["Data"]
        for value in exports:
            if value["Name"] == "_costumeMeshs":
                return value["Value"]

        raise RuntimeError(f"_costumeMeshs was not found in {json_path}")

    def detect_current_mod_skin(self):
        from util import MOD_DIR
        root = Path(MOD_DIR) / "HerovsGame/Content/Character"
        if not root.exists():
            return None

        mesh_dir = next(root.rglob("Mesh"), None)
        if mesh_dir is None or not mesh_dir.is_dir():
            return None

        current_skin = None

        for file in mesh_dir.iterdir():
            if not file.is_file():
                continue
            if not file.name.casefold().startswith("sk_ch"):
                continue
            if not file.name.casefold().endswith(".uasset"):
                continue

            current_skin = file.stem

        return current_skin

    def find_skin_thumbnail(self, character, skin_id):
        gui_dir = os.path.join(CHARACTER_DIR, character, "GUI", "Costume", "L")
        if not os.path.isdir(gui_dir):
            return None

        for image in os.listdir(gui_dir):
            if skin_id in image and image.lower().endswith(".png"):
                return os.path.join(gui_dir, image)

        return None

    def on_record_selection_changed(self, record, checked):
        record["is_selected"] = bool(checked)
        self.apply_filters()

    def build_status_badge(self, text, bg, fg="white"):
        label = QtWidgets.QLabel(text)
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(
            f"""
            QLabel {{
                background-color: {bg};
                color: {fg};
                border-radius: 9px;
                padding: 4px 10px;
                font-weight: 700;
            }}
            """
        )
        return label

    def create_skin_card(self, record):
        card = HoverFrame()
        card.setObjectName("SkinCard")
        card.setMinimumWidth(260)
        card.setMaximumWidth(320)
        card.setProperty("current", record["is_current"])
        card.setProperty("unknown", record.get("is_unknown", False))
        card.setProperty("selected", record["is_selected"])

        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        image_frame = QtWidgets.QFrame()
        image_frame.setObjectName("ThumbnailFrame")
        image_layout = QtWidgets.QVBoxLayout(image_frame)
        image_layout.setContentsMargins(8, 8, 8, 8)

        thumbnail_path = record["thumbnail_path"]

        if thumbnail_path and os.path.exists(thumbnail_path):
            pixmap = QtGui.QPixmap(thumbnail_path).scaled(
                260,
                260,
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation,
            )
            image_label = QtWidgets.QLabel()
            image_label.setPixmap(pixmap)
            image_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        else:
            image_label = QtWidgets.QLabel(tr("lbl_no_preview"))
            image_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            image_label.setMinimumHeight(260)
            image_label.setObjectName("MutedLabel")

        image_layout.addWidget(image_label)

        title_label = QtWidgets.QLabel(record["display_name"])
        title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        title_label.setWordWrap(True)
        title_label.setStyleSheet("font-size: 11pt; font-weight: 700;")

        internal_label = QtWidgets.QLabel(f'{record["internal_name"]}\nID: {record["skin_id"]}')
        internal_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        internal_label.setWordWrap(True)
        internal_label.setObjectName("MutedLabel")

        badge_row = QtWidgets.QHBoxLayout()
        badge_row.setSpacing(6)

        if record["is_current"]:
            badge_row.addWidget(self.build_status_badge(tr("badge_current"), "#2d7dff"))
        elif record.get("is_unknown", False):
            badge_row.addWidget(self.build_status_badge(tr("badge_unknown"), "#ff9f2d"))

        if record["is_selected"]:
            badge_row.addWidget(self.build_status_badge(tr("badge_selected"), "#31b86b"))

        badge_row.addStretch()

        description_label = QtWidgets.QLabel(record["description"] or "")
        description_label.setWordWrap(True)
        description_label.setObjectName("MutedLabel")
        description_label.setVisible(bool(record["description"]))

        checkbox = QtWidgets.QCheckBox(tr("lbl_select_batch"))
        checkbox.setChecked(record["is_selected"])
        checkbox.toggled.connect(lambda checked, r=record: self.on_record_selection_changed(r, checked))
        if record["is_current"]:
            checkbox.setEnabled(False)

        if record["is_current"]:
            button = QtWidgets.QPushButton(tr("btn_base_mod"))
            button.setEnabled(False)
        else:
            button = QtWidgets.QPushButton(tr("btn_export_skin"))
            button.setObjectName("AccentButton")
            button.clicked.connect(lambda _, r=record: self.export_selected_skin(r))

        layout.addWidget(image_frame)
        layout.addWidget(title_label)
        layout.addWidget(internal_label)
        layout.addLayout(badge_row)
        layout.addWidget(description_label)
        layout.addWidget(checkbox)
        layout.addWidget(button)

        return card

    def get_current_skin_record(self):
        for record in self.all_skin_records:
            if record["is_current"]:
                return record
        return None

    def close_export_progress_dialog(self):
        if self.export_progress_dialog is not None:
            try:
                self.export_progress_dialog.close()
            except Exception:
                pass
            self.export_progress_dialog = None

    def on_export_progress(self, current, total, label):
        dialog = self.export_progress_dialog
        if dialog is None:
            return

        dialog.setLabelText(label)

        if dialog.maximum() == 0:
            QtWidgets.QApplication.processEvents()
            return

        dialog.setMaximum(total)
        dialog.setValue(current)
        QtWidgets.QApplication.processEvents()

    def on_export_error(self, error_text):
        self.close_export_progress_dialog()
        self.export_worker = None

        QtWidgets.QMessageBox.critical(
            self,
            tr("err_export"),
            f"{tr('err_msg_export')}\n\n{error_text}"
        )

    def on_export_result(self, payload):
        mode = payload.get("mode")

        if mode == "single":
            cancelled = bool(payload.get("cancelled"))
            record = payload.get("record")
            final_export_path = payload.get("output_path")

            self.close_export_progress_dialog()
            self.export_worker = None

            if cancelled:
                QtWidgets.QMessageBox.information(
                    self,
                    tr("msg_export_cancelled"),
                    tr("msg_export_cancelled_desc")
                )
                return

            if record and final_export_path:
                selected_skin_name = Path(record["skin_path"]).name
                # The source remains the originally imported mod after export.

                ToastNotification.show_success(
                    tr("msg_export_success"),
                    tr("msg_export_success_desc"),
                    parent=self.window()
                )
            return

        if mode == "batch":
            result = payload["result"]

            completed_count = len(result["completed"])
            failed_count = len(result["failed"])
            cancelled = result["cancelled"]

            if completed_count > 0:
                for record in self.all_skin_records:
                    record["is_selected"] = False
                self.apply_filters()

            self.close_export_progress_dialog()
            self.export_worker = None

            if failed_count > 0 or cancelled:
                details = [
                    f"{tr('msg_completed')}: {completed_count}",
                    f"{tr('msg_failed')}: {failed_count}",
                    f"{tr('msg_cancelled')}: {'Yes' if cancelled else 'No'}",
                ]
                if failed_count:
                    preview = "\n".join(
                        f"- {item['record']['display_name']}: {item['error']}"
                        for item in result["failed"][:5]
                    )
                    details.append("")
                    details.append(tr("msg_errors"))
                    details.append(preview)

                QtWidgets.QMessageBox.information(
                    self,
                    tr("msg_batch_finished"),
                    "\n".join(details)
                )
            else:
                ToastNotification.show_success(
                    tr("msg_batch_finished"),
                    tr("msg_batch_success").format(completed_count),
                    parent=self.window()
                )

    def start_single_export_worker(self, target_record, output_path):
        if self.export_worker is not None:
            QtWidgets.QMessageBox.warning(
                self,
                tr("err_export_running"),
                tr("err_msg_export_running")
            )
            return

        self.export_progress_dialog = QtWidgets.QProgressDialog(
            tr("lbl_prep_export"),
            tr("btn_cancel"),
            0,
            0,
            self
        )
        self.export_progress_dialog.setWindowTitle(tr("win_exporting"))
        self.export_progress_dialog.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        self.export_progress_dialog.setMinimumDuration(0)
        self.export_progress_dialog.show()

        self.export_worker = ExportWorker(
            mode="single",
            mod_file=self.mod_file,
            target_record=target_record,
            output_path=output_path,
            parent=self,
        )
        self.export_worker.progress.connect(self.on_export_progress)
        self.export_worker.result.connect(self.on_export_result)
        self.export_worker.error.connect(self.on_export_error)
        self.export_worker.finished.connect(self.export_worker.deleteLater)
        self.export_progress_dialog.canceled.connect(self.export_worker.cancel)
        self.export_worker.start()

    def start_batch_export_worker(self, selected_records, output_dir):
        if self.export_worker is not None:
            QtWidgets.QMessageBox.warning(
                self,
                tr("err_export_running"),
                tr("err_msg_export_running")
            )
            return

        current_record = self.get_current_skin_record()

        self.export_progress_dialog = QtWidgets.QProgressDialog(
            tr("lbl_prep_batch"),
            tr("btn_cancel"),
            0,
            len(selected_records),
            self
        )
        self.export_progress_dialog.setWindowTitle(tr("win_batch_export"))
        self.export_progress_dialog.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        self.export_progress_dialog.setMinimumDuration(0)
        self.export_progress_dialog.setValue(0)
        self.export_progress_dialog.show()

        self.export_worker = ExportWorker(
            mode="batch",
            mod_file=self.mod_file,
            selected_records=selected_records,
            output_dir=output_dir,
            current_record=current_record,
            parent=self,
        )
        self.export_worker.progress.connect(self.on_export_progress)
        self.export_worker.result.connect(self.on_export_result)
        self.export_worker.error.connect(self.on_export_error)
        self.export_worker.finished.connect(self.export_worker.deleteLater)
        self.export_progress_dialog.canceled.connect(self.export_worker.cancel)
        self.export_worker.start()

    def refresh_current_skin(self, new_skin_name):
        self.current_skin_name = new_skin_name

        for record in self.all_skin_records:
            record["is_current"] = (
                record["internal_name"].casefold() == new_skin_name.casefold()
            )
            if record["is_current"]:
                record["is_selected"] = False

        self.update_active_mod_card()
        self.apply_filters()

    def select_visible_records(self):
        for record in self.get_filtered_records():
            if not record["is_current"]:
                record["is_selected"] = True
        self.apply_filters()

    def clear_selected_records(self):
        for record in self.all_skin_records:
            record["is_selected"] = False
        self.apply_filters()

    def go_back(self):
        if self.export_worker is not None and self.export_worker.isRunning():
            answer = QtWidgets.QMessageBox.question(
                self,
                tr("err_export_running"),
                tr("err_msg_cancel_export"),
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.StandardButton.Yes,
            )
            if answer == QtWidgets.QMessageBox.StandardButton.Yes:
                self.export_worker.cancel()
                return
            return

        cleanup_mod_workspace()

        if self.parent_window and hasattr(self.parent_window, "show_choose_mod"):
            self.parent_window.show_choose_mod()
            return

        try:
            main_window = self.window()
            if hasattr(main_window, "show_choose_mod"):
                main_window.show_choose_mod()
        except Exception:
            pass

    def export_selected_skin(self, target_record):
        current_record = self.get_current_skin_record()

        suggested_path = build_output_filename(
            original_mod_path=self.mod_file,
            target_skin_name=target_record["display_name"],
            current_skin_display_name=current_record["display_name"] if current_record else "",
            current_skin_internal_name=current_record["internal_name"] if current_record else self.current_skin_name,
        )

        dialog = QtWidgets.QFileDialog(self, tr("win_save_pak"))
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptSave)
        dialog.setNameFilter("PAK files (*.pak)")

        suggested_dir = os.path.dirname(suggested_path) or os.getcwd()
        suggested_name = os.path.basename(suggested_path)

        dialog.setDirectory(suggested_dir)
        dialog.selectFile(suggested_name)

        if not dialog.exec():
            return

        selected_files = dialog.selectedFiles()
        if not selected_files:
            return

        save_path = selected_files[0]
        if not save_path:
            return

        self.start_single_export_worker(target_record, save_path)

    def export_selected_batch(self):
        selected_records = [
            record for record in self.all_skin_records
            if record["is_selected"] and not record["is_current"]
        ]

        if not selected_records:
            QtWidgets.QMessageBox.information(
                self,
                tr("err_no_skins"),
                tr("err_msg_no_skins")
            )
            return

        output_dir = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            tr("win_choose_output_folder"),
            os.path.dirname(self.mod_file) or os.getcwd()
        )

        if not output_dir:
            return

        self.start_batch_export_worker(selected_records, output_dir)
