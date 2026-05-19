import os
import json
import logging
import webbrowser
import subprocess
import shutil
from openpyxl import Workbook
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QComboBox, QScrollArea,
    QFileDialog, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from importers.xlsx_importer import load_xlsx
from importers.xml_importer import load_xml
from utils.crypto import encrypt_data, decrypt_data

logger = logging.getLogger(__name__)


class DataEntryTab(QWidget):
    # Сигнал для передачи данных на вкладку Просмотр
    data_loaded = Signal(list, bool)  # (records, is_replace)

    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: transparent;")
        # Callback для получения существующих ключей (СНИЛС, программа)
        self.get_existing_keys_callback = None

        # Хранение ошибок последней загрузки для экспорта
        self._last_error_details = []
        self._last_duplicate_map = {}

        # Пути
        from utils.app_paths import get_app_data_dir, get_resource_dir
        self.resource_dir = get_resource_dir()
        self.data_dir = get_app_data_dir()
        self.schema_dir = os.path.join(self.resource_dir, "schema")
        self.settings_file = os.path.join(self.data_dir, "org_settings.json")
        
        # Создание директорий
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.schema_dir, exist_ok=True)
        
        # Основной layout с прокруткой
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background-color: transparent; border: none;")
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(15)
        
        # Раздел 1: Данные УЦ и работодателя
        scroll_layout.addWidget(self._create_org_group())
        
        # Раздел 2: Загрузка данных
        scroll_layout.addWidget(self._create_upload_group())
        
        # Раздел 3: Ввод данных работника
        scroll_layout.addWidget(self._create_manual_entry_group())
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)

        # Загрузка настроек
        self.load_settings()
        # Загрузка XSD при старте, если есть
        self.load_xsd_on_startup()

    def _create_org_group(self):
        """Создание группы 'Данные УЦ и работодателя'"""
        group = QGroupBox()
        group.setStyleSheet("""
            QGroupBox {
                border: 2px solid #4169E1;
                border-radius: 10px;
                margin-top: 10px;
                padding: 15px;
                background-color: transparent;
            }
            QGroupBox::title {
                color: #4169E1;
                font-weight: bold;
                font-size: 14px;
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        group.setTitle("Данные УЦ и работодателя")

        # QGridLayout для точного выравнивания:
        # Строка 0: ИНН УЦ (label) | ИНН УЦ (field) | [75px spacer] | Название УЦ (label) | Название УЦ (field)
        # Строка 1: ИНН Заказчика (label) | ИНН Заказчика (field) | [75px spacer] | Название Заказчика (label) | Название Заказчика (field)
        grid = QGridLayout(group)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(12)

        # === Строка 0: ИНН УЦ и Название УЦ ===
        self.tc_inn_label = QLabel("ИНН УЦ:")
        self.tc_inn_label.setStyleSheet("color: inherit; font-weight: bold;")
        self.tc_inn_label.setFixedWidth(110)
        grid.addWidget(self.tc_inn_label, 0, 0)

        self.tc_inn_input = QLineEdit()
        self.tc_inn_input.setFixedWidth(160)
        self.tc_inn_input.setPlaceholderText("10 или 12 цифр")
        self.tc_inn_input.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 5px; border-radius: 4px;")
        grid.addWidget(self.tc_inn_input, 0, 1)

        # Фиксированный отступ 2 см (~75px)
        grid.setColumnMinimumWidth(2, 75)

        self.tc_title_label = QLabel("Название УЦ:")
        self.tc_title_label.setStyleSheet("color: inherit; font-weight: bold;")
        self.tc_title_label.setFixedWidth(120)
        grid.addWidget(self.tc_title_label, 0, 3)

        self.tc_title_input = QLineEdit()
        self.tc_title_input.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 5px; border-radius: 4px;")
        self.tc_title_input.setPlaceholderText("Полное наименование")
        grid.addWidget(self.tc_title_input, 0, 4)

        # === Строка 1: ИНН Заказчика и Название Заказчика ===
        self.employer_inn_label = QLabel("ИНН Заказчика:")
        self.employer_inn_label.setStyleSheet("color: inherit; font-weight: bold;")
        self.employer_inn_label.setFixedWidth(110)
        grid.addWidget(self.employer_inn_label, 1, 0)

        self.employer_inn_input = QLineEdit()
        self.employer_inn_input.setFixedWidth(160)
        self.employer_inn_input.setPlaceholderText("10 или 12 цифр")
        self.employer_inn_input.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 5px; border-radius: 4px;")
        grid.addWidget(self.employer_inn_input, 1, 1)

        # Колонка-разделитель уже создана

        self.employer_title_label = QLabel("Название Заказчика:")
        self.employer_title_label.setStyleSheet("color: inherit; font-weight: bold;")
        self.employer_title_label.setFixedWidth(120)
        grid.addWidget(self.employer_title_label, 1, 3)

        self.employer_title_input = QLineEdit()
        self.employer_title_input.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 5px; border-radius: 4px;")
        self.employer_title_input.setPlaceholderText("Полное наименование")
        grid.addWidget(self.employer_title_input, 1, 4)

        # Растягивающаяся колонка для полей названий
        grid.setColumnStretch(4, 1)

        # Кнопка Сохранить данные
        btn_layout = QHBoxLayout()
        self.save_org_btn = QPushButton("Сохранить данные")
        self.save_org_btn.setStyleSheet("""
            QPushButton {
                background-color: #4169E1;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #3151B1;
            }
        """)
        self.save_org_btn.clicked.connect(self.save_org_settings)
        btn_layout.addWidget(self.save_org_btn)
        btn_layout.addStretch()
        grid.addLayout(btn_layout, 2, 0, 1, 5)

        return group

    def _create_upload_group(self):
        """Создание группы 'Загрузка данных'"""
        group = QGroupBox()
        group.setStyleSheet("""
            QGroupBox {
                border: 2px solid #4169E1;
                border-radius: 10px;
                margin-top: 10px;
                padding: 15px;
                background-color: transparent;
            }
            QGroupBox::title {
                color: #4169E1;
                font-weight: bold;
                font-size: 14px;
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        group.setTitle("Загрузка данных")
        
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        
        # Строка 1: XSD файл
        xsd_row = QHBoxLayout()
        self.xsd_label = QLabel("XSD схема:")
        self.xsd_label.setStyleSheet("color: inherit;")
        self.xsd_file_input = QLineEdit()
        self.xsd_file_input.setPlaceholderText("Не выбран")
        self.xsd_file_input.setReadOnly(True)
        self.xsd_file_input.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 4px;")
        self.upload_xsd_btn = QPushButton("Загрузить XSD")
        self.upload_xsd_btn.setStyleSheet("""
            QPushButton {
                background-color: #4169E1;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #3151B1;
            }
        """)
        self.upload_xsd_btn.clicked.connect(self.upload_xsd)
        xsd_separator = QLabel("  ")
        self.xsd_scheme_btn = QPushButton("Схема XSD")
        self.xsd_scheme_btn.setStyleSheet("""
            QPushButton {
                background-color: #4169E1;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #3151B1;
            }
        """)
        self.xsd_scheme_btn.clicked.connect(self.open_xsd_scheme)
        
        xsd_row.addWidget(self.xsd_label)
        xsd_row.addWidget(self.xsd_file_input)
        xsd_row.addWidget(self.upload_xsd_btn)
        xsd_row.addWidget(xsd_separator)
        xsd_row.addWidget(self.xsd_scheme_btn)
        layout.addLayout(xsd_row)
        
        # Строка 2: Выбранный файл
        file_row = QHBoxLayout()
        self.file_path_label = QLabel("Выбранный файл:")
        self.file_path_label.setStyleSheet("color: inherit;")
        self.file_path_input = QLineEdit()
        self.file_path_input.setPlaceholderText("Файл не выбран")
        self.file_path_input.setReadOnly(True)
        self.file_path_input.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 4px;")
        file_row.addWidget(self.file_path_label)
        file_row.addWidget(self.file_path_input)
        layout.addLayout(file_row)
        
        # Строка 3: Кнопки загрузки
        btn_row = QHBoxLayout()
        self.select_file_btn = QPushButton("Выбрать файл")
        self.select_file_btn.setStyleSheet("""
            QPushButton {
                background-color: #4169E1;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #3151B1;
            }
        """)
        self.select_file_btn.clicked.connect(self.select_file)
        self.upload_file_btn = QPushButton("Загрузить файл")
        self.upload_file_btn.setStyleSheet("""
            QPushButton {
                background-color: #4169E1;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #3151B1;
            }
        """)
        self.upload_file_btn.clicked.connect(self.upload_file)
        template_separator = QLabel("  ")
        self.create_template_btn = QPushButton("Создать шаблон")
        self.create_template_btn.setStyleSheet("""
            QPushButton {
                background-color: #4169E1;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #3151B1;
            }
        """)
        self.create_template_btn.clicked.connect(self.create_template)
        
        btn_row.addWidget(self.select_file_btn)
        btn_row.addWidget(self.upload_file_btn)
        btn_row.addWidget(template_separator)
        btn_row.addWidget(self.create_template_btn)
        layout.addLayout(btn_row)
        
        return group

    def _create_manual_entry_group(self):
        """Создание группы 'Ввод данных работника'"""
        group = QGroupBox()
        group.setStyleSheet("""
            QGroupBox {
                border: 2px solid #4169E1;
                border-radius: 10px;
                margin-top: 10px;
                padding: 15px;
                background-color: transparent;
            }
            QGroupBox::title {
                color: #4169E1;
                font-weight: bold;
                font-size: 14px;
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        group.setTitle("Ввод данных работника")

        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        # Два столбца с QFormLayout
        columns = QHBoxLayout()
        columns.setSpacing(40)  # 1 см отступ между столбцами

        # Первый столбец: QFormLayout
        col1 = QFormLayout()
        col1.setSpacing(10)
        col1.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        col1.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.last_name_input = QLineEdit()
        self.last_name_input.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 4px;")
        col1.addRow("Фамилия:", self.last_name_input)

        self.first_name_input = QLineEdit()
        self.first_name_input.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 4px;")
        col1.addRow("Имя:", self.first_name_input)

        self.middle_name_input = QLineEdit()
        self.middle_name_input.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 4px;")
        col1.addRow("Отчество:", self.middle_name_input)

        self.position_input = QLineEdit()
        self.position_input.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 4px;")
        col1.addRow("Должность:", self.position_input)

        self.snils_input = QLineEdit()
        self.snils_input.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 4px;")
        self.snils_input.setPlaceholderText("123-456-789 00")
        self.snils_input.setMaxLength(15)  # 123-456-789 00
        self.snils_input.textChanged.connect(self._format_snils_input)
        col1.addRow("СНИЛС:", self.snils_input)

        columns.addLayout(col1)

        # Второй столбец: QFormLayout
        col2 = QFormLayout()
        col2.setSpacing(10)
        col2.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        col2.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        program_row = QHBoxLayout()
        self.program_input = QLineEdit()
        self.program_input.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 4px;")
        self.program_input.setPlaceholderText("Например: 1,2,3")
        self.help_btn = QPushButton("Справка")
        self.help_btn.setStyleSheet("""
            QPushButton {
                background-color: #4169E1;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #3151B1;
            }
        """)
        self.help_btn.clicked.connect(self.show_programs_help)
        program_row.addWidget(self.program_input)
        program_row.addWidget(self.help_btn)
        col2.addRow("Номер программы:", program_row)

        self.protocol_input = QLineEdit()
        self.protocol_input.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 4px;")
        col2.addRow("Номер протокола:", self.protocol_input)

        self.result_combo = QComboBox()
        self.result_combo.addItems(["Удовлетворительно", "Неудовлетворительно"])
        self.result_combo.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 4px;")
        col2.addRow("Результат:", self.result_combo)

        self.date_input = QLineEdit()
        self.date_input.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 4px;")
        self.date_input.setPlaceholderText("ДД.ММ.ГГГГ или ДДММГГГГ")
        col2.addRow("Дата:", self.date_input)

        columns.addLayout(col2)
        layout.addLayout(columns)
        
        # Кнопки
        btn_row = QHBoxLayout()
        self.save_data_btn = QPushButton("Сохранить данные")
        self.save_data_btn.setStyleSheet("""
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
        """)
        self.save_data_btn.clicked.connect(self.save_manual_data)
        btn_row.addWidget(self.save_data_btn)
        
        btn_row.addSpacing(120)  # 3 см отступ
        
        self.clear_btn = QPushButton("Очистить")
        self.clear_btn.setStyleSheet("""
            QPushButton {
                color: red;
                border: 2px solid red;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
                background-color: white;
            }
            QPushButton:hover {
                background-color: #FFE0E0;
            }
        """)
        self.clear_btn.clicked.connect(self.clear_manual_form)
        btn_row.addWidget(self.clear_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        
        return group

    def load_settings(self):
        """Загрузка настроек из JSON файла (с расшифровкой)"""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    wrapper = json.load(f)
                encrypted = wrapper.get('data', '')
                if encrypted:
                    settings = decrypt_data(encrypted)
                else:
                    settings = wrapper
                self.tc_inn_input.setText(settings.get('tc_inn', ''))
                self.tc_title_input.setText(settings.get('tc_title', ''))
                self.employer_inn_input.setText(settings.get('employer_inn', ''))
                self.employer_title_input.setText(settings.get('employer_title', ''))
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Ошибка чтения настроек: {e}")

    def load_xsd_on_startup(self):
        """Загрузка XSD при старте, если есть в папке schema"""
        xsd_files = [f for f in os.listdir(self.schema_dir) if f.endswith('.xsd')]
        if xsd_files:
            xsd_path = os.path.join(self.schema_dir, xsd_files[0])
            self.xsd_file_input.setText(xsd_path)

    def save_org_settings(self):
        """Сохранение настроек УЦ и Заказчика (с шифрованием)"""
        tc_inn = self.tc_inn_input.text().strip()
        employer_inn = self.employer_inn_input.text().strip()
        
        if tc_inn and not (tc_inn.isdigit() and len(tc_inn) in [10, 12]):
            QMessageBox.warning(self, "Ошибка", "ИНН - только 10 или 12 цифр")
            return
        
        if employer_inn and not (employer_inn.isdigit() and len(employer_inn) in [10, 12]):
            QMessageBox.warning(self, "Ошибка", "ИНН - только 10 или 12 цифр")
            return
        
        if not tc_inn or not self.tc_title_input.text().strip() or \
           not employer_inn or not self.employer_title_input.text().strip():
            QMessageBox.warning(self, "Ошибка", "Заполните данные УЦ/Работодателя")
            return
        
        settings = {
            'tc_inn': tc_inn,
            'tc_title': self.tc_title_input.text().strip(),
            'employer_inn': employer_inn,
            'employer_title': self.employer_title_input.text().strip()
        }
        
        try:
            encrypted = encrypt_data(settings)
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump({"data": encrypted}, f, ensure_ascii=False, indent=4)
            QMessageBox.information(self, "Успех", "Данные сохранены (зашифрованы)")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка сохранения: {e}")

    def upload_xsd(self):
        """Загрузка XSD файла"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите XSD файл", "", "XSD Files (*.xsd)"
        )
        if file_path:
            try:
                dest_path = os.path.join(self.schema_dir, os.path.basename(file_path))
                shutil.copy(file_path, dest_path)
                self.xsd_file_input.setText(dest_path)
                QMessageBox.information(self, "Успех", "XSD файл успешно загружен")
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Ошибка загрузки XSD: {e}")

    def open_xsd_scheme(self):
        """Открытие ссылки на схему XSD"""
        import webbrowser
        webbrowser.open("https://akot.rosmintrud.ru/sout/info")

    def select_file(self):
        """Выбор файла для загрузки"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл", "", "Excel/XML Files (*.xlsx *.xls *.xml)"
        )
        if file_path:
            self.file_path_input.setText(file_path)

    def upload_file(self):
        """Загрузка выбранного файла"""
        file_path = self.file_path_input.text()
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "Ошибка", "Файл не выбран")
            return

        # Проверяем, есть ли уже данные (через callback)
        has_existing = False
        existing_keys = set()
        if self.get_existing_keys_callback:
            existing_keys = self.get_existing_keys_callback()
            has_existing = len(existing_keys) > 0

        # Если есть данные — показываем диалог слияния
        merge_mode = False  # False = добавить, True = заменить
        if has_existing:
            reply = self._show_merge_dialog()
            if reply == "cancel":
                return
            elif reply == "replace":
                merge_mode = True
                existing_keys = set()
            # "merge" — merge_mode = False

        records = None
        error_details = []  # [{'row': int, 'type': str, 'field': str, 'message': str}]
        error_rows_set = set()
        duplicate_map = {}  # {(snils, program): [строка1, строка2, ...]}
        xml_xsd_errors = []
        password = None

        if file_path.endswith(('.xlsx', '.xls')):
            result = load_xlsx(file_path)

            if len(result) >= 4:
                records, error_details, error_rows_set = result[0], result[1], result[2]
                error_msg = result[3] if len(result) > 3 else ""
                if records is None:
                    err_msg = error_msg if error_msg else (str(error_details[0]['message']) if error_details else "Неизвестная ошибка")
                    QMessageBox.warning(self, "Ошибка импорта", err_msg)
                    return
            elif len(result) >= 3:
                records, error_details, error_rows_set = result[0], result[1], result[2]
                if records is None:
                    err = error_details[0]['message'] if error_details else "Ошибка"
                    QMessageBox.warning(self, "Ошибка импорта", str(err))
                    return
            else:
                records = None
                error_details = []
                error_rows_set = set()
                QMessageBox.warning(self, "Ошибка", "Ошибка при загрузке файла")
                return
        elif file_path.endswith('.xml'):
            # Находим XSD для валидации
            xsd_files = [f for f in os.listdir(self.schema_dir) if f.endswith('.xsd')]
            xsd_path = os.path.join(self.schema_dir, xsd_files[0]) if xsd_files else None
            records, xml_error_count, xml_error_messages, xml_xsd_errors = load_xml(file_path, xsd_path)

            # Если есть XSD-ошибки — показываем
            if xml_xsd_errors:
                QMessageBox.warning(
                    self, "XSD-валидация",
                    "Файл не соответствует XSD-схеме:\n" + "\n".join(xml_xsd_errors[:20])
                )
        else:
            QMessageBox.warning(self, "Ошибка", "Неподдерживаемый формат файла")
            return

        if records is None:
            # Критическая ошибка
            msg = "\n".join(xml_xsd_errors[:10]) if xml_xsd_errors else "Ошибка импорта"
            QMessageBox.warning(self, "Ошибка импорта", msg)
            return

        # Проверка дубликатов с существующими данными и внутри загруженных
        validated_records = []
        # Сначала соберём карту существующих данных: (snils, program) -> [номера строк]
        existing_rows_map = {}
        if not merge_mode and self.get_existing_keys_callback:
            # Для режима "объединить" — найдём номера строк в существующей таблице
            # Получаем строки из таблицы "Просмотр данных"
            try:
                table = None
                # Ищем таблицу через родительский виджет
                main_window = self.window()
                if main_window:
                    tabs_widget = main_window.findChild(type(self.data_view_tab.table))
                    # Проще — получим через callback
                    pass
            except Exception as e:
                logger.debug(f"Could not get table: {e}")

            # Альтернативный подход: передаём таблицу через callback
            # Но пока используем то, что есть — добавим callback get_existing_rows
            if hasattr(self, 'get_existing_rows_callback') and self.get_existing_rows_callback:
                for row_idx, snils, prog in self.get_existing_rows_callback():
                    key = (snils, prog)
                    if key not in existing_rows_map:
                        existing_rows_map[key] = []
                    existing_rows_map[key].append(f"система (стр. {row_idx})")

        for rec in records:
            key = (rec.get('snils', ''), rec.get('program', ''))
            source_row = rec.get('source_row', '?')
            if key in existing_keys:
                # Дубликат с существующими данными
                if key not in duplicate_map:
                    duplicate_map[key] = []
                # Добавляем строки из системы (если ещё не добавлены)
                if key in existing_rows_map:
                    for label in existing_rows_map[key]:
                        if label not in duplicate_map[key]:
                            duplicate_map[key].append(label)
                # Добавляем текущую строку
                row_label = f"стр. {source_row}"
                if row_label not in duplicate_map[key]:
                    duplicate_map[key].append(row_label)
                continue

            # Проверка дубликата внутри загруженного файла
            is_internal_dup = False
            for vr in validated_records:
                if (vr.get('snils', ''), vr.get('program', '')) == key:
                    is_internal_dup = True
                    break

            if is_internal_dup:
                # Дубликат внутри загруженного файла
                if key not in duplicate_map:
                    duplicate_map[key] = []
                row_label = f"стр. {source_row}"
                if row_label not in duplicate_map[key]:
                    duplicate_map[key].append(row_label)
                continue

            existing_keys.add(key)
            validated_records.append(rec)

        # Подстановка настроек УЦ/Заказчика — значения из формы ВСЕГДА заменяют данные из файла
        tc_inn = self.tc_inn_input.text().strip()
        tc_title = self.tc_title_input.text().strip()
        employer_inn = self.employer_inn_input.text().strip()
        employer_title = self.employer_title_input.text().strip()

        for rec in validated_records:
            if tc_inn:
                rec['tc_inn'] = tc_inn
            if tc_title:
                rec['tc_title'] = tc_title
            if employer_inn:
                rec['employer_inn'] = employer_inn
            if employer_title:
                rec['employer_title'] = employer_title
            # Удаляем техническое поле source_row
            rec.pop('source_row', None)

        # Передаём данные на вкладку Просмотр
        self.data_loaded.emit(validated_records, merge_mode)

        # Сохраняем ошибки и дубликаты для экспорта
        self._last_error_details = error_details
        self._last_duplicate_map = duplicate_map

        # Уведомление
        total_errors = len(error_rows_set) + len(duplicate_map)
        if total_errors > 0:
            self._show_upload_result_dialog(len(validated_records), len(error_rows_set), len(duplicate_map))
        else:
            QMessageBox.information(self, "Успех", f"Успешно загружено: {len(validated_records)} записей")

    def _show_merge_dialog(self):
        """Диалог: что делать с существующими данными."""
        msg = QMessageBox()
        msg.setWindowTitle("Загрузка данных")
        msg.setText("В системе уже есть данные. Что сделать?")
        msg.setInformativeText("Выберите действие:")
        merge_btn = msg.addButton("Объединить", QMessageBox.ButtonRole.AcceptRole)
        replace_btn = msg.addButton("Удалить старые", QMessageBox.ButtonRole.AcceptRole)
        cancel_btn = msg.addButton("Отменить загрузку", QMessageBox.ButtonRole.RejectRole)

        msg.exec()
        clicked = msg.clickedButton()

        if clicked == merge_btn:
            return "merge"
        elif clicked == replace_btn:
            return "replace"
        else:
            return "cancel"

    def _ask_password(self):
        """Диалог ввода пароля для защищённого Excel-файла."""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout

        dialog = QDialog(self)
        dialog.setWindowTitle("Ввод пароля")
        dialog.setMinimumSize(350, 130)
        dialog.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        dialog.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                color: inherit;
                font-size: 13px;
            }
            QLineEdit { color: black;
                border: 1px solid #CCCCCC;
                padding: 5px;
                background-color: white;
            }
            QPushButton {
                background-color: #4169E1;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #3151B1;
            }
        """)

        layout = QVBoxLayout(dialog)

        label = QLabel("Внимание: библиотека openpyxl не поддерживает пароли Excel.\nДля загрузки сохраните файл БЕЗ пароля:\nExcel → Файл → Сохранить как → Инструменты → Параметры → Защита → снять пароль")
        label.setWordWrap(True)
        layout.addWidget(label)

        password_input = QLineEdit()
        password_input.setEchoMode(QLineEdit.EchoMode.Password)
        password_input.setPlaceholderText("Оставьте пустым, если файл без пароля")
        layout.addWidget(password_input)

        buttons = QHBoxLayout()
        ok_btn = QPushButton("ОК")
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(dialog.reject)
        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

        if dialog.exec():
            return password_input.text()
        return "CANCEL"

    def _show_upload_result_dialog(self, success_count, error_rows, duplicate_count):
        """Диалог результата загрузки с кнопкой 'Показать ошибки'."""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout

        dialog = QDialog(self)
        dialog.setWindowTitle("Загрузка завершена")
        dialog.setMinimumSize(450, 200)
        dialog.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        dialog.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                color: inherit;
                font-size: 13px;
            }
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
            QPushButton#showErrorsBtn {
                background-color: #FF8C00;
            }
            QPushButton#showErrorsBtn:hover {
                background-color: #E07800;
            }
        """)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)

        # Информация
        info_label = QLabel(
            f"<b>Успешно загружено:</b> {success_count} записей<br><br>"
            f"<b style='color:red;'>Строк с ошибками:</b> {error_rows}<br>"
            f"<b style='color:orange;'>Дубликатов:</b> {duplicate_count}"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("padding: 10px;")
        layout.addWidget(info_label)

        # Кнопки
        btn_layout = QHBoxLayout()
        
        show_errors_btn = QPushButton("Показать ошибки")
        show_errors_btn.setObjectName("showErrorsBtn")
        show_errors_btn.clicked.connect(lambda: [self._export_error_report(dialog)])
        
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(dialog.close)

        btn_layout.addWidget(show_errors_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        dialog.exec()

    def _export_error_report(self, parent_dialog):
        """Экспорт отчёта об ошибках в XLSX."""
        from importers.error_report import export_error_report
        from datetime import datetime

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить отчёт об ошибках",
            f"Ошибки_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            "Excel Files (*.xlsx)"
        )

        if file_path:
            error_details = getattr(self, '_last_error_details', [])
            duplicate_map = getattr(self, '_last_duplicate_map', {})

            ok, msg = export_error_report(error_details, duplicate_map, file_path)
            if ok:
                QMessageBox.information(self, "Успех", msg)
            else:
                QMessageBox.warning(self, "Ошибка", msg)

        # Закрываем родительский диалог
        parent_dialog.close()

    def create_template(self):
        """Создание шаблона XLSX"""
        try:
            from openpyxl import Workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "Шаблон"
            
            headers = [
                "Фамилия", "Имя", "Отчество", "СНИЛС", "Должность",
                "ИНН Заказчика", "Наименование ЮЛ Заказчика", "ИНН УЦ",
                "Наименование УЦ", "Результат", "№ программы", "Дата", "№ протокола"
            ]
            ws.append(headers)
            
            template_path = os.path.join(self.base_dir, "Шаблон.xlsx")
            wb.save(template_path)
            
            reply = QMessageBox.question(
                self, "Успех",
                "Шаблон создан. Открыть расположение файла?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                import subprocess
                subprocess.Popen(f'explorer /select,"{template_path}"')
        except ImportError:
            QMessageBox.warning(self, "Ошибка", "Установите openpyxl: pip install openpyxl")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка создания шаблона: {e}")

    def show_programs_help(self):
        """Показать справку по программам обучения"""
        programs = {
            "1": "Оказание первой помощи пострадавшим",
            "2": "Использование (применение) средств индивидуальной защиты",
            "3": "Общие вопросы охраны труда и функционирования системы управления охраной труда",
            "4": "Безопасные методы и приемы выполнения работ при воздействии вредных и (или) опасных производственных факторов",
            "6": "Безопасные методы и приемы выполнения земляных работ",
            "7": "Безопасные методы и приемы выполнения ремонтных, монтажных и демонтажных работ зданий и сооружений",
            "8": "Безопасные методы и приемы выполнения работ при размещении, монтаже, техническом обслуживании и ремонте технологического оборудования",
            "9": "Безопасные методы и приемы выполнения работ на высоте",
            "10": "Безопасные методы и приемы выполнения пожароопасных работ",
            "11": "Безопасные методы и приемы выполнения работ в ограниченных и замкнутых пространствах (ОЗП)",
            "12": "Безопасные методы и приемы выполнения строительных работ",
            "13": "Безопасные методы и приемы выполнения работ, связанных с опасностью воздействия сильнодействующих и ядовитых веществ",
            "14": "Безопасные методы и приемы выполнения газоопасных работ",
            "15": "Безопасные методы и приемы выполнения огневых работ",
            "16": "Безопасные методы и приемы выполнения работ, связанных с эксплуатацией подъемных сооружений",
            "17": "Безопасные методы и приемы выполнения работ, связанных с эксплуатацией тепловых энергоустановок",
            "18": "Безопасные методы и приемы выполнения работ в электроустановках",
            "19": "Безопасные методы и приемы выполнения работ, связанных с эксплуатацией сосудов, работающих под избыточным давлением",
            "20": "Безопасные методы и приемы обращения с животными",
            "21": "Безопасные методы и приемы при выполнении водолазных работ",
            "22": "Безопасные методы и приемы работ по поиску, идентификации, обезвреживанию и уничтожению взрывоопасных предметов",
            "23": "Безопасные методы и приемы работ в непосредственной близости от полотна или проезжей части эксплуатируемых автомобильных и железных дорог",
            "24": "Безопасные методы и приемы работ на участках с патогенным заражением почвы",
            "25": "Безопасные методы и приемы работ по валке леса в особо опасных условиях",
            "26": "Безопасные методы и приемы работ по перемещению тяжеловесных и крупногабаритных грузов",
            "27": "Безопасные методы и приемы работ с радиоактивными веществами и источниками ионизирующих излучений",
            "28": "Безопасные методы и приемы работ с ручным инструментом, в том числе с пиротехническим",
            "29": "Безопасные методы и приемы работ в театрах"
        }

        blue_programs = {"1", "2", "3", "4", "18", "23"}

        from PySide6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QListWidgetItem, QHBoxLayout, QPushButton
        from PySide6.QtGui import QColor

        dialog = QDialog(self)
        dialog.setWindowTitle("Программы обучения")
        dialog.setMinimumSize(650, 700)
        layout = QVBoxLayout(dialog)

        list_widget = QListWidget()
        list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid #CCCCCC;
                background-color: white;
            }
            QListWidget::item {
                padding: 5px;
            }
        """)

        for num, title in programs.items():
            item = QListWidgetItem(f"{num}: {title}")
            item.setData(Qt.ItemDataRole.UserRole, num)
            if num in blue_programs:
                item.setForeground(QColor("#4169E1"))
            list_widget.addItem(item)

        layout.addWidget(list_widget)

        # Кнопка Закрыть
        btn_layout = QHBoxLayout()
        close_btn = QPushButton("Закрыть")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #4169E1;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #3151B1;
            }
        """)
        close_btn.clicked.connect(dialog.close)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        # Двойной клик
        def on_double_click(item):
            program_num = item.data(Qt.ItemDataRole.UserRole)
            current = self.program_input.text().strip()
            if current.endswith(','):
                current = current[:-1]
            programs_list = [p.strip() for p in current.split(',') if p.strip()] if current else []
            if len(programs_list) >= 10:
                QMessageBox.warning(self, "Предупреждение", "Превышено количество программ для одного работника")
                return
            if program_num not in programs_list:
                programs_list.append(program_num)
            self.program_input.setText(','.join(programs_list) + ',')

        list_widget.itemDoubleClicked.connect(on_double_click)
        dialog.exec()

    def _format_snils_input(self, text):
        """Автоформатирование СНИЛС при вводе: 123-456-789 00"""
        self.snils_input.blockSignals(True)
        try:
            digits = ''.join(c for c in text if c.isdigit())[:11]
            formatted = ''
            for i, d in enumerate(digits):
                if i == 3:
                    formatted += '-'
                elif i == 6:
                    formatted += '-'
                elif i == 9:
                    formatted += ' '
                formatted += d
            self.snils_input.setText(formatted)
        finally:
            self.snils_input.blockSignals(False)

    def _set_field_error(self, widget, is_error):
        """Подсветка поля красной рамкой при ошибке валидации."""
        if is_error:
            widget.setStyleSheet("color: inherit; border: 2px solid red; padding: 4px;")
        else:
            widget.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 4px;")

    def _clear_field_errors(self):
        """Сброс подсветки ошибок на всех полях."""
        for w in [self.last_name_input, self.first_name_input, self.middle_name_input,
                   self.position_input, self.snils_input, self.program_input,
                   self.protocol_input, self.result_combo, self.date_input]:
            w.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 4px;")

    def save_manual_data(self):
        """Сохранение данных ручного ввода"""
        from datetime import datetime

        # Сброс подсветки
        self._clear_field_errors()

        # Проверка заполненности полей
        fields = {
            'Фамилия': self.last_name_input.text().strip(),
            'Имя': self.first_name_input.text().strip(),
            'Отчество': self.middle_name_input.text().strip(),
            'Должность': self.position_input.text().strip(),
            'СНИЛС': self.snils_input.text().strip(),
            'Номер программы': self.program_input.text().strip(),
            'Номер протокола': self.protocol_input.text().strip(),
            'Результат': self.result_combo.currentText(),
            'Дата': self.date_input.text().strip()
        }

        # Карта полей к виджетам для подсветки
        field_widgets = {
            'Фамилия': self.last_name_input,
            'Имя': self.first_name_input,
            'Отчество': self.middle_name_input,
            'Должность': self.position_input,
            'СНИЛС': self.snils_input,
            'Номер программы': self.program_input,
            'Номер протокола': self.protocol_input,
            'Результат': self.result_combo,
            'Дата': self.date_input
        }

        empty_fields = [k for k, v in fields.items() if not v]
        if empty_fields:
            for f in empty_fields:
                self._set_field_error(field_widgets[f], True)
            QMessageBox.warning(self, "Ошибка", "Заполните все строки")
            return

        # Валидация ФИО и Должность — только текст
        for field_name in ['Фамилия', 'Имя', 'Отчество', 'Должность']:
            value = fields[field_name]
            if not value.replace(' ', '').replace('-', '').isalpha():
                self._set_field_error(field_widgets[field_name], True)
                QMessageBox.warning(self, "Ошибка", f"{field_name} — только текст")
                return

        # Валидация СНИЛС — 11 цифр
        snils = fields['СНИЛС'].replace('-', '').replace(' ', '')
        if not snils.isdigit() or len(snils) != 11:
            self._set_field_error(field_widgets['СНИЛС'], True)
            QMessageBox.warning(self, "Ошибка", "СНИЛС должен содержать 11 цифр")
            return

        # Валидация номера программы
        program_str = fields['Номер программы']
        valid_programs = {'1', '2', '3', '4', '6', '7', '8', '9', '10', '11', '12',
                         '13', '14', '15', '16', '17', '18', '19', '20', '21',
                         '22', '23', '24', '25', '26', '27', '28', '29'}
        programs = [p.strip() for p in program_str.rstrip(',').split(',') if p.strip()]
        if not programs:
            self._set_field_error(field_widgets['Номер программы'], True)
            QMessageBox.warning(self, "Ошибка", "Некорректный номер программы")
            return
        for prog in programs:
            if prog not in valid_programs:
                self._set_field_error(field_widgets['Номер программы'], True)
                QMessageBox.warning(self, "Ошибка", "Некорректный номер программы")
                return

        # Валидация даты
        date_str = fields['Дата'].replace('.', '').replace('-', '')
        if not date_str.isdigit():
            self._set_field_error(field_widgets['Дата'], True)
            QMessageBox.warning(self, "Ошибка", "Дата некорректна. Введите корректную дату в формате ЧЧ.ММ.ГГГГ или ЧЧММГГГГ")
            return
        try:
            if len(date_str) == 8:
                date_obj = datetime.strptime(date_str, "%d%m%Y")
            else:
                self._set_field_error(field_widgets['Дата'], True)
                QMessageBox.warning(self, "Ошибка", "Дата некорректна. Введите корректную дату в формате ЧЧ.ММ.ГГГГ или ЧЧММГГГГ")
                return
            # Дата <= текущей
            if date_obj.date() > datetime.now().date():
                self._set_field_error(field_widgets['Дата'], True)
                QMessageBox.warning(self, "Ошибка", "Дата не может быть больше текущей")
                return
        except ValueError:
            self._set_field_error(field_widgets['Дата'], True)
            QMessageBox.warning(self, "Ошибка", "Дата некорректна. Введите корректную дату в формате ЧЧ.ММ.ГГГГ или ЧЧММГГГГ")
            return

        QMessageBox.information(self, "Успех", "Запись создана")

        # Проверка дублей перед отправкой
        if self.get_existing_keys_callback:
            existing_keys = self.get_existing_keys_callback()
            new_keys = [(snils, prog) for prog in programs]
            duplicates = [k for k in new_keys if k in existing_keys]
            if duplicates:
                QMessageBox.warning(
                    self, "Предупреждение",
                    f"Выявлены аналогичные данные - {len(duplicates)} строк"
                )
                return

        # Формируем записи для передачи на вкладку Просмотр
        settings_tc_inn = self.tc_inn_input.text().strip()
        settings_tc_title = self.tc_title_input.text().strip()
        settings_employer_inn = self.employer_inn_input.text().strip()
        settings_employer_title = self.employer_title_input.text().strip()

        records = []
        for prog in programs:
            record = {
                'last_name': fields['Фамилия'],
                'first_name': fields['Имя'],
                'middle_name': fields['Отчество'],
                'snils': snils,
                'position': fields['Должность'],
                'employer_inn': settings_employer_inn,
                'employer_title': settings_employer_title,
                'tc_inn': settings_tc_inn,
                'tc_title': settings_tc_title,
                'result': fields['Результат'],
                'program': prog,
                'date': fields['Дата'],
                'protocol': fields['Номер протокола']
            }
            records.append(record)

        self.data_loaded.emit(records, False)
        self.clear_manual_form(except_program=True)

    def clear_manual_form(self, except_program=False):
        """Очистка формы ручного ввода"""
        self.last_name_input.clear()
        self.first_name_input.clear()
        self.middle_name_input.clear()
        self.position_input.clear()
        self.snils_input.clear()
        if not except_program:
            self.program_input.clear()
        self.protocol_input.clear()
        self.result_combo.setCurrentIndex(0)  # Удовлетворительно
        self.date_input.clear()
