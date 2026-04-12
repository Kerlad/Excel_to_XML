"""
Модуль шифрования данных
Используется для шифрования журнала (персональные данные)
По аналогии с API-ключом — Fernet + ключ из имени пользователя
"""
import os
import json
import base64
import hashlib
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def _get_derive_key():
    """Получение ключа шифрования на основе имени пользователя системы."""
    username = os.environ.get('USERNAME', 'default_user').encode('utf-8')
    return hashlib.sha256(username).digest()


def encrypt_data(data: dict) -> str:
    """
    Шифрование словаря в строку (AES/Fernet).
    Если cryptography нет — fallback на XOR.
    """
    try:
        from cryptography.fernet import Fernet

        key = _get_derive_key()
        fernet_key = base64.urlsafe_b64encode(key)
        fernet = Fernet(fernet_key)

        json_str = json.dumps(data, ensure_ascii=False)
        return fernet.encrypt(json_str.encode('utf-8')).decode('utf-8')
    except ImportError:
        return _encrypt_xor(data)
    except Exception as e:
        logger.error(f"Ошибка шифрования: {e}")
        return _encrypt_xor(data)


def decrypt_data(encrypted: str) -> dict:
    """
    Расшифровка строки в словарь.
    """
    try:
        from cryptography.fernet import Fernet

        key = _get_derive_key()
        fernet_key = base64.urlsafe_b64encode(key)
        fernet = Fernet(fernet_key)

        json_str = fernet.decrypt(encrypted.encode('utf-8')).decode('utf-8')
        return json.loads(json_str)
    except ImportError:
        return _decrypt_xor(encrypted)
    except Exception as e:
        logger.error(f"Ошибка расшифровки: {e}")
        return _decrypt_xor(encrypted)


def _encrypt_xor(data: dict) -> str:
    """XOR-шифрование (fallback)."""
    key = hashlib.sha256(os.environ.get('USERNAME', 'default_user').encode()).digest()
    json_str = json.dumps(data, ensure_ascii=False)
    key_bytes = json_str.encode('utf-8')
    encrypted = bytes([key_bytes[i] ^ key[i % len(key)] for i in range(len(key_bytes))])
    return base64.b64encode(encrypted).decode('utf-8')


def _decrypt_xor(encrypted: str) -> dict:
    """XOR-расшифровка (fallback)."""
    key = hashlib.sha256(os.environ.get('USERNAME', 'default_user').encode()).digest()
    encrypted_bytes = base64.b64decode(encrypted)
    decrypted = bytes([encrypted_bytes[i] ^ key[i % len(key)] for i in range(len(encrypted_bytes))])
    return json.loads(decrypted.decode('utf-8'))
