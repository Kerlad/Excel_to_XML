"""
Основное окно приложения с вкладками
"""

from PyQt6.QtWidgets import (QMainWindow, QTabWidget, QWidget, QVBoxLayout,QHBoxLayout, QLabel, QLineEdit, QPushButton,
QTextEdit, QFileDialog, QMessageBox, QDialog,
QDialogButtonBox, QListWidget, QListWidgetItem,
QTableWidget, QTableWidgetItem, QHeaderView,
QComboBox, QGroupBox, QFormLayout, QSplitter,
QToolBar, QStatusBar, QMenu, QMenuBar,
QScrollArea, QFrame)
from PyQt6.QtGui import QFont, QIcon, QAction
from PyQt6.QtCore import Qt, QCoreApplication

from typing import Optional
import sys
import os
import json

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data_model import DataManager, WorkerRecord


# Путь к файлу настроек организации
# Используем абсолютный путь относительно корневого каталога проекта
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORG_SETTINGS_FILE = os.path.join(PROJECT_ROOT, 'data', 'org_settings.json')


class ProgramListDialog(QDialog):
    """Диалог выбора программ обучения"""

    PROGRAMS = {
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
        "17": "Безопасные методы и приемы выполнения работ, связанные с эксплуатацией тепловых энергоустановок",
        "18": "Безопасные методы и приемы выполнения работ в электроустановках",
        "19": "Безопасные методы и приемы выполнения работ, связанные с эксплуатацией сосудов, работающих под избыточным давлением",
        "20": "Безопасные методы и приемы обращения с животными",
        "21": "Безопасные методы и приемы при выполнении водолазных работ",
        "22": "Безопасные методы и приемы работ по поиску, идентификации, обезвреживанию и уничтожению взрывоопасных предметов",
        "23": "Безопасные методы и приемы работ в непосредственной близости от полотна или проезжей части эксплуатируемых автомобильных и железных дорог",
        "24": "Безопасные методы и приемы работ на участках с патогенным заражением почвы",
        "25": "Безопасные методы и приемы работ по валке леса в особо опасных условиях",
        "26": "Безопасные методы и приемы работ по перемещению тяжеловесных и крупногабаритных грузов",
        "27": "Безопасные методы и приемы работ с радиоактивными веществами и источниками ионизирующих излучений",
        "28": "Безопасные методы и приемы работ с ручным инструментом",
        "29": "Безопасные методы и приемы работ в театрах"
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Программы обучения")
        self.setMinimumSize(600, 500)

        layout = QVBoxLayout()

        # Список программ
        self.list_widget = QListWidget()
        for num, name in sorted(self.PROGRAMS.items(), key=lambda x: int(x[0])):
            item = QListWidgetItem(f"№{num}: {name}")
            item.setData(Qt.ItemDataRole.UserRole, num)
            self.list_widget.addItem(item)

        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)

        layout.addWidget(QLabel("Дважды кликните на программу для выбора:"))
        layout.addWidget(self.list_widget)

        # Кнопки
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def on_item_double_clicked(self, item: QListWidgetItem):
        program_num = item.data(Qt.ItemDataRole.UserRole)
        self.selected_program = f"{program_num},"
        self.accept()


class DataEntryTab(QWidget):
    """Вкладка внесения данных"""

    def __init__(self, data_manager: DataManager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        
        # Настройка HiDPI
        self.setStyleSheet("""
            QWidget {
                font-size: 14px;
            }
            QLabel {
                min-width: 150px;
            }
            QLineEdit, QComboBox {
                min-height: 30px;
                padding: 5px;
            }
            QPushButton {
                min-height: 35px;
                padding: 8px 16px;
                min-width: 120px;
            }
        """)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Раздел данных работника
        worker_group = QGroupBox("Данные работника")
        worker_layout = QFormLayout()
        worker_layout.setSpacing(10)

        self.last_name_edit = QLineEdit()
        self.first_name_edit = QLineEdit()
        self.middle_name_edit = QLineEdit()
        self.snils_edit = QLineEdit()
        self.position_edit = QLineEdit()

        # Номер программы с кнопкой справки
        program_layout = QHBoxLayout()
        self.program_edit = QLineEdit()
        self.program_help_btn = QPushButton("Справка")
        self.program_help_btn.clicked.connect(self.show_program_help)
        program_layout.addWidget(self.program_edit)
        program_layout.addWidget(self.program_help_btn)

        self.result_combo = QComboBox()
        self.result_combo.addItems(["Удовлетворительно", "Неудовлетворительно"])
        self.date_edit = QLineEdit()
        self.protocol_edit = QLineEdit()

        worker_layout.addRow("Фамилия:", self.last_name_edit)
        worker_layout.addRow("Имя:", self.first_name_edit)
        worker_layout.addRow("Отчество:", self.middle_name_edit)
        worker_layout.addRow("СНИЛС:", self.snils_edit)
        worker_layout.addRow("Должность:", self.position_edit)
        worker_layout.addRow("№ программы:", program_layout)
        worker_layout.addRow("Результат:", self.result_combo)
        worker_layout.addRow("Дата:", self.date_edit)
        worker_layout.addRow("№ протокола:", self.protocol_edit)

        worker_group.setLayout(worker_layout)
        main_layout.addWidget(worker_group)

        # Раздел данных УЦ и Заказчика
        org_group = QGroupBox("Данные Учебного центра и Заказчика")
        org_layout = QFormLayout()
        org_layout.setSpacing(10)

        self.tc_inn_edit = QLineEdit()
        self.tc_title_edit = QLineEdit()
        self.employer_inn_edit = QLineEdit()
        self.employer_title_edit = QLineEdit()

        org_layout.addRow("ИНН УЦ:", self.tc_inn_edit)
        org_layout.addRow("Название УЦ:", self.tc_title_edit)
        org_layout.addRow("ИНН Заказчика:", self.employer_inn_edit)
        org_layout.addRow("Название Заказчика:", self.employer_title_edit)

        org_group.setLayout(org_layout)
        main_layout.addWidget(org_group)

        # Кнопки управления
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)

        self.save_btn = QPushButton("Сохранить данные")
        self.save_btn.clicked.connect(self.save_data)

        self.clear_btn = QPushButton("Очистить")
        self.clear_btn.clicked.connect(self.clear_form)

        self.import_xlsx_btn = QPushButton("Загрузить XLSX")
        self.import_xlsx_btn.clicked.connect(self.import_xlsx)

        self.import_xml_btn = QPushButton("Загрузить XML")
        self.import_xml_btn.clicked.connect(self.import_xml)

        self.import_xsd_btn = QPushButton("Загрузить XSD")
        self.import_xsd_btn.clicked.connect(self.import_xsd)

        self.xsd_link_btn = QPushButton("Схема XSD")
        self.xsd_link_btn.clicked.connect(self.open_xsd_url)

        self.template_btn = QPushButton("Создать шаблон")
        self.template_btn.clicked.connect(self.create_template)

        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addWidget(self.import_xlsx_btn)
        btn_layout.addWidget(self.import_xml_btn)
        btn_layout.addWidget(self.import_xsd_btn)
        btn_layout.addWidget(self.xsd_link_btn)
        btn_layout.addWidget(self.template_btn)

        main_layout.addLayout(btn_layout)
        main_layout.addStretch()

        self.setLayout(main_layout)
        
        # Загрузка сохраненных данных УЦ/Заказчика из JSON файла
        self.load_organization_data()

    def show_program_help(self):
        dialog = ProgramListDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            current = self.program_edit.text()
            self.program_edit.setText(current + dialog.selected_program)

    def validate_and_save(self) -> tuple[bool, str]:
        """Валидация данных формы"""
        # Проверка обязательных полей
        if not all([self.last_name_edit.text().strip(),
                   self.first_name_edit.text().strip(),
                   self.snils_edit.text().strip(),
                   self.position_edit.text().strip(),
                   self.program_edit.text().strip(),
                   self.date_edit.text().strip(),
                   self.protocol_edit.text().strip()]):
            return False, "Заполните все строки"

        # Валидация текста
        for field_name, edit in [("Фамилия", self.last_name_edit),
                                 ("Имя", self.first_name_edit),
                                 ("Отчество", self.middle_name_edit),
                                 ("Должность", self.position_edit)]:
            text = edit.text().strip()
            if text and not text.replace(' ', '').isalpha():
                return False, f"{field_name} - только текст"

        # Валидация СНИЛС
        snils = self.snils_edit.text().strip()
        if not self.data_manager.validate_snils(snils):
            return False, "СНИЛС должен содержать 11 цифр"

        # Валидация программ
        valid, msg = self.data_manager.validate_programs(self.program_edit.text())
        if not valid:
            return False, msg

        # Валидация даты
        valid, msg = self.data_manager.validate_date(self.date_edit.text().strip())
        if not valid:
            return False, msg

        # Данные организации
        if not all([self.tc_inn_edit.text().strip(),
                   self.tc_title_edit.text().strip(),
                   self.employer_inn_edit.text().strip(),
                   self.employer_title_edit.text().strip()]):
            return False, "Заполните данные УЦ/Работодателя"

        # Валидация ИНН
        for inn_field, name in [(self.tc_inn_edit, "ИНН УЦ"),
                               (self.employer_inn_edit, "ИНН Заказчика")]:
            if not self.data_manager.validate_inn(inn_field.text().strip()):
                return False, f"{name} - только 10 или 12 цифр"

        return True, "OK"

    def save_data(self):
        valid, msg = self.validate_and_save()
        if not valid:
            QMessageBox.warning(self, "Ошибка", msg)
            return

        record = WorkerRecord(
            last_name=self.last_name_edit.text().strip(),
            first_name=self.first_name_edit.text().strip(),
            middle_name=self.middle_name_edit.text().strip(),
            snils=self.snils_edit.text().strip(),
            position=self.position_edit.text().strip(),
            program_numbers=self.program_edit.text().strip().rstrip(','),
            result=self.result_combo.currentText(),
            date=self.date_edit.text().strip(),
            protocol_number=self.protocol_edit.text().strip(),
            training_center_inn=self.tc_inn_edit.text().strip(),
            training_center_title=self.tc_title_edit.text().strip(),
            employer_inn=self.employer_inn_edit.text().strip(),
            employer_title=self.employer_title_edit.text().strip()
        )

        success, result_msg = self.data_manager.add_record(record)
        if success:
            QMessageBox.information(self, "Успех", "Запись сохранена")
            # Сохраняем данные УЦ/Заказчика для будущих сессий
            self.save_organization_data()
            # Очищаем поля кроме программ
            self.clear_form(clear_programs=False)
            # Сигнал об обновлении данных
            if hasattr(self.parent(), 'on_data_updated'):
                self.parent().on_data_updated()
        else:
            QMessageBox.warning(self, "Ошибка", result_msg)

    
    def clear_form(self, clear_programs=True):
        self.last_name_edit.clear()
        self.first_name_edit.clear()
        self.middle_name_edit.clear()
        self.snils_edit.clear()
        self.position_edit.clear()
        if clear_programs:
            self.program_edit.clear()
        self.date_edit.clear()
        self.protocol_edit.clear()

    def load_organization_data(self):
        """Загрузка сохраненных данных об УЦ и Заказчике из JSON файла"""
        try:
            if os.path.exists(ORG_SETTINGS_FILE):
                with open(ORG_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.tc_inn_edit.setText(data.get("tc_inn", ""))
                self.tc_title_edit.setText(data.get("tc_title", ""))
                self.employer_inn_edit.setText(data.get("employer_inn", ""))
                self.employer_title_edit.setText(data.get("employer_title", ""))
            else:
                # Файл не существует - создаем с пустыми значениями
                self._save_organization_data_to_file({})
        except (json.JSONDecodeError, IOError) as e:
            QMessageBox.warning(
                self, 
                "Ошибка", 
                f"Ошибка чтения файла настроек: {str(e)}\nБудут использованы пустые значения."
            )
            self.tc_inn_edit.clear()
            self.tc_title_edit.clear()
            self.employer_inn_edit.clear()
            self.employer_title_edit.clear()

    def save_organization_data(self):
        """Сохранение данных об УЦ и Заказчике в JSON файл"""
        data = {
            "tc_inn": self.tc_inn_edit.text().strip(),
            "tc_title": self.tc_title_edit.text().strip(),
            "employer_inn": self.employer_inn_edit.text().strip(),
            "employer_title": self.employer_title_edit.text().strip()
        }
        
        if self._save_organization_data_to_file(data):
            pass  # Успешно сохранено
        else:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Не удалось сохранить данные организации в файл.\nПроверьте права доступа к папке /data/"
            )

    def _save_organization_data_to_file(self, data: dict) -> bool:
        """Внутренний метод сохранения данных в JSON файл
        
        Args:
            data: Словарь с данными организации
            
        Returns:
            True если успешно, False иначе
        """
        try:
            # Создаем директорию data если не существует
            data_dir = os.path.dirname(ORG_SETTINGS_FILE)
            os.makedirs(data_dir, exist_ok=True)
            
            with open(ORG_SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return True
        except IOError as e:
            print(f"Ошибка записи файла настроек: {e}")
            return False

    def import_xlsx(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите XLSX файл", "", "Excel files (*.xlsx *.xls)"
        )
        if file_path:
            # TODO: Реализовать импорт XLSX
            QMessageBox.information(self, "Информация", "Импорт XLSX будет реализован")

    def import_xml(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите XML файл", "", "XML files (*.xml)"
        )
        if file_path:
            # TODO: Реализовать импорт XML
            QMessageBox.information(self, "Информация", "Импорт XML будет реализован")

    def import_xsd(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите XSD файл", "", "XSD files (*.xsd)"
        )
        if file_path:
            self.data_manager.xsd_path = file_path
            # Копируем в директорию schema
            import shutil
            schema_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'schema')
            os.makedirs(schema_dir, exist_ok=True)
            dest_path = os.path.join(schema_dir, 'schema.xsd')
            shutil.copy(file_path, dest_path)
            QMessageBox.information(self, "Успех", "XSD схема загружена и сохранена")

    def open_xsd_url(self):
        import webbrowser
        webbrowser.open("https://akot.rosmintrud.ru/sout/info")

    def create_template(self):
        from utils.excel_handler import ExcelHandler
        handler = ExcelHandler()
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'Шаблон.xlsx'
        )
        handler.create_template(template_path)

        reply = QMessageBox.question(
            self, "Шаблон создан",
            "Шаблон создан. Открыть расположение файла?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            import subprocess
            subprocess.run(['xdg-open', os.path.dirname(template_path)])


class DataViewTab(QWidget):
    """Вкладка просмотра данных"""

    def __init__(self, data_manager: DataManager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager

        self.setStyleSheet("""
            QWidget {
                font-size: 14px;
            }
            QTableWidget {
                gridline-color: #cccccc;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QPushButton {
                min-height: 35px;
                padding: 8px 16px;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Таблица данных
        self.table = QTableWidget()
        self.table.setColumnCount(13)
        self.table.setHorizontalHeaderLabels([
            'Фамилия', 'Имя', 'Отчество', 'СНИЛС', 'Должность',
            'ИНН Заказчика', 'Наименование ЮЛ Заказчика', 'ИНН УЦ',
            'Наименование УЦ', 'Результат', '№ программы', 'Дата', '№ протокола'
        ])

        # Настройка заголовков
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setStretchLastSection(True)

        layout.addWidget(self.table)

        # Кнопки управления
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)

        self.edit_btn = QPushButton("Редактировать")
        self.edit_btn.clicked.connect(self.edit_record)

        self.delete_btn = QPushButton("Удалить")
        self.delete_btn.clicked.connect(self.delete_record)

        self.clear_btn = QPushButton("Очистить все")
        self.clear_btn.clicked.connect(self.clear_all)

        self.convert_btn = QPushButton("Конвертация в XML")
        self.convert_btn.clicked.connect(self.convert_to_xml)

        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addWidget(self.convert_btn)

        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def refresh_table(self):
        """Обновление таблицы"""
        self.table.setRowCount(0)
        for record in self.data_manager.records:
            row = self.table.rowCount()
            self.table.insertRow(row)
            d = record.to_dict()
            for col, key in enumerate([
                'Фамилия', 'Имя', 'Отчество', 'СНИЛС', 'Должность',
                'ИНН Заказчика', 'Наименование ЮЛ Заказчика', 'ИНН УЦ',
                'Наименование УЦ', 'Результат', '№ программы', 'Дата', '№ протокола'
            ]):
                self.table.setItem(row, col, QTableWidgetItem(d.get(key, '')))

    def get_selected_record(self) -> Optional[WorkerRecord]:
        """Получение выбранной записи"""
        row = self.table.currentRow()
        if row < 0:
            return None

        data = {}
        for col, key in enumerate([
            'Фамилия', 'Имя', 'Отчество', 'СНИЛС', 'Должность',
            'ИНН Заказчика', 'Наименование ЮЛ Заказчика', 'ИНН УЦ',
            'Наименование УЦ', 'Результат', '№ программы', 'Дата', '№ протокола'
        ]):
            item = self.table.item(row, col)
            data[key] = item.text() if item else ''

        return WorkerRecord.from_dict(data)

    def edit_record(self):
        record = self.get_selected_record()
        if not record:
            QMessageBox.warning(self, "Ошибка", "Выберите запись для редактирования")
            return

        # TODO: Реализовать диалог редактирования
        QMessageBox.information(self, "Информация", "Редактирование будет реализовано")

    def delete_record(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите запись для удаления")
            return

        reply = QMessageBox.question(
            self, "Подтверждение",
            "Вы уверены, что хотите удалить?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            del self.data_manager.records[row]
            self.refresh_table()

    def clear_all(self):
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Очистить все данные? Данные удалятся безвозвратно.",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
        )

        if reply == QMessageBox.StandardButton.Ok:
            self.data_manager.clear_all()
            self.refresh_table()

    def convert_to_xml(self):
        if not self.data_manager.records:
            QMessageBox.warning(self, "Ошибка", "Нет данных для конвертации")
            return

        from utils.xml_converter import XMLConverter
        converter = XMLConverter(self.data_manager)

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить XML файл", "", "XML files (*.xml)"
        )

        if file_path:
            success, message = converter.convert(file_path)
            if success:
                QMessageBox.information(self, "Успех", f"XML файл создан:\n{file_path}")
            else:
                QMessageBox.critical(self, "Ошибка", message)


class SendDataTab(QWidget):
    """Вкладка отправки данных"""

    def __init__(self, data_manager: DataManager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager

        self.setStyleSheet("""
            QWidget {
                font-size: 14px;
            }
            QLineEdit {
                min-height: 30px;
                padding: 5px;
            }
            QPushButton {
                min-height: 35px;
                padding: 8px 16px;
                min-width: 150px;
            }
            QGroupBox {
                margin-top: 15px;
                padding-top: 15px;
                font-weight: bold;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # Раздел API ключа
        api_group = QGroupBox("API ключ")
        api_layout = QHBoxLayout()

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setPlaceholderText("Введите 32-символьный API ключ")
        self.api_key_edit.setMaxLength(32)

        self.save_api_btn = QPushButton("Сохранить ключ")
        self.save_api_btn.clicked.connect(self.save_api_key)

        api_layout.addWidget(QLabel("API ключ:"))
        api_layout.addWidget(self.api_key_edit)
        api_layout.addWidget(self.save_api_btn)

        api_group.setLayout(api_layout)
        layout.addWidget(api_group)

        # Раздел отправки XML
        send_group = QGroupBox("Отправка XML")
        send_layout = QVBoxLayout()

        self.xml_file_edit = QLineEdit()
        self.xml_file_edit.setReadOnly(True)
        self.xml_file_edit.setPlaceholderText("Выберите XML файл для отправки")

        browse_layout = QHBoxLayout()
        browse_layout.addWidget(self.xml_file_edit)

        self.browse_btn = QPushButton("Обзор")
        self.browse_btn.clicked.connect(self.browse_xml_file)
        browse_layout.addWidget(self.browse_btn)

        self.send_btn = QPushButton("Отправить XML на сервер")
        self.send_btn.clicked.connect(self.send_xml)

        send_layout.addLayout(browse_layout)
        send_layout.addWidget(self.send_btn)

        send_group.setLayout(send_layout)
        layout.addWidget(send_group)

        # Раздел запроса номеров
        request_group = QGroupBox("Запрос номеров")
        request_layout = QHBoxLayout()

        self.setid_edit = QLineEdit()
        self.setid_edit.setPlaceholderText("Введите номер набора (Setid)")

        self.request_btn = QPushButton("Запросить номера")
        self.request_btn.clicked.connect(self.request_numbers)

        request_layout.addWidget(QLabel("SetId:"))
        request_layout.addWidget(self.setid_edit)
        request_layout.addWidget(self.request_btn)

        request_group.setLayout(request_layout)
        layout.addWidget(request_group)

        layout.addStretch()
        self.setLayout(layout)

    def save_api_key(self):
        api_key = self.api_key_edit.text().strip()
        if len(api_key) != 32:
            QMessageBox.warning(self, "Ошибка", "API ключ должен содержать 32 символа")
            return

        self.data_manager.api_key = api_key

        # Сохранение в файл
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'data', 'config.json'
        )
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

        import json
        # В реальном приложении нужно шифрование
        with open(config_path, 'w') as f:
            json.dump({'api_key': api_key}, f)

        QMessageBox.information(self, "Успех", "API ключ сохранен")

    def browse_xml_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите XML файл", "", "XML files (*.xml)"
        )
        if file_path:
            self.xml_file_edit.setText(file_path)

    def send_xml(self):
        xml_file = self.xml_file_edit.text().strip()
        if not xml_file:
            QMessageBox.warning(self, "Ошибка", "Выберите XML файл")
            return

        if not self.data_manager.api_key:
            QMessageBox.warning(self, "Ошибка", "Введите API ключ")
            return

        from utils.mintrud_api import MinTrudAPI
        api = MinTrudAPI(self.data_manager.api_key)

        success, result = api.send_xml(xml_file)

        if success:
            QMessageBox.information(
                self, "Успех",
                f"Данные загружены на сервер\n\nЗапишите номер набора: {result}"
            )
        else:
            QMessageBox.critical(self, "Ошибка", result)

    def request_numbers(self):
        setid = self.setid_edit.text().strip()
        if not setid:
            QMessageBox.warning(self, "Ошибка", "Введите SetId")
            return

        if not self.data_manager.api_key:
            QMessageBox.warning(self, "Ошибка", "Введите API ключ")
            return

        from utils.mintrud_api import MinTrudAPI
        api = MinTrudAPI(self.data_manager.api_key)

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить отчет", "", "Excel files (*.xlsx)"
        )

        if file_path:
            success, result = api.request_by_setid(setid, file_path)
            if success:
                QMessageBox.information(self, "Успех", f"Отчет сохранен:\n{file_path}")
            else:
                QMessageBox.critical(self, "Ошибка", result)


class MainWindow(QMainWindow):
    """Главное окно приложения"""

    def __init__(self):
        super().__init__()

        self.data_manager = DataManager()

        self.setWindowTitle("Система Excel-XML для Минтруда")
        self.setMinimumSize(1200, 800)

        # Настройка HiDPI
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                border-radius: 5px;
            }
            QTabBar::tab {
                background-color: #e0e0e0;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
            }
            QTabBar::tab:hover {
                background-color: #f0f0f0;
            }
        """)

        # Центральная виджет с вкладками
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        central_widget.setLayout(main_layout)

        # Вкладки
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(False)
        self.tabs.setMovable(False)

        self.data_entry_tab = DataEntryTab(self.data_manager, self)
        self.data_view_tab = DataViewTab(self.data_manager, self)
        self.send_data_tab = SendDataTab(self.data_manager, self)

        self.tabs.addTab(self.data_entry_tab, "Внесение данных")
        self.tabs.addTab(self.data_view_tab, "Просмотр данных")
        self.tabs.addTab(self.send_data_tab, "Отправка данных")

        main_layout.addWidget(self.tabs)

        # Статус бар
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Готов к работе")

        # Меню
        self.create_menu()

    def create_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("Файл")

        exit_action = QAction("Выход", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = menubar.addMenu("Справка")

        about_action = QAction("О программе", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def show_about(self):
        QMessageBox.about(
            self, "О программе",
            "Система Excel-XML для передачи данных в Минтруд\n\n"
            "Версия 1.0\n\n"
            "Разработано для автоматизации внесения информации о работниках "
            "в базу данных Минтруда."
        )

    def on_data_updated(self):
        """Обновление данных во вкладке просмотра"""
        self.data_view_tab.refresh_table()

"""
Основное окно приложения с вкладками
"""

from PyQt6.QtWidgets import (QMainWindow, QTabWidget, QWidget, QVBoxLayout,QHBoxLayout, QLabel, QLineEdit, QPushButton,
QTextEdit, QFileDialog, QMessageBox, QDialog,
QDialogButtonBox, QListWidget, QListWidgetItem,
QTableWidget, QTableWidgetItem, QHeaderView,
QComboBox, QGroupBox, QFormLayout, QSplitter,
QToolBar, QStatusBar, QMenu, QMenuBar,
QScrollArea, QFrame)
from PyQt6.QtGui import QFont, QIcon, QAction
from PyQt6.QtCore import Qt, QCoreApplication

from typing import Optional
import sys
import os

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data_model import DataManager, WorkerRecord


class ProgramListDialog(QDialog):
    """Диалог выбора программ обучения"""

    PROGRAMS = {
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
        "17": "Безопасные методы и приемы выполнения работ, связанные с эксплуатацией тепловых энергоустановок",
        "18": "Безопасные методы и приемы выполнения работ в электроустановках",
        "19": "Безопасные методы и приемы выполнения работ, связанные с эксплуатацией сосудов, работающих под избыточным давлением",
        "20": "Безопасные методы и приемы обращения с животными",
        "21": "Безопасные методы и приемы при выполнении водолазных работ",
        "22": "Безопасные методы и приемы работ по поиску, идентификации, обезвреживанию и уничтожению взрывоопасных предметов",
        "23": "Безопасные методы и приемы работ в непосредственной близости от полотна или проезжей части эксплуатируемых автомобильных и железных дорог",
        "24": "Безопасные методы и приемы работ на участках с патогенным заражением почвы",
        "25": "Безопасные методы и приемы работ по валке леса в особо опасных условиях",
        "26": "Безопасные методы и приемы работ по перемещению тяжеловесных и крупногабаритных грузов",
        "27": "Безопасные методы и приемы работ с радиоактивными веществами и источниками ионизирующих излучений",
        "28": "Безопасные методы и приемы работ с ручным инструментом",
        "29": "Безопасные методы и приемы работ в театрах"
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Программы обучения")
        self.setMinimumSize(600, 500)

        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
            QLabel {
                color: #000000;
                font-size: 14px;
            }
            QListWidget {
                color: #000000;
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 3px;
                padding: 5px;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #000000;
                color: #ffffff;
            }
            QListWidget::item:hover {
                background-color: #e0e0e0;
            }
            QPushButton {
                color: #000000;
                background-color: #e0e0e0;
                border: 1px solid #cccccc;
                border-radius: 3px;
                padding: 8px 16px;
                min-height: 35px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
        """)

        layout = QVBoxLayout()

        # Список программ
        self.list_widget = QListWidget()
        for num, name in sorted(self.PROGRAMS.items(), key=lambda x: int(x[0])):
            item = QListWidgetItem(f"№{num}: {name}")
            item.setData(Qt.ItemDataRole.UserRole, num)
            self.list_widget.addItem(item)

        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)

        layout.addWidget(QLabel("Дважды кликните на программу для выбора:"))
        layout.addWidget(self.list_widget)

        # Кнопки
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def on_item_double_clicked(self, item: QListWidgetItem):
        program_num = item.data(Qt.ItemDataRole.UserRole)
        self.selected_program = f"{program_num},"
        self.accept()


class DataEntryTab(QWidget):
    """Вкладка внесения данных"""

    def __init__(self, data_manager: DataManager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager

        # Настройка HiDPI
        self.setStyleSheet("""
            QWidget {
                font-size: 14px;
                color: #000000;
                background-color: #ffffff;
            }
            QLabel {
                min-width: 150px;
                color: #000000;
            }
            QLineEdit, QComboBox {
                min-height: 30px;
                padding: 5px;
                color: #000000;
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 3px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #0066cc;
            }
            QComboBox::drop-down {
                width: 25px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #000000;
                margin-right: 8px;
            }
            QPushButton {
                min-height: 35px;
                padding: 8px 16px;
                min-width: 120px;
                color: #000000;
                background-color: #e0e0e0;
                border: 1px solid #cccccc;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
            QPushButton:pressed {
                background-color: #c0c0c0;
            }
            QGroupBox {
                font-weight: bold;
                color: #000000;
                border: 1px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Scroll area for form fields
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_content = QWidget()
        scroll_widget_layout = QVBoxLayout()
        scroll_widget_layout.setSpacing(15)
        scroll_widget_layout.setContentsMargins(0, 0, 0, 0)

        # Раздел данных работника
        worker_group = QGroupBox("Данные работника")
        worker_layout = QFormLayout()
        worker_layout.setSpacing(12)
        worker_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        worker_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        worker_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.last_name_edit = QLineEdit()
        self.first_name_edit = QLineEdit()
        self.middle_name_edit = QLineEdit()
        self.snils_edit = QLineEdit()
        self.position_edit = QLineEdit()

        # Set minimum width for input fields
        min_field_width = 300
        self.last_name_edit.setMinimumWidth(min_field_width)
        self.first_name_edit.setMinimumWidth(min_field_width)
        self.middle_name_edit.setMinimumWidth(min_field_width)
        self.snils_edit.setMinimumWidth(min_field_width)
        self.position_edit.setMinimumWidth(min_field_width)

        # Номер программы с кнопкой справки
        program_layout = QHBoxLayout()
        self.program_edit = QLineEdit()
        self.program_edit.setMinimumWidth(min_field_width)
        self.program_help_btn = QPushButton("Справка")
        self.program_help_btn.clicked.connect(self.show_program_help)
        program_layout.addWidget(self.program_edit)
        program_layout.addWidget(self.program_help_btn)

        self.result_combo = QComboBox()
        self.result_combo.setMinimumWidth(min_field_width)
        self.result_combo.addItems(["Удовлетворительно", "Неудовлетворительно"])
        self.date_edit = QLineEdit()
        self.date_edit.setMinimumWidth(min_field_width)
        self.protocol_edit = QLineEdit()
        self.protocol_edit.setMinimumWidth(min_field_width)

        worker_layout.addRow("Фамилия:", self.last_name_edit)
        worker_layout.addRow("Имя:", self.first_name_edit)
        worker_layout.addRow("Отчество:", self.middle_name_edit)
        worker_layout.addRow("СНИЛС:", self.snils_edit)
        worker_layout.addRow("Должность:", self.position_edit)
        worker_layout.addRow("№ программы:", program_layout)
        worker_layout.addRow("Результат:", self.result_combo)
        worker_layout.addRow("Дата:", self.date_edit)
        worker_layout.addRow("№ протокола:", self.protocol_edit)

        worker_group.setLayout(worker_layout)
        scroll_widget_layout.addWidget(worker_group)

        # Раздел данных УЦ и Заказчика
        org_group = QGroupBox("Данные Учебного центра и Заказчика")
        org_layout = QFormLayout()
        org_layout.setSpacing(12)
        org_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        org_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        org_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.tc_inn_edit = QLineEdit()
        self.tc_inn_edit.setMinimumWidth(min_field_width)
        self.tc_title_edit = QLineEdit()
        self.tc_title_edit.setMinimumWidth(min_field_width)
        self.employer_inn_edit = QLineEdit()
        self.employer_inn_edit.setMinimumWidth(min_field_width)
        self.employer_title_edit = QLineEdit()
        self.employer_title_edit.setMinimumWidth(min_field_width)

        org_layout.addRow("ИНН УЦ:", self.tc_inn_edit)
        org_layout.addRow("Название УЦ:", self.tc_title_edit)
        org_layout.addRow("ИНН Заказчика:", self.employer_inn_edit)
        org_layout.addRow("Название Заказчика:", self.employer_title_edit)

        org_group.setLayout(org_layout)
        scroll_widget_layout.addWidget(org_group)
        scroll_widget_layout.addStretch()

        scroll_content.setLayout(scroll_widget_layout)
        scroll.setWidget(scroll_content)

        main_layout.addWidget(scroll)

        # Кнопки управления - выравнивание по низу
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        btn_layout.setContentsMargins(0, 10, 0, 0)

        self.save_btn = QPushButton("Сохранить данные")
        self.save_btn.clicked.connect(self.save_data)

        self.clear_btn = QPushButton("Очистить")
        self.clear_btn.clicked.connect(self.clear_form)

        self.import_xlsx_btn = QPushButton("Загрузить XLSX")
        self.import_xlsx_btn.clicked.connect(self.import_xlsx)

        self.import_xml_btn = QPushButton("Загрузить XML")
        self.import_xml_btn.clicked.connect(self.import_xml)

        self.import_xsd_btn = QPushButton("Загрузить XSD")
        self.import_xsd_btn.clicked.connect(self.import_xsd)

        self.xsd_link_btn = QPushButton("Схема XSD")
        self.xsd_link_btn.clicked.connect(self.open_xsd_url)

        self.template_btn = QPushButton("Создать шаблон")
        self.template_btn.clicked.connect(self.create_template)

        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addWidget(self.import_xlsx_btn)
        btn_layout.addWidget(self.import_xml_btn)
        btn_layout.addWidget(self.import_xsd_btn)
        btn_layout.addWidget(self.xsd_link_btn)
        btn_layout.addWidget(self.template_btn)
        btn_layout.addStretch()

        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)
        
        # Загрузка сохраненных данных УЦ/Заказчика из JSON файла
        self.load_organization_data()

    def show_program_help(self):
        dialog = ProgramListDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            current = self.program_edit.text()
            self.program_edit.setText(current + dialog.selected_program)

    def validate_and_save(self) -> tuple[bool, str]:
        """Валидация данных формы"""
        # Проверка обязательных полей
        if not all([self.last_name_edit.text().strip(),
                   self.first_name_edit.text().strip(),
                   self.snils_edit.text().strip(),
                   self.position_edit.text().strip(),
                   self.program_edit.text().strip(),
                   self.date_edit.text().strip(),
                   self.protocol_edit.text().strip()]):
            return False, "Заполните все строки"

        # Валидация текста
        for field_name, edit in [("Фамилия", self.last_name_edit),
                                 ("Имя", self.first_name_edit),
                                 ("Отчество", self.middle_name_edit),
                                 ("Должность", self.position_edit)]:
            text = edit.text().strip()
            if text and not text.replace(' ', '').isalpha():
                return False, f"{field_name} - только текст"

        # Валидация СНИЛС
        snils = self.snils_edit.text().strip()
        if not self.data_manager.validate_snils(snils):
            return False, "СНИЛС должен содержать 11 цифр"

        # Валидация программ
        valid, msg = self.data_manager.validate_programs(self.program_edit.text())
        if not valid:
            return False, msg

        # Валидация даты
        valid, msg = self.data_manager.validate_date(self.date_edit.text().strip())
        if not valid:
            return False, msg

        # Данные организации
        if not all([self.tc_inn_edit.text().strip(),
                   self.tc_title_edit.text().strip(),
                   self.employer_inn_edit.text().strip(),
                   self.employer_title_edit.text().strip()]):
            return False, "Заполните данные УЦ/Работодателя"

        # Валидация ИНН
        for inn_field, name in [(self.tc_inn_edit, "ИНН УЦ"),
                               (self.employer_inn_edit, "ИНН Заказчика")]:
            if not self.data_manager.validate_inn(inn_field.text().strip()):
                return False, f"{name} - только 10 или 12 цифр"

        return True, "OK"

    def save_data(self):
        valid, msg = self.validate_and_save()
        if not valid:
            QMessageBox.warning(self, "Ошибка", msg)
            return

        record = WorkerRecord(
            last_name=self.last_name_edit.text().strip(),
            first_name=self.first_name_edit.text().strip(),
            middle_name=self.middle_name_edit.text().strip(),
            snils=self.snils_edit.text().strip(),
            position=self.position_edit.text().strip(),
            program_numbers=self.program_edit.text().strip().rstrip(','),
            result=self.result_combo.currentText(),
            date=self.date_edit.text().strip(),
            protocol_number=self.protocol_edit.text().strip(),
            training_center_inn=self.tc_inn_edit.text().strip(),
            training_center_title=self.tc_title_edit.text().strip(),
            employer_inn=self.employer_inn_edit.text().strip(),
            employer_title=self.employer_title_edit.text().strip()
        )

        success, result_msg = self.data_manager.add_record(record)
        if success:
            QMessageBox.information(self, "Успех", "Запись сохранена")
            # Очищаем поля кроме программ
            self.clear_form(clear_programs=False)
            # Сигнал об обновлении данных
            if hasattr(self.parent(), 'on_data_updated'):
                self.parent().on_data_updated()
        else:
            QMessageBox.warning(self, "Ошибка", result_msg)

    def clear_form(self, clear_programs=True):
        self.last_name_edit.clear()
        self.first_name_edit.clear()
        self.middle_name_edit.clear()
        self.snils_edit.clear()
        self.position_edit.clear()
        if clear_programs:
            self.program_edit.clear()
        self.date_edit.clear()
        self.protocol_edit.clear()

    def import_xlsx(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите XLSX файл", "", "Excel files (*.xlsx *.xls)"
        )
        if file_path:
            # TODO: Реализовать импорт XLSX
            QMessageBox.information(self, "Информация", "Импорт XLSX будет реализован")

    def import_xml(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите XML файл", "", "XML files (*.xml)"
        )
        if file_path:
            # TODO: Реализовать импорт XML
            QMessageBox.information(self, "Информация", "Импорт XML будет реализован")

    def import_xsd(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите XSD файл", "", "XSD files (*.xsd)"
        )
        if file_path:
            self.data_manager.xsd_path = file_path
            # Копируем в директорию schema
            import shutil
            schema_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'schema')
            os.makedirs(schema_dir, exist_ok=True)
            dest_path = os.path.join(schema_dir, 'schema.xsd')
            shutil.copy(file_path, dest_path)
            QMessageBox.information(self, "Успех", "XSD схема загружена и сохранена")

    def open_xsd_url(self):
        import webbrowser
        webbrowser.open("https://akot.rosmintrud.ru/sout/info")

    def create_template(self):
        from utils.excel_handler import ExcelHandler
        handler = ExcelHandler()
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'Шаблон.xlsx'
        )
        handler.create_template(template_path)

        reply = QMessageBox.question(
            self, "Шаблон создан",
            "Шаблон создан. Открыть расположение файла?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            import subprocess
            subprocess.run(['xdg-open', os.path.dirname(template_path)])


class DataViewTab(QWidget):
    """Вкладка просмотра данных"""

    def __init__(self, data_manager: DataManager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager

        self.setStyleSheet("""
            QWidget {
                font-size: 14px;
                color: #000000;
                background-color: #ffffff;
            }
            QTableWidget {
                gridline-color: #cccccc;
                color: #000000;
                background-color: #ffffff;
                border: 1px solid #cccccc;
            }
            QTableWidget::item {
                padding: 5px;
                color: #000000;
                background-color: #ffffff;
            }
            QTableWidget::item:selected {
                background-color: #0066cc;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #e0e0e0;
                color: #000000;
                padding: 5px;
                border: 1px solid #cccccc;
                font-weight: bold;
            }
            QPushButton {
                min-height: 35px;
                padding: 8px 16px;
                color: #000000;
                background-color: #e0e0e0;
                border: 1px solid #cccccc;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
            QPushButton:pressed {
                background-color: #c0c0c0;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Таблица данных
        self.table = QTableWidget()
        self.table.setColumnCount(13)
        self.table.setHorizontalHeaderLabels([
            'Фамилия', 'Имя', 'Отчество', 'СНИЛС', 'Должность',
            'ИНН Заказчика', 'Наименование ЮЛ Заказчика', 'ИНН УЦ',
            'Наименование УЦ', 'Результат', '№ программы', 'Дата', '№ протокола'
        ])

        # Настройка заголовков
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setStretchLastSection(True)

        layout.addWidget(self.table)

        # Кнопки управления
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)

        self.edit_btn = QPushButton("Редактировать")
        self.edit_btn.clicked.connect(self.edit_record)

        self.delete_btn = QPushButton("Удалить")
        self.delete_btn.clicked.connect(self.delete_record)

        self.clear_btn = QPushButton("Очистить все")
        self.clear_btn.clicked.connect(self.clear_all)

        self.convert_btn = QPushButton("Конвертация в XML")
        self.convert_btn.clicked.connect(self.convert_to_xml)

        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addWidget(self.convert_btn)

        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def refresh_table(self):
        """Обновление таблицы"""
        self.table.setRowCount(0)
        for record in self.data_manager.records:
            row = self.table.rowCount()
            self.table.insertRow(row)
            d = record.to_dict()
            for col, key in enumerate([
                'Фамилия', 'Имя', 'Отчество', 'СНИЛС', 'Должность',
                'ИНН Заказчика', 'Наименование ЮЛ Заказчика', 'ИНН УЦ',
                'Наименование УЦ', 'Результат', '№ программы', 'Дата', '№ протокола'
            ]):
                self.table.setItem(row, col, QTableWidgetItem(d.get(key, '')))

    def get_selected_record(self) -> Optional[WorkerRecord]:
        """Получение выбранной записи"""
        row = self.table.currentRow()
        if row < 0:
            return None

        data = {}
        for col, key in enumerate([
            'Фамилия', 'Имя', 'Отчество', 'СНИЛС', 'Должность',
            'ИНН Заказчика', 'Наименование ЮЛ Заказчика', 'ИНН УЦ',
            'Наименование УЦ', 'Результат', '№ программы', 'Дата', '№ протокола'
        ]):
            item = self.table.item(row, col)
            data[key] = item.text() if item else ''

        return WorkerRecord.from_dict(data)

    def edit_record(self):
        record = self.get_selected_record()
        if not record:
            QMessageBox.warning(self, "Ошибка", "Выберите запись для редактирования")
            return

        # TODO: Реализовать диалог редактирования
        QMessageBox.information(self, "Информация", "Редактирование будет реализовано")

    def delete_record(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите запись для удаления")
            return

        reply = QMessageBox.question(
            self, "Подтверждение",
            "Вы уверены, что хотите удалить?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            del self.data_manager.records[row]
            self.refresh_table()

    def clear_all(self):
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Очистить все данные? Данные удалятся безвозвратно.",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
        )

        if reply == QMessageBox.StandardButton.Ok:
            self.data_manager.clear_all()
            self.refresh_table()

    def convert_to_xml(self):
        if not self.data_manager.records:
            QMessageBox.warning(self, "Ошибка", "Нет данных для конвертации")
            return

        from utils.xml_converter import XMLConverter
        converter = XMLConverter(self.data_manager)

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить XML файл", "", "XML files (*.xml)"
        )

        if file_path:
            success, message = converter.convert(file_path)
            if success:
                QMessageBox.information(self, "Успех", f"XML файл создан:\n{file_path}")
            else:
                QMessageBox.critical(self, "Ошибка", message)


class SendDataTab(QWidget):
    """Вкладка отправки данных"""

    def __init__(self, data_manager: DataManager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager

        self.setStyleSheet("""
            QWidget {
                font-size: 14px;
                color: #000000;
                background-color: #ffffff;
            }
            QLineEdit {
                min-height: 30px;
                padding: 5px;
                color: #000000;
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 3px;
            }
            QLineEdit:focus {
                border: 1px solid #0066cc;
            }
            QPushButton {
                min-height: 35px;
                padding: 8px 16px;
                min-width: 150px;
                color: #000000;
                background-color: #e0e0e0;
                border: 1px solid #cccccc;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
            QPushButton:pressed {
                background-color: #c0c0c0;
            }
            QGroupBox {
                margin-top: 15px;
                padding-top: 15px;
                font-weight: bold;
                color: #000000;
                border: 1px solid #cccccc;
                border-radius: 5px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # Раздел API ключа
        api_group = QGroupBox("API ключ")
        api_layout = QHBoxLayout()

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setPlaceholderText("Введите 32-символьный API ключ")
        self.api_key_edit.setMaxLength(32)

        self.save_api_btn = QPushButton("Сохранить ключ")
        self.save_api_btn.clicked.connect(self.save_api_key)

        api_layout.addWidget(QLabel("API ключ:"))
        api_layout.addWidget(self.api_key_edit)
        api_layout.addWidget(self.save_api_btn)

        api_group.setLayout(api_layout)
        layout.addWidget(api_group)

        # Раздел отправки XML
        send_group = QGroupBox("Отправка XML")
        send_layout = QVBoxLayout()

        self.xml_file_edit = QLineEdit()
        self.xml_file_edit.setReadOnly(True)
        self.xml_file_edit.setPlaceholderText("Выберите XML файл для отправки")

        browse_layout = QHBoxLayout()
        browse_layout.addWidget(self.xml_file_edit)

        self.browse_btn = QPushButton("Обзор")
        self.browse_btn.clicked.connect(self.browse_xml_file)
        browse_layout.addWidget(self.browse_btn)

        self.send_btn = QPushButton("Отправить XML на сервер")
        self.send_btn.clicked.connect(self.send_xml)

        send_layout.addLayout(browse_layout)
        send_layout.addWidget(self.send_btn)

        send_group.setLayout(send_layout)
        layout.addWidget(send_group)

        # Раздел запроса номеров
        request_group = QGroupBox("Запрос номеров")
        request_layout = QHBoxLayout()

        self.setid_edit = QLineEdit()
        self.setid_edit.setPlaceholderText("Введите номер набора (Setid)")

        self.request_btn = QPushButton("Запросить номера")
        self.request_btn.clicked.connect(self.request_numbers)

        request_layout.addWidget(QLabel("SetId:"))
        request_layout.addWidget(self.setid_edit)
        request_layout.addWidget(self.request_btn)

        request_group.setLayout(request_layout)
        layout.addWidget(request_group)

        layout.addStretch()
        self.setLayout(layout)

    def save_api_key(self):
        api_key = self.api_key_edit.text().strip()
        if len(api_key) != 32:
            QMessageBox.warning(self, "Ошибка", "API ключ должен содержать 32 символа")
            return

        self.data_manager.api_key = api_key

        # Сохранение в файл
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'data', 'config.json'
        )
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

        import json
        # В реальном приложении нужно шифрование
        with open(config_path, 'w') as f:
            json.dump({'api_key': api_key}, f)

        QMessageBox.information(self, "Успех", "API ключ сохранен")

    def browse_xml_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите XML файл", "", "XML files (*.xml)"
        )
        if file_path:
            self.xml_file_edit.setText(file_path)

    def send_xml(self):
        xml_file = self.xml_file_edit.text().strip()
        if not xml_file:
            QMessageBox.warning(self, "Ошибка", "Выберите XML файл")
            return

        if not self.data_manager.api_key:
            QMessageBox.warning(self, "Ошибка", "Введите API ключ")
            return

        from utils.mintrud_api import MinTrudAPI
        api = MinTrudAPI(self.data_manager.api_key)

        success, result = api.send_xml(xml_file)

        if success:
            QMessageBox.information(
                self, "Успех",
                f"Данные загружены на сервер\n\nЗапишите номер набора: {result}"
            )
        else:
            QMessageBox.critical(self, "Ошибка", result)

    def request_numbers(self):
        setid = self.setid_edit.text().strip()
        if not setid:
            QMessageBox.warning(self, "Ошибка", "Введите SetId")
            return

        if not self.data_manager.api_key:
            QMessageBox.warning(self, "Ошибка", "Введите API ключ")
            return

        from utils.mintrud_api import MinTrudAPI
        api = MinTrudAPI(self.data_manager.api_key)

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить отчет", "", "Excel files (*.xlsx)"
        )

        if file_path:
            success, result = api.request_by_setid(setid, file_path)
            if success:
                QMessageBox.information(self, "Успех", f"Отчет сохранен:\n{file_path}")
            else:
                QMessageBox.critical(self, "Ошибка", result)


class MainWindow(QMainWindow):
    """Главное окно приложения"""

    def __init__(self):
        super().__init__()

        self.data_manager = DataManager()

        self.setWindowTitle("Система Excel-XML для Минтруда")
        self.setMinimumSize(1200, 800)

        # Настройка HiDPI
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                border-radius: 5px;
            }
            QTabBar::tab {
                background-color: #e0e0e0;
                color: #000000;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                color: #000000;
            }
            QTabBar::tab:hover {
                background-color: #f0f0f0;
                color: #000000;
            }
            QMessageBox {
                background-color: #ffffff;
                color: #000000;
            }
            QMessageBox QLabel {
                color: #000000;
                font-size: 14px;
                min-width: 50px;
                qproperty-alignment: AlignLeft;
            }
            QMessageBox QPushButton {
                color: #000000;
                background-color: #e0e0e0;
                border: 1px solid #cccccc;
                border-radius: 3px;
                padding: 8px 16px;
                min-height: 35px;
            }
            QMessageBox QPushButton:hover {
                background-color: #d0d0d0;
            }
            QMenu {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #cccccc;
            }
            QMenu::item {
                color: #000000;
                padding: 8px 30px 8px 20px;
            }
            QMenu::item:selected {
                background-color: #e0e0e0;
            }
            QMenuBar {
                background-color: #f0f0f0;
                color: #000000;
            }
            QMenuBar::item:selected {
                background-color: #e0e0e0;
            }
            QMenuBar::item:pressed {
                background-color: #d0d0d0;
            }
        """)

        # Центральная виджет с вкладками
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        central_widget.setLayout(main_layout)

        # Вкладки
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(False)
        self.tabs.setMovable(False)

        self.data_entry_tab = DataEntryTab(self.data_manager, self)
        self.data_view_tab = DataViewTab(self.data_manager, self)
        self.send_data_tab = SendDataTab(self.data_manager, self)

        self.tabs.addTab(self.data_entry_tab, "Внесение данных")
        self.tabs.addTab(self.data_view_tab, "Просмотр данных")
        self.tabs.addTab(self.send_data_tab, "Отправка данных")

        main_layout.addWidget(self.tabs)

        # Статус бар
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Готов к работе")

        # Меню
        self.create_menu()

    def create_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("Файл")

        exit_action = QAction("Выход", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = menubar.addMenu("Справка")

        about_action = QAction("О программе", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def show_about(self):
        QMessageBox.about(
            self, "О программе",
            "Система Excel-XML для передачи данных в Минтруд\n\n"
            "Версия 1.0\n\n"
            "Разработано для автоматизации внесения информации о работниках "
            "в базу данных Минтруда."
        )

    def on_data_updated(self):
        """Обновление данных во вкладке просмотра"""
        self.data_view_tab.refresh_table()