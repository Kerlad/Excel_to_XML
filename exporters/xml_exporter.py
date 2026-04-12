"""
Модуль конвертации данных в XML согласно схеме educated_person_import_v1.0.9.xsd
"""
import os
import uuid
import logging
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, ElementTree
import xml.etree.ElementTree as ET
import xml.dom.minidom

logging.basicConfig(filename='export_errors.log', level=logging.ERROR, encoding='utf-8')

# Названия программ согласно XSD (learnProgram: название)
PROGRAM_TITLES = {
    "1": "Оказание первой помощи пострадавшим",
    "2": "Использование (применение) средств индивидуальной защиты",
    "3": "Общие вопросы охраны труда и функционирования системы управления охраной труда",
    "4": "Безопасные методы и приемы выполнения работ при воздействии вредных и (или) опасных производственных факторов, источников опасности, идентифицированных в рамках специальной оценки условий труда и оценки профессиональных рисков",
    "6": "Безопасные методы и приемы выполнения земляных работ",
    "7": "Безопасные методы и приемы выполнения ремонтных, монтажных и демонтажных работ зданий и сооружений",
    "8": "Безопасные методы и приемы выполнения работ при размещении, монтаже, техническом обслуживании и ремонте технологического оборудования (включая технологическое оборудование)",
    "9": "Безопасные методы и приемы выполнения работ на высоте",
    "10": "Безопасные методы и приемы выполнения пожароопасных работ",
    "11": "Безопасные методы и приемы выполнения работ в ограниченных и замкнутых пространствах (ОЗП)",
    "12": "Безопасные методы и приемы выполнения строительных работ, в том числе: - окрасочные работы - электросварочные и газосварочные работы",
    "13": "Безопасные методы и приемы выполнения работ, связанных с опасностью воздействия сильнодействующих и ядовитых веществ",
    "14": "Безопасные методы и приемы выполнения газоопасных работ",
    "15": "Безопасные методы и приемы выполнения огневых работ",
    "16": "Безопасные методы и приемы выполнения работ, связанных с эксплуатацией подъемных сооружений",
    "17": "Безопасные методы и приемы выполнения работ, связанных с эксплуатацией тепловых энергоустановок",
    "18": "Безопасные методы и приемы выполнения работ в электроустановках",
    "19": "Безопасные методы и приемы выполнения работ, связанных с эксплуатацией сосудов, работающих под избыточным давлением",
    "20": "Безопасные методы и приемы обращения с животными",
    "21": "Безопасные методы и приемы при выполнении водолазных работ",
    "22": "Безопасные методы и приемы работ по поиску, идентификации, обезвреживанию и уничтожению взрывоопасных предметов",
    "23": "Безопасные методы и приемы работ в непосредственной близости от полотна или проезжей части эксплуатируемых автомобильных и железных дорог",
    "24": "Безопасные методы и приемы работ на участках с патогенным заражением почвы",
    "25": "Безопасные методы и приемы работ по валке леса в особо опасных условиях",
    "26": "Безопасные методы и приемы работ по перемещению тяжеловесных и крупногабаритных грузов при отсутствии машин соответствующей грузоподъемности и разборке покосившихся и опасных (неправильно уложенных) штабелей круглых лесоматериалов",
    "27": "Безопасные методы и приемы работ с радиоактивными веществами и источниками ионизирующих излучений",
    "28": "Безопасные методы и приемы работ с ручным инструментом, в том числе с пиротехническим",
    "29": "Безопасные методы и приемы работ в театрах"
}


def format_snils(snils_raw):
    """Форматирование СНИЛС в вид '123-456-789 00' (требование сервера)"""
    clean = str(snils_raw).replace('-', '').replace(' ', '')
    if len(clean) != 11:
        return snils_raw
    return f"{clean[0:3]}-{clean[3:6]}-{clean[6:9]} {clean[9:11]}"


def format_date_xsd(date_str):
    """Форматирование даты в xs:date (YYYY-MM-DD)"""
    clean = str(date_str).replace('.', '').replace('-', '')
    if len(clean) == 8 and clean.isdigit():
        try:
            dt = datetime.strptime(clean, "%d%m%Y")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return None
    # Уже в формате YYYY-MM-DD
    if len(date_str) == 10 and date_str[4] == '-' and date_str[7] == '-':
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return date_str
        except ValueError:
            return None
    return None


def is_passed(result):
    """Конвертация результата в bit: true/false"""
    if result == "Удовлетворительно":
        return "true"
    return "false"


def build_xml(records, org_settings=None):
    """
    Построение XML-документа согласно XSD educated_person_import_v1.0.9.xsd

    Структура:
    RegistrySet
      └── RegistryRecord (outerId, maxOccurs=5000)
            ├── Worker (LastName, FirstName, MiddleName, Snils, Position, EmployerInn, EmployerTitle)
            ├── Organization (Inn, Title) — Учебный центр
            └── Test (isPassed, learnProgramId, Date, ProtocolNumber, LearnProgramTitle)
    """
    # Корневой элемент
    root = Element("RegistrySet")

    for rec in records:
        # RegistryRecord с опциональным outerId
        record = SubElement(root, "RegistryRecord")
        record.set("outerId", str(uuid.uuid4()))

        # --- Worker ---
        worker = SubElement(record, "Worker")

        last_name = SubElement(worker, "LastName")
        last_name.text = rec.get('last_name', '')

        first_name = SubElement(worker, "FirstName")
        first_name.text = rec.get('first_name', '')

        middle_name = SubElement(worker, "MiddleName")
        middle_name.text = rec.get('middle_name', '')

        snils = SubElement(worker, "Snils")
        snils.text = format_snils(rec.get('snils', ''))

        position = SubElement(worker, "Position")
        position.text = rec.get('position', '')

        employer_inn = SubElement(worker, "EmployerInn")
        employer_inn.text = str(rec.get('employer_inn', '')).strip()

        employer_title = SubElement(worker, "EmployerTitle")
        employer_title.text = rec.get('employer_title', '')

        # --- Organization (Учебный центр) ---
        organization = SubElement(record, "Organization")

        tc_inn = org_settings.get('tc_inn', rec.get('tc_inn', '')) if org_settings else rec.get('tc_inn', '')
        org_inn = SubElement(organization, "Inn")
        org_inn.text = str(tc_inn).strip()

        tc_title = org_settings.get('tc_title', rec.get('tc_title', '')) if org_settings else rec.get('tc_title', '')
        org_title = SubElement(organization, "Title")
        org_title.text = tc_title

        # --- Test ---
        test = SubElement(record, "Test")
        test.set("isPassed", is_passed(rec.get('result', '')))
        test.set("learnProgramId", str(rec.get('program', '')))

        # Дата в формате xs:date
        date_elem = SubElement(test, "Date")
        formatted_date = format_date_xsd(rec.get('date', ''))
        date_elem.text = formatted_date if formatted_date else rec.get('date', '')

        protocol = SubElement(test, "ProtocolNumber")
        protocol.text = str(rec.get('protocol', ''))

        program_id = str(rec.get('program', ''))
        learn_title = SubElement(test, "LearnProgramTitle")
        learn_title.text = PROGRAM_TITLES.get(program_id, '')

    # Форматирование XML с отступами
    rough_string = ET.tostring(root, encoding='utf-8', xml_declaration=False)

    try:
        dom = xml.dom.minidom.parseString(rough_string)
        pretty_xml = dom.toprettyxml(indent="  ", encoding='UTF-8')
        # Заменяем декларацию minidom на нашу
        pretty_str = pretty_xml.decode('utf-8')
        lines = pretty_str.split('\n')
        if lines[0].startswith('<?xml'):
            lines[0] = '<?xml version="1.0" encoding="UTF-8"?>'
        return '\n'.join(lines).encode('utf-8')
    except Exception as e:
        logging.error(f"Ошибка форматирования XML: {e}")
        xml_declaration = b'<?xml version="1.0" encoding="UTF-8"?>\n'
        return xml_declaration + rough_string


def export_to_xml(records, file_path, org_settings=None):
    """
    Экспорт данных в XML файл согласно XSD.

    records — список словарей с полями:
        last_name, first_name, middle_name, snils, position,
        employer_inn, employer_title, tc_inn, tc_title,
        result, program, date, protocol

    file_path — путь для сохранения
    org_settings — настройки организации (опционально)

    Возвращает (True, message) или (False, error_message)
    """
    try:
        if not records:
            return False, "Нет данных для экспорта"

        if len(records) > 5000:
            return False, "Превышен лимит: max 5000 записей (RegistryRecord)"

        xml_content = build_xml(records, org_settings)

        with open(file_path, 'wb') as f:
            f.write(xml_content)

        return True, f"Файл сохранён: {file_path}\nЗаписей: {len(records)}"

    except PermissionError:
        return False, "Нет прав на запись файла"
    except Exception as e:
        logging.error(f"Ошибка экспорта в XML: {e}")
        return False, f"Ошибка экспорта: {e}"
