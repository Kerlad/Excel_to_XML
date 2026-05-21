"""
Session auto-lock for PDn protection.
Locks the UI after configurable inactivity timeout.
Unlock requires passphrase (if set).
Locked screen is blurred and overlaid with semi-transparent dark layer.
"""
import os
import sys
import logging
from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QDialog, QMessageBox, QWidget, QApplication
)
from PySide6.QtCore import Qt, QTimer, QEvent, QObject, QRect
from PySide6.QtGui import QPixmap, QIcon, QPainter, QImage, QColor, QBrush, QPainterPath
from utils.crypto import verify_passphrase, is_passphrase_protected, CryptoPassphraseRequiredError
from utils.audit import log_audit
from utils.app_paths import get_resource_dir
from utils.error_utils import safe_message_box

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_MINUTES = 10
WARNING_SECONDS = 30
CHECK_INTERVAL_MS = 1000
BLUR_DOWNSCALE_FACTOR = 6
OVERLAY_OPACITY = 180


class BlurOverlay(QWidget):
    """Child overlay widget with blurred + darkened content for lock screen.
    Child of the main window so it renders correctly behind the modal LockDialog."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setGeometry(parent.rect())
        self.setStyleSheet("background: transparent;")

    def capture_and_blur(self):
        """Capture parent widget content and apply pixelation blur + dark overlay."""
        parent = self.parentWidget()
        if not parent or not parent.isVisible():
            self.setStyleSheet("background-color: rgba(0, 0, 0, 200);")
            return

        size = parent.size()
        if size.width() < 1 or size.height() < 1:
            return

        small_w = max(size.width() // BLUR_DOWNSCALE_FACTOR, 1)
        small_h = max(size.height() // BLUR_DOWNSCALE_FACTOR, 1)

        pixmap = QPixmap(size)
        pixmap.fill(Qt.transparent)
        parent.render(pixmap, QPoint(), QRegion(QRect(QPoint(0, 0), size)))

        blurred = QImage(pixmap.toImage())\
            .scaled(small_w, small_h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)\
            .scaled(size.width(), size.height(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

        result = QImage(size, QImage.Format_ARGB32)
        result.fill(Qt.transparent)

        painter = QPainter(result)
        painter.begin(result)
        painter.drawImage(QPoint(0, 0), blurred)
        painter.fillRect(QRect(QPoint(0, 0), size), QColor(0, 0, 0, OVERLAY_OPACITY))
        painter.end()

        self._bg = QPixmap.fromImage(result)
        self.setStyleSheet("background: transparent;")
        self.update()

    def paintEvent(self, event):
        if hasattr(self, '_bg') and not self._bg.isNull():
            painter = QPainter(self)
            painter.drawPixmap(QPoint(0, 0), self._bg)
            painter.end()
        else:
            super().paintEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.setGeometry(self.parentWidget().rect())
        if self.isVisible():
            self.capture_and_blur()


class LockDialog(QDialog):
    """Modal lock screen. Cannot be dismissed without valid passphrase.
    Provides Exit button to close the application without unlocking.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._unlocked = False
        self._build_ui()
        self.setStyleSheet("")

    def _build_ui(self):
        self.setWindowTitle("Сессия заблокирована")
        self.setFixedSize(440, 340)
        self.setModal(True)
        self.setWindowFlags(
            Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint
        )
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(
            "LockDialog { background-color: palette(window); }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(12)

        icon_path = os.path.join(get_resource_dir(), "resources", "ico.ico")
        icon_lbl = QLabel()
        if os.path.exists(icon_path):
            pix = QPixmap(icon_path)
            if not pix.isNull():
                icon_lbl.setPixmap(
                    pix.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
        icon_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_lbl)

        title = QLabel("Сессия заблокирована")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: palette(text); background: transparent;"
        )
        layout.addWidget(title)

        desc = QLabel(
            "Приложение было заблокировано из-за отсутствия активности.\n"
            "Введите парольную фразу для продолжения работы."
        )
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 13px; color: palette(mid); background: transparent;")
        layout.addWidget(desc)

        self.pwd_input = QLineEdit()
        self.pwd_input.setEchoMode(QLineEdit.Password)
        self.pwd_input.setPlaceholderText("Парольная фраза")
        self.pwd_input.setMinimumHeight(40)
        self.pwd_input.setStyleSheet(
            "QLineEdit { font-size: 14px; padding: 4px 12px; "
            "border: 1px solid palette(mid); border-radius: 4px; }"
            "QLineEdit:focus { border: 1px solid #27AE60; }"
        )
        self.pwd_input.returnPressed.connect(self._try_unlock)
        layout.addWidget(self.pwd_input)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.exit_btn = QPushButton("Выход")
        self.exit_btn.setMinimumHeight(40)
        self.exit_btn.setMinimumWidth(100)
        self.exit_btn.setStyleSheet(
            "QPushButton { background-color: transparent; color: palette(text); "
            "border: 1px solid palette(mid); padding: 8px 16px; "
            "border-radius: 5px; font-size: 13px; }"
            "QPushButton:hover { background-color: rgba(128, 128, 128, 40); }"
        )
        self.exit_btn.clicked.connect(self._exit_app)
        btn_row.addWidget(self.exit_btn)

        btn_row.addSpacing(12)

        self.lock_btn = QPushButton("Разблокировать")
        self.lock_btn.setMinimumHeight(40)
        self.lock_btn.setMinimumWidth(180)
        self.lock_btn.setDefault(True)
        self.lock_btn.setStyleSheet(
            "QPushButton { background-color: #27AE60; color: white; border: none; "
            "padding: 8px 24px; border-radius: 5px; font-weight: bold; font-size: 13px; }"
            "QPushButton:hover { background-color: #219A52; }"
            "QPushButton:pressed { background-color: #1E8449; }"
        )
        self.lock_btn.clicked.connect(self._try_unlock)
        btn_row.addWidget(self.lock_btn)
        layout.addLayout(btn_row)

        self.pwd_input.setFocus()

    def _try_unlock(self):
        pp = self.pwd_input.text()
        if not pp:
            self._shake_input("Введите парольную фразу")
            return
        try:
            if verify_passphrase(pp):
                self._unlocked = True
                logger.info("Session unlocked via passphrase")
                log_audit("SESSION_UNLOCK", "Unlocked via passphrase after inactivity")
                self.accept()
            else:
                self._on_wrong()
        except CryptoPassphraseRequiredError:
            self._on_wrong()

    def _on_wrong(self):
        self._shake_input("Неверная парольная фраза")
        safe_message_box(
            self, "Неверная парольная фраза",
            "Введённая парольная фраза не подходит.\n\nПопробуйте ещё раз.",
            QMessageBox.Warning
        )
        self.pwd_input.setFocus()

    def _exit_app(self):
        logger.info("Session: user chose to exit application from lock screen")
        log_audit("SESSION_LOCK", "Application closed from lock screen (exit button)")
        QApplication.quit()

    def _shake_input(self, placeholder: str):
        self.pwd_input.setStyleSheet(
            "QLineEdit { font-size: 14px; padding: 4px 12px; "
            "border: 2px solid #E74C3C; border-radius: 4px; }"
        )
        self.pwd_input.clear()
        self.pwd_input.setPlaceholderText(placeholder)
        QTimer.singleShot(2000, self._restore_input_style)

    def _restore_input_style(self):
        self.pwd_input.setStyleSheet(
            "QLineEdit { font-size: 14px; padding: 4px 12px; "
            "border: 1px solid palette(mid); border-radius: 4px; }"
            "QLineEdit:focus { border: 1px solid #27AE60; }"
        )

    def closeEvent(self, event):
        if not self._unlocked:
            event.ignore()
        else:
            super().closeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and not self._unlocked:
            event.ignore()
        else:
            super().keyPressEvent(event)

    @property
    def was_unlocked(self) -> bool:
        return self._unlocked


class LockWarningDialog(QDialog):
    """Non-modal warning shown shortly before auto-lock.
    Inherits application-wide palette and stylesheet automatically.
    """

    def __init__(self, remaining_sec: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Предупреждение")
        self.setFixedSize(420, 140)
        self.setModal(False)
        self.setWindowFlags(
            Qt.Dialog | Qt.WindowTitleHint | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        msg = QLabel(
            f"Сессия будет заблокирована через {remaining_sec} секунд\n"
            "из-за отсутствия активности."
        )
        msg.setWordWrap(True)
        msg.setAlignment(Qt.AlignCenter)
        layout.addWidget(msg)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        ok_btn = QPushButton("Продолжить работу")
        ok_btn.setMinimumHeight(36)
        ok_btn.setStyleSheet(
            "QPushButton { background-color: #2980B9; color: white; border: none; "
            "padding: 6px 16px; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background-color: #2471A3; }"
        )
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)

        self.setFocus()
        ok_btn.setFocus()


class AutoLockManager(QObject):
    """Tracks user inactivity and locks the session after timeout.

    Only activates when a passphrase is set on the master key.
    On lock, blurs and darkens the main window content behind the LockDialog.
    """

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._enabled = False
        self._timeout_minutes = DEFAULT_TIMEOUT_MINUTES
        self._last_activity = datetime.now()
        self._locked = False
        self._warning_shown = False
        self._warning_dialog: QWidget = None
        self._blur_overlay: BlurOverlay = None

        self._timer = QTimer(self)
        self._timer.setInterval(CHECK_INTERVAL_MS)
        self._timer.timeout.connect(self._check_idle)
        self._timer.start()

        self._check_passphrase_state()

    def _check_passphrase_state(self):
        self._enabled = is_passphrase_protected()
        if not self._enabled:
            logger.info(
                "AutoLock disabled: no passphrase set on master key. "
                "Set a passphrase via About dialog to enable."
            )

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value
        if not value:
            self._warning_shown = False
            self._last_activity = datetime.now()

    @property
    def timeout_minutes(self) -> int:
        return self._timeout_minutes

    @timeout_minutes.setter
    def timeout_minutes(self, minutes: int):
        self._timeout_minutes = max(1, min(minutes, 120))
        self._last_activity = datetime.now()
        self._warning_shown = False

    def refresh(self):
        """Re-check passphrase state (call after passphrase changes)."""
        self._check_passphrase_state()
        self._warning_shown = False
        self._last_activity = datetime.now()

    def reset_timer(self):
        if not self._enabled:
            return
        self._last_activity = datetime.now()
        self._warning_shown = False

    def eventFilter(self, obj, event):
        if not self._enabled or self._locked:
            return super().eventFilter(obj, event)
        et = event.type()
        if et in (
            QEvent.MouseButtonPress,
            QEvent.MouseMove,
            QEvent.KeyPress,
            QEvent.KeyRelease,
            QEvent.Wheel,
            QEvent.TouchBegin,
            QEvent.TouchUpdate,
            QEvent.TabletPress,
        ):
            self.reset_timer()
        return super().eventFilter(obj, event)

    def _check_idle(self):
        if not self._enabled or self._locked:
            return
        now = datetime.now()
        idle_sec = (now - self._last_activity).total_seconds()
        timeout_sec = self._timeout_minutes * 60
        warning_sec = max(timeout_sec - WARNING_SECONDS, 0)

        if idle_sec >= timeout_sec:
            self._do_lock()
        elif idle_sec >= warning_sec and not self._warning_shown:
            self._show_warning(int(timeout_sec - idle_sec))

    def _show_warning(self, remaining_sec: int):
        self._warning_shown = True
        parent = self.parent() if isinstance(self.parent(), QWidget) else None
        if parent and parent.isVisible():
            try:
                self._warning_dialog = LockWarningDialog(remaining_sec, parent)
                self._warning_dialog.show()
            except Exception as e:
                logger.debug("AutoLock warning dialog failed: %s", e)

    def _do_lock(self):
        self._check_passphrase_state()
        if not self._enabled:
            self._locked = False
            logger.info("AutoLock skipped: passphrase no longer available")
            return

        self._locked = True
        logger.info("Session locked after %d min inactivity", self._timeout_minutes)
        log_audit("SESSION_LOCK", f"Auto-lock after {self._timeout_minutes} min inactivity")

        if self._warning_dialog:
            try:
                self._warning_dialog.close()
            except RuntimeError:
                pass
            self._warning_dialog = None

        parent = self.parent() if isinstance(self.parent(), QWidget) else None

        self._show_blur(parent)
        dialog = LockDialog(parent)
        dialog.exec()

        if dialog.was_unlocked:
            self._hide_blur()
            self._unlock()
        else:
            self._locked = True

    def _unlock(self):
        self._locked = False
        self._last_activity = datetime.now()
        self._warning_shown = False

    def _show_blur(self, parent: QWidget):
        """Create and show a blur overlay over the main window."""
        if parent and parent.isVisible():
            try:
                self._blur_overlay = BlurOverlay(parent)
                self._blur_overlay.capture_and_blur()
                self._blur_overlay.show()
                self._blur_overlay.raise_()
                from PySide6.QtWidgets import QApplication as QApp
                QApp.processEvents()
            except Exception as e:
                logger.debug("Blur overlay failed: %s", e)
                self._blur_overlay = None

    def _hide_blur(self):
        """Remove the blur overlay."""
        if self._blur_overlay:
            try:
                self._blur_overlay.hide()
                self._blur_overlay.deleteLater()
            except RuntimeError:
                pass
            self._blur_overlay = None

    def force_lock(self):
        """Manually lock the session immediately."""
        self._check_passphrase_state()
        if not self._enabled:
            safe_message_box(
                self.parent() if isinstance(self.parent(), QWidget) else None,
                "Блокировка недоступна",
                "Автоматическая блокировка сессии требует установки "
                "парольной фразы.\n\n"
                "Установите парольную фразу в диалоге 'О программе' "
                "(меню Справка → О программе, раздел Безопасность).",
                QMessageBox.Information
            )
            return
        self._do_lock()
