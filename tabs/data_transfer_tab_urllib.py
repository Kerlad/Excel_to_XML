"""
Альтернативная вкладка передачи данных с использованием urllib вместо requests.
Используется при проблемах с прокси-серверами в корпоративной сети.
"""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit,
    QPushButton, QFileDialog, QMessageBox, QScrollArea, QApplication,
    QRadioButton, QButtonGroup, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from lxml import etree
from api.mintrud_api_urllib import (
    push_xml,
    get_by_set_id, get_by_snils, export_records_to_xlsx
)
from utils.proxy_manager import (
    load_proxy_settings, save_proxy_settings, test_proxy_connection,
    detect_windows_proxy
)
# Для работы с API ключом используем основной модуль
from api.mintrud_api import load_api_key, save_api_key


class DataTransferTabUrllib(QWidget):
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

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)

        # Загрузка API-ключа
        self.load_api_key()

        # Загрузка настроек прокси
        self.load_proxy_settings()

        # Callback-функции для журнала (устанавливаются из main.py)
        self._journal_add_callback = None    # add_records_to_journal
        self._journal_update_callback = None  # update_base_no

    def _create_api_key_group(self):
        group = QGroupBox("API ключ")
        group.setStyleSheet("""
            QGroupBox { 
                color: black; 
                font-weight: bold; 
                padding-top: 10px; 
                border: 1px solid #CCCCCC; 
                border-radius: 5px; 
                margin-top: 10px; 
            }
            QGroupBox::title { 
                subcontrol-origin: margin; 
                left: 10px; 
                padding: 0 5px; 
            }
        """)
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        inner = QHBoxLayout()

        label = QLabel("API ключ (32 символа):")
        label.setStyleSheet("color: black;")
        self.api_key_input = QLineEdit()
        self.api_key_input.setFixedWidth(500)
        self.api_key_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        self.api_key_input.setPlaceholderText("Вставьте API ключ из личного кабинета")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)

        inner.addWidget(label)
        inner.addWidget(self.api_key_input)
        layout.addLayout(inner)

        # Кнопки
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Сохранить ключ")
        save_btn.setStyleSheet(self._btn_style())
        save_btn.clicked.connect(self.save_api_key_ui)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)
        return group

    def _create_proxy_group(self):
        group = QGroupBox("Настройки прокси")
        group.setStyleSheet("""
            QGroupBox { 
                color: black; 
                font-weight: bold; 
                padding-top: 10px; 
                border: 1px solid #CCCCCC; 
                border-radius: 5px; 
                margin-top: 10px; 
            }
            QGroupBox::title { 
                subcontrol-origin: margin; 
                left: 10px; 
                padding: 0 5px; 
            }
        """)
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        # Радиокнопки режима
        radio_inner = QHBoxLayout()
        rb_style = "color: black;"
        
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
        layout.addLayout(radio_inner)

        # Информация о системном прокси
        self.proxy_auto_info = QLabel()
        self.proxy_auto_info.setStyleSheet("color: #666; font-style: italic; padding: 4px;")
        self.proxy_auto_info.setWordWrap(True)
        self.proxy_auto_info.setVisible(False)
        layout.addWidget(self.proxy_auto_info)

        # Поля ручных настроек
        row1 = QHBoxLayout()
        # Адрес прокси
        self.proxy_url_label = QLabel("Адрес прокси:")
        self.proxy_url_label.setStyleSheet("color: black;")
        self.proxy_url_input = QLineEdit()
        self.proxy_url_input.setFixedWidth(400)
        self.proxy_url_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        self.proxy_url_input.setPlaceholderText("http://proxy.example.com:3128")
        row1.addWidget(self.proxy_url_label)
        row1.addWidget(self.proxy_url_input)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        # Логин и пароль
        self.proxy_user_label = QLabel("Логин:")
        self.proxy_user_label.setStyleSheet("color: black;")
        self.proxy_user_input = QLineEdit()
        self.proxy_user_input.setFixedWidth(150)
        self.proxy_user_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        self.proxy_user_input.setPlaceholderText("Если прокси требует авторизацию")
        row2.addWidget(self.proxy_user_label)
        row2.addWidget(self.proxy_user_input)

        self.proxy_pass_label = QLabel("Пароль:")
        self.proxy_pass_label.setStyleSheet("color: black;")
        self.proxy_pass_input = QLineEdit()
        self.proxy_pass_input.setFixedWidth(150)
        self.proxy_pass_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        self.proxy_pass_input.setPlaceholderText("Если прокси требует авторизацию")
        self.proxy_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        row2.addWidget(self.proxy_pass_label)
        row2.addWidget(self.proxy_pass_input)
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
        layout.addLayout(btn_row)

        # Инициализация видимости
        self._on_proxy_mode_changed(self.proxy_off_rb)
        return group

    def _on_proxy_mode_changed(self, button):
        """Обработка смены режима прокси."""
        mode = self.proxy_mode_group.id(button)
        # Скрыть все поля
        for w in [
            self.proxy_url_label, self.proxy_url_input,
            self.proxy_user_label, self.proxy_user_input,
            self.proxy_pass_label, self.proxy_pass_input
        ]:
            w.setVisible(False)

        if mode == 0:  # off
            self.proxy_auto_info.setVisible(False)
        elif mode == 1:  # auto
            # Покажем текущий системный прокси
            sys_proxy = detect_windows_proxy()
            if sys_proxy:
                self.proxy_auto_info.setText(f"Обнаружен системный прокси: {sys_proxy}")
            else:
                self.proxy_auto_info.setText("Системный прокси не обнаружен в настройках Windows")
            self.proxy_auto_info.setVisible(True)
        else:  # manual
            for w in [
                self.proxy_url_label, self.proxy_url_input,
                self.proxy_user_label, self.proxy_user_input,
                self.proxy_pass_label, self.proxy_pass_input
            ]:
                w.setVisible(True)
            self.proxy_auto_info.setVisible(False)

    def _create_send_xml_group(self):
        group = QGroupBox("Отправка XML")
        group.setStyleSheet("""
            QGroupBox { 
                color: black; 
                font-weight: bold; 
                padding-top: 10px; 
                border: 1px solid #CCCCCC; 
                border-radius: 5px; 
                margin-top: 10px; 
            }
            QGroupBox::title { 
                subcontrol-origin: margin; 
                left: 10px; 
                padding: 0 5px; 
            }
        """)
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        row = QHBoxLayout()
        label = QLabel("XML файл:")
        label.setStyleSheet("color: black;")
        self.xml_file_input = QLineEdit()
        self.xml_file_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        self.xml_file_input.setReadOnly(True)

        select_btn = QPushButton("Выбрать")
        select_btn.setStyleSheet(self._btn_style())
        select_btn.clicked.connect(self.select_xml_file)

        row.addWidget(label)
        row.addWidget(self.xml_file_input)
        row.addWidget(select_btn)
        layout.addLayout(row)

        send_btn = QPushButton("Отправить XML на сервер")
        send_btn.setStyleSheet(self._btn_style())
        send_btn.clicked.connect(self.send_xml)
        layout.addWidget(send_btn)

        return group

    def _create_query_setid_group(self):
        group = QGroupBox("Запрос по SetId")
        group.setStyleSheet("""
            QGroupBox { 
                color: black; 
                font-weight: bold; 
                padding-top: 10px; 
                border: 1px solid #CCCCCC; 
                border-radius: 5px; 
                margin-top: 10px; 
            }
            QGroupBox::title { 
                subcontrol-origin: margin; 
                left: 10px; 
                padding: 0 5px; 
            }
        """)
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        row = QHBoxLayout()
        label = QLabel("Введите номер набора (SetId):")
        label.setStyleSheet("color: black;")
        self.query_setid_input = QLineEdit()
        self.query_setid_input.setFixedWidth(300)
        self.query_setid_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")

        row.addWidget(label)
        row.addWidget(self.query_setid_input)
        layout.addLayout(row)

        query_btn = QPushButton("Запросить номера")
        query_btn.setStyleSheet(self._btn_style())
        query_btn.clicked.connect(self.query_set_id)
        layout.addWidget(query_btn)

        return group

    def _create_query_snils_group(self):
        group = QGroupBox("Запрос по СНИЛС")
        group.setStyleSheet("""
            QGroupBox { 
                color: black; 
                font-weight: bold; 
                padding-top: 10px; 
                border: 1px solid #CCCCCC; 
                border-radius: 5px; 
                margin-top: 10px; 
            }
            QGroupBox::title { 
                subcontrol-origin: margin; 
                left: 10px; 
                padding: 0 5px; 
            }
        """)
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        row = QHBoxLayout()
        label = QLabel("Введите СНИЛС:")
        label.setStyleSheet("color: black;")
        self.query_snils_input = QLineEdit()
        self.query_snils_input.setFixedWidth(300)
        self.query_snils_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        self.query_snils_input.setPlaceholderText("123-456-789 00 или 12345678900")

        row.addWidget(label)
        row.addWidget(self.query_snils_input)
        layout.addLayout(row)

        query_btn = QPushButton("Отправить запрос")
        query_btn.setStyleSheet(self._btn_style())
        query_btn.clicked.connect(self.query_snils)
        layout.addWidget(query_btn)

        return group

    def _btn_style(self):
        return """
            QPushButton {
                background-color: #4169E1;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3151B1;
            }
            QPushButton:pressed {
                background-color: #264090;
            }
        """

    # ============ Логика API-ключа ============

    def load_api_key(self):
        """Загрузка API-ключа из файла."""
        key = load_api_key(self.data_dir)
        if key:
            self.api_key_input.setText(key)

    def save_api_key(self):
        """Сохранение API-ключа в файл."""
        api_key = self.api_key_input.text().strip()
        ok, msg = save_api_key(api_key, self.data_dir)
        if ok:
            QMessageBox.information(self, "Успех", "API-ключ сохранён")
        else:
            QMessageBox.warning(self, "Ошибка", msg)

    def save_api_key_ui(self):
        """Обработчик кнопки сохранения API-ключа."""
        self.save_api_key()

    # ============ Логика настроек прокси ============

    def load_proxy_settings(self):
        """Загрузка настроек прокси из файла."""
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

        if mode == 'auto':
            self._on_proxy_mode_changed(self.proxy_auto_rb)
        elif mode == 'manual':
            self._on_proxy_mode_changed(self.proxy_manual_rb)
        else:
            self._on_proxy_mode_changed(self.proxy_off_rb)

    def save_proxy_settings_ui(self):
        """Сохранение настроек прокси из UI."""
        mode_id = self.proxy_mode_group.checkedId()
        mode = {0: 'off', 1: 'auto', 2: 'manual'}[mode_id]

        settings = {
            'mode': mode,
            'url': self.proxy_url_input.text().strip(),
            'username': self.proxy_user_input.text().strip(),
            'password': self.proxy_pass_input.text().strip()
        }

        ok, msg = save_proxy_settings(self.data_dir, settings)
        if ok:
            mode_text = {'off': 'Без прокси', 'auto': 'Авто (системный)', 'manual': 'Ручной'}
            QMessageBox.information(self, "Успех", f"Режим: {mode_text[mode]}\n{msg}")
        else:
            QMessageBox.warning(self, "Ошибка", msg)

    def test_proxy(self):
        """Тестирование подключения через прокси."""
        mode_id = self.proxy_mode_group.checkedId()
        mode = {0: 'off', 1: 'auto', 2: 'manual'}[mode_id]

        settings = {
            'mode': mode,
            'url': self.proxy_url_input.text().strip(),
            'username': self.proxy_user_input.text().strip(),
            'password': self.proxy_pass_input.text().strip()
        }

        if mode == 'off':
            QMessageBox.information(self, "Информация", "Режим 'Без прокси' — будет использовано прямое подключение.")
            return

        if mode == 'auto':
            sys_proxy = detect_windows_proxy()
            if not sys_proxy:
                QMessageBox.warning(self, "Ошибка", "Системный прокси не обнаружен.\nПроверьте настройки прокси в Windows (Параметры → Сеть → Прокси-сервер).")
                return

        ok, msg = test_proxy_connection(settings)
        if ok:
            QMessageBox.information(self, "Успех", msg)
        else:
            QMessageBox.critical(self, "Ошибка", msg)

    def _get_proxy_settings(self):
        """Получение текущих настроек прокси для передачи в API."""
        mode_id = self.proxy_mode_group.checkedId()
        mode = {0: 'off', 1: 'auto', 2: 'manual'}[mode_id]

        return {
            'mode': mode,
            'url': self.proxy_url_input.text().strip(),
            'username': self.proxy_user_input.text().strip(),
            'password': self.proxy_pass_input.text().strip()
        }

    # ============ Отправка XML ============

    def select_xml_file(self):
        """Выбор XML файла."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите XML файл", "", "XML Files (*.xml)"
        )
        if file_path:
            self.xml_file_input.setText(file_path)

    def send_xml(self):
        """Отправка XML на сервер."""
        api_key = self.api_key_input.text().strip()
        xml_file = self.xml_file_input.text().strip()

        if len(api_key) != 32:
            QMessageBox.warning(self, "Ошибка", "Проверьте API ключ (32 символа)")
            return

        if not xml_file:
            QMessageBox.warning(self, "Ошибка", "Выберите XML файл")
            return

        if not os.path.exists(xml_file):
            QMessageBox.warning(self, "Ошибка", "Файл не найден")
            return

        # Валидация XSD (опционально)
        xsd_file = self._find_xsd()
        if xsd_file:
            try:
                xml_doc = etree.parse(xml_file)
                xsd_doc = etree.parse(xsd_file)
                schema = etree.XMLSchema(xsd_doc)
                if not schema.validate(xml_doc):
                    errors = [str(e) for e in schema.error_log]
                    QMessageBox.warning(self, "Ошибка XSD", f"Файл не соответствует схеме:\n" + "\n".join(errors[:5]))
                    return
            except Exception as e:
                QMessageBox.warning(self, "Ошибка валидации", str(e))
                return

        QMessageBox.information(self, "Информация", "Отправка XML на сервер...\nЭто может занять время.")
        QApplication.processEvents()

        proxy_settings = self._get_proxy_settings()
        result = push_xml(api_key, xml_file, proxy_settings=proxy_settings)

        if result.get("success"):
            set_id = result.get("set_id", "")
            msg = f"Данные загружены на сервер\n\nЗапишите номер набора: {set_id}"
            
            # Показываем SetId жирным красным
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Успех")
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setText(msg)
            msg_box.setStyleSheet("""
                QMessageBox QLabel {
                    color: black;
                    font-size: 14px;
                }
            """)
            msg_box.exec()

            # Добавляем в журнал если есть callback
            if self._journal_add_callback:
                try:
                    from exporters.xml_exporter import convert_xml_to_records
                    records = convert_xml_to_records(xml_file)
                    self._journal_add_callback(records, set_id, xml_file)
                except Exception as e:
                    pass
        else:
            error = result.get("error", "Неизвестная ошибка")
            QMessageBox.critical(self, "Ошибка загрузки", f"Ошибка: {error}")

    def _find_xsd(self):
        """Поиск XSD файла в директории schema."""
        if not os.path.exists(self.schema_dir):
            return None
        for f in os.listdir(self.schema_dir):
            if f.endswith('.xsd'):
                return os.path.join(self.schema_dir, f)
        return None

    # ============ Запрос по SetId ============

    def query_set_id(self):
        """Запрос по SetId."""
        api_key = self.api_key_input.text().strip()
        set_id = self.query_setid_input.text().strip()

        if len(api_key) != 32:
            QMessageBox.warning(self, "Ошибка", "Проверьте API ключ (32 символа)")
            return

        if not set_id:
            QMessageBox.warning(self, "Ошибка", "Введите номер набора")
            return

        QMessageBox.information(self, "Информация", f"Запрос данных по SetId: {set_id}...")
        QApplication.processEvents()

        proxy_settings = self._get_proxy_settings()
        result = get_by_set_id(api_key, set_id, proxy_settings=proxy_settings)

        if not result.get("success"):
            QMessageBox.critical(self, "Ошибка", result.get("error", "Неизвестная ошибка"))
            return

        records = result.get("records", [])
        if not records:
            QMessageBox.information(self, "Информация", "Записей не найдено")
            return

        # Обновляем журнал если есть callback
        if self._journal_update_callback:
            try:
                self._journal_update_callback(set_id, records)
            except Exception as e:
                pass

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

    # ============ Запрос по СНИЛС ============

    def query_snils(self):
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
        import unicodedata
        snils_clean = ''.join(c for c in snils_raw if unicodedata.category(c) != 'Zs')
        snils_clean = snils_clean.replace('-', '')  # Удаляем дефисы перед проверкой
        if not snils_clean.isdigit() or len(snils_clean) != 11:
            QMessageBox.warning(self, "Ошибка", "СНИЛС должен содержать 11 цифр")
            return
        snils = f"{snils_clean[0:3]}-{snils_clean[3:6]}-{snils_clean[6:9]} {snils_clean[9:11]}"

        QMessageBox.information(self, "Информация", f"Запрос данных по СНИЛС: {snils}...")
        QApplication.processEvents()

        proxy_settings = self._get_proxy_settings()
        result = get_by_snils(api_key, snils, proxy_settings=proxy_settings)

        if not result["success"]:
            QMessageBox.critical(self, "Ошибка", result.get("error", "Неизвестная ошибка"))
            return

        records = result.get("records", [])
        if not records:
            QMessageBox.information(self, "Информация", "Записей не найдено")
            return

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

    # ============ Установка callback-функций ============

    def set_journal_callback(self, add_callback, update_callback):
        """Установка callback-функций для журнала."""
        self._journal_add_callback = add_callback
        self._journal_update_callback = update_callback
