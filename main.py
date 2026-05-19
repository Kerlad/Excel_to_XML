import sys
import os
import logging
import traceback
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget, QMenuBar, QMenu, QMessageBox, QTextEdit, QVBoxLayout, QDialog, QLabel, QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QFont, QPalette, QColor
from tabs.data_entry_tab import DataEntryTab
from tabs.data_view_tab import DataViewTab
from tabs.data_transfer_tab import DataTransferTab
from tabs.exam_journal_tab import ExamJournalTab
from tabs.protocol_tab import ProtocolTab
from tabs.single_worker_protocol_tab import SingleWorkerProtocolTab
from tabs.employee_summary_tab import EmployeeSummaryTab
from journal.journal_manager import JournalManager
from protocol.commission_manager import CommissionManager
from protocol.programs_manager import ProgramsManager
from utils.logger import setup_logging
from utils.audit import setup_audit_log
from utils.tahoe_style import get_global_stylesheet, apply_mica, load_theme, save_theme
from utils.app_paths import get_app_data_dir, get_app_log_dir, get_resource_dir
from db import DatabaseManager, create_schema


def _create_palette(theme: str) -> QPalette:
    """Создание палитры для темы (light/dark)."""
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
    return palette


class MainWindow(QMainWindow):
    def __init__(self, app=None):
        super().__init__()
        self.app = app
        self.current_theme = load_theme(get_app_data_dir())
        self.setWindowTitle("Excel-XML для передачи данных в Минтруд")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)

        # Иконка приложения
        icon_path = os.path.join(get_resource_dir(), "resources", "ico.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Главное меню
        self._create_menu_bar()

        # Создание вкладок
        self.tabs = QTabWidget()
        self.data_entry_tab = DataEntryTab()
        self.data_view_tab = DataViewTab()
        self.data_transfer_tab = DataTransferTab()

        # Журнал проверки знаний
        data_dir = get_app_data_dir()
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
        self.tabs.addTab(self.exam_journal_tab, "Журнал проверки знаний")
        self.tabs.addTab(self.protocol_tab, "Протокол")

        # Вкладка "Протокол одиночного работника"
        self.single_worker_tab = SingleWorkerProtocolTab(self.programs_manager, data_dir)
        self.tabs.addTab(self.single_worker_tab, "Протокол одиночного")

        # Вкладка "Сводка по сотрудникам"
        self.employee_summary_tab = EmployeeSummaryTab()
        self.tabs.addTab(self.employee_summary_tab, "Сводка по сотрудникам")

        # Подключение сигнала передачи данных
        self.data_entry_tab.data_loaded.connect(self.data_view_tab.add_data)
        # Подключение callback для проверки дублей
        self.data_entry_tab.get_existing_keys_callback = self.data_view_tab.get_existing_keys

        # Подключение журнала к вкладке передачи данных
        self.data_transfer_tab.set_journal_callback(self.exam_journal_tab.add_records_to_journal, self.exam_journal_tab.update_base_no)

        self.setCentralWidget(self.tabs)

    def _apply_theme(self, theme: str):
        """Применение темы (light/dark) ко всему приложению."""
        self.current_theme = theme
        save_theme(get_app_data_dir(), theme)

        if self.app:
            self.app.setPalette(_create_palette(theme))
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
        self._theme_action = settings_menu.addAction("Светлая тема" if self.current_theme == "dark" else "Тёмная тема")
        self._theme_action.triggered.connect(self._toggle_theme)

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
        # Обновляем текст пункта меню ДО смены темы (меню может быть удалено при refresh)
        try:
            theme_action = self._theme_action
            theme_action.setText("Светлая тема" if new_theme == "dark" else "Тёмная тема")
        except (RuntimeError, AttributeError):
            pass
        self._apply_theme(new_theme)

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

        <h3 style="color: #4169E1;">Протокол одиночного работника</h3>
        <p>На вкладке «Протокол одиночного» можно быстро сформировать протокол
        проверки знаний для одного работника без использования данных журнала.
        Заполните ФИО, должность, программу, дату, результат. Данные комиссии
        подгружаются из сохранённых на вкладке «Протокол».</p>

        <h3 style="color: #4169E1;">Хранение данных</h3>
        <p>Все данные приложения хранятся в папке <code>data/</code> рядом с программой:
        SQLite-база <code>app_data.db</code> (ФИО, СНИЛС, программы, журнал),
        зашифрованные JSON для API-ключа, настроек УЦ, данных комиссии.
        Файл базы данных шифруется на диске (AES/Fernet) и расшифровывается
        при запуске. Логи — в папке <code>log/</code>.</p>

        <h3 style="color: #4169E1;">Сводка по сотрудникам</h3>
        <p>На вкладке «Сводка по сотрудникам» ведётся учёт и анализ статуса обучения
        всех сотрудников по программам охраны труда.</p>
        <p><b>Источники данных:</b> ручной ввод, импорт из XLSX, результаты запросов
        из реестра Минтруда по СНИЛС.</p>
        <p><b>Ручной ввод:</b> заполните ФИО, СНИЛС, должность и номера программ
        (через запятую). Кнопка «Справка» покажет перечень программ — двойной клик
        добавляет номер. Нажмите «Добавить запись». Кнопка «Отмена» очищает форму.</p>
        <p><b>Таблица:</b> отображает выбранные программы (по умолчанию №1, 2, 3, 4, 18, 23).
        Для каждой программы — четыре подколонки: Потребность, Дата обучения, Протокол,
        Рег. номер. Ячейки подсвечиваются цветом: зелёный — обучен, красный — не обучен,
        жёлтый — просрочено. Двойной клик по колонке «Потребность» переключает
        значение Да/Нет.</p>
        <p><b>Выбор программ-колонок:</b> нажмите кнопку «Выбрать программы»
        (фиолетовая) на панели инструментов. Отметьте нужные программы (макс. 6)
        и нажмите «Применить». Выбор сохраняется между сессиями.</p>
        <p><b>Фильтры:</b> фильтрация по программе (выпадающий список),
        статусу (все/обучен/не обучен/просрочено), должности (текстовый поиск),
        галочка «Только проблемные» показывает не обученных и просроченных.</p>
        <p><b>Статистика:</b> в верхней панели отображаются карточки: всего сотрудников,
        всего записей, обучено, не обучено, просрочено, дата последнего обновления
        из реестра.</p>
        <p><b>Запрос из реестра Минтруда:</b> кнопка «Запросить из реестра» отправляет
        запрос по СНИЛС всех сотрудников (с паузой 0.5 сек между запросами).
        Полученные данные (даты, протоколы, рег. номера) обновляются в таблице.
        Контекстное меню → «Запросить из реестра» — для одного сотрудника.</p>
        <p><b>Редактирование:</b> контекстное меню → «Редактировать» — диалог
        изменения ФИО, СНИЛС, должности, списка программ. Двойной клик по колонке
        «Потребность» переключает Да/Нет.</p>
        <p><b>Импорт/экспорт XLSX:</b> кнопка «Импорт .xlsx» загружает данные
        из Excel-файла (обязателен столбец СНИЛС). «Экспорт .xlsx» выгружает
        текущее отображение с учётом фильтров. «Экспорт .xlsx (все)» — все данные
        без фильтров. Пустая таблица → шаблон для заполнения.</p>
        <p><b>Удаление:</b> контекстное меню → «Удалить» — удаляет выбранного
        сотрудника. Кнопка «Удалить данные» (красная) — удаляет ВСЕ записи
        из сводки с подтверждением.</p>
        <p><b>Планы обучения:</b> кнопки «Сформировать план на текущий год»
        и «Сформировать план на следующий год» открывают диалог с настройками.
        Выберите, кого включить (не обученных, просроченных, истекающих,
        не сдавших), и нажмите «Сформировать». Откроется окно плана с карточками
        статистики, таблицей и кнопками «Экспорт XLSX», «Печать».</p>
        """)

        layout.addWidget(help_text)

        from PySide6.QtWidgets import QPushButton
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

        from PySide6.QtWidgets import QLabel, QPushButton
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


def global_exception_handler(exc_type, exc_value, exc_tb):
    logger = logging.getLogger(__name__)
    logger.critical("Unhandled exception",
                    exc_info=(exc_type, exc_value, exc_tb))
    try:
        from PySide6.QtWidgets import QMessageBox
        msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        error_box = QMessageBox()
        error_box.setIcon(QMessageBox.Icon.Critical)
        error_box.setWindowTitle("Критическая ошибка")
        error_box.setText("Произошла неожиданная ошибка. Приложение будет закрыто.")
        error_box.setDetailedText(msg)
        error_box.exec()
    except Exception:
        pass
    sys.__excepthook__(exc_type, exc_value, exc_tb)


sys.excepthook = global_exception_handler


if __name__ == "__main__":
    # Настройка логирования
    log_dir = get_app_log_dir()
    setup_logging(log_dir)
    setup_audit_log(log_dir)
    logging.getLogger(__name__).info("=== Приложение запущено ===")

    # Инициализация БД
    data_dir = get_app_data_dir()
    db_path = os.path.join(data_dir, "app_data.db")
    db = DatabaseManager.get_instance(db_path)
    db.initialize()
    create_schema()
    logging.getLogger(__name__).info(f"БД: {db_path}")
    db.create_backup()

    import atexit
    atexit.register(db.close_all)

    # Загрузка темы
    theme = load_theme(data_dir)

    app = QApplication(sys.argv)

    app.setPalette(_create_palette(theme))

    app.setStyle("Fusion")
    app.setStyleSheet(get_global_stylesheet(theme))

    # Авто-применение темы ко всем всплывающим окнам (QMessageBox, QFileDialog и т.д.)
    from PySide6.QtCore import QEvent, QObject

    class DialogStyler(QObject):
        """Применяет stylesheet ко всем новым QDialog."""
        def __init__(self, style: str):
            super().__init__()
            self._style = style

        def eventFilter(self, obj, event):
            from PySide6.QtWidgets import QDialog
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
