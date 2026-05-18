import os
import json
import time
import logging
import threading
from datetime import datetime, date
from typing import List, Optional
from dateutil.relativedelta import relativedelta

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QScrollArea,
    QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QFrame, QDialog, QCheckBox,
    QGridLayout
)
from PySide6.QtCore import Qt, QThread, Signal, QDate
from PySide6.QtGui import QColor, QBrush

from db import (
    DatabaseManager, EmployeesRepo, EmployeeProgramsRepo
)
from api.mintrud_api import load_api_key, get_by_snils
from utils.proxy_manager import load_proxy_settings

logger = logging.getLogger(__name__)

VALID_PROGRAMS = [str(i) for i in range(1, 30) if i != 5]
DEFAULT_PROGRAMS = ["1", "2", "3", "4", "18", "23"]

PROGRAM_TITLES = {
    "1": "Оказание первой помощи пострадавшим",
    "2": "Использование СИЗ",
    "3": "Общие вопросы охраны труда",
    "4": "Безопасные методы при воздействии вредных факторов",
    "6": "Земляные работы",
    "7": "Ремонтные и монтажные работы",
    "8": "Работы с технологическим оборудованием",
    "9": "Работы на высоте",
    "10": "Пожароопасные работы",
    "11": "Работы в ОЗП",
    "12": "Строительные работы",
    "13": "Работы с сильнодействующими веществами",
    "14": "Газоопасные работы",
    "15": "Огневые работы",
    "16": "Эксплуатация подъемных сооружений",
    "17": "Эксплуатация тепловых энергоустановок",
    "18": "Работы в электроустановках",
    "19": "Эксплуатация сосудов под давлением",
    "20": "Обращение с животными",
    "21": "Водолазные работы",
    "22": "Работы с взрывоопасными предметами",
    "23": "Работы вблизи автодорог и ЖД",
    "24": "Работы с патогенным заражением почвы",
    "25": "Валка леса",
    "26": "Перемещение тяжеловесных грузов",
    "27": "Работы с радиоактивными веществами",
    "28": "Работы с ручным инструментом",
    "29": "Работы в театрах",
}

BASE_COLUMNS = 3  # ФИО, СНИЛС, Должность (hidden employee_id — в конце)
SUB_COLUMNS = 4   # Потребность, Дата, Протокол, Рег.номер


class ApiQueryThread(QThread):
    finished = Signal(int, int)
    error_signal = Signal(str)
    progress = Signal(int, int)

    def __init__(self, employees, api_key, proxy_settings=None):
        super().__init__()
        self.employees = employees
        self.api_key = api_key
        self.proxy_settings = proxy_settings or {}

    def run(self):
        total = len(self.employees)
        updated = 0
        errors = 0
        for idx, emp in enumerate(self.employees):
            try:
                snils_clean = emp['snils'].replace('-', '').replace(' ', '')
                result = get_by_snils(self.api_key, snils_clean, proxy_settings=self.proxy_settings)
                if result.get("success"):
                    records = result.get("records", [])
                    self._process_api_records(emp['id'], records)
                    updated += 1
                    now = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
                    EmployeesRepo.update_sync(emp['id'], now)
                else:
                    errors += 1
                    logger.warning(f"API error for SNILS {snils_clean}: {result.get('error')}")
            except Exception as e:
                errors += 1
                logger.error(f"Exception for SNILS: {e}")
            self.progress.emit(idx + 1, total)
            if idx < total - 1:
                time.sleep(0.5)
        self.finished.emit(updated, errors)

    def _process_api_records(self, employee_id, records):
        seen_programs = {}
        for rec in records:
            prog_id = rec.get('learnProgramId', '')
            if not prog_id:
                continue
            exam_date = rec.get('Date', '')
            protocol = rec.get('ProtocolNumber', '')
            base_no = rec.get('baseNo', '')
            is_passed = rec.get('isPassed', '')
            result = 1 if is_passed and is_passed.lower() in ('true', '1', 'да', 'удовлетворительно') else 0

            if prog_id not in seen_programs or (exam_date and exam_date > seen_programs[prog_id].get('exam_date', '')):
                seen_programs[prog_id] = {
                    'exam_date': exam_date,
                    'protocol': protocol,
                    'base_no': base_no,
                    'result': result,
                }

        for prog_id, data in seen_programs.items():
            try:
                EmployeeProgramsRepo.update_from_api(
                    employee_id, int(prog_id),
                    data['exam_date'], data['protocol'],
                    data['base_no'], data['result']
                )
            except (ValueError, TypeError):
                pass


class PlanDialog(QDialog):
    def __init__(self, plan_data, plan_title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(plan_title)
        self.setMinimumSize(900, 600)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("PlanDialog { background-color: white; }")

        layout = QVBoxLayout(self)

        stats_layout = QHBoxLayout()
        total = len(plan_data)
        high = sum(1 for p in plan_data if p['priority'] == 'Высокий')
        medium = sum(1 for p in plan_data if p['priority'] == 'Средний')
        low = sum(1 for p in plan_data if p['priority'] == 'Низкий')

        for label, value, color in [
            ("Всего в плане", str(total), "#4169E1"),
            ("Высокий", str(high), "#dc3545"),
            ("Средний", str(medium), "#ffc107"),
            ("Низкий", str(low), "#28a745"),
        ]:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    border: 2px solid {color};
                    border-radius: 8px;
                    padding: 10px;
                    background-color: #f8f9fa;
                }}
            """)
            card_layout = QVBoxLayout(card)
            val_label = QLabel(value)
            val_label.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {color};")
            val_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            desc_label = QLabel(label)
            desc_label.setStyleSheet("font-size: 12px; color: #666;")
            desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(val_label)
            card_layout.addWidget(desc_label)
            stats_layout.addWidget(card)
        layout.addLayout(stats_layout)

        table = QTableWidget()
        table.setColumnCount(9)
        table.setHorizontalHeaderLabels([
            "№", "ФИО", "СНИЛС", "Должность", "Программа",
            "Последняя дата обучения", "Дата окончания действия",
            "Основание", "Приоритет"
        ])
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)

        for i, p in enumerate(plan_data, 1):
            row = table.rowCount()
            table.insertRow(row)
            items = [
                str(i),
                f"{p['last_name']} {p['first_name']} {p['middle_name']}".strip(),
                p['snils'],
                p['position'],
                p['program'],
                p['last_exam_date'],
                p['expiry_date'],
                p['reason'],
                p['priority'],
            ]
            for col, text in enumerate(items):
                item = QTableWidgetItem(str(text))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col == 8:
                    color_map = {'Высокий': '#dc3545', 'Средний': '#ffc107', 'Низкий': '#28a745'}
                    item.setForeground(QColor(color_map.get(text, '#000')))
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                table.setItem(row, col, item)

        layout.addWidget(table)

        btn_layout = QHBoxLayout()
        export_btn = QPushButton("Экспорт XLSX")
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: #4169E1; color: white; border: none;
                padding: 8px 16px; border-radius: 5px; font-weight: bold;
            }
            QPushButton:hover { background-color: #3151B1; }
        """)
        export_btn.clicked.connect(lambda: self._export_plan(plan_data, plan_title))
        close_btn = QPushButton("Закрыть")
        close_btn.setStyleSheet("""
            QPushButton {
                color: red; border: 2px solid red; padding: 8px 16px;
                border-radius: 5px; font-weight: bold; background-color: white;
            }
            QPushButton:hover { background-color: #FFE0E0; }
        """)
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(export_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _export_plan(self, plan_data, plan_title):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить XLSX",
            f"{plan_title}.xlsx",
            "Excel Files (*.xlsx)"
        )
        if not file_path:
            return
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment

            wb = Workbook()
            ws = wb.active
            ws.title = "План"

            headers = [
                "№", "ФИО", "СНИЛС", "Должность", "Программа",
                "Последняя дата обучения", "Дата окончания действия",
                "Основание", "Приоритет"
            ]
            ws.append(headers)
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="4169E1", end_color="4169E1", fill_type="solid")
            for cell in ws[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center")

            for i, p in enumerate(plan_data, 1):
                ws.append([
                    i,
                    f"{p['last_name']} {p['first_name']} {p['middle_name']}".strip(),
                    p['snils'], p['position'], p['program'],
                    p['last_exam_date'], p['expiry_date'],
                    p['reason'], p['priority'],
                ])

            ws2 = wb.create_sheet("Сводка")
            ws2.append(["Программа", "Кол-во"])
            from collections import Counter
            prog_counts = Counter(p['program'] for p in plan_data)
            for prog, cnt in sorted(prog_counts.items()):
                ws2.append([prog, cnt])
            for cell in ws2[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center")

            wb.save(file_path)
            QMessageBox.information(self, "Успех", f"Файл сохранён:\n{file_path}")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка экспорта: {e}")


class EmployeeSummaryTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: transparent;")
        self._selected_programs = DEFAULT_PROGRAMS.copy()
        self._current_filter_status = "all"
        self._current_filter_program = "all"
        self._current_filter_position = ""
        self._problem_only = False
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(self.base_dir, "data")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background-color: transparent; border: none;")

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(10)

        scroll_layout.addWidget(self._create_stats_panel())
        scroll_layout.addWidget(self._create_manual_entry_group())
        scroll_layout.addWidget(self._create_action_buttons())
        scroll_layout.addWidget(self._create_filter_panel())
        scroll_layout.addWidget(self._create_plan_buttons())
        scroll_layout.addWidget(self._create_table())
        scroll_layout.addStretch()

        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)

        self.refresh_table()

    def _btn_style(self, bg="#4169E1", hover="#3151B1"):
        return f"""
            QPushButton {{
                background-color: {bg}; color: white; border: none;
                padding: 8px 16px; border-radius: 5px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {hover}; }}
        """

    def _group_style(self):
        return """
            QGroupBox {
                border: 2px solid #4169E1; border-radius: 10px;
                margin-top: 10px; padding: 15px; background-color: white;
            }
            QGroupBox::title {
                color: #4169E1; font-weight: bold; font-size: 14px;
                subcontrol-origin: margin; left: 10px; padding: 0 5px;
            }
        """

    def _create_stats_panel(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.stats_cards = []
        stat_defs = [
            ("Всего сотрудников", "0", "#4169E1"),
            ("Всего записей", "0", "#6c757d"),
            ("Обучено", "0", "#28a745"),
            ("Не обучено", "0", "#dc3545"),
            ("Просрочено", "0", "#ffc107"),
            ("Актуальность данных", "нет", "#17a2b8"),
        ]

        for label, default, color in stat_defs:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    border: 2px solid {color};
                    border-radius: 8px;
                    padding: 8px;
                    background-color: #f8f9fa;
                }}
            """)
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(2)

            val_label = QLabel(default)
            val_label.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {color};")
            val_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(val_label)

            desc_label = QLabel(label)
            desc_label.setStyleSheet("font-size: 11px; color: #666;")
            desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(desc_label)

            self.stats_cards.append(val_label)
            layout.addWidget(card)

        return widget

    def _create_manual_entry_group(self):
        group = QGroupBox()
        group.setStyleSheet(self._group_style())
        group.setTitle("Ручной ввод данных работника")

        layout = QHBoxLayout(group)
        layout.setSpacing(15)

        form = QFormLayout()
        form.setSpacing(8)

        self.me_last_name = QLineEdit()
        self.me_last_name.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        form.addRow("Фамилия:", self.me_last_name)

        self.me_first_name = QLineEdit()
        self.me_first_name.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        form.addRow("Имя:", self.me_first_name)

        self.me_middle_name = QLineEdit()
        self.me_middle_name.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        form.addRow("Отчество:", self.me_middle_name)

        self.me_snils = QLineEdit()
        self.me_snils.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        self.me_snils.setPlaceholderText("123-456-789 00")
        form.addRow("СНИЛС:", self.me_snils)

        layout.addLayout(form)

        form2 = QFormLayout()
        form2.setSpacing(8)

        self.me_position = QLineEdit()
        self.me_position.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        form2.addRow("Должность:", self.me_position)

        prog_row = QHBoxLayout()
        self.me_program = QLineEdit()
        self.me_program.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        self.me_program.setPlaceholderText("1,2,3")
        help_btn = QPushButton("Справка")
        help_btn.setStyleSheet(self._btn_style())
        help_btn.clicked.connect(self._show_programs_help)
        prog_row.addWidget(self.me_program)
        prog_row.addWidget(help_btn)
        form2.addRow("Программы:", prog_row)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Добавить запись")
        add_btn.setStyleSheet(self._btn_style())
        add_btn.clicked.connect(self._add_manual_entry)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setStyleSheet("""
            QPushButton {
                color: red; border: 2px solid red; padding: 8px 16px;
                border-radius: 5px; font-weight: bold; background-color: white;
            }
            QPushButton:hover { background-color: #FFE0E0; }
        """)
        cancel_btn.clicked.connect(self._clear_manual_entry)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(cancel_btn)
        form2.addRow("", btn_layout)

        layout.addLayout(form2)
        return group

    def _create_action_buttons(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 5, 0, 5)

        self.import_btn = QPushButton("Импорт .xlsx")
        self.import_btn.setStyleSheet(self._btn_style())
        self.import_btn.clicked.connect(self._import_xlsx)
        layout.addWidget(self.import_btn)

        self.export_btn = QPushButton("Экспорт .xlsx")
        self.export_btn.setStyleSheet(self._btn_style())
        self.export_btn.clicked.connect(lambda: self._export_xlsx(filtered=True))
        layout.addWidget(self.export_btn)

        self.export_all_btn = QPushButton("Экспорт .xlsx (все)")
        self.export_all_btn.setStyleSheet(self._btn_style())
        self.export_all_btn.clicked.connect(lambda: self._export_xlsx(filtered=False))
        layout.addWidget(self.export_all_btn)

        self.query_btn = QPushButton("Запросить из реестра")
        self.query_btn.setStyleSheet(self._btn_style(bg="#28a745", hover="#218838"))
        self.query_btn.clicked.connect(self._query_reestr)
        layout.addWidget(self.query_btn)

        self.refresh_btn = QPushButton("Обновить данные")
        self.refresh_btn.setStyleSheet(self._btn_style(bg="#ffc107", hover="#e0a800"))
        self.refresh_btn.clicked.connect(self.refresh_table)
        layout.addWidget(self.refresh_btn)

        layout.addStretch()
        # Кнопка выбора столбцов программ
        self.program_selector_btn = QPushButton("Выбрать программы")
        self.program_selector_btn.setStyleSheet(self._btn_style(bg="#6f42c1", hover="#5a32a3"))
        self.program_selector_btn.clicked.connect(self._show_program_selector)
        layout.addWidget(self.program_selector_btn)
        return widget

    def _create_filter_panel(self):
        group = QGroupBox()
        group.setStyleSheet(self._group_style())
        group.setTitle("Фильтры")

        layout = QHBoxLayout(group)
        layout.setSpacing(15)

        layout.addWidget(QLabel("Статус:"))
        self.filter_status = QComboBox()
        self.filter_status.addItems(["Все", "Обучен", "Не обучен", "Просрочено"])
        self.filter_status.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        self.filter_status.currentIndexChanged.connect(self._apply_filters)
        layout.addWidget(self.filter_status)

        layout.addWidget(QLabel("Должность:"))
        self.filter_position = QLineEdit()
        self.filter_position.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        self.filter_position.setPlaceholderText("Фильтр по должности")
        self.filter_position.textChanged.connect(self._apply_filters)
        layout.addWidget(self.filter_position)

        self.problem_cb = QCheckBox("Только проблемные")
        self.problem_cb.setStyleSheet("color: black;")
        self.problem_cb.toggled.connect(self._apply_filters)
        layout.addWidget(self.problem_cb)

        return group

    def _create_plan_buttons(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 5, 0, 5)

        self.plan_current_btn = QPushButton("Сформировать план на текущий год")
        self.plan_current_btn.setStyleSheet(self._btn_style())
        self.plan_current_btn.clicked.connect(lambda: self._generate_plan(current_year=True))
        layout.addWidget(self.plan_current_btn)

        self.plan_next_btn = QPushButton("Сформировать план на следующий год")
        self.plan_next_btn.setStyleSheet(self._btn_style())
        self.plan_next_btn.clicked.connect(lambda: self._generate_plan(current_year=False))
        layout.addWidget(self.plan_next_btn)

        layout.addStretch()
        return widget

    def _show_program_selector(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Выбор программ для отображения")
        dialog.setMinimumSize(500, 500)
        dialog.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        dialog.setStyleSheet("QDialog { background-color: white; }")

        from PySide6.QtWidgets import QListWidget, QListWidgetItem

        list_widget = QListWidget()
        list_widget.setStyleSheet("""
            QListWidget { border: 1px solid #CCCCCC; background-color: white; }
            QListWidget::item { padding: 6px; }
        """)

        selected = set(self._selected_programs)
        for p in VALID_PROGRAMS:
            item = QListWidgetItem(f"{p}: {PROGRAM_TITLES.get(p, '')}")
            item.setData(Qt.ItemDataRole.UserRole, p)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if p in selected else Qt.CheckState.Unchecked)
            list_widget.addItem(item)

        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Отметьте программы для отображения (макс. 6):"))
        layout.addWidget(list_widget)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("Применить")
        ok_btn.setStyleSheet(self._btn_style())
        ok_btn.clicked.connect(lambda: self._apply_program_selection(list_widget, dialog))
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setStyleSheet("""
            QPushButton {
                color: red; border: 2px solid red; padding: 8px 16px;
                border-radius: 5px; font-weight: bold; background-color: white;
            }
            QPushButton:hover { background-color: #FFE0E0; }
        """)
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        dialog.exec()

    def _apply_program_selection(self, list_widget, dialog):
        checked = []
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                checked.append(item.data(Qt.ItemDataRole.UserRole))
        if not checked:
            QMessageBox.warning(self, "Ошибка", "Выберите хотя бы одну программу")
            return
        if len(checked) > 6:
            QMessageBox.warning(self, "Ошибка", "Максимум 6 программ одновременно")
            return
        self._selected_programs = checked
        dialog.accept()
        self.refresh_table()

    def _create_table(self):
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.verticalHeader().setDefaultSectionSize(25)
        self.table.verticalHeader().setVisible(False)
        self.table.setSortingEnabled(True)

        self.table.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                background-color: #4169E1; color: white; padding: 5px;
                border: 1px solid #3050C0; font-weight: bold;
            }
        """)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: white; border: 2px solid #4169E1;
                border-radius: 5px; gridline-color: #E0E0E0;
            }
            QTableWidget::item { padding: 5px; }
        """)

        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        self.table.itemDoubleClicked.connect(self._on_item_double_click)

        return self.table

    def refresh_table(self):
        employees = EmployeesRepo.get_all()
        self._build_table(employees)
        self._update_stats()

    def _build_table(self, employees: List[dict]):
        self.table.setSortingEnabled(False)
        self.table.clear()
        self.table.setRowCount(0)

        programs = self._selected_programs[:6]
        num_prog_cols = len(programs) * SUB_COLUMNS
        num_cols = BASE_COLUMNS + num_prog_cols + 1  # +1 hidden emp_id
        HEADER_ROWS = 2

        self.table.setColumnCount(num_cols)

        header_font = self.font()
        header_font.setBold(True)

        # Row 0: program group headers
        self.table.insertRow(0)
        for c in range(BASE_COLUMNS - 1):  # ФИО, СНИЛС, Должность
            item = QTableWidgetItem(["ФИО", "СНИЛС", "Должность"][c])
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            item.setBackground(QColor("#4169E1"))
            item.setForeground(QColor("white"))
            item.setFont(header_font)
            self.table.setItem(0, c, item)
            self.table.setSpan(0, c, HEADER_ROWS, 1)

        for pi, p in enumerate(programs):
            col = BASE_COLUMNS + pi * SUB_COLUMNS
            item = QTableWidgetItem(f"№{p}: {PROGRAM_TITLES.get(p, '')}")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            item.setBackground(QColor("#4169E1"))
            item.setForeground(QColor("white"))
            item.setFont(header_font)
            self.table.setItem(0, col, item)
            self.table.setSpan(0, col, 1, SUB_COLUMNS)

        # empty cell at end of row 0
        item = QTableWidgetItem("")
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        self.table.setItem(0, num_cols - 1, item)
        self.table.setSpan(0, num_cols - 1, HEADER_ROWS, 1)

        # Row 1: sub-headers
        self.table.insertRow(1)
        for c in range(BASE_COLUMNS - 1):
            item = QTableWidgetItem("")
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(1, c, item)

        sub_labels = ["Потребность", "Дата", "Протокол", "Рег.№"]
        sub_font = self.font()
        sub_font.setBold(True)
        for pi, p in enumerate(programs):
            col = BASE_COLUMNS + pi * SUB_COLUMNS
            for j, label in enumerate(sub_labels):
                item = QTableWidgetItem(label)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                item.setBackground(QColor("#4169E1"))
                item.setForeground(QColor("white"))
                item.setFont(sub_font)
                self.table.setItem(1, col + j, item)

        # Row height for headers
        self.table.setRowHeight(0, 35)
        self.table.setRowHeight(1, 30)

        # Filters
        status_filter = self.filter_status.currentText()
        pos_filter = self.filter_position.text().strip().lower()
        problem_only = self.problem_cb.isChecked()

        for emp in employees:
            if pos_filter:
                emp_pos = emp['position'].lower()
                if pos_filter not in emp_pos:
                    continue

            progs = EmployeeProgramsRepo.get_by_employee(emp['id'])
            prog_map = {str(p['program_id']): p for p in progs}

            row_programs = {}
            overall_status = None
            for p in programs:
                pd = prog_map.get(p)
                if not pd or pd.get('need_training') != 1:
                    row_programs[p] = {'need_training': 0, 'exam_date': '', 'protocol': '', 'base_no': '', 'status': ''}
                    continue
                s = pd.get('status', 'not_trained')
                row_programs[p] = {
                    'need_training': pd.get('need_training', 0),
                    'exam_date': pd.get('exam_date', ''),
                    'protocol': pd.get('protocol', ''),
                    'base_no': pd.get('base_no', ''),
                    'status': s,
                }
                if s == 'trained':
                    overall_status = 'trained'
                elif s == 'expired' and overall_status != 'trained':
                    overall_status = 'expired'
                elif s == 'not_trained' and overall_status not in ('trained', 'expired'):
                    overall_status = 'not_trained'

            if status_filter != "Все":
                status_map = {"Обучен": "trained", "Не обучен": "not_trained", "Просрочено": "expired"}
                mapped = status_map.get(status_filter, "")
                if overall_status != mapped:
                    continue

            if problem_only and overall_status in (None, 'trained'):
                continue

            row_idx = self.table.rowCount()
            self.table.insertRow(row_idx)

            fio = f"{emp['last_name']} {emp['first_name']} {emp['middle_name']}".strip()
            row_data = [fio, emp['snils'], emp['position']]

            for p in programs:
                pd = row_programs.get(p, {})
                need = pd.get('need_training', 0)
                need_text = "Да" if need == 1 else "Нет"
                row_data.extend([
                    need_text,
                    pd.get('exam_date', ''),
                    pd.get('protocol', ''),
                    pd.get('base_no', ''),
                ])

            col_idx = 0
            for val in row_data:
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row_idx, col_idx, item)
                col_idx += 1

            emp_id_item = QTableWidgetItem(str(emp['id']))
            self.table.setItem(row_idx, col_idx, emp_id_item)
            self.table.item(row_idx, col_idx).setData(Qt.ItemDataRole.UserRole, emp['id'])

            for pi, p in enumerate(programs):
                pd = row_programs.get(p, {})
                s = pd.get('status', '')
                if pd.get('need_training') != 1:
                    continue
                col_start = BASE_COLUMNS + pi * SUB_COLUMNS
                if s == 'trained':
                    color = QColor("#d4edda")
                elif s == 'expired':
                    color = QColor("#fff3cd")
                else:
                    color = QColor("#f8d7da")

                for sub in range(SUB_COLUMNS):
                    ci = col_start + sub
                    it = self.table.item(row_idx, ci)
                    if it:
                        it.setBackground(color)

        self.table.setSortingEnabled(True)

    def _update_stats(self):
        emp_count = EmployeesRepo.count()
        self.stats_cards[0].setText(str(emp_count))

        counts = EmployeeProgramsRepo.get_status_counts()
        total_records = sum(counts.values())
        self.stats_cards[1].setText(str(total_records))
        self.stats_cards[2].setText(str(counts.get('trained', 0)))
        self.stats_cards[3].setText(str(counts.get('not_trained', 0)))
        self.stats_cards[4].setText(str(counts.get('expired', 0)))

        last_sync = ""
        rows = DatabaseManager.get_instance().fetchone(
            "SELECT MAX(last_sync) as ls FROM employees WHERE last_sync IS NOT NULL"
        )
        if rows and rows['ls']:
            last_sync = rows['ls']
        self.stats_cards[5].setText(last_sync or "нет")

    def _apply_filters(self):
        self.refresh_table()

    def _show_context_menu(self, position):
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: white; color: black; border: 1px solid #CCCCCC; }
            QMenu::item:selected { background-color: #4169E1; color: white; }
        """)

        query_action = menu.addAction("Запросить из реестра")
        delete_action = menu.addAction("Удалить")

        action = menu.exec(self.table.mapToGlobal(position))
        row = self.table.currentRow()
        if row < 2:  # skip header rows
            return
        emp_id = self.table.item(row, self.table.columnCount() - 1).data(Qt.ItemDataRole.UserRole)

        if action == query_action:
            if emp_id:
                self._query_single(emp_id)
        elif action == delete_action:
            if emp_id:
                reply = QMessageBox.question(
                    self, "Подтверждение",
                    "Удалить сотрудника из сводки?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    EmployeesRepo.delete(emp_id)
                    self.refresh_table()

    def _on_item_double_click(self, item):
        if not item:
            return
        row = item.row()
        if row < 2:  # skip header rows
            return
        col = item.column()
        hidden_idx = self.table.columnCount() - 1

        programs = self._selected_programs[:6]
        for pi, p in enumerate(programs):
            col_start = BASE_COLUMNS + pi * SUB_COLUMNS
            if col == col_start:
                emp_id = self.table.item(row, hidden_idx).data(Qt.ItemDataRole.UserRole)
                current = self.table.item(row, col).text() if self.table.item(row, col) else "Нет"
                new_val = "Да" if current != "Да" else "Нет"
                need = 1 if new_val == "Да" else 0
                EmployeeProgramsRepo.update_need_training(emp_id, int(p), need)
                self.refresh_table()
                return

    def _add_manual_entry(self):
        last_name = self.me_last_name.text().strip()
        first_name = self.me_first_name.text().strip()
        middle_name = self.me_middle_name.text().strip()
        snils = self.me_snils.text().strip()
        position = self.me_position.text().strip()
        programs_str = self.me_program.text().strip()

        if not all([last_name, first_name, snils]):
            QMessageBox.warning(self, "Ошибка", "Заполните Фамилию, СНИЛС")
            return

        snils_clean = snils.replace('-', '').replace(' ', '')
        if not snils_clean.isdigit() or len(snils_clean) != 11:
            QMessageBox.warning(self, "Ошибка", "СНИЛС должен содержать 11 цифр")
            return

        snils_fmt = f"{snils_clean[:3]}-{snils_clean[3:6]}-{snils_clean[6:9]} {snils_clean[9:]}"

        programs = [p.strip() for p in programs_str.split(',') if p.strip() and p.strip() in VALID_PROGRAMS]

        emp_data = {
            'snils': snils_fmt,
            'last_name': last_name,
            'first_name': first_name,
            'middle_name': middle_name,
            'position': position,
            'required_programs': ';'.join(programs),
        }
        emp_id = EmployeesRepo.upsert(emp_data)

        for p in programs:
            EmployeeProgramsRepo.upsert(emp_id, {'program_id': int(p), 'need_training': 1})

        self._clear_manual_entry()
        self.refresh_table()
        QMessageBox.information(self, "Успех", "Сотрудник добавлен")

    def _clear_manual_entry(self):
        for w in [self.me_last_name, self.me_first_name, self.me_middle_name,
                  self.me_snils, self.me_position, self.me_program]:
            w.clear()

    def _show_programs_help(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Программы обучения")
        dialog.setMinimumSize(650, 700)
        layout = QVBoxLayout(dialog)

        from PySide6.QtWidgets import QListWidget, QListWidgetItem
        list_widget = QListWidget()
        list_widget.setStyleSheet("""
            QListWidget { border: 1px solid #CCCCCC; background-color: white; }
            QListWidget::item { padding: 5px; }
        """)

        blue_set = {"1", "2", "3", "4", "18", "23"}
        for num in VALID_PROGRAMS:
            title = PROGRAM_TITLES.get(num, "")
            item = QListWidgetItem(f"{num}: {title}")
            item.setData(Qt.ItemDataRole.UserRole, num)
            if num in blue_set:
                item.setForeground(QColor("#4169E1"))
            list_widget.addItem(item)

        layout.addWidget(list_widget)

        btn_layout = QHBoxLayout()
        close_btn = QPushButton("Закрыть")
        close_btn.setStyleSheet(self._btn_style())
        close_btn.clicked.connect(dialog.close)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        def on_double_click(item):
            num = item.data(Qt.ItemDataRole.UserRole)
            current = self.me_program.text().strip()
            programs = [p.strip() for p in current.split(',') if p.strip()]
            if num not in programs:
                programs.append(num)
            self.me_program.setText(','.join(programs))

        list_widget.itemDoubleClicked.connect(on_double_click)
        dialog.exec()

    def _import_xlsx(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите XLSX файл", "", "Excel Files (*.xlsx)"
        )
        if not file_path:
            return
        try:
            from openpyxl import load_workbook
            wb = load_workbook(file_path, data_only=True)
            ws = wb.active

            headers = [str(ws.cell(row=1, column=c).value).strip() for c in range(1, ws.max_column + 1)]
            col_map = {h: i for i, h in enumerate(headers)}

            if 'СНИЛС' not in col_map:
                QMessageBox.warning(self, "Ошибка", "Не найден столбец 'СНИЛС'")
                return

            snils_col = col_map['СНИЛС']
            last_name_col = col_map.get('Фамилия')
            first_name_col = col_map.get('Имя')
            middle_name_col = col_map.get('Отчество')
            position_col = col_map.get('Должность')

            program_cols = {}
            for p in VALID_PROGRAMS:
                need_key = f"программа #{p} Потребность"
                if need_key in col_map:
                    program_cols[p] = col_map[need_key]

            hidden_col = col_map.get('Потребность в обучении по программам')

            imported = 0
            for row_num in range(2, ws.max_row + 1):
                snils_raw = str(ws.cell(row=row_num, column=snils_col + 1).value or '').strip()
                if not snils_raw:
                    continue

                snils_clean = snils_raw.replace('-', '').replace(' ', '')
                if not snils_clean.isdigit() or len(snils_clean) != 11:
                    continue
                snils_fmt = f"{snils_clean[:3]}-{snils_clean[3:6]}-{snils_clean[6:9]} {snils_clean[9:]}"

                last_name = str(ws.cell(row=row_num, column=(last_name_col or 0) + 1).value or '').strip() if last_name_col else ''
                first_name = str(ws.cell(row=row_num, column=(first_name_col or 0) + 1).value or '').strip() if first_name_col else ''
                middle_name = str(ws.cell(row=row_num, column=(middle_name_col or 0) + 1).value or '').strip() if middle_name_col else ''
                position = str(ws.cell(row=row_num, column=(position_col or 0) + 1).value or '').strip() if position_col else ''

                required_programs = set()
                if hidden_col is not None:
                    hidden_val = str(ws.cell(row=row_num, column=hidden_col + 1).value or '').strip()
                    if hidden_val:
                        parts = [p.strip() for p in hidden_val.replace(';', ',').split(',')]
                        for p in parts:
                            if p in VALID_PROGRAMS:
                                required_programs.add(p)

                for p, col_idx in program_cols.items():
                    val = str(ws.cell(row=row_num, column=col_idx + 1).value or '').strip().lower()
                    if val in ('1', 'да', 'true', 'yes'):
                        required_programs.add(p)

                if not required_programs:
                    continue

                emp_id = EmployeesRepo.upsert({
                    'snils': snils_fmt,
                    'last_name': last_name,
                    'first_name': first_name,
                    'middle_name': middle_name,
                    'position': position,
                    'required_programs': ';'.join(sorted(required_programs)),
                })
                for p in required_programs:
                    EmployeeProgramsRepo.upsert(emp_id, {
                        'program_id': int(p), 'need_training': 1
                    })
                imported += 1

            QMessageBox.information(self, "Успех", f"Импортировано: {imported} сотрудников")
            self.refresh_table()
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка импорта: {e}")

    def _export_xlsx(self, filtered=True):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить XLSX", "Сводка_сотрудников.xlsx", "Excel Files (*.xlsx)"
        )
        if not file_path:
            return
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment

            employees = EmployeesRepo.get_all()
            wb = Workbook()
            ws = wb.active
            ws.title = "Сводка"

            programs = self._selected_programs[:6] if filtered else VALID_PROGRAMS

            headers = ["ФИО", "СНИЛС", "Должность"]
            for p in programs:
                headers.append(f"программа #{p} Потребность")
                headers.append(f"программа #{p} Дата обучения")
                headers.append(f"программа #{p} Протокол")
                headers.append(f"программа #{p} Рег.№")
            ws.append(headers)

            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="4169E1", end_color="4169E1", fill_type="solid")
            for cell in ws[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center")

            for emp in employees:
                progs = EmployeeProgramsRepo.get_by_employee(emp['id'])
                prog_map = {str(p['program_id']): p for p in progs}

                fio = f"{emp['last_name']} {emp['first_name']} {emp['middle_name']}".strip()
                row_data = [fio, emp['snils'], emp['position']]

                for p in programs:
                    pd = prog_map.get(p, {})
                    need = "Да" if pd.get('need_training') == 1 else "Нет"
                    row_data.extend([need, pd.get('exam_date', ''), pd.get('protocol', ''), pd.get('base_no', '')])

                ws.append(row_data)

            for col in ws.columns:
                max_len = 0
                for cell in col:
                    if cell.value:
                        max_len = max(max_len, len(str(cell.value)))
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 50)

            wb.save(file_path)
            QMessageBox.information(self, "Успех", f"Файл сохранён:\n{file_path}")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка экспорта: {e}")

    def _query_reestr(self):
        api_key = load_api_key(self.data_dir)
        if not api_key:
            QMessageBox.warning(self, "Ошибка", "API ключ не найден. Сохраните ключ на вкладке 'Передача данных'")
            return

        employees = EmployeesRepo.get_all()
        if not employees:
            QMessageBox.information(self, "Информация", "Нет сотрудников для запроса")
            return

        proxy_settings = load_proxy_settings(self.data_dir)

        self.query_btn.setEnabled(False)
        self.query_btn.setText("Запрос...")

        self._api_thread = ApiQueryThread(employees, api_key, proxy_settings)
        self._api_thread.finished.connect(self._on_query_finished)
        self._api_thread.error_signal.connect(lambda msg: logger.error(msg))
        self._api_thread.progress.connect(lambda c, t: self.query_btn.setText(f"Запрос... {c}/{t}"))
        self._api_thread.start()

    def _on_query_finished(self, updated, errors):
        self.query_btn.setEnabled(True)
        self.query_btn.setText("Запросить из реестра")
        if errors > 0:
            QMessageBox.warning(
                self, "Результат",
                f"Обновлено: {updated}\nОшибок: {errors}"
            )
        else:
            QMessageBox.information(self, "Успех", f"Обновлено: {updated} сотрудников")
        self.refresh_table()

    def _query_single(self, emp_id):
        api_key = load_api_key(self.data_dir)
        if not api_key:
            QMessageBox.warning(self, "Ошибка", "API ключ не найден")
            return

        emp = EmployeesRepo.get_by_id(emp_id)
        if not emp:
            return

        proxy_settings = load_proxy_settings(self.data_dir)
        snils_clean = emp['snils'].replace('-', '').replace(' ', '')
        try:
            result = get_by_snils(api_key, snils_clean, proxy_settings=proxy_settings)
            if result.get("success"):
                records = result.get("records", [])
                from collections import defaultdict
                best = {}
                for rec in records:
                    prog_id = rec.get('learnProgramId', '')
                    if not prog_id:
                        continue
                    exam_date = rec.get('Date', '')
                    if prog_id not in best or (exam_date and exam_date > best[prog_id].get('Date', '')):
                        best[prog_id] = rec
                updated = 0
                for prog_id, rec in best.items():
                    is_passed = rec.get('isPassed', '')
                    result_val = 1 if is_passed and is_passed.lower() in ('true', '1', 'да') else 0
                    try:
                        EmployeeProgramsRepo.update_from_api(
                            emp_id, int(prog_id),
                            rec.get('Date', ''), rec.get('ProtocolNumber', ''),
                            rec.get('baseNo', ''), result_val
                        )
                        updated += 1
                    except (ValueError, TypeError):
                        pass
                EmployeesRepo.update_sync(emp_id, datetime.now().strftime('%d.%m.%Y %H:%M:%S'))
                QMessageBox.information(self, "Успех", f"Обновлено программ: {updated}")
                self.refresh_table()
            else:
                QMessageBox.warning(self, "Ошибка", result.get("error", "Неизвестная ошибка"))
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка запроса: {e}")

    def _generate_plan(self, current_year=True):
        year = datetime.now().year if current_year else datetime.now().year + 1
        plan_year = year
        today = datetime.now()

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Параметры формирования плана на {plan_year} год")
        dialog.setMinimumSize(400, 250)
        dialog.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        dialog.setStyleSheet("QDialog { background-color: white; }")

        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(f"Параметры формирования плана на {plan_year} год:"))

        cb_not_trained = QCheckBox("Включать не обученных")
        cb_not_trained.setChecked(True)
        cb_not_trained.setStyleSheet("color: black;")
        layout.addWidget(cb_not_trained)

        cb_expired = QCheckBox("Включать просроченных")
        cb_expired.setChecked(True)
        cb_expired.setStyleSheet("color: black;")
        layout.addWidget(cb_expired)

        cb_expiring = QCheckBox("Включать истекающих в планируемом году")
        cb_expiring.setChecked(True)
        cb_expiring.setStyleSheet("color: black;")
        layout.addWidget(cb_expiring)

        cb_failed = QCheckBox("Включать неуспешно прошедших проверку знаний")
        cb_failed.setChecked(True)
        cb_failed.setStyleSheet("color: black;")
        layout.addWidget(cb_failed)

        btn_layout = QHBoxLayout()
        generate_btn = QPushButton("Сформировать")
        generate_btn.setStyleSheet(self._btn_style())
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setStyleSheet("""
            QPushButton {
                color: red; border: 2px solid red; padding: 8px 16px;
                border-radius: 5px; font-weight: bold; background-color: white;
            }
            QPushButton:hover { background-color: #FFE0E0; }
        """)
        cancel_btn.clicked.connect(dialog.reject)

        plan_data = []

        def do_generate():
            nonlocal plan_data
            employees = EmployeesRepo.get_all()
            for emp in employees:
                progs = EmployeeProgramsRepo.get_by_employee(emp['id'])
                for p in progs:
                    if p.get('need_training') != 1:
                        continue
                    prog_id = str(p['program_id'])
                    exam_date_str = p.get('exam_date', '')
                    result_val = p.get('result')
                    status = p.get('status', '')

                    reason = None
                    priority = None
                    last_exam = exam_date_str or ""
                    expiry = ""

                    if not exam_date_str or result_val == 0:
                        if cb_not_trained.isChecked() or cb_failed.isChecked():
                            if not exam_date_str and cb_not_trained.isChecked():
                                reason = "Не обучен"
                                priority = "Высокий"
                                expiry = (today + relativedelta(days=60)).strftime('%d.%m.%Y')
                            elif result_val == 0 and cb_failed.isChecked():
                                reason = "Не сдал проверку знаний"
                                priority = "Высокий"
                                expiry = (today + relativedelta(days=30)).strftime('%d.%m.%Y')
                    else:
                        try:
                            exam_date = datetime.strptime(exam_date_str.split()[0], '%d.%m.%Y')
                            expiry_date = exam_date + relativedelta(years=3)
                            expiry_str = expiry_date.strftime('%d.%m.%Y')

                            if expiry_date < today:
                                if cb_expired.isChecked():
                                    reason = "Просрочено"
                                    priority = "Высокий"
                                    expiry = (today + relativedelta(days=30)).strftime('%d.%m.%Y')
                            elif expiry_date.year == plan_year:
                                if cb_expiring.isChecked():
                                    reason = f"Истекает срок действия"
                                    priority = "Средний"
                                    expiry = expiry_str
                        except (ValueError, IndexError):
                            continue

                    if reason and priority:
                        plan_data.append({
                            'last_name': emp['last_name'],
                            'first_name': emp['first_name'],
                            'middle_name': emp['middle_name'],
                            'snils': emp['snils'],
                            'position': emp['position'],
                            'program': prog_id,
                            'last_exam_date': last_exam,
                            'expiry_date': expiry,
                            'reason': reason,
                            'priority': priority,
                        })

            plan_data.sort(key=lambda x: (
                {"Высокий": 0, "Средний": 1, "Низкий": 2}.get(x['priority'], 3),
                x['last_name']
            ))

            dialog.accept()

        generate_btn.clicked.connect(do_generate)
        btn_layout.addWidget(generate_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        if dialog.exec() != 1 or not plan_data:
            if not plan_data:
                QMessageBox.information(self, "Информация", "Нет сотрудников для включения в план")
            return

        title = f"План обучения на {plan_year} год"
        plan_dlg = PlanDialog(plan_data, title, self)
        plan_dlg.exec()
