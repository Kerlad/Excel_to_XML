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
    QFileDialog, QMessageBox, QFrame, QProgressBar, QDialog
)
from utils.crypto import hash_for_search
from PySide6.QtCore import Qt, Signal, QUrl, QThread
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from importers.xml_importer import load_xml
from utils.crypto import encrypt_data, decrypt_data, CryptoPassphraseRequiredError
from utils.constants import VALID_PROGRAMS_SET
from utils.workers import ExcelImportWorker

logger = logging.getLogger(__name__)


class DataEntryTab(QWidget):
    data_loaded = Signal(list, bool)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.get_existing_keys_callback = None

        self._last_error_details = []
        self._last_duplicate_map = []
        self._import_thread = None
        self._import_worker = None
        self._import_merge_mode = False
        self._import_existing_keys = set()
        self._is_xlsx_importing = False

        from utils.app_paths import get_app_data_dir, get_resource_dir
        self.resource_dir = get_resource_dir()
        self.data_dir = get_app_data_dir()
        self.schema_dir = os.path.join(self.resource_dir, "schema")
        self.settings_file = os.path.join(self.data_dir, "org_settings.json")

        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.schema_dir, exist_ok=True)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(16)
        scroll_layout.setContentsMargins(0, 0, 0, 0)

        scroll_layout.addWidget(self._create_org_group())
        scroll_layout.addWidget(self._create_upload_group())
        scroll_layout.addWidget(self._create_manual_entry_group())

        self._drop_label = QLabel("📁 Перетащите файл XLSX или XML сюда для загрузки")
        self._drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._drop_label.setMinimumHeight(60)
        self._drop_label.setStyleSheet("""
            QLabel { border: 2px dashed #888; border-radius: 10px;
                color: #666; font-size: 13px;
                background-color: transparent; padding: 8px; }
            QLabel:hover { border-color: #4169E1; color: #4169E1; }
        """)
        scroll_layout.addWidget(self._drop_label)
        scroll_layout.addStretch()

        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)

        self.load_settings()
        self.load_xsd_on_startup()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile().lower()
                if path.endswith(('.xlsx', '.xml')):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        urls = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        for path in urls:
            self.file_path_input.setText(path)
            self.upload_file()
            break

    # ── helpers ─────────────────────────────────────────────

    def _btn_style(self, bg="#4169E1", hover="#3151B1"):
        return f"""
            QPushButton {{
                background-color: {bg};
                color: white;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
        """

    # ── Group 1: Данные УЦ и работодателя ──────────────────

    def _create_org_group(self):
        group = QGroupBox("Данные УЦ и работодателя")

        grid = QGridLayout(group)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(14)
        grid.setContentsMargins(4, 4, 4, 4)

        # === row 0: ИНН УЦ  +  Название УЦ ===
        tc_inn_icon = QLabel("\U0001F511")
        tc_inn_icon.setToolTip("Идентификационный номер налогоплательщика")
        grid.addWidget(tc_inn_icon, 0, 0)

        self.tc_inn_label = QLabel("ИНН УЦ:")
        self.tc_inn_label.setToolTip("10 или 12 цифр")
        grid.addWidget(self.tc_inn_label, 0, 1)

        self.tc_inn_input = QLineEdit()
        self.tc_inn_input.setPlaceholderText("10 или 12 цифр")
        self.tc_inn_input.setToolTip("ИНН удостоверяющего центра (10 или 12 цифр)")
        self.tc_inn_input.setFixedWidth(180)
        grid.addWidget(self.tc_inn_input, 0, 2)

        spacer = QLabel("  ")
        grid.addWidget(spacer, 0, 3)

        self.tc_title_label = QLabel("Название УЦ:")
        self.tc_title_label.setToolTip("Полное наименование")
        grid.addWidget(self.tc_title_label, 0, 4)

        self.tc_title_input = QLineEdit()
        self.tc_title_input.setPlaceholderText("Полное наименование")
        self.tc_title_input.setToolTip("Полное наименование удостоверяющего центра")
        grid.addWidget(self.tc_title_input, 0, 5)

        # === row 1: ИНН Заказчика  +  Название Заказчика ===
        emp_inn_icon = QLabel("\U0001F464")
        emp_inn_icon.setToolTip("ИНН организации-заказчика")
        grid.addWidget(emp_inn_icon, 1, 0)

        self.employer_inn_label = QLabel("ИНН Заказчика:")
        self.employer_inn_label.setToolTip("10 или 12 цифр")
        grid.addWidget(self.employer_inn_label, 1, 1)

        self.employer_inn_input = QLineEdit()
        self.employer_inn_input.setPlaceholderText("10 или 12 цифр")
        self.employer_inn_input.setToolTip("ИНН организации-заказчика (10 или 12 цифр)")
        self.employer_inn_input.setFixedWidth(180)
        grid.addWidget(self.employer_inn_input, 1, 2)

        self.employer_title_label = QLabel("Название Заказчика:")
        self.employer_title_label.setToolTip("Полное наименование")
        grid.addWidget(self.employer_title_label, 1, 4)

        self.employer_title_input = QLineEdit()
        self.employer_title_input.setPlaceholderText("Полное наименование")
        self.employer_title_input.setToolTip("Полное наименование организации-заказчика")
        grid.addWidget(self.employer_title_input, 1, 5)

        grid.setColumnStretch(5, 1)

        # === row 2: кнопка ===
        self.save_org_btn = QPushButton("\U0001F4BE  Сохранить данные")
        self.save_org_btn.setStyleSheet(self._btn_style())
        self.save_org_btn.setToolTip("Сохранить данные УЦ и работодателя в зашифрованном виде")
        self.save_org_btn.clicked.connect(self.save_org_settings)

        btn_wrapper = QHBoxLayout()
        btn_wrapper.addWidget(self.save_org_btn)
        btn_wrapper.addStretch()
        grid.addLayout(btn_wrapper, 2, 0, 1, 6)

        return group

    # ── Group 2: Загрузка данных ───────────────────────────

    def _create_upload_group(self):
        group = QGroupBox("Загрузка данных")

        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        layout.setContentsMargins(4, 4, 4, 4)

        form = QFormLayout()
        form.setSpacing(10)

        # XSD схема
        xsd_row = QHBoxLayout()
        self.xsd_file_input = QLineEdit()
        self.xsd_file_input.setReadOnly(True)
        self.xsd_file_input.setPlaceholderText("XSD не загружена")
        self.xsd_file_input.setToolTip("Путь к загруженной XSD схеме")

        self.upload_xsd_btn = QPushButton("\U0001F4C1  Загрузить XSD")
        self.upload_xsd_btn.setStyleSheet(self._btn_style())
        self.upload_xsd_btn.setToolTip("Выбрать и загрузить XSD файл схемы")
        self.upload_xsd_btn.clicked.connect(self.upload_xsd)

        self.xsd_scheme_btn = QPushButton("\U0001F517  Скачать XSD")
        self.xsd_scheme_btn.setStyleSheet(self._btn_style(bg="#6c757d", hover="#5a6268"))
        self.xsd_scheme_btn.setToolTip("Открыть сайт для скачивания XSD схемы")
        self.xsd_scheme_btn.clicked.connect(self.open_xsd_scheme)

        xsd_row.addWidget(self.xsd_file_input, 1)
        xsd_row.addWidget(self.upload_xsd_btn)
        xsd_row.addWidget(self.xsd_scheme_btn)
        form.addRow("XSD схема:", xsd_row)

        # Выбранный файл
        file_row = QHBoxLayout()
        self.file_path_input = QLineEdit()
        self.file_path_input.setReadOnly(True)
        self.file_path_input.setPlaceholderText("Файл не выбран")
        self.file_path_input.setToolTip("Путь к выбранному файлу для загрузки")

        self.select_file_btn = QPushButton("\U0001F4C2  Выбрать файл")
        self.select_file_btn.setStyleSheet(self._btn_style())
        self.select_file_btn.setToolTip("Выбрать XLSX или XML файл")
        self.select_file_btn.clicked.connect(self.select_file)

        file_row.addWidget(self.file_path_input, 1)
        file_row.addWidget(self.select_file_btn)
        form.addRow("Файл данных:", file_row)

        layout.addLayout(form)

        # Progress area
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(6)
        layout.addWidget(self.progress_bar)

        self._import_status_label = QLabel()
        self._import_status_label.setVisible(False)
        self._import_status_label.setStyleSheet("color: #555; font-size: 12px;")
        layout.addWidget(self._import_status_label)

        self._cancel_import_btn = QPushButton("✕ Отменить импорт")
        self._cancel_import_btn.setVisible(False)
        self._cancel_import_btn.setStyleSheet(self._btn_style(bg="#E74C3C", hover="#C0392B"))
        self._cancel_import_btn.setToolTip("Отменить текущий импорт")
        self._cancel_import_btn.clicked.connect(self._cancel_import)

        cancel_row = QHBoxLayout()
        cancel_row.addWidget(self._cancel_import_btn)
        cancel_row.addStretch()
        cancel_layout = QVBoxLayout()
        cancel_layout.addLayout(cancel_row)
        layout.addLayout(cancel_layout)

        # Action buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self.upload_file_btn = QPushButton("\U0001F680  Загрузить файл")
        self.upload_file_btn.setStyleSheet(self._btn_style())
        self.upload_file_btn.setToolTip("Загрузить выбранный XLSX/XML файл в систему")
        self.upload_file_btn.clicked.connect(self.upload_file)

        self.create_template_btn = QPushButton("\U0001F4DD  Создать шаблон")
        self.create_template_btn.setStyleSheet(self._btn_style(bg="#6c757d", hover="#5a6268"))
        self.create_template_btn.setToolTip("Создать XLSX шаблон для заполнения")
        self.create_template_btn.clicked.connect(self.create_template)

        btn_row.addWidget(self.upload_file_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.create_template_btn)
        layout.addLayout(btn_row)

        return group

    # ── Group 3: Ввод данных работника (кнопка → диалог) ──

    def _create_manual_entry_group(self):
        group = QGroupBox("Ввод данных работника")

        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        layout.setContentsMargins(4, 4, 4, 4)

        desc = QLabel("Добавьте одного работника вручную, если нет файла для массовой загрузки.")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        add_btn = QPushButton("\U00002795  Добавить работника вручную")
        add_btn.setStyleSheet(self._btn_style())
        add_btn.setToolTip("Открыть форму для ручного ввода данных работника")
        add_btn.clicked.connect(self._open_manual_dialog)

        btn_wrapper = QHBoxLayout()
        btn_wrapper.addWidget(add_btn)
        btn_wrapper.addStretch()
        layout.addLayout(btn_wrapper)

        return group

    def _open_manual_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Добавление работника вручную")
        dialog.setMinimumWidth(640)

        main_layout = QVBoxLayout(dialog)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # ── left column ──
        col1 = QFormLayout()
        col1.setSpacing(12)
        col1.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        self._last_name_input = QLineEdit()
        self._last_name_input.setPlaceholderText("Иванов")
        self._last_name_input.setToolTip("Фамилия работника (только буквы)")
        col1.addRow("Фамилия:", self._last_name_input)

        self._first_name_input = QLineEdit()
        self._first_name_input.setPlaceholderText("Иван")
        self._first_name_input.setToolTip("Имя работника (только буквы)")
        col1.addRow("Имя:", self._first_name_input)

        self._middle_name_input = QLineEdit()
        self._middle_name_input.setPlaceholderText("Иванович")
        self._middle_name_input.setToolTip("Отчество работника (только буквы)")
        col1.addRow("Отчество:", self._middle_name_input)

        self._position_input = QLineEdit()
        self._position_input.setPlaceholderText("Главный специалист")
        self._position_input.setToolTip("Должность работника (только буквы, пробелы, дефис)")
        col1.addRow("Должность:", self._position_input)

        self._snils_input = QLineEdit()
        self._snils_input.setPlaceholderText("123-456-789 00")
        self._snils_input.setMaxLength(15)
        self._snils_input.setToolTip("СНИЛС в формате XXX-XXX-XXX XX (11 цифр)")
        self._snils_input.textChanged.connect(self._format_snils_input)
        col1.addRow("СНИЛС:", self._snils_input)

        # ── right column ──
        col2 = QFormLayout()
        col2.setSpacing(12)
        col2.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        program_row = QHBoxLayout()
        self._program_input = QLineEdit()
        self._program_input.setPlaceholderText("Например: 1,2,3")
        self._program_input.setToolTip("Номера программ обучения через запятую")
        self._help_btn = QPushButton("Справка")
        self._help_btn.setToolTip("Открыть список доступных программ обучения")
        self._help_btn.clicked.connect(self._on_program_help_dialog)
        program_row.addWidget(self._program_input, 1)
        program_row.addWidget(self._help_btn)
        col2.addRow("Программы:", program_row)

        self._protocol_input = QLineEdit()
        self._protocol_input.setPlaceholderText("ПР-2025-001")
        self._protocol_input.setToolTip("Номер протокола проверки знаний")
        col2.addRow("Протокол:", self._protocol_input)

        self._result_combo = QComboBox()
        self._result_combo.addItems(["Удовлетворительно", "Неудовлетворительно"])
        self._result_combo.setToolTip("Результат проверки знаний")
        col2.addRow("Результат:", self._result_combo)

        self._date_input = QLineEdit()
        self._date_input.setPlaceholderText("ДД.ММ.ГГГГ")
        self._date_input.setToolTip("Дата проверки знаний в формате ДД.ММ.ГГГГ (или ДДММГГГГ)")
        col2.addRow("Дата:", self._date_input)

        # ── columns side by side ──
        columns = QHBoxLayout()
        columns.setSpacing(32)
        columns.addLayout(col1)
        columns.addLayout(col2)
        main_layout.addLayout(columns)

        # ── buttons ──
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self._save_btn = QPushButton("\U0001F4BE  Сохранить")
        self._save_btn.setStyleSheet(self._btn_style())
        self._save_btn.setToolTip("Сохранить данные и передать в систему")
        self._save_btn.clicked.connect(lambda: self._save_manual_from_dialog(dialog))
        btn_row.addWidget(self._save_btn)

        self._clear_btn = QPushButton("\U0001F9F9  Очистить")
        self._clear_btn.setStyleSheet(self._btn_style(bg="#6c757d", hover="#5a6268"))
        self._clear_btn.setToolTip("Очистить все поля формы")
        self._clear_btn.clicked.connect(self._clear_dialog_form)
        btn_row.addWidget(self._clear_btn)

        btn_row.addStretch()

        self._cancel_btn = QPushButton("Отмена")
        self._cancel_btn.setToolTip("Закрыть форму без сохранения")
        self._cancel_btn.clicked.connect(dialog.reject)
        btn_row.addWidget(self._cancel_btn)

        main_layout.addLayout(btn_row)
        dialog.exec()

    def _on_program_help_dialog(self):
        self.show_programs_help()

    def _set_dialog_field_error(self, widget, is_error):
        if is_error:
            widget.setStyleSheet("border: 2px solid #E74C3C;")
        else:
            widget.setStyleSheet("")

    def _clear_dialog_errors(self):
        for w in [self._last_name_input, self._first_name_input, self._middle_name_input,
                   self._position_input, self._snils_input, self._program_input,
                   self._protocol_input, self._result_combo, self._date_input]:
            w.setStyleSheet("")

    def _clear_dialog_form(self):
        self._last_name_input.clear()
        self._first_name_input.clear()
        self._middle_name_input.clear()
        self._position_input.clear()
        self._snils_input.clear()
        self._program_input.clear()
        self._protocol_input.clear()
        self._result_combo.setCurrentIndex(0)
        self._date_input.clear()
        self._clear_dialog_errors()

    def _save_manual_from_dialog(self, dialog):
        from datetime import datetime

        self._clear_dialog_errors()

        fields = {
            'Фамилия': self._last_name_input.text().strip(),
            'Имя': self._first_name_input.text().strip(),
            'Отчество': self._middle_name_input.text().strip(),
            'Должность': self._position_input.text().strip(),
            'СНИЛС': self._snils_input.text().strip(),
            'Номер программы': self._program_input.text().strip(),
            'Номер протокола': self._protocol_input.text().strip(),
            'Результат': self._result_combo.currentText(),
            'Дата': self._date_input.text().strip(),
        }

        field_widgets = {
            'Фамилия': self._last_name_input,
            'Имя': self._first_name_input,
            'Отчество': self._middle_name_input,
            'Должность': self._position_input,
            'СНИЛС': self._snils_input,
            'Номер программы': self._program_input,
            'Номер протокола': self._protocol_input,
            'Результат': self._result_combo,
            'Дата': self._date_input,
        }

        empty_fields = [k for k, v in fields.items() if not v]
        if empty_fields:
            for f in empty_fields:
                self._set_dialog_field_error(field_widgets[f], True)
            QMessageBox.warning(self, "Ошибка", "Заполните все строки")
            return

        for field_name in ['Фамилия', 'Имя', 'Отчество', 'Должность']:
            value = fields[field_name]
            if not value.replace(' ', '').replace('-', '').isalpha():
                self._set_dialog_field_error(field_widgets[field_name], True)
                QMessageBox.warning(self, "Ошибка", f"{field_name} — только текст")
                return

        snils = fields['СНИЛС'].replace('-', '').replace(' ', '')
        if not snils.isdigit() or len(snils) != 11:
            self._set_dialog_field_error(field_widgets['СНИЛС'], True)
            QMessageBox.warning(self, "Ошибка", "СНИЛС должен содержать 11 цифр")
            return

        program_str = fields['Номер программы']
        programs = [p.strip() for p in program_str.rstrip(',').split(',') if p.strip()]
        if not programs:
            self._set_dialog_field_error(field_widgets['Номер программы'], True)
            QMessageBox.warning(self, "Ошибка", "Некорректный номер программы")
            return
        for prog in programs:
            if prog not in VALID_PROGRAMS_SET:
                self._set_dialog_field_error(field_widgets['Номер программы'], True)
                QMessageBox.warning(self, "Ошибка", "Некорректный номер программы")
                return

        date_str = fields['Дата'].replace('.', '').replace('-', '')
        if not date_str.isdigit():
            self._set_dialog_field_error(field_widgets['Дата'], True)
            QMessageBox.warning(self, "Ошибка", "Дата некорректна. Введите корректную дату в формате ДД.ММ.ГГГГ или ДДММГГГГ")
            return
        try:
            if len(date_str) == 8:
                date_obj = datetime.strptime(date_str, "%d%m%Y")
            else:
                self._set_dialog_field_error(field_widgets['Дата'], True)
                QMessageBox.warning(self, "Ошибка", "Дата некорректна. Введите корректную дату в формате ДД.ММ.ГГГГ или ДДММГГГГ")
                return
            if date_obj.date() > datetime.now().date():
                self._set_dialog_field_error(field_widgets['Дата'], True)
                QMessageBox.warning(self, "Ошибка", "Дата не может быть больше текущей")
                return
        except ValueError:
            self._set_dialog_field_error(field_widgets['Дата'], True)
            QMessageBox.warning(self, "Ошибка", "Дата некорректна. Введите корректную дату в формате ДД.ММ.ГГГГ или ДДММГГГГ")
            return

        if self.get_existing_keys_callback:
            existing_keys = self.get_existing_keys_callback()
            normalized_date = fields['Дата'].strip()
            new_keys = [(hash_for_search(snils), str(prog), normalized_date) for prog in programs]
            duplicates = [k for k in new_keys if k in existing_keys]
            if duplicates:
                QMessageBox.warning(
                    self, "Предупреждение",
                    f"Выявлены аналогичные данные — {len(duplicates)} строк"
                )
                return

        settings_tc_inn = self.tc_inn_input.text().strip()
        settings_tc_title = self.tc_title_input.text().strip()
        settings_employer_inn = self.employer_inn_input.text().strip()
        settings_employer_title = self.employer_title_input.text().strip()

        records = []
        for prog in programs:
            records.append({
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
                'protocol': fields['Номер протокола'],
            })

        self.data_loaded.emit(records, False)

        QMessageBox.information(dialog, "Успех", "Запись создана и передана в систему")
        dialog.accept()

    # ── сохранённая (старая) логика ────────────────────────

    def load_settings(self):
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
            except CryptoPassphraseRequiredError:
                logger.info("Settings not loaded - passphrase required")
            except Exception as e:
                logger.exception("Error loading org settings")
                QMessageBox.warning(self, "Ошибка", f"Ошибка чтения настроек: {e}")

    def load_xsd_on_startup(self):
        xsd_files = [f for f in os.listdir(self.schema_dir) if f.endswith('.xsd')]
        if xsd_files:
            xsd_path = os.path.join(self.schema_dir, xsd_files[0])
            self.xsd_file_input.setText(xsd_path)

    def save_org_settings(self):
        tc_inn = self.tc_inn_input.text().strip()
        employer_inn = self.employer_inn_input.text().strip()

        if tc_inn and not (tc_inn.isdigit() and len(tc_inn) in [10, 12]):
            QMessageBox.warning(self, "Ошибка", "ИНН — только 10 или 12 цифр")
            return

        if employer_inn and not (employer_inn.isdigit() and len(employer_inn) in [10, 12]):
            QMessageBox.warning(self, "Ошибка", "ИНН — только 10 или 12 цифр")
            return

        if not tc_inn or not self.tc_title_input.text().strip() or \
           not employer_inn or not self.employer_title_input.text().strip():
            QMessageBox.warning(self, "Ошибка", "Заполните данные УЦ/Работодателя")
            return

        settings = {
            'tc_inn': tc_inn,
            'tc_title': self.tc_title_input.text().strip(),
            'employer_inn': employer_inn,
            'employer_title': self.employer_title_input.text().strip(),
        }

        try:
            encrypted = encrypt_data(settings)
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump({"data": encrypted}, f, ensure_ascii=False, indent=4)
            QMessageBox.information(self, "Успех", "Данные сохранены (зашифрованы)")
        except Exception as e:
            logger.exception("Error saving org settings")
            QMessageBox.warning(self, "Ошибка", f"Ошибка сохранения: {e}")

    def upload_xsd(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите XSD файл", "", "XSD Files (*.xsd)"
        )
        if file_path:
            try:
                dest_path = os.path.join(self.schema_dir, os.path.basename(file_path))
                shutil.copy(file_path, dest_path)
                self.xsd_file_input.setText(dest_path)
                QMessageBox.information(self, "Успех", "XSD файл успешно загружен")
            except (OSError, shutil.Error) as e:
                logger.exception("Error uploading XSD")
                QMessageBox.warning(self, "Ошибка", f"Ошибка загрузки XSD: {e}")

    def open_xsd_scheme(self):
        webbrowser.open("https://akot.rosmintrud.ru/sout/info")

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл", "", "Excel/XML Files (*.xlsx *.xml)"
        )
        if file_path:
            self.file_path_input.setText(file_path)

    def upload_file(self):
        file_path = self.file_path_input.text()
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "Ошибка", "Файл не выбран")
            return

        has_existing = False
        existing_keys = set()
        if self.get_existing_keys_callback:
            existing_keys = self.get_existing_keys_callback()
            has_existing = len(existing_keys) > 0

        merge_mode = False
        if has_existing:
            self.progress_bar.setVisible(True)
            reply = self._show_merge_dialog()
            if reply == "cancel":
                self.progress_bar.setVisible(False)
                return
            elif reply == "replace":
                merge_mode = True
                existing_keys = set()

        if file_path.endswith('.xlsx'):
            self._start_xlsx_import(file_path, merge_mode, existing_keys)
        elif file_path.endswith('.xml'):
            self._run_xml_import(file_path, merge_mode, existing_keys)
        else:
            QMessageBox.warning(self, "Ошибка", "Неподдерживаемый формат файла")

    def _run_xml_import(self, file_path, merge_mode, existing_keys):
        """Синхронный импорт XML (быстрый, не требует фонового потока)."""
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(True)
        self._import_status_label.setText("Загрузка XML...")
        self._import_status_label.setVisible(True)

        try:
            xsd_files = [f for f in os.listdir(self.schema_dir) if f.endswith('.xsd')]
            xsd_path = os.path.join(self.schema_dir, xsd_files[0]) if xsd_files else None
            records, xml_error_count, xml_error_messages, xml_xsd_errors = load_xml(file_path, xsd_path)

            if records is None:
                logger.error(f"XML import failed: {xml_error_messages}")
            if xml_error_messages:
                logger.error(f"XML import errors: {xml_error_messages}")

            if xml_xsd_errors:
                logger.error(f"XSD validation errors: {xml_xsd_errors}")
                QMessageBox.warning(
                    self, "XSD-валидация",
                    "Файл не соответствует XSD-схеме:\n" + "\n".join(xml_xsd_errors[:20])
                )
                self.progress_bar.setVisible(False)
                self._import_status_label.setVisible(False)
                return

            if records is None:
                msgs = xml_error_messages[:5] if xml_error_messages else ["Ошибка импорта"]
                msg = "\n".join(msgs)
                QMessageBox.warning(self, "Ошибка импорта", msg)
                self.progress_bar.setVisible(False)
                self._import_status_label.setVisible(False)
                return

            self._finalize_import(records, merge_mode, existing_keys, [], set())

        except Exception as e:
            logger.exception("XML import failed")
            QMessageBox.warning(self, "Ошибка", f"Ошибка импорта XML: {e}")
        finally:
            self.progress_bar.setVisible(False)
            self._import_status_label.setVisible(False)

    def _start_xlsx_import(self, file_path, merge_mode, existing_keys):
        """Запуск фонового импорта XLSX в отдельном потоке."""
        self._is_xlsx_importing = True
        self._import_merge_mode = merge_mode
        self._import_existing_keys = existing_keys.copy()

        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(True)
        self._import_status_label.setText("Открытие файла...")
        self._import_status_label.setVisible(True)
        self._cancel_import_btn.setVisible(True)
        self.upload_file_btn.setEnabled(False)
        self.select_file_btn.setEnabled(False)
        self.file_path_input.setStyleSheet("background-color: #FFF3CD;")

        self._import_thread = QThread()
        self._import_worker = ExcelImportWorker(file_path)
        self._import_worker.moveToThread(self._import_thread)

        self._import_thread.started.connect(self._import_worker.run)
        self._import_worker.progress.connect(self._on_import_progress)
        self._import_worker.status_message.connect(self._on_import_status)
        self._import_worker.finished.connect(self._on_import_finished)
        self._import_worker.error.connect(self._on_import_error)
        self._import_worker.finished.connect(self._import_thread.quit)
        self._import_worker.finished.connect(self._import_worker.deleteLater)
        self._import_thread.finished.connect(self._import_thread.deleteLater)

        self._import_thread.start()

    def _cancel_import(self):
        """Отмена текущего импорта."""
        if self._import_worker:
            logger.info("Cancel requested by user")
            self._import_worker.cancel()
            self._import_status_label.setText("Отмена импорта...")
            self._cancel_import_btn.setEnabled(False)

    def _on_import_progress(self, current, total):
        """Обновление прогресс-бара."""
        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)
        else:
            self.progress_bar.setRange(0, 0)

    def _on_import_status(self, message):
        """Обновление текстового статуса импорта."""
        self._import_status_label.setText(message)

    def _on_import_finished(self, records, error_count, error_details, error_msg):
        """Завершение фонового импорта — финализация и UI."""
        self._cleanup_import()

        cancelled = (records is None and error_msg == ["Импорт отменён пользователем"])

        if cancelled:
            logger.info("Import was cancelled, no data loaded")
            return

        if records is None:
            err_msg = error_msg if error_msg else (str(error_details[0]['message']) if error_details else "Неизвестная ошибка")
            QMessageBox.warning(self, "Ошибка импорта", err_msg)
            return

        error_rows_set = {e['row'] for e in error_details}
        self._finalize_import(records, self._import_merge_mode, self._import_existing_keys,
                              error_details, error_rows_set)

    def _on_import_error(self, error_message):
        """Ошибка в фоновом импорте."""
        self._cleanup_import()
        QMessageBox.critical(self, "Ошибка импорта", error_message)

    def _cleanup_import(self):
        """Сброс UI и очистка после импорта (успех/отмена/ошибка)."""
        self._is_xlsx_importing = False
        self._import_thread = None
        self._import_worker = None

        self.progress_bar.setVisible(False)
        self._import_status_label.setVisible(False)
        self._cancel_import_btn.setVisible(False)
        self._cancel_import_btn.setEnabled(True)
        self.upload_file_btn.setEnabled(True)
        self.select_file_btn.setEnabled(True)
        self.file_path_input.setStyleSheet("")

    def _finalize_import(self, records, merge_mode, existing_keys, error_details, error_rows_set):
        """Общая финализация импорта: дедупликация, перезапись полей, эмит данных, диалог результата."""
        duplicate_map = {}
        existing_rows_map = {}
        if not merge_mode and self.get_existing_keys_callback:
            if hasattr(self, 'get_existing_rows_callback') and self.get_existing_rows_callback:
                for row_idx, snils, prog in self.get_existing_rows_callback():
                    key = (hash_for_search(snils), str(prog), '')
                    if key not in existing_rows_map:
                        existing_rows_map[key] = []
                    existing_rows_map[key].append(f"система (стр. {row_idx})")

        validated_records = []
        for rec in records:
            key = (hash_for_search(rec.get('snils', '')), str(rec.get('program', '')), rec.get('date', '') or '')
            source_row = rec.get('source_row', '?')
            if key in existing_keys:
                if key not in duplicate_map:
                    duplicate_map[key] = []
                if key in existing_rows_map:
                    for label in existing_rows_map[key]:
                        if label not in duplicate_map[key]:
                            duplicate_map[key].append(label)
                row_label = f"стр. {source_row}"
                if row_label not in duplicate_map[key]:
                    duplicate_map[key].append(row_label)
                continue

            is_internal_dup = False
            for vr in validated_records:
                if (hash_for_search(vr.get('snils', '')), str(vr.get('program', '')), vr.get('date', '') or '') == key:
                    is_internal_dup = True
                    break

            if is_internal_dup:
                if key not in duplicate_map:
                    duplicate_map[key] = []
                row_label = f"стр. {source_row}"
                if row_label not in duplicate_map[key]:
                    duplicate_map[key].append(row_label)
                continue

            existing_keys.add(key)
            validated_records.append(rec)

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
            rec.pop('source_row', None)

        self.data_loaded.emit(validated_records, merge_mode)

        self._last_error_details = error_details
        self._last_duplicate_map = duplicate_map

        total_errors = len(error_rows_set) + len(duplicate_map)
        if total_errors > 0:
            self._show_upload_result_dialog(len(validated_records), len(error_rows_set), len(duplicate_map))
        else:
            QMessageBox.information(self, "Успех", f"Успешно загружено: {len(validated_records)} записей")

    def _show_merge_dialog(self):
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout

        dialog = QDialog(self)
        dialog.setWindowTitle("Загрузка данных")
        dialog.setMinimumSize(400, 180)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(QLabel("В системе уже есть данные. Что сделать?"))
        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        merge_btn = QPushButton("Объединить")
        merge_btn.setObjectName("dialogPrimaryBtn")
        replace_btn = QPushButton("Удалить старые")
        replace_btn.setObjectName("toolbarDangerBtn")
        cancel_btn = QPushButton("Отменить загрузку")
        cancel_btn.setObjectName("dialogDangerBtn")

        result = "cancel"
        def set_result(val):
            nonlocal result
            result = val
            dialog.accept()

        merge_btn.clicked.connect(lambda: set_result("merge"))
        replace_btn.clicked.connect(lambda: set_result("replace"))
        cancel_btn.clicked.connect(lambda: set_result("cancel"))

        btn_layout.addWidget(merge_btn)
        btn_layout.addWidget(replace_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        dialog.exec()
        return result

    def _ask_password(self):
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout

        dialog = QDialog(self)
        dialog.setWindowTitle("Ввод пароля")
        dialog.setMinimumSize(400, 160)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        label = QLabel("Внимание: библиотека openpyxl не поддерживает пароли Excel.\nДля загрузки сохраните файл БЕЗ пароля:\nExcel → Файл → Сохранить как → Инструменты → Параметры → Защита → снять пароль")
        label.setWordWrap(True)
        layout.addWidget(label)

        password_input = QLineEdit()
        password_input.setEchoMode(QLineEdit.EchoMode.Password)
        password_input.setPlaceholderText("Оставьте пустым, если файл без пароля")
        layout.addWidget(password_input)

        buttons = QHBoxLayout()
        ok_btn = QPushButton("ОК")
        ok_btn.setObjectName("dialogPrimaryBtn")
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setObjectName("dialogDangerBtn")
        cancel_btn.clicked.connect(dialog.reject)
        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

        if dialog.exec():
            return password_input.text()
        return "CANCEL"

    def _show_upload_result_dialog(self, success_count, error_rows, duplicate_count):
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout

        dialog = QDialog(self)
        dialog.setWindowTitle("Загрузка завершена")
        dialog.setMinimumSize(460, 220)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        info_label = QLabel(
            f"<b>Успешно загружено:</b> {success_count} записей<br><br>"
            f"<b style='color:#E74C3C;'>Строк с ошибками:</b> {error_rows}<br>"
            f"<b style='color:#F1C40F;'>Дубликатов:</b> {duplicate_count}"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        btn_layout = QHBoxLayout()

        show_errors_btn = QPushButton("\U000026A0  Показать ошибки")
        show_errors_btn.setObjectName("showErrorsBtn")
        show_errors_btn.setStyleSheet(self._btn_style(bg="#E67E22", hover="#D35400"))
        show_errors_btn.clicked.connect(lambda: self._export_error_report(dialog))

        close_btn = QPushButton("Закрыть")
        close_btn.setObjectName("dialogPrimaryBtn")
        close_btn.clicked.connect(dialog.close)

        btn_layout.addWidget(show_errors_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        dialog.exec()

    def _export_error_report(self, parent_dialog):
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

        parent_dialog.close()

    def create_template(self):
        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "Шаблон"

            headers = [
                "Фамилия", "Имя", "Отчество", "СНИЛС", "Должность",
                "ИНН Заказчика", "Наименование ЮЛ Заказчика", "ИНН УЦ",
                "Наименование УЦ", "Результат", "№ программы", "Дата", "№ протокола"
            ]
            ws.append(headers)

            template_path = os.path.join(self.data_dir, "Шаблон.xlsx")
            wb.save(template_path)

            reply = QMessageBox.question(
                self, "Успех",
                "Шаблон создан. Открыть расположение файла?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                subprocess.Popen(f'explorer /select,"{template_path}"')
        except ImportError:
            QMessageBox.warning(self, "Ошибка", "Установите openpyxl: pip install openpyxl")
        except Exception as e:
            logger.exception("Error creating template")
            QMessageBox.warning(self, "Ошибка", f"Ошибка создания шаблона: {e}")

    def show_programs_help(self):
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
            "20": "Безопасные методы и приемы выполнения работ, связанных с эксплуатацией емкостей (сосудов, работающих под избыточным давлением)",
            "21": "Безопасные методы и приемы при выполнении водолазных работ",
            "22": "Безопасные методы и приемы работ по поиску, идентификации, обезвреживанию и уничтожению взрывоопасных предметов",
            "23": "Безопасные методы и приемы работ в непосредственной близости от полотна или проезжей части эксплуатируемых автомобильных и железных дорог",
            "24": "Безопасные методы и приемы работ на участках с патогенным заражением почвы",
            "25": "Безопасные методы и приемы работ по валке леса в особо опасных условиях",
            "26": "Безопасные методы и приемы работ по перемещению тяжеловесных и крупногабаритных грузов",
            "27": "Безопасные методы и приемы работ с радиоактивными веществами и источниками ионизирующих излучений",
            "28": "Безопасные методы и приемы работ с ручным инструментом, в том числе с пиротехническим",
            "29": "Безопасные методы и приемы работ в театрах",
        }

        blue_programs = {"1", "2", "3", "4", "18", "23"}

        from PySide6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QListWidgetItem, QHBoxLayout, QPushButton
        from PySide6.QtGui import QColor

        dialog = QDialog(self)
        dialog.setWindowTitle("Программы обучения")
        dialog.setMinimumSize(660, 720)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)

        list_widget = QListWidget()
        list_widget.setAlternatingRowColors(True)

        from PySide6.QtGui import QPalette
        pal = dialog.palette()
        primary = pal.color(QPalette.ColorRole.Highlight)
        for num, title in programs.items():
            item = QListWidgetItem(f"{num}: {title}")
            item.setData(Qt.ItemDataRole.UserRole, num)
            if num in blue_programs:
                item.setForeground(primary)
            list_widget.addItem(item)

        layout.addWidget(list_widget)

        hint = QLabel("Двойной клик по программе — добавить номер в поле")
        hint.setStyleSheet("font-style: italic; background-color: transparent;")
        layout.addWidget(hint)

        btn_layout = QHBoxLayout()
        close_btn = QPushButton("Закрыть")
        close_btn.setObjectName("dialogPrimaryBtn")
        close_btn.clicked.connect(dialog.close)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        def on_double_click(item):
            program_num = item.data(Qt.ItemDataRole.UserRole)
            target = self._program_input if hasattr(self, '_program_input') else self.program_input
            current = target.text().strip()
            if current.endswith(','):
                current = current[:-1]
            programs_list = [p.strip() for p in current.split(',') if p.strip()] if current else []
            if len(programs_list) >= 10:
                QMessageBox.warning(self, "Предупреждение", "Превышено количество программ для одного работника")
                return
            if program_num not in programs_list:
                programs_list.append(program_num)
            target.setText(','.join(programs_list) + ',')

        list_widget.itemDoubleClicked.connect(on_double_click)
        dialog.exec()

    def _format_snils_input(self, text):
        target = self._snils_input if hasattr(self, '_snils_input') else self.snils_input
        target.blockSignals(True)
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
            target.setText(formatted)
        finally:
            target.blockSignals(False)


