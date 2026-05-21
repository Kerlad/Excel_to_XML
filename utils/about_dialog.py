import os
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget,
    QMessageBox, QFileDialog, QInputDialog, QLineEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QFont, QDesktopServices
from PySide6.QtCore import QUrl
from utils.dialog_base import BaseDialog
from utils.app_paths import get_resource_dir
from utils.crypto import (
    check_master_key_security, create_master_key_backup,
    is_passphrase_protected, set_passphrase, remove_passphrase,
    verify_passphrase, get_key_fingerprint, CryptoPassphraseRequiredError,
    CryptoError
)


VERSION = "1.3.0"


class ClickableLabel(QLabel):
    def __init__(self, text, url, parent=None):
        super().__init__(text, parent)
        self._url = url
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        QDesktopServices.openUrl(QUrl(self._url))
        super().mousePressEvent(event)


class AboutDialog(BaseDialog):
    def __init__(self, parent=None):
        super().__init__(parent, title="О программе", min_width=520, min_height=360)

        bl = self.body_layout()

        header_row = QHBoxLayout()
        header_row.setSpacing(16)

        icon_path = os.path.join(get_resource_dir(), "resources", "ico.ico")
        icon_label = QLabel()
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                icon_label.setPixmap(pixmap.scaled(56, 56, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        icon_label.setFixedSize(60, 60)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_row.addWidget(icon_label)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_label = QLabel("Excel-XML для передачи данных в Минтруд")
        title_label.setObjectName("aboutTitleLabel")
        title_label.setWordWrap(True)
        title_col.addWidget(title_label)

        version_label = QLabel(f"Версия {VERSION}")
        version_label.setObjectName("aboutVersionLabel")
        title_col.addWidget(version_label)

        header_row.addLayout(title_col, 1)
        bl.addLayout(header_row)

        desc = QLabel(
            "Автоматизированная система учёта обучения работников требованиям охраны труда "
            "(постановление 2464), ведения реестра с контролем статуса (обучен / не обучен / "
            "просрочено), синхронизации с реестром Минтруда России, "
            "генерации XML-файлов для передачи данных, формирования планов обучения "
            "и протоколов проверки знаний."
        )
        desc.setObjectName("aboutDescLabel")
        desc.setWordWrap(True)
        bl.addWidget(desc)

        info_widget = QWidget()
        info_widget.setObjectName("aboutInfoWidget")
        info_layout = QVBoxLayout(info_widget)
        info_layout.setSpacing(4)
        info_layout.setContentsMargins(12, 10, 12, 10)

        dev_label = QLabel("<b>Разработчик:</b> Кривоносов Д.А.")
        dev_label.setObjectName("aboutInfoLabel")
        info_layout.addWidget(dev_label)

        studio_label = QLabel("<b>При участии:</b> QWEN Studio, OpenCode (free AI)")
        studio_label.setObjectName("aboutInfoLabel")
        info_layout.addWidget(studio_label)

        repo_link = ClickableLabel(
            "<b>Репозиторий:</b> https://github.com/Kerlad/Excel_to_XML.git",
            "https://github.com/Kerlad/Excel_to_XML.git"
        )
        repo_link.setObjectName("aboutInfoLink")
        info_layout.addWidget(repo_link)

        email_link = ClickableLabel(
            "<b>Электронная почта:</b> denis-krv@yandex.ru",
            "mailto:denis-krv@yandex.ru"
        )
        email_link.setObjectName("aboutInfoLink")
        info_layout.addWidget(email_link)

        bl.addWidget(info_widget)

        security_widget = QWidget()
        security_widget.setObjectName("aboutInfoWidget")
        security_layout = QVBoxLayout(security_widget)
        security_layout.setSpacing(4)
        security_layout.setContentsMargins(12, 10, 12, 10)

        self._security_status_label = QLabel()
        self._update_security_status()
        self._security_status_label.setObjectName("aboutInfoLabel")
        self._security_status_label.setWordWrap(True)
        security_layout.addWidget(self._security_status_label)

        backup_btn = QPushButton("Создать защищённый бэкап master.key")
        backup_btn.setObjectName("dialogPrimaryBtn")
        backup_btn.setMinimumHeight(36)
        backup_btn.clicked.connect(self._create_key_backup)
        security_layout.addWidget(backup_btn)

        passphrase_btn_row = QHBoxLayout()

        self._set_passphrase_btn = QPushButton("Установить парольную фразу")
        self._set_passphrase_btn.setObjectName("dialogPrimaryBtn")
        self._set_passphrase_btn.setMinimumHeight(36)
        self._set_passphrase_btn.clicked.connect(self._set_passphrase)
        passphrase_btn_row.addWidget(self._set_passphrase_btn)

        self._remove_passphrase_btn = QPushButton("Снять парольную фразу")
        self._remove_passphrase_btn.setObjectName("dialogDangerBtn")
        self._remove_passphrase_btn.setMinimumHeight(36)
        self._remove_passphrase_btn.clicked.connect(self._remove_passphrase)
        passphrase_btn_row.addWidget(self._remove_passphrase_btn)

        security_layout.addLayout(passphrase_btn_row)

        bl.addWidget(security_widget)
        bl.addStretch()

        close_btn = QPushButton("Закрыть")
        close_btn.setObjectName("dialogPrimaryBtn")
        close_btn.setMinimumHeight(40)
        self._button_layout.addStretch()
        self._button_layout.addWidget(close_btn)
        close_btn.clicked.connect(self.close)

    def _update_security_status(self):
        mode, msg = check_master_key_security()
        pp = is_passphrase_protected()
        if mode in ('dpapi', 'dpapi_passphrase'):
            html = f'<span style="color:#27AE60;"><b>✓ Безопасность:</b> {msg}</span>'
        elif mode == 'raw_passphrase':
            html = f'<span style="color:#27AE60;"><b>✓ Безопасность:</b> {msg}</span>'
        elif mode == 'raw':
            html = f'<span style="color:#E74C3C;"><b>✗ ВНИМАНИЕ!</b> {msg}</span>'
        else:
            html = f'<span style="color:#F39C12;"><b>⚠</b> {msg}</span>'
        fingerprint = get_key_fingerprint()
        html += f'<br><span style="font-size:11px;color:#7F8C8D;">Отпечаток ключа: {fingerprint}</span>'
        self._security_status_label.setText(html)
        self._set_passphrase_btn.setVisible(not pp)
        self._remove_passphrase_btn.setVisible(pp)

    def _set_passphrase(self):
        pp, ok = QInputDialog.getText(
            self, "Установка парольной фразы",
            "Введите парольную фразу для дополнительной защиты мастер-ключа:",
            QLineEdit.EchoMode.Password
        )
        if not ok or not pp:
            return
        confirm, ok = QInputDialog.getText(
            self, "Подтверждение парольной фразы",
            "Повторите парольную фразу:",
            QLineEdit.EchoMode.Password
        )
        if not ok or pp != confirm:
            QMessageBox.warning(self, "Ошибка", "Парольные фразы не совпадают")
            return
        try:
            set_passphrase(pp)
            QMessageBox.information(self, "Успех", "Парольная фраза установлена")
            self._update_security_status()
        except CryptoError as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось установить парольную фразу:\n{e}")

    def _remove_passphrase(self):
        pp, ok = QInputDialog.getText(
            self, "Снятие парольной фразы",
            "Введите текущую парольную фразу:",
            QLineEdit.EchoMode.Password
        )
        if not ok or not pp:
            return
        try:
            verify_passphrase(pp)
            remove_passphrase(pp)
            QMessageBox.information(self, "Успех", "Парольная фраза снята")
            self._update_security_status()
        except CryptoPassphraseRequiredError:
            QMessageBox.warning(self, "Ошибка", "Неверная парольная фраза")
        except CryptoError as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось снять парольную фразу:\n{e}")

    def _create_key_backup(self):
        backup_dir = QFileDialog.getExistingDirectory(self, "Выберите папку для бэкапа master.key")
        if not backup_dir:
            return
        ok, result = create_master_key_backup(backup_dir)
        if ok:
            QMessageBox.information(self, "Успех", f"Бэкап создан:\n{result}")
        else:
            QMessageBox.warning(self, "Ошибка", f"Не удалось создать бэкап:\n{result}")
