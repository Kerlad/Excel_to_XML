"""
Конвертер данных в XML формат согласно XSD схеме Минтруда
"""

from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from typing import Optional
import os

from core.data_model import DataManager, WorkerRecord


class XMLConverter:
    """Конвертер данных в XML"""

    # Программы обучения
    PROGRAM_NAMES = {
        "1": "Оказание первой помощи пострадавшим",
        "2": "Использование (применение) средств индивидуальной защиты",
        "3": "Общие вопросы охраны труда и функционирования системы управления охраной труда",
        "4": "Безопасные методы и приемы выполнения работ при воздействии вредных и (или) опасных производственных факторов",
        "6": "Безопасные методы и приемы выполнения земляных работ",
        "7": "Безопасные методы и приемы выполнения ремонтных, монтажных и демонтажных работ зданий и сооружений",
        "8": "Безопасные методы и приемы выполнения работ при размещении, монтаже, техническом обслуживании и ремонте технологического оборудования",
        "9": "Безопасные методы и приемы выполнения работ на высоте",
        "10": "Безопасные методы и приемы выполнения пожароопасных работ",
        "11": "Безопасные методы и приемы выполнения работ в ограниченных и замкнутых пространствах (ОЗП)",
        "12": "Безопасные методы и приемы выполнения строительных работ",
        "13": "Безопасные методы и приемы выполнения работ, связанных с опасностью воздействия сильнодействующих и ядовитых веществ",
        "14": "Безопасные методы и приемы выполнения газоопасных работ",
        "15": "Безопасные методы и приемы выполнения огневых работ",
        "16": "Безопасные методы и приемы выполнения работ, связанных с эксплуатацией подъемных сооружений",
        "17": "Безопасные методы и приемы выполнения работ, связанные с эксплуатацией тепловых энергоустановок",
        "18": "Безопасные методы и приемы выполнения работ в электроустановках",
        "19": "Безопасные методы и приемы выполнения работ, связанные с эксплуатацией сосудов, работающих под избыточным давлением",
        "20": "Безопасные методы и приемы обращения с животными",
        "21": "Безопасные методы и приемы при выполнении водолазных работ",
        "22": "Безопасные методы и приемы работ по поиску, идентификации, обезвреживанию и уничтожению взрывоопасных предметов",
        "23": "Безопасные методы и приемы работ в непосредственной близости от полотна или проезжей части эксплуатируемых автомобильных и железных дорог",
        "24": "Безопасные методы и приемы работ на участках с патогенным заражением почвы",
        "25": "Безопасные методы и приемы работ по валке леса в особо опасных условиях",
        "26": "Безопасные методы и приемы работ по перемещению тяжеловесных и крупногабаритных грузов",
        "27": "Безопасные методы и приемы работ с радиоактивными веществами и источниками ионизирующих излучений",
        "28": "Безопасные методы и приемы работ с ручным инструментом",
        "29": "Безопасные методы и приемы работ в театрах"
    }

    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager

    def convert(self, filepath: str) -> tuple[bool, str]:
        """
        Конвертация данных в XML
        Возвращает кортеж (успех, сообщение)
        """
        if not self.data_manager.records:
            return False, "Нет данных для конвертации"

        try:
            # Создание корневого элемента
            root = Element("RegistrySet")

            for record in self.data_manager.records:
                registry_record = self._create_registry_record(record)
                root.append(registry_record)

            # Преобразование в строку
            xml_str = tostring(root, encoding='utf-8', method='xml')

            # Форматирование
            dom = minidom.parseString(xml_str)
            pretty_xml = dom.toprettyxml(indent="  ", encoding='utf-8')

            # Сохранение в файл
            with open(filepath, 'wb') as f:
                f.write(pretty_xml)

            return True, f"XML файл создан: {filepath}"

        except Exception as e:
            return False, f"Ошибка конвертации: {str(e)}"

    def _create_registry_record(self, record: WorkerRecord) -> Element:
        """Создание элемента RegistryRecord"""
        registry_record = Element("RegistryRecord")

        # Элемент Worker
        worker = SubElement(registry_record, "Worker")
        SubElement(worker, "LastName").text = record.last_name
        SubElement(worker, "FirstName").text = record.first_name
        SubElement(worker, "MiddleName").text = record.middle_name
        SubElement(worker, "Snils").text = record.snils.replace('-', '').replace(' ', '')
        SubElement(worker, "IsForeignSnils").text = "false"
        SubElement(worker, "Position").text = record.position
        SubElement(worker, "EmployerInn").text = record.employer_inn
        SubElement(worker, "EmployerTitle").text = record.employer_title

        # Элемент Organization (Учебный центр)
        organization = SubElement(registry_record, "Organization")
        SubElement(organization, "Inn").text = record.training_center_inn
        SubElement(organization, "Title").text = record.training_center_title

        # Элемент Test
        test = SubElement(registry_record, "Test")

        # Форматирование даты (YYYY-MM-DD)
        date_str = record.date
        if '.' in date_str:
            parts = date_str.split('.')
            if len(parts) == 3:
                date_str = f"{parts[2]}-{parts[1]}-{parts[0]}"

        SubElement(test, "Date").text = date_str
        SubElement(test, "ProtocolNumber").text = record.protocol_number

        # Номер программы и название
        program_id = record.program_numbers
        program_title = self.PROGRAM_NAMES.get(program_id, f"Программа №{program_id}")

        SubElement(test, "LearnProgramTitle").text = program_title

        # Атрибуты isPassed и learnProgramId
        test.set("isPassed", "true" if record.result == "Удовлетворительно" else "false")
        test.set("learnProgramId", program_id)

        return registry_record