"""
Вкладка «Протокол» — формирование протокола проверки знаний
Поля: № протокола, Данные комиссии, Председатель, Члены комиссии, Профсоюз
Кнопки: Сохранить, Загрузить, Программы обучения, Сгенерировать протокол
"""
import os
import logging
from copy import deepcopy
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLineEdit, QPushButton,
    QLabel, QMessageBox, QFileDialog, QComboBox, QCheckBox, QScrollArea, QFrame,
    QDateEdit, QPlainTextEdit, QFormLayout
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont
from protocol.commission_manager import CommissionManager
from protocol.programs_manager import ProgramsManager
from tabs.programs_dialog import ProgramsDialog

logger = logging.getLogger(__name__)


class ProtocolTab(QWidget):
    def __init__(self, commission_manager: CommissionManager, programs_manager: ProgramsManager,
                 data_dir: str, journal_manager=None, data_source=None):
        super().__init__()
        self.setStyleSheet("background-color: transparent;")
        self.commission = commission_manager
        self.programs = programs_manager
        self.journal_manager = journal_manager
        self.data_source = data_source
        self.data_dir = data_dir
        self.last_save_path = self._load_last_save_path()

        # Основной layout с прокруткой
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background-color: transparent; border: none;")

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(15)

        # Раздел 1: Данные протокола
        scroll_layout.addWidget(self._create_protocol_group())

        # Раздел 2: Данные комиссии
        scroll_layout.addWidget(self._create_commission_group())

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)

        # Кнопки действий (вне прокрутки)
        main_layout.addWidget(self._create_action_buttons())

        # Загрузка данных
        self._load_commission_data()
        self._populate_protocol_combo()
    
    def _populate_protocol_combo(self):
        """Заполнение комбобокса номеров протоколов из журнала."""
        if not hasattr(self, 'journal_manager') or self.journal_manager is None:
            return
        
        # Получаем уникальные номера протоколов
        all_records = self.journal_manager.get_all_records()
        protocols = set()
        for rec in all_records:
            if rec.protocol:
                protocols.add(rec.protocol)
        
        # Очищаем и добавляем "Все"
        self.protocol_combo.clear()
        self.protocol_combo.addItem("Все")
        
        # Добавляем номера протоколов
        for proto in sorted(protocols):
            self.protocol_combo.addItem(proto)
        
        # Подключаем обработчик для автозаполнения даты
        self.protocol_combo.currentTextChanged.connect(self._on_protocol_selected)
    
    def _on_protocol_selected(self, protocol_number):
        """При выборе протокола автозаполняем дату из журнала."""
        if protocol_number == "Все" or not protocol_number:
            return
        if not hasattr(self, 'journal_manager') or self.journal_manager is None:
            return
        
        # Ищем записи с этим протоколом
        records = self.journal_manager.get_records_by_protocol(protocol_number)
        if records:
            for rec in records:
                if rec.exam_date:
                    self.exam_date_input.setText(rec.exam_date)
                    break
    
    def _load_last_save_path(self):
        """Загрузка последнего пути сохранения протокола."""
        import json
        settings_file = os.path.join(self.data_dir, "protocol_settings.json")
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    return settings.get('last_save_path', '')
            except Exception as e:
                logger.debug(f"Could not load last_save_path: {e}")
        return ''
    
    def _save_last_save_path(self, path):
        """Сохранение последнего пути сохранения протокола."""
        import json
        settings_file = os.path.join(self.data_dir, "protocol_settings.json")
        settings = {}
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
            except Exception as e:
                logger.debug(f"Could not load settings: {e}")
        # Сохраняем полный путь, а не только директорию
        settings['last_save_path'] = path
        try:
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Could not save settings: {e}")

    def set_data_source(self, data_view_tab):
        """Установка источника данных для протокола (DataViewTab)."""
        self.data_source = data_view_tab
    
    def set_journal_manager(self, journal_manager):
        """Установка менеджера журнала для получения регистрационных номеров."""
        self.journal_manager = journal_manager

    def _group_style(self):
        return """
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
        """

    def _btn_style(self, hover_color="#3151B1"):
        return f"""
            QPushButton {{
                background-color: #4169E1;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
        """

    # ============ Раздел: Данные протокола ============

    def _create_protocol_group(self):
        """Раздел: кнопка Программы обучения."""
        group = QGroupBox()
        group.setStyleSheet(self._group_style())
        group.setTitle("Данные протокола")

        layout = QHBoxLayout(group)
        layout.setSpacing(20)

        # Кнопка Программы обучения
        programs_btn = QPushButton("Программы обучения")
        programs_btn.setStyleSheet(self._btn_style())
        programs_btn.clicked.connect(self._open_programs_dialog)
        layout.addWidget(programs_btn)

        layout.addStretch()
        return group

    # ============ Раздел: Данные комиссии ============

    def _create_commission_group(self):
        """Раздел: Данные комиссии — организация, приказ, № протокола, дата проверки, председатель, члены, профсоюз."""
        group = QGroupBox()
        group.setStyleSheet(self._group_style())
        group.setTitle("Данные комиссии")

        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # Строка 1: Название организации
        row1 = QHBoxLayout()
        form1 = QFormLayout()
        self.org_name_label = QLabel("Название организации:")
        self.org_name_label.setStyleSheet("color: inherit;")
        self.org_name_input = QLineEdit()
        self.org_name_input.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 4px;")
        self.org_name_input.setPlaceholderText("ООО \"Организация\"")
        form1.addRow(self.org_name_label, self.org_name_input)
        row1.addLayout(form1)
        row1.addStretch()
        layout.addLayout(row1)

        # Строка 2: № протокола + Дата проверки знаний
        row2 = QHBoxLayout()
        row2.setSpacing(20)

        proto_form = QFormLayout()
        self.protocol_label = QLabel("№ протокола:")
        self.protocol_label.setStyleSheet("color: inherit;")
        self.protocol_combo = QComboBox()
        self.protocol_combo.setFixedWidth(200)
        self.protocol_combo.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 4px; background-color: white;")
        proto_form.addRow(self.protocol_label, self.protocol_combo)
        row2.addLayout(proto_form)

        exam_form = QFormLayout()
        self.exam_date_label = QLabel("Дата проверки знаний:")
        self.exam_date_label.setStyleSheet("color: inherit;")
        self.exam_date_input = QLineEdit()
        self.exam_date_input.setFixedWidth(160)
        self.exam_date_input.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 4px;")
        self.exam_date_input.setPlaceholderText("ДД.ММ.ГГГГ")
        exam_form.addRow(self.exam_date_label, self.exam_date_input)
        row2.addLayout(exam_form)

        row2.addStretch()
        layout.addLayout(row2)

        # Строка 3: Приказ о создании комиссии
        row3 = QHBoxLayout()
        form2 = QFormLayout()
        self.order_label = QLabel("Приказ о создании комиссии:")
        self.order_label.setStyleSheet("color: inherit;")

        order_row = QHBoxLayout()
        self.order_number_input = QLineEdit()
        self.order_number_input.setFixedWidth(120)
        self.order_number_input.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 4px;")
        self.order_number_input.setPlaceholderText("№ приказа")

        self.order_date_input = QLineEdit()
        self.order_date_input.setFixedWidth(140)
        self.order_date_input.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 4px;")
        self.order_date_input.setPlaceholderText("ДД.ММ.ГГГГ")

        order_row.addWidget(self.order_number_input)
        order_row.addWidget(QLabel("от"))
        order_row.addWidget(self.order_date_input)

        form2.addRow(self.order_label, order_row)
        row3.addLayout(form2)
        row3.addStretch()
        layout.addLayout(row3)

        # Подраздел: Председатель комиссии
        chairman_group = QGroupBox()
        chairman_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #CCCCCC;
                border-radius: 8px;
                margin-top: 8px;
                padding: 10px;
                background-color: transparent;
            }
            QGroupBox::title {
                color: #4169E1;
                font-weight: bold;
                font-size: 13px;
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        chairman_group.setTitle("Председатель комиссии")

        chairman_layout = QFormLayout(chairman_group)
        chairman_layout.setContentsMargins(0, 8, 0, 0)
        chairman_layout.setSpacing(6)
        chairman_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        chairman_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.chairman_fio_label = QLabel("ФИО:")
        self.chairman_fio_label.setStyleSheet("color: inherit;")
        self.chairman_fio_input = QLineEdit()
        self.chairman_fio_input.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 5px; border-radius: 4px;")
        self.chairman_fio_input.setPlaceholderText("Иванов И.И.")
        chairman_layout.addRow(self.chairman_fio_label, self.chairman_fio_input)

        self.chairman_pos_label = QLabel("Должность:")
        self.chairman_pos_label.setStyleSheet("color: inherit;")
        self.chairman_pos_input = QLineEdit()
        self.chairman_pos_input.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 5px; border-radius: 4px;")
        self.chairman_pos_input.setPlaceholderText("Директор")
        chairman_layout.addRow(self.chairman_pos_label, self.chairman_pos_input)
        layout.addWidget(chairman_group)

        # Подраздел: Члены комиссии (2 колонки)
        members_group = QGroupBox()
        members_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #CCCCCC;
                border-radius: 8px;
                margin-top: 8px;
                padding: 10px;
                background-color: transparent;
            }
            QGroupBox::title {
                color: #4169E1;
                font-weight: bold;
                font-size: 13px;
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        members_group.setTitle("Члены комиссии")

        members_layout = QHBoxLayout(members_group)
        members_layout.setSpacing(30)

        # Колонка 1: Член №1, Член №2
        col1 = QVBoxLayout()

        m1_group = self._create_member_fields("Член комиссии №1")
        col1.addWidget(m1_group)
        self.member1_fio_input = m1_group.fio_input
        self.member1_pos_input = m1_group.pos_input

        m2_group = self._create_member_fields("Член комиссии №2")
        col1.addWidget(m2_group)
        self.member2_fio_input = m2_group.fio_input
        self.member2_pos_input = m2_group.pos_input

        members_layout.addLayout(col1)

        # Колонка 2: Член №3, Представитель профсоюза
        col2 = QVBoxLayout()

        m3_group = self._create_member_fields("Член комиссии №3")
        col2.addWidget(m3_group)
        self.member3_fio_input = m3_group.fio_input
        self.member3_pos_input = m3_group.pos_input

        union_group = self._create_member_fields("Представитель профсоюза")
        col2.addWidget(union_group)
        self.union_fio_input = union_group.fio_input
        self.union_pos_input = union_group.pos_input

        members_layout.addLayout(col2)
        layout.addWidget(members_group)

        # Кнопки сохранения/загрузки
        btn_row = QHBoxLayout()
        self.save_commission_btn = QPushButton("Сохранить данные комиссии")
        self.save_commission_btn.setStyleSheet(self._btn_style())
        self.save_commission_btn.clicked.connect(self._save_commission_data)

        self.load_commission_btn = QPushButton("Загрузить данные комиссии")
        self.load_commission_btn.setStyleSheet(self._btn_style())
        self.load_commission_btn.clicked.connect(self._load_commission_data)

        btn_row.addWidget(self.save_commission_btn)
        btn_row.addWidget(self.load_commission_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        return group

    def _create_member_fields(self, title: str):
        """Создание полей для члена комиссии. Возвращает QGroupBox с атрибутами fio_input, pos_input."""
        from PySide6.QtWidgets import QGroupBox as QB

        group = QB()
        group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                margin-top: 5px;
                padding: 8px 12px;
                background-color: transparent;
            }
            QGroupBox::title {
                color: #666;
                font-size: 12px;
                font-weight: normal;
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        group.setTitle(title)

        # QFormLayout как основной — поля растягиваются до границы группы
        form = QFormLayout(group)
        form.setContentsMargins(0, 8, 0, 0)
        form.setSpacing(6)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        fio_label = QLabel("ФИО:")
        fio_label.setStyleSheet("color: inherit;")
        fio_input = QLineEdit()
        fio_input.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 5px; border-radius: 4px;")
        fio_input.setPlaceholderText("Петров П.П.")
        form.addRow(fio_label, fio_input)

        pos_label = QLabel("Должность:")
        pos_label.setStyleSheet("color: inherit;")
        pos_input = QLineEdit()
        pos_input.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 5px; border-radius: 4px;")
        pos_input.setPlaceholderText("Инженер по ОТ")
        form.addRow(pos_label, pos_input)

        # Сохраняем как атрибуты для удобного доступа
        group.fio_input = fio_input
        group.pos_input = pos_input

        return group

    # ============ Кнопки действий ============

    def _create_action_buttons(self):
        """Кнопка «Сгенерировать протокол»."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 5, 0, 5)

        generate_btn = QPushButton("Сгенерировать протокол")
        generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 10px 24px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        generate_btn.clicked.connect(self._generate_protocol)
        layout.addWidget(generate_btn)
        layout.addStretch()

        return widget

    # ============ Диалоги и действия ============

    def _open_programs_dialog(self):
        """Открытие окна «Программы обучения»."""
        dialog = ProgramsDialog(self.programs, self)
        dialog.exec()

    def _save_commission_data(self):
        """Сохранение данных комиссии."""
        data = {
            "org_name": self.org_name_input.text().strip(),
            "order_number": self.order_number_input.text().strip(),
            "order_date": self.order_date_input.text().strip(),
            "exam_date": self.exam_date_input.text().strip(),
            "chairman_fio": self.chairman_fio_input.text().strip(),
            "chairman_position": self.chairman_pos_input.text().strip(),
            "member1_fio": self.member1_fio_input.text().strip(),
            "member1_position": self.member1_pos_input.text().strip(),
            "member2_fio": self.member2_fio_input.text().strip(),
            "member2_position": self.member2_pos_input.text().strip(),
            "member3_fio": self.member3_fio_input.text().strip(),
            "member3_position": self.member3_pos_input.text().strip(),
            "union_fio": self.union_fio_input.text().strip(),
            "union_position": self.union_pos_input.text().strip()
        }

        ok, msg = self.commission.save(data)
        if ok:
            QMessageBox.information(self, "Успех", "Данные комиссии сохранены")
        else:
            QMessageBox.warning(self, "Ошибка", msg)

    def _load_commission_data(self):
        """Загрузка данных комиссии."""
        data = self.commission.load()

        self.org_name_input.setText(data.get("org_name", ""))
        self.order_number_input.setText(data.get("order_number", ""))
        self.order_date_input.setText(data.get("order_date", ""))
        self.exam_date_input.setText(data.get("exam_date", ""))
        self.chairman_fio_input.setText(data.get("chairman_fio", ""))
        self.chairman_pos_input.setText(data.get("chairman_position", ""))
        self.member1_fio_input.setText(data.get("member1_fio", ""))
        self.member1_pos_input.setText(data.get("member1_position", ""))
        self.member2_fio_input.setText(data.get("member2_fio", ""))
        self.member2_pos_input.setText(data.get("member2_position", ""))
        self.member3_fio_input.setText(data.get("member3_fio", ""))
        self.member3_pos_input.setText(data.get("member3_position", ""))
        self.union_fio_input.setText(data.get("union_fio", ""))
        self.union_pos_input.setText(data.get("union_position", ""))

    def _generate_protocol(self):
        """Генерация протокола — получение данных из DataViewTab и передача в exporter."""
        from exporters.protocol_exporter import ProtocolExporter

        # Проверка обязательных полей комиссии
        is_complete, missing = self.commission.is_complete()
        if not is_complete:
            QMessageBox.warning(self, "Ошибка", f"Не заполнены обязательные поля:\n{missing}")
            return

        selected_protocol = self.protocol_combo.currentText()

        # Определяем список протоколов для генерации
        if selected_protocol == "Все":
            # Получаем все уникальные номера протоколов
            if not hasattr(self, 'journal_manager') or self.journal_manager is None:
                QMessageBox.warning(self, "Ошибка", "Журнал недоступен")
                return
            all_records = self.journal_manager.get_all_records()
            protocols = sorted(set(rec.protocol for rec in all_records if rec.protocol))
            if not protocols:
                QMessageBox.warning(self, "Ошибка", "Нет протоколов в журнале")
                return
        else:
            protocols = [selected_protocol]

        # Проверяем, что есть данные для каждого протокола
        protocols_with_data = []
        for proto in protocols:
            worker_records = self._get_worker_records_by_protocol(proto)
            if worker_records:
                protocols_with_data.append(proto)
        
        if not protocols_with_data:
            QMessageBox.warning(self, "Ошибка", f"Нет данных работников для выбранных протоколов")
            return

        # Диалог сохранения
        exam_date = self.exam_date_input.text().strip()
        # Форматируем дату для имени файла
        date_for_filename = ""
        if exam_date:
            try:
                from datetime import datetime
                # Убираем время если есть
                date_part = exam_date.split()[0] if ' ' in exam_date else exam_date
                # Парсим дату в разных форматах
                for fmt in ["%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"]:
                    try:
                        dt = datetime.strptime(date_part, fmt)
                        date_for_filename = dt.strftime("%d-%m-%Y")
                        break
                    except ValueError:
                        continue
            except ValueError:
                pass
        
        # Если date_for_filename пустой, пытаемся хоть как-то обработать
        if not date_for_filename and exam_date:
            date_for_filename = exam_date.replace('.', '-').replace('/', '-').split()[0]
        
        if len(protocols_with_data) == 1:
            if date_for_filename:
                default_file = f"Протокол {protocols_with_data[0]} от {date_for_filename}.docx"
            else:
                default_file = f"Протокол {protocols_with_data[0]}.docx"
        else:
            default_file = "Протоколы.docx"
        
        # Используем полный путь если файл существует и соответствует типу (для "Все" или одиночного)
        if self.last_save_path and os.path.exists(self.last_save_path):
            basename = os.path.basename(self.last_save_path)
            # Проверяем: если "Протоколы" в имени и мы генерируем "Все", или если номер совпадает
            if len(protocols_with_data) == 1:
                # Одиночный - проверяем номер в имени
                if protocols_with_data[0] in basename and "Протоколы" not in basename:
                    default_path = self.last_save_path
                else:
                    default_path = os.path.join(os.path.dirname(self.last_save_path), default_file)
            else:
                # Все - только "Протоколы"
                if "Протоколы" in basename:
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
        
        # Сохраняем путь для следующего раза
        self._save_last_save_path(file_path)

        # Собираем данные комиссии
        commission_data = {
            "org_name": self.org_name_input.text().strip(),
            "order_number": self.order_number_input.text().strip(),
            "order_date": self.order_date_input.text().strip(),
            "exam_date": self.exam_date_input.text().strip(),
            "chairman_fio": self.chairman_fio_input.text().strip(),
            "chairman_position": self.chairman_pos_input.text().strip(),
            "member1_fio": self.member1_fio_input.text().strip(),
            "member1_position": self.member1_pos_input.text().strip(),
            "member2_fio": self.member2_fio_input.text().strip(),
            "member2_position": self.member2_pos_input.text().strip(),
            "member3_fio": self.member3_fio_input.text().strip(),
            "member3_position": self.member3_pos_input.text().strip(),
            "union_fio": self.union_fio_input.text().strip(),
            "union_position": self.union_pos_input.text().strip()
        }

        # Шаблон
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "Protokol_proverki_znanii_OT.docx"
        )

        # Генерируем протоколы
        if len(protocols_with_data) == 1:
            # Один протокол - как раньше
            protocol_number = protocols_with_data[0]
            worker_records = self._get_worker_records_by_protocol(protocol_number)
            
            success, msg = ProtocolExporter.generate_from_commission(
                commission_data=commission_data,
                protocol_number=protocol_number,
                worker_records=worker_records,
                programs_manager=self.programs,
                output_path=file_path,
                template_path=template_path,
                data_dir=self.data_dir
            )

            if success:
                QMessageBox.information(self, "Успех", msg)
            else:
                QMessageBox.warning(self, "Ошибка генерации", msg)
        else:
            # Несколько протоколов - каждый в отдельный файл
            # Выбираем директорию для сохранения
            save_dir = QFileDialog.getExistingDirectory(
                self, "Выберите папку для сохранения протоколов",
                os.path.dirname(file_path) if file_path else ""
            )
            if not save_dir:
                return
            
            saved_count = 0
            for protocol_number in protocols_with_data:
                worker_records = self._get_worker_records_by_protocol(protocol_number)
                if not worker_records:
                    continue
                
                # Формируем имя файла
                exam_date = self.exam_date_input.text().strip()
                date_str = ""
                if exam_date:
                    try:
                        from datetime import datetime
                        date_part = exam_date.split()[0] if ' ' in exam_date else exam_date
                        for fmt in ["%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"]:
                            try:
                                dt = datetime.strptime(date_part, fmt)
                                date_str = "_" + dt.strftime("%d-%m-%Y")
                                break
                            except ValueError:
                                continue
                    except ValueError:
                        pass
                
                output_file = os.path.join(save_dir, f"Протокол {protocol_number}{date_str}.docx")
                
                success, _ = ProtocolExporter.generate_from_commission(
                    commission_data=commission_data,
                    protocol_number=protocol_number,
                    worker_records=worker_records,
                    programs_manager=self.programs,
                    output_path=output_file,
                    template_path=template_path,
                    data_dir=self.data_dir
                )
                
                if success:
                    saved_count += 1
            
            QMessageBox.information(self, "Успех", f"Сохранено протоколов: {saved_count}\nПапка: {save_dir}")

    def _get_worker_records_by_protocol(self, protocol_number: str) -> list:
        """Получение записей работников по номеру протокола из JournalManager."""
        if not hasattr(self, 'journal_manager') or self.journal_manager is None:
            return []

        journal_records = self.journal_manager.get_records_by_protocol(protocol_number)
        
        records = []
        for rec in journal_records:
            record = {
                'last_name': rec.last_name,
                'first_name': rec.first_name,
                'middle_name': rec.middle_name,
                'snils': rec.snils,
                'position': rec.position,
                'employer_inn': '',
                'employer_title': '',
                'tc_inn': '',
                'tc_title': '',
                'result': rec.result,
                'program': rec.program_title,
                'program_id': rec.program_id,
                'date': rec.exam_date,
                'protocol': rec.protocol,
                'base_no': rec.base_no,
            }
            records.append(record)
        return records
