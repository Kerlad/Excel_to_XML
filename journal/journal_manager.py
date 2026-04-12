"""
Менеджер журнала проверок знаний
CRUD операции + поиск/фильтрация + обновление baseNo
"""
import os
import json
import uuid
import logging
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)


@dataclass
class JournalRecord:
    """Одна запись в журнале (один работник)."""
    uuid: str
    send_date: str                # Дата/время отправки на сервер
    set_id: str                   # SetId от сервера
    xml_file: str                 # Путь к отправленному XML файлу
    last_name: str
    first_name: str
    middle_name: str
    snils: str                    # Формат: "123-456-789 00"
    position: str
    program_id: str               # Номер программы: "1"-"29"
    program_title: str            # Название программы
    exam_date: str                # Дата экзамена: "ДД.ММ.ГГГГ"
    protocol: str                 # Номер протокола
    base_no: str = ""             # Регистрационный номер (заполняется позже)
    status: str = "pending"       # "pending" | "received"


class JournalManager:
    """Управление журналом проверок знаний."""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.journal_file = os.path.join(self.data_dir, "exam_journal.json")
        self.records: List[JournalRecord] = []
        self._load()

    # ============ CRUD ============

    def _load(self):
        """Загрузка журнала из файла."""
        if os.path.exists(self.journal_file):
            try:
                with open(self.journal_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.records = []
                for item in data:
                    record = JournalRecord(
                        uuid=item.get('uuid', str(uuid.uuid4())),
                        send_date=item.get('send_date', ''),
                        set_id=item.get('set_id', ''),
                        xml_file=item.get('xml_file', ''),
                        last_name=item.get('last_name', ''),
                        first_name=item.get('first_name', ''),
                        middle_name=item.get('middle_name', ''),
                        snils=item.get('snils', ''),
                        position=item.get('position', ''),
                        program_id=item.get('program_id', ''),
                        program_title=item.get('program_title', ''),
                        exam_date=item.get('exam_date', ''),
                        protocol=item.get('protocol', ''),
                        base_no=item.get('base_no', ''),
                        status=item.get('status', 'pending')
                    )
                    self.records.append(record)
            except Exception as e:
                logger.error(f"Ошибка загрузки журнала: {e}")
                self.records = []

    def _save(self):
        """Сохранение журнала в файл."""
        try:
            data = [asdict(r) for r in self.records]
            with open(self.journal_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения журнала: {e}")

    def add_records(self, records_data: List[Dict], set_id: str, xml_file: str) -> int:
        """
        Добавление записей в журнал (при успешной отправке XML).

        records_data — список словарей с полями работника (как для XML экспорта)
        set_id — идентификатор набора от сервера
        xml_file — путь к отправленному XML файлу

        Возвращает количество добавленных записей.
        """
        send_date = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        added = 0

        for rec in records_data:
            program_id = str(rec.get('program', ''))
            program_title = self._get_program_title(program_id)

            record = JournalRecord(
                uuid=str(uuid.uuid4()),
                send_date=send_date,
                set_id=set_id,
                xml_file=xml_file,
                last_name=rec.get('last_name', ''),
                first_name=rec.get('first_name', ''),
                middle_name=rec.get('middle_name', ''),
                snils=rec.get('snils', ''),
                position=rec.get('position', ''),
                program_id=program_id,
                program_title=program_title,
                exam_date=rec.get('date', ''),
                protocol=rec.get('protocol', ''),
                base_no="",
                status="pending"
            )
            self.records.append(record)
            added += 1

        self._save()
        return added

    def update_base_no_by_set_id(self, set_id: str, base_no_map: Dict[str, str]) -> int:
        """
        Обновление baseNo для всех записей с данным SetId.

        set_id — идентификатор набора
        base_no_map — словарь {snils: baseNo} из ответа сервера

        Возвращает количество обновлённых записей.
        """
        updated = 0
        for record in self.records:
            if record.set_id == set_id and record.status == "pending":
                # Ищем baseNo по СНИЛС
                snils_clean = record.snils.replace('-', '').replace(' ', '')
                if snils_clean in base_no_map:
                    record.base_no = base_no_map[snils_clean]
                    record.status = "received"
                    updated += 1

        if updated > 0:
            self._save()
        return updated

    def delete_by_uuid(self, uuids: List[str]) -> int:
        """
        Удаление записей по UUID.

        uuids — список UUID для удаления
        Возвращает количество удалённых записей.
        """
        original_count = len(self.records)
        self.records = [r for r in self.records if r.uuid not in uuids]
        deleted = original_count - len(self.records)

        if deleted > 0:
            self._save()
        return deleted

    # ============ Поиск и фильтрация ============

    def search(self, query: str = "", set_id: str = "",
               status: str = "all", date_from: str = "", date_to: str = "") -> List[JournalRecord]:
        """
        Поиск и фильтрация записей.

        query — поиск по ФИО/СНИЛС (вхождение, регистронезависимо)
        set_id — фильтр по SetId (точное совпадение)
        status — "pending", "received", "all"
        date_from — дата отправки с (ДД.ММ.ГГГГ)
        date_to — дата отправки по (ДД.ММ.ГГГГ)

        Возвращает отфильтрованный список записей.
        """
        results = self.records

        # Поиск по ФИО/СНИЛС
        if query.strip():
            q = query.strip().lower()
            results = [
                r for r in results
                if q in r.last_name.lower()
                or q in r.first_name.lower()
                or q in r.middle_name.lower()
                or q in r.snils.replace('-', '').replace(' ', '')
            ]

        # Фильтр по SetId
        if set_id.strip():
            results = [r for r in results if r.set_id == set_id.strip()]

        # Фильтр по статусу
        if status != "all":
            results = [r for r in results if r.status == status]

        # Фильтр по дате
        if date_from:
            try:
                df = datetime.strptime(date_from, "%d.%m.%Y")
                results_filtered = []
                for r in results:
                    try:
                        date_part = r.send_date.split()[0] if ' ' in r.send_date else r.send_date[:10]
                        if datetime.strptime(date_part, "%d.%m.%Y") >= df:
                            results_filtered.append(r)
                    except (ValueError, TypeError, IndexError):
                        logger.warning(f"Ошибка парсинга даты send_date='{r.send_date}'")
                        continue
                results = results_filtered
            except ValueError:
                pass

        if date_to:
            try:
                dt = datetime.strptime(date_to, "%d.%m.%Y")
                results_filtered = []
                for r in results:
                    try:
                        date_part = r.send_date.split()[0] if ' ' in r.send_date else r.send_date[:10]
                        if datetime.strptime(date_part, "%d.%m.%Y") <= dt:
                            results_filtered.append(r)
                    except (ValueError, TypeError, IndexError):
                        logger.warning(f"Ошибка парсинга даты send_date='{r.send_date}'")
                        continue
                results = results_filtered
            except ValueError:
                pass

        return results

    def get_unique_set_ids(self) -> List[str]:
        """Возвращает список уникальных SetId из журнала."""
        return list(dict.fromkeys(r.set_id for r in self.records if r.set_id))

    def get_all_records(self) -> List[JournalRecord]:
        """Возвращает все записи журнала."""
        return self.records

    # ============ Внутренние методы ============

    @staticmethod
    def _get_program_title(program_id: str) -> str:
        """Получение названия программы по номеру."""
        titles = {
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
        return titles.get(program_id, "")
