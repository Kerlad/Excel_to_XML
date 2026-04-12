import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget, QMenuBar, QMenu, QMessageBox, QTextEdit, QVBoxLayout, QDialog, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QFont
from tabs.data_entry_tab import DataEntryTab
from tabs.data_view_tab import DataViewTab
from tabs.data_transfer_tab import DataTransferTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Excel-XML для передачи данных в Минтруд")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)

        # Иконка приложения
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ico.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Главное меню
        self._create_menu_bar()

        # Создание вкладок
        self.tabs = QTabWidget()
        self.data_entry_tab = DataEntryTab()
        self.data_view_tab = DataViewTab()
        self.data_transfer_tab = DataTransferTab()
        self.tabs.addTab(self.data_entry_tab, "Внесение данных")
        self.tabs.addTab(self.data_view_tab, "Просмотр данных")
        self.tabs.addTab(self.data_transfer_tab, "Передача данных")

        # Подключение сигнала передачи данных
        self.data_entry_tab.data_loaded.connect(self.data_view_tab.add_data)
        # Подключение callback для проверки дублей
        self.data_entry_tab.get_existing_keys_callback = self.data_view_tab.get_existing_keys

        self.setCentralWidget(self.tabs)

    def _create_menu_bar(self):
        """Создание главного меню."""
        menubar = self.menuBar()

        # Меню "Справка"
        help_menu = menubar.addMenu("Справка")
        help_action = help_menu.addAction("Справка по работе с программой")
        help_action.triggered.connect(self.show_help)

        # Меню "О программе"
        about_menu = menubar.addMenu("О программе")
        about_action = about_menu.addAction("О программе")
        about_action.triggered.connect(self.show_about)

    def show_help(self):
        """Окно справки по работе с программой."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Справка по работе с программой")
        dialog.setMinimumSize(700, 600)

        layout = QVBoxLayout(dialog)

        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setStyleSheet("background-color: white; color: black; border: none;")
        help_text.setHtml("""
        <h2 style="color: #4169E1;">Справка по работе с программой</h2>

        <h3 style="color: #4169E1;">Начало работы</h3>
        <p>При первом запуске заполните данные учебного центра и заказчика на вкладке 
        «Внесение данных». Укажите ИНН и названия организаций — эти данные будут 
        автоматически подставляться в записи работников и использоваться при экспорте 
        в XML. Нажмите «Сохранить данные».</p>

        <h3 style="color: #4169E1;">Ручной ввод данных</h3>
        <p>На вкладке «Внесение данных» в разделе «Ввод данных работника» заполните 
        поля: Фамилия, Имя, Отчество, Должность, СНИЛС (11 цифр), Номер программы 
        (от 1 до 29, кроме 5; несколько программ через запятую), Номер протокола, 
        Результат (выбирается из списка), Дата (ДД.ММ.ГГГГ). Нажмите «Сохранить данные». 
        Кнопка «Справка» рядом с полем «Номер программы» покажет перечень доступных 
        программ — двойной клик добавит номер в поле.</p>

        <h3 style="color: #4169E1;">Загрузка из Excel/XML</h3>
        <p>В разделе «Загрузка данных» нажмите «Выбрать файл», выберите .xlsx, .xls 
        или .xml файл, затем нажмите «Загрузить файл». Данные автоматически появятся 
        на вкладке «Просмотр данных». Если данные уже есть — система предложит 
        объединить или заменить их. Кнопка «Создать шаблон» создаст образец XLSX 
        файла для заполнения.</p>
        <p><b>Примечание:</b> поля ИНН УЦ, Наименование УЦ, ИНН Заказчика, Наименование 
        Заказчика в файле Excel являются <b>необязательными</b>. Если они пусты, 
        система автоматически подставит значения, введённые на вкладке «Внесение данных» 
        в разделе «Данные УЦ и работодателя».</p>

        <h3 style="color: #4169E1;">Конвертация в XML</h3>
        <p>На вкладке «Просмотр данных» проверьте загруженные записи. При необходимости 
        отредактируйте строку (правый клик → Редактировать) или удалите лишнее. 
        Нажмите «Конвертировать» — откроется диалог сохранения XML-файла, 
        соответствующего схеме XSD из папки <code>schema</code>. Без XSD-файла 
        конвертация невозможна.</p>

        <h3 style="color: #4169E1;">Отправка в Минтруд</h3>
        <p>На вкладке «Передача данных» введите API-ключ (32 символа) из личного 
        кабинета на edu.rosmintrud.ru и нажмите «Сохранить ключ». В разделе 
        «Отправка XML» выберите созданный файл и нажмите «Отправить XML на сервер». 
        При успешной загрузке вы получите SetId — уникальный номер набора записей. 
        Сохраните его!</p>
        <p><b>Важно:</b> после загрузки данных на сервер необходимо перейти на сайт 
        edu.rosmintrud.ru, открыть загруженный реестр, вручную указать структурное 
        подразделение и подписать документы усиленной квалифицированной электронной 
        подписью (УКЭП). Без подписи данные не будут переданы в реестр.</p>

        <h3 style="color: #4169E1;">Получение регистрационных номеров</h3>
        <p>После обработки данных на сервере Минтруда используйте раздел «Запрос по SetId» 
        — введите полученный SetId и нажмите «Запросить номера». Система сохранит 
        XLSX-файл с регистрационными номерами (baseNo) всех записей. Для поиска 
        конкретного работника используйте раздел «Запрос по СНИЛС».</p>
        """)

        layout.addWidget(help_text)

        from PyQt6.QtWidgets import QPushButton
        close_btn = QPushButton("Закрыть")
        close_btn.setStyleSheet("""
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
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)

        dialog.exec()

    def show_about(self):
        """Окно «О программе»."""
        dialog = QDialog(self)
        dialog.setWindowTitle("О программе")
        dialog.setMinimumSize(450, 280)

        layout = QVBoxLayout(dialog)

        from PyQt6.QtWidgets import QLabel, QPushButton
        label = QLabel()
        label.setOpenExternalLinks(True)
        label.setStyleSheet("color: black; font-size: 13px;")
        label.setText(
            "<b>Excel-XML для передачи данных в Минтруд</b><br><br>"
            "Система генерации XML-файлов с данными работников, "
            "обученных требованиям охраны труда (постановление 2464), "
            "и отправки данных в информационную систему Минтруда России.<br><br>"
            "<b>Разработчик:</b> Кривоносов Д.А.<br>"
            "<b>При участии:</b> QWEN Studio<br>"
            "<b>Электронная почта:</b> <a href='mailto:denis-krv@yandex.ru'>denis-krv@yandex.ru</a>"
        )
        label.setWordWrap(True)
        layout.addWidget(label)

        close_btn = QPushButton("Закрыть")
        close_btn.setStyleSheet("""
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
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)

        dialog.exec()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
