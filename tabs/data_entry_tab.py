import os
import json
import webbrowser
import subprocess
import shutil
from openpyxl import Workbook
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QComboBox, QScrollArea,
    QFileDialog, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from importers.xlsx_importer import load_xlsx
from importers.xml_importer import load_xml


class DataEntryTab(QWidget):
    # Сигнал для передачи данных на вкладку Просмотр
    data_loaded = pyqtSignal(list, bool)  # (records, is_replace)

    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: white;")
        # Callback для получения существующих ключей (СНИЛС, программа)
        self.get_existing_keys_callback = None
        
        # Пути
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(self.base_dir, "data")
        self.schema_dir = os.path.join(self.base_dir, "schema")
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
        scroll.setStyleSheet("background-color: white; border: none;")
        
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
        """)
        group.setTitle("Данные УЦ и работодателя")
        
        layout = QVBoxLayout(group)
        
        # Первая строка: ИНН УЦ и Название УЦ
        row1 = QHBoxLayout()
        
        form1 = QFormLayout()
        self.tc_inn_label = QLabel("ИНН УЦ:")
        self.tc_inn_label.setStyleSheet("color: black;")
        self.tc_inn_input = QLineEdit()
        self.tc_inn_input.setFixedWidth(150)
        self.tc_inn_input.setPlaceholderText("10 или 12 цифр")
        self.tc_inn_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        form1.addRow(self.tc_inn_label, self.tc_inn_input)
        row1.addLayout(form1)
        row1.addSpacing(20)
        
        form2 = QFormLayout()
        self.tc_title_label = QLabel("Название УЦ:")
        self.tc_title_label.setStyleSheet("color: black;")
        self.tc_title_input = QLineEdit()
        self.tc_title_input.setMinimumWidth(300)
        self.tc_title_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        form2.addRow(self.tc_title_label, self.tc_title_input)
        row1.addLayout(form2)
        
        layout.addLayout(row1)
        
        # Вторая строка: ИНН Заказчика и Название Заказчика
        row2 = QHBoxLayout()
        
        form3 = QFormLayout()
        self.employer_inn_label = QLabel("ИНН Заказчика:")
        self.employer_inn_label.setStyleSheet("color: black;")
        self.employer_inn_input = QLineEdit()
        self.employer_inn_input.setFixedWidth(150)
        self.employer_inn_input.setPlaceholderText("10 или 12 цифр")
        self.employer_inn_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        form3.addRow(self.employer_inn_label, self.employer_inn_input)
        row2.addLayout(form3)
        row2.addSpacing(20)
        
        form4 = QFormLayout()
        self.employer_title_label = QLabel("Название Заказчика:")
        self.employer_title_label.setStyleSheet("color: black;")
        self.employer_title_input = QLineEdit()
        self.employer_title_input.setMinimumWidth(300)
        self.employer_title_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        form4.addRow(self.employer_title_label, self.employer_title_input)
        row2.addLayout(form4)
        
        layout.addLayout(row2)
        
        # Кнопка Сохранить данные
        btn_layout = QHBoxLayout()
        self.save_org_btn = QPushButton("Сохранить данные")
        self.save_org_btn.setStyleSheet("""
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
        self.save_org_btn.clicked.connect(self.save_org_settings)
        btn_layout.addWidget(self.save_org_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
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
        """)
        group.setTitle("Загрузка данных")
        
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        
        # Строка 1: XSD файл
        xsd_row = QHBoxLayout()
        self.xsd_label = QLabel("XSD схема:")
        self.xsd_label.setStyleSheet("color: black;")
        self.xsd_file_input = QLineEdit()
        self.xsd_file_input.setPlaceholderText("Не выбран")
        self.xsd_file_input.setReadOnly(True)
        self.xsd_file_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
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
        self.file_path_label.setStyleSheet("color: black;")
        self.file_path_input = QLineEdit()
        self.file_path_input.setPlaceholderText("Файл не выбран")
        self.file_path_input.setReadOnly(True)
        self.file_path_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
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
        self.last_name_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        col1.addRow("Фамилия:", self.last_name_input)

        self.first_name_input = QLineEdit()
        self.first_name_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        col1.addRow("Имя:", self.first_name_input)

        self.middle_name_input = QLineEdit()
        self.middle_name_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        col1.addRow("Отчество:", self.middle_name_input)

        self.position_input = QLineEdit()
        self.position_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        col1.addRow("Должность:", self.position_input)

        self.snils_input = QLineEdit()
        self.snils_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
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
        self.program_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
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
        self.protocol_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        col2.addRow("Номер протокола:", self.protocol_input)

        self.result_combo = QComboBox()
        self.result_combo.addItems(["Удовлетворительно", "Неудовлетворительно"])
        self.result_combo.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        col2.addRow("Результат:", self.result_combo)

        self.date_input = QLineEdit()
        self.date_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
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
        """Загрузка настроек из JSON файла"""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
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
        """Сохранение настроек УЦ и Заказчика"""
        # Валидация ИНН
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
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
            QMessageBox.information(self, "Успех", "Данные сохранены")
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
        if self.get_existing_keys_callback:
            existing = self.get_existing_keys_callback()
            has_existing = len(existing) > 0

        # Если есть данные — показываем диалог слияния
        merge_mode = False  # False = добавить, True = заменить
        if has_existing:
            reply = self._show_merge_dialog()
            if reply == "cancel":
                return
            elif reply == "replace":
                merge_mode = True
            # "merge" — merge_mode = False

        records = None
        error_count = 0
        error_messages = []

        if file_path.endswith(('.xlsx', '.xls')):
            records, error_count, error_messages = load_xlsx(file_path)
        elif file_path.endswith('.xml'):
            # Находим XSD для валидации
            xsd_files = [f for f in os.listdir(self.schema_dir) if f.endswith('.xsd')]
            xsd_path = os.path.join(self.schema_dir, xsd_files[0]) if xsd_files else None
            records, error_count, error_messages, xsd_errors = load_xml(file_path, xsd_path)

            # Если есть XSD-ошибки — показываем
            if xsd_errors:
                QMessageBox.warning(
                    self, "XSD-валидация",
                    "Файл не соответствует XSD-схеме:\n" + "\n".join(xsd_errors[:20])
                )
        else:
            QMessageBox.warning(self, "Ошибка", "Неподдерживаемый формат файла")
            return

        if records is None:
            # Критическая ошибка
            QMessageBox.warning(self, "Ошибка импорта", "\n".join(error_messages[:10]))
            return

        # Подстановка настроек УЦ/Заказчика — значения из формы ВСЕГДА заменяют данные из файла
        tc_inn = self.tc_inn_input.text().strip()
        tc_title = self.tc_title_input.text().strip()
        employer_inn = self.employer_inn_input.text().strip()
        employer_title = self.employer_title_input.text().strip()

        for rec in records:
            if tc_inn:
                rec['tc_inn'] = tc_inn
            if tc_title:
                rec['tc_title'] = tc_title
            if employer_inn:
                rec['employer_inn'] = employer_inn
            if employer_title:
                rec['employer_title'] = employer_title

        # Передаём данные на вкладку Просмотр
        self.data_loaded.emit(records, merge_mode)

        # Уведомление
        if error_count > 0:
            QMessageBox.warning(
                self, "Загрузка завершена",
                f"Успешно загружено: {len(records)} записей\n"
                f"Количество строк с ошибками: {error_count}"
            )
        else:
            QMessageBox.information(self, "Успех", f"Успешно загружено: {len(records)} записей")

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

        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QListWidgetItem, QHBoxLayout, QPushButton
        from PyQt6.QtGui import QColor

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
            widget.setStyleSheet("color: black; border: 2px solid red; padding: 4px;")
        else:
            widget.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")

    def _clear_field_errors(self):
        """Сброс подсветки ошибок на всех полях."""
        for w in [self.last_name_input, self.first_name_input, self.middle_name_input,
                   self.position_input, self.snils_input, self.program_input,
                   self.protocol_input, self.result_combo, self.date_input]:
            w.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")

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
