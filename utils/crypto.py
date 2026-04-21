"""
Модуль шифрования данных
Используется для шифрования журнала (персональные данные)
Шифрование: AES/Fernet, ключ из имени пользователя системы
Требуется библиотека cryptography (pip install cryptography)
"""
import os
import json
import base64
import hashlib
import logging

logger = logging.getLogger(__name__)

try:
    from cryptography.fernet import Fernet
except ImportError:
    raise ImportError(
        "Библиотека 'cryptography' не установлена. "
        "Установите её: pip install cryptography"
    )


def _get_derive_key():
    """Получение ключа шифрования на основе имени пользователя системы."""
    username = os.environ.get('USERNAME', 'default_user').encode('utf-8')
    return hashlib.sha256(username).digest()


def _fernet():
    """Создание объекта Fernet с ключом из имени пользователя."""
    key = _get_derive_key()
    fernet_key = base64.urlsafe_b64encode(key)
    return Fernet(fernet_key)


def encrypt_data(data: dict) -> str:
    """Шифрование словаря в строку (AES/Fernet)."""
    json_str = json.dumps(data, ensure_ascii=False)
    return _fernet().encrypt(json_str.encode('utf-8')).decode('utf-8')


def decrypt_data(encrypted: str) -> dict:
    """Расшифровка строки в словарь."""
    json_str = _fernet().decrypt(encrypted.encode('utf-8')).decode('utf-8')
    return json.loads(json_str)
