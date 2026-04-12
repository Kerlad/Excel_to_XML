import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit,
    QPushButton, QFileDialog, QMessageBox, QScrollArea, QApplication
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from lxml import etree
from api.mintrud_api import (
    load_api_key, save_api_key, push_xml,
    get_by_set_id, get_by_snils, export_records_to_xlsx
)


class DataTransferTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: white;")

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
        scroll.setStyleSheet("background-color: white; border: none;")

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(15)

        # Группа 1: API ключ
        scroll_layout.addWidget(self._create_api_key_group())

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

        paste_btn = QPushButton("Вставить из буфера")
        paste_btn.setStyleSheet(self._btn_style())
        paste_btn.clicked.connect(self.paste_api_key)

        save_btn = QPushButton("Сохранить ключ")
        save_btn.setStyleSheet(self._btn_style())
        save_btn.clicked.connect(self.save_api_key)

        row.addWidget(self.api_key_label)
        row.addWidget(self.api_key_input)
        row.addWidget(paste_btn)
        row.addWidget(save_btn)
        row.addStretch()
        layout.addLayout(row)

        return group

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

    # ============ Логика отправки XML ============

    def select_xml_file(self):
        """Выбор XML файла с валидацией по XSD."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите XML файл", "", "XML Files (*.xml)"
        )
        if file_path:
            # Валидация по XSD
            xsd_files = [f for f in os.listdir(self.schema_dir) if f.endswith('.xsd')]
            if xsd_files:
                xsd_path = os.path.join(self.schema_dir, xsd_files[0])
                try:
                    schema_doc = etree.parse(xsd_path)
                    schema = etree.XMLSchema(schema_doc)
                    xml_doc = etree.parse(file_path)
                    schema.assertValid(xml_doc)
                    self.xml_file_input.setText(file_path)
                except etree.DocumentInvalid as e:
                    QMessageBox.warning(self, "Ошибка", f"Файл не соответствует схеме:\n{e}")
                    return
            else:
                # XSD нет — просто принимаем файл
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

        QMessageBox.information(self, "Информация", "Отправка данных...")
        QApplication.processEvents()

        result = push_xml(api_key, xml_file)

        if result["success"]:
            set_id = result.get("set_id", "")
            self.last_setid_display.setText(set_id)

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

        QMessageBox.information(self, "Информация", f"Запрос данных по SetId: {set_id}...")
        QApplication.processEvents()

        result = get_by_set_id(api_key, set_id)

        if not result["success"]:
            QMessageBox.critical(self, "Ошибка", result.get("error", "Неизвестная ошибка"))
            return

        records = result.get("records", [])
        if not records:
            QMessageBox.information(self, "Информация", "Записей не найдено")
            return

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
        snils_clean = snils_raw.replace('-', '').replace(' ', '')
        if not snils_clean.isdigit() or len(snils_clean) != 11:
            QMessageBox.warning(self, "Ошибка", "СНИЛС должен содержать 11 цифр")
            return
        snils = f"{snils_clean[0:3]}-{snils_clean[3:6]}-{snils_clean[6:9]} {snils_clean[9:11]}"

        QMessageBox.information(self, "Информация", f"Запрос данных по СНИЛС: {snils}...")
        QApplication.processEvents()

        result = get_by_snils(api_key, snils)

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
