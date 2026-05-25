_FORMULA_PREFIXES = ('=', '+', '-', '@', '\t', '\r', '\n', '\x00')


def sanitize_cell_value(value: str) -> str:
    if not isinstance(value, str):
        return value
    value = value.strip()
    if value and value[0] in _FORMULA_PREFIXES:
        return "'" + value
    return value
