"""
Основное окно приложения с вкладками
"""

from PyQt6.QtWidgets import (QMainWindow, QTabWidget, QWidget, QVBoxLayout,
                             QToolBar, QStatusBar, QMenu, QMenuBar, QMessageBox)
from PyQt6.QtGui import QFont, QIcon, QAction
from PyQt6.QtCore import Qt

import sys
import os

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data_model import DataManager
from ui.tabs.data_entry_tab import DataEntryTab
from ui.tabs.data_view_tab import DataViewTab
from ui.tabs.send_data_tab import SendDataTab


class MainWindow(QMainWindow):
    """Главное окно приложения"""

    def __init__(self):
        super().__init__()

        self.data_manager = DataManager()

        self.setWindowTitle("Система Excel-XML для Минтруда")
        self.setMinimumSize(1200, 800)

        # Настройка HiDPI
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                border-radius: 5px;
            }
            QTabBar::tab {
                background-color: #e0e0e0;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
            }
            QTabBar::tab:hover {
                background-color: #f0f0f0;
            }
        """)

        # Центральная виджет с вкладками
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        central_widget.setLayout(main_layout)

        # Вкладки
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(False)
        self.tabs.setMovable(False)

        self.data_entry_tab = DataEntryTab(self.data_manager, self)
        self.data_view_tab = DataViewTab(self.data_manager, self)
        self.send_data_tab = SendDataTab(self.data_manager, self)

        self.tabs.addTab(self.data_entry_tab, "Внесение данных")
        self.tabs.addTab(self.data_view_tab, "Просмотр данных")
        self.tabs.addTab(self.send_data_tab, "Отправка данных")

        main_layout.addWidget(self.tabs)

        # Статус бар
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Готов к работе")

        # Меню
        self.create_menu()

    def create_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("Файл")

        exit_action = QAction("Выход", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = menubar.addMenu("Справка")

        about_action = QAction("О программе", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def show_about(self):
        QMessageBox.about(
            self, "О программе",
            "Система Excel-XML для передачи данных в Минтруд\n\n"
            "Версия 1.0\n\n"
            "Разработано для автоматизации внесения информации о работниках "
            "в базу данных Минтруда."
        )

    def on_data_updated(self):
        """Обновление данных во вкладке просмотра"""
        self.data_view_tab.refresh_table()