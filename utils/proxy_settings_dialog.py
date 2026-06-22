import os
import logging

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget,
    QScrollArea, QFrame, QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPalette

from utils.app_paths import get_resource_dir

logger = logging.getLogger(__name__)


class ProxySettingsDialog(QDialog):
    """Отдельное окно настроек прокси.

    Окно принимает готовый виджет (группу настроек прокси), построенный в
    вкладке «Передача данных», и отображает его отдельно от вкладки.
    Вся логика (сохранение, тест подключения) остаётся на вкладке, так как
    сами виджеты принадлежат ей.

    Содержимое размещается в прокручиваемой области, чтобы переключение
    режимов прокси (ручной режим добавляет поля) не растягивало окно за
    пределы экрана.
    """

    def __init__(self, content_widget: QWidget, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки прокси")
        self.setMinimumWidth(600)
        self.setSizeGripEnabled(True)

        icon_path = os.path.join(get_resource_dir(), "resources", "ico.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self._intro = QLabel(
            "Настройте способ подключения к серверу Минтруда. "
            "Для большинства пользователей подходит режим «Без прокси». "
            "Изменения применяются после нажатия «Сохранить настройки прокси»."
        )
        self._intro.setWordWrap(True)
        self._intro.setObjectName("dialogIntro")
        layout.addWidget(self._intro)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        if content_widget is not None:
            scroll.setWidget(content_widget)
        layout.addWidget(scroll, 1)

        footer = QHBoxLayout()
        footer.addStretch()
        close_btn = QPushButton("Закрыть")
        close_btn.setObjectName("dialogPrimaryBtn")
        close_btn.setMinimumHeight(34)
        close_btn.setMinimumWidth(120)
        close_btn.setToolTip("Закрыть окно настроек прокси")
        close_btn.clicked.connect(self.accept)
        footer.addWidget(close_btn)
        layout.addLayout(footer)

        self._constrain_to_screen()
        self.resize(680, 620)
        self._apply_intro_color()

    def _constrain_to_screen(self):
        """Ограничивает максимальную высоту окна высотой доступной области экрана."""
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        avail = screen.availableGeometry()
        self.setMaximumHeight(max(420, avail.height() - 40))
        self.setMaximumWidth(max(620, avail.width() - 40))

    def _apply_intro_color(self):
        """Подбирает цвет вводного текста под текущую тему (светлую/тёмную)."""
        is_dark = self.palette().color(QPalette.ColorRole.Window).lightness() < 128
        color = "#bcc0d8" if is_dark else "#6b7280"
        self._intro.setStyleSheet("color: %s; font-size: 12px;" % color)

    def showEvent(self, event):
        super().showEvent(event)
        # тема и/или экран могли измениться между открытиями окна
        self._constrain_to_screen()
        self._apply_intro_color()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.accept()
        else:
            super().keyPressEvent(event)
