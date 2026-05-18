from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLineEdit, QPushButton,
    QLabel, QMessageBox, QFileDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QComboBox, QCheckBox, QScrollArea, QFrame, QDialog, QFormLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from datetime import datetime
import os
import json
import logging
from exporters.xml_exporter import export_to_xml
from utils.crypto import encrypt_data, decrypt_data

logger = logging.getLogger(__name__)


class DataViewTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: transparent;")
        
        # Хранилище данных
        self.data = []
        
        # Путь к файлу зашифрованных данных работников
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_dir = os.path.join(base_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        self.workers_file = os.path.join(data_dir, "workers_data.json")
        self._load_workers_on_startup()
        
        # Основной layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Кнопки
        btn_layout = QHBoxLayout()
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
        self.clear_btn.clicked.connect(self.clear_all_data)
        
        separator = QLabel("   ")
        
        self.convert_btn = QPushButton("Конвертировать")
        self.convert_btn.setStyleSheet("""
            QPushButton {
                color: green;
                border: 2px solid #4169E1;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #E0FFE0;
            }
        """)
        self.convert_btn.clicked.connect(self.convert_to_xml)

        btn_layout.addWidget(self.clear_btn)
        btn_layout.addWidget(separator)
        btn_layout.addWidget(self.convert_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(13)
        self.table.setHorizontalHeaderLabels([
            "Фамилия", "Имя", "Отчество", "СНИЛС", "Должность",
            "ИНН\nзаказчика", "Наименование\nзаказчика", "ИНН\nУЦ",
            "Наименование\nУЦ", "Результат", "№ программы", "Дата", "№ протокола"
        ])

        # Настройка таблицы
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(25)
        self.table.verticalHeader().setVisible(False)

        # Разделители между заголовками столбцов
        self.table.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                background-color: #4169E1;
                color: white;
                padding: 5px;
                border: 1px solid #3050C0;
                font-weight: bold;
            }
        """)

        # Стилизация
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 2px solid #4169E1;
                border-radius: 5px;
                gridline-color: #CCCCCC;
            }
            QTableWidget::item {
                padding: 5px;
            }
        """)
        
        # Контекстное меню для редактирования/удаления
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        layout.addWidget(self.table)

    def get_existing_keys(self):
        """Возвращает set кортежей (snils, program) существующих записей."""
        keys = set()
        for r in range(self.table.rowCount()):
            snils = self.table.item(r, 3).text() if self.table.item(r, 3) else ''
            prog = self.table.item(r, 10).text() if self.table.item(r, 10) else ''
            keys.add((snils, prog))
        return keys
    
    def add_data(self, new_data, merge_mode=False):
        """Добавление данных в таблицу.
        
        merge_mode:
            False — объединить (добавить к существующим, пропуская дубли)
            True — заменить (удалить старые, загрузить только новые)
        """
        if merge_mode:
            self.data = []
            self.table.setRowCount(0)
        
        # Проверка на дубликаты
        duplicates = 0
        existing_keys = set()
        for r in range(self.table.rowCount()):
            snils = self.table.item(r, 3).text() if self.table.item(r, 3) else ''
            prog = self.table.item(r, 10).text() if self.table.item(r, 10) else ''
            existing_keys.add((snils, prog))
        
        for row in new_data:
            key = (row.get('snils', ''), row.get('program', ''))
            if key in existing_keys:
                duplicates += 1
                continue
            
            existing_keys.add(key)
            self.data.append(row)
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)
            
            # Заполнение строки
            for col, col_key in enumerate(['last_name', 'first_name', 'middle_name', 
                                       'snils', 'position', 'employer_inn', 
                                       'employer_title', 'tc_inn', 'tc_title',
                                       'result', 'program', 'date', 'protocol']):
                item = QTableWidgetItem(str(row.get(col_key, '')))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row_position, col, item)
        
        if duplicates > 0:
            QMessageBox.information(
                self, "Загрузка завершена",
                f"Добавлено записей: {len(new_data) - duplicates}\n"
                f"Пропущено дублей: {duplicates}"
            )
    
    def show_context_menu(self, position):
        """Контекстное меню для строки"""
        from PySide6.QtWidgets import QMenu

        menu = QMenu(self)
        menu.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                color: black;
                border: 1px solid #CCCCCC;
                padding: 5px;
            }
            QMenu::item {
                background-color: white;
                color: black;
                padding: 5px 25px 5px 20px;
            }
            QMenu::item:selected {
                background-color: #E8E8FF;
                color: black;
            }
        """)
        edit_action = menu.addAction("Редактировать")
        delete_action = menu.addAction("Удалить")
        
        action = menu.exec(self.table.mapToGlobal(position))
        
        if action == edit_action:
            self.edit_selected_row()
        elif action == delete_action:
            self.delete_selected_row()
    
    def edit_selected_row(self):
        """Редактирование выбранной строки"""
        current_row = self.table.currentRow()
        if current_row < 0:
            return
        
        # Получаем данные строки
        row_data = {}
        for col in range(self.table.columnCount()):
            item = self.table.item(current_row, col)
            if item:
                row_data[col] = item.text()
        
        # Открываем диалог редактирования
        dialog = EditDialog(row_data, self)
        if dialog.exec() == 1:
            # Обновляем данные
            new_data = dialog.get_data()
            for col, value in new_data.items():
                self.table.setItem(current_row, col, QTableWidgetItem(value))
    
    def delete_selected_row(self):
        """Удаление выбранной строки"""
        current_row = self.table.currentRow()
        if current_row < 0:
            return
        
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Вы уверены, что хотите удалить?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.table.removeRow(current_row)
            if current_row < len(self.data):
                self.data.pop(current_row)
    
    def clear_all_data(self):
        """Очистка всех данных"""
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Очистить все данные? Данные удалятся безвозвратно.",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
        )
        
        if reply == QMessageBox.StandardButton.Ok:
            self.data = []
            self.table.setRowCount(0)
    
    def convert_to_xml(self):
        """Конвертация данных в XML"""
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "Предупреждение", "Нет данных для конвертации")
            return

        # Проверка наличия XSD
        schema_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "schema")
        os.makedirs(schema_dir, exist_ok=True)
        xsd_files = [f for f in os.listdir(schema_dir) if f.endswith('.xsd')]

        if not xsd_files:
            QMessageBox.warning(self, "Предупреждение", "XSD отсутствует")
            return

        # Загрузка настроек организации (с расшифровкой)
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
        settings_file = os.path.join(data_dir, "org_settings.json")
        org_settings = {}
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    wrapper = json.load(f)
                encrypted = wrapper.get('data', '')
                if encrypted:
                    org_settings = decrypt_data(encrypted)
                else:
                    org_settings = wrapper
            except Exception as e:
                logger.debug(f"Could not load org settings: {e}")

        # Диалог сохранения
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить XML", "", "XML Files (*.xml)"
        )

        if file_path:
            # Подготовка данных
            records = []
            for row in range(self.table.rowCount()):
                record = {}
                keys = ['last_name', 'first_name', 'middle_name', 'snils', 'position',
                        'employer_inn', 'employer_title', 'tc_inn', 'tc_title',
                        'result', 'program', 'date', 'protocol']
                for col, key in enumerate(keys):
                    item = self.table.item(row, col)
                    record[key] = item.text() if item else ''
                records.append(record)

            # Экспорт
            success, message = export_to_xml(records, file_path, org_settings)
            if success:
                QMessageBox.information(self, "Успех", message)
            else:
                QMessageBox.warning(self, "Ошибка", message)

    def _load_workers_on_startup(self):
        """Загрузка зашифрованных данных работников при старте."""
        if not os.path.exists(self.workers_file):
            return
        try:
            with open(self.workers_file, 'r', encoding='utf-8') as f:
                wrapper = json.load(f)
            encrypted = wrapper.get('data', '')
            if encrypted:
                records = decrypt_data(encrypted)
                if isinstance(records, list):
                    self.add_data(records, replace=False)
        except Exception as e:
            logger.debug(f"Could not load workers: {e}")


class EditDialog(QDialog):
    """Диалог редактирования строки"""
    def __init__(self, row_data, parent=None):
        super().__init__(parent)
        self.row_data = row_data
        self.setWindowTitle("Редактирование данных")
        self.setMinimumWidth(500)

        # Белый фон — через атрибут и stylesheet
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            EditDialog {
                background-color: white;
            }
            EditDialog QLabel {
                color: black;
                background: transparent;
            }
            EditDialog QLineEdit {
                color: black;
                background-color: white;
                border: 1px solid #CCCCCC;
                padding: 4px;
            }
            EditDialog QComboBox {
                color: black;
                background-color: white;
                border: 1px solid #CCCCCC;
                padding: 4px;
            }
            EditDialog QPushButton {
                background-color: #4169E1;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
            }
            EditDialog QPushButton:hover {
                background-color: #3151B1;
            }
        """)

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.fields = {}
        self.field_widgets = {}  # для подсветки ошибок
        field_names = [
            ("Фамилия", 0), ("Имя", 1), ("Отчество", 2), ("СНИЛС", 3),
            ("Должность", 4), ("ИНН Заказчика", 5), ("Наименование ЮЛ заказчика", 6),
            ("ИНН УЦ", 7), ("Наименование УЦ", 8), ("Результат", 9),
            ("№ программы", 10), ("Дата", 11), ("№ протокола", 12)
        ]

        for label, col_idx in field_names:
            if col_idx == 9:  # Результат - выпадающий список
                combo = QComboBox()
                combo.addItems(["Удовлетворительно", "Неудовлетворительно"])
                current_value = row_data.get(col_idx, "Удовлетворительно")
                idx = combo.findText(current_value)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
                form_layout.addRow(label, combo)
                self.fields[col_idx] = combo
                self.field_widgets[col_idx] = {'widget': combo, 'label': label}
            else:
                line_edit = QLineEdit()
                line_edit.setText(row_data.get(col_idx, ""))
                line_edit.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
                form_layout.addRow(label, line_edit)
                self.fields[col_idx] = line_edit
                self.field_widgets[col_idx] = {'widget': line_edit, 'label': label}

        layout.addLayout(form_layout)

        # Кнопки
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.validate_and_save)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _set_error(self, col_idx):
        """Подсветка поля ошибкой."""
        info = self.field_widgets.get(col_idx)
        if info:
            info['widget'].setStyleSheet("color: black; border: 2px solid red; padding: 4px;")

    def _clear_errors(self):
        """Сброс всех ошибок."""
        for info in self.field_widgets.values():
            info['widget'].setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")

    def validate_and_save(self):
        """Валидация данных согласно FR-001."""
        self._clear_errors()

        # Получаем значения
        values = {}
        for col_idx, info in self.field_widgets.items():
            if isinstance(info['widget'], QComboBox):
                values[col_idx] = info['widget'].currentText()
            else:
                values[col_idx] = info['widget'].text().strip()

        valid_programs = {'1', '2', '3', '4', '6', '7', '8', '9', '10', '11', '12',
                         '13', '14', '15', '16', '17', '18', '19', '20', '21',
                         '22', '23', '24', '25', '26', '27', '28', '29'}

        # ФИО — только текст (колонки 0,1,2)
        for col_idx in [0, 1, 2]:
            val = values.get(col_idx, '')
            info = self.field_widgets.get(col_idx)
            if val and not val.replace(' ', '').replace('-', '').isalpha():
                self._set_error(col_idx)
                QMessageBox.warning(self, "Ошибка", f"{info['label']} — только текст")
                return

        # СНИЛС — 11 цифр (колонка 3)
        import unicodedata
        snils_raw = values.get(3, '')
        # Удаляем все Unicode-пробелы (категория Zs) включая \xa0
        snils_clean = ''.join(c for c in snils_raw if unicodedata.category(c) != 'Zs')
        snils_clean = snils_clean.replace('-', '')
        if snils_clean and (not snils_clean.isdigit() or len(snils_clean) != 11):
            self._set_error(3)
            QMessageBox.warning(self, "Ошибка", "СНИЛС должен содержать 11 цифр")
            return

        # № программы (колонка 10)
        prog = values.get(10, '').strip()
        if prog and prog not in valid_programs:
            self._set_error(10)
            QMessageBox.warning(self, "Ошибка", "Некорректный номер программы")
            return

        # Дата (колонка 11)
        date_val = values.get(11, '').strip()
        if date_val:
            clean = date_val.replace('.', '').replace('-', '')
            if not clean.isdigit() or len(clean) != 8:
                self._set_error(11)
                QMessageBox.warning(self, "Ошибка", "Дата некорректна. Введите корректную дату в формате ЧЧ.ММ.ГГГГ или ЧЧММГГГГ")
                return
            try:
                dt = datetime.strptime(clean, "%d%m%Y")
                if dt.date() > datetime.now().date():
                    self._set_error(11)
                    QMessageBox.warning(self, "Ошибка", "Дата не может быть больше текущей")
                    return
            except ValueError:
                self._set_error(11)
                QMessageBox.warning(self, "Ошибка", "Дата некорректна. Введите корректную дату в формате ЧЧ.ММ.ГГГГ или ЧЧММГГГГ")
                return

        self.accept()

    def get_data(self):
        """Получение данных из диалога"""
        data = {}
        for col_idx, widget in self.fields.items():
            if isinstance(widget, QComboBox):
                data[col_idx] = widget.currentText()
            else:
                data[col_idx] = widget.text()
        return data
