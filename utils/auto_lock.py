"""
Session auto-lock for PDn protection.
Locks the UI after configurable inactivity timeout.
Unlock requires passphrase (if set).
Locked screen is blurred and overlaid with semi-transparent dark layer.
"""
import os
import json
import logging
from datetime import datetime
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QDialog, QMessageBox, QWidget, QApplication
)
from PySide6.QtCore import Qt, QTimer, QEvent, QObject, QPoint, QRect
from PySide6.QtGui import QPixmap, QPainter, QImage, QColor, QRegion
from PySide6.QtGui import QPixmap, QPainter, QImage, QColor
from utils.crypto import verify_passphrase, is_passphrase_protected, CryptoPassphraseRequiredError
from utils.crypto import compute_org_settings_hmac, verify_org_settings_hmac
from utils.audit import log_audit
from utils.app_paths import get_resource_dir, get_app_data_dir
from utils.error_utils import safe_message_box
from utils.security_dialog import SecurityDialog

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_MINUTES = 10
WARNING_SECONDS = 30
CHECK_INTERVAL_MS = 1000
BLUR_DOWNSCALE_FACTOR = 6
OVERLAY_OPACITY = 180
EXIT_CODE_QUIT = 42


class LockDialog(QDialog):
    """Full-window modal lock screen with blurred background + centered unlock UI.
    Captures the parent window, pixelation-blurs it, and overlays the passphrase dialog.
    """

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self._unlocked = False
        self._wrong_attempts: int = 0
        self._MAX_ATTEMPTS: int = 5
        self._BASE_DELAY_MS: int = 1000
        self._bg_pixmap = None
        self._capture_and_blur(parent)
        self._build_ui(parent)

    def _capture_and_blur(self, parent: QWidget):
        """Capture parent content and create pixelation-blurred + darkened pixmap."""
        if not parent or not parent.isVisible():
            return
        size = parent.size()
        if size.width() < 1 or size.height() < 1:
            return

        small_w = max(size.width() // BLUR_DOWNSCALE_FACTOR, 1)
        small_h = max(size.height() // BLUR_DOWNSCALE_FACTOR, 1)

        pixmap = QPixmap(size)
        pixmap.fill(Qt.transparent)
        parent.render(pixmap, QPoint(), QRegion(QRect(QPoint(0, 0), size)))
        QApplication.processEvents()

        blurred = QImage(pixmap.toImage())\
            .scaled(small_w, small_h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)\
            .scaled(size.width(), size.height(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

        result = QImage(size, QImage.Format_ARGB32)
        result.fill(Qt.transparent)

        painter = QPainter(result)
        painter.drawImage(QPoint(0, 0), blurred)
        painter.fillRect(QRect(QPoint(0, 0), size), QColor(0, 0, 0, OVERLAY_OPACITY))
        painter.end()

        self._bg_pixmap = QPixmap.fromImage(result)

    def _build_ui(self, parent: QWidget):
        self.setWindowTitle("Сессия заблокирована")
        self.setModal(True)
        self.setGeometry(parent.geometry())
        self.setWindowFlags(
            Qt.Dialog | Qt.FramelessWindowHint
        )
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("LockDialog { background: transparent; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        outer = QHBoxLayout()
        outer.addStretch()

        center = QVBoxLayout()
        center.setContentsMargins(28, 24, 28, 20)
        center.setSpacing(12)
        center.setAlignment(Qt.AlignCenter)

        card = QWidget()
        card.setObjectName("lockCard")
        card.setMinimumSize(380, 280)
        card.setMaximumSize(520, 400)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 24, 28, 20)
        card_layout.setSpacing(12)

        icon_path = os.path.join(get_resource_dir(), "resources", "ico.ico")
        icon_lbl = QLabel()
        if os.path.exists(icon_path):
            pix = QPixmap(icon_path)
            if not pix.isNull():
                icon_lbl.setPixmap(
                    pix.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
        icon_lbl.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(icon_lbl)

        title = QLabel("Сессия заблокирована")
        title.setObjectName("lockTitle")
        title.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title)

        desc = QLabel(
            "Приложение было заблокировано из-за отсутствия активности.\n"
            "Введите парольную фразу для продолжения работы."
        )
        desc.setObjectName("lockDesc")
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        card_layout.addWidget(desc)

        self.pwd_input = QLineEdit()
        self.pwd_input.setObjectName("lockPwdInput")
        self.pwd_input.setEchoMode(QLineEdit.Password)
        self.pwd_input.setPlaceholderText("Парольная фраза")
        self.pwd_input.setMinimumHeight(40)
        self.pwd_input.returnPressed.connect(self._try_unlock)
        card_layout.addWidget(self.pwd_input)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.exit_btn = QPushButton("Выход")
        self.exit_btn.setObjectName("lockExitBtn")
        self.exit_btn.setMinimumHeight(40)
        self.exit_btn.setMinimumWidth(100)
        self.exit_btn.clicked.connect(self._exit_app)
        btn_row.addWidget(self.exit_btn)

        btn_row.addSpacing(12)

        self.lock_btn = QPushButton("Разблокировать")
        self.lock_btn.setObjectName("lockUnlockBtn")
        self.lock_btn.setMinimumHeight(40)
        self.lock_btn.setMinimumWidth(180)
        self.lock_btn.setDefault(True)
        self.lock_btn.clicked.connect(self._try_unlock)
        btn_row.addWidget(self.lock_btn)
        card_layout.addLayout(btn_row)

        self.pwd_input.setFocus()

        center.addWidget(card)
        outer.addLayout(center)
        outer.addStretch()
        layout.addLayout(outer)

    def paintEvent(self, event):
        if self._bg_pixmap and not self._bg_pixmap.isNull():
            painter = QPainter(self)
            painter.drawPixmap(QPoint(0, 0), self._bg_pixmap)
            painter.end()
        else:
            super().paintEvent(event)

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
        self._wrong_attempts += 1
        log_audit("SESSION_LOCK",
                  f"Wrong passphrase attempt {self._wrong_attempts}/{self._MAX_ATTEMPTS}")
        if self._wrong_attempts >= self._MAX_ATTEMPTS:
            log_audit("SECURITY_WARNING",
                      f"Max passphrase attempts ({self._MAX_ATTEMPTS}) reached — forcing exit")
            QMessageBox.critical(
                self, "Превышено число попыток",
                f"Введено {self._MAX_ATTEMPTS} неверных парольных фраз.\n"
                "Приложение будет закрыто в целях безопасности."
            )
            self.done(EXIT_CODE_QUIT)
            return
        delay_ms = self._BASE_DELAY_MS * (2 ** (self._wrong_attempts - 1))
        delay_ms = min(delay_ms, 30_000)
        self.lock_btn.setEnabled(False)
        self.pwd_input.setEnabled(False)
        self.pwd_input.setPlaceholderText(
            f"Неверно. Подождите {delay_ms // 1000} сек..."
        )
        QTimer.singleShot(delay_ms, self._restore_after_delay)

    def _restore_after_delay(self):
        self.pwd_input.setEnabled(True)
        self.lock_btn.setEnabled(True)
        self.pwd_input.clear()
        self.pwd_input.setPlaceholderText("Введите парольную фразу")
        self.pwd_input.setFocus()

    def _exit_app(self):
        logger.info("Session: user chose to exit application from lock screen")
        log_audit("SESSION_LOCK", "Application closed from lock screen (exit button)")
        self.done(EXIT_CODE_QUIT)

    def _shake_input(self, placeholder: str):
        self.pwd_input.setProperty("danger", True)
        self.pwd_input.style().unpolish(self.pwd_input)
        self.pwd_input.style().polish(self.pwd_input)
        self.pwd_input.clear()
        self.pwd_input.setPlaceholderText(placeholder)
        QTimer.singleShot(2000, self._restore_input_style)

    def _restore_input_style(self):
        self.pwd_input.setProperty("danger", False)
        self.pwd_input.style().unpolish(self.pwd_input)
        self.pwd_input.style().polish(self.pwd_input)
        self.pwd_input.setPlaceholderText("Парольная фраза")

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
    """Non-modal warning shown shortly before auto-lock."""

    def __init__(self, remaining_sec: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Предупреждение")
        self.setMinimumSize(360, 120)
        self.setMaximumSize(600, 200)
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
        msg.setObjectName("lockWarningMsg")
        msg.setWordWrap(True)
        msg.setAlignment(Qt.AlignCenter)
        layout.addWidget(msg)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        ok_btn = QPushButton("Продолжить работу")
        ok_btn.setObjectName("lockWarningBtn")
        ok_btn.setMinimumHeight(36)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)

        self.setFocus()
        ok_btn.setFocus()


class AutoLockManager(QObject):
    """Tracks user inactivity and locks the session after timeout.
    Only activates when a passphrase is set on the master key.
    """

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._enabled = False
        self._timeout_minutes = self._load_timeout()
        self._last_activity = datetime.now()
        self._locked = False
        self._warning_shown = False
        self._warning_dialog: QWidget = None

        self._timer = QTimer(self)
        self._timer.setInterval(CHECK_INTERVAL_MS)
        self._timer.timeout.connect(self._check_idle)
        self._timer.start()

        self._check_passphrase_state()

    def _settings_path(self) -> str:
        return os.path.join(get_app_data_dir(), "auto_lock_settings.json")

    def _load_timeout(self) -> int:
        path = self._settings_path()
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not verify_org_settings_hmac(dict(data)):
                    logger.warning("AutoLock: timeout settings HMAC mismatch — using default")
                    log_audit("SECURITY_WARNING", "Auto-lock timeout file tampered — reset to default")
                    return DEFAULT_TIMEOUT_MINUTES
                return max(1, min(int(data.get("timeout_minutes", DEFAULT_TIMEOUT_MINUTES)), 120))
        except Exception as e:
            logger.debug("AutoLock: failed to load timeout setting: %s", e)
        return DEFAULT_TIMEOUT_MINUTES

    def _save_timeout(self):
        path = self._settings_path()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            data = {"timeout_minutes": self._timeout_minutes}
            data["hmac"] = compute_org_settings_hmac(data)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception as e:
            logger.debug("AutoLock: failed to save timeout setting: %s", e)

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
        self._save_timeout()

    def refresh(self):
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
            logger.info("AutoLock: opening Security dialog for passphrase setup")
            parent = self.parent() if isinstance(self.parent(), QWidget) else None
            dialog = SecurityDialog(parent)
            dialog.exec()
            self._check_passphrase_state()
            if not self._enabled:
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

        dialog = LockDialog(parent)
        dialog.setAttribute(Qt.WA_DeleteOnClose)
        result = dialog.exec()

        if result == EXIT_CODE_QUIT:
            QApplication.closeAllWindows()
            return

        if dialog.was_unlocked:
            self._unlock()

    def _unlock(self):
        self._locked = False
        self._last_activity = datetime.now()
        self._warning_shown = False

    def force_lock(self):
        self._check_passphrase_state()
        if not self._enabled:
            logger.info("Manual lock: opening Security dialog for passphrase setup")
            parent = self.parent() if isinstance(self.parent(), QWidget) else None
            dialog = SecurityDialog(parent)
            dialog.exec()
            self._check_passphrase_state()
            if not self._enabled:
                return
        self._do_lock()
