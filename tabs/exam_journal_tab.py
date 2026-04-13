"""
Вкладка «Журнал проверки знаний»
Отображение истории отправок, поиск, фильтрация, экспорт, удаление
"""
import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QLineEdit, QComboBox, QHeaderView, QAbstractItemView,
    QMessageBox, QFileDialog, QDateEdit, QGroupBox, QFormLayout
)
from PyQt6.QtCore import Qt, QSortFilterProxyModel
from PyQt6.QtGui import QColor, QFont
from journal.journal_manager import JournalRecord


class ExamJournalTab(QWidget):
    def __init__(self, journal_manager):
        super().__init__()
        self.setStyleSheet("background-color: transparent;")
        self.journal = journal_manager

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
                background-color: white;
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
        search_label.setStyleSheet("color: black; font-weight: normal;")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Фамилия, Имя или СНИЛС")
        self.search_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        self.search_input.textChanged.connect(self._apply_filters)
        row1.addWidget(search_label)
        row1.addWidget(self.search_input)

        row1.addSpacing(15)

        # Фильтр по SetId
        setid_label = QLabel("SetId:")
        setid_label.setStyleSheet("color: black; font-weight: normal;")
        self.setid_combo = QComboBox()
        self.setid_combo.setMinimumWidth(250)
        self.setid_combo.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        self.setid_combo.addItem("Все")
        self.setid_combo.currentTextChanged.connect(self._apply_filters)
        row1.addWidget(setid_label)
        row1.addWidget(self.setid_combo)

        layout.addLayout(row1)

        # Строка 2: Статус + Даты
        row2 = QHBoxLayout()

        # Фильтр по статусу
        status_label = QLabel("Статус:")
        status_label.setStyleSheet("color: black; font-weight: normal;")
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Все", "ожидает", "получен"])
        self.status_combo.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        self.status_combo.currentTextChanged.connect(self._apply_filters)
        row2.addWidget(status_label)
        row2.addWidget(self.status_combo)

        row2.addSpacing(15)

        # Фильтр по дате (с)
        date_from_label = QLabel("Дата с:")
        date_from_label.setStyleSheet("color: black; font-weight: normal;")
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("dd.MM.yyyy")
        self.date_from.blockSignals(True)
        self.date_from.setDate(self.date_from.minimumDate())
        self.date_from.blockSignals(False)
        self.date_from.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        self.date_from.dateChanged.connect(self._apply_filters)
        row2.addWidget(date_from_label)
        row2.addWidget(self.date_from)

        row2.addSpacing(15)

        # Фильтр по дате (по)
        date_to_label = QLabel("Дата по:")
        date_to_label.setStyleSheet("color: black; font-weight: normal;")
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("dd.MM.yyyy")
        self.date_to.blockSignals(True)
        self.date_to.setDate(self.date_to.maximumDate())
        self.date_to.blockSignals(False)
        self.date_to.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
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
                background-color: #3151B1;
            }
        """)
        self.export_btn.clicked.connect(self._export_to_xlsx)
        layout.addWidget(self.export_btn)

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
        table.setColumnCount(14)
        table.setHorizontalHeaderLabels([
            "Дата отправки", "SetId", "Фамилия", "Имя", "Отчество", "СНИЛС",
            "Должность", "№ программы", "Название программы", "Дата экзамена",
            "№ протокола", "Рег. номер", "Статус", ""
        ])

        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        table.verticalHeader().setDefaultSectionSize(25)

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
                border: none;
                font-weight: bold;
            }
        """)

        # Ширина колонок
        table.setColumnWidth(0, 140)   # Дата отправки
        table.setColumnWidth(1, 280)   # SetId
        table.setColumnWidth(2, 120)   # Фамилия
        table.setColumnWidth(3, 100)   # Имя
        table.setColumnWidth(4, 120)   # Отчество
        table.setColumnWidth(5, 130)   # СНИЛС
        table.setColumnWidth(6, 150)   # Должность
        table.setColumnWidth(7, 80)    # № программы
        table.setColumnWidth(8, 350)   # Название программы
        table.setColumnWidth(9, 100)   # Дата экзамена
        table.setColumnWidth(10, 100)  # № протокола
        table.setColumnWidth(11, 130)  # Рег. номер
        table.setColumnWidth(12, 80)   # Статус
        table.hideColumn(13)           # Скрытый UUID

        return table

    # ============ Обновление данных ============

    def refresh_journal(self):
        """Обновление таблицы из журнала."""
        self.table.setRowCount(0)

        filtered = self._get_filtered_records()

        for row_idx, record in enumerate(filtered):
            self.table.insertRow(row_idx)

            items = [
                record.send_date,
                record.set_id,
                record.last_name,
                record.first_name,
                record.middle_name,
                record.snils,
                record.position,
                record.program_id,
                record.program_title,
                record.exam_date,
                record.protocol,
                record.base_no,
                "получен" if record.status == "received" else "ожидает",
                record.uuid  # Скрытая колонка
            ]

            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                # Цветовая индикация статуса
                if col == 12:
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

    def _get_filtered_records(self):
        """Получение отфильтрованных записей."""
        query = self.search_input.text()
        set_id = self.setid_combo.currentText()
        if set_id == "Все":
            set_id = ""
        status_map = {"Все": "all", "ожидает": "pending", "получен": "received"}
        status = status_map.get(self.status_combo.currentText(), "all")

        # Проверяем, установлены ли фильтры дат
        date_from = ""
        date_to = ""

        self.date_from.blockSignals(True)
        self.date_to.blockSignals(True)
        try:
            if self.date_from.date() > self.date_from.minimumDate():
                date_from = self.date_from.date().toString("dd.MM.yyyy")
            if self.date_to.date() < self.date_to.maximumDate():
                date_to = self.date_to.date().toString("dd.MM.yyyy")
        finally:
            self.date_from.blockSignals(False)
            self.date_to.blockSignals(False)

        return self.journal.search(
            query=query, set_id=set_id,
            status=status, date_from=date_from, date_to=date_to
        )

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

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить XLSX", "Журнал_проверки_знаний.xlsx",
            "Excel Files (*.xlsx)"
        )
        if not file_path:
            return

        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "Журнал"

            headers = [
                "Дата отправки", "SetId", "Фамилия", "Имя", "Отчество", "СНИЛС",
                "Должность", "№ программы", "Название программы", "Дата экзамена",
                "№ протокола", "Рег. номер", "Статус"
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
                ws.append([
                    rec.send_date, rec.set_id, rec.last_name, rec.first_name,
                    rec.middle_name, rec.snils, rec.position, rec.program_id,
                    rec.program_title, rec.exam_date, rec.protocol,
                    rec.base_no,
                    "получен" if rec.status == "received" else "ожидает"
                ])

            # Автоширина
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

    def _print_protocol(self):
        """Печать протокола — вызов диалога выбора."""
        from exporters.protocol_exporter import ProtocolExporter

        records = self._get_filtered_records()
        if not records:
            QMessageBox.information(self, "Информация", "Нет данных для формирования протокола")
            return

        # Группировка по SetId для выбора
        set_ids = list(dict.fromkeys(r.set_id for r in records))
        if not set_ids:
            QMessageBox.warning(self, "Ошибка", "Не удалось определить SetId для записей")
            return

        # Используем первый SetId из отфильтрованных
        selected_set_id = set_ids[0]
        selected_records = [r for r in records if r.set_id == selected_set_id]

        if not selected_records:
            QMessageBox.warning(self, "Ошибка", "Нет данных для выбранного SetId")
            return

        # Экспорт протокола
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить протокол",
            f"Протокол_{selected_records[0].protocol}.xlsx",
            "Excel Files (*.xlsx)"
        )
        if not file_path:
            return

        success, msg = ProtocolExporter.export_protocol(
            records=selected_records,
            output_path=file_path,
            template_path=os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "Protokol_proverki_znanii_OT.xlsx"
            ),
            data_dir=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
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
                uuid_item = self.table.item(row, 13)  # Скрытая колонка UUID
                if uuid_item:
                    records_to_delete.append(uuid_item.text())

            self.journal.delete_by_uuid(records_to_delete)
            self.refresh_journal()
            QMessageBox.information(self, "Успех", "Записи удалены")

    def _show_context_menu(self, position):
        """Контекстное меню для строки."""
        from PyQt6.QtWidgets import QMenu

        menu = QMenu(self)
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
