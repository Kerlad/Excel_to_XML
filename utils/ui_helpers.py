"""
Общие UI-хелперы (без хардкод-цветов): пометка полей через тему,
курсор ожидания для длительных операций и заглушка пустой таблицы.
"""
import logging
from contextlib import contextmanager

from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication, QLabel

logger = logging.getLogger(__name__)


def set_field_state(widget, state=None):
    """Пометить поле как 'invalid'/'warning' или сбросить (None).
    Цвет берётся из глобальной темы (см. tahoe_style), без хардкода."""
    try:
        widget.setProperty("fieldState", state or "")
        style = widget.style()
        if style is not None:
            style.unpolish(widget)
            style.polish(widget)
        widget.update()
    except Exception:
        logger.exception("set_field_state failed")


def mark_invalid(widget, invalid=True):
    set_field_state(widget, "invalid" if invalid else None)


def mark_warning(widget, warning=True):
    set_field_state(widget, "warning" if warning else None)


@contextmanager
def busy_cursor():
    """Курсор ожидания на время длительной синхронной операции."""
    QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
    try:
        QApplication.processEvents()
        yield
    finally:
        QApplication.restoreOverrideCursor()


class EmptyStateOverlay(QLabel):
    """Подсказка по центру таблицы, когда в ней нет строк."""

    def __init__(self, table, text):
        super().__init__(text, table.viewport())
        self._table = table
        self.setObjectName("tableEmptyState")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        table.viewport().installEventFilter(self)
        model = table.model()
        if model is not None:
            for sig in ("modelReset", "rowsInserted", "rowsRemoved", "layoutChanged"):
                try:
                    getattr(model, sig).connect(self._refresh)
                except Exception:
                    pass
        self._refresh()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Resize:
            self.setGeometry(obj.rect())
        return False

    def _row_count(self):
        model = self._table.model()
        return model.rowCount() if model is not None else 0

    def _refresh(self, *args):
        try:
            self.setGeometry(self._table.viewport().rect())
            self.setVisible(self._row_count() == 0)
            self.raise_()
        except Exception:
            pass
