from typing import Optional, Callable
from PySide6.QtWidgets import QLineEdit, QWidget
from PySide6.QtCore import Qt


_ERROR_STYLE = "border: 2px solid #E74C3C; background-color: #FFF0F0;"
_NORMAL_STYLE = ""


class ValidatedLineEdit(QLineEdit):
    """QLineEdit с визуальной валидацией (красная обводка + tooltip)."""

    def __init__(self, parent: Optional[QWidget] = None,
                 validator: Optional[Callable[[str], Optional[str]]] = None):
        super().__init__(parent)
        self._validator = validator
        self._valid = True
        self.textChanged.connect(self._on_text_changed)

    def set_validator_fn(self, validator: Callable[[str], Optional[str]]) -> None:
        self._validator = validator

    def _on_text_changed(self, text: str) -> None:
        if self._validator:
            error = self._validator(text)
            self._valid = error is None
            self.setStyleSheet(_ERROR_STYLE if error else _NORMAL_STYLE)
            self.setToolTip(error if error else "")
        else:
            self._valid = True
            self.setStyleSheet(_NORMAL_STYLE)
            self.setToolTip("")

    def is_valid(self) -> bool:
        if not self._validator:
            return True
        return self._validator(self.text()) is None

    def set_invalid(self, error: str) -> None:
        self._valid = False
        self.setStyleSheet(_ERROR_STYLE)
        self.setToolTip(error)

    def clear_validation(self) -> None:
        self._valid = True
        self.setStyleSheet(_NORMAL_STYLE)
        self.setToolTip("")


def _snils_checksum_valid(clean_digits: str) -> bool:
    if len(clean_digits) != 11 or not clean_digits.isdigit():
        return False
    digits = [int(c) for c in clean_digits[:9]]
    check = int(clean_digits[9:])
    total = sum(d * (9 - i) for i, d in enumerate(digits))
    if total < 100:
        control = total
    elif total in (100, 101):
        control = 0
    else:
        control = total % 101
        if control in (100, 101):
            control = 0
    return control == check


def validate_snils(snils: str) -> Optional[str]:
    """Проверяет СНИЛС. Возвращает ошибку или None."""
    clean = snils.replace("-", "").replace(" ", "").replace("\xa0", "")
    if not clean:
        return None
    if not clean.isdigit() or len(clean) != 11:
        return "СНИЛС должен содержать 11 цифр"
    if not _snils_checksum_valid(clean):
        return "Неверная контрольная сумма СНИЛС"
    return None


def validate_required(text: str, field_name: str = "Поле") -> Optional[str]:
    """Проверяет, что поле не пустое."""
    if not text.strip():
        return f"{field_name} обязательно для заполнения"
    return None


def validate_program_id(pid: str) -> Optional[str]:
    """Проверяет номер программы."""
    valid = {"1", "2", "3", "4", "6", "7", "8", "9", "10", "11", "12",
             "13", "14", "15", "16", "17", "18", "19", "20", "21",
             "22", "23", "24", "25", "26", "27", "28", "29"}
    clean = pid.strip()
    if not clean:
        return None
    if clean not in valid:
        return "Некорректный номер программы (допустимо: 1-4, 6-29)"
    return None


def validate_date(date_str: str) -> Optional[str]:
    """Проверяет дату в формате DD.MM.YYYY."""
    from datetime import datetime
    clean = date_str.replace("-", "").replace(".", "").strip()
    if not clean:
        return None
    if not clean.isdigit() or len(clean) != 8:
        return "Дата должна быть в формате ДД.ММ.ГГГГ"
    try:
        dt = datetime.strptime(clean, "%d%m%Y")
        if dt.date() > datetime.now().date():
            return "Дата не может быть больше текущей"
    except ValueError:
        return "Дата некорректна"
    return None


def validate_name(name: str) -> Optional[str]:
    """Проверяет, что имя/фамилия содержит только буквы."""
    clean = name.strip().replace(" ", "").replace("-", "")
    if not clean:
        return None
    if not clean.replace(".", "").isalpha():
        return "Допускаются только буквы"
    return None
