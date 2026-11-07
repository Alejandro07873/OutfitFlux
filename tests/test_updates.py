import hashlib
import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from services.update_service import repository,version,validated_entries,install_update

class UpdateTests(unittest.TestCase):
    def test_repository_and_version(self):
        self.assertEqual(repository('https://github.com/example/OutfitFlux/'),'example/OutfitFlux')
        self.assertGreater(version('v1.10.0'),version('1.9.0'))
        for invalid in ['https://evil.test/u/r','../repo','owner/repo/path','']:
            with self.assertRaises(ValueError):repository(invalid)
    def zip(self,extra=None):
        data=io.BytesIO()
        with zipfile.ZipFile(data,'w') as z:
            z.writestr('OutfitFlux/OutfitFlux.exe',b'MZfixture')
            z.writestr('OutfitFlux/_internal/runtime.dll',b'runtime')
            if extra:z.writestr(extra,b'bad')
        return data.getvalue()
    def test_rejects_traversal_and_user_data(self):
        for entry in ['OutfitFlux/../../outside','/absolute','OutfitFlux/assets/config/config.json','OutfitFlux/C:bad','OutfitFlux/outfitflux.exe']:
            with zipfile.ZipFile(io.BytesIO(self.zip(entry))) as z:
                with self.assertRaises(ValueError):validated_entries(z)
    def release(self,data):
        return dict(repo='example/OutfitFlux',version='v99.0.0',asset=dict(name='OutfitFlux-windows-x64.zip',browser_download_url='https://github.com/example/OutfitFlux/releases/download/v99.0.0/OutfitFlux-windows-x64.zip',size=len(data),digest='sha256:'+hashlib.sha256(data).hexdigest()))
    def test_install_preserves_settings_and_old_version(self):
        data=self.zip()
        with tempfile.TemporaryDirectory() as temp:
            current=Path(temp)/'current';(current/'assets/config').mkdir(parents=True)
            (current/'assets/config/config.json').write_text('{"language":"es"}')
            (current/'OutfitFlux.exe').write_bytes(b'MZold')
            with patch('services.update_service.urllib.request.urlopen',return_value=io.BytesIO(data)):
                installed=Path(install_update(self.release(data),workspace=current))
            self.assertTrue(installed.is_file())
            self.assertEqual((installed.parent/'assets/config/config.json').read_text(),'{"language":"es"}')
            self.assertEqual((current/'OutfitFlux.exe').read_bytes(),b'MZold')
    def test_hash_mismatch_does_not_publish(self):
        data=self.zip();release=self.release(data);release['asset']['digest']='sha256:'+'0'*64
        with tempfile.TemporaryDirectory() as temp:
            current=Path(temp)/'current';current.mkdir()
            with patch('services.update_service.urllib.request.urlopen',return_value=io.BytesIO(data)):
                with self.assertRaises(ValueError):install_update(release,workspace=current)
            self.assertFalse((Path(temp)/'OutfitFlux-99.0.0').exists())
    def test_cancel_does_not_publish(self):
        from services.process_service import ExportCancelled
        data=self.zip()
        with tempfile.TemporaryDirectory() as temp:
            current=Path(temp)/'current';current.mkdir()
            with patch('services.update_service.urllib.request.urlopen',return_value=io.BytesIO(data)):
                with self.assertRaises(ExportCancelled):install_update(self.release(data),lambda:True,workspace=current)
            self.assertFalse((Path(temp)/'OutfitFlux-99.0.0').exists())
