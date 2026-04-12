"""
Вкладка «Протокол» — формирование протокола проверки знаний
Поля: № протокола, Данные комиссии, Председатель, Члены комиссии, Профсоюз
Кнопки: Сохранить, Загрузить, Программы обучения, Сгенерировать протокол
"""
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QScrollArea, QFileDialog, QMessageBox,
    QFrame, QGridLayout, QDialog
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont
from protocol.commission_manager import CommissionManager
from protocol.programs_manager import ProgramsManager
from tabs.programs_dialog import ProgramsDialog


class ProtocolTab(QWidget):
    def __init__(self, commission_manager: CommissionManager, programs_manager: ProgramsManager,
                 data_dir: str):
        super().__init__()
        self.setStyleSheet("background-color: white;")
        self.commission = commission_manager
        self.programs = programs_manager
        self.data_dir = data_dir

        # Основной layout с прокруткой
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background-color: white; border: none;")

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

    def _group_style(self):
        return """
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
        """Раздел: № протокола, кнопка Программы обучения."""
        group = QGroupBox()
        group.setStyleSheet(self._group_style())
        group.setTitle("Данные протокола")

        layout = QHBoxLayout(group)
        layout.setSpacing(20)

        # № протокола
        form = QFormLayout()
        self.protocol_label = QLabel("№ протокола:")
        self.protocol_label.setStyleSheet("color: black;")
        self.protocol_input = QLineEdit()
        self.protocol_input.setFixedWidth(150)
        self.protocol_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        self.protocol_input.setPlaceholderText("Номер протокола")
        form.addRow(self.protocol_label, self.protocol_input)
        layout.addLayout(form)

        # Кнопка Программы обучения
        programs_btn = QPushButton("Программы обучения")
        programs_btn.setStyleSheet(self._btn_style())
        programs_btn.clicked.connect(self._open_programs_dialog)
        layout.addWidget(programs_btn)

        layout.addStretch()
        return group

    # ============ Раздел: Данные комиссии ============

    def _create_commission_group(self):
        """Раздел: Данные комиссии — организация, приказ, председатель, члены, профсоюз."""
        group = QGroupBox()
        group.setStyleSheet(self._group_style())
        group.setTitle("Данные комиссии")

        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # Строка 1: Название организации + Приказ
        row1 = QHBoxLayout()

        form1 = QFormLayout()
        self.org_name_label = QLabel("Название организации:")
        self.org_name_label.setStyleSheet("color: black;")
        self.org_name_input = QLineEdit()
        self.org_name_input.setMinimumWidth(350)
        self.org_name_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        self.org_name_input.setPlaceholderText("ООО \"Организация\"")
        form1.addRow(self.org_name_label, self.org_name_input)
        row1.addLayout(form1)

        row1.addSpacing(20)

        form2 = QFormLayout()
        self.order_label = QLabel("Приказ о создании комиссии:")
        self.order_label.setStyleSheet("color: black;")

        # Номер и дата приказа
        order_row = QHBoxLayout()
        self.order_number_input = QLineEdit()
        self.order_number_input.setFixedWidth(100)
        self.order_number_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        self.order_number_input.setPlaceholderText("№ приказа")

        self.order_date_input = QLineEdit()
        self.order_date_input.setFixedWidth(120)
        self.order_date_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        self.order_date_input.setPlaceholderText("ДД.ММ.ГГГГ")

        order_row.addWidget(self.order_number_input)
        order_row.addWidget(QLabel("от"))
        order_row.addWidget(self.order_date_input)

        form2.addRow(self.order_label, order_row)
        row1.addLayout(form2)

        row1.addStretch()
        layout.addLayout(row1)

        # Подраздел: Председатель комиссии
        chairman_group = QGroupBox()
        chairman_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #CCCCCC;
                border-radius: 8px;
                margin-top: 8px;
                padding: 10px;
                background-color: white;
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

        chairman_layout = QHBoxLayout(chairman_group)
        chairman_form = QFormLayout()
        self.chairman_fio_label = QLabel("ФИО:")
        self.chairman_fio_label.setStyleSheet("color: black;")
        self.chairman_fio_input = QLineEdit()
        self.chairman_fio_input.setMinimumWidth(250)
        self.chairman_fio_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        self.chairman_fio_input.setPlaceholderText("Иванов И.И.")
        chairman_form.addRow(self.chairman_fio_label, self.chairman_fio_input)

        self.chairman_pos_label = QLabel("Должность:")
        self.chairman_pos_label.setStyleSheet("color: black;")
        self.chairman_pos_input = QLineEdit()
        self.chairman_pos_input.setMinimumWidth(250)
        self.chairman_pos_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        self.chairman_pos_input.setPlaceholderText("Директор")
        chairman_form.addRow(self.chairman_pos_label, self.chairman_pos_input)

        chairman_layout.addLayout(chairman_form)
        chairman_layout.addStretch()
        layout.addWidget(chairman_group)

        # Подраздел: Члены комиссии (2 колонки)
        members_group = QGroupBox()
        members_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #CCCCCC;
                border-radius: 8px;
                margin-top: 8px;
                padding: 10px;
                background-color: white;
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
        from PyQt6.QtWidgets import QGroupBox as QB

        group = QB()
        group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                margin-top: 5px;
                padding: 8px;
                background-color: white;
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

        layout = QHBoxLayout(group)
        form = QFormLayout()

        fio_label = QLabel("ФИО:")
        fio_label.setStyleSheet("color: black;")
        fio_input = QLineEdit()
        fio_input.setMinimumWidth(200)
        fio_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        fio_input.setPlaceholderText("Петров П.П.")
        form.addRow(fio_label, fio_input)

        pos_label = QLabel("Должность:")
        pos_label.setStyleSheet("color: black;")
        pos_input = QLineEdit()
        pos_input.setMinimumWidth(200)
        pos_input.setStyleSheet("color: black; border: 1px solid #CCCCCC; padding: 4px;")
        pos_input.setPlaceholderText("Инженер по ОТ")
        form.addRow(pos_label, pos_input)

        layout.addLayout(form)
        layout.addStretch()

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
        """Генерация протокола — передача данных в exporter."""
        from exporters.protocol_exporter import ProtocolExporter

        # Проверка обязательных полей
        is_complete, missing = self.commission.is_complete()
        if not is_complete:
            QMessageBox.warning(self, "Ошибка", f"Не заполнены обязательные поля:\n{missing}")
            return

        protocol_number = self.protocol_input.text().strip()
        if not protocol_number:
            QMessageBox.warning(self, "Ошибка", "Введите номер протокола")
            return

        # Диалог сохранения
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить протокол",
            f"Протокол_{protocol_number}.xlsx",
            "Excel Files (*.xlsx)"
        )
        if not file_path:
            return

        # Собираем данные комиссии
        commission_data = {
            "org_name": self.org_name_input.text().strip(),
            "order_number": self.order_number_input.text().strip(),
            "order_date": self.order_date_input.text().strip(),
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
            "Protokol_proverki_znanii_OT.xlsx"
        )

        success, msg = ProtocolExporter.generate_from_commission(
            commission_data=commission_data,
            protocol_number=protocol_number,
            programs_manager=self.programs,
            output_path=file_path,
            template_path=template_path,
            data_dir=self.data_dir
        )

        if success:
            QMessageBox.information(self, "Успех", msg)
        else:
            QMessageBox.warning(self, "Ошибка генерации", msg)
