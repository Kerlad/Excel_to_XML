"""
Tahoe Liquid Glass — дизайн-система для PySide6
Поддержка светлой и тёмной темы + переключатель
"""
import sys
import os
import json
import ctypes

from PySide6.QtGui import QPalette, QColor


# ============ ЕДИНАЯ ЦВЕТОВАЯ СИСТЕМА ============
# Primary  : #4A90E2  Action, focus, links
# Success  : #27AE60  Positive states
# Danger   : #E74C3C  Errors, destructive
# Warning  : #F1C40F  Attention


class _BaseColors:
    """Базовые цвета для обоих тем (primitive palette)."""
    PRIMARY_LIGHT   = "#4A90E2"
    SUCCESS_LIGHT   = "#27AE60"
    DANGER_LIGHT    = "#E74C3C"
    WARNING_LIGHT   = "#F1C40F"

    PRIMARY_DARK    = "#5A9CF3"
    SUCCESS_DARK    = "#2ECC71"
    DANGER_DARK     = "#EC7063"
    WARNING_DARK    = "#F4D03F"


class TahoeColorsLight:
    """Светлая тема — прозрачные стеклянные тона."""
    LAVENDER_CORAL = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #B39DDB, stop:1 #FF8A65)"
    CORAL_LAVENDER = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF8A65, stop:1 #B39DDB)"
    PRIMARY = "#4A90E2"
    SECONDARY = "#FF6E40"
    ACCENT = "#00BCD4"
    GLASS_LIGHT = "rgba(255, 255, 255, 0.75)"
    GLASS_DARK = "rgba(30, 30, 40, 0.2)"
    GLASS_SUBTLE = "rgba(255, 255, 255, 0.5)"
    TEXT_PRIMARY = "#1A1A2E"
    TEXT_SECONDARY = "#666680"
    TEXT_ON_ACCENT = "#FFFFFF"
    TEXT_PLACEHOLDER = "#999999"
    SUCCESS = "#27AE60"
    WARNING = "#F1C40F"
    ERROR = "#E74C3C"
    BORDER_LIGHT = "rgba(0, 0, 0, 0.12)"
    BORDER_SUBTLE = "rgba(74, 144, 226, 0.2)"
    WINDOW_BG = "#F0F2F5"
    SURFACE_BG = "#FFFFFF"
    TABLE_ALTERNATE = "rgba(74, 144, 226, 0.06)"
    INPUT_BG = "#FFFFFF"
    SCROLLBAR_HANDLE = "rgba(74, 144, 226, 0.25)"
    SCROLLBAR_HOVER = "rgba(74, 144, 226, 0.45)"
    MENU_BG = "#FFFFFF"
    HIGHLIGHT_BG = "rgba(74, 144, 226, 0.15)"
    HIGHLIGHT_SELECTED = "rgba(74, 144, 226, 0.3)"


class TahoeColorsDark:
    """Тёмная тема — #2D2D2D фон, #363636 base, #5E9ED6 primary."""
    LAVENDER_CORAL = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7C4DFF, stop:1 #FF6E40)"
    CORAL_LAVENDER = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF6E40, stop:1 #7C4DFF)"
    PRIMARY = "#5E9ED6"
    SECONDARY = "#FF8A65"
    ACCENT = "#26C6DA"

    GLASS_LIGHT = "#363636"
    GLASS_DARK = "#2A2A2A"
    GLASS_SUBTLE = "#000000"

    TEXT_PRIMARY = "#E0E0E0"
    TEXT_SECONDARY = "#A0A0A0"
    TEXT_ON_ACCENT = "#FFFFFF"
    TEXT_DISABLED = "#777777"
    TEXT_PLACEHOLDER = "#888888"

    SUCCESS = "#4CAF50"
    WARNING = "#F4D03F"
    ERROR = "#F44336"

    BORDER_LIGHT = "rgba(255, 255, 255, 0.08)"
    BORDER_SUBTLE = "rgba(94, 158, 214, 0.3)"
    BORDER_INPUT = "#555555"

    WINDOW_BG = "#2D2D2D"
    SURFACE_BG = "#363636"
    TABLE_ALTERNATE = "#3A3A3A"
    INPUT_BG = "#424242"

    SCROLLBAR_HANDLE = "rgba(94, 158, 214, 0.3)"
    SCROLLBAR_HOVER = "rgba(94, 158, 214, 0.5)"
    MENU_BG = "#363636"

    HIGHLIGHT_BG = "rgba(94, 158, 214, 0.15)"
    HIGHLIGHT_SELECTED = "rgba(94, 158, 214, 0.3)"


# ============ QPALETTE ============

def create_palette(theme: str = "light") -> QPalette:
    """
    Создаёт QPalette с полным набором ColorRole.
    Включает Normal, Disabled, Inactive группы для корректной работы Fusion style.
    """
    if theme == "dark":
        return _build_dark_palette()
    return _build_light_palette()


def _build_light_palette() -> QPalette:
    p = QPalette()

    # Normal
    p.setColor(QPalette.ColorRole.Window,          QColor(240, 242, 245))
    p.setColor(QPalette.ColorRole.WindowText,      QColor(26, 26, 46))
    p.setColor(QPalette.ColorRole.Base,            QColor(255, 255, 255))
    p.setColor(QPalette.ColorRole.AlternateBase,   QColor(244, 246, 250))
    p.setColor(QPalette.ColorRole.Text,            QColor(26, 26, 46))
    p.setColor(QPalette.ColorRole.Button,          QColor(240, 242, 245))
    p.setColor(QPalette.ColorRole.ButtonText,      QColor(26, 26, 46))
    p.setColor(QPalette.ColorRole.BrightText,      QColor(255, 255, 255))
    p.setColor(QPalette.ColorRole.Highlight,       QColor(74, 144, 226))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    p.setColor(QPalette.ColorRole.Link,            QColor(74, 144, 226))
    p.setColor(QPalette.ColorRole.LinkVisited,     QColor(74, 144, 226))
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor(153, 153, 153))

    # Disabled
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText,      QColor(160, 160, 170))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text,            QColor(160, 160, 170))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText,      QColor(160, 160, 170))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Highlight,       QColor(200, 200, 210))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Base,            QColor(230, 230, 235))

    # Inactive (same as Normal except selection)
    p.setColor(QPalette.ColorGroup.Inactive, QPalette.ColorRole.Highlight,       QColor(74, 144, 226, 100))
    p.setColor(QPalette.ColorGroup.Inactive, QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))

    return p


def _build_dark_palette() -> QPalette:
    p = QPalette()

    # Normal
    p.setColor(QPalette.ColorRole.Window,          QColor(45, 45, 45))
    p.setColor(QPalette.ColorRole.WindowText,      QColor(224, 224, 224))
    p.setColor(QPalette.ColorRole.Base,            QColor(54, 54, 54))
    p.setColor(QPalette.ColorRole.AlternateBase,   QColor(58, 58, 58))
    p.setColor(QPalette.ColorRole.Text,            QColor(224, 224, 224))
    p.setColor(QPalette.ColorRole.Button,          QColor(54, 54, 54))
    p.setColor(QPalette.ColorRole.ButtonText,      QColor(224, 224, 224))
    p.setColor(QPalette.ColorRole.BrightText,      QColor(255, 255, 255))
    p.setColor(QPalette.ColorRole.Highlight,       QColor(94, 158, 214))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    p.setColor(QPalette.ColorRole.Link,            QColor(94, 158, 214))
    p.setColor(QPalette.ColorRole.LinkVisited,     QColor(94, 158, 214))
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor(136, 136, 136))

    # Disabled
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText,      QColor(119, 119, 119))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text,            QColor(119, 119, 119))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText,      QColor(119, 119, 119))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Highlight,       QColor(60, 60, 60))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.HighlightedText, QColor(128, 128, 128))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Base,            QColor(40, 40, 40))

    # Inactive
    p.setColor(QPalette.ColorGroup.Inactive, QPalette.ColorRole.Highlight,       QColor(94, 158, 214, 100))
    p.setColor(QPalette.ColorGroup.Inactive, QPalette.ColorRole.HighlightedText, QColor(224, 224, 224))

    return p


# ============ ГЛОБАЛЬНЫЙ STYLESHEET ============

def get_global_stylesheet(theme: str = "light") -> str:
    """Глобальная QSS-stylesheet. theme: 'light' или 'dark'."""
    if theme == "dark":
        c = TahoeColorsDark()
    else:
        c = TahoeColorsLight()

    primary_hex = c.PRIMARY
    highlight_bg = c.HIGHLIGHT_BG
    highlight_sel = c.HIGHLIGHT_SELECTED

    return f"""
        QMainWindow,
        QDialog {{
            background-color: {c.WINDOW_BG};
        }}

        QWidget {{
            color: {c.TEXT_PRIMARY};
            font-size: 13px;
        }}

        /* ============ QGroupBox ============ */
        QGroupBox {{
            background-color: {c.SURFACE_BG};
            border: 1px solid {c.BORDER_LIGHT};
            border-radius: 10px;
            margin-top: 14px;
            padding: 18px 16px 16px 16px;
            font-weight: bold;
            font-size: 14px;
            color: {c.PRIMARY};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 14px;
            padding: 0 8px;
            color: {c.PRIMARY};
            font-weight: bold;
        }}

        /* ============ QPushButton ============ */
        QPushButton {{
            background-color: {c.SURFACE_BG};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER_INPUT if theme == "dark" else c.BORDER_LIGHT};
            border-radius: 8px;
            padding: 7px 18px;
            font-weight: bold;
            font-size: 13px;
        }}
        QPushButton:hover {{
            background-color: {highlight_bg};
            border-color: {c.PRIMARY};
        }}
        QPushButton:pressed {{
            background-color: {highlight_sel};
            padding-top: 8px;
            padding-bottom: 6px;
        }}
        QPushButton:disabled {{
            color: {c.TEXT_DISABLED if theme == "dark" else "#AAA"} !important;
            background-color: {c.SURFACE_BG};
            border-color: {c.BORDER_LIGHT};
        }}

        QPushButton[primary="true"] {{
            background-color: {primary_hex};
            color: #FFFFFF;
            border: none;
        }}
        QPushButton[primary="true"]:hover {{
            background-color: {primary_hex};
        }}
        QPushButton[primary="true"]:pressed {{
            background-color: {primary_hex};
            padding-top: 8px;
            padding-bottom: 6px;
        }}

        QPushButton[success="true"] {{
            background-color: {c.SUCCESS};
            color: #FFFFFF;
            border: none;
        }}
        QPushButton[success="true"]:hover {{
            background-color: {c.SUCCESS};
        }}
        QPushButton[success="true"]:pressed {{
            background-color: {c.SUCCESS};
            padding-top: 8px;
            padding-bottom: 6px;
        }}

        QPushButton[danger="true"] {{
            background-color: transparent;
            color: {c.ERROR};
            border: 1.5px solid {c.ERROR};
        }}
        QPushButton[danger="true"]:hover {{
            background-color: {c.ERROR}22;
        }}
        QPushButton[danger="true"]:pressed {{
            background-color: {c.ERROR}44;
        }}

        /* ============ ProtocolTab member cards ============ */
        #memberCard {{
            background-color: {c.SURFACE_BG};
            border: 1px solid {c.BORDER_INPUT if theme == "dark" else c.BORDER_LIGHT};
            border-radius: 8px;
        }}
        #memberRemoveBtn {{
            background-color: transparent;
            color: {c.ERROR};
            border: 1px solid {c.ERROR};
            border-radius: 4px;
            font-weight: bold;
            font-size: 12px;
            padding: 0;
            min-width: 24px;
            min-height: 24px;
        }}
        #memberRemoveBtn:hover {{
            background-color: rgba(236, 112, 99, 0.15);
        }}
        #addMemberBtn {{
            background-color: transparent;
            color: {c.PRIMARY};
            border: 1px dashed {c.BORDER_INPUT if theme == "dark" else "#AAA"};
            border-radius: 6px;
            padding: 6px 14px;
            font-weight: normal;
        }}
        #addMemberBtn:hover {{
            background-color: {highlight_bg};
            border-color: {c.PRIMARY};
            border-style: solid;
        }}

        /* ============ ProtocolTab action buttons ============ */
        #saveCommissionBtn {{
            background-color: {primary_hex};
            color: #FFFFFF;
            border: none;
            padding: 8px 22px;
        }}
        #saveCommissionBtn:hover {{
            background-color: {primary_hex};
        }}
        #saveCommissionBtn:pressed {{
            background-color: {primary_hex};
            padding-top: 9px;
            padding-bottom: 7px;
        }}

        #loadCommissionBtn {{
            background-color: {c.SURFACE_BG};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER_INPUT if theme == "dark" else c.BORDER_LIGHT};
        }}
        #loadCommissionBtn:hover {{
            background-color: {highlight_bg};
            border-color: {c.PRIMARY};
        }}

        #generateProtocolBtn {{
            background-color: {c.SUCCESS};
            color: #FFFFFF;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: bold;
            padding: 14px 32px;
        }}
        #generateProtocolBtn:hover {{
            background-color: {c.SUCCESS};
        }}
        #generateProtocolBtn:pressed {{
            background-color: {c.SUCCESS};
            padding-top: 15px;
            padding-bottom: 13px;
        }}

        /* ============ SingleWorkerProtocolTab ============ */
        #workerFormCard {{
            background-color: {c.SURFACE_BG};
            border: 1px solid {c.BORDER_INPUT if theme == "dark" else c.BORDER_LIGHT};
            border-radius: 10px;
        }}
        #programHelpBtn {{
            background-color: {c.SURFACE_BG};
            color: {c.PRIMARY};
            border: 1px solid {c.PRIMARY};
            border-radius: 6px;
            padding: 5px 14px;
            font-weight: normal;
        }}
        #programHelpBtn:hover {{
            background-color: {highlight_bg};
        }}
        #previewLabel {{
            color: {c.TEXT_SECONDARY};
            font-size: 12px;
            padding: 2px 4px;
            background-color: transparent;
        }}

        /* ============ ProtocolTab programs tab ============ */
        #programsHint {{
            color: {c.TEXT_SECONDARY};
            font-size: 12px;
            padding: 4px 0;
            background-color: transparent;
        }}
        #programsTable {{
            background-color: {c.INPUT_BG};
            alternate-background-color: {c.TABLE_ALTERNATE};
            border: 1px solid {c.BORDER_INPUT if theme == "dark" else c.BORDER_LIGHT};
            border-radius: 8px;
            gridline-color: {c.BORDER_INPUT if theme == "dark" else "rgba(0,0,0,0.08)"};
        }}
        #programsTable::item {{
            padding: 6px 8px;
            background-color: transparent;
            color: {c.TEXT_PRIMARY};
        }}
        #programsTable::item:selected {{
            background-color: {highlight_sel};
            color: {c.TEXT_PRIMARY};
        }}
        #saveProgramsBtn {{
            background-color: {primary_hex};
            color: #FFFFFF;
            border: none;
            padding: 8px 22px;
        }}
        #saveProgramsBtn:hover {{
            background-color: {primary_hex};
        }}

        /* ============ EmployeeSummaryTab ============ */
        /* Stats cards */
        #statsContainer QFrame {{
            border-radius: 10px;
            padding: 4px;
            min-height: 80px;
        }}
        #statCardBlue {{
            background-color: {c.SURFACE_BG};
            border: 2px solid {primary_hex};
        }}
        #statCardGreen {{
            background-color: {c.SURFACE_BG};
            border: 2px solid {c.SUCCESS};
        }}
        #statCardRed {{
            background-color: {c.SURFACE_BG};
            border: 2px solid {c.ERROR};
        }}
        #statCardYellow {{
            background-color: {c.SURFACE_BG};
            border: 2px solid {c.WARNING};
        }}
        #statCardInfo {{
            background-color: {c.SURFACE_BG};
            border: 2px solid #17a2b8;
        }}
        #statValue {{
            font-size: 26px;
            font-weight: bold;
            color: {c.TEXT_PRIMARY};
            background-color: transparent;
        }}
        #statValueGreen {{
            font-size: 26px;
            font-weight: bold;
            color: {c.SUCCESS};
            background-color: transparent;
        }}
        #statValueRed {{
            font-size: 26px;
            font-weight: bold;
            color: {c.ERROR};
            background-color: transparent;
        }}
        #statValueYellow {{
            font-size: 26px;
            font-weight: bold;
            color: {c.WARNING};
            background-color: transparent;
        }}
        #statValueInfo {{
            font-size: 20px;
            font-weight: bold;
            color: #17a2b8;
            background-color: transparent;
        }}
        #statLabel {{
            font-size: 14px;
            font-weight: bold;
            color: {c.TEXT_SECONDARY};
            background-color: transparent;
        }}

        /* Toolbar */
        #toolbarContainer {{
            background-color: transparent;
        }}
        #toolbarPrimaryBtn {{
            background-color: {primary_hex};
            color: #FFFFFF;
            border: none;
            border-radius: 6px;
            padding: 7px 16px;
            font-weight: bold;
        }}
        #toolbarPrimaryBtn:hover {{
            background-color: {primary_hex};
        }}
        #toolbarBtn {{
            background-color: {c.SURFACE_BG};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER_INPUT if theme == "dark" else c.BORDER_LIGHT};
            border-radius: 6px;
            padding: 7px 14px;
        }}
        #toolbarBtn:hover {{
            background-color: {highlight_bg};
            border-color: {c.PRIMARY};
        }}
        #toolbarSuccessBtn {{
            background-color: {c.SUCCESS};
            color: #FFFFFF;
            border: none;
            border-radius: 6px;
            padding: 7px 16px;
            font-weight: bold;
        }}
        #toolbarSuccessBtn:hover {{
            background-color: {c.SUCCESS};
        }}
        #toolbarPurpleBtn {{
            background-color: #6f42c1;
            color: #FFFFFF;
            border: none;
            border-radius: 6px;
            padding: 7px 16px;
            font-weight: bold;
        }}
        #toolbarPurpleBtn:hover {{
            background-color: #5a32a3;
        }}
        #toolbarDangerBtn {{
            background-color: transparent;
            color: {c.ERROR};
            border: 1.5px solid {c.ERROR};
            border-radius: 6px;
            padding: 7px 16px;
            font-weight: bold;
        }}
        #toolbarDangerBtn:hover {{
            background-color: {c.ERROR}22;
        }}
        #toolbarDangerBtn:pressed {{
            background-color: {c.ERROR}44;
        }}

        /* Filter panel */
        #filterContainer {{
            background-color: {c.SURFACE_BG};
            border: 1px solid {c.BORDER_INPUT if theme == "dark" else c.BORDER_LIGHT};
            border-radius: 8px;
        }}
        #filterContainer QLabel {{
            font-size: 12px;
            color: {c.TEXT_SECONDARY};
            background-color: transparent;
        }}
        #filterCombo {{
            background-color: {c.INPUT_BG};
            border: 1px solid {c.BORDER_INPUT if theme == "dark" else "#CCCCCC"};
            border-radius: 6px;
            padding: 4px 10px;
            color: {c.TEXT_PRIMARY};
            min-width: 100px;
        }}
        #filterInput {{
            background-color: {c.INPUT_BG};
            border: 1px solid {c.BORDER_INPUT if theme == "dark" else "#CCCCCC"};
            border-radius: 6px;
            padding: 4px 10px;
            color: {c.TEXT_PRIMARY};
            min-width: 140px;
        }}
        #filterCheck {{
            color: {c.TEXT_PRIMARY};
            spacing: 4px;
        }}
        #planBtn {{
            background-color: {primary_hex};
            color: #FFFFFF;
            border: none;
            border-radius: 6px;
            padding: 5px 12px;
            font-size: 12px;
        }}
        #planBtn:hover {{
            background-color: {primary_hex};
        }}
        #planBtnInfo {{
            background-color: #17a2b8;
            color: #FFFFFF;
            border: none;
            border-radius: 6px;
            padding: 5px 12px;
            font-size: 12px;
        }}
        #planBtnInfo:hover {{
            background-color: #138496;
        }}
        #planBtnSuccess {{
            background-color: {c.SUCCESS};
            color: #FFFFFF;
            border: none;
            border-radius: 6px;
            padding: 5px 12px;
            font-size: 12px;
        }}
        #planBtnSuccess:hover {{
            background-color: {c.SUCCESS};
        }}

        /* Summary table */
        #summaryTable {{
            background-color: {c.INPUT_BG};
            alternate-background-color: {c.TABLE_ALTERNATE};
            border: 1px solid {c.BORDER_INPUT if theme == "dark" else c.BORDER_LIGHT};
            border-radius: 8px;
            gridline-color: {c.BORDER_INPUT if theme == "dark" else "rgba(0,0,0,0.08)"};
        }}
        #summaryTable::item {{
            padding: 4px 6px;
            background-color: transparent;
            color: {c.TEXT_PRIMARY};
        }}
        #summaryTable::item:selected {{
            background-color: {highlight_sel};
            color: {c.TEXT_PRIMARY};
        }}

        /* Dialog helper buttons */
        #dialogPrimaryBtn {{
            background-color: {primary_hex};
            color: #FFFFFF;
            border: none;
            border-radius: 6px;
            padding: 7px 18px;
            font-weight: bold;
        }}
        #dialogDangerBtn {{
            background-color: transparent;
            color: {c.ERROR};
            border: 1.5px solid {c.ERROR};
            border-radius: 6px;
            padding: 7px 18px;
            font-weight: bold;
        }}
        #dialogDangerBtn:hover {{
            background-color: {c.ERROR}22;
        }}

        /* Plan dialog */
        #planExportBtn {{
            background-color: {primary_hex};
            color: #FFFFFF;
            border: none;
            border-radius: 6px;
            padding: 7px 18px;
            font-weight: bold;
        }}
        #planCloseBtn {{
            background-color: transparent;
            color: {c.ERROR};
            border: 1.5px solid {c.ERROR};
            border-radius: 6px;
            padding: 7px 18px;
            font-weight: bold;
        }}

        #planStatCard {{
            background-color: {c.SURFACE_BG};
        }}

        /* Context menu */
        #summaryCtxMenu {{
            background-color: {c.MENU_BG};
            border: 1px solid {c.BORDER_INPUT if theme == "dark" else c.BORDER_LIGHT};
            border-radius: 6px;
            padding: 4px;
        }}
        #summaryCtxMenu::item {{
            padding: 6px 24px 6px 12px;
            border-radius: 4px;
            color: {c.TEXT_PRIMARY};
        }}
        #summaryCtxMenu::item:selected {{
            background-color: {highlight_bg};
        }}

        /* ============ QLineEdit ============ */
        QLineEdit {{
            background-color: {c.INPUT_BG};
            border: 1px solid {c.BORDER_INPUT if theme == "dark" else "#CCCCCC"};
            border-radius: 6px;
            padding: 7px 12px;
            color: {c.TEXT_PRIMARY};
            selection-background-color: {primary_hex};
            selection-color: #FFFFFF;
        }}
        QLineEdit:hover {{
            border-color: {c.BORDER_INPUT if theme == "dark" else "#999"};
        }}
        QLineEdit:focus {{
            border-color: {c.PRIMARY};
            border-width: 2px;
        }}
        QLineEdit:read-only {{
            background-color: {c.SURFACE_BG};
            color: {c.TEXT_SECONDARY};
        }}
        QLineEdit:disabled {{
            background-color: {c.SURFACE_BG};
            color: {c.TEXT_DISABLED if theme == "dark" else "#999"};
            border-color: {c.BORDER_LIGHT};
        }}

        /* ============ QComboBox ============ */
        QComboBox {{
            background-color: {c.INPUT_BG};
            border: 1px solid {c.BORDER_INPUT if theme == "dark" else "#CCCCCC"};
            border-radius: 6px;
            padding: 6px 12px;
            color: {c.TEXT_PRIMARY};
            min-height: 20px;
        }}
        QComboBox:hover {{
            border-color: {c.PRIMARY};
        }}
        QComboBox:focus {{
            border-color: {c.PRIMARY};
            border-width: 2px;
        }}
        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {c.SURFACE_BG};
            border: 1px solid {c.BORDER_INPUT if theme == "dark" else "#CCCCCC"};
            border-radius: 6px;
            selection-background-color: {highlight_bg};
            selection-color: {c.TEXT_PRIMARY};
            padding: 4px;
            outline: none;
        }}
        QComboBox QAbstractItemView::item {{
            padding: 6px 10px;
            border-radius: 4px;
            color: {c.TEXT_PRIMARY};
        }}
        QComboBox QAbstractItemView::item:selected {{
            background-color: {highlight_sel};
            color: {c.TEXT_PRIMARY};
        }}

        /* ============ QDateEdit ============ */
        QDateEdit {{
            background-color: {c.INPUT_BG};
            border: 1px solid {c.BORDER_INPUT if theme == "dark" else "#CCCCCC"};
            border-radius: 6px;
            padding: 6px 12px;
            color: {c.TEXT_PRIMARY};
            min-height: 20px;
        }}
        QDateEdit:hover {{
            border-color: {c.BORDER_INPUT if theme == "dark" else "#999"};
        }}
        QDateEdit:focus {{
            border-color: {c.PRIMARY};
            border-width: 2px;
        }}
        QDateEdit::drop-down {{
            border: none;
            width: 24px;
        }}
        QDateEdit::down-arrow {{
            image: none;
        }}

        /* ============ QSpinBox ============ */
        QSpinBox {{
            background-color: {c.INPUT_BG};
            border: 1px solid {c.BORDER_INPUT if theme == "dark" else "#CCCCCC"};
            border-radius: 6px;
            padding: 6px 12px;
            color: {c.TEXT_PRIMARY};
            min-height: 20px;
        }}
        QSpinBox:hover {{
            border-color: {c.BORDER_INPUT if theme == "dark" else "#999"};
        }}
        QSpinBox:focus {{
            border-color: {c.PRIMARY};
            border-width: 2px;
        }}

        /* ============ QCheckBox / QRadioButton ============ */
        QCheckBox, QRadioButton {{
            color: {c.TEXT_PRIMARY};
            spacing: 6px;
        }}
        QCheckBox::indicator, QRadioButton::indicator {{
            border: 2px solid {c.BORDER_INPUT if theme == "dark" else "#888"};
            border-radius: 3px;
            width: 16px;
            height: 16px;
        }}
        QCheckBox::indicator:hover,
        QRadioButton::indicator:hover {{
            border-color: {c.PRIMARY};
        }}
        QCheckBox::indicator:checked {{
            background-color: {primary_hex};
            border-color: {primary_hex};
        }}
        QRadioButton::indicator {{
            border-radius: 9px;
        }}
        QRadioButton::indicator:checked {{
            background-color: {primary_hex};
            border-color: {primary_hex};
        }}

        /* ============ QTableWidget ============ */
        QTableWidget {{
            background-color: {c.INPUT_BG};
            alternate-background-color: {c.TABLE_ALTERNATE};
            border: 1px solid {c.BORDER_INPUT if theme == "dark" else c.BORDER_LIGHT};
            border-radius: 8px;
            gridline-color: {c.BORDER_INPUT if theme == "dark" else "rgba(0,0,0,0.08)"};
            color: {c.TEXT_PRIMARY};
            selection-background-color: {highlight_sel};
            selection-color: {c.TEXT_PRIMARY};
        }}
        QTableWidget::item {{
            padding: 6px 8px;
            background-color: transparent;
            color: {c.TEXT_PRIMARY};
        }}
        QTableWidget::item:selected {{
            background-color: {highlight_sel};
            color: {c.TEXT_PRIMARY};
        }}
        QHeaderView::section {{
            background-color: {c.SURFACE_BG};
            color: {c.PRIMARY};
            padding: 8px 10px;
            border: none;
            border-bottom: 1px solid {c.BORDER_INPUT if theme == "dark" else "rgba(0,0,0,0.08)"};
            border-right: 1px solid {c.BORDER_LIGHT};
            font-weight: bold;
            font-size: 12px;
        }}
        QHeaderView::section:first {{
            border-top-left-radius: 8px;
        }}
        QHeaderView::section:last {{
            border-top-right-radius: 8px;
            border-right: none;
        }}
        QHeaderView::section:hover {{
            background-color: {highlight_bg};
        }}

        /* ============ QLabel ============ */
        QLabel {{
            background-color: transparent;
            color: {c.TEXT_PRIMARY};
        }}

        /* ============ QTabWidget / QTabBar ============ */
        QTabWidget::pane {{
            border: none;
            background: transparent;
        }}
        QTabBar::tab {{
            background-color: transparent;
            color: {c.TEXT_SECONDARY};
            padding: 10px 22px;
            border: none;
            border-bottom: 2px solid transparent;
            font-weight: bold;
            margin-right: 2px;
        }}
        QTabBar::tab:selected {{
            color: {c.PRIMARY};
            border-bottom: 2px solid {c.PRIMARY};
            background-color: {highlight_bg};
        }}
        QTabBar::tab:hover:!selected {{
            color: {c.TEXT_PRIMARY};
            border-bottom: 2px solid {c.BORDER_INPUT if theme == "dark" else "transparent"};
            background-color: {c.GLASS_DARK if theme == "dark" else "rgba(0,0,0,0.03)"};
        }}

        /* ============ QListWidget ============ */
        QListWidget {{
            background-color: {c.INPUT_BG};
            border: 1px solid {c.BORDER_INPUT if theme == "dark" else c.BORDER_LIGHT};
            border-radius: 8px;
            color: {c.TEXT_PRIMARY};
        }}
        QListWidget::item {{
            padding: 8px 12px;
            border-radius: 6px;
            color: {c.TEXT_PRIMARY};
        }}
        QListWidget::item:selected {{
            background-color: {highlight_sel};
            color: {c.TEXT_PRIMARY};
        }}
        QListWidget::item:hover {{
            background-color: {highlight_bg};
        }}

        /* ============ QTextEdit / QPlainTextEdit ============ */
        QTextEdit, QPlainTextEdit {{
            background-color: {c.INPUT_BG};
            border: 1px solid {c.BORDER_INPUT if theme == "dark" else c.BORDER_LIGHT};
            border-radius: 8px;
            padding: 10px;
            color: {c.TEXT_PRIMARY};
            selection-background-color: {primary_hex};
            selection-color: #FFFFFF;
        }}

        /* ============ QScrollBar ============ */
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
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
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
        QScrollBar::add-line:horizontal,
        QScrollBar::sub-line:horizontal {{
            width: 0;
        }}

        /* ============ QMenu / QMenuBar ============ */
        QMenuBar {{
            background-color: {c.MENU_BG};
            border-bottom: 1px solid {c.BORDER_LIGHT};
            color: {c.TEXT_PRIMARY};
        }}
        QMenuBar::item {{
            padding: 6px 14px;
            border-radius: 4px;
            color: {c.TEXT_PRIMARY};
        }}
        QMenuBar::item:selected {{
            background-color: {highlight_bg};
        }}
        QMenu {{
            background-color: {c.MENU_BG};
            border: 1px solid {c.BORDER_INPUT if theme == "dark" else c.BORDER_LIGHT};
            border-radius: 8px;
            padding: 6px;
            color: {c.TEXT_PRIMARY};
        }}
        QMenu::item {{
            padding: 7px 24px 7px 14px;
            border-radius: 4px;
            color: {c.TEXT_PRIMARY};
        }}
        QMenu::item:selected {{
            background-color: {highlight_bg};
        }}
        QMenu::item:disabled {{
            color: {c.TEXT_DISABLED if theme == "dark" else "#999"};
        }}
        QMenu::separator {{
            height: 1px;
            background-color: {c.BORDER_INPUT if theme == "dark" else "rgba(0,0,0,0.08)"};
            margin: 4px 8px;
        }}

        /* ============ QToolTip ============ */
        QToolTip {{
            background-color: {c.SURFACE_BG};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER_INPUT if theme == "dark" else "#CCC"};
            border-radius: 4px;
            padding: 4px 8px;
        }}
        QProgressBar {{
            background-color: {c.INPUT_BG};
            border: 1px solid {c.BORDER_INPUT if theme == "dark" else "#CCC"};
            border-radius: 4px;
            text-align: center;
            color: {c.TEXT_PRIMARY};
            height: 20px;
        }}
        QProgressBar::chunk {{
            background-color: {primary_hex};
            border-radius: 3px;
        }}

        /* ============ QCalendarWidget ============ */
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
            border-radius: 4px;
            padding: 4px;
        }}
        QCalendarWidget QToolButton:hover {{
            background-color: {highlight_bg};
        }}
        QCalendarWidget QSpinBox {{
            background-color: {c.INPUT_BG};
            border: 1px solid {c.BORDER_INPUT if theme == "dark" else "#CCC"};
            border-radius: 4px;
            padding: 2px 6px;
            color: {c.TEXT_PRIMARY};
        }}

        /* ============ QMessageBox ============ */
        QMessageBox {{
            background-color: {c.WINDOW_BG};
        }}
        QMessageBox QLabel {{
            color: {c.TEXT_PRIMARY};
            background-color: transparent;
        }}
        QMessageBox QPushButton {{
            min-width: 80px;
        }}
        QMessageBox QPushButton,
        QFileDialog QPushButton,
        QInputDialog QPushButton {{
            background-color: {c.SURFACE_BG};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER_INPUT if theme == "dark" else "#CCC"};
            border-radius: 8px;
            padding: 6px 18px;
            font-weight: bold;
            min-height: 24px;
        }}
        QMessageBox QPushButton:hover,
        QFileDialog QPushButton:hover,
        QInputDialog QPushButton:hover {{
            background-color: {highlight_bg};
            border-color: {c.PRIMARY};
        }}

        /* ============ Generic QDialog (for custom dialogs) ============ */
        QDialog {{
            background-color: {c.WINDOW_BG};
        }}
        QDialog QLabel {{
            color: {c.TEXT_PRIMARY};
            background-color: transparent;
        }}
        QDialog QLineEdit {{
            color: {c.TEXT_PRIMARY};
        }}

        /* ============ AboutDialog ============ */
        #aboutTitleLabel {{
            font-size: 16px;
            font-weight: bold;
            color: {c.PRIMARY};
            background-color: transparent;
        }}
        #aboutVersionLabel {{
            font-size: 12px;
            color: {c.TEXT_SECONDARY};
            background-color: transparent;
        }}
        #aboutDescLabel {{
            font-size: 13px;
            color: {c.TEXT_PRIMARY};
            line-height: 1.6;
            padding: 8px 0;
            background-color: transparent;
        }}
        #aboutInfoWidget {{
            background-color: {c.SURFACE_BG};
            border: 1px solid {c.BORDER_LIGHT};
            border-radius: 10px;
        }}
        #aboutInfoLabel {{
            font-size: 13px;
            color: {c.TEXT_PRIMARY};
            background-color: transparent;
        }}
        #aboutInfoLink {{
            font-size: 13px;
            color: {c.PRIMARY};
            background-color: transparent;
        }}
        #aboutInfoLink:hover {{
            color: {primary_hex};
        }}

        /* ============ Report dialog titles ============ */
        #reportTitleLabel {{
            font-size: 16px;
            font-weight: bold;
            color: {c.PRIMARY};
            padding: 4px 0;
        }}

        /* ============ HelpDialog ============ */
        #helpGroupBox {{
            background-color: {c.SURFACE_BG};
            border: 1px solid {c.BORDER_LIGHT};
            border-radius: 10px;
            margin-top: 14px;
            padding: 18px 16px 16px 16px;
            font-weight: bold;
            font-size: 14px;
            color: {c.PRIMARY};
        }}
        #helpGroupBox::title {{
            subcontrol-origin: margin;
            left: 14px;
            padding: 0 8px;
            color: {c.PRIMARY};
            font-weight: bold;
            font-size: 15px;
        }}
        #helpGroupLabel {{
            font-size: 13px;
            color: {c.TEXT_PRIMARY};
            line-height: 1.5;
            padding: 2px 0;
            background-color: transparent;
        }}

        /* ============ QFileDialog ============ */
        QFileDialog {{
            background-color: {c.WINDOW_BG};
        }}
        QFileDialog QLabel {{
            color: {c.TEXT_PRIMARY};
            background-color: transparent;
        }}
        QFileDialog QListView,
        QFileDialog QTreeView {{
            background-color: {c.INPUT_BG};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER_INPUT if theme == "dark" else "#CCC"};
            border-radius: 6px;
        }}

        /* ============ QInputDialog ============ */
        QInputDialog {{
            background-color: {c.WINDOW_BG};
        }}
        QInputDialog QLabel {{
            color: {c.TEXT_PRIMARY};
            background-color: transparent;
        }}

        /* ============ Dialog children fallback ============ */
        QDialog QTableWidget {{
            background-color: {c.INPUT_BG};
            alternate-background-color: {c.TABLE_ALTERNATE};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER_INPUT if theme == "dark" else "#CCC"};
            border-radius: 8px;
            gridline-color: {c.BORDER_INPUT if theme == "dark" else "rgba(0,0,0,0.08)"};
        }}
        QDialog QTableWidget::item {{
            background-color: transparent;
            color: {c.TEXT_PRIMARY};
        }}
        QDialog QTableWidget::item:selected {{
            background-color: {highlight_sel};
            color: {c.TEXT_PRIMARY};
        }}
        QDialog QListWidget {{
            background-color: {c.INPUT_BG};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER_INPUT if theme == "dark" else "#CCC"};
            border-radius: 8px;
        }}
        QDialog QListWidget::item {{
            color: {c.TEXT_PRIMARY};
        }}
        QDialog QListWidget::item:selected {{
            background-color: {highlight_sel};
            color: {c.TEXT_PRIMARY};
        }}
        QDialog QTextEdit,
        QDialog QLineEdit {{
            background-color: {c.INPUT_BG};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER_INPUT if theme == "dark" else "#CCC"};
            border-radius: 6px;
            padding: 7px 12px;
        }}
        QDialog QLineEdit:hover,
        QDialog QComboBox:hover {{
            border-color: {c.BORDER_INPUT if theme == "dark" else "#999"};
        }}
        QDialog QComboBox {{
            background-color: {c.INPUT_BG};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER_INPUT if theme == "dark" else "#CCC"};
            border-radius: 6px;
            padding: 6px 12px;
        }}

        /* ============ QStatusBar ============ */
        QStatusBar {{
            background-color: {c.SURFACE_BG};
            border-top: 1px solid {c.BORDER_LIGHT};
            color: {c.TEXT_SECONDARY};
            font-size: 12px;
            padding: 2px 8px;
        }}
        QStatusBar::item {{
            border: none;
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

from PySide6.QtWidgets import QFrame, QPushButton, QVBoxLayout, QLabel
from PySide6.QtCore import Qt


class GlassCard(QFrame):
    """Glass-карточка с acrylic-эффектом (имитация через полупрозрачность)."""

    def __init__(self, parent=None, title: str = "", elevation: int = 1):
        super().__init__(parent)
        self._title = title
        self._elevation = elevation
        self._init_ui()

    def _init_ui(self):
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                border: 1px solid rgba(74, 144, 226, 0.15);
                border-radius: 12px;
            }
        """)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(12)

        if self._title:
            title_label = QLabel(self._title)
            title_label.setStyleSheet("""
                color: #4A90E2;
                font-weight: bold;
                font-size: 15px;
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
