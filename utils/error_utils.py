"""
Centralized error display utilities.
Safe exception handling - no PII in user-facing dialogs.
"""
import logging
from typing import Optional

from PySide6.QtWidgets import QWidget, QMessageBox, QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout, QApplication
from PySide6.QtCore import Qt

from utils.clipboard_guard import ClipboardGuard
from utils.logger import filter_sensitive_text

logger = logging.getLogger(__name__)


def show_error_dialog(
    parent: Optional[QWidget],
    title: str,
    message: str,
    details: Optional[str] = None,
    critical: bool = False,
) -> None:
    icon = QMessageBox.Icon.Critical if critical else QMessageBox.Icon.Warning
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    sanitized_msg = filter_sensitive_text(message)
    box.setText(sanitized_msg)
    box.setTextFormat(Qt.TextFormat.RichText if '<' in sanitized_msg else Qt.TextFormat.AutoText)

    if details:
        sanitized_details = filter_sensitive_text(details)
        box.setDetailedText(sanitized_details)

    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    box.exec()


def show_exception_dialog(parent: Optional[QWidget], title: str, message: str, exc: BaseException) -> None:
    """Show exception dialog with sanitized traceback (no PII)."""
    safe_msg = filter_sensitive_text(str(exc)[:200])
    logger.error("%s: %s", message, safe_msg)
    show_error_dialog(
        parent, title,
        filter_sensitive_text(message),
        details=f"Тип ошибки: {type(exc).__name__}\nОписание: {safe_msg}",
        critical=True
    )


def safe_message_box(
    parent: Optional[QWidget],
    icon: QMessageBox.Icon,
    title: str,
    text: str,
    detailed_text: Optional[str] = None,
) -> None:
    """QMessageBox wrapper that automatically sanitizes all text via filter_sensitive_text()."""
    safe_text = filter_sensitive_text(text)
    safe_details = filter_sensitive_text(detailed_text) if detailed_text else None
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(safe_text)
    if safe_details:
        box.setDetailedText(safe_details)
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    box.exec()


class DetailsDialog(QDialog):
    def __init__(self, parent: Optional[QWidget], title: str, text: str, min_width: int = 700, min_height: int = 500):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(min_width, min_height)
        self.resize(min_width, min_height)

        layout = QVBoxLayout(self)
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(filter_sensitive_text(text))
        text_edit.setStyleSheet("font-family: Consolas, monospace; font-size: 12px;")
        layout.addWidget(text_edit)

        btn_layout = QHBoxLayout()
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)

        copy_btn = QPushButton("Копировать")
        def _copy():
            ClipboardGuard.mark_own_copy()
            QApplication.clipboard().setText(filter_sensitive_text(text))
            copy_btn.setText("Скопировано ✓")
        copy_btn.clicked.connect(_copy)

        btn_layout.addWidget(copy_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
