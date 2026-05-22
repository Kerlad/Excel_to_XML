"""
Clipboard guard — auto-clears clipboard after 30 seconds.
"""
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication


class ClipboardGuard:
    _timer: QTimer = None

    @classmethod
    def start(cls, timeout_ms: int = 30000):
        if cls._timer is not None and cls._timer.isActive():
            cls._timer.stop()
        cls._timer = QTimer()
        cls._timer.setSingleShot(True)
        cls._timer.timeout.connect(cls._clear)
        QApplication.clipboard().dataChanged.connect(cls._reset_timer)

    @classmethod
    def _reset_timer(cls):
        if cls._timer is not None:
            cls._timer.start()

    @classmethod
    def _clear(cls):
        QApplication.clipboard().clear()
