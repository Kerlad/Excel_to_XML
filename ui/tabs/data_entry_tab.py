"""
Вкладка внесения данных о работниках
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QTextEdit, QFileDialog, QMessageBox, QDialog,
                             QDialogButtonBox, QListWidget, QListWidgetItem,
                             QComboBox, QGroupBox, QFormLayout, QScrollArea)
from PyQt6.QtCore import Qt

import sys
import os
import json
import shutil
import webbrowser
import subprocess

from typing import Optional

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data_model import DataManager, WorkerRecord


# Путь к файлу настроек организации
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
            schema_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'schema')
            os.makedirs(schema_dir, exist_ok=True)
            dest_path = os.path.join(schema_dir, 'schema.xsd')
            shutil.copy(file_path, dest_path)
            QMessageBox.information(self, "Успех", "XSD схема загружена и сохранена")

    def open_xsd_url(self):
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
            subprocess.run(['xdg-open', os.path.dirname(template_path)])