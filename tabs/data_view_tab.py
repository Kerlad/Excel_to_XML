from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QLabel, QMessageBox, QFileDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMenu, QDialog, QFormLayout, QComboBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from datetime import datetime
import os
import logging

from exporters.xml_exporter import export_to_xml
from db.workers_data_repo import WorkersDataRepo
from utils.crypto import decrypt_data, hash_for_search

logger = logging.getLogger(__name__)

FIELD_KEYS = ['last_name', 'first_name', 'middle_name', 'snils', 'position',
              'employer_inn', 'employer_title', 'tc_inn', 'tc_title',
              'result', 'program', 'date', 'protocol']

COLUMN_LABELS = [
    "Фамилия", "Имя", "Отчество", "СНИЛС", "Должность",
    "ИНН\nзаказчика", "Наименование\nзаказчика", "ИНН\nУЦ",
    "Наименование\nУЦ", "Результат", "№ программы", "Дата", "№ протокола"
]


class DataViewTab(QWidget):
    def __init__(self):
        super().__init__()
        self._all_records = []
        self._setup_ui()
        self._connect_signals()
        self._load_all_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("\U0001F50D Поиск...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setMaximumWidth(300)
        toolbar.addWidget(self.search_edit)

        toolbar.addStretch()

        self.refresh_btn = QPushButton("Обновить")
        self.convert_btn = QPushButton("Конвертировать в XML")
        self.clear_btn = QPushButton("Очистить")
        self.export_btn = QPushButton("Экспорт XLSX")

        self.convert_btn.setStyleSheet("""
            QPushButton { color: white; background-color: #27AE60;
                border: none; padding: 8px 16px;
                border-radius: 5px; font-weight: bold}
            QPushButton:hover { background-color: #219A52}
        """)
        self.clear_btn.setStyleSheet("""
            QPushButton { color: white; background-color: #E74C3C;
                border: none; padding: 8px 16px;
                border-radius: 5px; font-weight: bold}
            QPushButton:hover { background-color: #C0392B}
        """)

        toolbar.addWidget(self.refresh_btn)
        toolbar.addWidget(self.convert_btn)
        toolbar.addWidget(self.clear_btn)
        toolbar.addWidget(self.export_btn)
        layout.addLayout(toolbar)

        self.table = QTableWidget()
        self.table.setColumnCount(13)
        self.table.setHorizontalHeaderLabels(COLUMN_LABELS)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.horizontalHeader().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self.status_label = QLabel("Записей: 0 | Выбрано: 0")

        layout.addWidget(self.table)
        layout.addWidget(self.status_label)

    def _connect_signals(self):
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.itemSelectionChanged.connect(self._update_status)
        self.table.horizontalHeader().customContextMenuRequested.connect(self._show_header_menu)
        self.search_edit.textChanged.connect(self._filter_table)
        self.refresh_btn.clicked.connect(self._load_all_data)
        self.convert_btn.clicked.connect(self.convert_to_xml)
        self.clear_btn.clicked.connect(self.clear_all_data)
        self.export_btn.clicked.connect(self._export_xlsx)

    def _load_all_data(self):
        rows = WorkersDataRepo.get_all()
        self._all_records = []
        for r in rows:
            self._all_records.append({
                'last_name': r['last_name'],
                'first_name': r['first_name'],
                'middle_name': r['middle_name'],
                'snils': r['snils'],
                'position': r['position'],
                'employer_inn': r['employer_inn'],
                'employer_title': r['employer_title'],
                'tc_inn': r['tc_inn'],
                'tc_title': r['tc_title'],
                'result': r['result'],
                'program': str(r['program']),
                'date': r['date'],
                'protocol': r['protocol'],
                'id': r['id'],
            })
        self._display_records(self._all_records)

    def _display_records(self, records: list):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for record in records:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col, key in enumerate(FIELD_KEYS):
                item = QTableWidgetItem(str(record.get(key, '')))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, col, item)
            first_item = self.table.item(row, 0)
            if first_item:
                first_item.setData(Qt.ItemDataRole.UserRole, record.get('id'))
            result_item = self.table.item(row, 9)
            if result_item:
                text = result_item.text()
                if text == "Удовлетворительно":
                    result_item.setForeground(QColor("#27AE60"))
                elif text == "Неудовлетворительно":
                    result_item.setForeground(QColor("#E74C3C"))
        self.table.setSortingEnabled(True)
        self._update_status()

    def get_existing_keys(self):
        return WorkersDataRepo.get_existing_keys()

    def add_data(self, new_data, merge_mode=False):
        if merge_mode:
            WorkersDataRepo.clear()
            self.table.setRowCount(0)

        existing_keys = WorkersDataRepo.get_existing_keys()
        duplicates = 0
        to_add = []

        for row in new_data:
            key = (hash_for_search(row.get('snils', '')), str(row.get('program', '')), row.get('date', '') or '')
            if key in existing_keys:
                duplicates += 1
                continue
            existing_keys.add(key)
            to_add.append(row)

        if to_add:
            WorkersDataRepo.add_many(to_add)

        self._load_all_data()

        QMessageBox.information(
            self, "Загрузка завершена",
            f"Добавлено записей: {len(to_add)}\n"
            f"Пропущено дублей: {duplicates}"
        )

    def _filter_table(self, text):
        text = text.strip().lower()
        for row in range(self.table.rowCount()):
            visible = not text
            if text:
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item and text in item.text().lower():
                        visible = True
                        break
            self.table.setRowHidden(row, not visible)
        self._update_status()

    def _update_status(self):
        total = self.table.rowCount()
        visible = sum(1 for row in range(total) if not self.table.isRowHidden(row))
        selected_rows = len(set(
            index.row() for index in self.table.selectedItems()
        )) if self.table.selectedItems() else 0
        self.status_label.setText(f"Записей: {visible} | Выбрано: {selected_rows}")

    def _show_context_menu(self, position):
        row = self.table.rowAt(position.y())
        if row < 0:
            return

        menu = QMenu(self)
        menu.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        edit_action = menu.addAction("Редактировать")
        delete_action = menu.addAction("Удалить")
        duplicate_action = menu.addAction("Дублировать запись")

        action = menu.exec(self.table.mapToGlobal(position))
        if action == edit_action:
            self.edit_selected_row()
        elif action == delete_action:
            self.delete_selected_rows()
        elif action == duplicate_action:
            self._duplicate_selected_rows()

    def _show_header_menu(self, position):
        menu = QMenu(self)
        for i, label in enumerate(COLUMN_LABELS):
            clean = label.replace('\n', ' ')
            action = menu.addAction(clean)
            action.setCheckable(True)
            action.setChecked(not self.table.isColumnHidden(i))
            action.triggered.connect(lambda checked, col=i: self._toggle_column(col))
        menu.exec(self.table.horizontalHeader().mapToGlobal(position))

    def _toggle_column(self, col):
        self.table.setColumnHidden(col, not self.table.isColumnHidden(col))

    def _get_row_data(self, row: int) -> dict:
        data = {}
        for col, key in enumerate(FIELD_KEYS):
            item = self.table.item(row, col)
            data[key] = item.text() if item else ''
        data['id'] = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole) if self.table.item(row, 0) else None
        return data

    def edit_selected_row(self):
        rows = sorted(set(index.row() for index in self.table.selectedItems()))
        if not rows:
            return
        row = rows[0]
        row_data = self._get_row_data(row)
        col_data = {}
        for col, key in enumerate(FIELD_KEYS):
            col_data[col] = row_data.get(key, '')
        col_data['id'] = row_data.get('id')
        dialog = EditDialog(col_data, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_data = dialog.get_data()
            record_id = col_data.get('id')
            if record_id:
                record = {}
                for col, key in enumerate(FIELD_KEYS):
                    record[key] = new_data.get(col, '')
                WorkersDataRepo.update(record_id, record)
                self._load_all_data()

    def delete_selected_rows(self):
        rows = sorted(set(index.row() for index in self.table.selectedItems()))
        if not rows:
            return
        count = len(rows)
        msg = "Вы уверены, что хотите удалить выбранные записи?" if count > 1 else "Вы уверены, что хотите удалить?"
        reply = QMessageBox.question(
            self, "Подтверждение", msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            for row in reversed(rows):
                record_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
                if record_id:
                    WorkersDataRepo.delete(record_id)
            self._load_all_data()

    def _duplicate_selected_rows(self):
        rows = sorted(set(index.row() for index in self.table.selectedItems()))
        if not rows:
            return
        for row in rows:
            data = self._get_row_data(row)
            data.pop('id', None)
            WorkersDataRepo.add(data)
        self._load_all_data()

    def clear_all_data(self):
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Очистить все данные? Данные удалятся безвозвратно.",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
        )
        if reply == QMessageBox.StandardButton.Ok:
            WorkersDataRepo.clear()
            self._all_records.clear()
            self.table.setRowCount(0)
            self._update_status()

    def convert_to_xml(self):
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "Предупреждение", "Нет данных для конвертации")
            return

        from utils.app_paths import get_resource_dir, get_app_data_dir
        resource_dir = get_resource_dir()
        schema_dir = os.path.join(resource_dir, "schema")
        os.makedirs(schema_dir, exist_ok=True)
        xsd_files = [f for f in os.listdir(schema_dir) if f.endswith('.xsd')]

        if not xsd_files:
            QMessageBox.warning(self, "Предупреждение", "XSD отсутствует")
            return

        data_dir = get_app_data_dir()
        settings_file = os.path.join(data_dir, "org_settings.json")
        org_settings = {}
        if os.path.exists(settings_file):
            try:
                import json
                with open(settings_file, 'r', encoding='utf-8') as f:
                    wrapper = json.load(f)
                encrypted = wrapper.get('data', '')
                if encrypted:
                    org_settings = decrypt_data(encrypted)
                else:
                    org_settings = wrapper
            except Exception as e:
                logger.debug(f"Could not load org settings: {e}")

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить XML", "", "XML Files (*.xml)"
        )

        if file_path:
            records = []
            for row in range(self.table.rowCount()):
                if self.table.isRowHidden(row):
                    continue
                record = {}
                for col, key in enumerate(FIELD_KEYS):
                    item = self.table.item(row, col)
                    record[key] = item.text() if item else ''
                records.append(record)

            success, message = export_to_xml(records, file_path, org_settings)
            if success:
                QMessageBox.information(self, "Успех", message)
            else:
                QMessageBox.warning(self, "Ошибка", message)

    def _export_xlsx(self):
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

        total_rows = self.table.rowCount()
        if total_rows == 0:
            QMessageBox.warning(self, "Предупреждение", "Нет данных для экспорта")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить XLSX", "", "Excel Files (*.xlsx)"
        )
        if not file_path:
            return

        wb = Workbook()
        ws = wb.active
        ws.title = "Данные"

        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4169E1", end_color="4169E1", fill_type="solid")
        header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
        thin_border = Border(
            left=Side(style='thin'), right=Side(style='thin'),
            top=Side(style='thin'), bottom=Side(style='thin')
        )

        for col, label in enumerate(COLUMN_LABELS, 1):
            cell = ws.cell(row=1, column=col, value=label.replace('\n', ' '))
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_align
            cell.border = thin_border

        row_num = 2
        for row in range(total_rows):
            if self.table.isRowHidden(row):
                continue
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                value = item.text() if item else ''
                cell = ws.cell(row=row_num, column=col + 1, value=value)
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = thin_border
            row_num += 1

        exported = row_num - 2
        for col in range(1, len(COLUMN_LABELS) + 1):
            max_len = len(COLUMN_LABELS[col - 1].replace('\n', ' '))
            for row in range(2, row_num):
                val = ws.cell(row=row, column=col).value
                if val:
                    max_len = max(max_len, len(str(val)))
            ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = min(max_len + 3, 50)

        wb.save(file_path)
        QMessageBox.information(self, "Успех", f"Экспортировано записей: {exported}")


class EditDialog(QDialog):
    def __init__(self, row_data, parent=None):
        super().__init__(parent)
        self.row_data = row_data
        self.setWindowTitle("Редактирование данных")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.fields = {}
        self.field_widgets = {}
        field_names = [
            ("Фамилия", 0), ("Имя", 1), ("Отчество", 2), ("СНИЛС", 3),
            ("Должность", 4), ("ИНН Заказчика", 5), ("Наименование ЮЛ заказчика", 6),
            ("ИНН УЦ", 7), ("Наименование УЦ", 8), ("Результат", 9),
            ("№ программы", 10), ("Дата", 11), ("№ протокола", 12)
        ]

        for label, col_idx in field_names:
            if col_idx == 9:
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
                form_layout.addRow(label, line_edit)
                self.fields[col_idx] = line_edit
                self.field_widgets[col_idx] = {'widget': line_edit, 'label': label}

        layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Сохранить")
        save_btn.setObjectName("dialogPrimaryBtn")
        save_btn.clicked.connect(self.validate_and_save)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setObjectName("dialogDangerBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _set_error(self, col_idx):
        info = self.field_widgets.get(col_idx)
        if info:
            info['widget'].setStyleSheet("border: 2px solid #E74C3C;")

    def _clear_errors(self):
        for info in self.field_widgets.values():
            info['widget'].setStyleSheet("")

    def validate_and_save(self):
        self._clear_errors()

        values = {}
        for col_idx, info in self.field_widgets.items():
            if isinstance(info['widget'], QComboBox):
                values[col_idx] = info['widget'].currentText()
            else:
                values[col_idx] = info['widget'].text().strip()

        valid_programs = {'1', '2', '3', '4', '6', '7', '8', '9', '10', '11', '12',
                         '13', '14', '15', '16', '17', '18', '19', '20', '21',
                         '22', '23', '24', '25', '26', '27', '28', '29'}

        for col_idx in [0, 1, 2]:
            val = values.get(col_idx, '')
            info = self.field_widgets.get(col_idx)
            if val and not val.replace(' ', '').replace('-', '').isalpha():
                self._set_error(col_idx)
                QMessageBox.warning(self, "Ошибка", f"{info['label']} — только текст")
                return

        import unicodedata
        snils_raw = values.get(3, '')
        snils_clean = ''.join(c for c in snils_raw if unicodedata.category(c) != 'Zs')
        snils_clean = snils_clean.replace('-', '')
        if snils_clean and (not snils_clean.isdigit() or len(snils_clean) != 11):
            self._set_error(3)
            QMessageBox.warning(self, "Ошибка", "СНИЛС должен содержать 11 цифр")
            return

        prog = values.get(10, '').strip()
        if prog and prog not in valid_programs:
            self._set_error(10)
            QMessageBox.warning(self, "Ошибка", "Некорректный номер программы")
            return

        date_val = values.get(11, '').strip()
        if date_val:
            clean = date_val.replace('.', '').replace('-', '')
            if not clean.isdigit() or len(clean) != 8:
                self._set_error(11)
                QMessageBox.warning(self, "Ошибка", "Дата некорректна")
                return
            try:
                dt = datetime.strptime(clean, "%d%m%Y")
                if dt.date() > datetime.now().date():
                    self._set_error(11)
                    QMessageBox.warning(self, "Ошибка", "Дата не может быть больше текущей")
                    return
            except ValueError:
                self._set_error(11)
                QMessageBox.warning(self, "Ошибка", "Дата некорректна")
                return

        self.accept()

    def get_data(self):
        data = {}
        for col_idx, widget in self.fields.items():
            if isinstance(widget, QComboBox):
                data[col_idx] = widget.currentText()
            else:
                data[col_idx] = widget.text()
        return data
