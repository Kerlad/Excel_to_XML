import sys
import json
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QLineEdit, QPushButton, QTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QFileDialog, QGroupBox, QFormLayout, QSplitter,
    QFrame, QGridLayout, QComboBox, QCheckBox
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont, QIcon
import shutil
import webbrowser
import subprocess


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Система управления сертификатами")
        self.setGeometry(100, 100, 1200, 800)
        
        # Основной виджет и слой
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Создаем табы
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Инициализация данных организаций
        self.org_data = {
            "training_center": {"inn": "", "title": ""},
            "employer": {"inn": "", "title": ""}
        }
        self.load_organization_data()
        
        # Создаем вкладки
        self.create_certificate_tab()
        self.create_employee_tab()
        self.create_settings_tab()
        
    def load_organization_data(self):
        """Загружает данные УЦ и Заказчика из JSON файла"""
        try:
            data_dir = os.path.join(os.getcwd(), 'data')
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
            
            file_path = os.path.join(data_dir, 'org_settings.json')
            
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.org_data = json.load(f)
            else:
                # Создаем файл с пустыми данными
                self.save_organization_data()
                
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить данные организаций: {str(e)}")
    
    def save_organization_data(self):
        """Сохраняет данные УЦ и Заказчика в JSON файл"""
        try:
            data_dir = os.path.join(os.getcwd(), 'data')
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
            
            file_path = os.path.join(data_dir, 'org_settings.json')
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.org_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить данные организаций: {str(e)}")

    def create_certificate_tab(self):
        """Создает вкладку управления сертификатами"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Группа поиска
        search_group = QGroupBox("Поиск сертификата")
        search_layout = QHBoxLayout(search_group)
        
        self.cert_search_input = QLineEdit()
        self.cert_search_input.setPlaceholderText("Введите номер сертификата или ФИО владельца...")
        search_button = QPushButton("Найти")
        search_button.clicked.connect(self.search_certificate)
        
        search_layout.addWidget(self.cert_search_input)
        search_layout.addWidget(search_button)
        
        layout.addWidget(search_group)
        
        # Таблица сертификатов
        self.cert_table = QTableWidget()
        self.cert_table.setColumnCount(6)
        self.cert_table.setHorizontalHeaderLabels([
            "Номер сертификата", "ФИО владельца", "Дата выдачи", 
            "Срок действия", "Статус", "Действия"
        ])
        header = self.cert_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        
        layout.addWidget(self.cert_table)
        
        # Кнопки действий
        button_layout = QHBoxLayout()
        
        add_cert_btn = QPushButton("Добавить сертификат")
        add_cert_btn.clicked.connect(self.add_certificate)
        
        edit_cert_btn = QPushButton("Редактировать сертификат")
        edit_cert_btn.clicked.connect(self.edit_certificate)
        
        delete_cert_btn = QPushButton("Удалить сертификат")
        delete_cert_btn.clicked.connect(self.delete_certificate)
        
        export_cert_btn = QPushButton("Экспорт в Excel")
        export_cert_btn.clicked.connect(self.export_to_excel)
        
        button_layout.addWidget(add_cert_btn)
        button_layout.addWidget(edit_cert_btn)
        button_layout.addWidget(delete_cert_btn)
        button_layout.addWidget(export_cert_btn)
        
        layout.addLayout(button_layout)
        
        self.tabs.addTab(tab, "Сертификаты")
        
    def create_employee_tab(self):
        """Создает вкладку управления сотрудниками"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Левая часть - форма добавления/редактирования
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        employee_form_group = QGroupBox("Информация о сотруднике")
        form_layout = QFormLayout(employee_form_group)
        
        self.employee_name_input = QLineEdit()
        self.employee_position_input = QLineEdit()
        self.employee_department_input = QLineEdit()
        self.employee_email_input = QLineEdit()
        self.employee_phone_input = QLineEdit()
        
        form_layout.addRow("ФИО:", self.employee_name_input)
        form_layout.addRow("Должность:", self.employee_position_input)
        form_layout.addRow("Отдел:", self.employee_department_input)
        form_layout.addRow("Email:", self.employee_email_input)
        form_layout.addRow("Телефон:", self.employee_phone_input)
        
        left_layout.addWidget(employee_form_group)
        
        # Кнопки действий для сотрудников
        employee_buttons_layout = QHBoxLayout()
        
        add_emp_btn = QPushButton("Добавить сотрудника")
        add_emp_btn.clicked.connect(self.add_employee)
        
        edit_emp_btn = QPushButton("Редактировать сотрудника")
        edit_emp_btn.clicked.connect(self.edit_employee)
        
        delete_emp_btn = QPushButton("Удалить сотрудника")
        delete_emp_btn.clicked.connect(self.delete_employee)
        
        employee_buttons_layout.addWidget(add_emp_btn)
        employee_buttons_layout.addWidget(edit_emp_btn)
        employee_buttons_layout.addWidget(delete_emp_btn)
        
        left_layout.addLayout(employee_buttons_layout)
        
        # Правая часть - таблица сотрудников
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        self.employee_table = QTableWidget()
        self.employee_table.setColumnCount(5)
        self.employee_table.setHorizontalHeaderLabels([
            "ФИО", "Должность", "Отдел", "Email", "Телефон"
        ])
        right_layout.addWidget(self.employee_table)
        
        # Разделитель
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 600])
        
        layout.addWidget(splitter)
        
        self.tabs.addTab(tab, "Сотрудники")
        
    def create_settings_tab(self):
        """Создает вкладку настроек"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Группа настроек УЦ
        uc_group = QGroupBox("Данные учебного центра (УЦ)")
        uc_layout = QFormLayout(uc_group)
        
        self.uc_title_input = QLineEdit(self.org_data["training_center"]["title"])
        self.uc_inn_input = QLineEdit(self.org_data["training_center"]["inn"])
        
        uc_layout.addRow("Наименование:", self.uc_title_input)
        uc_layout.addRow("ИНН:", self.uc_inn_input)
        
        layout.addWidget(uc_group)
        
        # Группа настроек Заказчика
        employer_group = QGroupBox("Данные заказчика")
        employer_layout = QFormLayout(employer_group)
        
        self.employer_title_input = QLineEdit(self.org_data["employer"]["title"])
        self.employer_inn_input = QLineEdit(self.org_data["employer"]["inn"])
        
        employer_layout.addRow("Наименование:", self.employer_title_input)
        employer_layout.addRow("ИНН:", self.employer_inn_input)
        
        layout.addWidget(employer_group)
        
        # Кнопка сохранения
        save_settings_btn = QPushButton("Сохранить данные")
        save_settings_btn.clicked.connect(self.save_settings)
        
        layout.addWidget(save_settings_btn)
        
        # Информационная панель
        info_group = QGroupBox("Информация")
        info_layout = QVBoxLayout(info_group)
        
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setPlainText(
            "Здесь можно настроить основные параметры системы:\n\n"
            "• Данные учебного центра (УЦ) - используются при генерации сертификатов\n"
            "• Данные заказчика - информация об организации-заказчике\n\n"
            "Все изменения сохраняются автоматически в файл org_settings.json"
        )
        
        info_layout.addWidget(info_text)
        layout.addWidget(info_group)
        
        self.tabs.addTab(tab, "Настройки")
        
    def search_certificate(self):
        """Поиск сертификата"""
        search_text = self.cert_search_input.text().strip()
        # Реализация поиска будет добавлена позже
        QMessageBox.information(self, "Поиск", f"Поиск по запросу: {search_text}")
        
    def add_certificate(self):
        """Добавление нового сертификата"""
        QMessageBox.information(self, "Добавление", "Функция добавления сертификата")
        
    def edit_certificate(self):
        """Редактирование выбранного сертификата"""
        selected_row = self.cert_table.currentRow()
        if selected_row >= 0:
            cert_number = self.cert_table.item(selected_row, 0).text()
            QMessageBox.information(self, "Редактирование", f"Редактирование сертификата: {cert_number}")
        else:
            QMessageBox.warning(self, "Внимание", "Выберите сертификат для редактирования")
            
    def delete_certificate(self):
        """Удаление выбранного сертификата"""
        selected_row = self.cert_table.currentRow()
        if selected_row >= 0:
            reply = QMessageBox.question(
                self, "Подтверждение", 
                "Вы уверены, что хотите удалить выбранный сертификат?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.cert_table.removeRow(selected_row)
        else:
            QMessageBox.warning(self, "Внимание", "Выберите сертификат для удаления")
            
    def export_to_excel(self):
        """Экспорт данных в Excel"""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить как", "", "Excel Files (*.xlsx);;All Files (*)", options=options
        )
        if file_path:
            # Реализация экспорта будет добавлена позже
            QMessageBox.information(self, "Экспорт", f"Данные экспортированы в: {file_path}")
            
    def add_employee(self):
        """Добавление нового сотрудника"""
        name = self.employee_name_input.text().strip()
        if name:
            row_position = self.employee_table.rowCount()
            self.employee_table.insertRow(row_position)
            
            self.employee_table.setItem(row_position, 0, QTableWidgetItem(name))
            self.employee_table.setItem(row_position, 1, QTableWidgetItem(self.employee_position_input.text()))
            self.employee_table.setItem(row_position, 2, QTableWidgetItem(self.employee_department_input.text()))
            self.employee_table.setItem(row_position, 3, QTableWidgetItem(self.employee_email_input.text()))
            self.employee_table.setItem(row_position, 4, QTableWidgetItem(self.employee_phone_input.text()))
            
            # Очистка полей после добавления
            self.clear_employee_form()
        else:
            QMessageBox.warning(self, "Внимание", "Введите ФИО сотрудника")
            
    def edit_employee(self):
        """Редактирование выбранного сотрудника"""
        selected_row = self.employee_table.currentRow()
        if selected_row >= 0:
            # Заполнение формы данными из выбранной строки
            self.employee_name_input.setText(self.employee_table.item(selected_row, 0).text())
            self.employee_position_input.setText(self.employee_table.item(selected_row, 1).text())
            self.employee_department_input.setText(self.employee_table.item(selected_row, 2).text())
            self.employee_email_input.setText(self.employee_table.item(selected_row, 3).text())
            self.employee_phone_input.setText(self.employee_table.item(selected_row, 4).text())
        else:
            QMessageBox.warning(self, "Внимание", "Выберите сотрудника для редактирования")
            
    def delete_employee(self):
        """Удаление выбранного сотрудника"""
        selected_row = self.employee_table.currentRow()
        if selected_row >= 0:
            reply = QMessageBox.question(
                self, "Подтверждение", 
                "Вы уверены, что хотите удалить выбранного сотрудника?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.employee_table.removeRow(selected_row)
        else:
            QMessageBox.warning(self, "Внимание", "Выберите сотрудника для удаления")
            
    def clear_employee_form(self):
        """Очистка формы сотрудника"""
        self.employee_name_input.clear()
        self.employee_position_input.clear()
        self.employee_department_input.clear()
        self.employee_email_input.clear()
        self.employee_phone_input.clear()
        
    def save_settings(self):
        """Сохранение настроек УЦ и Заказчика"""
        # Обновляем данные из полей ввода
        self.org_data["training_center"]["title"] = self.uc_title_input.text().strip()
        self.org_data["training_center"]["inn"] = self.uc_inn_input.text().strip()
        self.org_data["employer"]["title"] = self.employer_title_input.text().strip()
        self.org_data["employer"]["inn"] = self.employer_inn_input.text().strip()
        
        # Сохраняем в файл
        self.save_organization_data()
        
        QMessageBox.information(self, "Сохранено", "Данные успешно сохранены!")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()