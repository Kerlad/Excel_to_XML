import os
import logging
import unicodedata
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLineEdit, QPushButton,
    QLabel, QMessageBox, QFileDialog, QCheckBox, QScrollArea, QFrame,
    QRadioButton, QButtonGroup, QApplication, QComboBox, QProgressBar,
    QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt, QCoreApplication, QThread, QObject, Signal, QTimer
from PySide6.QtGui import QFont, QColor
from lxml import etree
from api.mintrud_api import (
    load_api_key, save_api_key, push_xml, push_xml_signed,
    get_by_set_id, get_by_snils, export_records_to_xlsx,
)
from utils.error_utils import safe_message_box
from utils.proxy_manager import (
    load_proxy_settings, save_proxy_settings, detect_windows_proxy
)
from utils.audit import log_audit
from network.client import (
    get_network_diagnostics, test_external_access, NetworkStatus
)

logger = logging.getLogger(__name__)


class _ProxyTestWorker(QObject):
    finished = Signal(str, bool)

    def __init__(self, tls_verify):
        super().__init__()
        self.tls_verify = tls_verify

    def run(self):
        diag = get_network_diagnostics()
        status, msg = test_external_access(
            url="https://edu.rosmintrud.ru",
            timeout=30,
            tls_verify=self.tls_verify,
        )
        corp_label = "Да" if diag.get('is_corporate_env') else "Нет"
        ssl_insp = "Да" if diag.get('ssl_inspection_detected') else "Нет"
        result_text = (
            "Диагностика сети:\n\n"
            "Обнаруженный прокси: %s\n"
            "Корпоративная среда: %s\n"
            "SSL-инспекция: %s\n"
            "Метод авторизации: %s\n"
            "Negotiate доступен: %s\n"
            "TLS доступен: %s\n"
            "Авторизация прокси: %s\n\n"
            "Результат теста:\n"
            "Статус: %s\n"
            "Сообщение: %s"
        ) % (
            diag.get('detected_proxy', 'Не обнаружен'),
            corp_label,
            ssl_insp,
            diag.get('auth_method', 'Нет'),
            'Да' if diag.get('negotiate_available') else 'Нет',
            'Да' if diag.get('tls_ok') else 'Нет',
            'Да' if diag.get('proxy_auth_ok') else 'Нет',
            status.value,
            msg,
        )
        rec = diag.get('recommendation', '')
        if rec:
            result_text += "\n\nРекомендация:\n%s" % rec
        self.finished.emit(result_text, status == NetworkStatus.SUCCESS)


class _SnilsQueryWorker(QObject):
    finished = Signal(dict)

    def __init__(self, api_key, snils, proxy_settings):
        super().__init__()
        self.api_key = api_key
        self.snils = snils
        self.proxy_settings = proxy_settings

    def run(self):
        from api.mintrud_api import get_by_snils
        try:
            result = get_by_snils(self.api_key, self.snils, proxy_settings=self.proxy_settings)
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit({"success": False, "error": str(e), "records": []})


class DataTransferTab(QWidget):
    def __init__(self):
        super().__init__()
        from utils.app_paths import get_app_data_dir, get_resource_dir
        self.resource_dir = get_resource_dir()
        self.data_dir = get_app_data_dir()
        self.schema_dir = os.path.join(self.resource_dir, "schema")
        os.makedirs(self.data_dir, exist_ok=True)

        self._journal_add_callback = None
        self._journal_update_callback = None
        self._snils_thread = None
        self._snils_worker = None
        self._tls_warned_this_session = False
        self._tls_startup_warning_shown = False

        self._setup_ui()
        self._connect_signals()
        self._load_settings()

    def set_journal_callback(self, add_callback, update_callback):
        self._journal_add_callback = add_callback
        self._journal_update_callback = update_callback

    # ============================================================
    # UI Setup
    # ============================================================

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll_area = scroll

        content = QWidget()
        self._scroll_layout = QVBoxLayout(content)
        self._scroll_layout.setSpacing(12)
        self._scroll_layout.setContentsMargins(0, 0, 0, 0)

        self._scroll_layout.addWidget(self._create_api_key_group())
        self._scroll_layout.addWidget(self._create_proxy_group())
        self._scroll_layout.addWidget(self._create_sig_group())
        self._scroll_layout.addWidget(self._create_send_xml_group())
        self._scroll_layout.addWidget(self._create_query_setid_group())
        self._scroll_layout.addWidget(self._create_query_snils_group())
        self._scroll_layout.addStretch()

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _connect_signals(self):
        self.proxy_mode_group.buttonClicked.connect(self._on_proxy_mode_changed)
        self.proxy_save_btn.clicked.connect(self.save_proxy_settings_ui)
        self.proxy_test_btn.clicked.connect(self.test_proxy)
        self.select_sig_btn.clicked.connect(self.select_sig_file)
        self.send_xml_signed_btn.clicked.connect(self.send_xml_signed)
        self.tls_checkbox.toggled.connect(self._on_tls_verify_toggled)

    def _load_settings(self):
        self.load_api_key()
        self.load_proxy_settings()

    # ============================================================
    # Group: API Key
    # ============================================================

    def _create_api_key_group(self):
        group = QGroupBox("API ключ")

        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        row = QHBoxLayout()
        self.api_key_input = QLineEdit()
        self.api_key_input.setMaxLength(32)
        self.api_key_input.setPlaceholderText("32 символа")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.api_key_toggle_btn = QPushButton("Показать")
        self.api_key_toggle_btn.setCheckable(True)
        self.api_key_toggle_btn.setToolTip("Зажмите для просмотра ключа")
        self.api_key_toggle_btn.pressed.connect(lambda: self.api_key_input.setEchoMode(QLineEdit.EchoMode.Normal))
        self.api_key_toggle_btn.released.connect(lambda: self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password))

        paste_btn = QPushButton("Вставить")
        paste_btn.clicked.connect(self.paste_api_key)

        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.save_api_key)

        row.addWidget(QLabel("API ключ:"))
        row.addWidget(self.api_key_input)
        row.addWidget(self.api_key_toggle_btn)
        row.addWidget(paste_btn)
        row.addWidget(save_btn)
        row.addStretch()
        layout.addLayout(row)

        layout.addStretch()

        return group

    # ============================================================
    # Group: Proxy Settings
    # ============================================================

    def scroll_to_proxy(self):
        proxy = getattr(self, '_proxy_group', None)
        area = getattr(self, '_scroll_area', None)
        if proxy and area:
            area.ensureWidgetVisible(proxy)

    def _create_proxy_group(self):
        group = QGroupBox("Настройки прокси")
        self._proxy_group = group

        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        mode_row = QHBoxLayout()
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setStyleSheet("QFrame { border-radius: 6px; padding: 6px; }")
        inner = QHBoxLayout(frame)
        inner.setSpacing(20)

        self.proxy_off_rb = QRadioButton("Без прокси")
        self.proxy_off_rb.setChecked(True)
        self.proxy_auto_rb = QRadioButton("Авто (системные)")
        self.proxy_manual_rb = QRadioButton("Вручную")
        self.proxy_mode_group = QButtonGroup(self)
        self.proxy_mode_group.addButton(self.proxy_off_rb, 0)
        self.proxy_mode_group.addButton(self.proxy_auto_rb, 1)
        self.proxy_mode_group.addButton(self.proxy_manual_rb, 2)

        inner.addWidget(self.proxy_off_rb)
        inner.addWidget(self.proxy_auto_rb)
        inner.addWidget(self.proxy_manual_rb)
        inner.addStretch()
        mode_row.addWidget(frame)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        self.proxy_auto_info = QLabel()
        self.proxy_auto_info.setWordWrap(True)
        self.proxy_auto_info.setVisible(False)
        layout.addWidget(self.proxy_auto_info)

        self.proxy_manual_container = QFrame()
        self.proxy_manual_container.setFrameShape(QFrame.Shape.StyledPanel)
        self.proxy_manual_container.setStyleSheet(
            "QFrame { border-radius: 6px; padding: 10px; }"
        )
        manual_layout = QVBoxLayout(self.proxy_manual_container)
        manual_layout.setContentsMargins(8, 8, 8, 8)
        manual_layout.setSpacing(8)

        url_row = QHBoxLayout()
        self.proxy_url_input = QLineEdit()
        self.proxy_url_input.setPlaceholderText("http://proxy.example.invalid:3128")
        url_row.addWidget(QLabel("Адрес прокси:"))
        url_row.addWidget(self.proxy_url_input)
        url_row.addStretch()
        manual_layout.addLayout(url_row)

        cred_row = QHBoxLayout()
        self.proxy_user_input = QLineEdit()
        self.proxy_user_input.setPlaceholderText("Логин (если требуется)")
        self.proxy_pass_input = QLineEdit()
        self.proxy_pass_input.setPlaceholderText("Пароль (если требуется)")
        self.proxy_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        cred_row.addWidget(QLabel("Логин:"))
        cred_row.addWidget(self.proxy_user_input)
        cred_row.addSpacing(16)
        cred_row.addWidget(QLabel("Пароль:"))
        cred_row.addWidget(self.proxy_pass_input)
        cred_row.addStretch()
        manual_layout.addLayout(cred_row)

        self.proxy_negotiate_cb = QCheckBox(
            "Использовать Windows-авторизацию (Negotiate/Kerberos)"
        )
        self.proxy_negotiate_cb.setToolTip(
            "Для корпоративных прокси с авторизацией через Active Directory.\n"
            "Приложение автоматически передаст токен текущего пользователя Windows.\n"
            "Ввод логина/пароля не требуется."
        )
        manual_layout.addWidget(self.proxy_negotiate_cb)

        self.proxy_manual_container.setVisible(False)
        layout.addWidget(self.proxy_manual_container)

        extra_row = QHBoxLayout()
        self.tls_checkbox = QCheckBox("TLS верификация (рекомендуется)")
        self.tls_checkbox.setToolTip(
            "Проверка SSL-сертификата. Отключайте только при работе "
            "через корпоративный прокси с SSL-инспекцией"
        )
        self.tls_checkbox.setChecked(True)
        extra_row.addWidget(self.tls_checkbox)

        self.tls_warning_label = QLabel("⚠ TLS: небезопасно")
        self.tls_warning_label.setStyleSheet(
            "color: #CC0000; font-weight: bold; padding: 2px 8px; "
            "border: 1px solid #CC0000; border-radius: 3px;"
        )
        self.tls_warning_label.setVisible(False)
        extra_row.addWidget(self.tls_warning_label)

        extra_row.addSpacing(20)
        extra_row.addWidget(QLabel("Transport:"))
        from api.mintrud_api import get_available_backends
        self.backend_combo = QComboBox()
        self.backend_combo.addItem("Auto", "auto")
        for be in get_available_backends():
            self.backend_combo.addItem(be.capitalize(), be)
        self.backend_combo.setFixedWidth(120)
        self.backend_combo.currentIndexChanged.connect(self._on_backend_change)
        extra_row.addWidget(self.backend_combo)
        extra_row.addStretch()
        layout.addLayout(extra_row)

        btn_row = QHBoxLayout()
        self.proxy_save_btn = QPushButton("Сохранить настройки прокси")
        self.proxy_test_btn = QPushButton("Тест подключения")
        btn_row.addWidget(self.proxy_save_btn)
        btn_row.addWidget(self.proxy_test_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        return group

    def _save_tls_setting(self, checked: bool):
        from utils.proxy_manager import save_proxy_settings
        settings = self._get_proxy_settings_from_ui()
        settings['tls_verify'] = checked
        save_proxy_settings(self.data_dir, settings)

    def _show_tls_startup_warning(self):
        w = QMessageBox(self)
        w.setWindowTitle("TLS отключён")
        w.setIcon(QMessageBox.Icon.Warning)
        w.setText(
            "Проверка TLS-сертификата отключена в настройках.\n\n"
            "Соединение не защищено — возможен перехват ПДн "
            "(ФИО, СНИЛС, ИНН, реестры).\n\n"
            "Включите TLS верификацию в настройках прокси, "
            "если вы не используете корпоративную SSL-инспекцию."
        )
        w.setWindowFlags(w.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        w.exec()

    def _warn_tls_if_needed(self) -> bool:
        if self._tls_warned_this_session:
            return True
        if not self.tls_checkbox.isChecked():
            reply = QMessageBox.warning(
                self,
                "Соединение небезопасно",
                "TLS-верификация отключена. Данные (ФИО, СНИЛС, ИНН) "
                "могут быть перехвачены.\n\n"
                "Продолжить отправку?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return False
            self._tls_warned_this_session = True
        return True

    def _get_proxy_settings_from_ui(self):
        mode_id = self.proxy_mode_group.checkedId()
        mode_map = {0: 'off', 1: 'auto', 2: 'manual'}
        mode = mode_map.get(mode_id, 'off')
        return {
            'mode': mode,
            'url': self.proxy_url_input.text().strip(),
            'username': self.proxy_user_input.text().strip(),
            'password': self.proxy_pass_input.text().strip(),
            'use_negotiate': self.proxy_negotiate_cb.isChecked(),
            'backend': self.backend_combo.currentData(),
        }

    def _on_tls_verify_toggled(self, checked: bool):
        if not checked:
            reply = QMessageBox.warning(
                self,
                "Предупреждение безопасности",
                "Вы отключаете проверку TLS-сертификата. Это позволяет атакующему "
                "перехватить или подменить данные (ФИО/СНИЛС/ИНН/реестры).\n\n"
                "Используйте только если вы понимаете риск "
                "(например, корпоративная SSL-инспекция).\n\n"
                "Это действие будет зафиксировано в журнале аудита.",
                QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            disable_btn = QPushButton("Отключить проверку TLS")
            reply.addButton(disable_btn, QMessageBox.ButtonRole.AcceptRole)
            reply.exec()
            if reply.clickedButton() != disable_btn:
                self.tls_checkbox.setChecked(True)
                return
            self.tls_warning_label.setVisible(True)
            self._save_tls_setting(False)
            log_audit("TLS_WARNING", "TLS verification disabled by user")
        else:
            self.tls_warning_label.setVisible(False)
            log_audit("TLS_WARNING", "TLS verification enabled by user")

    def _on_proxy_mode_changed(self, button):
        mode = self.proxy_mode_group.id(button)
        if mode == 0:
            self.proxy_manual_container.setVisible(False)
            self.proxy_auto_info.setVisible(False)
        elif mode == 1:
            self.proxy_manual_container.setVisible(False)
            sys_proxy = detect_windows_proxy()
            if sys_proxy:
                self.proxy_auto_info.setText(f"Обнаружен системный прокси: {sys_proxy}")
            else:
                self.proxy_auto_info.setText("Системный прокси не обнаружен в настройках Windows")
            self.proxy_auto_info.setVisible(True)
        else:
            self.proxy_manual_container.setVisible(True)
            self.proxy_auto_info.setVisible(False)

    # ============================================================
    # Group: Signature file (.sig)
    # ============================================================

    def _create_sig_group(self):
        group = QGroupBox("Электронная подпись (.sig)")

        row = QHBoxLayout(group)
        self.sig_file_input = QLineEdit()
        self.sig_file_input.setReadOnly(True)
        self.sig_file_input.setPlaceholderText("Файл .sig не выбран (только для отправки в РОЛ)")

        self.select_sig_btn = QPushButton("Выбрать")

        row.addWidget(QLabel("Файл подписи:"))
        row.addWidget(self.sig_file_input)
        row.addWidget(self.select_sig_btn)
        row.addStretch()

        return group

    def select_sig_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл подписи", "", "Signature Files (*.sig);;All Files (*.*)"
        )
        if not file_path:
            return

        if not os.path.exists(file_path):
            QMessageBox.warning(self, "Ошибка", "Файл не найден")
            return

        if os.path.getsize(file_path) == 0:
            QMessageBox.warning(self, "Ошибка", "Файл пустой")
            return

        self.sig_file_input.setText(file_path)

    # ============================================================
    # Group: Send XML
    # ============================================================

    def _create_send_xml_group(self):
        group = QGroupBox("Отправка XML")

        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        file_row = QHBoxLayout()
        self.xml_file_input = QLineEdit()
        self.xml_file_input.setReadOnly(True)
        self.xml_file_input.setPlaceholderText("Файл не выбран")

        select_xml_btn = QPushButton("Выбрать")
        select_xml_btn.clicked.connect(self.select_xml_file)

        file_row.addWidget(QLabel("XML файл:"))
        file_row.addWidget(self.xml_file_input)
        file_row.addWidget(select_xml_btn)
        file_row.addStretch()
        layout.addLayout(file_row)

        send_row = QHBoxLayout()
        self.send_xml_btn = QPushButton("\u2B06 Отправить XML на сервер")
        self.send_xml_btn.setStyleSheet("""
            QPushButton { color: white; background-color: #27AE60;
                border: none; padding: 12px 28px;
                border-radius: 6px; font-weight: bold; font-size: 14px}
            QPushButton:hover { background-color: #219A52}
            QPushButton:disabled { background-color: #95A5A6}
        """)
        self.send_xml_btn.setMinimumHeight(44)
        self.send_xml_btn.clicked.connect(self.send_xml)
        send_row.addWidget(self.send_xml_btn)

        send_row.addSpacing(12)

        self.send_xml_signed_btn = QPushButton("\u2713 Отправить XML и ПОДПИСАТЬ")
        self.send_xml_signed_btn.setStyleSheet("""
            QPushButton { color: white; background-color: #E74C3C;
                border: none; padding: 12px 28px;
                border-radius: 6px; font-weight: bold; font-size: 14px}
            QPushButton:hover { background-color: #C0392B}
            QPushButton:disabled { background-color: #95A5A6}
        """)
        self.send_xml_signed_btn.setMinimumHeight(44)
        send_row.addWidget(self.send_xml_signed_btn)

        send_row.addStretch()
        layout.addLayout(send_row)

        self.send_progress = QProgressBar()
        self.send_progress.setRange(0, 0)
        self.send_progress.setVisible(False)
        self.send_progress.setFixedHeight(6)
        self.send_progress.setTextVisible(False)
        layout.addWidget(self.send_progress)

        setid_row = QHBoxLayout()
        self.last_setid_display = QLineEdit()
        self.last_setid_display.setReadOnly(True)
        self.last_setid_display.setPlaceholderText("SetId появится после отправки")
        setid_row.addWidget(QLabel("Последний SetId:"))
        setid_row.addWidget(self.last_setid_display)
        setid_row.addStretch()
        layout.addLayout(setid_row)

        return group

    # ============================================================
    # Group: Query by SetId
    # ============================================================

    def _create_query_setid_group(self):
        group = QGroupBox("Запрос по SetId")

        row = QHBoxLayout(group)
        self.query_setid_input = QLineEdit()
        self.query_setid_input.setPlaceholderText("SetId из ответа сервера")

        query_btn = QPushButton("Запросить номера")
        query_btn.clicked.connect(self.query_by_setid)

        row.addWidget(QLabel("Введите номер набора:"))
        row.addWidget(self.query_setid_input)
        row.addWidget(query_btn)
        row.addStretch()

        return group

    # ============================================================
    # Group: Query by SNILS
    # ============================================================

    def _create_query_snils_group(self):
        group = QGroupBox("Запрос по СНИЛС")

        row = QHBoxLayout(group)
        self.query_snils_input = QLineEdit()
        self.query_snils_input.setPlaceholderText("123-456-789 00 или 12345678900")

        self.query_snils_btn = QPushButton("Отправить запрос")
        self.query_snils_btn.clicked.connect(self.query_by_snils)

        row.addWidget(QLabel("Введите СНИЛС:"))
        row.addWidget(self.query_snils_input)
        row.addWidget(self.query_snils_btn)
        row.addStretch()

        return group

    # ============================================================
    # API Key Logic
    # ============================================================

    def load_api_key(self):
        key = load_api_key(self.data_dir)
        if key:
            self.api_key_input.setText(key)

    def paste_api_key(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            self.api_key_input.setText(text.strip())

    def save_api_key(self):
        api_key = self.api_key_input.text().strip()
        if len(api_key) != 32:
            safe_message_box(self, QMessageBox.Icon.Warning, "Ошибка", f"Длина ключа: {len(api_key)} (требуется 32 символа)")
            return
        ok, msg = save_api_key(api_key, self.data_dir)
        if ok:
            safe_message_box(self, QMessageBox.Icon.Information, "Успех", "API ключ сохранён")
        else:
            safe_message_box(self, QMessageBox.Icon.Warning, "Ошибка", msg)

    # ============================================================
    # Proxy Logic
    # ============================================================

    def load_proxy_settings(self):
        settings = load_proxy_settings(self.data_dir)
        mode = settings.get('mode', 'off')

        if mode == 'auto':
            self.proxy_auto_rb.setChecked(True)
        elif mode == 'manual':
            self.proxy_manual_rb.setChecked(True)
        else:
            self.proxy_off_rb.setChecked(True)

        self.proxy_url_input.setText(settings.get('url', ''))
        self.proxy_user_input.setText(settings.get('username', ''))
        self.proxy_pass_input.setText(settings.get('password', ''))
        tls_verify = settings.get('tls_verify', True)
        self.tls_checkbox.setChecked(tls_verify)
        self.tls_warning_label.setVisible(not tls_verify)
        self.proxy_negotiate_cb.setChecked(settings.get('use_negotiate', False))

        if not tls_verify and not self._tls_startup_warning_shown:
            self._tls_startup_warning_shown = True
            log_audit("TLS_WARNING", "Startup with tls_verify=False")
            QTimer.singleShot(500, lambda: self._show_tls_startup_warning())
        backend_val = settings.get('backend', 'auto')
        idx = self.backend_combo.findData(backend_val)
        if idx >= 0:
            self.backend_combo.setCurrentIndex(idx)

        if mode == 'auto':
            self._on_proxy_mode_changed(self.proxy_auto_rb)
        elif mode == 'manual':
            self._on_proxy_mode_changed(self.proxy_manual_rb)
        else:
            self._on_proxy_mode_changed(self.proxy_off_rb)

    def save_proxy_settings_ui(self):
        mode_id = self.proxy_mode_group.checkedId()
        mode_map = {0: 'off', 1: 'auto', 2: 'manual'}
        mode = mode_map.get(mode_id, 'off')

        settings = {
            'mode': mode,
            'url': self.proxy_url_input.text().strip(),
            'username': self.proxy_user_input.text().strip(),
            'password': self.proxy_pass_input.text().strip(),
            'tls_verify': self.tls_checkbox.isChecked(),
            'use_negotiate': self.proxy_negotiate_cb.isChecked(),
            'backend': self.backend_combo.currentData(),
        }

        ok, msg = save_proxy_settings(self.data_dir, settings)
        if ok:
            log_audit("PROXY_CHANGE", "mode=%s, tls_verify=%s" % (mode, settings.get('tls_verify', True)))
            mode_text = {'off': 'Без прокси', 'auto': 'Авто (системный)', 'manual': 'Ручной'}
            safe_message_box(self, QMessageBox.Icon.Information, "Успех", f"Режим: {mode_text.get(mode, mode)}\n{msg}")
        else:
            safe_message_box(self, QMessageBox.Icon.Warning, "Ошибка", msg)

    def test_proxy(self):
        self.proxy_test_btn.setEnabled(False)
        self.proxy_test_btn.setText("Тестирование...")
        QCoreApplication.processEvents()

        self._proxy_thread = QThread()
        self._proxy_worker = _ProxyTestWorker(
            tls_verify=self.tls_checkbox.isChecked(),
        )
        self._proxy_worker.moveToThread(self._proxy_thread)
        self._proxy_thread.started.connect(self._proxy_worker.run)
        self._proxy_worker.finished.connect(self._on_proxy_test_result)
        self._proxy_worker.finished.connect(self._proxy_thread.quit)
        self._proxy_thread.finished.connect(self._proxy_worker.deleteLater)
        self._proxy_thread.finished.connect(self._proxy_thread.deleteLater)
        self._proxy_thread.start()

    def _on_proxy_test_result(self, result_text, is_success):
        if is_success:
            safe_message_box(self, QMessageBox.Icon.Information, "Успех", result_text)
        else:
            safe_message_box(self, QMessageBox.Icon.Warning, "Проблема с доступом", result_text)
        self.proxy_test_btn.setEnabled(True)
        self.proxy_test_btn.setText("Тест подключения")

    def _on_backend_change(self, index):
        backend_name = self.backend_combo.currentData()
        log_audit("BACKEND_CHANGE", f"backend={backend_name}")

    def _get_proxy_settings(self):
        mode_id = self.proxy_mode_group.checkedId()
        mode_map = {0: 'off', 1: 'auto', 2: 'manual'}
        mode = mode_map.get(mode_id, 'off')
        return {
            'mode': mode,
            'url': self.proxy_url_input.text().strip(),
            'username': self.proxy_user_input.text().strip(),
            'password': self.proxy_pass_input.text().strip(),
            'tls_verify': self.tls_checkbox.isChecked(),
            'backend': self.backend_combo.currentData(),
        }

    # ============================================================
    # Send XML Logic
    # ============================================================

    def select_xml_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите XML файл", "", "XML Files (*.xml)"
        )
        if not file_path:
            return

        if not os.path.exists(file_path):
            QMessageBox.warning(self, "Ошибка", "Файл не найден")
            return

        if os.path.getsize(file_path) == 0:
            QMessageBox.warning(self, "Ошибка", "Файл пустой")
            return

        try:
            parser = etree.XMLParser(
                resolve_entities=False,
                no_network=True,
                dtd_validation=False,
                huge_tree=False,
            )
            tree = etree.parse(file_path, parser)
            root = tree.getroot()
            logger.info("XML loaded: root=%s, children=%d", root.tag, len(root))
        except etree.XMLSyntaxError as e:
            safe_message_box(self, QMessageBox.Icon.Warning, "Ошибка", f"Невалидный XML:\n{e}")
            return
        except (OSError, ValueError) as e:
            logger.error("Error reading XML file: %s", e)
            safe_message_box(self, QMessageBox.Icon.Warning, "Ошибка", f"Ошибка чтения файла:\n{e}")
            return

        xsd_files = [f for f in os.listdir(self.schema_dir) if f.endswith('.xsd')]
        if xsd_files:
            xsd_path = os.path.join(self.schema_dir, xsd_files[0])
            try:
                xsd_parser = etree.XMLParser(
                    resolve_entities=False,
                    no_network=True,
                    dtd_validation=False,
                    huge_tree=False,
                )
                schema_doc = etree.parse(xsd_path, xsd_parser)
                schema = etree.XMLSchema(schema_doc)
                schema.assertValid(tree)
            except etree.DocumentInvalid as e:
                safe_message_box(self, QMessageBox.Icon.Warning, "Ошибка валидации", f"Файл не соответствует схеме XSD:\n{e}")
                return
            except (etree.XMLSyntaxError, OSError, ValueError) as e:
                logger.error("XSD validation error: %s", e)
                safe_message_box(self, QMessageBox.Icon.Warning, "Ошибка", f"Ошибка валидации по XSD:\n{e}")
                return

        self.xml_file_input.setText(file_path)

    def send_xml(self):
        api_key = self.api_key_input.text().strip()
        xml_file = self.xml_file_input.text()

        if len(api_key) != 32:
            QMessageBox.warning(self, "Ошибка", "Проверьте API ключ (32 символа)")
            return

        if not xml_file or not os.path.exists(xml_file):
            QMessageBox.warning(self, "Ошибка", "Выберите XML файл")
            return

        if not self._warn_tls_if_needed():
            return

        xml_records_data = self._parse_xml_for_journal(xml_file)
        proxy_settings = self._get_proxy_settings()

        self.send_progress.setVisible(True)
        self.send_xml_btn.setEnabled(False)
        self.send_xml_btn.setText("Отправка...")
        QCoreApplication.processEvents()

        try:
            result = push_xml(api_key, xml_file, proxy_settings=proxy_settings)

            if result["success"]:
                set_id = result.get("set_id", "")
                self.last_setid_display.setText(set_id)

                if self._journal_add_callback and xml_records_data:
                    self._journal_add_callback(xml_records_data, set_id, xml_file)

                msg = QMessageBox(self)
                msg.setWindowTitle("Успех")
                msg.setText("Данные загружены на сервер")
                msg.setInformativeText(
                    '<span style="color:red; font-weight:bold; font-size:14px;">'
                    'Запишите номер набора: %s</span>' % set_id
                )
                msg.setTextFormat(Qt.TextFormat.RichText)
                msg.exec()
            elif result.get("ssl_error_detected"):
                retry = QMessageBox.question(
                    self,
                    "SSL ошибка",
                    "Сервер недоступен из-за SSL-инспекции корпоративного прокси.\n\n"
                    "%s\n\n"
                    "Попробовать с отключенной проверкой TLS?" % result.get("ssl_recommendation", ""),
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if retry == QMessageBox.Yes:
                    log_audit("TLS_WARNING", "Retry with TLS disabled after SSL error")
                    self.tls_checkbox.setChecked(False)
                    QCoreApplication.processEvents()
                    self.send_xml()
                    return
                else:
                    safe_message_box(self, QMessageBox.Icon.Critical, "SSL ошибка", result.get("error", "SSL handshake failed"))
            else:
                error_msg = result.get("error", "Неизвестная ошибка")
                raw_response = result.get("raw_response", "")
                msg = QMessageBox(self)
                msg.setWindowTitle("Ошибка загрузки")
                msg.setIcon(QMessageBox.Icon.Critical)
                msg.setText(error_msg)
                if raw_response:
                    msg.setDetailedText("Ответ сервера:\n%s" % raw_response[:500])
                msg.exec()
        except Exception as e:
            logger.exception("Ошибка отправки XML")
            safe_message_box(self, QMessageBox.Icon.Critical, "Ошибка", f"Ошибка отправки XML:\n{e}")
        finally:
            self.send_progress.setVisible(False)
            self.send_xml_btn.setEnabled(True)
            self.send_xml_btn.setText("\u2B06 Отправить XML на сервер")

    def send_xml_signed(self):
        api_key = self.api_key_input.text().strip()
        xml_file = self.xml_file_input.text()
        sig_file = self.sig_file_input.text()

        if len(api_key) != 32:
            QMessageBox.warning(self, "Ошибка", "Проверьте API ключ (32 символа)")
            return

        if not xml_file or not os.path.exists(xml_file):
            QMessageBox.warning(self, "Ошибка", "Выберите XML файл")
            return

        if not sig_file or not os.path.exists(sig_file):
            QMessageBox.warning(self, "Ошибка", "Выберите файл подписи .sig")
            return

        if not self._warn_tls_if_needed():
            return

        reply = QMessageBox.question(
            self, "Подтверждение",
            "Отправить XML с электронной подписью в РОЛ?\n\n"
            "Будет выполнена отправка подписанного набора в реестр.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        xml_records_data = self._parse_xml_for_journal(xml_file)
        proxy_settings = self._get_proxy_settings()

        self.send_progress.setVisible(True)
        self.send_xml_signed_btn.setEnabled(False)
        self.send_xml_signed_btn.setText("Отправка...")
        QCoreApplication.processEvents()

        try:
            result = push_xml_signed(api_key, xml_file, sig_file, proxy_settings=proxy_settings)

            if result["success"]:
                set_id = result.get("set_id", "")
                self.last_setid_display.setText(set_id)

                if self._journal_add_callback and xml_records_data:
                    self._journal_add_callback(xml_records_data, set_id, xml_file)

                msg = QMessageBox(self)
                msg.setWindowTitle("Успех")
                msg.setText("Подписанные данные отправлены в РОЛ")
                msg.setInformativeText(
                    '<span style="color:red; font-weight:bold; font-size:14px;">'
                    'Запишите номер набора: %s</span>' % set_id
                )
                msg.setTextFormat(Qt.TextFormat.RichText)
                msg.exec()
            elif result.get("ssl_error_detected"):
                retry = QMessageBox.question(
                    self,
                    "SSL ошибка",
                    "Сервер недоступен из-за SSL-инспекции корпоративного прокси.\n\n"
                    "%s\n\n"
                    "Попробовать с отключенной проверкой TLS?" % result.get("ssl_recommendation", ""),
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if retry == QMessageBox.Yes:
                    log_audit("TLS_WARNING", "Retry with TLS disabled after SSL error (signed)")
                    self.tls_checkbox.setChecked(False)
                    QCoreApplication.processEvents()
                    self.send_xml_signed()
                    return
                else:
                    safe_message_box(self, QMessageBox.Icon.Critical, "SSL ошибка", result.get("error", "SSL handshake failed"))
            else:
                error_msg = result.get("error", "Неизвестная ошибка")
                raw_response = result.get("raw_response", "")
                msg = QMessageBox(self)
                msg.setWindowTitle("Ошибка загрузки")
                msg.setIcon(QMessageBox.Icon.Critical)
                msg.setText(error_msg)
                if raw_response:
                    msg.setDetailedText("Ответ сервера:\n%s" % raw_response[:500])
                msg.exec()
        except Exception as e:
            logger.exception("Ошибка отправки подписанного XML")
            safe_message_box(self, QMessageBox.Icon.Critical, "Ошибка", f"Ошибка отправки подписанного XML:\n{e}")
        finally:
            self.send_progress.setVisible(False)
            self.send_xml_signed_btn.setEnabled(True)
            self.send_xml_signed_btn.setText("\u2713 Отправить XML и ПОДПИСАТЬ")

    # ============================================================
    # Query Logic
    # ============================================================

    def query_by_setid(self):
        api_key = self.api_key_input.text().strip()
        set_id = self.query_setid_input.text().strip()

        if len(api_key) != 32:
            QMessageBox.warning(self, "Ошибка", "Проверьте API ключ (32 символа)")
            return

        if not set_id:
            QMessageBox.warning(self, "Ошибка", "Введите SetId")
            return

        proxy_settings = self._get_proxy_settings()
        try:
            result = get_by_set_id(api_key, set_id, proxy_settings=proxy_settings)
        except Exception as e:
            logger.exception("Ошибка запроса по SetId")
            safe_message_box(self, QMessageBox.Icon.Critical, "Ошибка", f"Ошибка запроса по SetId:\n{e}")
            return

        if not result["success"]:
            safe_message_box(self, QMessageBox.Icon.Critical, "Ошибка", result.get("error", "Неизвестная ошибка"))
            return

        records = result.get("records", [])
        if not records:
            QMessageBox.information(self, "Информация", "Записей не найдено")
            return

        if self._journal_update_callback:
            base_no_map = {}
            for rec in records:
                snils_raw = rec.get('Snils', '')
                base_no = rec.get('baseNo', '')
                snils_clean = ''.join(c for c in snils_raw if unicodedata.category(c) != 'Zs')
                snils_clean = snils_clean.replace('-', '')
                if snils_clean:
                    base_no_map[snils_clean] = base_no
            if base_no_map:
                self._journal_update_callback(set_id, base_no_map)

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить XLSX", f"{set_id}.xlsx", "Excel Files (*.xlsx)"
        )
        if file_path:
            ok, msg = export_records_to_xlsx(records, file_path)
            if ok:
                safe_message_box(self, QMessageBox.Icon.Information, "Успех", f"Сохранено {len(records)} записей\n{msg}")
            else:
                safe_message_box(self, QMessageBox.Icon.Warning, "Ошибка", msg)

    def query_by_snils(self):
        api_key = self.api_key_input.text().strip()
        snils_raw = self.query_snils_input.text().strip()

        if len(api_key) != 32:
            QMessageBox.warning(self, "Ошибка", "Проверьте API ключ (32 символа)")
            return

        if not snils_raw:
            QMessageBox.warning(self, "Ошибка", "Введите СНИЛС")
            return

        snils_clean = ''.join(c for c in snils_raw if unicodedata.category(c) != 'Zs')
        snils_clean = snils_clean.replace('-', '')
        if not snils_clean.isdigit() or len(snils_clean) != 11:
            QMessageBox.warning(self, "Ошибка", "СНИЛС должен содержать 11 цифр")
            return
        snils = f"{snils_clean[0:3]}-{snils_clean[3:6]}-{snils_clean[6:9]} {snils_clean[9:11]}"

        if self._snils_thread and self._snils_thread.isRunning():
            QMessageBox.warning(self, "Ошибка", "Запрос уже выполняется")
            return

        self._snils_thread = QThread()
        self._snils_worker = _SnilsQueryWorker(
            api_key=api_key, snils=snils, proxy_settings=self._get_proxy_settings()
        )
        self._snils_worker.moveToThread(self._snils_thread)
        self._snils_thread.started.connect(self._snils_worker.run)
        self._snils_worker.finished.connect(self._on_snils_query_result)
        self._snils_worker.finished.connect(self._snils_thread.quit)
        self._snils_thread.finished.connect(self._snils_worker.deleteLater)
        self._snils_thread.finished.connect(self._snils_thread.deleteLater)
        self._snils_thread.finished.connect(self._re_enable_snils_btn)
        self._snils_thread.start()

        self._set_snils_query_state(False, "Запрос...")

    def _set_snils_query_state(self, enabled: bool, text: str = None):
        btn = getattr(self, 'query_snils_btn', None)
        if btn:
            btn.setEnabled(enabled)
            if text:
                btn.setText(text)

    def _re_enable_snils_btn(self):
        btn = getattr(self, 'query_snils_btn', None)
        if btn:
            btn.setEnabled(True)
            btn.setText("Запросить")

    def _on_snils_query_result(self, result):
        if not result["success"]:
            safe_message_box(self, QMessageBox.Icon.Critical, "Ошибка", result.get("error", "Неизвестная ошибка"))
            return

        records = result.get("records", [])
        if not records:
            QMessageBox.information(self, "Информация", "Записей не найдено")
            return

        first = records[0]
        name_parts = [
            first.get('LastName', '')[:1] + '***' if first.get('LastName', '') else '',
            first.get('FirstName', '')[:1] + '***' if first.get('FirstName', '') else '',
            first.get('MiddleName', '')[:1] + '***' if first.get('MiddleName', '') else '',
        ]
        masked_name = ' '.join(p for p in name_parts if p)
        safe_message_box(self, QMessageBox.Icon.Information, "Найдено", f"Записей: {len(records)}\n{masked_name}")

        snils_clean = ''.join(c for c in self.query_snils_input.text().strip() if c.isdigit())
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить XLSX", f"{snils_clean}.xlsx", "Excel Files (*.xlsx)"
        )
        if file_path:
            ok, msg = export_records_to_xlsx(records, file_path)
            if ok:
                safe_message_box(self, QMessageBox.Icon.Information, "Успех", f"Сохранено {len(records)} записей\n{msg}")
            else:
                safe_message_box(self, QMessageBox.Icon.Warning, "Ошибка", msg)

    # ============================================================
    # XML Parsing for Journal
    # ============================================================

    def _parse_xml_for_journal(self, xml_file_path):
        from defusedxml.ElementTree import parse as _xparse
        from defusedxml.common import DefusedXmlException

        records = []
        try:
            tree = _xparse(xml_file_path)
            root = tree.getroot()

            for record in root.findall('RegistryRecord'):
                worker = record.find('Worker')
                test = record.find('Test')

                if worker is None or test is None:
                    continue

                def get_text(elem, tag):
                    child = elem.find(tag)
                    return child.text.strip() if child is not None and child.text else ''

                rec = {
                    'last_name': get_text(worker, 'LastName'),
                    'first_name': get_text(worker, 'FirstName'),
                    'middle_name': get_text(worker, 'MiddleName'),
                    'snils': get_text(worker, 'Snils'),
                    'position': get_text(worker, 'Position'),
                    'program': test.get('learnProgramId', ''),
                    'date': get_text(test, 'Date'),
                    'protocol': get_text(test, 'ProtocolNumber'),
                }
                records.append(rec)
        except (DefusedXmlException, ValueError) as e:
            logger.warning(f"Failed to parse XML for journal: {e}")

        return records
