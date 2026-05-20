from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QRect
from PySide6.QtGui import QScreen


class Toast(QWidget):
    TYPE_INFO = 0
    TYPE_SUCCESS = 1
    TYPE_WARNING = 2
    TYPE_ERROR = 3

    _COLORS = {
        TYPE_INFO: ("#3498DB", "#2980B9"),
        TYPE_SUCCESS: ("#27AE60", "#1E8449"),
        TYPE_WARNING: ("#F39C12", "#D68910"),
        TYPE_ERROR: ("#E74C3C", "#C0392B"),
    }

    _ACTIVE_TOASTS = []

    def __init__(self, parent: QWidget, message: str, toast_type: int = TYPE_INFO, duration_ms: int = 3500):
        super().__init__(parent)
        self._duration = duration_ms
        self._parent_widget = parent
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        bg, accent = self._COLORS.get(toast_type, self._COLORS[self.TYPE_INFO])
        self.setStyleSheet(f"""
            Toast {{ background-color: {bg}; border-radius: 8px; }}
            QLabel#toastText {{ color: white; font-size: 13px; padding: 12px 20px; }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)

        icon_map = {self.TYPE_INFO: "i", self.TYPE_SUCCESS: "✓", self.TYPE_WARNING: "⚠", self.TYPE_ERROR: "✗"}
        icon_label = QLabel(icon_map.get(toast_type, ""))
        icon_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: white; padding-left: 12px;")
        icon_label.setFixedWidth(30)
        layout.addWidget(icon_label)

        label = QLabel(message)
        label.setObjectName("toastText")
        label.setWordWrap(True)
        layout.addWidget(label, 1)

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._opacity_effect.setOpacity(0.95)

        self.adjustSize()
        Toast._ACTIVE_TOASTS.append(self)
        self._schedule_show()

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
        anim.setStartValue(0.95)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        anim.finished.connect(self._remove_and_close)
        anim.start()

    def _remove_and_close(self):
        if self in Toast._ACTIVE_TOASTS:
            Toast._ACTIVE_TOASTS.remove(self)
        self.close()
        self.deleteLater()

    @classmethod
    def show_message(cls, parent: QWidget, message: str, toast_type: int = TYPE_INFO, duration_ms: int = 3500):
        t = cls(parent, message, toast_type, duration_ms)

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
