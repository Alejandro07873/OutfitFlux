"""Functional Studio on the approved iOS-inspired shell."""
from ui.outfit_translations import tr_text
import json
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets as W

from ui.studio_shell import SwapStudio
from workers.task_worker import TaskWorker
from services.studio_service import load_library, export_queue, read_history, index_fmodel, inspect_asset_json
from services.pak_service import inspect_pak, compare_paks, extract_pak
from services.safe_export_service import create_final_pak, normalize_export_path
from services.config_service import load_config, save_config
from services.json_store import write_json
from util import CONFIG_DIR, CHARACTER_DIR, unrealPak, repakPath, uejsonPath


class StudioWindow(SwapStudio):
    def __init__(self):
        self.worker = None
        self._closing = False
        self._initializing = True
        self.mod_info = None
        self.source_mesh = None
        self.category = 0
        self.category_queues = {0: {}, 1: {}}
        self.queue = self.category_queues[0]
        self.preferences = load_config()
        self.favorites = set(self.preferences.get('favorites', []))
        self._items_ready = False
        super().__init__()
        self._initializing = False
        self.setWindowTitle('OutfitFlux')
        from ui.export_queue import ExportQueue
        self.export_jobs = ExportQueue(self)
        self.pages.addWidget(self.export_jobs)
        self.source = None
        self.target = None
        self.source_image.clear()
        self.target_image.clear()
        self.source_title.setText('Importa tu mod')
        self.source_id.setText('PAK original protegido')
        self.target_title.setText('Elige un destino')
        self.target_id.setText('Desde la biblioteca')
        self.source_action.setText('Cambiar malla')
        self.import_button.setText('Cambiar mod')
        self.grid.setSelectionMode(W.QAbstractItemView.SelectionMode.ExtendedSelection)
        from ui.skin_delegate import SkinDelegate
        self.grid.setItemDelegate(SkinDelegate(self))
        self.grid.setMouseTracking(True)
        self.character_gallery = W.QListWidget()
        self.character_gallery.setViewMode(W.QListView.ViewMode.IconMode)
        self.character_gallery.setResizeMode(W.QListView.ResizeMode.Adjust)
        self.character_gallery.setMovement(W.QListView.Movement.Static)
        self.character_gallery.setIconSize(QtCore.QSize(120,130))
        self.character_gallery.setGridSize(QtCore.QSize(190,220))
        self.character_gallery.itemClicked.connect(self.choose_character_card)
        self.workspace_layout.insertWidget(self.workspace_layout.indexOf(self.grid), self.character_gallery, 1)
        self.character_gallery.hide()
        self.back_characters = W.QPushButton('← Personajes')
        self.back_characters.clicked.connect(lambda: self.character.setCurrentIndex(0))
        self.catalog_heading.insertWidget(0, self.back_characters)
        self.back_characters.hide()
        self.grid.itemClicked.connect(self.inspect)
        self.grid.itemDoubleClicked.connect(lambda _: self.set_target())
        self.grid.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.grid.customContextMenuRequested.connect(self.context_menu)
        self.search.textChanged.disconnect()
        self.search_timer = QtCore.QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(120)
        self.search_timer.timeout.connect(self.filter_records)
        self.search.textChanged.connect(lambda: self.search_timer.start())
        self.order_combo.currentIndexChanged.connect(self.sort_records)
        self.kind_combo.currentIndexChanged.connect(self.filter_records)
        toolbar = self.selection_toolbar
        self.favorite_filter = W.QCheckBox('Favoritos')
        self.favorite_filter.toggled.connect(self.filter_records)
        toolbar.addWidget(self.favorite_filter)
        select = W.QPushButton('Selección')
        selection_menu = W.QMenu(select)
        self.selection_menu_actions = [selection_menu.addAction('Seleccionar visibles', self.select_visible),
                                       selection_menu.addAction('Limpiar selección', self.grid.clearSelection)]
        self.selection_button = select
        select.clicked.connect(self.select_visible)
        self.clear_selection_button = W.QPushButton('Limpiar selección')
        self.clear_selection_button.clicked.connect(self.grid.clearSelection)
        toolbar.addWidget(select)
        toolbar.addWidget(self.clear_selection_button)
        toolbar.addStretch()
        enqueue = W.QPushButton('+  Añadir a la cola')
        self.enqueue_button = enqueue
        enqueue.clicked.connect(self.enqueue)
        enqueue.hide()
        self.queue_button = W.QPushButton('Cola · 0')
        self.queue_button.clicked.connect(self.show_queue)
        self.queue_button.hide()
        self.batch_button = W.QPushButton('Exportar seleccionados (0)')
        self.batch_button.setObjectName('Primary')
        self.batch_button.clicked.connect(self.export_selected)
        toolbar.addWidget(self.batch_button)
        self.selection_counter = W.QLabel('0 seleccionados')
        self.selection_counter.setObjectName('Muted')
        self.selection_counter.hide()  # The export button already shows the count.
        self.grid.itemSelectionChanged.connect(self.selection_changed)
        self.accent_combo.blockSignals(True)
        self.accent_combo.setCurrentIndex(max(0, self.accent_combo.findData(self.preferences.get('accentColor', '#0a84ff'))))
        self.accent_combo.blockSignals(False)
        self.set_theme(self.preferences.get('studioTheme', 'dark') == 'dark')
        self.review.setText('Exportar destino  →')
        self.update_summary()
        self.resize(1200, 720)
        screen = self.screen().availableGeometry()
        self.resize(min(1200, screen.width()), min(720, max(500, screen.height() - 40)))
        self.apply_category()
        self.setAcceptDrops(True)
        self.language_combo.setCurrentIndex(0 if self.preferences.get('language', 'es') == 'es' else 1)
        self.language_combo.currentIndexChanged.connect(self.change_language)
        self.apply_language()
        for key, callback in [('Ctrl+O', self.pick_mod), ('Ctrl+F', self.search.setFocus)]:
            shortcut = QtGui.QShortcut(QtGui.QKeySequence(key), self)
            shortcut.activated.connect(callback)

    def load_records(self):
        self.records, self.library_warnings = load_library()

    def open_session(self):
        self.pick_mod()

    def choose_character_card(self, item):
        self.character.setCurrentIndex(self.character.findData(item.data(QtCore.Qt.ItemDataRole.UserRole)))

    def selected_records(self):
        return [item.data(QtCore.Qt.ItemDataRole.UserRole) for item in self.grid.selectedItems()
                if not item.isHidden() and (not self.source or item.data(QtCore.Qt.ItemDataRole.UserRole)['skin_path'] != self.source['skin_path'])]

    def selection_changed(self):
        if not hasattr(self, 'batch_button'):
            return
        count = len(self.selected_records())
        english = self.preferences.get('language', 'es') == 'en'
        self.batch_button.setText(('Export selected' if english else 'Exportar seleccionados') + f' ({count})')
        self.batch_button.setEnabled(bool(count and self.mod_info))
        self.selection_counter.setText(f'{count} ' + ('selected' if english else 'seleccionados'))

    def export_selected(self):
        records = [dict(record) for record in self.selected_records()]
        if records:
            self.export_records(records, batch=True)

    def sort_records(self):
        selected = {r['skin_path'] for r in self.selected_records()}
        current = self.target['skin_path'] if self.target else None
        key = self.order_combo.currentData()
        self.records.sort(key=lambda r: int(r['id']) if key == 'id' and r['id'].isdigit() else r.get(key, '').casefold())
        self._items_ready = False
        self.filter_records()
        self.grid.clearSelection()
        for index in range(self.grid.count()):
            item = self.grid.item(index)
            path = item.data(QtCore.Qt.ItemDataRole.UserRole)['skin_path']
            if path == current:
                self.grid.setCurrentItem(item, QtCore.QItemSelectionModel.SelectionFlag.NoUpdate)
            item.setSelected(path in selected)

    def change_language(self):
        selected = {r['skin_path'] for r in self.selected_records()}
        current = self.target['skin_path'] if self.target else None
        self.preferences['language'] = self.language_combo.currentData()
        config = load_config()
        config['language'] = self.preferences['language']
        save_config(config)
        self.load_records()
        by_path = {r['skin_path']: r for r in self.records}
        if self.source:
            self.source = by_path.get(self.source['skin_path'], self.source)
        for queue in self.category_queues.values():
            for path in list(queue):
                queue[path] = by_path.get(path, queue[path])
        self._items_ready = False
        self.filter_records()
        self.grid.clearSelection()
        for index in range(self.grid.count()):
            item = self.grid.item(index)
            path = item.data(QtCore.Qt.ItemDataRole.UserRole)['skin_path']
            if path == current:
                self.grid.setCurrentItem(item, QtCore.QItemSelectionModel.SelectionFlag.NoUpdate)
            item.setSelected(path in selected)
        self.apply_language()

    def apply_language(self):
        english = self.preferences.get('language', 'es') == 'en'
        pairs = [(self.tab_group.button(0), 'Trajes', 'Costumes'), (self.tab_group.button(1), 'Entre personajes', 'Cross-character'),
                 (self.tab_group.button(2), 'Herramientas', 'Tools'), (self.home_import, '+  Importar mod PAK', '+  Import mod PAK'),
                 (self.import_button, 'Cambiar mod', 'Change mod'), (self.source_action, 'Cambiar malla', 'Change mesh'),
                 (self.favorite_filter, 'Favoritos', 'Favorites'), (self.review, 'Exportar este traje →', 'Export this costume →')]
        for widget, es, en in pairs:
            widget.setText(en if english else es)
        self.search.setPlaceholderText('Search costume, internal name or ID' if english else 'Buscar traje, nombre interno o ID')
        for combo, es, en in [(self.order_combo, ['Orden: ID','Orden: nombre','Orden: nombre interno'], ['Sort: ID','Sort: name','Sort: internal name']),
                              (self.kind_combo, ['Todos los trajes','Traje actual','Sin identificar'], ['All costumes','Current costume','Unknown'])]:
            for i, text in enumerate(en if english else es):
                combo.setItemText(i, text)
        self.heading.setText(('Change your costume.' if self.category == 0 else 'Cross-character swaps.') if english else ('Cambia de traje.' if self.category == 0 else 'Intercambia entre personajes.'))
        self.home_description.setText(('Import a mod to see costumes for its character.' if self.category == 0 else 'Import a mod, then choose a different destination character.') if english else ('Importa tu mod. Verás únicamente los trajes de su personaje.' if self.category == 0 else 'Importa el mod y elige otro personaje de destino.'))
        self.home_hint.setText('1. Import mod     2. Choose costume     3. Export' if english else '1. Importar mod     2. Elegir traje     3. Exportar')
        from ui.outfit_translations import ScreenTranslator
        ScreenTranslator().translate(self, english)
        for index, text in enumerate(['Blue','Violet','Rose','Emerald','Amber'] if english else ['Azul','Violeta','Rosa','Esmeralda','Ámbar']):
            self.accent_combo.setItemText(index, text)
        self.catalog_button.setText('Update catalog' if english else 'Actualizar catálogo')
        self.catalog_shortcut.setText('Update catalog' if english else 'Actualizar catálogo')
        self.tab_group.button(3).setText('Queue' if english else 'Cola')
        if hasattr(self, 'export_jobs'):
            self.export_jobs.refresh()
        if hasattr(self, 'tools_page'):
            old_page = self.tools_page
            current = self.pages.currentWidget()
            section = self.tools_navigation.currentRow()
            self.pages.removeWidget(old_page)
            del self.tools_page
            self.show_tools()
            self.tools_navigation.setCurrentRow(section)
            if current is not old_page:
                self.pages.setCurrentWidget(current)
            old_page.deleteLater()
        if hasattr(self, 'updates_page'):
            self.updates_page.translate()
        self.back_characters.setText('← Characters' if english else '← Personajes')
        self.update_summary()
        self.selection_changed()
        self.theme_button.setText(('☀  White' if self.dark else '☾  Dark') if english else ('☀  Claro' if self.dark else '☾  Oscuro'))
        self.selection_menu_actions[0].setText('Select visible' if english else 'Seleccionar visibles')
        self.selection_menu_actions[1].setText('Clear selection' if english else 'Limpiar selección')
        self.selection_button.setText('Select visible' if english else 'Seleccionar visibles')
        self.clear_selection_button.setText('Clear selected' if english else 'Limpiar selección')
        self.enqueue_button.setText('+  Add to queue' if english else '+  Añadir a la cola')
        self.queue_button.setText(('Queue' if english else 'Cola') + f' · {len(self.queue)}')
        if self.category == 0:
            self.category_label.setText('IMPORTED MOD · SAME CHARACTER COSTUMES' if english else 'MOD IMPORTADO · TRAJES DEL MISMO PERSONAJE')
            self.shelf_title.setText((f"Costumes for {self.source['character']}" if self.source else 'Choose a destination costume') if english else (('Trajes de ' + self.source['character']) if self.source else 'Elige el traje de destino'))
        else:
            self.category_label.setText('IMPORTED MOD · CROSS-CHARACTER' if english else 'MOD IMPORTADO · ENTRE PERSONAJES')
            self.shelf_title.setText('Destination character and costume' if english else 'Personaje y traje de destino')

    def filter_records(self, *_):
        if not self._items_ready:
            self.grid.clear()
            for record in self.records:
                item = W.QListWidgetItem(QtGui.QIcon(record['image']), f'{record["name"]}\n{record["character"]} · {record["id"]}')
                item.setData(QtCore.Qt.ItemDataRole.UserRole, record)
                item.setSizeHint(QtCore.QSize(178, 204))
                item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                item.setToolTip(record['name'] + '\n' + record['internal'])
                self.grid.addItem(item)
            self._items_ready = True
        query = self.search.text().strip().casefold()
        character = self.character.currentData()
        if hasattr(self, 'character_gallery'):
            gallery = bool(self.source and self.category == 1 and not character)
            self.character_gallery.setVisible(gallery)
            self.grid.setVisible(not gallery)
            self.back_characters.setVisible(bool(self.category == 1 and character))
            self.back_characters.setText('← Characters' if self.preferences.get('language') == 'en' else '← Personajes')
        favorites_only = hasattr(self, 'favorite_filter') and self.favorite_filter.isChecked()
        visible = []
        for i in range(self.grid.count()):
            item = self.grid.item(i)
            record = item.data(QtCore.Qt.ItemDataRole.UserRole)
            allowed = bool(self.source)
            if self.source and self.category == 0:
                allowed = record['character'] == self.source['character']
            elif self.source:
                allowed = bool(character) and record['character'] == character and character != self.source['character']
            match = allowed and query in record['search']
            kind = self.kind_combo.currentData() if hasattr(self, 'kind_combo') else 'all'
            if kind == 'current':
                match = match and bool(self.source and record['skin_path'] == self.source['skin_path'])
            elif kind == 'unknown':
                match = match and not record['is_known']
            match = match and (not favorites_only or record['skin_path'] in self.favorites)
            item.setHidden(not match)
            if not match:
                item.setSelected(False)
            else:
                visible.append(item)
        self.count.setText((f'{len(visible)} costumes · Ctrl to select multiple' if self.preferences.get('language') == 'en' else f'{len(visible)} trajes disponibles · Ctrl para selección múltiple') if visible
                           else (tr_text('Elige el personaje de destino.') if self.category == 1 and self.source and not character
                                 else tr_text('No hay trajes para esta selección.')))
        if visible and (not self.grid.currentItem() or self.grid.currentItem().isHidden()):
            current = next((item for item in visible if self.source and item.data(QtCore.Qt.ItemDataRole.UserRole)['skin_path'] == self.source['skin_path']), visible[0])
            self.grid.setCurrentItem(current)
        elif not visible:
            self.inspect(None)

    def set_theme(self, dark):
        super().set_theme(dark)
        if not self._initializing:
            self.preferences['studioTheme'] = 'dark' if dark else 'white'
            self.preferences['accentColor'] = self.accent_combo.currentData()
            self.persist_preferences()

    def persist_preferences(self):
        # Merge so settings edited through the legacy settings dialog are retained.
        config = load_config()
        config.update({key: self.preferences[key] for key in ('studioTheme', 'accentColor', 'favorites', 'fmodelRoot', 'outputRoot') if key in self.preferences})
        save_config(config)

    def start_task(self, title, function, on_result):
        if self.worker is not None:
            self.progress_dialog.show()
            self.progress_dialog.raise_()
            return
        self.progress_dialog = W.QProgressDialog(title, tr_text('Cancelar'), 0, 0, self)
        self.progress_dialog.setWindowTitle(title)
        self.progress_dialog.setWindowModality(QtCore.Qt.WindowModality.NonModal)
        self.progress_dialog.setAutoClose(False)
        self.progress_dialog.setAutoReset(False)
        worker = TaskWorker(function, self)
        self.worker = worker
        self._task_result = None
        self._task_error = None
        worker.result.connect(self.capture_result)
        worker.error.connect(self.capture_error)
        worker.cancelled.connect(lambda: setattr(self, '_task_error', tr_text('Operación cancelada.')))
        worker.progress.connect(self.task_progress)
        self.progress_dialog.canceled.connect(worker.cancel)
        self._task_callback = on_result
        worker.finished.connect(self.task_finished)
        worker.start()
        self.progress_dialog.show()

    def capture_result(self, result):
        self._task_result = result

    def capture_error(self, error):
        self._task_error = error

    def task_progress(self, current, total, text):
        self.progress_dialog.setRange(0, total)
        self.progress_dialog.setValue(current)
        self.progress_dialog.setLabelText(tr_text(text))

    def task_finished(self):
        worker = self.worker
        self.worker = None
        self.progress_dialog.close()
        self.progress_dialog.deleteLater()
        worker.deleteLater()
        if self._closing:
            self.close()
            return
        if self._task_error:
            W.QMessageBox.warning(self, tr_text('Operación'), tr_text(self._task_error))
        elif self._task_result is not None:
            self._task_callback(self._task_result)

    def closeEvent(self, event):
        if hasattr(self, 'export_jobs') and self.export_jobs.worker is not None:
            self.export_jobs.closing = True
            self.export_jobs.worker.cancel()
            event.ignore()
            return
        if self.worker is not None:
            self._closing = True
            self.worker.cancel()
            self.status.setText(tr_text('Esperando a que termine la operación antes de cerrar…'))
            event.ignore()
        else:
            event.accept()

    def pick_mod(self):
        path, _ = W.QFileDialog.getOpenFileName(self, tr_text('Importar mod'), '', 'Mod PAK (*.pak)')
        if path:
            self.import_mod(path)

    def import_mod(self, path):
        self.start_task(tr_text('Inspeccionando mod…'), lambda cancel, progress: inspect_pak(path, cancel), self.mod_loaded)

    def mod_loaded(self, info):
        if not info['meshes']:
            self.show_report(tr_text('PAK sin malla intercambiable'), info)
            return
        selected = info['meshes'][0]
        if len(info['meshes']) > 1:
            selected, ok = W.QInputDialog.getItem(self, tr_text('Mod con varias mallas'), tr_text('Malla que quieres reasignar; las demás se conservarán:'), info['meshes'], 0, False)
            if not ok:
                return
        self.mod_info = info
        self.source_mesh = selected
        internal = Path(selected).stem
        record = next((r for r in self.records if r['internal'] == internal), None)
        if not record:
            character = next((p for p in selected.split('/') if p.startswith('Ch') and len(p) == 5), '?')
            record = dict(name=internal, internal=internal, character=character, id='Mod', image='', skin_path=selected.partition('Character/')[2])
        self.source = record
        self.target = None
        for queue in self.category_queues.values():
            queue.clear()
        self.apply_category()

    def apply_category(self):
        self.queue = self.category_queues[self.category]
        self.queue_button.setText(f'Cola · {len(self.queue)}')
        self.mode.setCurrentIndex(self.category)
        self.target = None
        self.search.clear()
        self.grid.clearSelection()
        self.character.blockSignals(True)
        self.character.clear()
        self.character.addItem(tr_text('Elige personaje…'), '')
        if self.source:
            for ch in sorted({r['character'] for r in self.records if r['character'] != self.source['character']}):
                self.character.addItem(ch, ch)
        self.character.blockSignals(False)
        self.character.hide()
        self.character_gallery.clear()
        if self.source and self.category == 1:
            for ch in sorted({r['character'] for r in self.records if r['character'] != self.source['character']}):
                costumes = [r for r in self.records if r['character'] == ch]
                record = next((r for r in costumes if 'Default' in r['internal']), costumes[0])
                from ui.character_names import NAMES
                item = W.QListWidgetItem(QtGui.QIcon(record['image']), NAMES.get(ch,ch) + '\n' + str(len(costumes)) + (' costumes' if self.preferences.get('language') == 'en' else ' trajes'))
                item.setData(QtCore.Qt.ItemDataRole.UserRole,ch)
                item.setSizeHint(QtCore.QSize(180,210))
                self.character_gallery.addItem(item)
        self.heading.setText('Cambia de traje.' if self.category == 0 else 'Intercambia entre personajes.')
        self.home_description.setText('Importa tu mod. Verás únicamente los trajes de su personaje.' if self.category == 0
                                      else 'Importa el mod de origen y después elige otro personaje de destino.')
        self.home_hint.setText('1. Importar mod     2. Elegir traje     3. Exportar' if self.category == 0
                              else 'Elige el personaje y después su traje de destino.')
        self.shelf_title.setText('Trajes de ' + self.source['character'] if self.source and self.category == 0
                                else 'Personaje y traje de destino')
        self.category_label.setText('MOD IMPORTADO · TRAJES DEL MISMO PERSONAJE' if self.category == 0
                                    else 'MOD IMPORTADO · ENTRE PERSONAJES')
        self.pages.setCurrentWidget(self.workspace if self.mod_info else self.home)
        self.source_action.setVisible(bool(self.mod_info and len(self.mod_info['meshes']) > 1))
        self.filter_records()
        self.update_summary()
        if hasattr(self, 'language_combo'):
            self.apply_language()

    def inspect(self, item, previous=None):
        if not hasattr(self, 'selection_name'):
            return
        self.target = None
        self.selection_image.clear()
        self.selection_details.setText('')
        if item and not item.isHidden() and self.source:
            record = item.data(QtCore.Qt.ItemDataRole.UserRole)
            permitted = (record['character'] == self.source['character']) if self.category == 0 else (record['character'] != self.source['character'])
            if permitted:
                self.target = record
                self.selection_name.setText(record['name'] + ' · ' + record['character'])
                self.selection_details.setText(f"{record['internal']}  ·  ID {record['id']}")
                self.selection_image.setPixmap(QtGui.QPixmap(record['image']).scaled(42, 48, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation))
        if not self.target:
            self.selection_name.setText('Choose a destination costume' if self.preferences.get('language') == 'en' else 'Selecciona un traje de destino')
        self.update_summary()

    def set_source(self):
        if self.mod_info:
            self.mod_loaded(self.mod_info)
        else:
            self.pick_mod()

    def reverse_slots(self):
        W.QMessageBox.information(self, 'Origen del intercambio', 'El origen corresponde a la malla del PAK importado. Para invertir el intercambio, importa el mod del otro traje; seleccionar una miniatura no proporciona sus archivos.')

    def update_summary(self):
        if not hasattr(self, 'review'):
            return
        if self.source:
            self.source_title.setText(Path(self.mod_info['path']).name if self.mod_info else self.source['name'])
            self.source_title.setToolTip(self.source_title.text())
            self.source_id.setText(self.source['character'] + ' · ' + self.source['name'])
            self.source_image.setPixmap(QtGui.QPixmap(self.source['image']).scaled(self.source_image.size(), QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation))
        self.review.setEnabled(bool(self.mod_info and self.target and self.source and self.source['skin_path'] != self.target['skin_path']))
        if not self.mod_info:
            self.status.setText(tr_text('Importa un mod PAK para continuar.'))
        elif self.category == 0:
            self.status.setText(tr_text('Elige un traje y exporta. El mod original se conserva.'))
        else:
            self.status.setText(tr_text('Intercambio entre personajes · Comprueba el resultado en el juego.'))

    def select_visible(self):
        for i in range(self.grid.count()):
            item = self.grid.item(i)
            item.setSelected(not item.isHidden())

    def enqueue(self):
        for item in self.grid.selectedItems():
            if not item.isHidden():
                record = item.data(QtCore.Qt.ItemDataRole.UserRole)
                self.queue[record['skin_path']] = record
        self.queue_button.setText(f'Cola · {len(self.queue)}')

    def show_queue(self):
        dialog = W.QDialog(self)
        dialog.setWindowTitle(tr_text('Cola de destinos — varios personajes'))
        dialog.resize(720, 510)
        layout = W.QVBoxLayout(dialog)
        rows = W.QListWidget()
        rows.setSelectionMode(W.QAbstractItemView.SelectionMode.ExtendedSelection)
        for path, record in self.queue.items():
            item = W.QListWidgetItem(f'{record["character"]} · {record["name"]} · {record["id"]}')
            item.setData(QtCore.Qt.ItemDataRole.UserRole, path)
            rows.addItem(item)
        layout.addWidget(rows)
        buttons = W.QHBoxLayout()
        remove = W.QPushButton(tr_text('Quitar seleccionados'))
        def remove_rows():
            for item in rows.selectedItems():
                self.queue.pop(item.data(QtCore.Qt.ItemDataRole.UserRole), None)
                rows.takeItem(rows.row(item))
            self.queue_button.setText(f'Cola · {len(self.queue)}')
        remove.clicked.connect(remove_rows)
        buttons.addWidget(remove)
        save_profile = W.QPushButton(tr_text('Guardar perfil'))
        def save_queue():
            path, _ = W.QFileDialog.getSaveFileName(dialog, tr_text('Guardar destinos'), 'destinos.json', 'JSON (*.json)')
            if path:
                try:
                    write_json(path, {'schema': 1, 'targets': list(self.queue)})
                except OSError as exc:
                    W.QMessageBox.warning(dialog, tr_text('Perfil'), str(exc))
        save_profile.clicked.connect(save_queue)
        buttons.addWidget(save_profile)
        load_profile = W.QPushButton(tr_text('Cargar perfil'))
        def load_queue():
            path, _ = W.QFileDialog.getOpenFileName(dialog, tr_text('Cargar destinos'), '', 'JSON (*.json)')
            if not path:
                return
            try:
                data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
                if not isinstance(data, dict) or data.get('schema') != 1 or not isinstance(data.get('targets'), list):
                    raise ValueError(tr_text('El archivo no es un perfil de destinos compatible.'))
                by_path = {r['skin_path']: r for r in self.records}
                missing = []
                for target in data['targets']:
                    if not isinstance(target, str) or target not in by_path:
                        missing.append(str(target))
                        continue
                    if self.source and ((by_path[target]['character'] != self.source['character']) == (self.category == 0)):
                        missing.append(target)
                        continue
                    self.queue[target] = by_path[target]
                self.queue_button.setText(f'Cola · {len(self.queue)}')
                if missing:
                    W.QMessageBox.information(dialog, tr_text('Destinos no disponibles'), f'{len(missing)} destinos no están en la biblioteca o pertenecen a otra categoría de intercambio.')
                dialog.accept()
                self.show_queue()
            except (OSError, ValueError) as exc:
                W.QMessageBox.warning(dialog, tr_text('Perfil'), str(exc))
        load_profile.clicked.connect(load_queue)
        buttons.addWidget(load_profile)
        export = W.QPushButton(tr_text('Revisar y exportar cola'))
        export.setEnabled(bool(self.queue and self.mod_info))
        export.clicked.connect(lambda: (dialog.accept(), self.export_records(list(self.queue.values()), batch=True)))
        buttons.addWidget(export)
        layout.addLayout(buttons)
        dialog.exec()

    def review_swap(self):
        if self.target:
            self.export_records([self.target])

    def export_records(self, records, batch=False):
        records = [dict(record) for record in records]
        if not self.mod_info or not records:
            return
        invalid = [r for r in records if (r['character'] != self.source['character']) == (self.category == 0)]
        if invalid:
            W.QMessageBox.warning(self, tr_text('Categoría de intercambio'), tr_text('La cola incluye destinos de otra categoría. Usa Trajes para el mismo personaje y Entre personajes para los demás.'))
            return
        records = [r for r in records if r['skin_path'] != self.source['skin_path']]
        if not records:
            W.QMessageBox.information(self, tr_text('Destinos'), tr_text('Todos los destinos coinciden con el origen.'))
            return
        cross = any(r['character'] != self.source['character'] for r in records)
        from ui.export_review import ExportReviewDialog
        dialog = ExportReviewDialog(self, records, cross)
        create_folder = dialog.create_folder
        folder_name = dialog.folder_name
        grouped = dialog.grouped
        if dialog.exec() != W.QDialog.DialogCode.Accepted:
            return
        directory = W.QFileDialog.getExistingDirectory(self, tr_text('Carpeta de salida'), self.preferences.get('outputRoot', ''))
        if not directory:
            return
        self.preferences['outputRoot'] = directory
        if create_folder.isChecked():
            from services.filename_service import sanitize_filename_component
            base = Path(directory) / sanitize_filename_component(folder_name.text() or 'Intercambios')
            candidate = base
            counter = 1
            while candidate.exists():
                candidate = base.with_name(base.name + f' {counter}')
                counter += 1
            directory = str(candidate)
        self.persist_preferences()
        mod, mesh = self.mod_info['path'], self.source_mesh
        grouped_value = grouped.isChecked()
        self.export_jobs.add(Path(mod).name, self.source.get('image',''), lambda cancel, progress: export_queue(mod, mesh, records, directory, grouped_value, cross, cancel, progress), records)
        self.tab_group.button(3).setChecked(True)
        self.change_tab(3)

    def export_finished(self, result):
        for row in result['completed']:
            self.queue.pop(row['target'], None)
        self.queue_button.setText(f'Cola · {len(self.queue)}')
        self.last_export_result = result
        english = self.preferences.get('language', 'es') == 'en'
        self.status.setText((f'{len(result["completed"])} exported · {len(result["failed"])} failed' if english else f'{len(result["completed"])} exportados · {len(result["failed"])} fallidos') + ((' · Cancelled' if english else ' · Cancelado') if result.get('cancelled') else ''))
        if result['failed']:
            W.QMessageBox.warning(self, tr_text('Exportación'), result['failed'][0].get('error', tr_text('Error al exportar')))

    def export_single(self, record):
        # All entry points use the same destination-folder review and queue.
        self.export_records([record], batch=True)

    def context_menu(self, position):
        item = self.grid.itemAt(position)
        if not item:
            return
        record = item.data(QtCore.Qt.ItemDataRole.UserRole)
        menu = W.QMenu(self)
        favorite = menu.addAction(tr_text('Quitar de favoritos') if record['skin_path'] in self.favorites else tr_text('Añadir a favoritos'))
        info = menu.addAction(tr_text('Ver ruta y detalles'))
        chosen = menu.exec(self.grid.viewport().mapToGlobal(position))
        if chosen == favorite:
            if record['skin_path'] in self.favorites:
                self.favorites.remove(record['skin_path'])
            else:
                self.favorites.add(record['skin_path'])
            self.preferences['favorites'] = sorted(self.favorites)
            self.persist_preferences()
            self.filter_records()
        elif chosen == info:
            self.show_report(tr_text('Detalles del traje'), record)

    def change_tab(self, index):
        self.tab_group.button(index).setChecked(True)
        if index == 3:
            self.export_jobs.refresh()
            self.pages.setCurrentWidget(self.export_jobs)
            return
        if index == 2:
            self.show_tools()
            return
        self.category = index
        self.apply_category()

    def show_report(self, title, data):
        dialog = W.QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(850, 600)
        layout = W.QVBoxLayout(dialog)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(16)
        heading = W.QLabel(title)
        heading.setObjectName('ShelfTitle')
        layout.addWidget(heading)
        tree = W.QTreeWidget()
        tree.setHeaderLabels([tr_text('Campo'), tr_text('Valor')])
        tree.setAlternatingRowColors(False)
        tree.setColumnWidth(0, 245)
        def add_rows(parent, value):
            pairs = value.items() if isinstance(value, dict) else enumerate(value)
            for key, child in pairs:
                container = isinstance(child, (dict, list))
                item = W.QTreeWidgetItem([tr_text(str(key)), str(len(child)) + (' items' if self.preferences.get('language') == 'en' else ' elementos') if container else str(child)])
                item.setToolTip(1, item.text(1))
                if isinstance(parent, W.QTreeWidget):
                    parent.addTopLevelItem(item)
                else:
                    parent.addChild(item)
                if container:
                    add_rows(item, child)
        add_rows(tree, data if isinstance(data, (dict, list)) else {'result': data})
        tree.expandToDepth(0)
        layout.addWidget(tree, 1)
        text = W.QPlainTextEdit()
        text.setReadOnly(True)
        text.setPlainText(json.dumps(data, ensure_ascii=False, indent=2))
        text.hide()
        layout.addWidget(text, 1)
        raw = W.QCheckBox(tr_text('Ver JSON'))
        raw.toggled.connect(text.setVisible)
        raw.toggled.connect(lambda checked: tree.setVisible(not checked))
        layout.addWidget(raw)
        buttons = W.QDialogButtonBox(W.QDialogButtonBox.StandardButton.Close)
        save = buttons.addButton(tr_text('Guardar informe JSON'), W.QDialogButtonBox.ButtonRole.ActionRole)
        def save_report():
            path, _ = W.QFileDialog.getSaveFileName(dialog, tr_text('Guardar informe'), 'informe.json', 'JSON (*.json)')
            if path:
                try:
                    write_json(path, data)
                except OSError as exc:
                    W.QMessageBox.warning(dialog, tr_text('Error al guardar'), str(exc))
        save.clicked.connect(save_report)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()

    def show_tools(self):
        if hasattr(self, 'tools_page'):
            self.pages.setCurrentWidget(self.tools_page)
            return
        self.tools_page = W.QWidget()
        dialog = self.tools_page
        layout = W.QVBoxLayout(dialog)
        title = W.QLabel('Tools' if self.preferences.get('language') == 'en' else 'Herramientas')
        title.setObjectName('ShelfTitle')
        layout.addWidget(title)
        subtitle = W.QLabel(tr_text('Todo lo que necesitas para preparar, revisar y organizar tus mods.'))
        subtitle.setObjectName('Muted')
        layout.addWidget(subtitle)
        body = W.QHBoxLayout()
        body.setSpacing(20)
        layout.addLayout(body, 1)
        self.tools_navigation = W.QListWidget()
        self.tools_navigation.setFixedWidth(180)
        self.tools_navigation.setSpacing(6)
        body.addWidget(self.tools_navigation)
        sections = W.QStackedWidget()
        body.addWidget(sections, 1)
        self.tools_navigation.currentRowChanged.connect(sections.setCurrentIndex)
        groups = []
        for name in (['Mods', 'Library', 'Settings'] if self.preferences.get('language') == 'en' else ['Mods', 'Biblioteca', 'Configuración']):
            item = W.QListWidgetItem(name)
            item.setSizeHint(QtCore.QSize(160, 52))
            self.tools_navigation.addItem(item)
            scroll = W.QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(W.QFrame.Shape.NoFrame)
            page = W.QWidget()
            group = W.QGridLayout(page)
            group.setSpacing(14)
            group.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
            scroll.setWidget(page)
            sections.addWidget(scroll)
            groups.append(group)
        self.tools_navigation.setCurrentRow(0)
        counts = [0,0,0]
        actions = [
            (tr_text('Inspeccionar PAK'), tr_text('Archivos, personajes, mallas y archivos huérfanos'), self.tool_inspect),
            (tr_text('Detectar conflictos'), tr_text('Rutas compartidas entre varios mods'), self.tool_conflicts),
            (tr_text('Extraer PAK'), tr_text('Carpeta nueva; conserva el original'), self.tool_extract),
            (tr_text('Empaquetar carpeta'), tr_text('Crear PAK con verificación de contenido'), self.tool_pack),
            (tr_text('Indexar FModel'), tr_text('Inventario de mallas y archivos asociados'), self.tool_fmodel),
            (tr_text('Referencias de asset'), tr_text('Materiales, esqueleto y física desde JSON'), self.tool_asset),
            (tr_text('Historial'), tr_text('Resultados y errores de exportación'), lambda: self.show_report(tr_text('Historial'), read_history())),
            (tr_text('Diagnóstico'), tr_text('Herramientas y biblioteca local'), self.tool_diagnostics),
            (tr_text('Ajustes'), tr_text('Idioma, apariencia y rutas del juego'), self.tool_settings),
            (tr_text('Actualizar catálogo'), tr_text('Solo novedades y archivos que necesitan reparación'), self.tool_catalog),
            (tr_text('Preparar biblioteca'), tr_text('Extracción original del juego y miniaturas'), self.tool_prepare),
            (tr_text('Recargar biblioteca'), tr_text('Releer catálogo y rutas PA'), self.reload_library),
            ('Actualizaciones · GitHub' if self.preferences.get('language') != 'en' else 'Updates · GitHub', 'OutfitFlux '+__import__('util').APP_VERSION, self.show_updates),
        ]
        for index, (title, description, function) in enumerate(actions):
            button = W.QPushButton()
            card_layout = W.QVBoxLayout(button)
            card_layout.setContentsMargins(18, 16, 18, 16)
            card_title = W.QLabel(title + '  →')
            card_title.setObjectName('SelectionName')
            card_description = W.QLabel(description)
            card_description.setObjectName('Muted')
            card_description.setWordWrap(True)
            for label in (card_title, card_description):
                label.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
                card_layout.addWidget(label)
            button.setAccessibleName(title)
            button.setToolTip(description)
            button.setMinimumHeight(66)
            button.clicked.connect(lambda checked=False, fn=function: fn())
            button.setObjectName('ToolCard')
            section = 0 if index in (0,1,2,3,5,6) else (1 if index in (4,9,10,11) else 2)
            position = counts[section]
            button.setMinimumHeight(100)
            groups[section].addWidget(button,position // 2,position % 2)
            counts[section] += 1
        self.pages.addWidget(self.tools_page)
        self.pages.setCurrentWidget(self.tools_page)

    def tool_inspect(self):
        path, _ = W.QFileDialog.getOpenFileName(self, tr_text('Inspeccionar PAK'), '', 'PAK (*.pak)')
        if path:
            self.start_task(tr_text('Inspeccionando…'), lambda c, p: inspect_pak(path, c), lambda result: self.show_report('Inspector PAK', result))

    def tool_conflicts(self):
        paths, _ = W.QFileDialog.getOpenFileNames(self, tr_text('Selecciona dos o más mods'), '', 'PAK (*.pak)')
        if len(paths) > 1:
            self.start_task(tr_text('Comparando rutas…'), lambda c, p: compare_paks(paths, c), lambda result: self.show_report(tr_text('Conflictos de rutas (no compara contenido)'), result))

    def tool_extract(self):
        path, _ = W.QFileDialog.getOpenFileName(self, tr_text('Extraer PAK'), '', 'PAK (*.pak)')
        if not path:
            return
        parent = W.QFileDialog.getExistingDirectory(self, tr_text('Carpeta donde crear la extracción'))
        if not parent:
            return
        import uuid
        output = Path(parent) / (Path(path).stem + '-' + uuid.uuid4().hex[:8])
        def extract(cancel, progress):
            entries = extract_pak(path, output, cancel)
            return {'folder': str(output), 'files': len(entries)}
        self.start_task(tr_text('Extrayendo…'), extract, lambda result: self.show_report(tr_text('Extracción terminada'), result))

    def tool_pack(self):
        folder = W.QFileDialog.getExistingDirectory(self, tr_text('Carpeta que contiene HerovsGame'))
        if not folder:
            return
        if not (Path(folder) / 'HerovsGame').is_dir():
            W.QMessageBox.warning(self, tr_text('Estructura del mod'), tr_text('Selecciona una carpeta que contenga HerovsGame/Content.'))
            return
        path, _ = W.QFileDialog.getSaveFileName(self, tr_text('Nuevo PAK (no se sobrescriben archivos)'), 'Mod_P.pak', 'PAK (*.pak)')
        if path:
            output = normalize_export_path(path)
            self.start_task(tr_text('Empaquetando…'), lambda c, p: create_final_pak(output, c, folder), lambda result: self.show_report(tr_text('PAK verificado'), {'path': result}))

    def tool_fmodel(self):
        default = self.preferences.get('fmodelRoot', str(Path.home() / 'Documents'))
        folder = W.QFileDialog.getExistingDirectory(self, tr_text('Carpeta Character de FModel'), default)
        if folder:
            self.preferences['fmodelRoot'] = folder
            self.persist_preferences()
            self.start_task(tr_text('Indexando FModel…'), lambda c, p: index_fmodel(folder, c, p), lambda result: self.show_report(tr_text('Inventario FModel'), result))

    def tool_asset(self):
        path, _ = W.QFileDialog.getOpenFileName(self, tr_text('Asset exportado como JSON'), '', 'JSON (*.json)')
        if path:
            self.start_task(tr_text('Leyendo referencias…'), lambda c, p: inspect_asset_json(path), lambda result: self.show_report(tr_text('Referencias declaradas'), result))

    def tool_diagnostics(self):
        from services.game_service import validate_dependency_paths, check_dotnet_runtime
        self.start_task(tr_text('Comprobando herramientas…'), lambda c, p: {'missing': validate_dependency_paths(), 'dotnet8': check_dotnet_runtime(), 'library_records': len(self.records), 'library_warnings': self.library_warnings, 'paths': {'UnrealPak': unrealPak, 'repak': repakPath, 'UEJSON': uejsonPath, 'Character': CHARACTER_DIR}}, lambda result: self.show_report(tr_text('Diagnóstico'), result))

    def show_updates(self):
        if not hasattr(self,'updates_page'):
            from ui.updates_page import UpdatesPage
            self.updates_page=UpdatesPage(self)
            self.pages.addWidget(self.updates_page)
        self.updates_page.translate()
        self.tab_group.button(2).setChecked(True)
        self.pages.setCurrentWidget(self.updates_page)

    def tool_settings(self):
        from ui.outfit_setup import SetupDialog
        if SetupDialog(self).exec() == W.QDialog.DialogCode.Accepted:
            self.refresh_preferences()

    def refresh_preferences(self):
        self.preferences = load_config()
        self.accent_combo.blockSignals(True)
        self.accent_combo.setCurrentIndex(max(0, self.accent_combo.findData(self.preferences.get('accentColor','#0a84ff'))))
        self.accent_combo.blockSignals(False)
        self.language_combo.blockSignals(True)
        self.language_combo.setCurrentIndex(0 if self.preferences.get('language','es') == 'es' else 1)
        self.language_combo.blockSignals(False)
        self.set_theme(self.preferences.get('studioTheme','dark') == 'dark')
        self.change_language()

    def restart_app(self):
        # SettingsDialog compatibility; does not replace widgets with active workers.
        self.reload_library()

    def reload_library(self):
        if self.worker:
            return
        self.load_records()
        self._items_ready = False
        self.apply_category()

    def tool_catalog(self):
        from services.catalog_web_service import merge_web_catalog_into_local
        from services.skin_id_map_service import rebuild_skin_id_map_file, load_skin_id_map
        before = {r['skin_path'] for r in self.records}
        def refresh(cancel, progress):
            from services.incremental_service import refresh_assets
            config = load_config()
            assets_result = {}
            if Path(config.get('gamePakPath','')).is_file():
                assets_result = refresh_assets(config['aesKey'], config['gamePakPath'], cancel, progress)
            from services.process_service import raise_if_cancelled
            rebuild_skin_id_map_file()
            mapping = load_skin_id_map()
            result = {'assets': assets_result}
            for index, language in enumerate(['en', 'es']):
                raise_if_cancelled(cancel)
                progress(index, 2, f'Catalog: {language}' if config.get('language') == 'en' else f'Catálogo: {language}')
                result[language] = merge_web_catalog_into_local(language, mapping)
            return result
        def finished(result):
            self.reload_library()
            added = [r['name'] for r in self.records if r['skin_path'] not in before]
            en = self.preferences.get('language') == 'en'
            assets = result.get('assets', {})
            summary = (f'{len(added)} new costumes\n' if en else f'{len(added)} nuevos trajes\n')
            summary += (f"Converted: {assets.get('converted', 0)} · Reused: {assets.get('reused', 0)}\n" if en else f"Convertidos: {assets.get('converted', 0)} · Reutilizados: {assets.get('reused', 0)}\n")
            summary += '\n'.join(added[:25])
            if len(added)>25:summary += f'\n+{len(added)-25}'
            if assets.get('warnings'):summary += '\n' + ('Warnings: ' if en else 'Avisos: ') + str(len(assets['warnings'])) + '\n' + assets['warnings'][0]
            W.QMessageBox.information(self, 'Catalog' if en else 'Catálogo', summary)

        self.start_task(tr_text('Actualizando catálogo…'), refresh, finished)

    def tool_prepare(self):
        from services.game_service import prepare_game_assets, validate_game_path
        config = load_config()
        if not validate_game_path(config.get('gamePakPath')):
            W.QMessageBox.warning(self, tr_text('PAK del juego'), tr_text('Configura primero una ruta válida en Ajustes.'))
            return
        self.start_task(tr_text('Preparando biblioteca…'), lambda c, p: prepare_game_assets(config['aesKey'], config['gamePakPath'], progress_callback=p, is_cancelled_callback=c), lambda result: (self.reload_library(), self.show_report(tr_text('Biblioteca preparada'), result)))

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and any(url.toLocalFile().lower().endswith('.pak') for url in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            if url.toLocalFile().lower().endswith('.pak'):
                self.import_mod(url.toLocalFile())
                event.acceptProposedAction()
                break
