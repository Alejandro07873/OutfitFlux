import os
from PySide6 import QtWidgets, QtCore
from services.config_service import load_config, save_config
from ui.theme import get_saved_theme, save_theme
from services.i18n_service import tr  # <-- IMPORT DE TRADUCCIÓN

class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("settings_title"))
        self.setMinimumWidth(550)
        self.setModal(True)

        self.config = load_config()
        self.current_theme = get_saved_theme()

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QtWidgets.QLabel(tr("settings_title"))
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(title)

        # 1. Ruta del Juego
        path_layout = QtWidgets.QVBoxLayout()
        path_layout.setSpacing(4)
        path_layout.addWidget(QtWidgets.QLabel(tr("label_game_path")))
        row_path = QtWidgets.QHBoxLayout()
        self.path_input = QtWidgets.QLineEdit(self.config.get("gamePakPath", ""))
        self.path_btn = QtWidgets.QPushButton(tr("btn_browse"))
        self.path_btn.clicked.connect(self.browse_path)
        row_path.addWidget(self.path_input)
        row_path.addWidget(self.path_btn)
        path_layout.addLayout(row_path)
        layout.addLayout(path_layout)

        # 2. Clave AES
        aes_layout = QtWidgets.QVBoxLayout()
        aes_layout.setSpacing(4)
        aes_layout.addWidget(QtWidgets.QLabel(tr("label_aes_key")))
        self.aes_input = QtWidgets.QLineEdit(self.config.get("aesKey", ""))
        aes_layout.addWidget(self.aes_input)
        layout.addLayout(aes_layout)

        # 3. Idioma (Language)
        lang_layout = QtWidgets.QVBoxLayout()
        lang_layout.setSpacing(4)
        lang_layout.addWidget(QtWidgets.QLabel(tr("label_language")))
        self.lang_combo = QtWidgets.QComboBox()
        # Mantenemos los nombres de los idiomas en su idioma original (buena práctica)
        self.lang_combo.addItem("English", "en")
        self.lang_combo.addItem("Español", "es")
        # Leer el idioma guardado (por defecto "en")
        current_lang = self.config.get("language", "en")
        self.lang_combo.setCurrentIndex(0 if current_lang == "en" else 1)
        lang_layout.addWidget(self.lang_combo)
        layout.addLayout(lang_layout)

        # 4. Tema
        theme_layout = QtWidgets.QVBoxLayout()
        theme_layout.setSpacing(4)
        theme_layout.addWidget(QtWidgets.QLabel(tr("label_theme")))
        self.theme_combo = QtWidgets.QComboBox()
        self.theme_combo.addItem(tr("theme_dark"), "dark")
        self.theme_combo.addItem(tr("theme_light"), "light")
        self.theme_combo.setCurrentIndex(0 if self.current_theme == "dark" else 1)
        theme_layout.addWidget(self.theme_combo)
        layout.addLayout(theme_layout)

        layout.addStretch()

        # Botones Guardar / Cancelar
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        self.cancel_btn = QtWidgets.QPushButton(tr("btn_cancel"))
        self.save_btn = QtWidgets.QPushButton(tr("btn_save_restart"))
        self.save_btn.setObjectName("AccentButton")
        
        self.cancel_btn.clicked.connect(self.reject)
        self.save_btn.clicked.connect(self.save_settings)
        
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)

    def browse_path(self):
        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, tr("win_select_pak"), "", "PAK files (*.pak)"
        )
        if file_name:
            self.path_input.setText(file_name)

    def save_settings(self):
        # Guardar en config.json
        self.config["gamePakPath"] = self.path_input.text().strip()
        self.config["aesKey"] = self.aes_input.text().strip()
        # Forzamos la lectura correcta según la posición (0 = Inglés, 1 = Español)
        self.config["language"] = "es" if self.lang_combo.currentIndex() == 1 else "en"
        save_config(self.config)
        
        # Guardar Tema
        save_theme(self.theme_combo.currentData())
        
        self.accept()