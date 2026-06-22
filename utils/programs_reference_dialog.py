import os
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from utils.constants import PROGRAM_TITLES
from utils.app_paths import get_resource_dir

logger = logging.getLogger(__name__)


class ProgramsReferenceWindow(QWidget):
    """Неблокирующее окно-справочник: номера программ обучения и их названия.

    Это самостоятельное окно верхнего уровня (без родителя), поэтому оно не
    блокирует основное окно программы — справочник можно держать открытым и
    одновременно работать с приложением. Ссылку на экземпляр следует хранить
    у вызывающей стороны, чтобы окно не было удалено сборщиком мусора.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Программы обучения по охране труда")
        self.setWindowFlags(Qt.WindowType.Window)
        self.setMinimumSize(560, 480)

        icon_path = os.path.join(get_resource_dir(), "resources", "ico.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Программы обучения по охране труда")
        title.setStyleSheet("font-size: 15px; font-weight: bold;")
        title.setWordWrap(True)
        layout.addWidget(title)

        hint = QLabel(
            "Номер программы соответствует её наименованию согласно перечню "
            "программ обучения по охране труда. Используйте поле поиска для "
            "быстрой фильтрации по номеру или названию."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: palette(mid); font-size: 12px;")
        layout.addWidget(hint)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Поиск по номеру или названию…")
        self._search.setClearButtonEnabled(True)
        self._search.setMinimumHeight(34)
        self._search.textChanged.connect(self._apply_filter)
        layout.addWidget(self._search)

        self._table = QTableWidget()
        self._table.setColumnCount(2)
        self._table.setHorizontalHeaderLabels(["№", "Наименование программы"])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setAlternatingRowColors(True)
        self._table.setWordWrap(True)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._table, 1)

        self._rows = sorted(PROGRAM_TITLES.items(), key=lambda kv: int(kv[0]))
        self._populate(self._rows)

        footer = QHBoxLayout()
        self._count_label = QLabel()
        self._count_label.setStyleSheet("color: palette(mid); font-size: 12px;")
        footer.addWidget(self._count_label)
        footer.addStretch()
        close_btn = QPushButton("Закрыть")
        close_btn.setObjectName("dialogPrimaryBtn")
        close_btn.setMinimumHeight(34)
        close_btn.setMinimumWidth(120)
        close_btn.clicked.connect(self.close)
        footer.addWidget(close_btn)
        layout.addLayout(footer)

        self._update_count(len(self._rows))

    def _populate(self, items):
        self._table.setRowCount(len(items))
        for r, (num, name) in enumerate(items):
            num_item = QTableWidgetItem(str(num))
            num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            name_item = QTableWidgetItem(str(name))
            self._table.setItem(r, 0, num_item)
            self._table.setItem(r, 1, name_item)
        self._table.resizeRowsToContents()

    def _update_count(self, n: int):
        self._count_label.setText(f"Программ: {n}")

    def _apply_filter(self, text):
        text = (text or "").strip().lower()
        if not text:
            filtered = self._rows
        else:
            filtered = [
                (num, name) for num, name in self._rows
                if text in str(num).lower() or text in str(name).lower()
            ]
        self._populate(filtered)
        self._update_count(len(filtered))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)
