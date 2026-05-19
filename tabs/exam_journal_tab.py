"""
Вкладка «Журнал проверки знаний»
Отображение истории отправок, поиск, фильтрация, экспорт, удаление
"""
import os
import json
import logging
from datetime import datetime, date
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QLineEdit, QComboBox, QHeaderView, QAbstractItemView,
    QMessageBox, QFileDialog, QDateEdit, QGroupBox, QFormLayout, QInputDialog
)
from PySide6.QtCore import Qt, QSortFilterProxyModel, QDate
from PySide6.QtGui import QColor, QFont
from db.exam_journal_repo import JournalRecord

logger = logging.getLogger(__name__)


class ExamJournalTab(QWidget):
    def __init__(self, journal_manager, data_dir=None):
        super().__init__()
        self.setStyleSheet("background-color: transparent;")
        self.journal = journal_manager
        self.data_dir = data_dir
        self.last_save_path = self._load_last_save_path() if data_dir else ''

        # Основной layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Панель поиска и фильтров
        main_layout.addWidget(self._create_search_panel())

        # Кнопки действий
        main_layout.addWidget(self._create_action_buttons())

        # Таблица
        self.table = self._create_table()
        main_layout.addWidget(self.table)

        # Статус-бар
        self.status_label = QLabel("Записей: 0")
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")
        main_layout.addWidget(self.status_label)

        # Контекстное меню
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        # Загрузка данных
        self.refresh_journal()
    
    def _load_last_save_path(self):
        """Загрузка последнего пути сохранения."""
        import json
        if not self.data_dir:
            return ''
        settings_file = os.path.join(self.data_dir, "journal_settings.json")
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    return settings.get('last_save_path', '')
            except Exception as e:
                logger.debug(f"Could not load last_save_path: {e}")
        return ''
    
    def _save_last_save_path(self, path):
        """Сохранение последнего пути сохранения."""
        import json
        if not self.data_dir:
            return
        settings_file = os.path.join(self.data_dir, "journal_settings.json")
        settings = {}
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
            except Exception as e:
                logger.debug(f"Could not load settings: {e}")
        settings['last_save_path'] = path  # Полный путь
        try:
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Could not save settings: {e}")

    def _create_search_panel(self) -> QGroupBox:
        """Панель поиска и фильтрации."""
        group = QGroupBox()
        group.setTitle("Поиск и фильтрация")
        group.setStyleSheet("""
            QGroupBox {
                border: 2px solid #4169E1;
                border-radius: 8px;
                margin-top: 8px;
                padding: 10px 15px;
                background-color: transparent;
                font-weight: bold;
                color: #4169E1;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)

        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # Строка 1: Поиск + SetId
        row1 = QHBoxLayout()

        # Поиск по ФИО/СНИЛС
        search_label = QLabel("Поиск:")
        search_label.setStyleSheet("color: inherit; font-weight: normal;")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Фамилия, Имя или СНИЛС")
        self.search_input.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 4px;")
        self.search_input.textChanged.connect(self._apply_filters)
        row1.addWidget(search_label)
        row1.addWidget(self.search_input)

        row1.addSpacing(15)

        # Фильтр по SetId
        setid_label = QLabel("SetId:")
        setid_label.setStyleSheet("color: inherit; font-weight: normal;")
        self.setid_combo = QComboBox()
        self.setid_combo.setMinimumWidth(250)
        self.setid_combo.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 4px;")
        self.setid_combo.addItem("Все")
        self.setid_combo.currentTextChanged.connect(self._apply_filters)
        row1.addWidget(setid_label)
        row1.addWidget(self.setid_combo)

        row1.addSpacing(15)

        # Фильтр по номеру протокола
        protocol_label = QLabel("Протокол:")
        protocol_label.setStyleSheet("color: inherit; font-weight: normal;")
        self.protocol_combo = QComboBox()
        self.protocol_combo.setMinimumWidth(150)
        self.protocol_combo.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 4px;")
        self.protocol_combo.addItem("Все")
        self.protocol_combo.currentTextChanged.connect(self._apply_filters)
        row1.addWidget(protocol_label)
        row1.addWidget(self.protocol_combo)

        layout.addLayout(row1)

        # Строка 2: Статус + Даты
        row2 = QHBoxLayout()

        # Фильтр по статусу
        status_label = QLabel("Статус:")
        status_label.setStyleSheet("color: inherit; font-weight: normal;")
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Все", "ожидает", "получен"])
        self.status_combo.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 4px;")
        self.status_combo.currentTextChanged.connect(self._apply_filters)
        row2.addWidget(status_label)
        row2.addWidget(self.status_combo)

        row2.addSpacing(15)

        # Фильтр по дате (с)
        date_from_label = QLabel("Дата с:")
        date_from_label.setStyleSheet("color: inherit; font-weight: normal;")
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("dd.MM.yyyy")
        self.date_from.blockSignals(True)
        self.date_from.setDate(QDate(2023, 1, 1))
        self.date_from.blockSignals(False)
        self.date_from.setStyleSheet("""
            color: inherit; 
            border: 1px solid #CCCCCC; 
            padding: 4px;
            background-color: white;
        """)
        self.date_from.dateChanged.connect(self._apply_filters)
        row2.addWidget(date_from_label)
        row2.addWidget(self.date_from)

        row2.addSpacing(15)

        # Фильтр по дате (по)
        date_to_label = QLabel("Дата по:")
        date_to_label.setStyleSheet("color: inherit; font-weight: normal;")
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("dd.MM.yyyy")
        self.date_to.blockSignals(True)
        self.date_to.setDate(self.date_to.maximumDate())
        self.date_to.blockSignals(False)
        self.date_to.setStyleSheet("""
            color: inherit; 
            border: 1px solid #CCCCCC; 
            padding: 4px;
            background-color: white;
        """)
        self.date_to.dateChanged.connect(self._apply_filters)
        row2.addWidget(date_to_label)
        row2.addWidget(self.date_to)

        row2.addSpacing(15)

        # Кнопка сброса
        reset_btn = QPushButton("Сбросить")
        reset_btn.setStyleSheet("""
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
        reset_btn.clicked.connect(self._reset_filters)
        row2.addWidget(reset_btn)

        row2.addStretch()
        layout.addLayout(row2)

        return group

    def _create_action_buttons(self) -> QWidget:
        """Кнопки действий."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 5, 0, 5)

        # Экспорт в XLSX
        self.export_btn = QPushButton("Экспорт в XLSX")
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #4169E1;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3151B8;
            }
        """)
        self.export_btn.clicked.connect(self._export_to_xlsx)
        layout.addWidget(self.export_btn)

        # Импорт из Excel
        self.import_btn = QPushButton("Импорт из Excel")
        self.import_btn.setStyleSheet("""
            QPushButton {
                background-color: #4169E1;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3151B8;
            }
        """)
        self.import_btn.clicked.connect(self._import_from_excel)
        layout.addWidget(self.import_btn)

        # Сформировать шаблон журнала
        self.template_btn = QPushButton("Сформировать шаблон журнала")
        self.template_btn.setStyleSheet("""
            QPushButton {
                background-color: #4169E1;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3151B8;
            }
        """)
        self.template_btn.clicked.connect(self._create_journal_template)
        layout.addWidget(self.template_btn)

        # Печать протокола
        self.print_protocol_btn = QPushButton("Печать протокола")
        self.print_protocol_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        self.print_protocol_btn.clicked.connect(self._print_protocol)
        layout.addWidget(self.print_protocol_btn)

        # Удалить
        self.delete_btn = QPushButton("Удалить")
        self.delete_btn.setStyleSheet("""
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
        self.delete_btn.clicked.connect(self._delete_selected)
        layout.addWidget(self.delete_btn)

        layout.addStretch()
        return widget

    def _create_table(self) -> QTableWidget:
        """Создание таблицы журнала."""
        table = QTableWidget()
        table.setColumnCount(15)
        table.setHorizontalHeaderLabels([
            "№ протокола", "Дата экзамена", "Фамилия", "Имя", "Отчество", "СНИЛС",
            "Рег. номер", "№ программы", "Название программы", "Должность",
            "Результат", "SetId", "Дата отправки", "Статус", ""
        ])

        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        table.verticalHeader().setDefaultSectionSize(25)
        table.verticalHeader().setVisible(False)

        # Стилизация
        table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 2px solid #4169E1;
                border-radius: 5px;
                gridline-color: #E0E0E0;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #4169E1;
                color: white;
                padding: 5px;
                border: 1px solid #3050C0;
                font-weight: bold;
            }
        """)

        # Ширина колонок (10 символов ≈ 100px)
        table.setColumnWidth(0, 100)   # № протокола
        table.setColumnWidth(1, 100)   # Дата экзамена
        table.setColumnWidth(2, 100)   # Фамилия
        table.setColumnWidth(3, 100)   # Имя
        table.setColumnWidth(4, 100)   # Отчество
        table.setColumnWidth(5, 120)   # СНИЛС
        table.setColumnWidth(6, 100)   # Рег. номер
        table.setColumnWidth(7, 100)   # № программы
        table.setColumnWidth(8, 300)   # Название программы
        table.setColumnWidth(9, 100)   # Должность
        table.setColumnWidth(10, 100)  # Результат
        table.setColumnWidth(11, 120)  # SetId
        table.setColumnWidth(12, 120) # Дата отправки
        table.setColumnWidth(13, 100)  # Статус
        table.hideColumn(14)           # Скрытый UUID

        return table

    # ============ Обновление данных ============

    def refresh_journal(self):
        """Обновление таблицы из журнала."""
        self.table.setRowCount(0)

        filtered = self._get_filtered_records()

        for row_idx, record in enumerate(filtered):
            self.table.insertRow(row_idx)

            # Форматирование дат без времени
            exam_date = record.exam_date.split()[0] if record.exam_date else ""
            send_date = record.send_date.split()[0] if record.send_date else ""

            items = [
                record.protocol,  # 0 - № протокола
                exam_date,  # 1 - Дата экзамена
                record.last_name,  # 2 - Фамилия
                record.first_name,  # 3 - Имя
                record.middle_name,  # 4 - Отчество
                record.snils,  # 5 - СНИЛС
                record.base_no,  # 6 - Рег. номер
                record.program_id,  # 7 - № программы
                record.program_title,  # 8 - Название программы
                record.position,  # 9 - Должность
                record.result,  # 10 - Результат
                record.set_id,  # 11 - SetId
                send_date,  # 12 - Дата отправки
                "получен" if record.status == "received" else "ожидает",  # 13 - Статус
                record.uuid  # 14 - Скрытая колонка
            ]

            for col, text in enumerate(items):
                item = QTableWidgetItem(str(text))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                # Цветовая индикация статуса (колонка 13)
                if col == 13:
                    if record.status == "received":
                        item.setForeground(QColor("#28a745"))
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)
                    else:
                        item.setForeground(QColor("#e67e22"))
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)

                self.table.setItem(row_idx, col, item)

        # Обновить статус
        all_count = len(self.journal.get_all_records())
        shown = len(filtered)
        if shown != all_count:
            self.status_label.setText(f"Показано: {shown} из {all_count}")
        else:
            self.status_label.setText(f"Записей: {all_count}")

        # Обновить combo SetId
        self._update_setid_combo()
        
        # Обновить combo протоколов
        self._update_protocol_combo()

    def _get_filtered_records(self):
        """Получение отфильтрованных записей."""
        query = self.search_input.text()
        set_id = self.setid_combo.currentText()
        if set_id == "Все":
            set_id = ""
        status_map = {"Все": "all", "ожидает": "pending", "получен": "received"}
        status = self.status_combo.currentText()
        if status == "Все":
            status = "all"
        else:
            status = "pending" if status == "ожидает" else "received"
        
        # Фильтр по номеру протокола
        protocol_filter = self.protocol_combo.currentText()
        if protocol_filter == "Все":
            protocol_filter = ""
        
        from datetime import date as datetime_date
        # Проверяем, установлены ли фильтры дат
        date_from = ""
        date_to = ""

        self.date_from.blockSignals(True)
        self.date_to.blockSignals(True)
        try:
            if self.date_from.date() > QDate(2023, 1, 1):
                date_from = self.date_from.date().toString("dd.MM.yyyy")
            if self.date_to.date() < self.date_to.maximumDate():
                date_to = self.date_to.date().toString("dd.MM.yyyy")
        finally:
            self.date_from.blockSignals(False)
            self.date_to.blockSignals(False)

        records = self.journal.search(
            query=query, set_id=set_id,
            status=status, date_from=date_from, date_to=date_to
        )
        
        # Дополнительный фильтр по номеру протокола
        if protocol_filter:
            records = [r for r in records if r.protocol == protocol_filter]
        
        return records

    def _update_setid_combo(self):
        """Обновление combo-бокса SetId."""
        current = self.setid_combo.currentText()
        self.setid_combo.blockSignals(True)
        try:
            self.setid_combo.clear()
            self.setid_combo.addItem("Все")

            set_ids = self.journal.get_unique_set_ids()
            for sid in set_ids:
                short = sid[:20] + "..." if len(sid) > 20 else sid
                self.setid_combo.addItem(short, sid)

            # Восстановить выбор
            idx = self.setid_combo.findData(current)
            if idx >= 0:
                self.setid_combo.setCurrentIndex(idx)
            else:
                self.setid_combo.setCurrentIndex(0)
        finally:
            self.setid_combo.blockSignals(False)

    def _update_protocol_combo(self):
        """Обновление combo-бокса номеров протоколов."""
        if not hasattr(self, 'protocol_combo'):
            return
        current = self.protocol_combo.currentText()
        self.protocol_combo.blockSignals(True)
        try:
            self.protocol_combo.clear()
            self.protocol_combo.addItem("Все")
            
            # Получаем уникальные номера протоколов
            all_records = self.journal.get_all_records()
            protocols = sorted(set(r.protocol for r in all_records if r.protocol))
            for proto in protocols:
                self.protocol_combo.addItem(proto)
            
            # Восстановить выбор
            idx = self.protocol_combo.findText(current)
            if idx >= 0:
                self.protocol_combo.setCurrentIndex(idx)
            else:
                self.protocol_combo.setCurrentIndex(0)
        finally:
            self.protocol_combo.blockSignals(False)

    # ============ Фильтры ============

    def _apply_filters(self):
        """Применение фильтров."""
        self.refresh_journal()

    def _reset_filters(self):
        """Сброс всех фильтров."""
        self.search_input.clear()
        self.setid_combo.setCurrentIndex(0)
        self.status_combo.setCurrentIndex(0)
        self.date_from.blockSignals(True)
        self.date_to.blockSignals(True)
        try:
            self.date_from.setDate(self.date_from.minimumDate())
            self.date_to.setDate(self.date_to.maximumDate())
        finally:
            self.date_from.blockSignals(False)
            self.date_to.blockSignals(False)
        self.refresh_journal()

    # ============ Действия ============

    def _export_to_xlsx(self):
        """Экспорт журнала в XLSX."""
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment

        records = self._get_filtered_records()
        if not records:
            QMessageBox.information(self, "Информация", "Нет данных для экспорта")
            return

        # Диалог с последним путем
        if self.last_save_path and os.path.exists(self.last_save_path):
            default_path = self.last_save_path
        elif self.last_save_path and os.path.exists(os.path.dirname(self.last_save_path)):
            default_path = os.path.join(os.path.dirname(self.last_save_path), "Журнал_проверки_знаний.xlsx")
        else:
            default_path = "Журнал_проверки_знаний.xlsx"
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить XLSX", default_path,
            "Excel Files (*.xlsx)"
        )
        if not file_path:
            return
        
        # Сохраняем путь
        self._save_last_save_path(file_path)

        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "Журнал"

            headers = [
                "№ протокола", "Дата экзамена", "Фамилия", "Имя", "Отчество", "СНИЛС",
                "Рег. номер", "№ программы", "Название программы", "Должность",
                "Результат", "SetId", "Дата отправки", "Статус"
            ]
            ws.append(headers)

            # Стилизация заголовков
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="4169E1", end_color="4169E1", fill_type="solid")
            for cell in ws[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center")

            for rec in records:
                exam_date = rec.exam_date.split()[0] if rec.exam_date else ""
                send_date = rec.send_date.split()[0] if rec.send_date else ""
                ws.append([
                    rec.protocol, exam_date, rec.last_name, rec.first_name,
                    rec.middle_name, rec.snils, rec.base_no, rec.program_id,
                    rec.program_title, rec.position, rec.result, rec.set_id,
                    send_date,
                    "получен" if rec.status == "received" else "ожидает"
                ])

            # Автоширина столбцов
            for col in ws.columns:
                max_len = 0
                col_letter = col[0].column_letter
                for cell in col:
                    if cell.value:
                        max_len = max(max_len, len(str(cell.value)))
                ws.column_dimensions[col_letter].width = min(max_len + 2, 50)

            wb.save(file_path)
            QMessageBox.information(self, "Успех", f"Журнал сохранён:\n{file_path}")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка экспорта: {e}")

    def _import_from_excel(self):
        """Импорт записей из Excel файла (поддерживает форматы журнала и API SetID)."""
        from openpyxl import load_workbook
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите Excel файл", "", "Excel Files (*.xlsx *.xls)"
        )
        if not file_path:
            return
            
        try:
            wb = load_workbook(file_path)
            ws = wb.active
            
            # Получаем заголовки
            headers = [cell.value for cell in ws[1]]
            
            # Определяем тип файла по заголовкам
            # Формат журнала экспорта
            journal_headers = [
                "№ протокола", "Дата экзамена", "Фамилия", "Имя", "Отчество", "СНИЛС",
                "Рег. номер", "№ программы", "Название программы", "Должность",
                "Результат", "SetId", "Дата отправки", "Статус"
            ]
            
            # Формат API SetID экспорта
            api_setid_headers = [
                "Номер записи в реестре", "Фамилия", "Имя", "Отчество",
                "СНИЛС", "Номер программы", "Название программы",
                "Номер протокола", "Дата"
            ]
            
            # Формат импорта журнала (английские колонки, из import_journal.py)
            import_headers = [
                "last_name", "first_name", "middle_name", "snils", "position",
                "program_id", "program_title", "exam_date", "protocol", "result",
                "set_id", "base_no", "status"
            ]
            
            # Проверяем, какой формат файла
            is_journal_format = all(header in headers for header in journal_headers)
            is_api_setid_format = all(header in headers for header in api_setid_headers)
            is_import_format = all(header in headers for header in import_headers)
            
            if not (is_journal_format or is_api_setid_format or is_import_format):
                logger.error(f"Unsupported journal format. Headers: {headers}")
                QMessageBox.warning(
                    self, "Ошибка", 
                    "Неподдерживаемый формат файла. Ожидается формат журнала экспорта или API SetID экспорта."
                )
                return
                
            # Словарь для быстрого поиска индексов колонок
            col_indices = {header: idx for idx, header in enumerate(headers)}
            
            records_to_add = []
            errors = []
            
            # Обрабатываем строки данных
            for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                try:
                    # Пропускаем пустые строки
                    if not any(cell is not None for cell in row):
                        continue
                    
                    if is_journal_format:
                        # Импорт из формата журнала экспорта
                        protocol = str(row[col_indices.get("№ протокола", 0)] or "").strip()
                        exam_date = str(row[col_indices.get("Дата экзамена", 1)] or "").strip()
                        last_name = str(row[col_indices.get("Фамилия", 2)] or "").strip()
                        first_name = str(row[col_indices.get("Имя", 3)] or "").strip()
                        middle_name = str(row[col_indices.get("Отчество", 4)] or "").strip()
                        snils = str(row[col_indices.get("СНИЛС", 5)] or "").strip()
                        base_no = str(row[col_indices.get("Рег. номер", 6)] or "").strip()
                        program_id = str(row[col_indices.get("№ программы", 7)] or "").strip()
                        program_title = str(row[col_indices.get("Название программы", 8)] or "").strip()
                        position = str(row[col_indices.get("Должность", 9)] or "").strip()
                        result = str(row[col_indices.get("Результат", 10)] or "").strip()
                        set_id = str(row[col_indices.get("SetId", 11)] or "").strip()
                        send_date = str(row[col_indices.get("Дата отправки", 12)] or "").strip()
                        status_str = str(row[col_indices.get("Статус", 13)] or "").lower()
                        
                        # Проверяем обязательные поля
                        if not all([last_name, first_name, middle_name, snils, program_id, 
                                  program_title, protocol, exam_date]):
                            errors.append(f"Строка {row_idx}: заполните все обязательные поля")
                            continue
                        
                        # Форматируем СНИЛС (удаляем все кроме цифр, затем форматируем)
                        snils_digits = ''.join(filter(str.isdigit, snils))
                        if len(snils_digits) != 11:
                            errors.append(f"Строка {row_idx}: СНИЛС должен содержать 11 цифр")
                            continue
                        snils_formatted = f"{snils_digits[:3]}-{snils_digits[3:6]}-{snils_digits[6:9]} {snils_digits[9:]}"

                        # Определяем статус
                        if "получен" in status_str or "received" in status_str:
                            status = "received"
                        else:
                            status = "pending"  # По умолчанию ожидает

                        # Если результат не указан, устанавливаем значение по умолчанию
                        if not result:
                            result = "Удовлетворительно"
                    elif is_api_setid_format:
                        # Импорт из формата API SetID экспорта
                        base_no = str(row[col_indices.get("Номер записи в реестре", 0)] or "").strip()
                        last_name = str(row[col_indices.get("Фамилия", 1)] or "").strip()
                        first_name = str(row[col_indices.get("Имя", 2)] or "").strip()
                        middle_name = str(row[col_indices.get("Отчество", 3)] or "").strip()
                        snils = str(row[col_indices.get("СНИЛС", 4)] or "").strip()
                        program_id = str(row[col_indices.get("Номер программы", 5)] or "").strip()
                        program_title = str(row[col_indices.get("Название программы", 6)] or "").strip()
                        protocol = str(row[col_indices.get("Номер протокола", 7)] or "").strip()
                        exam_date = str(row[col_indices.get("Дата", 8)] or "").strip()

                        # Проверяем обязательные поля (кроме base_no, который может быть пустым)
                        if not all([last_name, first_name, middle_name, snils, program_id,
                                  program_title, protocol, exam_date]):
                            errors.append(f"Строка {row_idx}: заполните все обязательные поля кроме номера реестра")
                            continue

                        # Форматируем СНИЛС (удаляем все кроме цифр, затем форматируем)
                        snils_digits = ''.join(filter(str.isdigit, snils))
                        if len(snils_digits) != 11:
                            errors.append(f"Строка {row_idx}: СНИЛС должен содержать 11 цифр")
                            continue
                        snils_formatted = f"{snils_digits[:3]}-{snils_digits[3:6]}-{snils_digits[6:9]} {snils_digits[9:]}"

                        # Для API SetID формата отсутствуют эти поля
                        send_date = ""
                        set_id = ""
                        position = ""
                        result = ""

                        # Определяем статус: если есть номер реестра, то статус "received", иначе "pending"
                        status = "received" if base_no else "pending"
                        if not result:
                            result = "Удовлетворительно"
                    elif is_import_format:
                        # Импорт из формата import_journal (английские колонки)
                        last_name = str(row[col_indices.get("last_name", 0)] or "").strip()
                        first_name = str(row[col_indices.get("first_name", 1)] or "").strip()
                        middle_name = str(row[col_indices.get("middle_name", 2)] or "").strip()
                        snils = str(row[col_indices.get("snils", 3)] or "").strip()
                        position = str(row[col_indices.get("position", 4)] or "").strip()
                        program_id = str(row[col_indices.get("program_id", 5)] or "").strip()
                        program_title = str(row[col_indices.get("program_title", 6)] or "").strip()
                        exam_date = str(row[col_indices.get("exam_date", 7)] or "").strip()
                        protocol = str(row[col_indices.get("protocol", 8)] or "").strip()
                        result = str(row[col_indices.get("result", 9)] or "").strip()
                        set_id = str(row[col_indices.get("set_id", 10)] or "").strip()
                        base_no = str(row[col_indices.get("base_no", 11)] or "").strip()
                        status_str = str(row[col_indices.get("status", 12)] or "").lower()

                        if not all([last_name, first_name, middle_name, snils, program_id,
                                  program_title, protocol, exam_date]):
                            errors.append(f"Строка {row_idx}: заполните все обязательные поля")
                            continue

                        snils_digits = ''.join(filter(str.isdigit, snils))
                        if len(snils_digits) != 11:
                            errors.append(f"Строка {row_idx}: СНИЛС должен содержать 11 цифр")
                            continue
                        snils_formatted = f"{snils_digits[:3]}-{snils_digits[3:6]}-{snils_digits[6:9]} {snils_digits[9:]}"

                        send_date = ""
                        if "получен" in status_str or "received" in status_str:
                            status = "received"
                        else:
                            status = "pending"
                        if not result:
                            result = "Удовлетворительно"

                    # Создаем запись
                    import uuid
                    record = JournalRecord(
                        uuid=str(uuid.uuid4()),
                        send_date=send_date,
                        set_id=set_id,
                        xml_file="",   # Путь к XML файлу будет заполнен при отправке
                        last_name=last_name,
                        first_name=first_name,
                        middle_name=middle_name,
                        snils=snils_formatted,
                        position=position,
                        program_id=program_id,
                        program_title=program_title,
                        exam_date=exam_date,
                        protocol=protocol,
                        result=result,
                        base_no=base_no,
                        status=status
                    )
                    records_to_add.append(record)
                     
                except Exception as e:
                    errors.append(f"Строка {row_idx}: {str(e)}")
             
            # Если есть ошибки, показываем их
            if errors:
                logger.error(f"Journal import errors: {errors}")
                error_msg = "Обнаружены ошибки при импорте:\n" + "\n".join(errors[:10])
                if len(errors) > 10:
                    error_msg += f"\n... и еще {len(errors) - 10} ошибок"
                QMessageBox.warning(self, "Ошибки импорта", error_msg)
                # Продолжаем с теми записями, которые прошли валидацию
             
            if not records_to_add:
                QMessageBox.information(self, "Информация", "Нет данных для импорта")
                return
                 
            # Добавляем записи в журнал
            self.journal.add_journal_records_directly(records_to_add)
             
            QMessageBox.information(
                self, "Успех", 
                f"Успешно импортировано {len(records_to_add)} записей"
            )
            self.refresh_journal()
             
        except Exception as e:
            logger.error(f"Journal import failed: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось прочитать файл:\n{str(e)}")

    def _create_journal_template(self):
        """Создание шаблона журнала с тестовой записью."""
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить шаблон журнала", "Шаблон_журнала.xlsx",
            "Excel Files (*.xlsx)"
        )
        if not file_path:
            return
            
        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "Журнал"

            headers = [
                "№ протокола", "Дата экзамена", "Фамилия", "Имя", "Отчество", "СНИЛС",
                "Рег. номер", "№ программы", "Название программы", "Должность",
                "Результат", "SetId", "Дата отправки", "Статус"
            ]
            ws.append(headers)

            # Стилизация заголовков
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="4169E1", end_color="4169E1", fill_type="solid")
            for cell in ws[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center")

            # Добавляем тестовую запись
            test_record = [
                "1",                               # № протокола
                "01.01.2026",                       # Дата экзамена
                "Иванов",                          # Фамилия
                "Иван",                            # Имя
                "Иванович",                        # Отчество
                "123-456-789 00",                  # СНИЛС
                "123456",                          # Рег. номер
                "1",                               # № программы
                "Оказание первой помощи пострадавшим",  # Название программы
                "Инженер",                         # Должность
                "Удовлетворительно",              # Результат
                "SET123456",                       # SetId
                "01.01.2026",                     # Дата отправки
                "получен"                          # Статус
            ]
            ws.append(test_record)

            # Автоширина столбцов
            for col in ws.columns:
                max_len = 0
                col_letter = col[0].column_letter
                for cell in col:
                    if cell.value:
                        max_len = max(max_len, len(str(cell.value)))
                ws.column_dimensions[col_letter].width = min(max_len + 2, 50)

            wb.save(file_path)
            QMessageBox.information(self, "Успех", f"Шаблон журнала создан:\n{file_path}")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка создания шаблона: {e}")

    def _print_protocol(self):
        """Печать протокола — ввод номера протокола."""
        from exporters.protocol_exporter import ProtocolExporter

        records = self._get_filtered_records()
        if not records:
            QMessageBox.information(self, "Информация", "Нет данных для формирования протокола")
            return

        # Получаем уникальные номера протоколов
        protocol_numbers = sorted(set(r.protocol for r in records if r.protocol))
        if not protocol_numbers:
            QMessageBox.warning(self, "Ошибка", "Не найдены номера протоколов в записях")
            return

        # Диалог выбора номера протокола (с опцией "Все")
        choices = ["Все"] + protocol_numbers
        
        if len(choices) == 2:
            protocol_number = choices[0]  # "Все" или единственный
        else:
            protocol_number, ok = QInputDialog.getItem(
                self, "Номер протокола",
                "Выберите номер протокола:",
                choices, 0, False
            )
            if not ok or not protocol_number:
                return

        # Диалог сохранения с последним путем
        if protocol_number == "Все":
            default_file = "Протоколы.docx"
            # Проверяем путь - если "Протоколы", используем его
            if self.last_save_path and os.path.exists(self.last_save_path):
                if "Протоколы" in os.path.basename(self.last_save_path):
                    default_path = self.last_save_path
                else:
                    default_path = os.path.join(os.path.dirname(self.last_save_path), default_file)
            elif self.last_save_path and os.path.exists(os.path.dirname(self.last_save_path)):
                default_path = os.path.join(os.path.dirname(self.last_save_path), default_file)
            else:
                default_path = default_file
        else:
            # Определяем дату для этого протокола
            exam_date_str = ""
            proto_records = [r for r in records if r.protocol == protocol_number]
            for r in proto_records:
                if r.exam_date:
                    # Пытаемся преобразовать дату в формат ДД-ММ-ГГГГ
                    try:
                        from datetime import datetime
                        # Убираем время если есть
                        date_part = r.exam_date.split()[0] if ' ' in r.exam_date else r.exam_date
                        # Парсим дату
                        dt = datetime.strptime(date_part, "%d.%m.%Y")
                        exam_date_str = dt.strftime("%d-%m-%Y")
                    except:
                        # Если не удалось - просто убираем лишнее
                        exam_date_str = r.exam_date.replace('.', '-').split()[0]
                    break
            if exam_date_str:
                default_file = f"Протокол {protocol_number} от {exam_date_str}.docx"
            else:
                default_file = f"Протокол {protocol_number}.docx"
            
            # Проверяем путь - если номер совпадает, используем его
            if self.last_save_path and os.path.exists(self.last_save_path):
                basename = os.path.basename(self.last_save_path)
                if protocol_number in basename and "Протоколы" not in basename:
                    default_path = self.last_save_path
                else:
                    default_path = os.path.join(os.path.dirname(self.last_save_path), default_file)
            elif self.last_save_path and os.path.exists(os.path.dirname(self.last_save_path)):
                default_path = os.path.join(os.path.dirname(self.last_save_path), default_file)
            else:
                default_path = default_file
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить протокол",
            default_path,
            "Word Files (*.docx)"
        )
        if not file_path:
            return
        
        # Сохраняем путь
        self._save_last_save_path(file_path)

        from utils.app_paths import get_app_data_dir, get_resource_dir
        data_dir = get_app_data_dir()
        template_path = os.path.join(
            get_resource_dir(), "templates",
            "Protokol_proverki_znanii_OT.docx"
        )

        if protocol_number == "Все":
            # Генерируем все протоколы - каждый в отдельный файл
            # Выбираем директорию для сохранения
            save_dir = QFileDialog.getExistingDirectory(
                self, "Выберите папку для сохранения протоколов",
                os.path.dirname(file_path) if file_path else ""
            )
            if not save_dir:
                return
            
            saved_count = 0
            for proto_num in protocol_numbers:
                proto_records = [r for r in records if r.protocol == proto_num]
                if not proto_records:
                    continue
                
                # Формируем имя файла
                exam_date_str = ""
                for r in proto_records:
                    if r.exam_date:
                        try:
                            from datetime import datetime
                            date_part = r.exam_date.split()[0] if ' ' in r.exam_date else r.exam_date
                            for fmt in ["%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"]:
                                try:
                                    dt = datetime.strptime(date_part, fmt)
                                    exam_date_str = "_" + dt.strftime("%d-%m-%Y")
                                    break
                                except ValueError:
                                    continue
                        except ValueError:
                            pass
                        break
                
                output_file = os.path.join(save_dir, f"Протокол {proto_num}{exam_date_str}.docx")
                
                success, _ = ProtocolExporter.export_protocol(
                    records=proto_records,
                    output_path=output_file,
                    template_path=template_path,
                    data_dir=data_dir
                )
                
                if success:
                    saved_count += 1
            
            QMessageBox.information(self, "Успех", f"Сохранено протоколов: {saved_count}\nПапка: {save_dir}")
        else:
            # Один протокол
            selected_records = [r for r in records if r.protocol == protocol_number]

            if not selected_records:
                QMessageBox.warning(self, "Ошибка", "Нет данных для выбранного протокола")
                return

            success, msg = ProtocolExporter.export_protocol(
                records=selected_records,
                output_path=file_path,
                template_path=template_path,
                data_dir=data_dir
            )

            if success:
                QMessageBox.information(self, "Успех", msg)
            else:
                QMessageBox.warning(self, "Ошибка", msg)

    def _delete_selected(self):
        """Удаление выбранных записей."""
        selected_rows = set(item.row() for item in self.table.selectedIndexes())
        if not selected_rows:
            QMessageBox.information(self, "Информация", "Выберите записи для удаления")
            return

        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить выбранные записи ({len(selected_rows)} шт.)?\nДанные удалятся безвозвратно.",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
        )

        if reply == QMessageBox.StandardButton.Ok:
            # Удаляем из журнала (по UUID) через менеджер
            records_to_delete = []
            for row in selected_rows:
                uuid_item = self.table.item(row, 14)  # Скрытая колонка UUID
                if uuid_item:
                    records_to_delete.append(uuid_item.text())

            self.journal.delete_by_uuid(records_to_delete)
            self.refresh_journal()
            QMessageBox.information(self, "Успех", "Записи удалены")

    def _show_context_menu(self, position):
        """Контекстное меню для строки."""
        from PySide6.QtWidgets import QMenu

        # Проверяем есть ли выделенные строки
        if not self.table.selectedIndexes():
            # Если нет выделенных строк, выделяем строку под курсором
            item = self.table.itemAt(position)
            if item:
                self.table.selectRow(item.row())

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                color: inherit;
            }
            QMenu::item:selected {
                background-color: #4169E1;
                color: white;
            }
        """)
        delete_action = menu.addAction("Удалить")
        action = menu.exec(self.table.mapToGlobal(position))

        if action == delete_action:
            self._delete_selected()

    def add_records_to_journal(self, records_data, set_id, xml_file):
        """
        Публичный метод для добавления записей (вызывается из data_transfer_tab).
        """
        count = self.journal.add_records(records_data, set_id, xml_file)
        self.refresh_journal()
        return count

    def update_base_no(self, set_id, base_no_map):
        """
        Публичный метод для обновления baseNo (вызывается из data_transfer_tab).
        """
        count = self.journal.update_base_no_by_set_id(set_id, base_no_map)
        if count > 0:
            self.refresh_journal()
        return count
