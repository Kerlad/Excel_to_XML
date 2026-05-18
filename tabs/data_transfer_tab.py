import os
import logging
import unicodedata
import xml.etree.ElementTree as ET
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLineEdit, QPushButton,
    QLabel, QMessageBox, QFileDialog, QCheckBox, QScrollArea, QFrame, QRadioButton, QButtonGroup, QApplication, QComboBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from lxml import etree
from api.mintrud_api import (
    load_api_key, save_api_key, push_xml,
    get_by_set_id, get_by_snils, get_by_org_id, export_records_to_xlsx
)
from utils.proxy_manager import (
    load_proxy_settings, save_proxy_settings, detect_windows_proxy
)
from network.client import (
    get_network_diagnostics, test_external_access, NetworkStatus
)

logger = logging.getLogger(__name__)


class DataTransferTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: transparent;")

        # Пути
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(self.base_dir, "data")
        self.schema_dir = os.path.join(self.base_dir, "schema")
        os.makedirs(self.data_dir, exist_ok=True)

        # Основной layout с прокруткой
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background-color: transparent; border: none;")

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(15)

        # Группа 1: API ключ
        scroll_layout.addWidget(self._create_api_key_group())

        # Группа 1.5: Настройки прокси
        scroll_layout.addWidget(self._create_proxy_group())

        # Группа 2: Отправка XML
        scroll_layout.addWidget(self._create_send_xml_group())

        # Группа 3: Запрос по SetId
        scroll_layout.addWidget(self._create_query_setid_group())

        # Группа 4: Запрос по СНИЛС
        scroll_layout.addWidget(self._create_query_snils_group())

        # Группа 5: Запрос по OrgId (НСПР)
        scroll_layout.addWidget(self._create_query_orgid_group())

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)

        # Загрузка API-ключа
        self.load_api_key()

        # Загрузка настроек прокси
        self.load_proxy_settings()

        # Callback-функции для журнала (устанавливаются из main.py)
        self._journal_add_callback = None    # add_records_to_journal
        self._journal_update_callback = None # update_base_no

    def set_journal_callback(self, add_callback, update_callback):
        """Установка callback-функций для журнала проверки знаний."""
        self._journal_add_callback = add_callback
        self._journal_update_callback = update_callback

    def _group_style(self):
        return """
            QGroupBox {
                border: 2px solid #4169E1;
                border-radius: 10px;
                margin-top: 10px;
                padding: 15px;
                background-color: white;
            }
            QGroupBox::title {
                color: #4169E1;
                font-weight: bold;
                font-size: 14px;
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """

    def _btn_style(self, hover_color="#3151B1"):
        return f"""
            QPushButton {{
                background-color: #4169E1;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
        """

    # ============ Группа API ключ ============

    def _create_api_key_group(self):
        group = QGroupBox()
        group.setStyleSheet(self._group_style())
        group.setTitle("API ключ")

        layout = QVBoxLayout(group)

        row = QHBoxLayout()
        self.api_key_label = QLabel("API ключ:")
        self.api_key_label.setStyleSheet("color: black;")
        self.api_key_input = QLineEdit()
        self.api_key_input.setMaxLength(32)
        self.api_key_input.setFixedWidth(350)
        self.api_key_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        self.api_key_input.setPlaceholderText("32 символа")
        
        # Кнопка показать/скрыть API (зажать = показать)
        self.api_key_toggle_btn = QPushButton("👁")
        self.api_key_toggle_btn.setFixedWidth(40)
        self.api_key_toggle_btn.setStyleSheet(self._btn_style())
        self.api_key_toggle_btn.setCheckable(True)
        self.api_key_toggle_btn.setToolTip("Зажмите для просмотра ключа")
        # По умолчанию скрытие - показываем только при зажатии
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_toggle_btn.pressed.connect(lambda: self.api_key_input.setEchoMode(QLineEdit.EchoMode.Normal))
        self.api_key_toggle_btn.released.connect(lambda: self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password))
        
        paste_btn = QPushButton("Вставить")
        paste_btn.setStyleSheet(self._btn_style())
        paste_btn.clicked.connect(self.paste_api_key)

        save_btn = QPushButton("Сохранить")
        save_btn.setStyleSheet(self._btn_style())
        save_btn.clicked.connect(self.save_api_key)

        row.addWidget(self.api_key_label)
        row.addWidget(self.api_key_input)
        row.addWidget(self.api_key_toggle_btn)
        row.addWidget(paste_btn)
        row.addWidget(save_btn)
        row.addStretch()
        layout.addLayout(row)

        return group

    # ============ Группа Настройки прокси ============

    def _create_proxy_group(self):
        group = QGroupBox()
        group.setStyleSheet(self._group_style())
        group.setTitle("Настройки прокси")

        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        # Радиокнопки выбора режима
        mode_layout = QHBoxLayout()

        # Обёртка с серой границей
        radio_frame = QFrame()
        radio_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #CCCCCC;
                border-radius: 6px;
                padding: 8px;
                background-color: #F5F5F5;
            }
        """)
        radio_inner = QHBoxLayout(radio_frame)
        radio_inner.setSpacing(25)

        # Стиль для радиокнопок — видимый кружок
        rb_style = """
            QRadioButton {
                color: black;
                spacing: 6px;
                font-size: 13px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #888;
                border-radius: 9px;
                background-color: white;
            }
            QRadioButton::indicator:hover {
                border: 2px solid #4169E1;
                background-color: #E8E8FF;
            }
            QRadioButton::indicator:checked {
                border: 3px solid #4169E1;
                background-color: #4169E1;
            }
        """

        self.proxy_off_rb = QRadioButton("Без прокси")
        self.proxy_off_rb.setStyleSheet(rb_style)
        self.proxy_off_rb.setChecked(True)

        self.proxy_auto_rb = QRadioButton("Авто (системные)")
        self.proxy_auto_rb.setStyleSheet(rb_style)

        self.proxy_manual_rb = QRadioButton("Вручную")
        self.proxy_manual_rb.setStyleSheet(rb_style)

        self.proxy_mode_group = QButtonGroup(self)
        self.proxy_mode_group.addButton(self.proxy_off_rb, 0)
        self.proxy_mode_group.addButton(self.proxy_auto_rb, 1)
        self.proxy_mode_group.addButton(self.proxy_manual_rb, 2)
        self.proxy_mode_group.buttonClicked.connect(self._on_proxy_mode_changed)

        radio_inner.addWidget(self.proxy_off_rb)
        radio_inner.addWidget(self.proxy_auto_rb)
        radio_inner.addWidget(self.proxy_manual_rb)
        radio_inner.addStretch()

        mode_layout.addWidget(radio_frame)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        # Инфо об авто-режиме (показывается только при "Авто")
        self.proxy_auto_info = QLabel()
        self.proxy_auto_info.setStyleSheet("color: #666; font-style: italic; padding: 4px;")
        self.proxy_auto_info.setWordWrap(True)
        self.proxy_auto_info.setVisible(False)
        layout.addWidget(self.proxy_auto_info)

        # Поля для ручного режима
        # Адрес прокси
        row1 = QHBoxLayout()
        self.proxy_url_label = QLabel("Адрес прокси:")
        self.proxy_url_label.setStyleSheet("color: black;")
        self.proxy_url_input = QLineEdit()
        self.proxy_url_input.setFixedWidth(400)
        self.proxy_url_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        self.proxy_url_input.setPlaceholderText("http://proxy.example.com:3128")
        row1.addWidget(self.proxy_url_label)
        row1.addWidget(self.proxy_url_input)
        row1.addStretch()
        layout.addLayout(row1)

        # Логин и пароль
        row2 = QHBoxLayout()
        self.proxy_user_label = QLabel("Логин:")
        self.proxy_user_label.setStyleSheet("color: black;")
        self.proxy_user_input = QLineEdit()
        self.proxy_user_input.setFixedWidth(150)
        self.proxy_user_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        self.proxy_user_input.setPlaceholderText("Если прокси требует авторизацию")
        row2.addWidget(self.proxy_user_label)
        row2.addWidget(self.proxy_user_input)

        row2.addSpacing(20)

        self.proxy_pass_label = QLabel("Пароль:")
        self.proxy_pass_label.setStyleSheet("color: black;")
        self.proxy_pass_input = QLineEdit()
        self.proxy_pass_input.setFixedWidth(150)
        self.proxy_pass_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        self.proxy_pass_input.setPlaceholderText("Если прокси требует авторизацию")
        self.proxy_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        row2.addWidget(self.proxy_pass_label)
        row2.addWidget(self.proxy_pass_input)
        row2.addStretch()
        layout.addLayout(row2)

        # Кнопки
        btn_row = QHBoxLayout()
        self.proxy_save_btn = QPushButton("Сохранить настройки")
        self.proxy_save_btn.setStyleSheet(self._btn_style())
        self.proxy_save_btn.clicked.connect(self.save_proxy_settings_ui)

        self.proxy_test_btn = QPushButton("Тест подключения")
        self.proxy_test_btn.setStyleSheet(self._btn_style())
        self.proxy_test_btn.clicked.connect(self.test_proxy)

        btn_row.addWidget(self.proxy_save_btn)
        btn_row.addWidget(self.proxy_test_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        
        # Переключатель TLS с стилями
        tls_row = QHBoxLayout()
        self.tls_checkbox = QCheckBox("TLS верификация (включить для прода)")
        self.tls_checkbox.setToolTip("Включите для безопасного соединения. Отключите для работы через корпоративный прокси с SSL-инспекцией")
        self.tls_checkbox.setStyleSheet("""
            QCheckBox {
                color: black;
            }
            QCheckBox::indicator {
                border: 1px solid #888888;
                border-radius: 3px;
                width: 16px;
                height: 16px;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #4169E1;
                border: 1px solid #4169E1;
            }
            QToolTip {
                color: black;
                background-color: white;
                border: 1px solid #CCCCCC;
                padding: 4px;
            }
        """)
        self.tls_checkbox.setChecked(True)  # TLS verify enabled by default
        tls_row.addWidget(self.tls_checkbox)
        tls_row.addStretch()
        layout.addLayout(tls_row)

        # Transport backend selection
        backend_row = QHBoxLayout()
        backend_label = QLabel("Transport backend:")
        backend_label.setStyleSheet("color: black;")
        backend_row.addWidget(backend_label)

        from api.mintrud_api import get_available_backends
        available_backends = get_available_backends()

        self.backend_combo = QComboBox()
        self.backend_combo.addItem("Auto", "auto")
        for be in available_backends:
            self.backend_combo.addItem(be.capitalize(), be)
        self.backend_combo.setFixedWidth(150)
        self.backend_combo.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        backend_row.addWidget(self.backend_combo)
        backend_row.addStretch()
        layout.addLayout(backend_row)

        # Кнопка показа пароль прокси (зажать = показать)
        pass_row = QHBoxLayout()
        self.proxy_pass_toggle_btn = QPushButton("👁 Показать пароль прокси")
        self.proxy_pass_toggle_btn.setStyleSheet(self._btn_style())
        self.proxy_pass_toggle_btn.setCheckable(True)
        self.proxy_pass_toggle_btn.setToolTip("Зажмите для просмотра пароля")
        self.proxy_pass_toggle_btn.pressed.connect(lambda: self.proxy_pass_input.setEchoMode(QLineEdit.EchoMode.Normal))
        self.proxy_pass_toggle_btn.released.connect(lambda: self.proxy_pass_input.setEchoMode(QLineEdit.EchoMode.Password))
        pass_row.addWidget(self.proxy_pass_toggle_btn)
        pass_row.addStretch()
        layout.addLayout(pass_row)

        # Инициальное состояние — скрыть ручные поля
        self._on_proxy_mode_changed(self.proxy_off_rb)

        return group

    def _on_proxy_mode_changed(self, button):
        """Обработка смены режима прокси."""
        mode = self.proxy_mode_group.id(button)
        # 0 = off, 1 = auto, 2 = manual

        manual_fields = [
            self.proxy_url_label, self.proxy_url_input,
            self.proxy_user_label, self.proxy_user_input,
            self.proxy_pass_label, self.proxy_pass_input
        ]

        if mode == 0:  # off
            for w in manual_fields:
                w.setVisible(False)
            self.proxy_auto_info.setVisible(False)
        elif mode == 1:  # auto
            for w in manual_fields:
                w.setVisible(False)
            # Покажем текущий системный прокси
            sys_proxy = detect_windows_proxy()
            if sys_proxy:
                self.proxy_auto_info.setText(f"Обнаружен системный прокси: {sys_proxy}")
            else:
                self.proxy_auto_info.setText("Системный прокси не обнаружен в настройках Windows")
            self.proxy_auto_info.setVisible(True)
        else:  # manual
            for w in manual_fields:
                w.setVisible(True)
            self.proxy_auto_info.setVisible(False)

    def _create_send_xml_group(self):
        group = QGroupBox()
        group.setStyleSheet(self._group_style())
        group.setTitle("Отправка XML")

        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        # Строка 1: Выбор файла
        file_row = QHBoxLayout()
        self.xml_file_label = QLabel("XML файл:")
        self.xml_file_label.setStyleSheet("color: black;")
        self.xml_file_input = QLineEdit()
        self.xml_file_input.setReadOnly(True)
        self.xml_file_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        self.xml_file_input.setPlaceholderText("Файл не выбран")

        select_xml_btn = QPushButton("Выбрать")
        select_xml_btn.setStyleSheet(self._btn_style())
        select_xml_btn.clicked.connect(self.select_xml_file)

        file_row.addWidget(self.xml_file_label)
        file_row.addWidget(self.xml_file_input)
        file_row.addWidget(select_xml_btn)
        layout.addLayout(file_row)

        # Строка 2: Кнопка отправки
        send_btn = QPushButton("Отправить XML на сервер")
        send_btn.setStyleSheet(self._btn_style())
        send_btn.clicked.connect(self.send_xml)
        layout.addWidget(send_btn)

        # Строка 3: Последний SetId
        setid_row = QHBoxLayout()
        self.last_setid_label = QLabel("Последний SetId:")
        self.last_setid_label.setStyleSheet("color: black;")
        self.last_setid_display = QLineEdit()
        self.last_setid_display.setReadOnly(True)
        self.last_setid_display.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        setid_row.addWidget(self.last_setid_label)
        setid_row.addWidget(self.last_setid_display)
        layout.addLayout(setid_row)

        return group

    def _create_query_setid_group(self):
        group = QGroupBox()
        group.setStyleSheet(self._group_style())
        group.setTitle("Запрос по SetId")

        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        row = QHBoxLayout()
        self.query_setid_label = QLabel("Введите номер набора (SetId):")
        self.query_setid_label.setStyleSheet("color: black;")
        self.query_setid_input = QLineEdit()
        self.query_setid_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        self.query_setid_input.setPlaceholderText("SetId из ответа сервера")

        query_btn = QPushButton("Запросить номера")
        query_btn.setStyleSheet(self._btn_style())
        query_btn.clicked.connect(self.query_by_setid)

        row.addWidget(self.query_setid_label)
        row.addWidget(self.query_setid_input)
        row.addWidget(query_btn)
        layout.addLayout(row)

        return group

    def _create_query_snils_group(self):
        group = QGroupBox()
        group.setStyleSheet(self._group_style())
        group.setTitle("Запрос по СНИЛС")

        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        row = QHBoxLayout()
        self.query_snils_label = QLabel("Введите СНИЛС:")
        self.query_snils_label.setStyleSheet("color: black;")
        self.query_snils_input = QLineEdit()
        self.query_snils_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        self.query_snils_input.setPlaceholderText("123-456-789 00 или 12345678900")

        query_btn = QPushButton("Отправить запрос")
        query_btn.setStyleSheet(self._btn_style())
        query_btn.clicked.connect(self.query_by_snils)

        row.addWidget(self.query_snils_label)
        row.addWidget(self.query_snils_input)
        row.addWidget(query_btn)
        layout.addLayout(row)

        return group

    def _create_query_orgid_group(self):
        """Группа для запроса данных по OrgId (НСПР)."""
        group = QGroupBox()
        group.setStyleSheet(self._group_style())
        group.setTitle("Запрос по OrgId (НСПР)")

        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        # Строка 1: OrgId
        row1 = QHBoxLayout()
        self.query_orgid_label = QLabel("ID организации:")
        self.query_orgid_label.setStyleSheet("color: black;")
        self.query_orgid_input = QLineEdit()
        self.query_orgid_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        self.query_orgid_input.setPlaceholderText("00000000-0000-0000-0000-000000000001")

        row1.addWidget(self.query_orgid_label)
        row1.addWidget(self.query_orgid_input)
        row1.addStretch()
        layout.addLayout(row1)

        # Строка 2: Лимит записей
        row2 = QHBoxLayout()
        self.query_limit_label = QLabel("Лимит записей:")
        self.query_limit_label.setStyleSheet("color: black;")
        self.query_limit_input = QLineEdit()
        self.query_limit_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        self.query_limit_input.setPlaceholderText("0 = без ограничения")
        self.query_limit_input.setFixedWidth(150)
        self.query_limit_input.setText("0")

        row2.addWidget(self.query_limit_label)
        row2.addWidget(self.query_limit_input)
        row2.addStretch()
        layout.addLayout(row2)

        # Строка 3: Кнопка запроса
        query_btn = QPushButton("Загрузить данные по организации")
        query_btn.setStyleSheet(self._btn_style())
        query_btn.clicked.connect(self.query_by_orgid)
        layout.addWidget(query_btn)

        return group

    # ============ Логика API ключа ============

    def load_api_key(self):
        """Загрузка API-ключа из файла."""
        key = load_api_key(self.data_dir)
        if key:
            self.api_key_input.setText(key)

    def paste_api_key(self):
        """Вставка из буфера."""
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            self.api_key_input.setText(text.strip())

    def save_api_key(self):
        """Сохранение API-ключа."""
        api_key = self.api_key_input.text().strip()
        if len(api_key) != 32:
            QMessageBox.warning(self, "Ошибка", f"Длина ключа: {len(api_key)} (требуется 32 символа)")
            return

        ok, msg = save_api_key(api_key, self.data_dir)
        if ok:
            QMessageBox.information(self, "Успех", "API ключ сохранён")
        else:
            QMessageBox.warning(self, "Ошибка", msg)

    # ============ Логика настроек прокси ============

    def load_proxy_settings(self):
        """Загрузка настроек прокси из файла."""
        settings = load_proxy_settings(self.data_dir)
        mode = settings.get('mode', 'off')

        # Установить радиокнопку
        if mode == 'auto':
            self.proxy_auto_rb.setChecked(True)
        elif mode == 'manual':
            self.proxy_manual_rb.setChecked(True)
        else:
            self.proxy_off_rb.setChecked(True)

        self.proxy_url_input.setText(settings.get('url', ''))
        self.proxy_user_input.setText(settings.get('username', ''))
        self.proxy_pass_input.setText(settings.get('password', ''))

        # Загрузить TLS настройку
        self.tls_checkbox.setChecked(settings.get('tls_verify', True))

        # Обновить видимость полей
        if mode == 'auto':
            self._on_proxy_mode_changed(self.proxy_auto_rb)
        elif mode == 'manual':
            self._on_proxy_mode_changed(self.proxy_manual_rb)
        else:
            self._on_proxy_mode_changed(self.proxy_off_rb)

    def save_proxy_settings_ui(self):
        """Сохранение настроек прокси из UI."""
        mode_id = self.proxy_mode_group.checkedId()
        mode_map = {0: 'off', 1: 'auto', 2: 'manual'}
        mode = mode_map.get(mode_id, 'off')

        settings = {
            'mode': mode,
            'url': self.proxy_url_input.text().strip(),
            'username': self.proxy_user_input.text().strip(),
            'password': self.proxy_pass_input.text().strip(),
            'tls_verify': self.tls_checkbox.isChecked()
        }

        ok, msg = save_proxy_settings(self.data_dir, settings)
        if ok:
            mode_text = {'off': 'Без прокси', 'auto': 'Авто (системный)', 'manual': 'Ручной'}
            QMessageBox.information(self, "Успех", f"Режим: {mode_text.get(mode, mode)}\n{msg}")
        else:
            QMessageBox.warning(self, "Ошибка", msg)

    def test_proxy(self):
        """Тестирование подключения к edu.rosmintrud.ru через Windows Integrated Authentication."""
        diag = get_network_diagnostics()

        tls_verify = self.tls_checkbox.isChecked()
        status, msg = test_external_access(
            url="https://edu.rosmintrud.ru",
            timeout=30,
            tls_verify=tls_verify
        )
        
        # Формируем результат
        result_text = f"""Диагностика сети:

Обнаруженный прокси: {diag.get('detected_proxy', 'Не обнаружен')}
Метод авторизации: {diag.get('auth_method', 'Нет')}
Windows пользователь: {diag.get('windows_user', 'Не определен')}
Negotiate доступен: {'Да' if diag.get('negotiate_available') else 'Нет'}

Результат теста:
Статус: {status.value}
Сообщение: {msg}"""
        
        if status == NetworkStatus.SUCCESS:
            QMessageBox.information(self, "Успех", result_text)
        else:
            QMessageBox.warning(self, "Проблема с доступом", result_text)

    def _get_proxy_settings(self):
        """Получение текущих настроек прокси для передачи в API."""
        mode_id = self.proxy_mode_group.checkedId()
        mode_map = {0: 'off', 1: 'auto', 2: 'manual'}
        mode = mode_map.get(mode_id, 'off')

        return {
            'mode': mode,
            'url': self.proxy_url_input.text().strip(),
            'username': self.proxy_user_input.text().strip(),
            'password': self.proxy_pass_input.text().strip(),
            'tls_verify': self.tls_checkbox.isChecked(),
            'backend': self.backend_combo.currentData()
        }

    # ============ Логика отправки XML ============

    def select_xml_file(self):
        """Выбор XML файла с валидацией по XSD."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите XML файл", "", "XML Files (*.xml)"
        )
        if not file_path:
            return

        # Проверяем что файл существует
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "Ошибка", "Файл не найден")
            return

        # Проверяем что файл не пустой
        if os.path.getsize(file_path) == 0:
            QMessageBox.warning(self, "Ошибка", "Файл пустой")
            return

        # Проверяем XML на валидность
        try:
            tree = etree.parse(file_path)
            root = tree.getroot()
            logger.info(f"XML loaded: root={root.tag}, children={len(root)}")
        except etree.XMLSyntaxError as e:
            QMessageBox.warning(self, "Ошибка", f"Невалидный XML:\n{e}")
            return
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка чтения файла:\n{e}")
            return

        # Валидация по XSD
        xsd_files = [f for f in os.listdir(self.schema_dir) if f.endswith('.xsd')]
        if xsd_files:
            xsd_path = os.path.join(self.schema_dir, xsd_files[0])
            try:
                schema_doc = etree.parse(xsd_path)
                schema = etree.XMLSchema(schema_doc)
                schema.assertValid(tree)
            except etree.DocumentInvalid as e:
                QMessageBox.warning(self, "Ошибка валидации", f"Файл не соответствует схеме XSD:\n{e}")
                return
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Ошибка валидации по XSD:\n{e}")
                return

        self.xml_file_input.setText(file_path)

    def send_xml(self):
        """Отправка XML на сервер."""
        api_key = self.api_key_input.text().strip()
        xml_file = self.xml_file_input.text()

        # Валидация ключа
        if len(api_key) != 32:
            QMessageBox.warning(self, "Ошибка", "Проверьте API ключ (32 символа)")
            return

        if not xml_file or not os.path.exists(xml_file):
            QMessageBox.warning(self, "Ошибка", "Выберите XML файл")
            return

        # Парсим XML для получения данных работников (для журнала)
        xml_records_data = self._parse_xml_for_journal(xml_file)

        proxy_settings = self._get_proxy_settings()

        result = push_xml(api_key, xml_file, proxy_settings=proxy_settings)

        if result["success"]:
            set_id = result.get("set_id", "")
            self.last_setid_display.setText(set_id)

            # Сохраняем в журнал
            if self._journal_add_callback and xml_records_data:
                count = self._journal_add_callback(xml_records_data, set_id, xml_file)

            # Диалог с SetId красным полужирным
            msg = QMessageBox()
            msg.setWindowTitle("Успех")
            msg.setText("Данные загружены на сервер")
            msg.setInformativeText(f'<span style="color:red; font-weight:bold; font-size:14px;">Запишите номер набора: {set_id}</span>')
            msg.setTextFormat(Qt.TextFormat.RichText)
            msg.exec()
        else:
            error_msg = result.get("error", "Неизвестная ошибка")
            # Покажем детали ответа если есть
            raw_response = result.get("raw_response", "")
            full_error = error_msg
            if raw_response:
                full_error += f"\n\nОтвет сервера:\n{raw_response[:500]}"
            QMessageBox.critical(self, "Ошибка загрузки", full_error)

    # ============ Логика запросов ============

    def query_by_setid(self):
        """Запрос по SetId."""
        api_key = self.api_key_input.text().strip()
        set_id = self.query_setid_input.text().strip()

        if len(api_key) != 32:
            QMessageBox.warning(self, "Ошибка", "Проверьте API ключ (32 символа)")
            return

        if not set_id:
            QMessageBox.warning(self, "Ошибка", "Введите SetId")
            return

        proxy_settings = self._get_proxy_settings()
        result = get_by_set_id(api_key, set_id, proxy_settings=proxy_settings)

        if not result["success"]:
            QMessageBox.critical(self, "Ошибка", result.get("error", "Неизвестная ошибка"))
            return

        records = result.get("records", [])
        if not records:
            QMessageBox.information(self, "Информация", "Записей не найдено")
            return

        # Обновляем baseNo в журнале
        if self._journal_update_callback:
            base_no_map = {}
            for rec in records:
                snils_raw = rec.get('Snils', '')
                base_no = rec.get('baseNo', '')
                # Удаляем все Unicode-пробелы (категория Zs) включая \xa0
                snils_clean = ''.join(c for c in snils_raw if unicodedata.category(c) != 'Zs')
                snils_clean = snils_clean.replace('-', '')
                if snils_clean:
                    base_no_map[snils_clean] = base_no

            if base_no_map:
                updated = self._journal_update_callback(set_id, base_no_map)

        # Сохранение XLSX
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить XLSX", f"{set_id}.xlsx", "Excel Files (*.xlsx)"
        )
        if file_path:
            ok, msg = export_records_to_xlsx(records, file_path)
            if ok:
                QMessageBox.information(self, "Успех", f"Сохранено {len(records)} записей\n{msg}")
            else:
                QMessageBox.warning(self, "Ошибка", msg)

    def _parse_xml_for_journal(self, xml_file_path):
        """
        Парсинг XML файла для получения данных работников (для журнала).

        Возвращает список словарей с полями:
            last_name, first_name, middle_name, snils, position,
            program, date, protocol
        """
        import xml.etree.ElementTree as ET

        records = []
        try:
            tree = ET.parse(xml_file_path)
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
                    'protocol': get_text(test, 'ProtocolNumber')
                }
                records.append(rec)
        except Exception as e:
            logger.warning(f"Failed to parse XML for journal: {e}")

        return records

    def query_by_snils(self):
        """Запрос по СНИЛС."""
        api_key = self.api_key_input.text().strip()
        snils_raw = self.query_snils_input.text().strip()

        if len(api_key) != 32:
            QMessageBox.warning(self, "Ошибка", "Проверьте API ключ (32 символа)")
            return

        if not snils_raw:
            QMessageBox.warning(self, "Ошибка", "Введите СНИЛС")
            return

        # Форматирование СНИЛС в вид "123-456-789 00"
        snils_clean = ''.join(c for c in snils_raw if unicodedata.category(c) != 'Zs')
        snils_clean = snils_clean.replace('-', '')  # Удаляем дефисы перед проверкой
        if not snils_clean.isdigit() or len(snils_clean) != 11:
            QMessageBox.warning(self, "Ошибка", "СНИЛС должен содержать 11 цифр")
            return
        snils = f"{snils_clean[0:3]}-{snils_clean[3:6]}-{snils_clean[6:9]} {snils_clean[9:11]}"

        proxy_settings = self._get_proxy_settings()
        result = get_by_snils(api_key, snils, proxy_settings=proxy_settings)

        if not result["success"]:
            QMessageBox.critical(self, "Ошибка", result.get("error", "Неизвестная ошибка"))
            return

        records = result.get("records", [])
        if not records:
            QMessageBox.information(self, "Информация", "Записей не найдено")
            return

        first = records[0]
        name = f"{first.get('LastName', '')} {first.get('FirstName', '')} {first.get('MiddleName', '')}".strip()
        QMessageBox.information(self, "Найдено", f"Записей: {len(records)}\n{name}")

        # Сохранение XLSX
        snils_file = snils.replace('-', '').replace(' ', '')
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить XLSX", f"{snils_file}.xlsx", "Excel Files (*.xlsx)"
        )
        if file_path:
            ok, msg = export_records_to_xlsx(records, file_path)
            if ok:
                QMessageBox.information(self, "Успех", f"Сохранено {len(records)} записей\n{msg}")
            else:
                QMessageBox.warning(self, "Ошибка", msg)

    def query_by_orgid(self):
        """Запрос данных по OrgId (НСПР)."""
        api_key = self.api_key_input.text().strip()
        org_id = self.query_orgid_input.text().strip()
        limit_text = self.query_limit_input.text().strip()

        if len(api_key) != 32:
            QMessageBox.warning(self, "Ошибка", "Проверьте API ключ (32 символа)")
            return

        if not org_id:
            QMessageBox.warning(self, "Ошибка", "Введите OrgId")
            return

        if limit_text:
            try:
                limit = int(limit_text)
            except ValueError:
                QMessageBox.warning(self, "Ошибка", f"Limit must be a number: '{limit_text}'")
                return
        else:
            limit = 0

        proxy_settings = self._get_proxy_settings()
        result = get_by_org_id(api_key, org_id, proxy_settings=proxy_settings, limit=limit)

        if not result["success"]:
            QMessageBox.critical(self, "Ошибка", result.get("error", "Неизвестная ошибка"))
            return

        records = result.get("records", [])
        if not records:
            QMessageBox.information(self, "Информация", "Записей не найдено")
            return

        # Сохранение XLSX
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить XLSX", f"org_{org_id}.xlsx", "Excel Files (*.xlsx)"
        )
        if file_path:
            ok, msg = export_records_to_xlsx(records, file_path)
            if ok:
                QMessageBox.information(self, "Успех", f"Сохранено {len(records)} записей\n{msg}")
            else:
                QMessageBox.warning(self, "Ошибка", msg)
