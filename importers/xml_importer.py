"""
Модуль загрузки XML файлов (поддержка формата RegistrySet из XSD educated_person_import_v1.0.9.xsd)
"""
import os
import logging

from utils.constants import VALID_PROGRAMS_SET as VALID_PROGRAMS

try:
    from defusedxml.ElementTree import parse as _parse, fromstring as _fromstring
    from defusedxml.ElementTree import XMLParser as _XMLParser
    _HAS_DEFUSEDXML = True
except ImportError:
    from xml.etree.ElementTree import parse as _parse, fromstring as _fromstring
    from xml.etree.ElementTree import XMLParser as _XMLParser
    _HAS_DEFUSEDXML = False

logging.basicConfig(filename='import_errors.log', level=logging.ERROR, encoding='utf-8')

MAX_XML_SIZE_MB = 100
NS = {'xs': 'http://www.w3.org/2001/XMLSchema'}


def load_xml(file_path, xsd_path=None):
    """
    Загрузка XML файла.
    
    file_path — путь к XML
    xsd_path — путь к XSD для валидации (опционально)
    
    Возвращает (records, error_count, error_messages, xsd_errors)
    xsd_errors — список ошибок XSD-валидации (если xsd_path указан)
    """
    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if size_mb > MAX_XML_SIZE_MB:
        return None, 0, [f"Файл превышает лимит {MAX_XML_SIZE_MB} МБ ({size_mb:.1f} МБ)"], []
    # Парсинг (XXE-safe)
    try:
        tree = _parse(file_path)
        root = tree.getroot()
    except Exception as e:
        return None, 0, [f"Ошибка парсинга XML: {e}"], []

    # XSD-валидация (если указана схема)
    xsd_errors = []
    if xsd_path and os.path.exists(xsd_path):
        try:
            from lxml import etree
            schema_doc = etree.parse(xsd_path)
            schema = etree.XMLSchema(schema_doc)
            xml_doc = etree.parse(file_path)
            try:
                schema.assertValid(xml_doc)
            except etree.DocumentInvalid as e:
                xsd_errors = [str(err.message.strip()) for err in schema.error_log]
        except ImportError:
            xsd_errors = ["lxml не установлен. XSD-валидация недоступна: pip install lxml"]
        except Exception as e:
            xsd_errors = [f"Ошибка XSD-валидации: {e}"]

    # Определяем формат XML
    tag = root.tag
    if tag == "RegistrySet":
        return _load_registry_set(root, xsd_errors)
    else:
        # Legacy формат — пробуем стандартный парсинг
        return _load_legacy_xml(root, xsd_errors)


def _load_registry_set(root, xsd_errors):
    """Загрузка XML в формате RegistrySet (по XSD)."""
    records = []
    error_count = 0
    error_messages = []

    for rec_idx, record in enumerate(root.findall('RegistryRecord'), start=1):
        worker = record.find('Worker')
        organization = record.find('Organization')
        test = record.find('Test')

        if worker is None or organization is None or test is None:
            error_count += 1
            error_messages.append(f"Запись {rec_idx}: отсутствуют обязательные элементы Worker/Organization/Test")
            continue

        # Извлечение данных
        def get_text(elem, tag_name, default=''):
            child = elem.find(tag_name)
            return child.text.strip() if child is not None and child.text else default

        last_name = get_text(worker, 'LastName')
        first_name = get_text(worker, 'FirstName')
        middle_name = get_text(worker, 'MiddleName')
        snils_raw = get_text(worker, 'Snils', '')
        position = get_text(worker, 'Position')
        employer_inn = get_text(worker, 'EmployerInn')
        employer_title = get_text(worker, 'EmployerTitle')

        tc_inn = get_text(organization, 'Inn')
        tc_title = get_text(organization, 'Title')

        date_val = get_text(test, 'Date')
        protocol = get_text(test, 'ProtocolNumber')
        program_id = test.get('learnProgramId', '')
        is_passed = test.get('isPassed', '')

        # Конвертация isPassed
        result = "Удовлетворительно" if is_passed.lower() in ['true', '1'] else "Неудовлетворительно"

        # Конвертация даты из YYYY-MM-DD или YYYY-MM-DDTHH:MM:SS в ДД.ММ.ГГГГ
        date_formatted = date_val
        if date_val:
            try:
                from datetime import datetime
                if 'T' in date_val:
                    dt = datetime.fromisoformat(date_val.replace('Z', '+00:00'))
                else:
                    dt = datetime.strptime(date_val[:10], "%Y-%m-%d")
                date_formatted = dt.strftime("%d.%m.%Y")
            except (ValueError, TypeError):
                pass

        # Очистка СНИЛС
        snils = snils_raw.replace('-', '').replace(' ', '')

        # Валидация
        errors = []
        if not all([last_name, first_name, position, employer_inn, employer_title]):
            errors.append(f"Запись {rec_idx}: заполнены не все обязательные поля")

        if not snils:
            errors.append(f"Запись {rec_idx}: СНИЛС обязателен")
        elif not snils.isdigit() or len(snils) != 11:
            errors.append(f"Запись {rec_idx}: СНИЛС должен содержать 11 цифр")

        if program_id not in VALID_PROGRAMS:
            errors.append(f"Запись {rec_idx}: некорректный номер программы '{program_id}'")

        if errors:
            error_count += 1
            error_messages.extend(errors)
            continue

        record_data = {
            'last_name': last_name,
            'first_name': first_name,
            'middle_name': middle_name,
            'snils': snils,
            'position': position,
            'employer_inn': employer_inn,
            'employer_title': employer_title,
            'tc_inn': tc_inn,
            'tc_title': tc_title,
            'result': result,
            'program': program_id,
            'date': date_formatted,
            'protocol': protocol
        }
        records.append(record_data)

    return records, error_count, error_messages, xsd_errors


def _load_legacy_xml(root, xsd_errors):
    """Загрузка XML в произвольном формате (legacy)."""
    records = []
    error_count = 0
    error_messages = []

    # Ищем элементы с данными
    employee_elements = []
    for child in root:
        if child.tag.lower() in ['employee', 'работник', 'worker', 'registryrecord', 'record']:
            employee_elements.append(child)
        else:
            for sub in child:
                if sub.tag.lower() in ['employee', 'работник', 'worker', 'registryrecord', 'record']:
                    employee_elements.append(sub)

    if not employee_elements:
        employee_elements = list(root)

    for idx, elem in enumerate(employee_elements, start=1):
        data = {}
        for child in elem:
            data[child.tag] = child.text or ''
            # Альтернативные имена
            tag_lower = child.tag.lower()
            if tag_lower == 'inn':
                # Определяем контекст по родительскому элементу
                parent_tag = elem.tag.lower() if elem is not None else ''
                if 'worker' in parent_tag or 'работник' in parent_tag:
                    data['employer_inn'] = child.text or ''
                elif 'organization' in parent_tag or 'организация' in parent_tag:
                    data['tc_inn'] = child.text or ''
            elif tag_lower == 'title':
                parent_tag = elem.tag.lower() if elem is not None else ''
                if 'worker' in parent_tag or 'работник' in parent_tag:
                    data['employer_title'] = child.text or ''
                elif 'organization' in parent_tag or 'организация' in parent_tag:
                    data['tc_title'] = child.text or ''
            elif tag_lower in ['lastname', 'фамилия']:
                data['last_name'] = child.text or ''
            elif tag_lower in ['firstname', 'имя']:
                data['first_name'] = child.text or ''
            elif tag_lower in ['middlename', 'отчество']:
                data['middle_name'] = child.text or ''
            elif tag_lower in ['snils', 'снилс']:
                data['snils'] = (child.text or '').replace('-', '').replace(' ', '')
            elif tag_lower in ['position', 'должность']:
                data['position'] = child.text or ''
            elif tag_lower in ['employerinn', 'инн_заказчика', 'инн заказчика']:
                data['employer_inn'] = child.text or ''
            elif tag_lower in ['employertitle', 'наименование юл заказчика']:
                data['employer_title'] = child.text or ''
            elif tag_lower in ['инн_уц', 'инн уц']:
                data['tc_inn'] = child.text or ''
            elif tag_lower in ['наименование уц', 'наименование_уц']:
                data['tc_title'] = child.text or ''
            elif tag_lower in ['result', 'результат']:
                data['result'] = child.text or ''
            elif tag_lower in ['program', 'номер_программы', 'номер программы']:
                data['program'] = child.text or ''
            elif tag_lower in ['date', 'дата']:
                data['date'] = child.text or ''
            elif tag_lower in ['protocolnumber', 'номер_протокола', 'номер протокола']:
                data['protocol'] = child.text or ''

        # Проверяем обязательные поля
        errors = []
        for field in ['last_name', 'first_name', 'position', 'employer_inn', 'employer_title']:
            if not data.get(field, '').strip():
                errors.append(f"Запись {idx}: отсутствует {field}")

        snils = data.get('snils', '')
        if snils and (not snils.isdigit() or len(snils) != 11):
            errors.append(f"Запись {idx}: СНИЛС должен содержать 11 цифр")

        program = data.get('program', '')
        if program not in VALID_PROGRAMS:
            errors.append(f"Запись {idx}: некорректный номер программы '{program}'")

        result = data.get('result', '')
        if result and result not in ['Удовлетворительно', 'Неудовлетворительно']:
            errors.append(f"Запись {idx}: некорректный результат '{result}'")

        if errors:
            error_count += 1
            error_messages.extend(errors)
            continue

        if not data.get('result'):
            data['result'] = 'Удовлетворительно'

        records.append({
            'last_name': data.get('last_name', ''),
            'first_name': data.get('first_name', ''),
            'middle_name': data.get('middle_name', ''),
            'snils': snils,
            'position': data.get('position', ''),
            'employer_inn': data.get('employer_inn', ''),
            'employer_title': data.get('employer_title', ''),
            'tc_inn': data.get('tc_inn', ''),
            'tc_title': data.get('tc_title', ''),
            'result': data.get('result', 'Удовлетворительно'),
            'program': program,
            'date': data.get('date', ''),
            'protocol': data.get('protocol', '')
        })

    return records, error_count, error_messages, xsd_errors
