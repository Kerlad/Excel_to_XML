"""
Log viewer dialog — tail-based, auto-refresh, level filter, search.
"""
import os
import re
import shutil
import logging
import subprocess
from datetime import datetime
from collections import deque
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPlainTextEdit,
    QPushButton, QComboBox, QLineEdit, QLabel, QMessageBox,
    QFileDialog, QWidget, QApplication
)
from PySide6.QtCore import Qt, QTimer, QRegularExpression
from PySide6.QtGui import (
    QSyntaxHighlighter, QTextCharFormat, QFont, QColor,
    QTextCursor, QRegularExpressionValidator
)

from utils.logger import tail_log, get_log_files
from utils.app_paths import get_app_log_dir

logger = logging.getLogger(__name__)

MAX_BUFFER_LINES = 10000
AUTO_REFRESH_INTERVAL_MS = 2000
DEFAULT_TAIL_LINES = 1000
LOG_PATTERN = re.compile(
    r'^\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}\s+\|\s+\S+\s+\|\s+(\S+)\s+\|'
)

LEVEL_COLORS = {
    'DEBUG':    ('#999999', None),
    'INFO':     (None, None),
    'WARNING':  ('#CC8800', None),
    'ERROR':    ('#CC0000', None),
    'CRITICAL': ('#CC0000', '#FFDDDD'),
}


class LogHighlighter(QSyntaxHighlighter):
    """Highlights log lines based on level keyword."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rules = []

        self._level_order = ['CRITICAL', 'ERROR', 'WARNING', 'DEBUG']

        for level in self._level_order:
            fmt = QTextCharFormat()
            fg, bg = LEVEL_COLORS.get(level, (None, None))
            if fg:
                fmt.setForeground(QColor(fg))
            if bg:
                fmt.setBackground(QColor(bg))
            if level == 'CRITICAL':
                fmt.setFontWeight(QFont.Weight.Bold)
            if level == 'DEBUG':
                fmt.setFontItalic(True)

            pattern = QRegularExpression(
                rf'^\d{{4}}-\d{{2}}-\d{{2}}\s\d{{2}}:\d{{2}}:\d{{2}}\s+\|\s+\S+\s+\|\s+{level}\s+\|'
            )
            self._rules.append((pattern, fmt))

    def highlightBlock(self, text: str):
        for pattern, fmt in self._rules:
            match = pattern.match(text)
            if match.hasMatch():
                self.setFormat(0, len(text), fmt)
                return


class LogViewerDialog(QDialog):
    """Окно просмотра логов с автообновлением, фильтром по уровню и поиском."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Просмотр логов")
        self.setMinimumSize(900, 600)
        self.resize(1100, 700)

        self._log_dir = get_app_log_dir()
        self._buffer: deque[str] = deque(maxlen=MAX_BUFFER_LINES)
        self._last_file_pos: dict[str, int] = {}
        self._auto_scroll = True

        self._build_ui()
        self._load_initial()
        self._start_auto_refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # === Toolbar: filter + search ===
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self._level_combo = QComboBox()
        self._level_combo.addItems(["Все уровни", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self._level_combo.setToolTip("Фильтр по уровню логирования")
        self._level_combo.currentIndexChanged.connect(self._apply_filters)
        toolbar.addWidget(QLabel("Уровень:"))
        toolbar.addWidget(self._level_combo)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Поиск по тексту...")
        self._search_input.setToolTip("Поиск по тексту (регистронезависимый)")
        self._search_input.setClearButtonEnabled(True)
        self._search_input.textChanged.connect(self._apply_filters)
        toolbar.addWidget(self._search_input)

        self._refresh_btn = QPushButton("Обновить")
        self._refresh_btn.setToolTip("Принудительное обновление лога")
        self._refresh_btn.clicked.connect(self._refresh)
        toolbar.addWidget(self._refresh_btn)

        auto_label = QLabel("Авто:")
        auto_label.setToolTip("Автообновление каждые 2 сек")
        toolbar.addWidget(auto_label)

        self._auto_toggle = QPushButton("✓")
        self._auto_toggle.setToolTip("Включить/выключить автообновление")
        self._auto_toggle.setFixedWidth(30)
        self._auto_toggle.clicked.connect(self._toggle_auto_refresh)
        toolbar.addWidget(self._auto_toggle)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # === Log text area ===
        self._text_edit = QPlainTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setFont(QFont("Consolas", 10))
        self._text_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._text_edit.setToolTip("Лог-файл приложения")
        self._text_edit.verticalScrollBar().valueChanged.connect(self._on_scroll)

        self._highlighter = LogHighlighter(self._text_edit.document())
        layout.addWidget(self._text_edit)

        # === Status line ===
        status_line = QHBoxLayout()
        self._status_label = QLabel()
        status_line.addWidget(self._status_label)
        status_line.addStretch()
        layout.addLayout(status_line)

        # === Bottom buttons ===
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(8)

        self._clear_btn = QPushButton("Очистить логи")
        self._clear_btn.setToolTip("Очистить все файлы логов (с подтверждением)")
        self._clear_btn.clicked.connect(self._clear_logs)
        btn_bar.addWidget(self._clear_btn)

        self._open_folder_btn = QPushButton("Открыть папку")
        self._open_folder_btn.setToolTip("Открыть папку с логами в проводнике")
        self._open_folder_btn.clicked.connect(self._open_log_folder)
        btn_bar.addWidget(self._open_folder_btn)

        self._save_archive_btn = QPushButton("Сохранить архив")
        self._save_archive_btn.setToolTip("Упаковать логи в ZIP-архив")
        self._save_archive_btn.clicked.connect(self._save_archive)
        btn_bar.addWidget(self._save_archive_btn)

        self._copy_btn = QPushButton("Копировать всё")
        self._copy_btn.setToolTip("Копировать все отображаемые строки в буфер")
        self._copy_btn.clicked.connect(self._copy_all)
        btn_bar.addWidget(self._copy_btn)

        btn_bar.addStretch()

        self._close_btn = QPushButton("Закрыть")
        self._close_btn.clicked.connect(self.close)
        btn_bar.addWidget(self._close_btn)

        layout.addLayout(btn_bar)

    def _load_initial(self):
        """Initial load from app.log and error.log."""
        self._buffer.clear()
        self._last_file_pos.clear()

        files = get_log_files(self._log_dir)
        main_log = files.get('app.log')
        error_log = files.get('error.log')

        lines_app: list[str] = []
        if main_log:
            self._last_file_pos['app.log'] = os.path.getsize(main_log)
            lines_app = tail_log(main_log, DEFAULT_TAIL_LINES)

        lines_err: list[str] = []
        if error_log:
            self._last_file_pos['error.log'] = os.path.getsize(error_log)
            if lines_app:
                lines_err = tail_log(error_log, DEFAULT_TAIL_LINES)
            else:
                lines_err = tail_log(error_log, DEFAULT_TAIL_LINES)

        combined = lines_app + lines_err
        for line in combined:
            self._buffer.append(line)

        if not combined:
            self._buffer.append("[Лог пуст]")

        self._apply_filters()

    def _refresh(self):
        """Read new lines from all log files and append to buffer."""
        files = get_log_files(self._log_dir)
        new_lines: list[str] = []

        for key in ('app.log', 'error.log'):
            fp = files.get(key)
            if not fp:
                continue
            try:
                curr_size = os.path.getsize(fp)
                prev_pos = self._last_file_pos.get(key, 0)
                if curr_size > prev_pos:
                    with open(fp, 'r', encoding='utf-8', errors='replace') as f:
                        f.seek(prev_pos, os.SEEK_SET)
                        chunk = f.read(curr_size - prev_pos)
                    for line in chunk.split('\n'):
                        stripped = line.rstrip('\r')
                        if stripped:
                            new_lines.append(stripped)
                    self._last_file_pos[key] = curr_size
            except OSError as e:
                logger.debug("Log refresh error for %s: %s", key, e)

        for line in new_lines:
            self._buffer.append(line)

        if new_lines:
            self._auto_scroll = True

        self._apply_filters()

    def _apply_filters(self):
        """Apply level + text filter from buffer and update display."""
        level_filter = self._level_combo.currentText()
        search_text = self._search_input.text().strip().lower()

        # If "Все уровни", match any level
        level_filter = None if level_filter == "Все уровни" else level_filter

        filtered: list[str] = []
        for line in self._buffer:
            if level_filter:
                m = LOG_PATTERN.match(line)
                if not m or m.group(1) != level_filter:
                    continue
            if search_text:
                if search_text not in line.lower():
                    continue
            filtered.append(line)

        if not filtered and self._buffer:
            filtered = ["[Нет строк, соответствующих фильтру]"]

        self._text_edit.setPlainText('\n'.join(filtered))

        if self._auto_scroll and filtered:
            cursor = self._text_edit.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self._text_edit.setTextCursor(cursor)

        total = len(self._buffer)
        shown = len(filtered)
        self._status_label.setText(
            f"Показано: {shown} / всего в буфере: {total}"
            + (f"  |  фильтр: {self._level_combo.currentText()}" if level_filter else "")
            + (f"  |  поиск: \"{self._search_input.text()}\"" if self._search_input.text() else "")
        )

    def _on_scroll(self, value):
        """Track user scroll to disable auto-scroll when user scrolls up."""
        sb = self._text_edit.verticalScrollBar()
        if sb.isVisible():
            self._auto_scroll = (value >= sb.maximum())

    def _toggle_auto_refresh(self):
        if hasattr(self, '_refresh_timer') and self._refresh_timer.isActive():
            self._refresh_timer.stop()
            self._auto_toggle.setText("✗")
            self._auto_toggle.setToolTip("Автообновление выключено. Нажмите для включения.")
        else:
            self._start_auto_refresh()

    def _start_auto_refresh(self):
        if not hasattr(self, '_refresh_timer'):
            self._refresh_timer = QTimer(self)
            self._refresh_timer.setInterval(AUTO_REFRESH_INTERVAL_MS)
            self._refresh_timer.timeout.connect(self._refresh)
        self._refresh_timer.start()
        self._auto_toggle.setText("✓")
        self._auto_toggle.setToolTip("Автообновление включено. Нажмите для выключения.")

    def _clear_logs(self):
        reply = QMessageBox.warning(
            self, "Очистка логов",
            "Удалить все файлы логов?\n"
            "Рекомендуется сначала сохранить архив.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        files = get_log_files(self._log_dir)
        errors = []
        for name, fp in list(files.items()):
            if name == 'audit.log':
                continue
            try:
                os.remove(fp)
            except OSError as e:
                errors.append(f"{name}: {e}")

        self._buffer.clear()
        self._last_file_pos.clear()
        if errors:
            self._buffer.append(f"[Ошибки при очистке: {'; '.join(errors)}]")
        else:
            self._buffer.append("[Логи очищены]")

        self._apply_filters()

    def _open_log_folder(self):
        if os.path.isdir(self._log_dir):
            subprocess.Popen(['explorer', self._log_dir])

    def _save_archive(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить архив логов",
            f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            "ZIP архив (*.zip)"
        )
        if not file_path:
            return

        import zipfile
        try:
            with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                files = get_log_files(self._log_dir)
                for name, fp in sorted(files.items()):
                    if os.path.isfile(fp):
                        zf.write(fp, name)
            QMessageBox.information(self, "Архив сохранён", f"Логи упакованы:\n{file_path}")
        except (OSError, zipfile.BadZipFile) as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить архив:\n{e}")

    def _copy_all(self):
        text = self._text_edit.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self._copy_btn.setText("Скопировано ✓")
            QTimer.singleShot(2000, lambda: self._copy_btn.setText("Копировать всё"))

    def closeEvent(self, event):
        if hasattr(self, '_refresh_timer') and self._refresh_timer.isActive():
            self._refresh_timer.stop()
        super().closeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)
