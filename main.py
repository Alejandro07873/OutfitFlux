import sys
import os

from PySide6 import QtWidgets, QtGui, QtCore

from util import (
    APP_NAME,
    ICON_PATH,
    MOD_DIR,
    safe_rmtree,
)
from skinslist import SkinsList
from choosemod import ChooseModFileWidget
from services.config_service import load_config, save_config
from services.game_service import (
    check_dotnet_runtime,
    validate_dependency_paths,
    validate_game_path,
)
from workers.startup_worker import StartupWorker
from ui.theme import apply_app_theme, toggle_app_theme, current_theme_name
from services.i18n_service import tr  # <-- IMPORT DE TRADUCCIÓN


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QtGui.QIcon(ICON_PATH))
        self.resize(1180, 820)
        self.setMinimumSize(980, 700)

        self.current_theme = current_theme_name(QtWidgets.QApplication.instance())

        self.central_widget = QtWidgets.QStackedWidget()
        self.setCentralWidget(self.central_widget)

        self.choosemodfile = ChooseModFileWidget(parent=self)
        self.central_widget.addWidget(self.choosemodfile)
        self.central_widget.setCurrentWidget(self.choosemodfile)

    def toggle_theme(self):
        app = QtWidgets.QApplication.instance()
        self.current_theme = toggle_app_theme(app)
        self.refresh_theme_ui_all()

    def refresh_theme_ui_all(self):
        self.current_theme = current_theme_name(QtWidgets.QApplication.instance())
        apply_app_theme(QtWidgets.QApplication.instance(), self.current_theme)
        for index in range(self.central_widget.count()):
            widget = self.central_widget.widget(index)
            if hasattr(widget, "refresh_theme_ui"):
                widget.refresh_theme_ui(self.current_theme)

    def show_choose_mod(self):
        self.central_widget.setCurrentWidget(self.choosemodfile)

    def viewSkinsList(self, character, mod_file, current_skin_name=None):
        skins_widget = SkinsList(
            character,
            mod_file,
            parent=self,
            current_skin_name=current_skin_name
        )
        self.central_widget.addWidget(skins_widget)
        self.central_widget.setCurrentWidget(skins_widget)

    def restart_app(self):
        if any(worker.isRunning() for worker in self.findChildren(QtCore.QThread)):
            QtWidgets.QMessageBox.information(self, 'Operación activa', 'Espera a que termine la operación antes de recargar la interfaz.')
            return
        # SOLUCIÓN DEFINITIVA: Recarga interna sin cerrar el .exe
        
        # 1. Forzamos la recarga de las variables del config.json
        load_config()
        
        # 2. Refrescamos el tema general
        self.refresh_theme_ui_all()
        
        # 3. Refrescamos la pantalla de Skins si está abierta
        for index in range(self.central_widget.count()):
            widget = self.central_widget.widget(index)
            if hasattr(widget, "refresh_language"):
                widget.refresh_language()

        # 4. Destruimos el menú principal viejo y lo creamos de nuevo 
        # para que lea automáticamente las nuevas traducciones al nacer.
        self.central_widget.removeWidget(self.choosemodfile)
        self.choosemodfile.deleteLater()
        
        self.choosemodfile = ChooseModFileWidget(parent=self)
        self.central_widget.insertWidget(0, self.choosemodfile)
        self.central_widget.setCurrentWidget(self.choosemodfile)

        # 5. Avisamos al usuario que el cambio fue exitoso sin reiniciar.
        QtWidgets.QMessageBox.information(
            self, 
            tr("settings_title"), 
            "Settings applied successfully! / Configuración aplicada."
        )

    def closeEvent(self, event):
        active = [worker for worker in self.findChildren(QtCore.QThread) if worker.isRunning()]
        if active:
            for worker in active:
                if hasattr(worker, 'cancel'):
                    worker.cancel()
            if not hasattr(self, '_close_timer'):
                self._close_timer = QtCore.QTimer(self)
                self._close_timer.setInterval(200)
                self._close_timer.timeout.connect(self.close)
                self._close_timer.start()
            event.ignore()
            return
        safe_rmtree(MOD_DIR)
        event.accept()


class LoadingDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("loading_title"))
        self.setWindowIcon(QtGui.QIcon(ICON_PATH))
        self.setModal(True)
        self.setFixedSize(540, 200)

        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.setContentsMargins(18, 18, 18, 18)

        card = QtWidgets.QFrame()
        card.setObjectName("HeroCard")
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(10)

        self.title = QtWidgets.QLabel(tr("loading_title"))
        self.title.setObjectName("TitleLabel")

        self.label = QtWidgets.QLabel(tr("loading_startup"))
        self.label.setObjectName("SubtitleLabel")
        self.label.setWordWrap(True)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(1)
        self.progress_bar.setValue(0)

        card_layout.addWidget(self.title)
        card_layout.addWidget(self.label)
        card_layout.addSpacing(4)
        card_layout.addWidget(self.progress_bar)

        outer_layout.addWidget(card)

    def update_progress(self, current, total, text):
        self.label.setText(text)
        self.progress_bar.setMaximum(max(total, 1))
        self.progress_bar.setValue(current)
        QtWidgets.QApplication.processEvents()


def show_critical_message(title, text, informative_text=""):
    msg = QtWidgets.QMessageBox()
    msg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
    msg.setWindowTitle(title)
    msg.setWindowIcon(QtGui.QIcon(ICON_PATH))
    msg.setText(text)
    if informative_text:
        msg.setInformativeText(informative_text)
    return msg.exec()


def ask_for_game_pak():
    return QtWidgets.QFileDialog.getOpenFileName(
        None,
        tr("win_select_pak"),
        "",
        "MHUR PAK (HerovsGame-WindowsNoEditor.pak);;All files (*.*)"
    )[0]


def main():
    app = QtWidgets.QApplication(sys.argv)
    apply_app_theme(app)

    missing_dependencies = validate_dependency_paths()
    if missing_dependencies:
        show_critical_message(
            tr("err_missing_deps"),
            tr("err_msg_missing_deps"),
            "<br>".join(missing_dependencies),
        )
        return 1

    if not check_dotnet_runtime():
        show_critical_message(
            tr("err_dotnet"),
            tr("err_msg_dotnet"),
            (
                "This application requires .NET 8.0 runtime to be installed. "
                "Please install it from "
                "<a style='color: #7db7ff' href='https://dotnet.microsoft.com/en-us/download/dotnet'>here</a> "
                "or direct download from "
                "<a style='color: #7db7ff' href='https://dotnet.microsoft.com/en-us/download/dotnet/thank-you/runtime-desktop-8.0.23-windows-x64-installer'>here</a> "
                "and try again."
            ),
        )
        return 1

    config = load_config()
    aes_key = config.get("aesKey")
    game_path = config.get("gamePakPath")

    if not validate_game_path(game_path):
        game_path = ask_for_game_pak()
        if not validate_game_path(game_path):
            return 0
        config["gamePakPath"] = game_path

    save_config(config)

    loading = LoadingDialog()
    loading.show()

    state = {
        "window": None,
        "worker": None,
    }

    def on_startup_progress(current, total, text):
        loading.update_progress(current, total, text)

    def on_startup_finished(result):
        loading.close()

        window = MainWindow()
        state["window"] = window
        window.show()

    def on_startup_error(error_text):
        loading.close()
        show_critical_message(
            tr("err_startup"),
            tr("err_msg_startup"),
            error_text,
        )
        app.exit(1)

    worker = StartupWorker(aes_key, game_path)
    state["worker"] = worker

    worker.progress.connect(on_startup_progress)
    worker.finished_ok.connect(on_startup_finished)
    worker.error.connect(on_startup_error)
    worker.finished.connect(worker.deleteLater)

    worker.start()

    return app.exec()


if __name__ == "__main__":
    try:
        if '--classic' in sys.argv:
            sys.argv.remove('--classic')
            sys.exit(main())
        else:
            from studio import main as studio_main
            sys.exit(studio_main())
    except Exception:
        import traceback
        from pathlib import Path
        from util import WORKSPACE_DIR
        log = Path(WORKSPACE_DIR) / 'startup-error.log'
        log.write_text(traceback.format_exc(), encoding='utf-8')
        raise
