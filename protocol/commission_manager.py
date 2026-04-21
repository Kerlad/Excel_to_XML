"""
Менеджер данных комиссии для протокола проверки знаний
Сохранение/загрузка: председатель, члены комиссии, приказ, организация
"""
import os
import json
import logging

from utils.crypto import encrypt_data, decrypt_data

logger = logging.getLogger(__name__)


class CommissionManager:
    """Управление данными комиссии."""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.commission_file = os.path.join(self.data_dir, "commission_data.json")
        self.data = self._load()

    def _load(self) -> dict:
        """Загрузка данных комиссии из файла (с расшифровкой)."""
        if os.path.exists(self.commission_file):
            try:
                with open(self.commission_file, 'r', encoding='utf-8') as f:
                    wrapper = json.load(f)
                encrypted = wrapper.get('data', '')
                if encrypted:
                    return decrypt_data(encrypted)
                else:
                    return wrapper
            except Exception as e:
                logger.error(f"Ошибка загрузки данных комиссии: {e}")
        return self._default_data()

    def _default_data(self) -> dict:
        """Данные по умолчанию."""
        return {
            "org_name": "",
            "order_number": "",
            "order_date": "",
            "exam_date": "",
            "chairman_fio": "",
            "chairman_position": "",
            "member1_fio": "",
            "member1_position": "",
            "member2_fio": "",
            "member2_position": "",
            "member3_fio": "",
            "member3_position": "",
            "union_fio": "",
            "union_position": ""
        }

    def save(self, data: dict) -> tuple[bool, str]:
        """
        Сохранение данных комиссии (с шифрованием).

        data — словарь с полями:
            org_name, order_number, order_date, exam_date,
            chairman_fio, chairman_position,
            member1_fio, member1_position,
            member2_fio, member2_position,
            member3_fio, member3_position,
            union_fio, union_position

        Возвращает (success, message).
        """
        try:
            self.data = data
            encrypted = encrypt_data(data)
            with open(self.commission_file, 'w', encoding='utf-8') as f:
                json.dump({"data": encrypted}, f, ensure_ascii=False, indent=2)
            return True, "Данные комиссии сохранены (зашифрованы)"
        except Exception as e:
            logger.error(f"Ошибка сохранения данных комиссии: {e}")
            return False, f"Ошибка сохранения: {e}"

    def load(self) -> dict:
        """Загрузка данных комиссии."""
        self.data = self._load()
        return self.data

    def get_data(self) -> dict:
        """Получение текущих данных."""
        return self.data.copy()

    def is_complete(self) -> tuple[bool, str]:
        """
        Проверка заполненности обязательных полей.

        Обязательные: org_name, order_number, chairman_fio
        Возвращает (is_complete, missing_fields).
        """
        required = {
            'org_name': 'Название организации',
            'order_number': 'Номер приказа',
            'chairman_fio': 'ФИО председателя'
        }
        missing = []
        for key, label in required.items():
            if not self.data.get(key, '').strip():
                missing.append(label)

        if missing:
            return False, f"Не заполнены: {', '.join(missing)}"
        return True, ""
