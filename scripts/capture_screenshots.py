"""Capture actual English UI screens without writing user preferences or exporting mods."""
import os
import sys
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PySide6 import QtWidgets as W, QtGui
from ui.studio_window import StudioWindow
from ui.export_review import ExportReviewDialog
from services.config_service import load_config

app = W.QApplication.instance() or W.QApplication([])
for font in ['segoeui.ttf', 'segoeuib.ttf', 'seguisym.ttf']:
    QtGui.QFontDatabase.addApplicationFont('C:/Windows/Fonts/' + font)
config = dict(load_config(), language='en')
output = ROOT / 'docs/media'
output.mkdir(parents=True, exist_ok=True)
with patch('ui.studio_window.load_config', return_value=config), patch('services.config_service.load_config', return_value=config), patch.object(StudioWindow, 'persist_preferences', lambda self: None):
    window = StudioWindow()
    if not window.records:
        raise SystemExit('Prepare a local costume library before capturing screenshots.')
    source = next((r for r in window.records if r['character'] == 'Ch046'), window.records[0])
    mesh = 'HerovsGame/Content/Character/' + source['skin_path'] + '.uasset'
    window.mod_loaded(dict(path='StylePack_P.pak', entries=[mesh], meshes=[mesh]))
    window.resize(1366, 768)
    window.show()
    window.wordmark.timer.stop()
    window.wordmark.phase = .45
    window.select_visible()
    for dark, name in [(True, 'workspace-dark'), (False, 'workspace-light')]:
        window.set_theme(dark)
        window.apply_language()
        app.processEvents()
        window.grab().save(str(output / (name + '.png')))
    window.set_theme(True)
    records = [r for r in window.records if r['character'] == source['character'] and r['skin_path'] != source['skin_path']][:4]
    review = ExportReviewDialog(window, records)
    review.show()
    app.processEvents()
    review.grab().save(str(output / 'export-review.png'))
    review.close()
    window.change_tab(2)
    app.processEvents()
    window.grab().save(str(output / 'tools.png'))
    queue = window.export_jobs
    with patch.object(queue, 'start_next'):
        queue.add('StylePack_P.pak', source['image'], lambda c, p: None, records)
    job = queue.jobs[0]
    job['status'] = 'running'
    queue.progress(job, 0, len(records), 'outfitflux-target:{"index":0,"step":5,"state":"done"}')
    queue.progress(job, 1, len(records), 'outfitflux-target:{"index":1,"step":3,"state":"rebuilding"}')
    window.change_tab(3)
    app.processEvents()
    window.grab().save(str(output / 'queue.png'))
    window.close()
print(output)
