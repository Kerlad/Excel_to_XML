"""
Tahoe Liquid Glass — дизайн-система для PyQt6
Поддержка светлой и тёмной темы + переключатель
"""
import sys
import os
import json
import ctypes


# ============ ЦВЕТОВЫЕ ПАЛИТРЫ ============

class TahoeColorsLight:
    """Светлая тема Tahoe Liquid Glass."""
    LAVENDER_CORAL = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #B39DDB, stop:1 #FF8A65)"
    CORAL_LAVENDER = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF8A65, stop:1 #B39DDB)"
    PRIMARY = "#7C4DFF"
    SECONDARY = "#FF6E40"
    ACCENT = "#00BCD4"
    GLASS_LIGHT = "rgba(255, 255, 255, 0.65)"
    GLASS_DARK = "rgba(30, 30, 40, 0.55)"
    GLASS_SUBTLE = "rgba(255, 255, 255, 0.45)"
    TEXT_PRIMARY = "#1A1A2E"
    TEXT_SECONDARY = "#666680"
    TEXT_ON_ACCENT = "#FFFFFF"
    SUCCESS = "#4CAF50"
    WARNING = "#FF9800"
    ERROR = "#F44336"
    BORDER_LIGHT = "rgba(255, 255, 255, 0.3)"
    BORDER_SUBTLE = "rgba(124, 77, 255, 0.15)"
    WINDOW_BG = "rgba(240, 240, 250, 0.95)"
    TABLE_ALTERNATE = "rgba(240, 240, 255, 0.3)"
    SCROLLBAR_HANDLE = "rgba(124, 77, 255, 0.3)"
    SCROLLBAR_HOVER = "rgba(124, 77, 255, 0.5)"
    MENU_BG = "rgba(255, 255, 255, 0.7)"


class TahoeColorsDark:
    """Тёмная тема Tahoe Liquid Glass."""
    LAVENDER_CORAL = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7C4DFF, stop:1 #FF6E40)"
    CORAL_LAVENDER = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF6E40, stop:1 #7C4DFF)"
    PRIMARY = "#B388FF"
    SECONDARY = "#FF8A65"
    ACCENT = "#26C6DA"
    GLASS_LIGHT = "rgba(40, 40, 55, 0.75)"
    GLASS_DARK = "rgba(25, 25, 35, 0.65)"
    GLASS_SUBTLE = "rgba(50, 50, 65, 0.55)"
    TEXT_PRIMARY = "#E8E8F0"
    TEXT_SECONDARY = "#A0A0B8"
    TEXT_ON_ACCENT = "#FFFFFF"
    SUCCESS = "#66BB6A"
    WARNING = "#FFA726"
    ERROR = "#EF5350"
    BORDER_LIGHT = "rgba(255, 255, 255, 0.08)"
    BORDER_SUBTLE = "rgba(179, 136, 255, 0.2)"
    WINDOW_BG = "rgba(20, 20, 30, 0.95)"
    TABLE_ALTERNATE = "rgba(35, 35, 50, 0.4)"
    SCROLLBAR_HANDLE = "rgba(179, 136, 255, 0.3)"
    SCROLLBAR_HOVER = "rgba(179, 136, 255, 0.5)"
    MENU_BG = "rgba(40, 40, 55, 0.8)"


# ============ ГЛОБАЛЬНЫЕ СТИЛИ ============

def get_global_stylesheet(theme: str = "light") -> str:
    """Глобальная QSS-stylesheet. theme: "light" или "dark"."""
    if theme == "dark":
        c = TahoeColorsDark()
    else:
        c = TahoeColorsLight()

    return f"""
        /* === ОСНОВНЫЕ ВИДЖЕТЫ === */
        QMainWindow {{
            background-color: {c.WINDOW_BG};
        }}

        QDialog {{
            background-color: {c.WINDOW_BG};
        }}

        QWidget {{
            color: {c.TEXT_PRIMARY};
            font-size: 13px;
        }}

        /* === GLASS КАРТОЧКИ (QGroupBox) === */
        QGroupBox {{
            background-color: {c.GLASS_LIGHT};
            border: 1px solid {c.BORDER_SUBTLE};
            border-radius: 16px;
            margin-top: 12px;
            padding: 16px;
            font-weight: bold;
            font-size: 14px;
            color: {c.PRIMARY};
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 16px;
            padding: 0 8px;
            color: {c.PRIMARY};
        }}

        /* === PILL BUTTONS === */
        QPushButton {{
            background-color: {c.GLASS_LIGHT};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER_SUBTLE};
            border-radius: 9999px;
            padding: 8px 20px;
            font-weight: bold;
            font-size: 13px;
        }}

        QPushButton:hover {{
            background-color: rgba(124, 77, 255, 0.15);
            border-color: {c.PRIMARY};
        }}

        QPushButton:pressed {{
            background-color: rgba(124, 77, 255, 0.25);
            padding-top: 9px;
            padding-bottom: 7px;
        }}

        /* Primary кнопки */
        QPushButton[primary="true"] {{
            background: {c.LAVENDER_CORAL};
            color: white;
            border: none;
        }}

        QPushButton[primary="true"]:hover {{
            opacity: 0.85;
        }}

        QPushButton[primary="true"]:pressed {{
            opacity: 0.7;
        }}

        /* Success кнопки */
        QPushButton[success="true"] {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4CAF50, stop:1 #66BB6A);
            color: white;
            border: none;
        }}

        /* Danger кнопки */
        QPushButton[danger="true"] {{
            background-color: transparent;
            color: {c.ERROR};
            border: 1.5px solid {c.ERROR};
        }}

        QPushButton[danger="true"]:hover {{
            background-color: rgba(244, 67, 54, 0.1);
        }}

        /* === ПОЛЯ ВВОДА === */
        QLineEdit {{
            background-color: {c.GLASS_SUBTLE};
            border: 1px solid {c.BORDER_SUBTLE};
            border-radius: 12px;
            padding: 8px 14px;
            color: {c.TEXT_PRIMARY};
            selection-background-color: {c.PRIMARY};
        }}

        QLineEdit:focus {{
            border-color: {c.PRIMARY};
            background-color: {c.GLASS_LIGHT};
        }}

        QLineEdit:read-only {{
            background-color: rgba(200, 200, 220, 0.3);
        }}

        /* === COMBO BOX === */
        QComboBox {{
            background-color: {c.GLASS_SUBTLE};
            border: 1px solid {c.BORDER_SUBTLE};
            border-radius: 12px;
            padding: 6px 14px;
            color: {c.TEXT_PRIMARY};
        }}

        QComboBox:hover {{
            border-color: {c.PRIMARY};
        }}

        QComboBox::drop-down {{
            border: none;
            padding-right: 8px;
        }}

        QComboBox QAbstractItemView {{
            background-color: {c.GLASS_LIGHT};
            border: 1px solid {c.BORDER_SUBTLE};
            border-radius: 8px;
            selection-background-color: {c.PRIMARY};
            selection-color: white;
            outline: none;
        }}

        /* === ТАБЛИЦЫ === */
        QTableWidget {{
            background-color: {c.GLASS_SUBTLE};
            alternate-background-color: {c.TABLE_ALTERNATE};
            border: 1px solid {c.BORDER_SUBTLE};
            border-radius: 12px;
            gridline-color: rgba(124, 77, 255, 0.1);
            color: {c.TEXT_PRIMARY};
            selection-background-color: rgba(124, 77, 255, 0.25);
            selection-color: {c.TEXT_PRIMARY};
        }}

        QTableWidget::item {{
            padding: 6px;
            background-color: transparent;
            color: {c.TEXT_PRIMARY};
        }}

        QTableWidget::item:selected {{
            background-color: rgba(124, 77, 255, 0.25);
            color: {c.TEXT_PRIMARY};
        }}

        QHeaderView::section {{
            background: {c.LAVENDER_CORAL};
            color: white;
            padding: 8px;
            border: none;
            font-weight: bold;
            font-size: 12px;
        }}

        QHeaderView::section:first {{
            border-top-left-radius: 12px;
        }}

        QHeaderView::section:last {{
            border-top-right-radius: 12px;
        }}

        /* === СКРОЛЛБАРЫ === */
        QScrollBar:vertical {{
            background: transparent;
            width: 8px;
            margin: 0;
        }}

        QScrollBar::handle:vertical {{
            background: {c.SCROLLBAR_HANDLE};
            border-radius: 4px;
            min-height: 30px;
        }}

        QScrollBar::handle:vertical:hover {{
            background: {c.SCROLLBAR_HOVER};
        }}

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}

        QScrollBar:horizontal {{
            background: transparent;
            height: 8px;
            margin: 0;
        }}

        QScrollBar::handle:horizontal {{
            background: {c.SCROLLBAR_HANDLE};
            border-radius: 4px;
            min-width: 30px;
        }}

        QScrollBar::handle:horizontal:hover {{
            background: {c.SCROLLBAR_HOVER};
        }}

        /* === ВКЛАДКИ (QTabWidget) === */
        QTabWidget::pane {{
            border: none;
            background: transparent;
        }}

        QTabBar::tab {{
            background-color: transparent;
            color: {c.TEXT_SECONDARY};
            padding: 10px 20px;
            border: none;
            border-bottom: 2px solid transparent;
            font-weight: bold;
            margin-right: 4px;
        }}

        QTabBar::tab:selected {{
            color: {c.PRIMARY};
            border-bottom: 2px solid {c.PRIMARY};
        }}

        QTabBar::tab:hover:!selected {{
            color: {c.PRIMARY};
            border-bottom: 2px solid rgba(124, 77, 255, 0.3);
        }}

        /* === СПИСОК === */
        QListWidget {{
            background-color: {c.GLASS_SUBTLE};
            border: 1px solid {c.BORDER_SUBTLE};
            border-radius: 12px;
        }}

        QListWidget::item {{
            padding: 8px 12px;
            border-radius: 8px;
            color: {c.TEXT_PRIMARY};
        }}

        QListWidget::item:selected {{
            background-color: rgba(124, 77, 255, 0.25);
            color: {c.TEXT_PRIMARY};
        }}

        /* === TE (Справка) === */
        QTextEdit {{
            background-color: {c.GLASS_SUBTLE};
            border: 1px solid {c.BORDER_SUBTLE};
            border-radius: 12px;
            padding: 12px;
            color: {c.TEXT_PRIMARY};
        }}

        /* === QDateEdit === */
        QDateEdit {{
            background-color: {c.GLASS_SUBTLE};
            border: 1px solid {c.BORDER_SUBTLE};
            border-radius: 12px;
            padding: 6px 14px;
            color: {c.TEXT_PRIMARY};
        }}

        QDateEdit::drop-down {{
            border: none;
            padding-right: 8px;
        }}

        /* === QLabel === */
        QLabel {{
            background-color: transparent;
            color: {c.TEXT_PRIMARY};
        }}

        /* === QMenu / QMenuBar === */
        QMenuBar {{
            background-color: {c.MENU_BG};
            border-bottom: 1px solid {c.BORDER_SUBTLE};
            color: {c.TEXT_PRIMARY};
        }}

        QMenuBar::item {{
            padding: 6px 12px;
            border-radius: 6px;
            color: {c.TEXT_PRIMARY};
        }}

        QMenuBar::item:selected {{
            background-color: rgba(124, 77, 255, 0.2);
        }}

        QMenu {{
            background-color: {c.MENU_BG};
            border: 1px solid {c.BORDER_SUBTLE};
            border-radius: 8px;
            padding: 4px;
            color: {c.TEXT_PRIMARY};
        }}

        QMenu::item {{
            padding: 6px 20px;
            border-radius: 6px;
            color: {c.TEXT_PRIMARY};
        }}

        QMenu::item:selected {{
            background-color: rgba(124, 77, 255, 0.2);
        }}

        /* === QCalendarWidget === */
        QCalendarWidget QMenu {{
            background-color: {c.MENU_BG};
        }}

        QCalendarWidget QWidget#qt_calendar_navigationbar {{
            background-color: transparent;
        }}

        QCalendarWidget QToolButton {{
            background-color: transparent;
            border: none;
            color: {c.TEXT_PRIMARY};
            border-radius: 8px;
            padding: 6px;
        }}

        QCalendarWidget QToolButton:hover {{
            background-color: rgba(124, 77, 255, 0.15);
        }}

        QCalendarWidget QSpinBox {{
            background-color: {c.GLASS_SUBTLE};
            border: 1px solid {c.BORDER_SUBTLE};
            border-radius: 8px;
            color: {c.TEXT_PRIMARY};
        }}

        /* === ВСПЛЫВАЮЩИЕ ОКНА (QMessageBox, QInputDialog, QFileDialog) === */
        QMessageBox {{
            background-color: {c.WINDOW_BG};
            color: {c.TEXT_PRIMARY};
        }}

        QMessageBox QLabel {{
            color: {c.TEXT_PRIMARY};
            background-color: transparent;
        }}

        QMessageBox QPushButton {{
            background-color: {c.GLASS_LIGHT};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER_SUBTLE};
            border-radius: 9999px;
            padding: 8px 20px;
            font-weight: bold;
        }}

        QMessageBox QPushButton:hover {{
            background-color: rgba(124, 77, 255, 0.15);
            border-color: {c.PRIMARY};
        }}

        QFileDialog {{
            background-color: {c.WINDOW_BG};
            color: {c.TEXT_PRIMARY};
        }}

        QFileDialog QLabel {{
            color: {c.TEXT_PRIMARY};
            background-color: transparent;
        }}

        QFileDialog QPushButton {{
            background-color: {c.GLASS_LIGHT};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER_SUBTLE};
            border-radius: 9999px;
            padding: 6px 16px;
            font-weight: bold;
        }}

        QFileDialog QListView {{
            background-color: {c.GLASS_SUBTLE};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER_SUBTLE};
            border-radius: 8px;
        }}

        QInputDialog {{
            background-color: {c.WINDOW_BG};
            color: {c.TEXT_PRIMARY};
        }}

        QInputDialog QLabel {{
            color: {c.TEXT_PRIMARY};
            background-color: transparent;
        }}

        QInputDialog QLineEdit {{
            background-color: {c.GLASS_SUBTLE};
            border: 1px solid {c.BORDER_SUBTLE};
            border-radius: 12px;
            padding: 8px 14px;
            color: {c.TEXT_PRIMARY};
        }}

        QInputDialog QPushButton {{
            background-color: {c.GLASS_LIGHT};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER_SUBTLE};
            border-radius: 9999px;
            padding: 6px 16px;
            font-weight: bold;
        }}

        /* === QTextEdit в диалогах === */
        QDialog QTextEdit {{
            background-color: {c.GLASS_SUBTLE};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER_SUBTLE};
            border-radius: 12px;
        }}

        QDialog QLineEdit {{
            background-color: {c.GLASS_SUBTLE};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER_SUBTLE};
            border-radius: 12px;
            padding: 8px 14px;
        }}

        QDialog QComboBox {{
            background-color: {c.GLASS_SUBTLE};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER_SUBTLE};
            border-radius: 12px;
            padding: 6px 14px;
        }}

        QDialog QTableWidget {{
            background-color: {c.GLASS_SUBTLE};
            alternate-background-color: {c.TABLE_ALTERNATE};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER_SUBTLE};
            border-radius: 12px;
            gridline-color: rgba(124, 77, 255, 0.1);
        }}

        QDialog QTableWidget::item {{
            background-color: transparent;
            color: {c.TEXT_PRIMARY};
        }}

        QDialog QTableWidget::item:selected {{
            background-color: rgba(124, 77, 255, 0.25);
            color: {c.TEXT_PRIMARY};
        }}

        QDialog QListWidget {{
            background-color: {c.GLASS_SUBTLE};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER_SUBTLE};
            border-radius: 12px;
        }}

        QDialog QListWidget::item {{
            color: {c.TEXT_PRIMARY};
        }}

        QDialog QListWidget::item:selected {{
            background-color: rgba(124, 77, 255, 0.25);
            color: {c.TEXT_PRIMARY};
        }}
    """


# ============ MICA BACKDROP ============

def apply_mica(window) -> bool:
    """
    Применяет Mica backdrop к окну (Windows 11+).
    БЕЗ прозрачности — просто Mica + корректные цвета рамки.
    """
    if sys.platform != "win32":
        return False

    try:
        hwnd = int(window.winId())
        dwmapi = ctypes.windll.dwmapi

        DWMWA_SYSTEMBACKDROP_TYPE = 38
        DWMSBT_MAINWINDOW = 2

        attr = ctypes.c_int(DWMSBT_MAINWINDOW)
        result = dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_SYSTEMBACKDROP_TYPE,
            ctypes.byref(attr),
            ctypes.sizeof(attr)
        )

        if result == 0:
            # НЕ используем прозрачность — Mica работает и без неё
            # Отключаем системный dark mode рамки — всегда светлая
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            dark_mode = ctypes.c_int(0)
            dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(dark_mode),
                ctypes.sizeof(dark_mode)
            )
            return True

        return False

    except Exception:
        return False


# ============ THEME MANAGER ============

def get_theme_dir(base_dir: str) -> str:
    """Дирекория для файла настроек темы."""
    d = os.path.join(base_dir, "data")
    os.makedirs(d, exist_ok=True)
    return d


def get_theme_file(base_dir: str) -> str:
    """Путь к файлу настроек темы."""
    return os.path.join(get_theme_dir(base_dir), "theme_settings.json")


def load_theme(base_dir: str) -> str:
    """Загрузка темы: 'light' или 'dark'."""
    path = get_theme_file(base_dir)
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('theme', 'light')
        except Exception:
            pass
    return 'light'


def save_theme(base_dir: str, theme: str):
    """Сохранение темы."""
    path = get_theme_file(base_dir)
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'theme': theme}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ============ GLASS CARD & PILL BUTTON ============

from PyQt6.QtWidgets import QFrame, QPushButton, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt


class GlassCard(QFrame):
    """Glass-карточка с acrylic-эффектом (имитация через полупрозрачность)."""

    def __init__(self, parent=None, title: str = "", elevation: int = 1):
        super().__init__(parent)
        self._title = title
        self._elevation = elevation
        self._init_ui()

    def _init_ui(self):
        self.setFrameShape(QFrame.Shape.StyledPanel)
        opacity = 0.55 + (self._elevation * 0.05)
        opacity = min(opacity, 0.85)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(255, 255, 255, {opacity});
                border: 1px solid rgba(124, 77, 255, 0.12);
                border-radius: 16px;
            }}
        """)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(12)

        if self._title:
            title_label = QLabel(self._title)
            title_label.setStyleSheet("""
                color: #7C4DFF;
                font-weight: bold;
                font-size: 15px;
                background-color: transparent;
            """)
            self._layout.insertWidget(0, title_label)

    def layout(self):
        return self._layout


class PillButton(QPushButton):
    """Скруглённая кнопка с анимацией нажатия."""

    def __init__(self, text: str = "", variant: str = "default", parent=None):
        super().__init__(text, parent)
        self._variant = variant
        self._apply_style()

    def _apply_style(self):
        if self._variant == "primary":
            self.setProperty("primary", True)
        elif self._variant == "success":
            self.setProperty("success", True)
        elif self._variant == "danger":
            self.setProperty("danger", True)
        self.style().unpolish(self)
        self.style().polish(self)
