from typing import List, Optional, Callable
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QWidget
from PySide6.QtCore import Qt


class BaseDialog(QDialog):
    """Базовый класс для всех диалогов приложения."""

    def __init__(self, parent: Optional[QWidget] = None, title: str = "", min_width: int = 480, min_height: int = 320):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(min_width, min_height)
        self._fields: List[QLineEdit] = []

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        self._body_layout = QVBoxLayout()
        self._body_layout.setSpacing(12)
        main_layout.addLayout(self._body_layout)

        self._button_layout = QHBoxLayout()
        self._button_layout.setSpacing(10)
        main_layout.addLayout(self._button_layout)

    def body_layout(self) -> QVBoxLayout:
        return self._body_layout

    def register_field(self, field: QLineEdit) -> None:
        self._fields.append(field)

    def validate_fields(self) -> bool:
        for field in self._fields:
            validator_fn = getattr(field, '_validator', None)
            if validator_fn:
                error = validator_fn(field.text())
                if error:
                    field.setStyleSheet("border: 2px solid #E74C3C; background-color: #FFF0F0;")
                    field.setToolTip(error)
                    field.setFocus()
                    return False
                field.setStyleSheet("")
                field.setToolTip("")
        return True

    def add_buttons(self, buttons: List[QPushButton]) -> None:
        self._button_layout.addStretch()
        for btn in buttons:
            self._button_layout.addWidget(btn)

    def add_close_button(self, text: str = "Закрыть", primary: bool = True) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("dialogPrimaryBtn" if primary else "dialogDangerBtn")
        btn.clicked.connect(self.close)
        self._button_layout.addStretch()
        self._button_layout.addWidget(btn)
        return btn

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    @staticmethod
    def show_validation_error(parent: QWidget, field: QLineEdit, message: str) -> None:
        field.setStyleSheet("border: 2px solid #E74C3C; background-color: #FFF0F0;")
        field.setToolTip(message)
        field.setFocus()
