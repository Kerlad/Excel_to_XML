--- core/data_model.py (原始)


+++ core/data_model.py (修改后)
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модель данных для хранения информации о работниках
"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class WorkerRecord:
    """Запись о работнике"""
    last_name: str = ""
    first_name: str = ""
    middle_name: str = ""
    snils: str = ""
    position: str = ""
    employer_inn: str = ""
    employer_title: str = ""
    training_center_inn: str = ""
    training_center_title: str = ""
    result: str = "Удовлетворительно"
    program_numbers: str = ""
    date: str = ""
    protocol_number: str = ""

    def to_dict(self) -> dict:
        return {
            'Фамилия': self.last_name,
            'Имя': self.first_name,
            'Отчество': self.middle_name,
            'СНИЛС': self.snils,
            'Должность': self.position,
            'ИНН Заказчика': self.employer_inn,
            'Наименование ЮЛ Заказчика': self.employer_title,
            'ИНН УЦ': self.training_center_inn,
            'Наименование УЦ': self.training_center_title,
            'Результат': self.result,
            '№ программы': self.program_numbers,
            'Дата': self.date,
            '№ протокола': self.protocol_number
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'WorkerRecord':
        return cls(
            last_name=data.get('Фамилия', ''),
            first_name=data.get('Имя', ''),
            middle_name=data.get('Отчество', ''),
            snils=data.get('СНИЛС', ''),
            position=data.get('Должность', ''),
            employer_inn=data.get('ИНН Заказчика', ''),
            employer_title=data.get('Наименование ЮЛ Заказчика', ''),
            training_center_inn=data.get('ИНН УЦ', ''),
            training_center_title=data.get('Наименование УЦ', ''),
            result=data.get('Результат', 'Удовлетворительно'),
            program_numbers=data.get('№ программы', ''),
            date=data.get('Дата', ''),
            protocol_number=data.get('№ протокола', '')
        )


class DataManager:
    """Управление данными работников"""

    VALID_PROGRAMS = {'1', '2', '3', '4', '6', '7', '8', '9', '10',
                      '11', '12', '13', '14', '15', '16', '17', '18',
                      '19', '20', '21', '22', '23', '24', '25', '26',
                      '27', '28', '29'}

    def __init__(self):
        self.records: List[WorkerRecord] = []
        self.training_center_inn: str = ""
        self.training_center_title: str = ""
        self.employer_inn: str = ""
        self.employer_title: str = ""
        self.xsd_path: Optional[str] = None
        self.api_key: str = ""

    def add_record(self, record: WorkerRecord) -> tuple[bool, str]:
        """Добавление записи с проверкой на дубликаты"""
        # Разбиваем программы на отдельные
        programs = [p.strip() for p in record.program_numbers.replace(',,', ',').rstrip(',').split(',') if p.strip()]

        if not programs:
            return False, "Не указаны программы обучения"

        # Проверка программ
        for prog in programs:
            if prog not in self.VALID_PROGRAMS:
                return False, f"Неверный номер программы: {prog}"

        errors = []
        for prog in programs:
            # Проверка на дубликат
            for existing in self.records:
                if existing.snils == record.snils and prog in existing.program_numbers:
                    errors.append(f"Дубликат: СНИЛС {record.snils}, программа {prog}")
                    break
            else:
                # Создаем новую запись для каждой программы
                new_record = WorkerRecord(
                    last_name=record.last_name,
                    first_name=record.first_name,
                    middle_name=record.middle_name,
                    snils=record.snils,
                    position=record.position,
                    employer_inn=record.employer_inn,
                    employer_title=record.employer_title,
                    training_center_inn=record.training_center_inn,
                    training_center_title=record.training_center_title,
                    result=record.result,
                    program_numbers=prog,
                    date=record.date,
                    protocol_number=record.protocol_number
                )
                self.records.append(new_record)

        if errors:
            return False, "\n".join(errors)

        return True, "Запись добавлена"

    def validate_snils(self, snils: str) -> bool:
        """Валидация СНИЛС - 11 цифр"""
        digits = snils.replace('-', '').replace(' ', '')
        return len(digits) == 11 and digits.isdigit()

    def validate_inn(self, inn: str) -> bool:
        """Валидация ИНН - 10 или 12 цифр"""
        digits = inn.strip()
        return len(digits) in (10, 12) and digits.isdigit()

    def validate_programs(self, programs_str: str) -> tuple[bool, str]:
        """Валидация номеров программ"""
        programs = [p.strip() for p in programs_str.replace(',,', ',').rstrip(',').split(',') if p.strip()]

        if not programs:
            return False, "Не указаны программы"

        if len(programs) > 10:
            return False, "Превышено количество программ для одного работника (максимум 10)"

        invalid = [p for p in programs if p not in self.VALID_PROGRAMS]
        if invalid:
            return False, f"Неверные номера программ: {', '.join(invalid)}"

        return True, "OK"

    def validate_date(self, date_str: str) -> tuple[bool, str]:
        """Валидация даты"""
        if not date_str:
            return False, "Дата не указана"

        # Пробуем разные форматы
        formats = ['%d.%m.%Y', '%d%m%Y']
        for fmt in formats:
            try:
                date_obj = datetime.strptime(date_str, fmt)
                if date_obj.date() > datetime.now().date():
                    return False, "Дата не может быть в будущем"
                return True, "OK"
            except ValueError:
                continue

        return False, "Дата некорректна. Ведите корректную дату в формате ЧЧ.ММ.ГГГГ или ЧЧММГГГГ"

    def clear_all(self):
        """Очистка всех данных"""
        self.records.clear()

    def get_unique_key(self, record: WorkerRecord) -> str:
        """Получение уникального ключа записи (СНИЛС + программа)"""
        return f"{record.snils}_{record.program_numbers}"