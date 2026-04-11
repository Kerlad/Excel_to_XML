"""
Вкладка отправки данных на сервер Минтруда
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QFileDialog, QMessageBox, QGroupBox)
from PyQt6.QtCore import Qt

import sys
import os
import json

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data_model import DataManager


class SendDataTab(QWidget):
    """Вкладка отправки данных"""

    def __init__(self, data_manager: DataManager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager

        self.setStyleSheet("""
            QWidget {
                font-size: 14px;
            }
            QLineEdit {
                min-height: 30px;
                padding: 5px;
            }
            QPushButton {
                min-height: 35px;
                padding: 8px 16px;
                min-width: 150px;
            }
            QGroupBox {
                margin-top: 15px;
                padding-top: 15px;
                font-weight: bold;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # Раздел API ключа
        api_group = QGroupBox("API ключ")
        api_layout = QHBoxLayout()

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setPlaceholderText("Введите 32-символьный API ключ")
        self.api_key_edit.setMaxLength(32)

        self.save_api_btn = QPushButton("Сохранить ключ")
        self.save_api_btn.clicked.connect(self.save_api_key)

        api_layout.addWidget(QLabel("API ключ:"))
        api_layout.addWidget(self.api_key_edit)
        api_layout.addWidget(self.save_api_btn)

        api_group.setLayout(api_layout)
        layout.addWidget(api_group)

        # Раздел отправки XML
        send_group = QGroupBox("Отправка XML")
        send_layout = QVBoxLayout()

        self.xml_file_edit = QLineEdit()
        self.xml_file_edit.setReadOnly(True)
        self.xml_file_edit.setPlaceholderText("Выберите XML файл для отправки")

        browse_layout = QHBoxLayout()
        browse_layout.addWidget(self.xml_file_edit)

        self.browse_btn = QPushButton("Обзор")
        self.browse_btn.clicked.connect(self.browse_xml_file)
        browse_layout.addWidget(self.browse_btn)

        self.send_btn = QPushButton("Отправить XML на сервер")
        self.send_btn.clicked.connect(self.send_xml)

        send_layout.addLayout(browse_layout)
        send_layout.addWidget(self.send_btn)

        send_group.setLayout(send_layout)
        layout.addWidget(send_group)

        # Раздел запроса номеров
        request_group = QGroupBox("Запрос номеров")
        request_layout = QHBoxLayout()

        self.setid_edit = QLineEdit()
        self.setid_edit.setPlaceholderText("Введите номер набора (Setid)")

        self.request_btn = QPushButton("Запросить номера")
        self.request_btn.clicked.connect(self.request_numbers)

        request_layout.addWidget(QLabel("SetId:"))
        request_layout.addWidget(self.setid_edit)
        request_layout.addWidget(self.request_btn)

        request_group.setLayout(request_layout)
        layout.addWidget(request_group)

        layout.addStretch()
        self.setLayout(layout)

    def save_api_key(self):
        api_key = self.api_key_edit.text().strip()
        if len(api_key) != 32:
            QMessageBox.warning(self, "Ошибка", "API ключ должен содержать 32 символа")
            return

        self.data_manager.api_key = api_key

        # Сохранение в файл
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'data', 'config.json'
        )
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

        # В реальном приложении нужно шифрование
        with open(config_path, 'w') as f:
            json.dump({'api_key': api_key}, f)

        QMessageBox.information(self, "Успех", "API ключ сохранен")

    def browse_xml_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите XML файл", "", "XML files (*.xml)"
        )
        if file_path:
            self.xml_file_edit.setText(file_path)

    def send_xml(self):
        xml_file = self.xml_file_edit.text().strip()
        if not xml_file:
            QMessageBox.warning(self, "Ошибка", "Выберите XML файл")
            return

        if not self.data_manager.api_key:
            QMessageBox.warning(self, "Ошибка", "Введите API ключ")
            return

        from utils.mintrud_api import MinTrudAPI
        api = MinTrudAPI(self.data_manager.api_key)

        success, result = api.send_xml(xml_file)

        if success:
            QMessageBox.information(
                self, "Успех",
                f"Данные загружены на сервер\n\nЗапишите номер набора: {result}"
            )
        else:
            QMessageBox.critical(self, "Ошибка", result)

    def request_numbers(self):
        setid = self.setid_edit.text().strip()
        if not setid:
            QMessageBox.warning(self, "Ошибка", "Введите SetId")
            return

        if not self.data_manager.api_key:
            QMessageBox.warning(self, "Ошибка", "Введите API ключ")
            return

        from utils.mintrud_api import MinTrudAPI
        api = MinTrudAPI(self.data_manager.api_key)

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить отчет", "", "Excel files (*.xlsx)"
        )

        if file_path:
            success, result = api.request_by_setid(setid, file_path)
            if success:
                QMessageBox.information(self, "Успех", f"Отчет сохранен:\n{file_path}")
            else:
                QMessageBox.critical(self, "Ошибка", result)