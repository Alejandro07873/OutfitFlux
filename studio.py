"""New functional desktop entry point. Original UI remains available in main.py."""
import sys
from pathlib import Path
from PySide6 import QtCore, QtGui, QtWidgets
from ui.studio_window import StudioWindow


def main():
    QtWidgets.QApplication.setAttribute(QtCore.Qt.ApplicationAttribute.AA_DontUseNativeDialogs, False)
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    for filename in ['segoeui.ttf', 'segoeuib.ttf', 'seguisym.ttf']:
        path = Path('C:/Windows/Fonts') / filename
        if path.is_file():
            QtGui.QFontDatabase.addApplicationFont(str(path))
    from ui.outfit_translations import ScreenTranslator
    translator = ScreenTranslator(app)
    app.installEventFilter(translator)
    from util import ICON_PATH
    app.setWindowIcon(QtGui.QIcon(ICON_PATH))
    app.setApplicationName("OutfitFlux")
    window = StudioWindow()
    window.show()
    if '--smoke-test' not in sys.argv:
        from ui.outfit_setup import SetupDialog, claim_initial_setup
        if claim_initial_setup():
            if SetupDialog(window).exec() == QtWidgets.QDialog.DialogCode.Accepted:
                window.refresh_preferences()
    if '--smoke-test' in sys.argv:
        from services.json_store import write_json
        from services.game_service import validate_dependency_paths
        from util import WORKSPACE_DIR
        def smoke_test():
            output = Path(WORKSPACE_DIR) / 'temp' / 'studio-smoke'
            output.mkdir(parents=True, exist_ok=True)
            window.resize(1366, 705)
            app.processEvents()
            window.grab().save(str(output / 'startup.png'))
            write_json(output / 'result.json', {
                'records': len(window.records),
                'missing_dependencies': validate_dependency_paths(),
                'source_is_empty': window.source is None,
                'export_disabled_without_mod': not window.review.isEnabled(),
                'frozen': getattr(sys, 'frozen', False),
                'starts_at_import': window.pages.currentWidget() is window.home,
                'category': window.category,
            })
            window.close()
            app.quit()
        QtCore.QTimer.singleShot(100, smoke_test)
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
