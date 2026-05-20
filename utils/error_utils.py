import logging
import traceback
from typing import Optional

from PySide6.QtWidgets import QWidget, QMessageBox, QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout, QApplication
from PySide6.QtCore import Qt


logger = logging.getLogger(__name__)


def show_error_dialog(
    parent: Optional[QWidget],
    title: str,
    message: str,
    details: Optional[str] = None,
    critical: bool = False,
) -> None:
    """Централизованное отображение ошибок пользователю."""
    icon = QMessageBox.Icon.Critical if critical else QMessageBox.Icon.Warning
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(message)
    box.setTextFormat(Qt.TextFormat.RichText if '<' in message else Qt.TextFormat.AutoText)

    if details:
        box.setDetailedText(details)

    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    box.exec()


def show_exception_dialog(parent: Optional[QWidget], title: str, message: str, exc: BaseException) -> None:
    """Показывает диалог с исключением и деталями traceback."""
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logger.error(f"{message}: {exc}\n{tb}")
    show_error_dialog(parent, title, message, details=tb, critical=True)


class DetailsDialog(QDialog):
    """Диалог с подробным текстом (для логов, отчётов)."""

    def __init__(self, parent: Optional[QWidget], title: str, text: str, min_width: int = 700, min_height: int = 500):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(min_width, min_height)
        self.resize(min_width, min_height)

        layout = QVBoxLayout(self)
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(text)
        text_edit.setStyleSheet("font-family: Consolas, monospace; font-size: 12px;")
        layout.addWidget(text_edit)

        btn_layout = QHBoxLayout()
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)

        copy_btn = QPushButton("Копировать")
        def _copy():
            QApplication.clipboard().setText(text)
            close_btn.setText("Скопировано ✓")
        copy_btn.clicked.connect(_copy)

        btn_layout.addWidget(copy_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
