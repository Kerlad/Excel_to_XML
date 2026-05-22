"""
Clipboard guard — auto-clears clipboard after `timeout_ms` only for data copied from this app.
"""
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication


class ClipboardGuard:
    _timer: QTimer = None
    _our_copy: bool = False

    @classmethod
    def start(cls, timeout_ms: int = 30000):
        if cls._timer is not None and cls._timer.isActive():
            cls._timer.stop()
        cls._timer = QTimer()
        cls._timer.setSingleShot(True)
        cls._timer.timeout.connect(cls._clear)
        QApplication.clipboard().dataChanged.connect(cls._on_data_changed)

    @classmethod
    def mark_own_copy(cls):
        cls._our_copy = True

    @classmethod
    def _on_data_changed(cls):
        if cls._our_copy:
            cls._our_copy = False
            if cls._timer is not None:
                cls._timer.start()

    @classmethod
    def _clear(cls):
        QApplication.clipboard().clear()
