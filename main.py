import sys
import os
import logging
import traceback
from datetime import datetime
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget, QMenuBar, QMenu, QMessageBox, QTextEdit, QVBoxLayout, QDialog, QLabel, QWidget, QStatusBar, QFileDialog, QProgressBar
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QFont, QAction
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
from utils.tahoe_style import get_global_stylesheet, create_palette, apply_mica, load_theme, save_theme
from utils.app_paths import get_app_data_dir, get_app_log_dir, get_resource_dir
from utils.about_dialog import AboutDialog, VERSION
from utils.help_dialog import HelpDialog
from utils.crypto import check_master_key_security
from db import DatabaseManager, create_schema
from db.employees_repo import EmployeesRepo
from api.mintrud_api import load_api_key


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

        self._create_menu_bar()
        self._create_status_bar()

        data_dir = get_app_data_dir()

        # Создание вкладок
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.data_entry_tab = DataEntryTab()
        self.data_view_tab = DataViewTab()
        self.data_transfer_tab = DataTransferTab()

        # Журнал проверки знаний
        self.journal_manager = JournalManager(data_dir)
        self.exam_journal_tab = ExamJournalTab(self.journal_manager, data_dir)

        # Менеджеры для протокола
        self.commission_manager = CommissionManager(data_dir)
        self.programs_manager = ProgramsManager(data_dir)
        self.protocol_tab = ProtocolTab(self.commission_manager, self.programs_manager, data_dir, self.journal_manager)
        self.protocol_tab.set_data_source(self.data_view_tab)

        # Вкладка "Протокол одиночного работника"
        self.single_worker_tab = SingleWorkerProtocolTab(self.programs_manager, data_dir)

        # Вкладка "Сводка по сотрудникам"
        self.employee_summary_tab = EmployeeSummaryTab()

        self._setup_tabs()

        # Подключение сигнала передачи данных
        self.data_entry_tab.data_loaded.connect(self.data_view_tab.add_data)
        # Подключение callback для проверки дублей
        self.data_entry_tab.get_existing_keys_callback = self.data_view_tab.get_existing_keys

        # Подключение журнала к вкладке передачи данных
        self.data_transfer_tab.set_journal_callback(self.exam_journal_tab.add_records_to_journal, self.exam_journal_tab.update_base_no)

        # Обновление статус-бара при смене вкладки
        self.tabs.currentChanged.connect(self._on_tab_changed)

        self.setCentralWidget(self.tabs)

        # Таймер обновления статус-бара (каждые 10 сек)
        self._status_timer = QTimer(self)
        self._status_timer.setInterval(10000)
        self._status_timer.timeout.connect(self._update_status_bar)
        self._status_timer.start()

        self._update_status_bar()

    def _setup_tabs(self):
        """Настройка вкладок с иконками."""
        style = self.app.style() if self.app else QApplication.style()
        sp = style.StandardPixmap
        def _nl(t):
            s = t.split()
            return t if len(s) == 1 else s[0] + "\n" + " ".join(s[1:])

        tab_data = [
            (self.data_entry_tab, _nl("Внесение данных"), sp.SP_FileDialogNewFolder),
            (self.data_view_tab, _nl("Просмотр данных"), sp.SP_FileDialogDetailedView),
            (self.data_transfer_tab, _nl("Передача данных"), sp.SP_ComputerIcon),
            (self.exam_journal_tab, _nl("Журнал проверки знаний"), sp.SP_FileDialogContentsView),
            (self.protocol_tab, "Протокол", sp.SP_FileDialogInfoView),
            (self.single_worker_tab, _nl("Протокол одиночного"), sp.SP_FileDialogListView),
            (self.employee_summary_tab, _nl("Сводка по сотрудникам"), sp.SP_CommandLink),
        ]
        for tab, title, pixmap in tab_data:
            self.tabs.addTab(tab, style.standardIcon(pixmap), title)

    def _create_status_bar(self):
        """Создание строки состояния."""
        sb = self.statusBar()
        self._sb_employees = QLabel("Сотрудников: --")
        self._sb_sync = QLabel("Синхр.: --")
        self._sb_api = QLabel("API ключ: --")
        self._sb_journal = QLabel("Журнал: --")
        self._sb_api_indicator = QLabel()
        self._sb_api_indicator.setFixedSize(10, 10)
        self._sb_api_indicator.setStyleSheet("background-color: #888; border-radius: 5px;")
        for lbl in (self._sb_employees, self._sb_sync, self._sb_api_indicator, self._sb_api, self._sb_journal):
            lbl.setContentsMargins(10, 2, 10, 2)
            sb.addPermanentWidget(lbl)

        self._sb_version = QLabel(f"v{VERSION}")
        self._sb_version.setContentsMargins(10, 2, 10, 2)
        self._sb_version.setStyleSheet("color: #888;")
        sb.addPermanentWidget(self._sb_version)

        self._sb_progress = QProgressBar()
        self._sb_progress.setRange(0, 100)
        self._sb_progress.setFixedWidth(150)
        self._sb_progress.setFixedHeight(16)
        self._sb_progress.setVisible(False)
        self._sb_progress.setTextVisible(True)
        self._sb_progress.setStyleSheet("""
            QProgressBar { border: 1px solid #ccc; border-radius: 4px;
                text-align: center; font-size: 10px; }
            QProgressBar::chunk { background-color: #4169E1; border-radius: 3px; }
        """)
        sb.addPermanentWidget(self._sb_progress)

    def _update_status_bar(self):
        """Обновление данных в строке состояния."""
        try:
            emp_count = EmployeesRepo.count()
            self._sb_employees.setText(f"Сотрудников: {emp_count}")
        except Exception:
            self._sb_employees.setText("Сотрудников: --")
        try:
            from db.exam_journal_repo import ExamJournalRepo
            j_count = ExamJournalRepo.count()
            self._sb_journal.setText(f"Журнал: {j_count}")
        except Exception:
            self._sb_journal.setText("Журнал: --")
        try:
            key = load_api_key(get_app_data_dir())
            if key:
                self._sb_api.setText("API ключ: установлен")
                self._sb_api_indicator.setStyleSheet("background-color: #27AE60; border-radius: 5px;")
            else:
                self._sb_api.setText("API ключ: не задан")
                self._sb_api_indicator.setStyleSheet("background-color: #E74C3C; border-radius: 5px;")
        except Exception:
            self._sb_api.setText("API ключ: ?")
            self._sb_api_indicator.setStyleSheet("background-color: #888; border-radius: 5px;")
        try:
            db = DatabaseManager.get_instance()
            rows = db.fetchone("SELECT MAX(last_sync) as ls FROM employees WHERE last_sync IS NOT NULL")
            last_sync = rows['ls'] if rows and rows['ls'] else "нет"
            self._sb_sync.setText(f"Синхр.: {last_sync}")
        except Exception:
            self._sb_sync.setText("Синхр.: --")

    def show_progress(self, visible: bool = True, value: int = -1, text: str = ""):
        self._sb_progress.setVisible(visible)
        if value >= 0:
            self._sb_progress.setValue(value)
        if text:
            self._sb_progress.setFormat(text)
        if not visible:
            self._sb_progress.setFormat("")

    def show_progress_indeterminate(self, visible: bool = True, text: str = ""):
        self._sb_progress.setVisible(visible)
        self._sb_progress.setRange(0, 0)
        if text:
            self._sb_progress.setFormat(text)
        if not visible:
            self._sb_progress.setRange(0, 100)
            self._sb_progress.setFormat("")

    def _on_tab_changed(self, index):
        """Обработчик смены вкладки."""
        self._update_status_bar()
        if index < 0 or index >= self.tabs.count():
            return
        w = self.tabs.widget(index)
        if hasattr(w, 'refresh_table'):
            try: w.refresh_table()
            except Exception: pass
        elif hasattr(w, 'refresh_data'):
            try: w.refresh_data()
            except Exception: pass

    def _create_template(self):
        """Создать шаблон XLSX через вкладку Внесение данных."""
        self.tabs.setCurrentIndex(0)

    def _export_all(self):
        """Экспорт всех данных через вкладку Просмотр данных."""
        self.tabs.setCurrentIndex(1)

    def _open_proxy_settings(self):
        """Переход к настройкам прокси."""
        for i in range(self.tabs.count()):
            if "Передача данных" in self.tabs.tabText(i):
                self.tabs.setCurrentIndex(i)
                break

    def _apply_theme(self, theme: str):
        """Применение темы (light/dark) ко всему приложению."""
        self.current_theme = theme
        save_theme(get_app_data_dir(), theme)

        if self.app:
            self.app.setPalette(create_palette(theme))
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

        # Меню "Файл"
        file_menu = menubar.addMenu("Файл")
        template_action = file_menu.addAction("Создать шаблон XLSX")
        template_action.triggered.connect(self._create_template)
        export_action = file_menu.addAction("Экспорт всех данных XLSX")
        export_action.triggered.connect(self._export_all)
        file_menu.addSeparator()
        exit_action = file_menu.addAction("Выход")
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)

        # Меню "Настройки"
        settings_menu = menubar.addMenu("Настройки")
        self._theme_action = settings_menu.addAction("Светлая тема" if self.current_theme == "dark" else "Тёмная тема")
        self._theme_action.triggered.connect(self._toggle_theme)
        proxy_action = settings_menu.addAction("Настройки прокси")
        proxy_action.triggered.connect(self._open_proxy_settings)
        settings_menu.addSeparator()
        about_action = settings_menu.addAction("О программе")
        about_action.triggered.connect(self.show_about)

        # Меню "Справка"
        help_menu = menubar.addMenu("Справка")
        help_action = help_menu.addAction("Справка по работе с программой")
        help_action.triggered.connect(self.show_help)

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
        dialog = HelpDialog(self)
        dialog.exec()

    def show_about(self):
        dialog = AboutDialog(self)
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
    # PERFORMANCE: поддержка --profile для cProfile
    _profile_flag = '--profile' in sys.argv
    if _profile_flag:
        sys.argv.remove('--profile')

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

    # Security audit on startup
    def security_audit():
        audit_logger = logging.getLogger(__name__)
        mode, msg = check_master_key_security()
        audit_logger.info(f"Security audit - master.key: [{mode}] {msg}")
        if mode == 'raw':
            audit_logger.warning(
                "SECURITY: DPAPI unavailable - master.key stored as plaintext! "
                "Consider creating a backup via 'About' dialog."
            )
        elif mode == 'none':
            audit_logger.error("SECURITY: Master key not found!")
        elif mode == 'dpapi':
            audit_logger.info("Security audit - master.key protection: OK (DPAPI)")

        # Check API key existence
        from api.mintrud_api import load_api_key
        api_key = load_api_key(data_dir)
        if api_key:
            audit_logger.info("Security audit - API key: present (encrypted)")
        else:
            audit_logger.info("Security audit - API key: not set")

        # Check database encryption integrity
        try:
            from db.employees_repo import EmployeesRepo
            sample = EmployeesRepo.get_all(limit=1)
            if sample:
                audit_logger.info("Security audit - DB encryption: OK (field-level Fernet)")
        except Exception as e:
            audit_logger.warning(f"Security audit - DB encryption check: {e}")

    security_audit()

    import atexit
    atexit.register(db.close_all)

    # Загрузка темы
    theme = load_theme(data_dir)

    app = QApplication(sys.argv)

    # Иконка приложения (для панели задач Windows)
    icon_path = os.path.join(get_resource_dir(), "resources", "ico.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    app.setPalette(create_palette(theme))

    app.setStyle("Fusion")
    app.setStyleSheet(get_global_stylesheet(theme))

    window = MainWindow(app=app)
    window.show()

    # Mica backdrop (после show() для получения HWND)
    apply_mica(window)
    logging.getLogger(__name__).info(f"Окно отображено, тема: {theme}, Mica применён")

    if _profile_flag:
        import cProfile
        profiler = cProfile.Profile()
        profiler.runcall(app.exec)
        profiler.dump_stats(os.path.join(log_dir, "profile.prof"))
        logging.getLogger(__name__).info(f"Profile saved to {os.path.join(log_dir, 'profile.prof')}")
    else:
        sys.exit(app.exec())
