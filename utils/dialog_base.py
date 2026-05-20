from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QWidget
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QIcon


class BaseDialog(QDialog):
    def __init__(self, parent=None, title="", min_width=480, min_height=320):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(min_width, min_height)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        self._body_layout = QVBoxLayout()
        self._body_layout.setSpacing(12)
        main_layout.addLayout(self._body_layout)

        self._button_layout = QHBoxLayout()
        self._button_layout.setSpacing(10)
        main_layout.addLayout(self._button_layout)

    def body_layout(self):
        return self._body_layout

    def add_buttons(self, buttons):
        self._button_layout.addStretch()
        for btn in buttons:
            self._button_layout.addWidget(btn)

    def add_close_button(self, text="Закрыть", primary=True):
        btn = QPushButton(text)
        btn.setObjectName("dialogPrimaryBtn" if primary else "dialogDangerBtn")
        btn.clicked.connect(self.close)
        self._button_layout.addStretch()
        self._button_layout.addWidget(btn)
        return btn

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)
