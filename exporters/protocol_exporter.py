"""
Экспорт протокола проверки знаний
Заполнение шаблона Protokol_proverki_znanii_OT.xlsx данными из журнала
"""
import os
import shutil
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


# Названия программ согласно справочнику
PROGRAM_TITLES = {
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
    "17": "Безопасные методы и приемы выполнения работ, связанных с эксплуатацией тепловых энергоустановок",
    "18": "Безопасные методы и приемы выполнения работ в электроустановках",
    "19": "Безопасные методы и приемы выполнения работ, связанных с эксплуатацией сосудов, работающих под избыточным давлением",
    "20": "Безопасные методы и приемы обращения с животными",
    "21": "Безопасные методы и приемы при выполнении водолазных работ",
    "22": "Безопасные методы и приемы работ по поиску, идентификации, обезвреживанию и уничтожению взрывоопасных предметов",
    "23": "Безопасные методы и приемы работ в непосредственной близости от полотна или проезжей части эксплуатируемых автомобильных и железных дорог",
    "24": "Безопасные методы и приемы работ на участках с патогенным заражением почвы",
    "25": "Безопасные методы и приемы работ по валке леса в особо опасных условиях",
    "26": "Безопасные методы и приемы работ по перемещению тяжеловесных и крупногабаритных грузов",
    "27": "Безопасные методы и приемы работ с радиоактивными веществами и источниками ионизирующих излучений",
    "28": "Безопасные методы и приемы работ с ручным инструментом, в том числе с пиротехническим",
    "29": "Безопасные методы и приемы работ в театрах"
}


class ProtocolExporter:
    """Экспорт протокола проверки знаний из данных журнала."""

    @staticmethod
    def export_protocol(records, output_path, template_path, data_dir) -> tuple[bool, str]:
        """
        Формирование протокола проверки знаний на основе данных журнала.

        records — список JournalRecord (отфильтрованные записи)
        output_path — путь для сохранения итогового XLSX
        template_path — путь к шаблону Protokol_proverki_zhanii_OT.xlsx
        data_dir — директория data (для org_settings.json)

        Возвращает (success: bool, message: str)
        """
        try:
            from openpyxl import load_workbook
        except ImportError:
            return False, "Установите openpyxl: pip install openpyxl"

        if not records:
            return False, "Нет данных для формирования протокола"

        # Проверяем шаблон
        if not os.path.exists(template_path):
            return False, f"Шаблон протокола не найден:\n{template_path}"

        try:
            # Загружаем настройки организации
            org_settings = ProtocolExporter._load_org_settings(data_dir)

            # Копируем шаблон
            shutil.copy2(template_path, output_path)

            # Открываем копию
            wb = load_workbook(output_path)
            ws = wb.active

            # Заполняем данные организации (ячейки зависят от шаблона)
            # По protocol_create.md: данные организации берутся из GUI
            ProtocolExporter._fill_org_data(ws, org_settings)

            # Группировка записей по номеру протокола и программе
            # Один протокол = одна программа + один номер протокола
            protocol_groups = {}
            for rec in records:
                key = (rec.protocol, rec.program_id)
                if key not in protocol_groups:
                    protocol_groups[key] = []
                protocol_groups[key].append(rec)

            # Если несколько групп — берём первую (или можно создать несколько листов)
            if len(protocol_groups) > 1:
                # Предупреждение, но продолжаем с первой группой
                pass

            first_key = list(protocol_groups.keys())[0]
            group_records = protocol_groups[first_key]

            # Заполняем workers
            # Строка 1 = заголовки, Строка 2+ = данные
            start_row = 2  # Первая строка данных (после заголовков)

            for idx, rec in enumerate(group_records):
                row = start_row + idx

                # Колонки согласно protocol_create.md:
                # A=Фамилия, B=Имя, C=Отчество, D=СНИЛС, E=Должность,
                # F=Номер программы, G=Результат, H=Дата проверки, I=Номер протокола
                ws[f'A{row}'] = rec.last_name
                ws[f'B{row}'] = rec.first_name
                ws[f'C{row}'] = rec.middle_name
                ws[f'D{row}'] = rec.snils
                ws[f'E{row}'] = rec.position
                ws[f'F{row}'] = rec.program_id
                ws[f'G{row}'] = "Удовлетворительно" if rec.result == "Удовлетворительно" or rec.status == "received" else "Неудовлетворительно"
                ws[f'H{row}'] = rec.exam_date
                ws[f'I{row}'] = rec.protocol

            wb.save(output_path)

            return True, f"Протокол сохранён:\n{output_path}\nЗаписей: {len(group_records)}"

        except Exception as e:
            logger.error(f"Ошибка экспорта протокола: {e}")
            return False, f"Ошибка формирования протокола: {e}"

    @staticmethod
    def _fill_org_data(ws, org_settings):
        """
        Заполнение данных организации в шаблоне.

        Точные ячейки зависят от структуры шаблона Protokol_proverki_znanii_OT.xlsx.
        По protocol_create.md:
            ИНН Заказчика, Наименование заказчика, ИНН УЦ, Наименование УЦ
        """
        # Попробуем найти ячейки по заголовкам (универсальный подход)
        # Или используем фиксированные ячейки, если шаблон стандартный

        # Эвристика: ищем ячейки с ключевыми словами
        mappings = {
            'ИНН Заказчика': org_settings.get('employer_inn', ''),
            'Наименование': org_settings.get('employer_title', ''),
            'ИНН УЦ': org_settings.get('tc_inn', ''),
            'Наименование УЦ': org_settings.get('tc_title', ''),
        }

        for row in ws.iter_rows(min_row=1, max_row=30, max_col=10):
            for cell in row:
                if cell.value and isinstance(cell.value, str):
                    cell_val = cell.value.strip()
                    for keyword, value in mappings.items():
                        if keyword.lower() in cell_val.lower() and value:
                            # Записываем в соседнюю ячейку справа
                            target = ws.cell(row=cell.row, column=cell.column + 1)
                            target.value = value

    @staticmethod
    def _load_org_settings(data_dir: str) -> dict:
        """Загрузка настроек организации."""
        import json
        settings_file = os.path.join(data_dir, "org_settings.json")
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            'tc_inn': '', 'tc_title': '',
            'employer_inn': '', 'employer_title': ''
        }

    @staticmethod
    def generate_from_commission(commission_data: dict, protocol_number: str,
                                  programs_manager, output_path: str, template_path: str,
                                  data_dir: str) -> tuple[bool, str]:
        """
        Генерация протокола с данными комиссии.

        commission_data — данные комиссии (org_name, order_number, order_date,
                          chairman_fio, chairman_position, member*_fio, member*_position,
                          union_fio, union_position)
        protocol_number — номер протокола
        programs_manager — менеджер программ обучения (для номеров документов и часов)
        output_path — путь для сохранения
        template_path — путь к шаблону
        data_dir — директория data

        Возвращает (success: bool, message: str)
        """
        try:
            from openpyxl import load_workbook
        except ImportError:
            return False, "Установите openpyxl: pip install openpyxl"

        # Проверяем шаблон
        if not os.path.exists(template_path):
            return False, f"Шаблон протокола не найден:\n{template_path}"

        try:
            # Копируем шаблон
            import shutil
            shutil.copy2(template_path, output_path)

            # Открываем копию
            wb = load_workbook(output_path)
            ws = wb.active

            # Заполняем шаблон данными комиссии (эвристика по ключевым словам)
            ProtocolExporter._fill_commission_data(ws, commission_data, protocol_number)

            wb.save(output_path)
            return True, f"Протокол сформирован.\nФайл сохранён: {output_path}"

        except Exception as e:
            logger.error(f"Ошибка генерации протокола: {e}")
            return False, f"Ошибка формирования протокола: {e}"

    @staticmethod
    def _fill_commission_data(ws, commission_data: dict, protocol_number: str):
        """
        Заполнение ячеек шаблона данными комиссии.
        Использует эвристику — поиск по ключевым словам в заголовках.
        """
        mappings = {
            'номер протокол': protocol_number,
            'название организации': commission_data.get('org_name', ''),
            'наименование организации': commission_data.get('org_name', ''),
            'приказ': commission_data.get('order_number', ''),
            'дата приказа': commission_data.get('order_date', ''),
            'председатель': commission_data.get('chairman_fio', ''),
            'должность председателя': commission_data.get('chairman_position', ''),
            'член комиссии №1': commission_data.get('member1_fio', ''),
            'член комиссии 1': commission_data.get('member1_fio', ''),
            'должность члена 1': commission_data.get('member1_position', ''),
            'член комиссии №2': commission_data.get('member2_fio', ''),
            'член комиссии 2': commission_data.get('member2_fio', ''),
            'должность члена 2': commission_data.get('member2_position', ''),
            'член комиссии №3': commission_data.get('member3_fio', ''),
            'член комиссии 3': commission_data.get('member3_fio', ''),
            'должность члена 3': commission_data.get('member3_position', ''),
            'профсоюз': commission_data.get('union_fio', ''),
            'должность профсоюза': commission_data.get('union_position', ''),
        }

        # Защита от двойной записи одного ключа
        filled_keys = set()

        # Ищем по всему листу (первые 50 строк)
        for row in ws.iter_rows(min_row=1, max_row=50, max_col=15):
            for cell in row:
                if cell.value and isinstance(cell.value, str):
                    cell_val = cell.value.strip().lower()
                    for keyword, value in mappings.items():
                        if keyword in cell_val and value and keyword not in filled_keys:
                            target = ws.cell(row=cell.row, column=cell.column + 1)
                            if not target.value:
                                target.value = value
                                filled_keys.add(keyword)
                            break
