import os
import logging
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QDialog, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QIcon
from utils.crypto import verify_passphrase, CryptoPassphraseRequiredError
from utils.app_paths import get_resource_dir
from utils.about_dialog import VERSION
from utils.audit import log_audit


logger = logging.getLogger(__name__)


class PassphraseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Подтверждение парольной фразы")
        self.setMinimumSize(400, 280)
        self.setMaximumSize(600, 450)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setModal(True)

        icon_path = os.path.join(get_resource_dir(), "resources", "ico.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(14)

        header = QHBoxLayout()
        header.setSpacing(16)

        icon_lbl = QLabel()
        if os.path.exists(icon_path):
            pix = QPixmap(icon_path)
            if not pix.isNull():
                icon_lbl.setPixmap(pix.scaled(56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        icon_lbl.setFixedSize(60, 60)
        header.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        app_name = QLabel("Excel-XML для передачи\nданных в Минтруд")
        app_name.setStyleSheet("font-size: 16px; font-weight: bold;")
        header.addWidget(app_name)

        ver_label = QLabel(f"Версия {VERSION}")
        ver_label.setStyleSheet("font-size: 11px; color: #888; margin-top: 2px;")
        title_col.addWidget(ver_label)
        title_col.addStretch()
        header.addLayout(title_col, 1)

        layout.addLayout(header)

        separator = QLabel()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #ddd;")
        layout.addWidget(separator)

        prompt = QLabel("Для доступа к зашифрованным данным требуется парольная фраза.")
        prompt.setWordWrap(True)
        prompt.setStyleSheet("font-size: 13px;")
        layout.addWidget(prompt)

        info = QLabel(
            "Мастер-ключ зашифрован парольной фразой (PBKDF2, 600 000 итераций). "
            "Без неё расшифровать сохранённые персональные данные невозможно."
        )
        info.setWordWrap(True)
        info.setStyleSheet("font-size: 12px; color: #666; padding: 0 0 4px 0;")
        layout.addWidget(info)

        self.pwd_input = QLineEdit()
        self.pwd_input.setEchoMode(QLineEdit.Password)
        self.pwd_input.setPlaceholderText("Введите парольную фразу")
        self.pwd_input.setMinimumHeight(38)
        self.pwd_input.setStyleSheet("font-size: 14px; padding: 4px 10px;")
        self.pwd_input.returnPressed.connect(self._on_accept)
        layout.addWidget(self.pwd_input)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Отмена")
        cancel_btn.setMinimumHeight(38)
        cancel_btn.setMinimumWidth(100)
        cancel_btn.clicked.connect(self._on_cancel)
        btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton("Разблокировать")
        ok_btn.setMinimumHeight(38)
        ok_btn.setMinimumWidth(140)
        ok_btn.setDefault(True)
        ok_btn.setStyleSheet(
            "QPushButton { background-color: #27AE60; color: white; border: none; "
            "padding: 8px 20px; border-radius: 5px; font-weight: bold; }"
            "QPushButton:hover { background-color: #219A52; }"
            "QPushButton:pressed { background-color: #1E8449; }"
        )
        ok_btn.clicked.connect(self._on_accept)
        btn_row.addWidget(ok_btn)

        layout.addLayout(btn_row)

        self._wrong_attempts: int = 0
        self._MAX_ATTEMPTS: int = 5
        self._BASE_DELAY_MS: int = 1000
        self.ok_btn = ok_btn

        self.pwd_input.setFocus()

    def _on_accept(self):
        pp = self.pwd_input.text()
        if not pp:
            self.pwd_input.setStyleSheet(
                "font-size: 14px; padding: 4px 10px; "
                "border: 2px solid #E74C3C; background-color: #FFF0F0;"
            )
            self.pwd_input.setPlaceholderText("Введите парольную фразу (обязательно)")
            return
        try:
            if verify_passphrase(pp):
                logger.info("Passphrase verified at startup")
                self.accept()
            else:
                self._show_wrong()
        except CryptoPassphraseRequiredError:
            self._show_wrong()

    def _show_wrong(self):
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
            self.reject()
            from PySide6.QtWidgets import QApplication
            QApplication.instance().quit()
            return
        delay_ms = self._BASE_DELAY_MS * (2 ** (self._wrong_attempts - 1))
        delay_ms = min(delay_ms, 30_000)
        self.ok_btn.setEnabled(False)
        self.pwd_input.setEnabled(False)
        self.pwd_input.setStyleSheet(
            "font-size: 14px; padding: 4px 10px; "
            "border: 2px solid #E74C3C; background-color: #FFF0F0;"
        )
        self.pwd_input.setPlaceholderText(
            f"Неверно. Подождите {delay_ms // 1000} сек..."
        )
        QTimer.singleShot(delay_ms, self._restore_after_delay)

    def _restore_after_delay(self):
        self.pwd_input.setEnabled(True)
        self.ok_btn.setEnabled(True)
        self.pwd_input.setStyleSheet("font-size: 14px; padding: 4px 10px;")
        self.pwd_input.clear()
        self.pwd_input.setPlaceholderText("Введите парольную фразу")
        self.pwd_input.setFocus()

    def _on_cancel(self):
        logger.warning("Passphrase prompt cancelled at startup")
        QMessageBox.information(
            self, "Завершение работы",
            "Приложение не может работать без расшифровки данных.\n\n"
            "Программа будет закрыта."
        )
        self.reject()
