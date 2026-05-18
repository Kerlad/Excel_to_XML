"""
Вкладка «Протокол одиночного работника»
Создание протокола для одного работника с ручным вводом данных
"""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLineEdit, QPushButton,
    QLabel, QMessageBox, QFileDialog, QScrollArea, QDialog, QListWidget,
    QListWidgetItem, QDialogButtonBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from protocol.programs_manager import ProgramsManager
from exporters.protocol_exporter import ProtocolExporter


class SingleWorkerProtocolTab(QWidget):
    """Вкладка для создания протокола одиночного работника."""

    def __init__(self, programs_manager: ProgramsManager, data_dir: str, parent=None):
        super().__init__(parent)
        self.programs = programs_manager
        self.data_dir = data_dir
        self.setStyleSheet("background-color: transparent;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background-color: transparent; border: none;")

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(15)

        scroll_layout.addWidget(self._create_input_group())
        scroll_layout.addWidget(self._create_action_group())

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)

        from protocol.commission_manager import CommissionManager
        self.commission = CommissionManager(data_dir)
        self.commission_data = self.commission.load()

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

    def _create_input_group(self):
        """Группа ввода данных работника."""
        group = QGroupBox()
        group.setStyleSheet(self._group_style())
        group.setTitle("Данные работника")

        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        label_width = 160

        # Фамилия
        row1 = QHBoxLayout()
        label1 = QLabel("Фамилия:")
        label1.setFixedWidth(label_width)
        label1.setAlignment(Qt.AlignmentFlag.AlignRight)
        row1.addWidget(label1)
        self.last_name_input = QLineEdit()
        self.last_name_input.setPlaceholderText("Иванов")
        self.last_name_input.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 5px;")
        row1.addWidget(self.last_name_input)
        row1.addStretch()
        layout.addLayout(row1)

        # Имя
        row2 = QHBoxLayout()
        label2 = QLabel("Имя:")
        label2.setFixedWidth(label_width)
        label2.setAlignment(Qt.AlignmentFlag.AlignRight)
        row2.addWidget(label2)
        self.first_name_input = QLineEdit()
        self.first_name_input.setPlaceholderText("Иван")
        self.first_name_input.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 5px;")
        row2.addWidget(self.first_name_input)
        row2.addStretch()
        layout.addLayout(row2)

        # Отчество
        row3 = QHBoxLayout()
        label3 = QLabel("Отчество:")
        label3.setFixedWidth(label_width)
        label3.setAlignment(Qt.AlignmentFlag.AlignRight)
        row3.addWidget(label3)
        self.middle_name_input = QLineEdit()
        self.middle_name_input.setPlaceholderText("Иванович")
        self.middle_name_input.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 5px;")
        row3.addWidget(self.middle_name_input)
        row3.addStretch()
        layout.addLayout(row3)

        # Должность
        row4 = QHBoxLayout()
        label4 = QLabel("Должность:")
        label4.setFixedWidth(label_width)
        label4.setAlignment(Qt.AlignmentFlag.AlignRight)
        row4.addWidget(label4)
        self.position_input = QLineEdit()
        self.position_input.setPlaceholderText("Слесарь")
        self.position_input.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 5px;")
        row4.addWidget(self.position_input)
        row4.addStretch()
        layout.addLayout(row4)

        # Программы
        row5 = QHBoxLayout()
        label5 = QLabel("Программы:")
        label5.setFixedWidth(label_width)
        label5.setAlignment(Qt.AlignmentFlag.AlignRight)
        row5.addWidget(label5)
        self.programs_input = QLineEdit()
        self.programs_input.setPlaceholderText("1, 3, 18 (через запятую)")
        self.programs_input.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 5px;")
        self.programs_input.setMinimumWidth(200)
        row5.addWidget(self.programs_input)

        help_btn = QPushButton("Справка")
        help_btn.setStyleSheet(self._btn_style())
        help_btn.clicked.connect(self._show_programs_help)
        row5.addWidget(help_btn)
        row5.addStretch()
        layout.addLayout(row5)

        # Дата проверки знаний
        row6 = QHBoxLayout()
        label6 = QLabel("Дата проверки знаний:")
        label6.setFixedWidth(label_width)
        label6.setAlignment(Qt.AlignmentFlag.AlignRight)
        row6.addWidget(label6)
        self.exam_date_input = QLineEdit()
        self.exam_date_input.setPlaceholderText("21.08.2025")
        self.exam_date_input.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 5px;")
        row6.addWidget(self.exam_date_input)
        row6.addStretch()
        layout.addLayout(row6)

        # Номер протокола
        row7 = QHBoxLayout()
        label7 = QLabel("Номер протокола:")
        label7.setFixedWidth(label_width)
        label7.setAlignment(Qt.AlignmentFlag.AlignRight)
        row7.addWidget(label7)
        self.protocol_input = QLineEdit()
        self.protocol_input.setPlaceholderText("1")
        self.protocol_input.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 5px;")
        row7.addWidget(self.protocol_input)
        row7.addStretch()
        layout.addLayout(row7)

        # Рег. номер
        row8 = QHBoxLayout()
        label8 = QLabel("Рег. номер:")
        label8.setFixedWidth(label_width)
        label8.setAlignment(Qt.AlignmentFlag.AlignRight)
        row8.addWidget(label8)
        self.base_no_input = QLineEdit()
        self.base_no_input.setPlaceholderText("12345 (если получен)")
        self.base_no_input.setStyleSheet("color: inherit; border: 1px solid #CCCCCC; padding: 5px;")
        row8.addWidget(self.base_no_input)
        row8.addStretch()
        layout.addLayout(row8)

        return group

    def _create_action_group(self):
        """Группа кнопок действий."""
        group = QGroupBox()
        group.setStyleSheet(self._group_style())
        group.setTitle("Действия")

        layout = QHBoxLayout(group)

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

        return group

    def _show_programs_help(self):
        """Показать справку по программам с выбором."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Программы обучения")
        dialog.setMinimumSize(650, 700)
        layout = QVBoxLayout(dialog)

        list_widget = QListWidget()
        list_widget.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid #CCCCCC;
                background-color: white;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #4169E1;
                color: white;
            }
        """)

        blue_programs = {"1", "2", "3", "4", "18", "23"}
        current_programs = [p.strip() for p in self.programs_input.text().split(',') if p.strip()]

        all_programs = self.programs.get_all_programs()
        for prog_num, prog_info in all_programs.items():
            item = QListWidgetItem()
            hours = prog_info.get('hours', '')
            name = prog_info.get('name', '')
            doc = prog_info.get('doc', '')
            text = f"{prog_num}. {name}"
            if hours:
                text += f" ({hours} ч.)"
            if doc:
                text += f" - {doc}"
            item.setText(text)
            item.setData(Qt.ItemDataRole.UserRole, prog_num)
            if prog_num in current_programs:
                item.setBackground(QColor("#E6F0FF"))
            if prog_num in blue_programs:
                item.setForeground(QColor("#4169E1"))
            list_widget.addItem(item)

        def on_double_click(item):
            prog_num = item.data(Qt.ItemDataRole.UserRole)
            new_programs = current_programs.copy()
            if prog_num and prog_num not in new_programs:
                new_programs.append(prog_num)
                self.programs_input.setText(', '.join(new_programs))

        list_widget.itemDoubleClicked.connect(on_double_click)
        layout.addWidget(list_widget)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Добавить выбранные")
        add_btn.setStyleSheet(self._btn_style())
        add_btn.clicked.connect(lambda: self._add_selected_programs(list_widget, current_programs))
        btn_layout.addWidget(add_btn)

        close_btn = QPushButton("Закрыть")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #666;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #444;
            }
        """)
        close_btn.clicked.connect(dialog.close)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        dialog.exec()

    def _add_selected_programs(self, list_widget, current_programs):
        """Добавить выбранные программы в поле ввода."""
        selected = list_widget.selectedItems()
        if not selected:
            QMessageBox.information(self, "Информация", "Выберите программы из списка")
            return

        new_programs = current_programs.copy()
        for item in selected:
            prog_num = item.data(Qt.ItemDataRole.UserRole)
            if prog_num and prog_num not in new_programs:
                new_programs.append(prog_num)

        self.programs_input.setText(', '.join(new_programs))

    def _generate_protocol(self):
        """Генерация протокола для одного работника."""
        last_name = self.last_name_input.text().strip()
        first_name = self.first_name_input.text().strip()
        middle_name = self.middle_name_input.text().strip()
        position = self.position_input.text().strip()
        programs_str = self.programs_input.text().strip()
        exam_date = self.exam_date_input.text().strip()
        protocol = self.protocol_input.text().strip()
        base_no = self.base_no_input.text().strip()

        if not last_name and not first_name and not position and not programs_str and not exam_date:
            QMessageBox.warning(self, "Ошибка", "Заполните хотя бы одно поле")
            return

        # Парсим программы
        program_ids = []
        if programs_str:
            for p in programs_str.split(','):
                p = p.strip()
                if p and p not in program_ids:
                    program_ids.append(p)

        # Формируем названия программ из programs_manager
        program_titles = []
        for prog_id in program_ids:
            prog = self.programs.get_program(prog_id)
            if prog:
                name = prog.get('name', f'Программа {prog_id}')
                hours = prog.get('hours', '')
                doc = prog.get('doc', '')
                title = name
                if hours:
                    title = f"{hours}-часовая программа {prog_id} \"{name}\""
                elif doc:
                    title = f"{title} - {doc}"
            else:
                title = f'Программа {prog_id}'
            program_titles.append(title)

        # Создаем записи работников - по одной на каждую программу
        worker_records = []
        for i, (prog_id, prog_title) in enumerate(zip(program_ids, program_titles)):
            record = {
                'last_name': last_name,
                'first_name': first_name,
                'middle_name': middle_name,
                'snils': '',
                'position': position,
                'employer_inn': '',
                'employer_title': '',
                'tc_inn': '',
                'tc_title': '',
                'result': 'Удовлетворительно',
                'program': prog_title,
                'program_id': prog_id,
                'date': exam_date,
                'protocol': protocol,
                'base_no': base_no,
            }
            worker_records.append(record)

        # Если программы не указаны, создаем пустую запись
        if not worker_records:
            worker_records = [{
                'last_name': last_name,
                'first_name': first_name,
                'middle_name': middle_name,
                'snils': '',
                'position': position,
                'employer_inn': '',
                'employer_title': '',
                'tc_inn': '',
                'tc_title': '',
                'result': 'Удовлетворительно',
                'program': '',
                'program_id': '',
                'date': exam_date,
                'protocol': protocol,
                'base_no': base_no,
            }]

        # Диалог сохранения
        default_file = f"Протокол_{last_name or 'одиночный'}.docx"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить протокол", default_file, "Word Files (*.docx)"
        )
        if not file_path:
            return

        template_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "Protokol_proverki_znanii_OT.docx"
        )

        success, msg = ProtocolExporter.generate_from_commission(
            commission_data=self.commission_data,
            protocol_number=protocol or "1",
            worker_records=worker_records,
            programs_manager=self.programs,
            output_path=file_path,
            template_path=template_path,
            data_dir=self.data_dir
        )

        if success:
            QMessageBox.information(self, "Успех", f"Протокол сохранён:\n{file_path}")
        else:
            QMessageBox.warning(self, "Ошибка", msg)