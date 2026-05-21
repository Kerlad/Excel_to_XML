"""
Main application entry point.
Security audit and safe initialization for ISPDn.
"""
import sys
import os
import logging
from datetime import datetime
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget, QMenu, QMessageBox, QVBoxLayout, QDialog, QLabel, QWidget, QStatusBar, QProgressBar
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon
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
from utils.logger import setup_logging, filter_sensitive_text
from utils.audit import setup_audit_log, log_audit
from utils.tahoe_style import get_global_stylesheet, create_palette, apply_mica, load_theme, save_theme
from utils.app_paths import get_app_data_dir, get_app_log_dir, get_resource_dir
from utils.about_dialog import AboutDialog, VERSION
from utils.help_dialog import HelpDialog
from utils.log_viewer_dialog import LogViewerDialog
from utils.crypto import check_master_key_security, check_environment
from utils.auto_lock import AutoLockManager
from db import DatabaseManager, create_schema
from db.employees_repo import EmployeesRepo
from api.mintrud_api import load_api_key

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, app=None):
        super().__init__()
        self.app = app
        self.current_theme = load_theme(get_app_data_dir())
        self.setWindowTitle("Excel-XML для передачи данных в Минтруд")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)

        icon_path = os.path.join(get_resource_dir(), "resources", "ico.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self._create_menu_bar()
        self._create_status_bar()

        data_dir = get_app_data_dir()

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.data_entry_tab = DataEntryTab()
        self.data_view_tab = DataViewTab()
        self.data_transfer_tab = DataTransferTab()

        self.journal_manager = JournalManager(data_dir)
        self.exam_journal_tab = ExamJournalTab(self.journal_manager, data_dir)

        self.commission_manager = CommissionManager(data_dir)
        self.programs_manager = ProgramsManager(data_dir)
        self.protocol_tab = ProtocolTab(self.commission_manager, self.programs_manager, data_dir, self.journal_manager)
        self.protocol_tab.set_data_source(self.data_view_tab)

        self.single_worker_tab = SingleWorkerProtocolTab(self.programs_manager, data_dir)

        self.employee_summary_tab = EmployeeSummaryTab()

        self.auto_lock = AutoLockManager(self)

        self._setup_tabs()

        self.data_entry_tab.data_loaded.connect(self.data_view_tab.add_data)
        self.data_entry_tab.get_existing_keys_callback = self.data_view_tab.get_existing_keys

        self.data_transfer_tab.set_journal_callback(self.exam_journal_tab.add_records_to_journal, self.exam_journal_tab.update_base_no)

        self.tabs.currentChanged.connect(self._on_tab_changed)

        self.setCentralWidget(self.tabs)

        self._status_timer = QTimer(self)
        self._status_timer.setInterval(10000)
        self._status_timer.timeout.connect(self._update_status_bar)
        self._status_timer.start()

        self._update_status_bar()

        if self.app:
            self.app.installEventFilter(self.auto_lock)

    def _setup_tabs(self):
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
        try:
            emp_count = EmployeesRepo.count()
            self._sb_employees.setText(f"Сотрудников: {emp_count}")
        except Exception as e:
            logger.debug("Status bar: employees count unavailable: %s", e)
            self._sb_employees.setText("Сотрудников: --")
        try:
            from db.exam_journal_repo import ExamJournalRepo
            j_count = ExamJournalRepo.count()
            self._sb_journal.setText(f"Журнал: {j_count}")
        except Exception as e:
            logger.debug("Status bar: journal count unavailable: %s", e)
            self._sb_journal.setText("Журнал: --")
        try:
            key = load_api_key(get_app_data_dir())
            if key:
                self._sb_api.setText("API ключ: установлен")
                self._sb_api_indicator.setStyleSheet("background-color: #27AE60; border-radius: 5px;")
            else:
                self._sb_api.setText("API ключ: не задан")
                self._sb_api_indicator.setStyleSheet("background-color: #E74C3C; border-radius: 5px;")
        except Exception as e:
            logger.debug("Status bar: API key unavailable: %s", e)
            self._sb_api.setText("API ключ: ?")
            self._sb_api_indicator.setStyleSheet("background-color: #888; border-radius: 5px;")
        try:
            db = DatabaseManager.get_instance()
            rows = db.fetchone("SELECT MAX(last_sync) as ls FROM employees WHERE last_sync IS NOT NULL")
            last_sync = rows['ls'] if rows and rows['ls'] else "нет"
            self._sb_sync.setText(f"Синхр.: {last_sync}")
        except Exception as e:
            logger.debug("Status bar: sync date unavailable: %s", e)
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
        self._update_status_bar()
        if index < 0 or index >= self.tabs.count():
            return
        w = self.tabs.widget(index)
        if hasattr(w, 'refresh_table'):
            try: w.refresh_table()
            except Exception as e:
                logger.debug("Tab refresh_table failed: %s", e)
        elif hasattr(w, 'refresh_data'):
            try: w.refresh_data()
            except Exception as e:
                logger.debug("Tab refresh_data failed: %s", e)

    def _create_template(self):
        self.tabs.setCurrentIndex(0)
        self.data_entry_tab.create_template()

    def _export_all(self):
        self.tabs.setCurrentIndex(1)
        self.data_view_tab._export_xlsx()

    def _open_proxy_settings(self):
        for i in range(self.tabs.count()):
            if "Передача данных" in self.tabs.tabText(i):
                self.tabs.setCurrentIndex(i)
                break
        self.data_transfer_tab.scroll_to_proxy()

    def _open_security(self):
        from utils.security_dialog import SecurityDialog
        dialog = SecurityDialog(self)
        dialog.exec()
        self.auto_lock.refresh()

    def _apply_theme(self, theme: str):
        self.current_theme = theme
        save_theme(get_app_data_dir(), theme)
        if self.app:
            self.app.setPalette(create_palette(theme))
            self.app.setStyleSheet(get_global_stylesheet(theme))
            self._refresh_styles()

    def _refresh_styles(self):
        for w in self.findChildren(QWidget):
            w.style().unpolish(w)
            w.style().polish(w)
        self.style().unpolish(self)
        self.style().polish(self)

    def _create_menu_bar(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("Файл")
        template_action = file_menu.addAction("Создать шаблон XLSX")
        template_action.triggered.connect(self._create_template)
        export_action = file_menu.addAction("Экспорт всех данных XLSX")
        export_action.triggered.connect(self._export_all)
        file_menu.addSeparator()
        exit_action = file_menu.addAction("Выход")
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)

        settings_menu = menubar.addMenu("Настройки")
        self._theme_action = settings_menu.addAction("Светлая тема" if self.current_theme == "dark" else "Тёмная тема")
        self._theme_action.triggered.connect(self._toggle_theme)
        settings_menu.addSeparator()
        lock_action = settings_menu.addAction("Заблокировать сессию")
        lock_action.triggered.connect(self._manual_lock)
        timeout_action = settings_menu.addAction("Таймаут блокировки...")
        timeout_action.triggered.connect(self._configure_lock_timeout)
        settings_menu.addSeparator()
        security_action = settings_menu.addAction("Безопасность")
        security_action.triggered.connect(self._open_security)
        settings_menu.addSeparator()
        proxy_action = settings_menu.addAction("Настройки прокси")
        proxy_action.triggered.connect(self._open_proxy_settings)

        help_menu = menubar.addMenu("Справка")
        help_action = help_menu.addAction("Справка по работе с программой")
        help_action.triggered.connect(self.show_help)
        help_menu.addSeparator()
        about_action = help_menu.addAction("О программе")
        about_action.triggered.connect(self.show_about)

        tools_menu = menubar.addMenu("Инструменты")
        logs_action = tools_menu.addAction("Просмотр логов")
        logs_action.triggered.connect(self.show_log_viewer)

    def _toggle_theme(self):
        new_theme = "light" if self.current_theme == "dark" else "dark"
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
        self.auto_lock.refresh()

    def show_log_viewer(self):
        dialog = LogViewerDialog(self)
        dialog.exec()

    def _manual_lock(self):
        self.auto_lock.force_lock()

    def _configure_lock_timeout(self):
        from PySide6.QtWidgets import QInputDialog
        current = self.auto_lock.timeout_minutes
        value, ok = QInputDialog.getInt(
            self, "Таймаут блокировки",
            "Минуты бездействия до блокировки сессии (1-120):",
            value=current, minValue=1, maxValue=120, step=1
        )
        if ok:
            self.auto_lock.timeout_minutes = value
            logger.info("Auto-lock timeout set to %d min", value)


def global_exception_handler(exc_type, exc_value, exc_tb):
    """Safe global exception handler - no PII in crash dialog."""
    _logger = logging.getLogger(__name__)
    _logger.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))
    log_audit("CRASH", f"Type: {exc_type.__name__}")
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
        if QApplication.instance() is not None:
            error_box = QMessageBox()
            error_box.setIcon(QMessageBox.Icon.Critical)
            error_box.setWindowTitle("Критическая ошибка")
            error_box.setText(
                "Произошла неожиданная ошибка. Приложение будет закрыто.\n\n"
                "Подробности записаны в лог-файл."
            )
            error_box.setDetailedText(
                f"Тип: {exc_type.__name__}\n"
                f"Описание: {filter_sensitive_text(str(exc_value)[:200])}\n"
                f"Подробности см. в error.log"
            )
            error_box.exec()
    except Exception as e:
        _logger.critical("Crash dialog failed: %s", e)
    sys.__excepthook__(exc_type, exc_value, exc_tb)


sys.excepthook = global_exception_handler


def _show_first_about(window, flag_path):
    try:
        from utils.about_dialog import AboutDialog
        dialog = AboutDialog(window)
        dialog.exec()
        with open(flag_path, 'w', encoding='utf-8') as f:
            f.write('shown')
    except Exception as e:
        logging.getLogger(__name__).debug("First-launch About dialog failed: %s", e)


if __name__ == "__main__":
    _profile_flag = '--profile' in sys.argv
    if _profile_flag:
        sys.argv.remove('--profile')

    log_dir = get_app_log_dir()
    setup_logging(log_dir)
    setup_audit_log(log_dir)
    logger.info("=== Application started ===")

    data_dir = get_app_data_dir()
    db_path = os.path.join(data_dir, "app_data.db")
    db = DatabaseManager.get_instance(db_path)
    db.initialize()
    create_schema()
    logger.info("Database initialized")
    db.create_backup()
    log_audit("STARTUP", "Application started")

    _first_launch_flag = os.path.join(data_dir, ".about_shown")
    _is_first_launch = not os.path.exists(_first_launch_flag)

    def security_audit():
        audit_logger = logging.getLogger(__name__)

        env_ok, env_msg = check_environment()
        if not env_ok:
            audit_logger.warning("Security audit - environment: FAIL - %s", env_msg)
        else:
            audit_logger.info("Security audit - environment: OK")

        mode, msg = check_master_key_security()
        audit_logger.info("Security audit - master.key: [%s] %s", mode, msg)
        if mode in ('raw',):
            audit_logger.warning(
                "SECURITY: DPAPI unavailable - master.key stored as plaintext! "
                "Consider setting a passphrase via 'About' dialog."
            )
            log_audit("SECURITY_WARNING", "Master key is plaintext")
        elif mode == 'raw_passphrase':
            audit_logger.info("Security audit - master.key: plaintext but passphrase protected (PBKDF2)")
        elif mode == 'none':
            audit_logger.error("SECURITY: Master key not found!")
            log_audit("SECURITY_WARNING", "Master key not found")
        elif mode in ('dpapi', 'dpapi_passphrase'):
            audit_logger.info("Security audit - master.key protection: OK (%s)", mode)

        from api.mintrud_api import load_api_key
        api_key = load_api_key(data_dir)
        if api_key:
            audit_logger.info("Security audit - API key: present (encrypted)")
        else:
            audit_logger.info("Security audit - API key: not set")

        try:
            from db.employees_repo import EmployeesRepo
            sample = EmployeesRepo.get_all(limit=1)
            if sample:
                audit_logger.info("Security audit - DB encryption: OK (field-level Fernet)")
        except Exception as e:
            audit_logger.warning("Security audit - DB encryption check: %s", e)

    security_audit()

    theme = load_theme(data_dir)

    app = QApplication(sys.argv)

    icon_path = os.path.join(get_resource_dir(), "resources", "ico.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    app.setPalette(create_palette(theme))
    app.setStyle("Fusion")
    app.setStyleSheet(get_global_stylesheet(theme))

    from utils.crypto import is_passphrase_protected
    if is_passphrase_protected():
        from utils.passphrase_dialog import PassphraseDialog
        passphrase_dialog = PassphraseDialog()
        if passphrase_dialog.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)

    window = MainWindow(app=app)
    window.show()

    apply_mica(window)
    logger.info("Window displayed, theme: %s", theme)

    if _is_first_launch:
        from PySide6.QtCore import QTimer
        QTimer.singleShot(500, lambda: _show_first_about(window, _first_launch_flag))

    if _profile_flag:
        import cProfile
        profiler = cProfile.Profile()
        profiler.runcall(app.exec)
        profiler.dump_stats(os.path.join(log_dir, "profile.prof"))
        logger.info("Profile saved")
    else:
        sys.exit(app.exec())
