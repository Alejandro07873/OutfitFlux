from pathlib import Path
from PySide6 import QtWidgets as W, QtCore
from services.config_service import load_config, save_config


def claim_initial_setup():
    """Remember the first opening across portable builds, even if dismissed."""
    settings = QtCore.QSettings('OutfitFlux', 'OutfitFlux')
    config = load_config()
    seen = bool(config.get('outfitFluxSetup')) or settings.value('initialSetupShown', False, type=bool)
    settings.setValue('initialSetupShown', True)
    settings.sync()
    if not config.get('outfitFluxSetup'):
        config['outfitFluxSetup'] = True
        save_config(config)
    return not seen

class SetupDialog(W.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = load_config()
        self.resize(620, 460)
        layout = W.QVBoxLayout(self)
        layout.setContentsMargins(28,24,28,24)
        self.title = W.QLabel('OutfitFlux')
        self.title.setStyleSheet('font-size:28px; font-weight:700')
        layout.addWidget(self.title)
        form = W.QFormLayout()
        form.setSpacing(16)
        layout.addLayout(form)
        self.language = W.QComboBox()
        self.language.addItem('Español','es'); self.language.addItem('English','en')
        self.language.setCurrentIndex(1 if self.config.get('language') == 'en' else 0)
        self.theme = W.QComboBox()
        self.theme.addItem('', 'dark'); self.theme.addItem('', 'white')
        self.theme.setCurrentIndex(0 if self.config.get('studioTheme','dark') == 'dark' else 1)
        self.color = W.QComboBox()
        for value in ['#0a84ff','#8b5cf6','#db2777','#008a63','#a36500']:
            self.color.addItem('',value)
        self.color.setCurrentIndex(max(0,self.color.findData(self.config.get('accentColor','#0a84ff'))))
        self.path = W.QLineEdit(self.config.get('gamePakPath',''))
        row=W.QHBoxLayout();row.addWidget(self.path)
        self.browse=W.QPushButton('…');row.addWidget(self.browse)
        self.browse.clicked.connect(self.pick)
        self.labels=[W.QLabel() for _ in range(4)]
        for label,field in zip(self.labels,[self.language,self.theme,self.color,row]):
            form.addRow(label,field)
        self.hint=W.QLabel();self.hint.setWordWrap(True);layout.addWidget(self.hint)
        self.advanced=W.QGroupBox();self.advanced.setCheckable(True);self.advanced.setChecked(False)
        advanced_layout=W.QFormLayout(self.advanced)
        self.aes=W.QLineEdit(self.config.get('aesKey',''));self.aes.setEchoMode(W.QLineEdit.EchoMode.Password)
        advanced_layout.addRow('AES',self.aes);layout.addWidget(self.advanced)
        self.aes.hide()
        advanced_layout.labelForField(self.aes).hide()
        self.advanced.toggled.connect(self.aes.setVisible)
        self.advanced.toggled.connect(advanced_layout.labelForField(self.aes).setVisible)
        self.repository=W.QLineEdit(self.config.get('updateRepository',''))
        self.repository.setPlaceholderText('usuario/OutfitFlux')
        self.repo_label=W.QLabel()
        form.addRow(self.repo_label,self.repository)
        layout.addStretch()
        self.buttons=W.QDialogButtonBox(W.QDialogButtonBox.StandardButton.Save|W.QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.save);self.buttons.rejected.connect(self.reject);layout.addWidget(self.buttons)
        self.language.currentIndexChanged.connect(self.translate)
        self.translate()
        self._applying_appearance = False
        for control in (self.language, self.theme, self.color):
            control.currentIndexChanged.connect(self.apply_appearance)

    def apply_appearance(self):
        if self._applying_appearance:
            return
        self._applying_appearance = True
        try:
            config = load_config()
            config.update(language=self.language.currentData(), studioTheme=self.theme.currentData(), accentColor=self.color.currentData())
            save_config(config)
            if self.parent() and hasattr(self.parent(), 'refresh_preferences'):
                self.parent().refresh_preferences()
            self.translate()
        finally:
            self._applying_appearance = False
    def translate(self):
        en=self.language.currentData()=='en'
        self.repository.setPlaceholderText('owner/OutfitFlux' if en else 'usuario/OutfitFlux')
        self.repo_label.setText('GitHub updates' if en else 'Actualizaciones GitHub')
        self.setWindowTitle('OutfitFlux · Settings' if en else 'OutfitFlux · Configuración')
        for label,text in zip(self.labels,['Language','Appearance','Accent color','Game PAK'] if en else ['Idioma','Apariencia','Color de acento','PAK del juego']):label.setText(text)
        for i,text in enumerate(['Dark','Light'] if en else ['Oscuro','Claro']):self.theme.setItemText(i,text)
        for i,text in enumerate(['Blue','Violet','Rose','Emerald','Amber'] if en else ['Azul','Violeta','Rosa','Esmeralda','Ámbar']):self.color.setItemText(i,text)
        self.hint.setText('Language and appearance are applied and saved immediately. Save to keep changes to paths and GitHub.' if en else 'El idioma y la apariencia se aplican y guardan al instante. Pulsa Guardar para conservar cambios de rutas y GitHub.')
        self.advanced.setTitle('Advanced · AES key' if en else 'Avanzado · Clave AES')
        self.buttons.button(W.QDialogButtonBox.StandardButton.Save).setText('Save' if en else 'Guardar')
        self.buttons.button(W.QDialogButtonBox.StandardButton.Cancel).setText('Close' if en else 'Cerrar')
    def pick(self):
        path,_=W.QFileDialog.getOpenFileName(self,'PAK',self.path.text(),'PAK (*.pak)')
        if path:self.path.setText(path)
    def save(self):
        value=self.path.text().strip()
        if value and not Path(value).is_file():
            W.QMessageBox.warning(self,'PAK','Select an existing PAK file.' if self.language.currentData()=='en' else 'Selecciona un archivo PAK existente.')
            return
        repo=self.repository.text().strip()
        if repo:
            from services.update_service import repository
            try:repo=repository(repo)
            except ValueError as exc:
                W.QMessageBox.warning(self,'GitHub',str(exc));return
        config=load_config()
        config['updateRepository']=repo
        config.update(gamePakPath=value,language=self.language.currentData(),studioTheme=self.theme.currentData(),accentColor=self.color.currentData(),outfitFluxSetup=True)
        if self.advanced.isChecked():config['aesKey']=self.aes.text().strip()
        save_config(config)
        self.accept()
