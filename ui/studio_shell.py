"""Shared iOS Dark / White theme for import-first screens."""
from ui.studio_layout import StudioLayout


class SwapStudio(StudioLayout):
    def set_theme(self, dark):
        self.dark = dark
        self.theme_button.setText("☀  White" if dark else "☾  Dark")
        if dark:
            c = dict(bg="#111113", fg="#f5f5f7", muted="#a1a1a8", panel="#1c1c1e", border="#38383a", soft="#2c2c2e", selected="#303033", accent="#a8c7ff", primary="#0a84ff", pfg="#ffffff", hero1="#202024", hero2="#1b1b1e", hero3="#242428", stagefg="#f4f4f6", stagemuted="#b7b7bf", glass="#2c2c2e", card="#202023", active="#303034", hover="#29292d")
        else:
            c = dict(bg="#f3f6fb", fg="#1d1d20", muted="#656571", panel="#ffffff", border="#e0e0e8", soft="#e6ecf5", selected="#ffffff", accent="#0068dc", primary="#007aff", pfg="#ffffff", hero1="#e8e0fc", hero2="#e1ebff", hero3="#ddf1ee", stagefg="#27223c", stagemuted="#585875", glass="#ffffff", card="#ffffff", active="#eaf2ff", hover="#f0f4fc")
        if hasattr(self, 'accent_combo'):
            c['primary'] = self.accent_combo.currentData() or c['primary']
        self.theme_colors = c
        self.setStyleSheet("""
        #ToolCard { text-align: left; padding: 0px; border-radius: 20px; border-left: 4px solid %(primary)s; }

        QWidget { background: %(bg)s; color: %(fg)s; font-family: 'Segoe UI'; font-size: 13px; }
        QDialog, QMessageBox, QFileDialog, QProgressDialog { background: %(bg)s; }
        QPlainTextEdit, QTextEdit, QTreeView, QTableView { background: %(panel)s; color: %(fg)s; border: 1px solid %(border)s; border-radius: 16px; padding: 12px; selection-background-color: %(primary)s; selection-color: white; }
        QHeaderView::section { background: %(soft)s; color: %(fg)s; padding: 9px; border: none; }
        QComboBox QAbstractItemView { background: %(panel)s; color: %(fg)s; selection-background-color: %(primary)s; selection-color: white; padding: 8px; border: 1px solid %(border)s; }
        QGroupBox { background: %(panel)s; border: 1px solid %(border)s; border-radius: 18px; margin-top: 16px; padding: 20px 12px 12px; }
        QGroupBox::title { subcontrol-origin: margin; left: 16px; padding: 0 6px; color: %(muted)s; }
        QStatusBar { background: %(panel)s; color: %(fg)s; padding: 10px; border-top: 2px solid %(primary)s; }
        QStatusBar::item { border: none; }
        QScrollArea { border: none; }
        QRadioButton { background: transparent; spacing: 8px; }
        QRadioButton::indicator { width: 16px; height: 16px; border: 1px solid %(muted)s; border-radius: 8px; }
        QRadioButton::indicator:checked { background: %(primary)s; border: 3px solid %(panel)s; }
        QScrollBar:horizontal { background: transparent; height: 8px; }
        QScrollBar::handle:horizontal { background: %(border)s; border-radius: 4px; min-width: 30px; }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
        QProgressBar { border: none; border-radius: 6px; background: %(soft)s; min-height: 12px; max-height: 16px; text-align: center; font-size: 10px; }
        QProgressBar::chunk { border-radius: 6px; background: %(primary)s; }
        QTabWidget::pane { border: none; padding-top: 16px; }
        QTabBar::tab { padding: 12px 24px; background: %(soft)s; border-radius: 12px; margin-right: 8px; }
        QTabBar::tab:selected { background: %(primary)s; color: white; }
        QLabel, #Slot { background: transparent; }
        #WelcomeHero { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 %(hero1)s,stop:0.55 %(hero2)s,stop:1 %(hero3)s); border: 1px solid %(border)s; border-radius: 30px; }
        #WelcomeEyebrow { color: %(accent)s; font-size: 11px; font-weight: 600; letter-spacing: 3px; }
        #StepCard { background: %(panel)s; border: 1px solid %(border)s; border-radius: 18px; }
        QToolTip { background: %(panel)s; color: %(fg)s; border: 1px solid %(border)s; padding: 8px; }
        QMenu { background: %(panel)s; border: 1px solid %(border)s; padding: 6px; }
        QMenu::item { padding: 9px 18px; border-radius: 7px; }
        QMenu::item:selected { background: %(active)s; color: %(fg)s; }
        QCheckBox { background: transparent; spacing: 7px; }
        QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid %(muted)s; border-radius: 5px; background: %(panel)s; }
        QCheckBox::indicator:checked { background: %(primary)s; border: 3px solid %(accent)s; }
        QPushButton:pressed { background: %(active)s; }
        QPushButton::menu-indicator { subcontrol-position: right center; right: 8px; }
        #Wordmark { font-size: 29px; font-weight: 700; letter-spacing: -1px; }
        #Eyebrow { font-size: 10px; color: %(muted)s; letter-spacing: 2px; }
        #Headline { font-size: 44px; font-weight: 700; letter-spacing: -2px; }
        #Muted { font-size: 12px; color: %(muted)s; }
        #ShelfTitle { font-size: 23px; font-weight: 600; letter-spacing: -1px; }
        #SelectionName { font-size: 14px; font-weight: 600; }
        #Segment { background: %(soft)s; border: 1px solid %(border)s; border-radius: 24px; }
        #Segment QPushButton { background: transparent; border: 1px solid transparent; color: %(muted)s; padding: 8px 12px; border-radius: 14px; }
        #Segment QPushButton:checked { background: %(selected)s; color: %(fg)s; }
        #Stage { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 %(hero1)s,stop:0.55 %(hero2)s,stop:1 %(hero3)s); border: 1px solid %(border)s; border-radius: 32px; }
        #StageEyebrow { color: %(stagemuted)s; font-size: 10px; letter-spacing: 2px; }
        #SlotTitle { color: %(stagefg)s; font-size: 26px; font-weight: 600; letter-spacing: -1px; }
        #StageMuted { color: %(stagemuted)s; font-size: 12px; }
        QPushButton { padding: 10px 18px; border-radius: 18px; border: 1px solid %(border)s; background: %(panel)s; font-weight: 600; }
        QPushButton:hover { background: %(hover)s; }
        QPushButton:focus { border: 2px solid %(primary)s; }
        QPushButton:disabled { color: %(muted)s; background: %(soft)s; }
        #ThemeSwitch { border-radius: 19px; background: %(soft)s; }
        #Import { background: transparent; color: %(accent)s; border: none; padding-left: 0px; }
        #GlassButton { background: %(glass)s; color: %(stagefg)s; border: 1px solid %(border)s; border-radius: 14px; font-size: 11px; }
        #Reverse { background: %(glass)s; color: %(stagefg)s; font-size: 38px; font-weight: 400; border-radius: 37px; padding: 0; }
        QComboBox, QLineEdit { background: %(soft)s; border: 1px solid transparent; border-radius: 15px; padding: 11px 14px; }
        QComboBox::drop-down { border: none; width: 24px; }
        QLineEdit:focus { border-color: %(primary)s; }
        #Mode { background: %(glass)s; color: %(stagefg)s; font-size: 12px; }
        QListWidget { background: transparent; border: none; outline: none; }
        QListWidget::item { background: %(card)s; border: 1px solid %(border)s; border-radius: 23px; padding: 8px; }
        QListWidget::item:selected { background: %(active)s; color: %(fg)s; border: 2px solid %(primary)s; }
        QListWidget::item:hover { background: %(hover)s; }
        #Dock { background: %(panel)s; border: 1px solid %(border)s; border-radius: 28px; }
        #Primary { background: %(primary)s; color: %(pfg)s; border: none; padding: 15px 22px; border-radius: 22px; }
        #Primary:disabled { background: %(soft)s; color: %(muted)s; }
        QScrollBar:vertical { background: transparent; width: 8px; }
        QScrollBar::handle:vertical { background: %(border)s; border-radius: 4px; min-height: 30px; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """ % c)

