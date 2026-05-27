import os
import logging
import tempfile
import urllib.parse
from datetime import datetime
from zipfile import ZipFile
from pathlib import Path
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget,
    QMessageBox, QFileDialog, QInputDialog, QLineEdit, QTextEdit,
    QDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QFont, QDesktopServices
from PySide6.QtCore import QUrl
from utils.dialog_base import BaseDialog
from utils.app_paths import get_resource_dir, get_app_log_dir
from utils.crypto import (
    check_master_key_security, create_master_key_backup,
    is_passphrase_protected, set_passphrase, remove_passphrase,
    verify_passphrase, get_key_fingerprint, CryptoPassphraseRequiredError,
    CryptoError
)
from utils.error_utils import safe_message_box


VERSION = "3.2.0"


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

        passphrase_notice = QLabel(
            '🔑 <b>Рекомендуется установить парольную фразу</b> '
            'для защиты мастер-ключа (раздел «Безопасность» ниже). '
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

        info_widget = QWidget()
        info_widget.setObjectName("aboutInfoWidget")
        info_layout = QVBoxLayout(info_widget)
        info_layout.setSpacing(4)
        info_layout.setContentsMargins(12, 10, 12, 10)

        dev_label = QLabel("<b>Разработчик:</b> Кривоносов Д.А.")
        dev_label.setObjectName("aboutInfoLabel")
        info_layout.addWidget(dev_label)

        studio_label = QLabel("<b>При участии:</b> OpenCode")
        studio_label.setObjectName("aboutInfoLabel")
        info_layout.addWidget(studio_label)

        repo_link = ClickableLabel(
            "<b>Репозиторий:</b> https://github.com/Kerlad/Excel_to_XML.git",
            "https://github.com/Kerlad/Excel_to_XML.git"
        )
        repo_link.setObjectName("aboutInfoLink")
        info_layout.addWidget(repo_link)

        email_link = ClickableLabel(
            "<b>Электронная почта:</b> denis.krv@yandex.ru",
            "mailto:denis.krv@yandex.ru"
        )
        email_link.setObjectName("aboutInfoLink")
        info_layout.addWidget(email_link)

        bl.addWidget(info_widget)

        report_btn = QPushButton("Сообщить об ошибке")
        report_btn.setMinimumHeight(36)
        report_btn.setStyleSheet(
            "QPushButton { background-color: #E74C3C; color: white; border: none; "
            "padding: 8px 20px; border-radius: 5px; font-weight: bold; }"
            "QPushButton:hover { background-color: #C0392B; }"
            "QPushButton:pressed { background-color: #A93226; }"
        )
        report_btn.clicked.connect(self._report_error)
        bl.addWidget(report_btn)

        security_widget = QWidget()
        security_widget.setObjectName("aboutInfoWidget")
        security_layout = QVBoxLayout(security_widget)
        security_layout.setSpacing(4)
        security_layout.setContentsMargins(12, 10, 12, 10)

        self._security_status_label = QLabel()
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

        self._update_security_status()

        bl.addWidget(security_widget)
        bl.addStretch()

        donate_btn = QPushButton("Поддержать разработчика ❤️")
        donate_btn.setFixedHeight(32)
        donate_btn.setStyleSheet(
            "QPushButton { font-size: 12px; color: #9B59B6; border: 1px solid #9B59B6; "
            "border-radius: 4px; padding: 4px 12px; background: transparent; }"
            "QPushButton:hover { background-color: rgba(155, 89, 182, 0.1); }"
        )
        donate_btn.clicked.connect(self._open_donation)
        self._button_layout.addWidget(donate_btn)

        self._button_layout.addStretch()

        close_btn = QPushButton("Закрыть")
        close_btn.setObjectName("dialogPrimaryBtn")
        close_btn.setMinimumHeight(40)
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

    def _report_error(self):
        log_dir = get_app_log_dir()
        log_path = Path(log_dir)
        if not log_path.exists() or not any(log_path.iterdir()):
            QMessageBox.information(
                self, "Логи не найдены",
                "Директория логов пуста или не существует.\n\n"
                "Вы можете отправить сообщение об ошибке вручную "
                "на denis.krv@yandex.ru"
            )
            return

        desktop = os.path.join(os.environ.get('USERPROFILE', os.path.expanduser('~')), 'Desktop')
        if not os.path.isdir(desktop):
            desktop = os.path.join(os.environ.get('TEMP', os.path.expanduser('~')))
        zip_name = f"error_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        zip_path = os.path.join(desktop, zip_name)
        try:
            with ZipFile(zip_path, 'w') as zf:
                for f in log_path.iterdir():
                    if f.is_file():
                        zf.write(str(f), arcname=f.name)
        except Exception as e:
            logging.getLogger(__name__).error("Failed to create log ZIP: %s", e)
            QMessageBox.warning(
                self, "Ошибка",
                f"Не удалось создать архив логов:\n{e}"
            )
            return

        body_dialog = QDialog(self)
        body_dialog.setWindowTitle("Описание ошибки")
        body_dialog.setMinimumSize(380, 300)
        body_dialog.setModal(True)
        layout = QVBoxLayout(body_dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        hint = QLabel(
            "Опишите, что произошло. К письму будет приложен архив с логами."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        text_edit = QTextEdit()
        text_edit.setPlaceholderText(
            "Опишите проблему: что делали, что ожидали, что произошло на самом деле..."
        )
        text_edit.setMinimumHeight(180)
        layout.addWidget(text_edit)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setMinimumHeight(36)
        cancel_btn.clicked.connect(body_dialog.reject)
        btn_row.addWidget(cancel_btn)
        send_btn = QPushButton("Отправить")
        send_btn.setMinimumHeight(36)
        send_btn.setStyleSheet(
            "QPushButton { background-color: #27AE60; color: white; border: none; "
            "padding: 8px 20px; border-radius: 5px; font-weight: bold; }"
            "QPushButton:hover { background-color: #219A52; }"
        )
        send_btn.clicked.connect(body_dialog.accept)
        btn_row.addWidget(send_btn)
        layout.addLayout(btn_row)

        if body_dialog.exec() != QDialog.DialogCode.Accepted:
            try:
                os.remove(zip_path)
            except OSError:
                pass
            return

        user_text = text_edit.toPlainText().strip()

        sent = False
        try:
            import win32com.client
            outlook = win32com.client.Dispatch("Outlook.Application")
            mail = outlook.CreateItem(0)
            mail.To = "denis.krv@yandex.ru"
            mail.Subject = f"Excel-XML v{VERSION}: сообщение об ошибке"
            body_parts = []
            if user_text:
                body_parts.append(user_text)
            body_parts.append("")
            body_parts.append("---")
            body_parts.append(f"Версия: {VERSION}")
            body_parts.append(f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
            mail.Body = "\n".join(body_parts)
            mail.Attachments.Add(zip_path)
            mail.Display()
            sent = True
            logging.getLogger(__name__).info("Outlook error report created")
        except ImportError:
            logging.getLogger(__name__).debug("win32com not available for error report")
        except Exception as e:
            logging.getLogger(__name__).warning(f"Outlook COM failed: {e}")

        if not sent:
            subject = f"Excel-XML v{VERSION}: сообщение об ошибке"
            body = ""
            if user_text:
                body += user_text + "\n\n"
            body += "---\n"
            body += f"Архив логов: {zip_path}\n"
            body += f"Версия: {VERSION}\n"
            body += f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            mailto_url = (
                f"mailto:denis.krv@yandex.ru"
                f"?subject={urllib.parse.quote(subject, safe='')}"
                f"&body={urllib.parse.quote(body, safe='')}"
            )
            QDesktopServices.openUrl(QUrl(mailto_url))
            msg = QMessageBox(self)
            msg.setWindowTitle("Архив логов")
            msg.setIcon(QMessageBox.Information)
            msg.setText(
                f"Архив логов сохранён:\n{zip_path}\n\n"
                "Пожалуйста, прикрепите его к открывшемуся письму вручную."
            )
            open_btn = msg.addButton("Открыть папку", QMessageBox.ActionRole)
            msg.addButton("Закрыть", QMessageBox.RejectRole)
            msg.exec()
            if msg.clickedButton() == open_btn:
                folder = os.path.dirname(zip_path)
                QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    def _open_donation(self):
        from utils.donation_dialog import DonationDialog
        dialog = DonationDialog(self)
        dialog.exec()

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
