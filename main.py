import sys
import os
import logging
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget, QMenuBar, QMenu, QMessageBox, QTextEdit, QVBoxLayout, QDialog, QLabel, QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QFont, QPalette, QColor
from tabs.data_entry_tab import DataEntryTab
from tabs.data_view_tab import DataViewTab
from tabs.data_transfer_tab import DataTransferTab
from tabs.exam_journal_tab import ExamJournalTab
from tabs.protocol_tab import ProtocolTab
from journal.journal_manager import JournalManager
from protocol.commission_manager import CommissionManager
from protocol.programs_manager import ProgramsManager
from utils.logger import setup_logging
from utils.tahoe_style import get_global_stylesheet, apply_mica, load_theme, save_theme


class MainWindow(QMainWindow):
    def __init__(self, app=None):
        super().__init__()
        self.app = app
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.current_theme = load_theme(self.base_dir)
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
        #self.data_transfer_tab_urllib = DataTransferTabUrllib()
        #self.data_transfer_tab_httpx = DataTransferTabHttpx()
        #self.data_transfer_tab_pycurl = DataTransferTabPycurl()
        #self.data_transfer_tab_wininet = DataTransferTabWininet()

        # Журнал проверки знаний
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        self.journal_manager = JournalManager(data_dir)
        self.exam_journal_tab = ExamJournalTab(self.journal_manager, data_dir)

        # Менеджеры для протокола
        self.commission_manager = CommissionManager(data_dir)
        self.programs_manager = ProgramsManager(data_dir)
        self.protocol_tab = ProtocolTab(self.commission_manager, self.programs_manager, data_dir, self.journal_manager)
        self.protocol_tab.set_data_source(self.data_view_tab)

        self.tabs.addTab(self.data_entry_tab, "Внесение данных")
        self.tabs.addTab(self.data_view_tab, "Просмотр данных")
        self.tabs.addTab(self.data_transfer_tab, "Передача данных")
        #self.tabs.addTab(self.data_transfer_tab_urllib, "Передача данных (urllib)")
        #self.tabs.addTab(self.data_transfer_tab_httpx, "Передача данных (httpx)")
        #self.tabs.addTab(self.data_transfer_tab_pycurl, "Передача данных (pycurl)")
        #self.tabs.addTab(self.data_transfer_tab_wininet, "Передача данных (WinINET)")
        self.tabs.addTab(self.exam_journal_tab, "Журнал проверки знаний")
        self.tabs.addTab(self.protocol_tab, "Протокол")

        # Подключение сигнала передачи данных
        self.data_entry_tab.data_loaded.connect(self.data_view_tab.add_data)
        # Подключение callback для проверки дублей
        self.data_entry_tab.get_existing_keys_callback = self.data_view_tab.get_existing_keys

        # Подключение журнала к вкладке передачи данных
        self.data_transfer_tab.set_journal_callback(self.exam_journal_tab.add_records_to_journal, self.exam_journal_tab.update_base_no)
        #self.data_transfer_tab_urllib.set_journal_callback(self.exam_journal_tab.add_records_to_journal, self.exam_journal_tab.update_base_no)
        #self.data_transfer_tab_httpx.set_journal_callback(self.exam_journal_tab.add_records_to_journal, self.exam_journal_tab.update_base_no)
        #self.data_transfer_tab_pycurl.set_journal_callback(self.exam_journal_tab.add_records_to_journal, self.exam_journal_tab.update_base_no)
        #self.data_transfer_tab_wininet.set_journal_callback(self.exam_journal_tab.add_records_to_journal, self.exam_journal_tab.update_base_no)

        self.setCentralWidget(self.tabs)

    def _apply_theme(self, theme: str):
        """Применение темы (light/dark) ко всему приложению."""
        self.current_theme = theme
        save_theme(self.base_dir, theme)

        if self.app:
            # Обновляем палитру
            if theme == "dark":
                palette = QPalette()
                palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 42))
                palette.setColor(QPalette.ColorRole.WindowText, QColor(232, 232, 240))
                palette.setColor(QPalette.ColorRole.Base, QColor(40, 40, 55))
                palette.setColor(QPalette.ColorRole.AlternateBase, QColor(35, 35, 50))
                palette.setColor(QPalette.ColorRole.Text, QColor(232, 232, 240))
                palette.setColor(QPalette.ColorRole.Button, QColor(40, 40, 55))
                palette.setColor(QPalette.ColorRole.ButtonText, QColor(232, 232, 240))
                palette.setColor(QPalette.ColorRole.Highlight, QColor(179, 136, 255))
                palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
            else:
                palette = QPalette()
                palette.setColor(QPalette.ColorRole.Window, QColor(245, 245, 250))
                palette.setColor(QPalette.ColorRole.WindowText, QColor(26, 26, 46))
                palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
                palette.setColor(QPalette.ColorRole.AlternateBase, QColor(240, 240, 250))
                palette.setColor(QPalette.ColorRole.Text, QColor(26, 26, 46))
                palette.setColor(QPalette.ColorRole.Button, QColor(245, 245, 250))
                palette.setColor(QPalette.ColorRole.ButtonText, QColor(26, 26, 46))
                palette.setColor(QPalette.ColorRole.Highlight, QColor(124, 77, 255))
                palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
            self.app.setPalette(palette)
            self.app.setStyleSheet(get_global_stylesheet(theme))

            # Обновляем стили всех виджетов
            self._refresh_styles()

    def _refresh_styles(self):
        """Обновление стилей всех виджетов при смене темы."""
        # unpolish/polish для MainWindow и всех дочерних
        for w in self.findChildren(QWidget):
            w.style().unpolish(w)
            w.style().polish(w)
        self.style().unpolish(self)
        self.style().polish(self)

    def _create_menu_bar(self):
        """Создание главного меню."""
        menubar = self.menuBar()

        # Меню "Настройки"
        settings_menu = menubar.addMenu("Настройки")
        theme_action = settings_menu.addAction("Светлая тема" if self.current_theme == "dark" else "Тёмная тема")
        theme_action.triggered.connect(self._toggle_theme)

        # Меню "Справка"
        help_menu = menubar.addMenu("Справка")
        help_action = help_menu.addAction("Справка по работе с программой")
        help_action.triggered.connect(self.show_help)

        # Меню "О программе"
        about_menu = menubar.addMenu("О программе")
        about_action = about_menu.addAction("О программе")
        about_action.triggered.connect(self.show_about)

    def _toggle_theme(self):
        """Переключение темы."""
        new_theme = "light" if self.current_theme == "dark" else "dark"
        self._apply_theme(new_theme)
        # Обновляем текст пункта меню
        menubar = self.menuBar()
        settings_menu = menubar.actions()[0].menu()  # первое меню = Настройки
        settings_menu.actions()[0].setText("Светлая тема" if new_theme == "dark" else "Тёмная тема")

    def show_help(self):
        """Окно справки по работе с программой."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Справка по работе с программой")
        dialog.setMinimumSize(700, 650)

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

        <h3 style="color: #4169E1;">Просмотр и редактирование</h3>
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

        <h3 style="color: #4169E1;">Настройки прокси</h3>
        <p>На вкладке «Передача данных» в разделе «Настройки прокси» выберите режим
        подключения: «Без прокси» (прямое), «Авто (системные)» — использует прокси
        из настроек Windows, или «Вручную» — укажите адрес, логин и пароль прокси.</p>

        <h3 style="color: #4169E1;">Получение регистрационных номеров</h3>
        <p>После обработки данных на сервере Минтруда используйте раздел «Запрос по SetId»
        — введите полученный SetId и нажмите «Запросить номера». Система сохранит
        XLSX-файл с регистрационными номерами (baseNo) всех записей. Для поиска
        конкретного работника используйте раздел «Запрос по СНИЛС».</p>

        <h3 style="color: #4169E1;">Журнал проверки знаний</h3>
        <p>На вкладке «Журнал проверки знаний» хранится история всех отправок XML на сервер
        Минтруда. Каждая запись содержит: дату отправки, SetId, ФИО, СНИЛС, должность,
        номер и название программы, дату экзамена, номер протокола, SetId и
        регистрационный номер (baseNo).</p>
        <p><b>Поиск и фильтрация:</b> используйте панель поиска — можно фильтровать по
        ФИО/СНИЛС, SetId, статусу (ожидает/получен), номеру протокола
        и диапазону дат отправки. Кнопка «Сбросить» очищает все фильтры.</p>
        <p><b>Статусы записей:</b> «ожидает» (оранжевый) — XML отправлен, но рег. номер
        ещё не получен; «получен» (зелёный) — рег. номер подтянут автоматически
        после запроса по SetId.</p>
        <p><b>Экспорт в XLSX:</b> нажмите «Экспорт в XLSX» для сохранения отфильтрованных
        записей в Excel-файл. <b>Удаление:</b> выберите строки → кнопка «Удалить»
        или правый клик → «Удалить».</p>

        <h3 style="color: #4169E1;">Формирование протокола</h3>
        <p>На вкладке «Протокол» заполните данные комиссии и сформируйте протокол
        проверки знаний по шаблону.</p>
        <p><b>Данные комиссии:</b> введите название организации, номер протокола, дату
        проверки знаний, номер и дату приказа о создании комиссии. Заполните ФИО и
        должности председателя, членов комиссии №1, №2, №3 и представителя профсоюза.
        Нажмите «Сохранить данные комиссии» — данные сохранятся между сессиями.</p>
        <p><b>Программы обучения:</b> кнопка «Программы обучения» открывает окно для
        редактирования номеров документов и часов обучения по каждой программе
        (двойной клик по ячейке).</p>
        <p><b>Генерация протокола:</b> выберите номер протокола из выпадающего списка
        или «Все» для генерации всех протоколов. При выборе номера протокола
        автоматически заполняется поле «Дата проверки знаний» из Журнала.</p>
        <p>Нажмите «Сгенерировать протокол» — система найдёт работников с указанным
        номером протокола из журнала, заполнит шаблон <code>Protokol_proverki_znanii_OT.docx</code>
        данными комиссии и работников, и сохранит итоговый файл.</p>
        <p><b>Имена файлов:</b></p>
        <ul>
        <li>Одиночный протокол: «Протокол {номер} от {дата}.docx» (например, «Протокол 1 от 21-08-2025.docx»)</li>
        <li>При выборе «Все» — каждый протокол сохраняется в отдельный файл в выбранную папку</li>
        </ul>
        <p><b>Обязательные поля:</b> номер протокола, название организации,
        номер приказа, ФИО председателя.</p>
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
        dialog.setMinimumSize(480, 320)

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
            "<b>При участии:</b> QWEN Studio, OpenCode (free AI)<br>"
            "<b>Репозиторий:</b> <a href='https://github.com/Kerlad/Excel_to_XML.git'>https://github.com/Kerlad/Excel_to_XML.git</a><br>"
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
    # Настройка логирования
    base_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(base_dir, "log")
    setup_logging(log_dir)
    logging.getLogger(__name__).info("=== Приложение запущено ===")

    # Загрузка темы
    theme = load_theme(base_dir)

    app = QApplication(sys.argv)

    # Палитра под выбранную тему (не зависит от системной темы)
    if theme == "dark":
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 42))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(232, 232, 240))
        palette.setColor(QPalette.ColorRole.Base, QColor(40, 40, 55))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(35, 35, 50))
        palette.setColor(QPalette.ColorRole.Text, QColor(232, 232, 240))
        palette.setColor(QPalette.ColorRole.Button, QColor(40, 40, 55))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(232, 232, 240))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(179, 136, 255))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    else:
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(245, 245, 250))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(26, 26, 46))
        palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(240, 240, 250))
        palette.setColor(QPalette.ColorRole.Text, QColor(26, 26, 46))
        palette.setColor(QPalette.ColorRole.Button, QColor(245, 245, 250))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(26, 26, 46))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(124, 77, 255))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)

    app.setStyle("Fusion")
    app.setStyleSheet(get_global_stylesheet(theme))

    # Авто-применение темы ко всем всплывающим окнам (QMessageBox, QFileDialog и т.д.)
    from PyQt6.QtCore import QEvent, QObject

    class DialogStyler(QObject):
        """Применяет stylesheet ко всем новым QDialog."""
        def __init__(self, style: str):
            super().__init__()
            self._style = style

        def eventFilter(self, obj, event):
            from PyQt6.QtWidgets import QDialog
            if isinstance(obj, QDialog) and event.type() == QEvent.Type.Show:
                current = obj.styleSheet()
                if not current or self._style[:20] not in current:
                    obj.setStyleSheet(self._style)
            return False

    dialog_styler = DialogStyler(get_global_stylesheet(theme))
    app.installEventFilter(dialog_styler)

    window = MainWindow(app=app)
    window.show()

    # Mica backdrop (после show() для получения HWND)
    apply_mica(window)
    logging.getLogger(__name__).info(f"Окно отображено, тема: {theme}, Mica применён")
    sys.exit(app.exec())
