def build_app_stylesheet(theme_name="dark"):
    theme_name = (theme_name or "dark").strip().lower()

    if theme_name == "light":
        colors = {
            "bg": "#f4f6f8",
            "panel": "#ffffff",
            "panel2": "#eef2f6",
            "panel3": "#f8fafc",
            "border": "#d7dde5",
            "border_strong": "#c5ced8",
            "text": "#111827",
            "muted": "#5f6b7a",
            "soft": "#7b8794",
            "accent": "#0a6cff",
            "accent_hover": "#2d7dff",
            "accent_soft": "rgba(10,108,255,0.08)",
            "success": "#1f9d55",
            "success_soft": "rgba(31,157,85,0.10)",
            "warning": "#d9822b",
            "warning_soft": "rgba(217,130,43,0.10)",
            "danger": "#c93c37",
            "danger_soft": "rgba(201,60,55,0.10)",
            "input": "#ffffff",
            "input_border": "#cfd7e2",
            "hover": "#f3f6fb",
            "pressed": "#e8edf5",
            "disabled_bg": "#eef1f4",
            "disabled_text": "#95a0ad",
            "scroll": "#c4ccd7",
            "scroll_hover": "#aeb8c5",
            "selection": "#dbeafe",
        }
    else:
        colors = {
            "bg": "#1f1f1f",
            "panel": "#272727",
            "panel2": "#2d2d2d",
            "panel3": "#242424",
            "border": "#3a3a3a",
            "border_strong": "#4a4a4a",
            "text": "#f3f4f6",
            "muted": "#b7bec8",
            "soft": "#9aa4b2",
            "accent": "#2d7dff",
            "accent_hover": "#4a90ff",
            "accent_soft": "rgba(45,125,255,0.12)",
            "success": "#31b86b",
            "success_soft": "rgba(49,184,107,0.12)",
            "warning": "#ff9f2d",
            "warning_soft": "rgba(255,159,45,0.12)",
            "danger": "#ff6b6b",
            "danger_soft": "rgba(255,107,107,0.12)",
            "input": "#2b2b2b",
            "input_border": "#454545",
            "hover": "#333333",
            "pressed": "#2b2b2b",
            "disabled_bg": "#292929",
            "disabled_text": "#7d7d7d",
            "scroll": "#4c4c4c",
            "scroll_hover": "#666666",
            "selection": "#234a8a",
        }

    qss = f"""
    QWidget {{
        background-color: {colors['bg']};
        color: {colors['text']};
        font-family: "Segoe UI";
        font-size: 10pt;
    }}

    QMainWindow, QDialog {{
        background-color: {colors['bg']};
    }}

    QStackedWidget, QScrollArea {{
        border: none;
        background: transparent;
    }}

    QLabel#TitleLabel {{
        font-size: 22pt;
        font-weight: 700;
        color: {colors['text']};
        background: transparent;
    }}

    QLabel#SubtitleLabel {{
        font-size: 10pt;
        color: {colors['muted']};
        background: transparent;
    }}

    QLabel#MutedLabel {{
        color: {colors['soft']};
        background: transparent;
    }}

    QLabel#StatusLabel {{
        color: {colors['muted']};
        font-weight: 600;
        background: transparent;
    }}

    QLabel#SummaryLabel {{
        color: {colors['muted']};
        font-weight: 700;
        background: transparent;
    }}

    QFrame#HeroCard {{
        background-color: {colors['panel']};
        border: 1px solid {colors['border']};
        border-radius: 18px;
    }}

    QFrame#SectionCard {{
        background-color: {colors['panel']};
        border: 1px solid {colors['border']};
        border-radius: 14px;
    }}

    QFrame#SkinCard {{
        background-color: {colors['panel']};
        border: 1px solid {colors['border']};
        border-radius: 16px;
    }}

    QFrame#SkinCard[hovered="true"] {{
        background-color: {colors['hover']};
        border: 1px solid {colors['accent']};
    }}

    QFrame#SkinCard[current="true"] {{
        background-color: {colors['accent_soft']};
        border: 1px solid {colors['accent']};
    }}

    QFrame#SkinCard[unknown="true"] {{
        background-color: {colors['warning_soft']};
        border: 1px solid {colors['warning']};
    }}

    QFrame#SkinCard[selected="true"] {{
        background-color: {colors['success_soft']};
        border: 1px solid {colors['success']};
    }}

    QFrame#ThumbnailFrame {{
        background-color: {colors['panel2']};
        border: 1px solid {colors['border']};
        border-radius: 12px;
    }}

    QLineEdit, QComboBox {{
        background-color: {colors['input']};
        color: {colors['text']};
        border: 1px solid {colors['input_border']};
        border-radius: 10px;
        padding: 8px 10px;
        selection-background-color: {colors['selection']};
    }}

    QLineEdit:focus, QComboBox:focus {{
        border: 1px solid {colors['accent']};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {colors['panel2']};
        color: {colors['text']};
        border: 1px solid {colors['border']};
        selection-background-color: {colors['selection']};
    }}

    QPushButton {{
        background-color: {colors['panel2']};
        color: {colors['text']};
        border: 1px solid {colors['border_strong']};
        border-radius: 10px;
        padding: 9px 14px;
        font-weight: 600;
    }}

    QPushButton:hover {{
        background-color: {colors['hover']};
        border: 1px solid {colors['accent']};
    }}

    QPushButton:pressed {{
        background-color: {colors['pressed']};
    }}

    QPushButton:disabled {{
        background-color: {colors['disabled_bg']};
        color: {colors['disabled_text']};
        border: 1px solid {colors['border']};
    }}

    QPushButton#AccentButton {{
        background-color: {colors['accent']};
        color: white;
        border: 1px solid {colors['accent']};
    }}

    QPushButton#AccentButton:hover {{
        background-color: {colors['accent_hover']};
        border: 1px solid {colors['accent_hover']};
    }}

    QPushButton#GhostButton {{
        background-color: transparent;
        color: {colors['muted']};
        border: 1px solid {colors['border']};
    }}

    QPushButton#GhostButton:hover {{
        background-color: {colors['hover']};
        color: {colors['text']};
        border: 1px solid {colors['accent']};
    }}

    QPushButton#DangerButton {{
        background-color: {colors['danger_soft']};
        color: {colors['danger']};
        border: 1px solid {colors['danger']};
    }}

    QCheckBox {{
        color: {colors['text']};
        spacing: 8px;
        background: transparent;
    }}

    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
    }}

    QProgressBar {{
        background-color: {colors['panel2']};
        border: 1px solid {colors['border']};
        border-radius: 8px;
        text-align: center;
        min-height: 20px;
    }}

    QProgressBar::chunk {{
        background-color: {colors['accent']};
        border-radius: 7px;
    }}

    QMessageBox, QProgressDialog {{
        background-color: {colors['bg']};
    }}

    QScrollBar:vertical {{
        background: transparent;
        width: 12px;
        margin: 0;
    }}

    QScrollBar::handle:vertical {{
        background: {colors['scroll']};
        border-radius: 6px;
        min-height: 28px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: {colors['scroll_hover']};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
        background: transparent;
        border: none;
    }}

    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: transparent;
    }}
    """
    return qss