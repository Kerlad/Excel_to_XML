import os
import uuid
import logging
from datetime import datetime
from typing import List, Optional, Dict

from db.exam_journal_repo import ExamJournalRepo, JournalRecord

logger = logging.getLogger(__name__)


class JournalManager:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir

    def add_records(self, records_data: List[Dict], set_id: str, xml_file: str) -> int:
        send_date = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        records = []
        xml_file_basename = os.path.basename(xml_file) if xml_file else ''
        for rec in records_data:
            program_id = str(rec.get('program', ''))
            record = JournalRecord(
                uuid=str(uuid.uuid4()),
                send_date=send_date,
                set_id=set_id,
                xml_file=xml_file_basename,
                last_name=rec.get('last_name', ''),
                first_name=rec.get('first_name', ''),
                middle_name=rec.get('middle_name', ''),
                snils=rec.get('snils', ''),
                position=rec.get('position', ''),
                program_id=program_id,
                program_title=self._get_program_title(program_id),
                exam_date=rec.get('date', ''),
                protocol=rec.get('protocol', ''),
                result=rec.get('result', ''),
                base_no="",
                status="pending"
            )
            records.append(record)

        ExamJournalRepo.add_records(records)
        return len(records)

    def update_base_no_by_set_id(self, set_id: str, base_no_map: Dict[str, str]) -> int:
        return ExamJournalRepo.update_base_no(set_id, base_no_map)

    def delete_by_uuid(self, uuids: List[str]) -> int:
        return ExamJournalRepo.delete_by_uuid(uuids)

    def search(self, query: str = "", set_id: str = "",
               status: str = "all", date_from: str = "", date_to: str = "") -> List[JournalRecord]:
        return ExamJournalRepo.search(
            query=query, set_id=set_id,
            status=status, date_from=date_from, date_to=date_to
        )

    def get_unique_set_ids(self) -> List[str]:
        return ExamJournalRepo.get_unique_set_ids()

    def get_records_by_protocol(self, protocol_number: str) -> List[JournalRecord]:
        return ExamJournalRepo.get_records_by_protocol(protocol_number)

    def get_all_records(self) -> List[JournalRecord]:
        return ExamJournalRepo.get_all()

    def add_journal_records_directly(self, records: List[JournalRecord]):
        ExamJournalRepo.add_records(records)

    def get_record_count(self) -> int:
        return ExamJournalRepo.count()

    @staticmethod
    def _get_program_title(program_id: str) -> str:
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
