"""
Диалоговое окно «Программы обучения»
Таблица: № программы, Название, Номер документа, Часы
Двойной клик на ячейки «Номер документа» и «Часы» → диалог ввода
"""
from typing import Optional
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QMessageBox, QHeaderView, QLineEdit, QAbstractItemView, QLabel
)
from PySide6.QtCore import Qt
from utils.dialog_base import BaseDialog
from utils.toast import Toast


class ProgramsDialog(BaseDialog):
    """Окно редактирования данных программ обучения."""

    def __init__(self, programs_manager, parent=None):
        super().__init__(parent, title="Программы обучения", min_width=900, min_height=600)
        self.manager = programs_manager

        bl = self.body_layout()

        hint = QLabel("Двойной клик по ячейке «Номер документа» или «Часы» для редактирования")
        hint.setObjectName("programsHint")
        bl.addWidget(hint)

        self.table = self._create_table()
        bl.addWidget(self.table)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Сохранить")
        save_btn.setObjectName("dialogPrimaryBtn")
        save_btn.clicked.connect(self._save_and_close)

        cancel_btn = QPushButton("Отмена")
        cancel_btn.setObjectName("dialogDangerBtn")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()
        bl.addLayout(btn_layout)

        self._populate_table()

    def _create_table(self) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["№ программы", "Название", "Номер документа", "Часы"])

        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        table.verticalHeader().setDefaultSectionSize(25)
        table.verticalHeader().setVisible(False)

        table.setColumnWidth(0, 100)
        table.setColumnWidth(1, 400)
        table.setColumnWidth(2, 180)
        table.setColumnWidth(3, 80)

        table.doubleClicked.connect(self._on_double_click)
        return table

    def _populate_table(self):
        self.table.setRowCount(0)
        programs = self.manager.get_all_programs()
        sorted_ids = sorted(programs.keys(), key=lambda x: int(x) if x.isdigit() else 0)

        for prog_id in sorted_ids:
            prog = programs[prog_id]
            row = self.table.rowCount()
            self.table.insertRow(row)

            items = [
                prog_id,
                prog.get("name", ""),
                prog.get("doc", ""),
                prog.get("hours", "")
            ]

            for col, text in enumerate(items):
                item = QTableWidgetItem(str(text))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col in [2, 3] and not str(text):
                    item.setForeground(Qt.GlobalColor.gray)
                    item.setText("(двойной клик для ввода)")
                self.table.setItem(row, col, item)

    def _on_double_click(self, index):
        col = index.column()
        if col not in [2, 3]:
            return

        row = index.row()
        prog_id_item = self.table.item(row, 0)
        if not prog_id_item:
            return

        prog_id = prog_id_item.text()
        current_value = self.table.item(row, col).text() if self.table.item(row, col) else ""
        if current_value == "(двойной клик для ввода)":
            current_value = ""

        col_name = "Номер документа" if col == 2 else "Часы"
        new_value = self._show_input_dialog(col_name, current_value, digits_only=(col == 3))

        if new_value is not None:
            self.table.item(row, col).setText(new_value)
            if new_value:
                self.table.item(row, col).setForeground(Qt.GlobalColor.black)
            if col == 2:
                self.manager.programs[prog_id]["doc"] = new_value
            elif col == 3:
                self.manager.programs[prog_id]["hours"] = new_value

    def _show_input_dialog(self, title: str, current_value: str, digits_only: bool = False) -> Optional[str]:
        dialog = BaseDialog(self, title=title, min_width=400, min_height=150)
        bl = dialog.body_layout()

        input_field = QLineEdit()
        input_field.setText(current_value)
        input_field.setPlaceholderText(f"Введите {title.lower()}")
        bl.addWidget(input_field)

        ok_btn = QPushButton("ОК")
        ok_btn.setObjectName("dialogPrimaryBtn")
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setObjectName("dialogDangerBtn")

        result = [None]

        def on_ok():
            value = input_field.text().strip()
            if digits_only and value:
                try:
                    float(value)
                except ValueError:
                    from utils.error_utils import show_error_dialog
                    show_error_dialog(dialog, "Ошибка", "Допускается введение только цифр")
                    return
            result[0] = value
            dialog.accept()

        ok_btn.clicked.connect(on_ok)
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()
        bl.addLayout(btn_layout)

        dialog.exec()
        return result[0]

    def _save_and_close(self):
        ok, msg = self.manager.save()
        if ok:
            Toast.success(self, "Программы сохранены")
            self.accept()
        else:
            from utils.error_utils import show_error_dialog
            show_error_dialog(self, "Ошибка", msg)
