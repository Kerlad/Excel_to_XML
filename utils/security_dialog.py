import logging
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget,
    QMessageBox, QInputDialog, QLineEdit, QFileDialog
)
from PySide6.QtCore import Qt
from utils.dialog_base import BaseDialog
from utils.app_paths import get_app_data_dir, get_resource_dir
from utils.crypto import (
    check_master_key_security, create_master_key_backup,
    is_passphrase_protected, set_passphrase, remove_passphrase,
    verify_passphrase, get_key_fingerprint, CryptoPassphraseRequiredError,
    CryptoError
)
from utils.error_utils import safe_message_box

logger = logging.getLogger(__name__)


class SecurityDialog(BaseDialog):
    def __init__(self, parent=None):
        super().__init__(parent, title="Безопасность", min_width=520, min_height=420)

        bl = self.body_layout()

        passphrase_notice = QLabel(
            '🔑 <b>Рекомендуется установить парольную фразу</b> '
            'для защиты мастер-ключа. '
            '<b>Обязательно запишите или запомните её</b> — '
            'при утере восстановить данные будет невозможно.'
        )
        passphrase_notice.setObjectName("aboutPassphraseNotice")
        passphrase_notice.setWordWrap(True)
        passphrase_notice.setStyleSheet(
            "padding: 10px; border: 1px solid #F39C12; border-radius: 6px; "
            "background-color: rgba(243, 156, 18, 0.08);"
        )
        bl.addWidget(passphrase_notice)

        security_widget = QWidget()
        security_widget.setObjectName("aboutInfoWidget")
        security_layout = QVBoxLayout(security_widget)
        security_layout.setSpacing(4)
        security_layout.setContentsMargins(12, 10, 12, 10)

        self._security_status_label = QLabel()
        self._security_status_label.setObjectName("aboutInfoLabel")
        self._security_status_label.setWordWrap(True)
        security_layout.addWidget(self._security_status_label)

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

        backup_info = QLabel(
            '<b>Зачем нужен бэкап master.key?</b><br><br>'
            'Файл <code>master.key</code> содержит зашифрованный мастер-ключ, который '
            'используется для шифрования всех данных приложения (ФИО, СНИЛС, API-ключ, '
            'настройки прокси и т.д.).<br><br>'
            'Если мастер-ключ будет утерян или повреждён:<br>'
            '&bull; Все зашифрованные данные станут недоступны навсегда<br>'
            '&bull; Восстановить парольную фразу или расшифровать данные без ключа невозможно<br>'
            '&bull; Придётся заново вводить все данные сотрудников, API-ключ и настройки<br><br>'
            'Бэкап создаётся с паролем, производным от мастер-ключа, и сохраняется '
            'в выбранную вами папку. Храните бэкап в надёжном месте, отдельно от программы.'
        )
        backup_info.setWordWrap(True)
        backup_info.setStyleSheet(
            "padding: 10px; border: 1px solid palette(mid); border-radius: 6px;"
        )
        bl.addWidget(backup_info)

        backup_btn = QPushButton("Создать защищённый бэкап master.key")
        backup_btn.setObjectName("dialogPrimaryBtn")
        backup_btn.setMinimumHeight(36)
        backup_btn.clicked.connect(self._create_key_backup)
        bl.addWidget(backup_btn)

        bl.addStretch()

        self.add_close_button("Закрыть")

        self._update_security_status()

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
            safe_message_box(self, QMessageBox.Icon.Warning, "Ошибка", f"Не удалось установить парольную фразу:\n{e}")

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
            safe_message_box(self, QMessageBox.Icon.Warning, "Ошибка", f"Не удалось снять парольную фразу:\n{e}")

    def _create_key_backup(self):
        backup_dir = QFileDialog.getExistingDirectory(self, "Выберите папку для бэкапа master.key")
        if not backup_dir:
            return
        ok, result = create_master_key_backup(backup_dir)
        if ok:
            safe_message_box(self, QMessageBox.Icon.Information, "Успех", f"Бэкап создан:\n{result}")
        else:
            safe_message_box(self, QMessageBox.Icon.Warning, "Ошибка", f"Не удалось создать бэкап:\n{result}")
