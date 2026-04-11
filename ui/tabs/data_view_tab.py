"""
Вкладка просмотра данных о работниках
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt

import sys
import os
from typing import Optional

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data_model import DataManager, WorkerRecord


class DataViewTab(QWidget):
    """Вкладка просмотра данных"""

    def __init__(self, data_manager: DataManager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager

        self.setStyleSheet("""
            QWidget {
                font-size: 14px;
            }
            QTableWidget {
                gridline-color: #cccccc;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QPushButton {
                min-height: 35px;
                padding: 8px 16px;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Таблица данных
        self.table = QTableWidget()
        self.table.setColumnCount(13)
        self.table.setHorizontalHeaderLabels([
            'Фамилия', 'Имя', 'Отчество', 'СНИЛС', 'Должность',
            'ИНН Заказчика', 'Наименование ЮЛ Заказчика', 'ИНН УЦ',
            'Наименование УЦ', 'Результат', '№ программы', 'Дата', '№ протокола'
        ])

        # Настройка заголовков
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setStretchLastSection(True)

        layout.addWidget(self.table)

        # Кнопки управления
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)

        self.edit_btn = QPushButton("Редактировать")
        self.edit_btn.clicked.connect(self.edit_record)

        self.delete_btn = QPushButton("Удалить")
        self.delete_btn.clicked.connect(self.delete_record)

        self.clear_btn = QPushButton("Очистить все")
        self.clear_btn.clicked.connect(self.clear_all)

        self.convert_btn = QPushButton("Конвертация в XML")
        self.convert_btn.clicked.connect(self.convert_to_xml)

        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addWidget(self.convert_btn)

        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def refresh_table(self):
        """Обновление таблицы"""
        self.table.setRowCount(0)
        for record in self.data_manager.records:
            row = self.table.rowCount()
            self.table.insertRow(row)
            d = record.to_dict()
            for col, key in enumerate([
                'Фамилия', 'Имя', 'Отчество', 'СНИЛС', 'Должность',
                'ИНН Заказчика', 'Наименование ЮЛ Заказчика', 'ИНН УЦ',
                'Наименование УЦ', 'Результат', '№ программы', 'Дата', '№ протокола'
            ]):
                self.table.setItem(row, col, QTableWidgetItem(d.get(key, '')))

    def get_selected_record(self) -> Optional[WorkerRecord]:
        """Получение выбранной записи"""
        row = self.table.currentRow()
        if row < 0:
            return None

        data = {}
        for col, key in enumerate([
            'Фамилия', 'Имя', 'Отчество', 'СНИЛС', 'Должность',
            'ИНН Заказчика', 'Наименование ЮЛ Заказчика', 'ИНН УЦ',
            'Наименование УЦ', 'Результат', '№ программы', 'Дата', '№ протокола'
        ]):
            item = self.table.item(row, col)
            data[key] = item.text() if item else ''

        return WorkerRecord.from_dict(data)

    def edit_record(self):
        record = self.get_selected_record()
        if not record:
            QMessageBox.warning(self, "Ошибка", "Выберите запись для редактирования")
            return

        # TODO: Реализовать диалог редактирования
        QMessageBox.information(self, "Информация", "Редактирование будет реализовано")

    def delete_record(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите запись для удаления")
            return

        reply = QMessageBox.question(
            self, "Подтверждение",
            "Вы уверены, что хотите удалить?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            del self.data_manager.records[row]
            self.refresh_table()

    def clear_all(self):
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Очистить все данные? Данные удалятся безвозвратно.",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
        )

        if reply == QMessageBox.StandardButton.Ok:
            self.data_manager.clear_all()
            self.refresh_table()

    def convert_to_xml(self):
        if not self.data_manager.records:
            QMessageBox.warning(self, "Ошибка", "Нет данных для конвертации")
            return

        from utils.xml_converter import XMLConverter
        converter = XMLConverter(self.data_manager)

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить XML файл", "", "XML files (*.xml)"
        )

        if file_path:
            success, message = converter.convert(file_path)
            if success:
                QMessageBox.information(self, "Успех", f"XML файл создан:\n{file_path}")
            else:
                QMessageBox.critical(self, "Ошибка", message)