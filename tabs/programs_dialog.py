"""
Диалоговое окно «Программы обучения»
Таблица: № программы, Название, Номер документа, Часы
Двойной клик на ячейки «Номер документа» и «Часы» → диалог ввода
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QMessageBox, QHeaderView, QLineEdit, QAbstractItemView, QLabel
)
from PyQt6.QtCore import Qt


class ProgramsDialog(QDialog):
    """Окно редактирования данных программ обучения."""

    def __init__(self, programs_manager, parent=None):
        super().__init__(parent)
        self.manager = programs_manager
        self.setWindowTitle("Программы обучения")
        self.setMinimumSize(900, 600)
        self.setStyleSheet("background-color: rgba(240, 240, 250, 0.95);")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Подсказка
        hint = QLabel("Двойной клик по ячейке «Номер документа» или «Часы» для редактирования")
        hint.setStyleSheet("color: #666; font-size: 12px; padding: 5px;")
        layout.addWidget(hint)

        # Таблица
        self.table = self._create_table()
        layout.addWidget(self.table)

        # Кнопка сохранения
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Сохранить")
        save_btn.setStyleSheet("""
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
        save_btn.clicked.connect(self._save_and_close)

        cancel_btn = QPushButton("Отмена")
        cancel_btn.setStyleSheet("""
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
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Заполнение таблицы
        self._populate_table()

    def _create_table(self) -> QTableWidget:
        """Создание таблицы программ."""
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["№ программы", "Название", "Номер документа", "Часы"])

        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        table.verticalHeader().setDefaultSectionSize(25)

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

        table.setColumnWidth(0, 100)
        table.setColumnWidth(1, 400)
        table.setColumnWidth(2, 180)
        table.setColumnWidth(3, 80)

        # Двойной клик для редактирования
        table.doubleClicked.connect(self._on_double_click)

        return table

    def _populate_table(self):
        """Заполнение таблицы данными программ."""
        self.table.setRowCount(0)

        programs = self.manager.get_all_programs()
        # Сортируем по номеру
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

                # Подсветка редактируемых ячеек
                if col in [2, 3] and not str(text):
                    item.setForeground(Qt.GlobalColor.gray)
                    item.setText("(двойной клик для ввода)")

                self.table.setItem(row, col, item)

    def _on_double_click(self, index):
        """Обработка двойного клика."""
        col = index.column()

        # Редактируем только колонки 2 (Номер документа) и 3 (Часы)
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

        # Открываем диалог ввода
        new_value = self._show_input_dialog(col_name, current_value, digits_only=(col == 3))

        if new_value is not None:
            self.table.item(row, col).setText(new_value)
            if new_value:
                self.table.item(row, col).setForeground(Qt.GlobalColor.black)

            # Обновляем только в таблице, сохранение — при закрытии диалога
            if col == 2:
                self.manager.programs[prog_id]["doc"] = new_value
            elif col == 3:
                self.manager.programs[prog_id]["hours"] = new_value

    def _show_input_dialog(self, title: str, current_value: str, digits_only: bool = False) -> str:
        """Диалог ввода значения."""
        from PyQt6.QtGui import QPalette, QColor

        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setMinimumWidth(400)

        # Принудительно светлая палитра + QSS для гарантии белого фона
        dialog.setStyleSheet("""
            QDialog {
                background-color: rgb(240, 240, 250);
            }
            QLineEdit {
                background-color: rgb(255, 255, 255);
                color: #1A1A2E;
                padding: 8px 14px;
                border-radius: 12px;
                border: 1px solid rgba(124, 77, 255, 0.15);
            }
            QPushButton {
                background-color: rgba(255, 255, 255, 0.7);
                color: #1A1A2E;
                border: 1px solid rgba(124, 77, 255, 0.15);
                border-radius: 9999px;
                padding: 8px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(124, 77, 255, 0.15);
            }
            QLabel {
                background-color: transparent;
                color: #1A1A2E;
            }
        """)

        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 250))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(26, 26, 46))
        palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Text, QColor(26, 26, 46))
        palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 250))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(26, 26, 46))
        dialog.setPalette(palette)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)

        input_field = QLineEdit()
        input_field.setText(current_value)
        input_field.setPlaceholderText(f"Введите {title.lower()}")
        layout.addWidget(input_field)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("ОК")
        ok_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #B39DDB, stop:1 #FF8A65);
                color: white;
                border: none;
                border-radius: 9999px;
                padding: 8px 20px;
                font-weight: bold;
            }
            QPushButton:hover { opacity: 0.85; }
        """)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setStyleSheet("""
            QPushButton {
                color: #F44336;
                border: 1.5px solid #F44336;
                background-color: transparent;
                border-radius: 9999px;
                padding: 8px 20px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: rgba(244, 67, 54, 0.1); }
        """)

        def on_ok():
            value = input_field.text().strip()
            if digits_only and value:
                try:
                    float(value)
                except ValueError:
                    QMessageBox.warning(dialog, "Ошибка", "Допускается введение только цифр")
                    return
            dialog.accept()

        ok_btn.clicked.connect(on_ok)
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            return input_field.text().strip()
        return None

    def _save_and_close(self):
        """Сохранение и закрытие."""
        ok, msg = self.manager.save()
        if ok:
            self.accept()
        else:
            QMessageBox.warning(self, "Ошибка", msg)
