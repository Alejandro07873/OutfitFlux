import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from services import catalog_service, config_service
from services.filename_service import build_output_filename, sanitize_filename_component
from services.process_service import run_hidden_command, ExportCancelled
from services.pak_service import validate_entry, list_pak, extract_pak, compare_paks
from services.safe_export_service import patch_mesh_json, validate_target, create_final_pak, export_mod_to_skin
from services.studio_service import export_queue, inspect_asset_json


class RegressionTests(unittest.TestCase):
    def test_batch_keeps_chosen_destination_with_absolute_source(self):
        from services.studio_service import _export_queue
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'imports' / 'Mod(Author)_P.pak'
            destination = root / 'chosen-output'
            records = [dict(character='Ch001', name=name, skin_path=name)
                       for name in ('First', 'Second')]
            for grouped in (False, True):
                with self.subTest(grouped=grouped), \
                     patch('services.studio_service.export_mod_to_skin', side_effect=lambda mod, skin, output, *a, **k: output), \
                     patch('services.studio_service.save_history'):
                    result = _export_queue(str(source), 'mesh', records, str(destination), grouped, False, None, None, 'extracted')
                self.assertEqual(len(result['completed']), 2)
                self.assertFalse(result['failed'])
                expected = destination / 'Ch001' if grouped else destination
                for entry in result['completed']:
                    self.assertEqual(Path(entry['output']).parent, expected)
                    self.assertNotEqual(Path(entry['output']).parent, source.parent)

    def test_legacy_text_catalog(self):
        with patch.object(catalog_service, 'load_config', return_value={'language': 'es'}), patch.object(catalog_service, 'get_character_catalog', return_value={'old': 'Legacy'}):
            result = catalog_service.get_skin_display_data('Ch001', 'missing', '123')
        self.assertEqual(result['internal_name'], 'missing')

    def test_unknown_source_keeps_skin_group(self):
        self.assertEqual(build_output_filename('Mod(Skin)(Author).pak', 'Target'), 'Mod(Skin)(Target)(Author).pak')

    def test_reexport_removes_all_previous_costumes_in_both_languages(self):
        names = ['Cyber Hero Costume', 'Hero Costume Camouflage ver.', 'Traje de héroe', 'Traje de héroe dañado']
        for previous in ['(Cyber Hero Costume)', '(Cyber Hero Costume)(Hero Costume Camouflage ver)',
                         '(Traje de héroe)(Cyber Hero Costume)(Traje de héroe dañado)']:
            with self.subTest(previous=previous):
                result = build_output_filename('XMegamanDestroit' + previous + '(Aweeoppoe)-WindowsNoEditor_P.pak',
                                               'Hero Costume Damaged ver', known_skin_names=names)
                self.assertEqual(result, 'XMegamanDestroit(Hero Costume Damaged ver)(Aweeoppoe)-WindowsNoEditor_P.pak')

    def test_costume_cleanup_preserves_author_tags_counter_and_directory(self):
        source = str(Path('imports') / 'Mod(HD)(Cyber Hero Costume)(Author)-WindowsNoEditor_P(2).pak')
        result = build_output_filename(source, 'Traje de héroe', known_skin_names=['Cyber Hero Costume'])
        self.assertEqual(result, str(Path('imports') / 'Mod(HD)(Traje de héroe)(Author)-WindowsNoEditor_P(2).pak'))
        # Even an author name that coincides with a costume must be preserved.
        self.assertEqual(build_output_filename('Mod(Cyber Hero Costume)(Hero Costume).pak', 'Casual',
                                              known_skin_names=['Cyber Hero Costume', 'Hero Costume']),
                         'Mod(Casual)(Hero Costume).pak')

    def test_nested_costume_parentheses_and_target_deduplication(self):
        original = 'Mod(Hero Costume (Damaged ver.))(Casual)(Author)_P.pak'
        result = build_output_filename(original, 'Casual', known_skin_names=['Hero Costume Damaged ver.'])
        self.assertEqual(result, 'Mod(Casual)(Author)_P.pak')
        self.assertEqual(build_output_filename(result, 'Casual'), result)

    def test_filename_names_include_spanish_english_and_aliases(self):
        from services.catalog_service import costume_filename_names
        with patch.object(catalog_service, 'load_catalog', return_value={'Ch001': {'SK_Test': {
            'display_name': 'Hero Costume', 'display_name_es': 'Traje de héroe', 'aliases': ['Old hero name']}}}):
            self.assertTrue({'SK_Test','Hero Costume','Traje de héroe','Old hero name'} <= costume_filename_names())

    def test_windows_filenames(self):
        self.assertEqual(sanitize_filename_component('CON'), '_CON')
        self.assertEqual(sanitize_filename_component('hello. '), 'hello')

    def test_invalid_config_is_backed_up(self):
        with tempfile.TemporaryDirectory() as t:
            file = Path(t) / 'config.json'
            file.write_text('[]', encoding='utf-8')
            with patch.object(config_service, 'CONFIG_FILE', str(file)), patch.object(config_service, 'CONFIG_DIR', t):
                result = config_service.load_config()
            self.assertIn('gamePakPath', result)
            self.assertEqual(len(list(Path(t).glob('*.bak'))), 1)

    def test_process_large_output_no_deadlock(self):
        result = run_hidden_command([sys.executable, '-c', "import sys; sys.stdout.write('x'*200000); sys.stderr.write('y'*200000)"], timeout=10)
        self.assertEqual(len(result['stdout']), 200000)
        self.assertEqual(len(result['stderr']), 200000)

    def test_process_timeout(self):
        with self.assertRaises(TimeoutError):
            run_hidden_command([sys.executable, '-c', 'import time; time.sleep(20)'], timeout=.1)

    def test_process_cancellation(self):
        started = time.monotonic()
        with self.assertRaises(ExportCancelled):
            run_hidden_command([sys.executable, '-c', 'import time; time.sleep(20)'], lambda: time.monotonic() - started > .1)

    def test_unsafe_paths(self):
        for path in ['../escape', '/absolute', 'C:/escape', 'a/../../escape']:
            with self.subTest(path=path), self.assertRaises(ValueError):
                validate_entry(path)
        with self.assertRaises(ValueError):
            validate_target('Ch001/../../evil')

    def test_exact_references_only(self):
        with tempfile.TemporaryDirectory() as t:
            file = Path(t) / 'mesh.json'
            old = 'SK_Ch001_Default_00'
            target = 'Ch001/Model/Fm/A1/Mesh/SK_Ch001_FmA1_00'
            file.write_text(json.dumps({'NameMap': [old, 'Prefix_' + old, '/Game/Character/Ch001/Model/Default/Mesh/' + old + '.' + old, old + '_Clothing_0'], 'Exports': [{'ObjectName': old}, {'ObjectName': old + '_Clothing_0'}]}), encoding='utf-8')
            patch_mesh_json(file, old + '.uasset', target)
            data = json.loads(file.read_text(encoding='utf-8'))
            self.assertEqual(data['NameMap'][1], 'Prefix_' + old)
            self.assertEqual(data['Exports'][1]['ObjectName'], old + '_Clothing_0')
            self.assertEqual(data['NameMap'][2], '/Game/Character/' + target + '.SK_Ch001_FmA1_00')

    def test_unknown_mesh_rejected_without_write(self):
        with tempfile.TemporaryDirectory() as t:
            file = Path(t) / 'mesh.json'
            file.write_text('{"NameMap":[],"Exports":[]}', encoding='utf-8')
            original = file.read_bytes()
            with self.assertRaises(ValueError):
                patch_mesh_json(file, 'SK_unknown.uasset', 'Ch001/Model/Default/Mesh/SK_Ch001_Default_00')
            self.assertEqual(original, file.read_bytes())

    def test_inspector_handles_fmodel_list(self):
        with tempfile.TemporaryDirectory() as t:
            file = Path(t) / 'asset.json'
            file.write_text(json.dumps([{'ref': '/Game/Character/Skeleton', 'mat': '/Game/Character/Mat/M'}]))
            result = inspect_asset_json(file)
            self.assertEqual(len(result['references']), 2)
            self.assertEqual(len(result['materials']), 1)


class PakIntegrationTests(unittest.TestCase):
    def test_pack_list_extract_and_conflicts(self):
        from util import repakPath, unrealPak
        if not all(Path(path).is_file() for path in (repakPath, unrealPak)):
            self.skipTest('Requires local repak and UnrealPak tools')
        with tempfile.TemporaryDirectory(prefix='aurora-test-') as t:
            root = Path(t)
            content = root / 'source' / 'HerovsGame/Content/Test'
            content.mkdir(parents=True)
            (content / 'sample.bin').write_bytes(b'content' * 30000)
            output = create_final_pak(root / 'test_P.pak', workspace=root / 'source')
            self.assertEqual(list_pak(output), ['HerovsGame/Content/Test/sample.bin'])
            extract_pak(output, root / 'extracted')
            self.assertEqual((root/'extracted/HerovsGame/Content/Test/sample.bin').read_bytes(), (content/'sample.bin').read_bytes())
            self.assertEqual(len(compare_paks([output, output])), 1)
            before = Path(output).read_bytes()
            with self.assertRaises(FileExistsError):
                create_final_pak(output, workspace=root / 'source')
            self.assertEqual(before, Path(output).read_bytes())

    def test_output_inside_source_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ValueError):
                create_final_pak(Path(t)/'bad_P.pak', workspace=t)

    def test_cancel_leaves_no_pak(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t); source = root/'source'; source.mkdir(); (source/'a').write_text('test')
            with self.assertRaises(ExportCancelled):
                create_final_pak(root/'out_P.pak', lambda: True, source)
            self.assertFalse((root/'out_P.pak').exists())
            self.assertFalse(list(root.glob('.aurora-*')))

    def test_real_asset_roundtrip_and_batch(self):
        sample = Path(os.environ.get('AURORA_TEST_MESH', 'missing-test-fixture'))
        if not sample.is_file():
            self.skipTest('Set AURORA_TEST_MESH to an exported SK uasset for real conversion')
        with tempfile.TemporaryDirectory(prefix='aurora-asset-test-') as t:
            root = Path(t)
            directory = root/'source/HerovsGame/Content/Character/Ch001/Model/Default/Mesh'
            directory.mkdir(parents=True)
            for suffix in ['.uasset', '.uexp', '.ubulk']:
                shutil.copy2(sample.with_suffix(suffix), directory/sample.with_suffix(suffix).name)
            original = create_final_pak(root/'original_P.pak', workspace=root/'source')
            digest = hashlib.sha256(Path(original).read_bytes()).hexdigest()
            same = {'name': 'Casual', 'character': 'Ch001', 'skin_path': 'Ch001/Model/Fm/A1/Mesh/SK_Ch001_FmA1_00'}
            cross = {'name': 'Other', 'character': 'Ch002', 'skin_path': 'Ch002/Model/Default/Mesh/SK_Ch002_Default_00'}
            with self.assertRaises(ValueError):
                export_mod_to_skin(original, cross['skin_path'], root/'blocked_P.pak')
            with patch('services.studio_service.save_history'):
                result = export_queue(original, None, [same, cross], root/'outputs', grouped=False, cross=True)
            self.assertEqual(result['failed'], [])
            self.assertEqual(len(result['completed']), 2)
            for row in result['completed']:
                self.assertEqual(Path(row['output']).parent, root/'outputs')
                self.assertEqual(len(list_pak(row['output'])), 3)
                self.assertIn('Character/' + row['target'] + '.ubulk', '\n'.join(list_pak(row['output'])))
            self.assertEqual(hashlib.sha256(Path(original).read_bytes()).hexdigest(), digest)
            self.assertFalse((root/'blocked_P.pak').exists())
            with self.assertRaises(ValueError):
                export_mod_to_skin(original, same['skin_path'], original)


if __name__ == '__main__':
    unittest.main()
