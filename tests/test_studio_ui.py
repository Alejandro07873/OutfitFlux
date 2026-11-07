import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import time
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from PySide6 import QtWidgets, QtCore
from ui.studio_window import StudioWindow


class StudioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        # Use an ordinary descriptor: Qt introspects Python class attributes when
        # connecting slots; MagicMock descriptors can crash PySide's metatype walk.
        self.persistence = patch.object(StudioWindow, 'persist_preferences', lambda self: None)
        self.persistence.start()
        self.window = StudioWindow()
        self.window.show()
        self.app.processEvents()

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()
        self.persistence.stop()

    def test_initial_state_does_not_imply_loaded_mod(self):
        self.assertIsNone(self.window.source)
        self.assertIsNone(self.window.target)
        self.assertFalse(self.window.review.isEnabled())
        self.assertIs(self.window.pages.currentWidget(), self.window.home)
        self.assertFalse(self.window.grid.isVisible())

    def import_fixture(self):
        window = self.window
        if not window.records:
            self.skipTest('Requires a prepared local library')
        record = window.records[0]
        mesh = 'HerovsGame/Content/Character/' + record['skin_path'] + '.uasset'
        window.mod_loaded({'path': 'example.pak', 'entries': [mesh], 'meshes': [mesh]})
        self.app.processEvents()
        return record

    def test_filter_preserves_items_and_queue(self):
        window = self.window
        self.import_fixture()
        if not window.records:
            self.skipTest('Requires a prepared local library')
        first = window.grid.item(0)
        window.select_visible()
        window.enqueue()
        queued = len(window.queue)
        window.search.setText('impossible-query-9999')
        window.filter_records()
        self.assertTrue(all(window.grid.item(i).isHidden() for i in range(window.grid.count())))
        window.set_target()
        self.assertIsNone(window.target)
        window.search.clear()
        window.filter_records()
        self.assertIs(first, window.grid.item(0))
        self.assertEqual(queued, len(window.queue))

    def test_theme_switch_keeps_selection(self):
        window = self.window
        window.set_target()
        target = window.target
        window.set_theme(False)
        self.assertFalse(window.dark)
        window.set_theme(True)
        self.assertTrue(window.dark)
        self.assertEqual(target, window.target)

    def test_queue_is_immediately_right_of_costumes(self):
        layout = self.window.tabs.layout()
        self.assertEqual([self.window.tab_group.id(layout.itemAt(i).widget()) for i in range(layout.count())], [0, 3, 1, 2])

    def test_settings_apply_appearance_immediately_without_saving_paths(self):
        from ui.outfit_setup import SetupDialog
        from services.config_service import save_config, load_config
        with tempfile.TemporaryDirectory() as folder, \
             patch('services.config_service.CONFIG_DIR', folder), \
             patch('services.config_service.CONFIG_FILE', str(Path(folder) / 'config.json')):
            save_config({'language': 'es', 'studioTheme': 'white', 'accentColor': '#0a84ff', 'gamePakPath': 'original.pak'})
            self.window.refresh_preferences()
            dialog = SetupDialog(self.window)
            dialog.path.setText('unsaved.pak')
            dialog.theme.setCurrentIndex(0)
            self.assertTrue(self.window.dark)
            dialog.color.setCurrentIndex(1)
            self.assertEqual(self.window.theme_colors['primary'], '#8b5cf6')
            dialog.language.setCurrentIndex(1)
            self.assertEqual(self.window.tab_group.button(0).text(), 'Costumes')
            self.assertEqual(load_config()['language'], 'en')
            self.assertEqual(load_config()['gamePakPath'], 'original.pak')
            dialog.reject()
            self.assertEqual(load_config()['studioTheme'], 'dark')
            dialog.deleteLater()

    def test_initial_settings_only_claimed_once_across_builds(self):
        from ui.outfit_setup import claim_initial_setup
        from services.config_service import save_config
        class MemorySettings:
            seen = False
            def value(self, *args, **kwargs): return self.seen
            def setValue(self, key, value): self.seen = value
            def sync(self): pass
        settings = MemorySettings()
        with tempfile.TemporaryDirectory() as folder, \
             patch('services.config_service.CONFIG_DIR', folder), \
             patch('services.config_service.CONFIG_FILE', str(Path(folder) / 'config.json')), \
             patch('ui.outfit_setup.QtCore.QSettings', return_value=settings):
            self.assertTrue(claim_initial_setup())
            self.assertFalse(claim_initial_setup())
            save_config({'outfitFluxSetup': False})
            self.assertFalse(claim_initial_setup())

    def test_batch_uses_every_selected_destination(self):
        self.import_fixture()
        window = self.window
        window.select_visible()
        expected = {r['skin_path'] for r in window.selected_records()}
        self.assertGreater(len(expected), 1)
        captured = []
        window.export_records = lambda records, batch=False: captured.append((records, batch))
        window.batch_button.click()
        self.assertEqual({r['skin_path'] for r in captured[0][0]}, expected)
        self.assertTrue(captured[0][1])
        self.assertNotIn(window.source['skin_path'], expected)

    def test_language_change_preserves_batch_selection(self):
        self.import_fixture()
        window = self.window
        window.select_visible()
        expected = {r['skin_path'] for r in window.selected_records()}
        with patch('ui.studio_window.save_config'):
            window.language_combo.setCurrentIndex(1 - window.language_combo.currentIndex())
        self.assertEqual({r['skin_path'] for r in window.selected_records()}, expected)

    def test_worker_lifetime_and_completion(self):
        results = []
        self.window.start_task('Test', lambda c, p: {'ok': True}, results.append)
        deadline = time.monotonic() + 5
        while self.window.worker is not None and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.01)
        self.assertIsNone(self.window.worker)
        self.assertEqual(results, [{'ok': True}])

    def test_export_queue_accepts_second_job_while_import_state_changes(self):
        import threading
        release = threading.Event()
        order = []
        def first(cancel, progress):
            release.wait(2)
            order.append('first')
            return {'completed': [{'target': 'first'}], 'failed': []}
        def second(cancel, progress):
            order.append('second')
            return {'completed': [{'target': 'second'}], 'failed': []}
        queue = self.window.export_jobs
        queue.add('First mod', '', first, ['First target'])
        queue.add('Second mod', '', second, ['Second target'])
        self.import_fixture()
        self.assertIsNone(self.window.worker)
        self.assertEqual(queue.jobs[1]['status'], 'waiting')
        release.set()
        deadline = time.monotonic() + 5
        while any(j['status'] in ('waiting', 'running') for j in queue.jobs) and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.01)
        self.assertEqual(order, ['first', 'second'])
        self.assertTrue(all(j['status'] == 'done' for j in queue.jobs))

    def test_queue_tracks_each_costume_independently(self):
        queue = self.window.export_jobs
        records = [dict(name='First', skin_path='first', image=''), dict(name='Second', skin_path='second', image='')]
        with patch.object(queue, 'start_next'):
            queue.add('Mod', '', lambda c, p: None, records)
        job = queue.jobs[0]
        queue.progress(job, 0, 2, 'outfitflux-target:{"index":0,"step":4,"state":"packing"}')
        self.assertEqual(job['targets'][0]['bar'].value(), 4)
        self.assertEqual(job['targets'][1]['state'], 'waiting')
        queue.progress(job, 0, 2, 'outfitflux-target:{"index":0,"step":5,"state":"done"}')
        self.assertEqual(job['targets'][0]['state'], 'done')
        self.assertEqual(job['targets'][1]['bar'].value(), 0)
        queue.cancel(job)
        self.assertEqual(job['targets'][1]['state'], 'cancelled')

    def test_tools_categories_follow_live_language(self):
        self.window.change_tab(2)
        self.window.preferences['language'] = 'en'
        self.window.apply_language()
        self.assertEqual(self.window.tools_navigation.item(1).text(), 'Library')
        self.window.preferences['language'] = 'es'
        self.window.apply_language()
        self.assertEqual(self.window.tools_navigation.item(1).text(), 'Biblioteca')

    def test_import_identity_is_not_target(self):
        window = self.window
        if not window.records:
            self.skipTest('Requires a prepared local library')
        record = window.records[0]
        mesh = 'HerovsGame/Content/Character/' + record['skin_path'] + '.uasset'
        window.mod_loaded({'path': 'example.pak', 'entries': [mesh], 'meshes': [mesh]})
        original = window.source
        if window.grid.count() > 1:
            window.grid.setCurrentRow(1)
            window.set_target()
        self.assertEqual(window.source, original)
        self.assertEqual(window.source_mesh, mesh)

    def test_import_shows_only_source_character(self):
        record = self.import_fixture()
        window = self.window
        visible = [window.grid.item(i).data(QtCore.Qt.ItemDataRole.UserRole) for i in range(window.grid.count()) if not window.grid.item(i).isHidden()]
        self.assertTrue(visible)
        self.assertEqual({r['character'] for r in visible}, {record['character']})
        self.assertFalse(window.character.isVisible())
        self.assertIs(window.pages.currentWidget(), window.workspace)

    def test_cross_character_is_separate_category_and_queue(self):
        record = self.import_fixture()
        window = self.window
        window.select_visible(); window.enqueue()
        normal_queue = dict(window.queue)
        window.change_tab(1)
        self.assertEqual(window.queue, {})
        self.assertTrue(window.character_gallery.isVisible())
        self.assertFalse(window.character.isVisible())
        self.assertTrue(all(window.grid.item(i).isHidden() for i in range(window.grid.count())))
        self.assertEqual(window.character.findData(record['character']), -1)
        if window.character.count() > 1:
            window.character.setCurrentIndex(1)
            visible = [window.grid.item(i).data(QtCore.Qt.ItemDataRole.UserRole) for i in range(window.grid.count()) if not window.grid.item(i).isHidden()]
            self.assertTrue(visible)
            self.assertNotIn(record['character'], {r['character'] for r in visible})
        window.change_tab(0)
        self.assertEqual(window.queue, normal_queue)

    def test_compact_layout_does_not_overlap(self):
        self.import_fixture()
        for width, height in [(1366, 705), (1024, 600), (1000, 540)]:
            with self.subTest(size=(width, height)):
                self.window.resize(width, height)
                self.app.processEvents()
                stage = self.window.stage
                grid = self.window.grid
                grid_right = grid.mapTo(self.window.workspace, grid.rect().topRight()).x()
                self.assertLess(grid_right, stage.x())
                self.assertTrue(self.window.dock.isHidden())
                self.assertGreaterEqual(grid.height(), height - 250)
                self.assertGreaterEqual(grid.width(), 580)
                self.assertTrue(self.window.batch_button.isVisible())
                self.assertTrue(self.window.catalog_shortcut.isVisible())

    def test_pak_import_worker_enters_scoped_screen(self):
        from services.safe_export_service import create_final_pak
        if not self.window.records:
            self.skipTest('Requires a prepared local library')
        record = self.window.records[0]
        with tempfile.TemporaryDirectory(prefix='aurora-import-test-') as directory:
            root = Path(directory)
            entry = root / 'content/HerovsGame/Content/Character' / (record['skin_path'] + '.uasset')
            entry.parent.mkdir(parents=True)
            entry.write_bytes(b'inspection-only fixture')
            pak = create_final_pak(root / 'fixture_P.pak', workspace=root / 'content')
            self.window.import_mod(pak)
            deadline = time.monotonic() + 10
            while self.window.worker is not None and time.monotonic() < deadline:
                self.app.processEvents()
                time.sleep(.01)
            self.assertIsNone(self.window.worker)
            self.assertEqual(self.window.source['character'], record['character'])
            self.assertIs(self.window.pages.currentWidget(), self.window.workspace)
            visible = [self.window.grid.item(i).data(QtCore.Qt.ItemDataRole.UserRole) for i in range(self.window.grid.count()) if not self.window.grid.item(i).isHidden()]
            self.assertEqual({r['character'] for r in visible}, {record['character']})


if __name__ == '__main__':
    unittest.main()
