_FORMULA_PREFIXES = ('=', '+', '-', '@', '\t', '\r', '\n', '\x00')


def sanitize_cell_value(value: str) -> str:
    if not isinstance(value, str):
        return value
    value = value.strip()
    if value and value[0] in _FORMULA_PREFIXES:
        return "'" + value
    return value


_INVALID_FILENAME_CHARS = '<>:"/\\|?*'


def safe_filename_part(value: str, fallback: str = "") -> str:
    r"""Очищает строку для безопасного использования в имени файла.

    Заменяет недопустимые символы (\ / : * ? " < > |) на «-», убирает
    управляющие символы и лишние пробелы/точки по краям.
    Подходит для номеров протоколов вида "5-ОТ/2024".
    """
    if value is None:
        value = ""
    text = str(value).strip()
    cleaned = []
    for ch in text:
        if ch in _INVALID_FILENAME_CHARS:
            cleaned.append('-')
        elif ord(ch) < 32:
            cleaned.append(' ')
        else:
            cleaned.append(ch)
    result = ''.join(cleaned)
    # схлопываем повторы разделителей и пробелы
    while '--' in result:
        result = result.replace('--', '-')
    while '  ' in result:
        result = result.replace('  ', ' ')
    result = result.strip(' .-')
    return result or fallback
