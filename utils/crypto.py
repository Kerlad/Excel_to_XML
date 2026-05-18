import os
import json
import base64
import hashlib
import logging
import shutil

logger = logging.getLogger(__name__)

try:
    from cryptography.fernet import Fernet, InvalidToken
except ImportError:
    raise ImportError(
        "Библиотека 'cryptography' не установлена. "
        "Установите её: pip install cryptography"
    )


def _get_derive_key():
    username = os.environ.get('USERNAME', 'default_user').encode('utf-8')
    return hashlib.sha256(username).digest()


def _fernet():
    key = _get_derive_key()
    fernet_key = base64.urlsafe_b64encode(key)
    return Fernet(fernet_key)


def encrypt_data(data: dict) -> str:
    json_str = json.dumps(data, ensure_ascii=False)
    return _fernet().encrypt(json_str.encode('utf-8')).decode('utf-8')


def decrypt_data(encrypted: str) -> dict:
    json_str = _fernet().decrypt(encrypted.encode('utf-8')).decode('utf-8')
    return json.loads(json_str)


def encrypt_file(file_path: str) -> str:
    enc_path = file_path + '.enc'
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    with open(file_path, 'rb') as f:
        data = f.read()
    encrypted = _fernet().encrypt(data)
    with open(enc_path, 'wb') as f:
        f.write(encrypted)
    os.remove(file_path)
    logger.info(f"File encrypted: {file_path} -> {enc_path}")
    return enc_path


def decrypt_file(enc_path: str, output_path: str):
    if not os.path.exists(enc_path):
        raise FileNotFoundError(f"Encrypted file not found: {enc_path}")
    with open(enc_path, 'rb') as f:
        encrypted = f.read()
    try:
        data = _fernet().decrypt(encrypted)
    except InvalidToken:
        logger.error("Decryption failed: invalid key or corrupted file")
        raise
    with open(output_path, 'wb') as f:
        f.write(data)
    os.remove(enc_path)
    logger.info(f"File decrypted: {enc_path} -> {output_path}")


def backup_file(file_path: str, max_backups: int = 5):
    backup_pattern = file_path + '.backup.{}'
    for i in range(max_backups - 1, 0, -1):
        src = backup_pattern.format(i)
        dst = backup_pattern.format(i + 1)
        if os.path.exists(src):
            shutil.move(src, dst)
    if os.path.exists(file_path):
        shutil.copy2(file_path, backup_pattern.format(1))
        logger.info(f"Backup created: {backup_pattern.format(1)}")
