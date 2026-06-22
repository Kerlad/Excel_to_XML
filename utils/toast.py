"""
Неблокирующие всплывающие уведомления (toast).

Фон рисуется через QPainter (drawRoundedRect), а не через QSS на полупрозрачном
top-level окне — это устраняет известный баг "белый текст на прозрачном фоне"
на Windows и гарантирует читаемость в светлой и тёмной теме.
"""
from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QRectF
from PySide6.QtGui import QPainter, QColor, QBrush


class Toast(QWidget):
    TYPE_INFO = 0
    TYPE_SUCCESS = 1
    TYPE_WARNING = 2
    TYPE_ERROR = 3

    # Один непрозрачный цвет фона на тип уведомления.
    _COLORS = {
        TYPE_INFO: "#3498DB",
        TYPE_SUCCESS: "#27AE60",
        TYPE_WARNING: "#F39C12",
        TYPE_ERROR: "#E74C3C",
    }

    _ICONS = {
        TYPE_INFO: "\u2139",
        TYPE_SUCCESS: "\u2713",
        TYPE_WARNING: "\u26A0",
        TYPE_ERROR: "\u2715",
    }

    _ACTIVE_TOASTS = []

    def __init__(self, parent: QWidget, message: str, toast_type: int = TYPE_INFO, duration_ms: int = 3500):
        super().__init__(parent)
        self._duration = duration_ms
        self._parent_widget = parent
        self._bg_color = QColor(self._COLORS.get(toast_type, self._COLORS[self.TYPE_INFO]))

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 18, 12)
        layout.setSpacing(10)

        icon_label = QLabel(self._ICONS.get(toast_type, ""))
        icon_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: white; background: transparent;"
        )
        icon_label.setFixedWidth(22)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        label = QLabel(message)
        label.setObjectName("toastText")
        label.setWordWrap(True)
        label.setMaximumWidth(360)
        label.setStyleSheet(
            "color: white; background: transparent; font-size: 13px; font-weight: 600;"
        )
        layout.addWidget(label, 1)

        self.setMaximumWidth(420)

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._opacity_effect.setOpacity(0.97)

        self.adjustSize()
        Toast._ACTIVE_TOASTS.append(self)
        self._schedule_show()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0.0, 0.0, float(self.width()), float(self.height()))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self._bg_color))
        painter.drawRoundedRect(rect, 10.0, 10.0)
        super().paintEvent(event)

    def _schedule_show(self):
        QTimer.singleShot(50, self._position_and_show)

    def _position_and_show(self):
        self.show()
        self.raise_()
        parent_rect = self._parent_widget.rect()
        parent_tl = self._parent_widget.mapToGlobal(QPoint(0, 0))
        parent_width = parent_rect.width()

        offset_y = 20
        for t in Toast._ACTIVE_TOASTS:
            if t is not self and t.isVisible():
                offset_y += t.height() + 8

        x = parent_tl.x() + (parent_width - self.width()) // 2
        y = parent_tl.y() + offset_y
        self.move(x, y)

        QTimer.singleShot(self._duration, self._fade_out)

    def _fade_out(self):
        anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        anim.setDuration(500)
        anim.setStartValue(0.97)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        anim.finished.connect(self._remove_and_close)
        anim.start()
        self._anim = anim

    def _remove_and_close(self):
        if self in Toast._ACTIVE_TOASTS:
            Toast._ACTIVE_TOASTS.remove(self)
        self.close()
        self.deleteLater()

    @classmethod
    def show_message(cls, parent: QWidget, message: str, toast_type: int = TYPE_INFO, duration_ms: int = 3500):
        cls(parent, message, toast_type, duration_ms)

    @classmethod
    def info(cls, parent: QWidget, message: str, duration_ms: int = 3500):
        cls.show_message(parent, message, cls.TYPE_INFO, duration_ms)

    @classmethod
    def success(cls, parent: QWidget, message: str, duration_ms: int = 3500):
        cls.show_message(parent, message, cls.TYPE_SUCCESS, duration_ms)

    @classmethod
    def warning(cls, parent: QWidget, message: str, duration_ms: int = 4000):
        cls.show_message(parent, message, cls.TYPE_WARNING, duration_ms)

    @classmethod
    def error(cls, parent: QWidget, message: str, duration_ms: int = 5000):
        cls.show_message(parent, message, cls.TYPE_ERROR, duration_ms)
