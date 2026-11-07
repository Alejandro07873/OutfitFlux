from PySide6 import QtWidgets, QtCore

from util import APP_NAME
from ui.styles import build_app_stylesheet


_THEME_KEY = "ui/theme"
_THEME_DARK = "dark"
_THEME_LIGHT = "light"


def _settings():
    return QtCore.QSettings("aweooppoe", APP_NAME)


def get_saved_theme():
    value = _settings().value(_THEME_KEY, _THEME_DARK, type=str)
    value = (value or _THEME_DARK).strip().lower()
    if value not in {_THEME_DARK, _THEME_LIGHT}:
        value = _THEME_DARK
    return value


def save_theme(theme_name: str):
    theme_name = (theme_name or _THEME_DARK).strip().lower()
    if theme_name not in {_THEME_DARK, _THEME_LIGHT}:
        theme_name = _THEME_DARK
    _settings().setValue(_THEME_KEY, theme_name)


def current_theme_name(app=None):
    app = app or QtWidgets.QApplication.instance()
    if app is not None:
        value = app.property("theme_name")
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
    return get_saved_theme()


def apply_app_theme(app, theme_name=None):
    if app is None:
        return _THEME_DARK

    theme_name = (theme_name or get_saved_theme()).strip().lower()
    if theme_name not in {_THEME_DARK, _THEME_LIGHT}:
        theme_name = _THEME_DARK

    try:
        app.setStyle("Fusion")
    except Exception:
        pass

    app.setProperty("theme_name", theme_name)
    app.setStyleSheet(build_app_stylesheet(theme_name))
    save_theme(theme_name)
    return theme_name


def toggle_app_theme(app):
    current = current_theme_name(app)
    new_theme = _THEME_LIGHT if current == _THEME_DARK else _THEME_DARK
    return apply_app_theme(app, new_theme)