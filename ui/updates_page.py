from pathlib import Path
import subprocess
from PySide6 import QtCore, QtWidgets as W
from services.config_service import load_config, save_config
from services.update_service import check_update, install_update, repository
from util import APP_VERSION

class UpdatesPage(W.QWidget):
    def __init__(self,window):
        super().__init__();self.window=window;self.release=None;self.ready=None
        layout=W.QVBoxLayout(self);layout.setContentsMargins(28,24,28,24);layout.setSpacing(18)
        self.heading=W.QLabel();self.heading.setObjectName('ShelfTitle');layout.addWidget(self.heading)
        self.version=W.QLabel('OutfitFlux '+APP_VERSION);layout.addWidget(self.version)
        self.help=W.QLabel();self.help.setWordWrap(True);layout.addWidget(self.help)
        row=W.QHBoxLayout();self.repo=W.QLineEdit(load_config().get('updateRepository',''));self.repo.setPlaceholderText('usuario/OutfitFlux');row.addWidget(self.repo,1)
        self.check=W.QPushButton();self.check.setObjectName('Primary');self.check.clicked.connect(self.check_now);row.addWidget(self.check);layout.addLayout(row)
        self.state=W.QLabel();self.state.setWordWrap(True);layout.addWidget(self.state)
        self.notes=W.QPlainTextEdit();self.notes.setReadOnly(True);layout.addWidget(self.notes,1)
        self.install=W.QPushButton();self.install.setObjectName('Primary');self.install.setEnabled(False);self.install.clicked.connect(self.install_now);layout.addWidget(self.install)
        self.open=W.QPushButton();self.open.hide();self.open.clicked.connect(self.open_ready);layout.addWidget(self.open)
        self.translate()
    def t(self,es,en):return en if self.window.preferences.get('language')=='en' else es
    def translate(self):
        self.heading.setText(self.t('Actualizaciones','Updates'))
        self.repo.setPlaceholderText('owner/OutfitFlux' if self.window.preferences.get('language')=='en' else 'usuario/OutfitFlux')
        self.notes.setPlaceholderText(self.t('Las novedades de la próxima versión aparecerán aquí.','Release notes will appear here after checking for updates.'))
        self.help.setText(self.t('Configura tu repositorio público de GitHub. Las versiones se publican en Releases; tus ajustes y biblioteca se conservan.','Set your public GitHub repository. Versions are published in Releases; settings and library are preserved.'))
        self.check.setText(self.t('Buscar actualización','Check for updates'))
        self.install.setText(self.t('Descargar y preparar actualización','Download and prepare update'))
        self.open.setText(self.t('Abrir nueva versión y cerrar esta','Open new version and close this one'))
    def error(self,text):W.QMessageBox.warning(self,self.t('Actualización','Update'),text)
    def check_now(self):
        try:repo=repository(self.repo.text())
        except ValueError as exc:self.error(str(exc));return
        config=load_config();config['updateRepository']=repo;save_config(config)
        self.repo.setText(repo);self.release=None;self.install.setEnabled(False)
        self.window.start_task(self.t('Buscando actualización…','Checking for updates…'),lambda cancel,progress:check_update(repo,cancel),self.checked)
    def checked(self,result):
        self.release=result;self.notes.setPlainText(result['notes'])
        self.state.setText(self.t('Nueva versión: ','New version: ')+result['version'] if result['newer'] else self.t('Ya tienes la versión más reciente.','You have the latest version.'))
        self.install.setEnabled(bool(result['newer'] and result['asset']))
        if result['newer'] and not result['asset']:self.state.setText(self.t('La versión no incluye OutfitFlux-windows-x64.zip.','The release does not include OutfitFlux-windows-x64.zip.'))
    def busy(self):
        return self.window.worker is not None or any(j['status'] in ('waiting','running') for j in self.window.export_jobs.jobs)
    def install_now(self):
        if self.busy():self.error(self.t('Espera a que terminen los trabajos antes de actualizar.','Wait for active jobs to finish before updating.'));return
        if not self.release:return
        release=dict(self.release)
        self.window.start_task(self.t('Preparando actualización…','Preparing update…'),lambda cancel,progress:install_update(release,cancel,progress),self.prepared)
    def prepared(self,path):
        self.ready=path;self.install.setEnabled(False);self.open.show()
        self.state.setText(self.t('Actualización verificada y preparada. La versión anterior se conserva.','Update verified and ready. The previous version is preserved.'))
    def open_ready(self):
        if self.busy():self.error(self.t('Termina los trabajos antes de cambiar de versión.','Finish active jobs before switching versions.'));return
        if self.ready and Path(self.ready).is_file():
            subprocess.Popen([self.ready],cwd=str(Path(self.ready).parent),creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            self.window.close()
