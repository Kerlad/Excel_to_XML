import os
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QPushButton,
    QLabel, QMessageBox, QFileDialog, QComboBox, QFrame
)
from PySide6.QtCore import Qt
from protocol.programs_manager import ProgramsManager
from exporters.protocol_exporter import ProtocolExporter

logger = logging.getLogger(__name__)


class SingleWorkerProtocolTab(QWidget):
    def __init__(self, programs_manager: ProgramsManager, data_dir: str, parent=None):
        super().__init__(parent)
        self.programs = programs_manager
        self.data_dir = data_dir
        self.commission_data = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(self._build_worker_form())
        layout.addWidget(self._build_commission_bar())
        layout.addWidget(self._build_preview(), 0)
        layout.addStretch()

        gen_row = QHBoxLayout()
        gen_row.addStretch()
        self.generate_btn = QPushButton("  Сгенерировать протокол")
        self.generate_btn.setObjectName("generateProtocolBtn")
        self.generate_btn.setMinimumHeight(52)
        self.generate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.generate_btn.clicked.connect(self._generate_protocol)
        gen_row.addWidget(self.generate_btn)
        gen_row.addStretch()
        layout.addLayout(gen_row)

        self._update_preview()
        self._load_commission()

    def _build_worker_form(self):
        w = QFrame()
        w.setObjectName("workerFormCard")

        form = QFormLayout(w)
        form.setSpacing(8)
        form.setContentsMargins(12, 12, 12, 12)

        self.last_name_input = QLineEdit()
        self.last_name_input.setPlaceholderText("Иванов")
        self.last_name_input.textChanged.connect(self._update_preview)
        form.addRow("Фамилия:", self.last_name_input)

        self.first_name_input = QLineEdit()
        self.first_name_input.setPlaceholderText("Иван")
        self.first_name_input.textChanged.connect(self._update_preview)
        form.addRow("Имя:", self.first_name_input)

        self.middle_name_input = QLineEdit()
        self.middle_name_input.setPlaceholderText("Иванович")
        self.middle_name_input.textChanged.connect(self._update_preview)
        form.addRow("Отчество:", self.middle_name_input)

        self.position_input = QLineEdit()
        self.position_input.setPlaceholderText("Слесарь")
        form.addRow("Должность:", self.position_input)

        prog_row = QHBoxLayout()
        self.programs_input = QLineEdit()
        self.programs_input.setPlaceholderText("1, 3, 18 (через запятую)")
        prog_row.addWidget(self.programs_input, 1)
        help_btn = QPushButton("Справка")
        help_btn.setObjectName("programHelpBtn")
        help_btn.clicked.connect(self._show_programs_help)
        prog_row.addWidget(help_btn)
        form.addRow("Программы:", prog_row)

        self.exam_date_input = QLineEdit()
        self.exam_date_input.setPlaceholderText("21.08.2025")
        form.addRow("Дата проверки:", self.exam_date_input)

        self.protocol_input = QLineEdit()
        self.protocol_input.setPlaceholderText("1")
        form.addRow("Номер протокола:", self.protocol_input)

        self.result_combo = QComboBox()
        self.result_combo.addItems(["Удовлетворительно", "Неудовлетворительно", "Не сдавал"])
        form.addRow("Результат:", self.result_combo)

        self.base_no_input = QLineEdit()
        self.base_no_input.setPlaceholderText("Регистрационный номер (если получен)")
        form.addRow("Рег. номер:", self.base_no_input)

        return w

    def _build_commission_bar(self):
        bar = QVBoxLayout()
        bar.setSpacing(4)

        row1 = QHBoxLayout()
        row1.setSpacing(8)
        lbl = QLabel("Данные комиссии:")
        lbl.setStyleSheet("font-weight: bold;")
        row1.addWidget(lbl)

        self.commission_label = QLabel("не загружены")
        self.commission_label.setStyleSheet("color: #888;")
        row1.addWidget(self.commission_label, 1)

        load_btn = QPushButton("Загрузить комиссию")
        load_btn.setObjectName("loadCommissionBtn")
        load_btn.setToolTip("Загрузить сохранённые данные комиссии")
        load_btn.clicked.connect(self._load_commission)
        row1.addWidget(load_btn)
        bar.addLayout(row1)

        self.org_details_label = QLabel()
        self.org_details_label.setStyleSheet("color: #555; font-size: 11px;")
        self.org_details_label.setWordWrap(True)
        bar.addWidget(self.org_details_label)

        container = QWidget()
        container.setLayout(bar)
        return container

    def _build_preview(self):
        self.preview_label = QLabel()
        self.preview_label.setObjectName("previewLabel")
        self.preview_label.setWordWrap(True)
        return self.preview_label

    def _update_preview(self):
        last = self.last_name_input.text().strip() or "одиночный"
        proto = self.protocol_input.text().strip() or "1"
        from utils.export_safe import safe_filename_part
        name = f"Протокол_{safe_filename_part(last, 'одиночный')}_№{safe_filename_part(proto, '1')}.docx"
        self.preview_label.setText(f"Файл: {name}")

    def _load_commission(self):
        from protocol.commission_manager import CommissionManager
        cm = CommissionManager(self.data_dir)
        self.commission_data = cm.load()
        org = self.commission_data.get("org_name", "").strip()
        if org:
            self.commission_label.setText(f"загружена (организация: {org})")
            self.commission_label.setStyleSheet("color: #27AE60; font-weight: bold;")
        else:
            self.commission_label.setText("загружена (пустые поля)")
            self.commission_label.setStyleSheet("color: #888;")

        details = []
        if org:
            details.append(f"Организация: {org}")
        if self.commission_data.get("order_number"):
            details.append(f"Приказ №{self.commission_data['order_number']}")
        if self.commission_data.get("chairman_fio"):
            details.append(f"Председатель: {self.commission_data['chairman_fio']}")
        self.org_details_label.setText(" | ".join(details) if details else "")

        if self.commission_data.get("exam_date"):
            self.exam_date_input.setText(self.commission_data["exam_date"])

    def _show_programs_help(self):
        from PySide6.QtWidgets import QDialog, QListWidget, QListWidgetItem, QVBoxLayout, QHBoxLayout
        from PySide6.QtGui import QPalette, QColor

        dialog = QDialog(self)
        dialog.setWindowTitle("Программы обучения")
        dialog.setMinimumSize(600, 500)
        layout = QVBoxLayout(dialog)

        pal = dialog.palette()
        primary = pal.color(QPalette.ColorRole.Highlight)
        current_bg = QColor(primary.red(), primary.green(), primary.blue(), 35)

        lw = QListWidget()
        lw.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        current = [p.strip() for p in self.programs_input.text().split(",") if p.strip()]
        blue = {"1", "2", "3", "4", "18", "23"}
        all_progs = self.programs.get_all_programs()
        for pid, info in all_progs.items():
            parts = [f"{pid}. {info.get('name', '')}"]
            h = info.get("hours", "")
            d = info.get("doc", "")
            if h: parts.append(f"({h} ч.)")
            if d: parts.append(f"- {d}")
            item = QListWidgetItem(" ".join(parts))
            item.setData(Qt.ItemDataRole.UserRole, pid)
            if pid in current:
                item.setBackground(current_bg)
            if pid in blue:
                item.setForeground(primary)
            lw.addItem(item)

        def add_selected():
            sel = lw.selectedItems()
            if not sel:
                return
            new_set = set(current)
            for it in sel:
                new_set.add(it.data(Qt.ItemDataRole.UserRole))
            self.programs_input.setText(", ".join(sorted(new_set, key=lambda x: int(x) if x.isdigit() else 0)))
            dialog.accept()

        lw.itemDoubleClicked.connect(lambda item: (setattr(lw, "_dc_prog", item.data(Qt.ItemDataRole.UserRole)),
            current.append(item.data(Qt.ItemDataRole.UserRole)) or self.programs_input.setText(", ".join(current))))
        layout.addWidget(lw)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("Добавить выбранные")
        add_btn.setObjectName("dialogPrimaryBtn")
        add_btn.clicked.connect(add_selected)
        btn_row.addWidget(add_btn)
        btn_row.addStretch()
        close_btn = QPushButton("Отмена")
        close_btn.setObjectName("dialogDangerBtn")
        close_btn.clicked.connect(dialog.reject)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        dialog.exec()

    def _generate_protocol(self):
        last = self.last_name_input.text().strip()
        first = self.first_name_input.text().strip()
        middle = self.middle_name_input.text().strip()
        position = self.position_input.text().strip()
        prog_str = self.programs_input.text().strip()
        exam_date = self.exam_date_input.text().strip()
        protocol = self.protocol_input.text().strip()
        result = self.result_combo.currentText()
        base_no = self.base_no_input.text().strip()

        if not last and not first and not position and not prog_str and not exam_date:
            QMessageBox.warning(self, "Ошибка", "Заполните хотя бы одно поле")
            return

        program_ids = [p.strip() for p in prog_str.split(",") if p.strip()]
        program_titles = []
        for pid in program_ids:
            prog = self.programs.get_program(pid)
            if prog:
                name = prog.get("name", f"Программа {pid}")
                hours = prog.get("hours", "")
                doc = prog.get("doc", "")
                title = name
                if hours:
                    title = f'{hours}-часовая программа {pid} "{name}"'
                elif doc:
                    title = f"{title} - {doc}"
            else:
                title = f"Программа {pid}"
            program_titles.append(title)

        worker_records = []
        for pid, ptitle in zip(program_ids, program_titles):
            worker_records.append({
                "last_name": last, "first_name": first, "middle_name": middle,
                "snils": "", "position": position,
                "employer_inn": "", "employer_title": "",
                "tc_inn": "", "tc_title": "",
                "result": result, "program": ptitle, "program_id": pid,
                "date": exam_date, "protocol": protocol, "base_no": base_no,
            })

        if not worker_records:
            worker_records.append({
                "last_name": last, "first_name": first, "middle_name": middle,
                "snils": "", "position": position,
                "employer_inn": "", "employer_title": "",
                "tc_inn": "", "tc_title": "",
                "result": result, "program": "", "program_id": "",
                "date": exam_date, "protocol": protocol, "base_no": base_no,
            })

        proto_num = protocol or "1"
        from utils.export_safe import safe_filename_part
        default_file = f"Протокол_{safe_filename_part(last, 'одиночный')}_№{safe_filename_part(proto_num, '1')}.docx"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить протокол", default_file, "Word Files (*.docx)"
        )
        if not file_path:
            return

        from utils.app_paths import get_resource_dir
        template_path = os.path.join(
            get_resource_dir(), "templates",
            "Protokol_proverki_znanii_OT.docx"
        )

        success, msg = ProtocolExporter.generate_from_commission(
            commission_data=self.commission_data,
            protocol_number=proto_num,
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