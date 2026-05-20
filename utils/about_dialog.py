import os
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QFont, QDesktopServices
from PySide6.QtCore import QUrl
from utils.dialog_base import BaseDialog
from utils.app_paths import get_resource_dir


VERSION = "1.2.3"


class ClickableLabel(QLabel):
    def __init__(self, text, url, parent=None):
        super().__init__(text, parent)
        self._url = url
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        QDesktopServices.openUrl(QUrl(self._url))
        super().mousePressEvent(event)


class AboutDialog(BaseDialog):
    def __init__(self, parent=None):
        super().__init__(parent, title="О программе", min_width=520, min_height=360)

        bl = self.body_layout()

        header_row = QHBoxLayout()
        header_row.setSpacing(16)

        icon_path = os.path.join(get_resource_dir(), "resources", "ico.ico")
        icon_label = QLabel()
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                icon_label.setPixmap(pixmap.scaled(56, 56, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        icon_label.setFixedSize(60, 60)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_row.addWidget(icon_label)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_label = QLabel("Excel-XML для передачи данных в Минтруд")
        title_label.setObjectName("aboutTitleLabel")
        title_label.setWordWrap(True)
        title_col.addWidget(title_label)

        version_label = QLabel(f"Версия {VERSION}")
        version_label.setObjectName("aboutVersionLabel")
        title_col.addWidget(version_label)

        header_row.addLayout(title_col, 1)
        bl.addLayout(header_row)

        desc = QLabel(
            "Автоматизированная система учёта обучения работников требованиям охраны труда "
            "(постановление 2464), ведения реестра с контролем статуса (обучен / не обучен / "
            "просрочено), синхронизации с реестром Минтруда России, "
            "генерации XML-файлов для передачи данных, формирования планов обучения "
            "и протоколов проверки знаний."
        )
        desc.setObjectName("aboutDescLabel")
        desc.setWordWrap(True)
        bl.addWidget(desc)

        info_widget = QWidget()
        info_widget.setObjectName("aboutInfoWidget")
        info_layout = QVBoxLayout(info_widget)
        info_layout.setSpacing(4)
        info_layout.setContentsMargins(12, 10, 12, 10)

        dev_label = QLabel("<b>Разработчик:</b> Кривоносов Д.А.")
        dev_label.setObjectName("aboutInfoLabel")
        info_layout.addWidget(dev_label)

        studio_label = QLabel("<b>При участии:</b> QWEN Studio, OpenCode (free AI)")
        studio_label.setObjectName("aboutInfoLabel")
        info_layout.addWidget(studio_label)

        repo_link = ClickableLabel(
            "<b>Репозиторий:</b> https://github.com/Kerlad/Excel_to_XML.git",
            "https://github.com/Kerlad/Excel_to_XML.git"
        )
        repo_link.setObjectName("aboutInfoLink")
        info_layout.addWidget(repo_link)

        email_link = ClickableLabel(
            "<b>Электронная почта:</b> denis-krv@yandex.ru",
            "mailto:denis-krv@yandex.ru"
        )
        email_link.setObjectName("aboutInfoLink")
        info_layout.addWidget(email_link)

        bl.addWidget(info_widget)
        bl.addStretch()

        close_btn = QPushButton("Закрыть")
        close_btn.setObjectName("dialogPrimaryBtn")
        close_btn.setMinimumHeight(40)
        self._button_layout.addStretch()
        self._button_layout.addWidget(close_btn)
        close_btn.clicked.connect(self.close)
