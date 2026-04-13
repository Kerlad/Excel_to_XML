"""
Модуль загрузки XLSX/XLS файлов
"""
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

COLUMNS = [
    "Фамилия", "Имя", "Отчество", "СНИЛС", "Должность",
    "ИНН Заказчика", "Наименование ЮЛ Заказчика", "ИНН УЦ",
    "Наименование УЦ", "Результат", "№ программы", "Дата", "№ протокола"
]

FIELD_KEYS = [
    'last_name', 'first_name', 'middle_name', 'snils', 'position',
    'employer_inn', 'employer_title', 'tc_inn', 'tc_title',
    'result', 'program', 'date', 'protocol'
]

VALID_PROGRAMS = {'1', '2', '3', '4', '6', '7', '8', '9', '10', '11', '12',
                  '13', '14', '15', '16', '17', '18', '19', '20', '21',
                  '22', '23', '24', '25', '26', '27', '28', '29'}


def format_snils(raw):
    """
    Приведение СНИЛС к формату '123-456-789 00'.
    Принимает любой вид: '12345678900', '123-456-78900', '123-456-789 00' и т.д.
    Возвращает отформатированную строку или None при невалидном вводе.
    """
    clean = str(raw).strip().replace('-', '').replace(' ', '')
    if not clean.isdigit() or len(clean) != 11:
        return None
    return f"{clean[0:3]}-{clean[3:6]}-{clean[6:9]} {clean[9:11]}"


def validate_row(row_dict, row_num):
    """Валидация строки из Excel. Возвращает (True, data) или (False, error_msg)."""
    errors = []

    # Проверка обязательных полей (ИНН/названия УЦ и Заказчика — необязательные)
    required_cols = ['Фамилия', 'Имя', 'Отчество', 'СНИЛС', 'Должность', 'Результат', '№ программы', 'Дата', '№ протокола']
    for col in required_cols:
        val = row_dict.get(col)
        if val is None or str(val).strip() == '':
            errors.append(f"Строка {row_num}: поле '{col}' пустое")

    if errors:
        return False, "; ".join(errors)

    # СНИЛС
    snils = format_snils(str(row_dict['СНИЛС']))
    if snils is None:
        errors.append(f"Строка {row_num}: СНИЛС должен содержать 11 цифр")

    # Номер программы
    program_str = str(row_dict['№ программы']).strip()
    programs = [p.strip() for p in program_str.rstrip(',').split(',') if p.strip()]
    if not all(p in VALID_PROGRAMS for p in programs):
        errors.append(f"Строка {row_num}: некорректный номер программы")

    # Результат
    result = str(row_dict['Результат']).strip()
    if result not in ['Удовлетворительно', 'Неудовлетворительно']:
        errors.append(f"Строка {row_num}: результат должен быть 'Удовлетворительно' или 'Неудовлетворительно'")

    # Дата
    date_val = row_dict['Дата']
    if isinstance(date_val, datetime):
        date_str = date_val.strftime('%d.%m.%Y')
    elif isinstance(date_val, (int, float)):
        # Excel serial date
        try:
            delta = datetime(1899, 12, 30) + timedelta(days=date_val)
            date_str = delta.strftime('%d.%m.%Y')
        except Exception:
            errors.append(f"Строка {row_num}: ошибка парсинга даты")
            date_str = None
    else:
        date_str = str(date_val).strip()
        # Пробуем распарсить как дату
        if '.' in date_str or '-' in date_str:
            clean_date = date_str.replace('.', '').replace('-', '')
            if len(clean_date) == 8 and clean_date.isdigit():
                try:
                    d = datetime.strptime(clean_date, "%d%m%Y")
                    if d.date() > datetime.now().date():
                        errors.append(f"Строка {row_num}: дата больше текущей")
                    date_str = f"{clean_date[:2]}.{clean_date[2:4]}.{clean_date[4:]}"
                except ValueError:
                    errors.append(f"Строка {row_num}: дата некорректна")
                    date_str = None
            else:
                errors.append(f"Строка {row_num}: дата некорректна")
                date_str = None
        else:
            # Строка без разделителей — пробуем как 8 цифр
            clean_date = date_str.strip()
            if len(clean_date) == 8 and clean_date.isdigit():
                try:
                    d = datetime.strptime(clean_date, "%d%m%Y")
                    if d.date() > datetime.now().date():
                        errors.append(f"Строка {row_num}: дата больше текущей")
                    date_str = f"{clean_date[:2]}.{clean_date[2:4]}.{clean_date[4:]}"
                except ValueError:
                    errors.append(f"Строка {row_num}: дата некорректна")
                    date_str = None
            else:
                errors.append(f"Строка {row_num}: дата некорректна")
                date_str = None

    if errors:
        return False, "; ".join(errors)

    # Формирование данных
    # Поддержка нескольких программ — разбиваем на N записей
    records = []
    for prog in programs:
        # Безопасное получение строк (None → пустая строка)
        def gv(key):
            v = row_dict.get(key)
            return str(v).strip() if v is not None else ''

        record = {
            'last_name': gv('Фамилия'),
            'first_name': gv('Имя'),
            'middle_name': gv('Отчество'),
            'snils': snils,
            'position': gv('Должность'),
            'employer_inn': gv('ИНН Заказчика'),
            'employer_title': gv('Наименование ЮЛ Заказчика'),
            'tc_inn': gv('ИНН УЦ'),
            'tc_title': gv('Наименование УЦ'),
            'result': result,
            'program': prog,
            'date': date_str,
            'protocol': gv('№ протокола')
        }
        records.append(record)

    return True, records


def load_xlsx(file_path):
    """
    Загрузка XLSX/XLS файла.
    Возвращает (records, error_count, error_messages)
    records — список словарей, error_count — кол-во ошибок
    """
    import xlrd

    try:
        if file_path.endswith('.xlsx'):
            from openpyxl import load_workbook
            return _load_xlsx_openpyxl(file_path)
        elif file_path.endswith('.xls'):
            return _load_xls_xlrd(file_path)
        else:
            return None, 0, ["Неподдерживаемый формат. Используйте .xlsx или .xls"]
    except ImportError as e:
        return None, 0, [f"Не установлен модуль: {e}. pip install openpyxl xlrd"]
    except Exception as e:
        logger.error(f"Ошибка загрузки файла {file_path}: {e}")
        return None, 0, [f"Ошибка открытия файла: {e}"]


def _load_xlsx_openpyxl(file_path):
    """Загрузка .xlsx через openpyxl"""
    from openpyxl import load_workbook
    from datetime import datetime as dt

    wb = load_workbook(file_path, data_only=True)
    ws = wb.active

    records = []
    error_count = 0
    error_messages = []

    # Читаем заголовки
    headers = [str(ws.cell(row=1, column=c).value).strip() for c in range(1, ws.max_column + 1)]

    # Проверка обязательных полей (без ИНН/названий УЦ и Заказчика — они подставляются из настроек)
    required_fields = ['Фамилия', 'Имя', 'Отчество', 'СНИЛС', 'Должность', 'Результат', '№ программы', 'Дата', '№ протокола']
    for col in required_fields:
        if col not in headers:
            return None, 0, [f"Отсутствует столбец: {col}"]

    for row_num in range(2, ws.max_row + 1):
        row_dict = {}
        for c_idx, col_name in enumerate(headers):
            val = ws.cell(row=row_num, column=c_idx + 1).value
            row_dict[col_name] = val if val is not None else ''

        is_valid, result = validate_row(row_dict, row_num)
        if is_valid:
            records.extend(result)
        else:
            error_count += 1
            error_messages.append(result)

    return records, error_count, error_messages


def _load_xls_xlrd(file_path):
    """Загрузка .xls через xlrd"""
    import xlrd
    from xlrd import xldate_as_tuple
    from datetime import datetime as dt

    wb = xlrd.open_workbook(file_path)
    ws = wb.sheet_by_index(0)

    records = []
    error_count = 0
    error_messages = []

    # Читаем заголовки
    headers = [str(ws.cell_value(0, c)).strip() for c in range(ws.ncols)]

    # Проверка обязательных полей (без ИНН/названий УЦ и Заказчика)
    required_fields = ['Фамилия', 'Имя', 'Отчество', 'СНИЛС', 'Должность', 'Результат', '№ программы', 'Дата', '№ протокола']
    for col in required_fields:
        if col not in headers:
            return None, 0, [f"Отсутствует столбец: {col}"]

    for row_num in range(1, ws.nrows):
        row_dict = {}
        for c_idx, col_name in enumerate(headers):
            cell = ws.cell(row_num, c_idx)
            val = cell.value
            # Преобразование Excel-дат в datetime
            if cell.ctype in (xlrd.XL_CELL_DATE, xlrd.XL_CELL_DATETIME):
                try:
                    val = dt(*xldate_as_tuple(val, wb.datemode))
                except Exception:
                    pass
            row_dict[col_name] = val if val is not None else ''

        is_valid, result = validate_row(row_dict, row_num + 1)
        if is_valid:
            records.extend(result)
        else:
            error_count += 1
            error_messages.append(result)

    return records, error_count, error_messages
