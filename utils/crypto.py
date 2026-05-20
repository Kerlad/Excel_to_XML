import os
import json
import base64
import hashlib
import logging
from pathlib import Path
from typing import Optional, Tuple, Any, Dict
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)
_MASTER_KEY: Optional[bytes] = None
_FERNET_INSTANCE: Optional[Fernet] = None
_ENCRYPT_CACHE: Dict[str, str] = {}        # PERFORMANCE: cache recent encrypts
_DECRYPT_CACHE: Dict[str, str] = {}        # PERFORMANCE: cache recent decrypts
_MAX_CACHE_ITEMS: int = 2000


def _dpapi_encrypt(data: bytes) -> Optional[bytes]:
    """Шифрует данные через Windows DPAPI (CryptProtectData)."""
    try:
        import win32crypt
        return win32crypt.CryptProtectData(data, None, None, None, None, 0)
    except Exception:
        return None


def _dpapi_decrypt(encrypted: bytes) -> Optional[bytes]:
    """Дешифрует данные через Windows DPAPI (CryptUnprotectData)."""
    try:
        import win32crypt
        _, data = win32crypt.CryptUnprotectData(encrypted, None, None, None, 0)
        return data
    except Exception:
        return None


def _key_dir() -> Path:
    """Возвращает путь к директории с мастер-ключом."""
    return Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming')) / 'Excel_to_XML'


def _restrict_file_access(filepath: Path) -> None:
    """Ограничивает доступ к файлу только текущим пользователем."""
    try:
        import win32security
        import win32api
        import ntsecuritycon as con
        username = win32api.GetUserName()
        sid, _, _ = win32security.LookupAccountName(None, username)
        sd = win32security.SECURITY_DESCRIPTOR()
        dacl = win32security.ACL()
        dacl.AddAccessAllowedAce(
            win32security.ACL_REVISION,
            con.FILE_GENERIC_READ | con.FILE_GENERIC_WRITE,
            sid
        )
        sd.SetSecurityDescriptorDacl(1, dacl, 0)
        win32security.SetFileSecurity(
            str(filepath),
            win32security.DACL_SECURITY_INFORMATION,
            sd
        )
        logger.info("Master key file access restricted to current user")
    except Exception:
        logger.debug("Could not restrict master key file access")


def _get_or_create_master_key() -> bytes:
    """Получает существующий мастер-ключ или создаёт новый.
    Использует DPAPI для защиты ключа. При недоступности DPAPI
    сохраняет ключ в открытом виде (fallback)."""
    global _MASTER_KEY
    if _MASTER_KEY:
        return _MASTER_KEY
    kd = _key_dir()
    kd.mkdir(parents=True, exist_ok=True)
    kf = kd / 'master.key'
    if kf.exists():
        try:
            raw = _dpapi_decrypt(kf.read_bytes())
            if raw and len(raw) == 32:
                _MASTER_KEY = raw
                return raw
        except Exception as e:
            logger.warning(f'Key load failed: {e}')
    raw = os.urandom(32)
    prot = _dpapi_encrypt(raw)
    if prot:
        kf.write_bytes(prot)
        _MASTER_KEY = raw
        logger.info('Master key created')
        return raw
    kf.write_bytes(raw)
    _restrict_file_access(kf)
    logger.warning('DPAPI unavailable, using local fallback key (reduced security)')
    _MASTER_KEY = raw
    return raw


def _fernet() -> Fernet:
    """Возвращает кэшированный экземпляр Fernet. PERFORMANCE: создаётся один раз."""
    global _FERNET_INSTANCE
    if _FERNET_INSTANCE is None:
        _FERNET_INSTANCE = Fernet(base64.urlsafe_b64encode(_get_or_create_master_key()))
    return _FERNET_INSTANCE


def encrypt_value(plain: str) -> str:
    """Шифрует строку через Fernet. PERFORMANCE: кэширует результат."""
    if not plain:
        return ''
    # PERFORMANCE: cache hit
    if plain in _ENCRYPT_CACHE:
        return _ENCRYPT_CACHE[plain]
    f = _fernet()
    result = f.encrypt(plain.encode('utf-8')).decode('utf-8')
    # PERFORMANCE: LRU-like cache with max size
    if len(_ENCRYPT_CACHE) < _MAX_CACHE_ITEMS:
        _ENCRYPT_CACHE[plain] = result
    return result


def decrypt_value(enc: str) -> str:
    """Дешифрует строку. PERFORMANCE: кэширует результат, переиспользует Fernet."""
    if not enc:
        return ''
    # PERFORMANCE: cache hit
    if enc in _DECRYPT_CACHE:
        return _DECRYPT_CACHE[enc]
    try:
        f = _fernet()
        result = f.decrypt(enc.encode('utf-8')).decode('utf-8')
        if len(_DECRYPT_CACHE) < _MAX_CACHE_ITEMS:
            _DECRYPT_CACHE[enc] = result
        return result
    except Exception:
        logger.warning('Decrypt value failed')
        return ''


def hash_for_search(val: str) -> str:
    """SHA256-хеш для поиска по СНИЛС (безопасный поиск без расшифровки)."""
    normalized = val.lower().strip().replace('-', '').replace(' ', '').replace('\xa0', '')
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def encrypt_data(data: Any) -> str:
    """Шифрует произвольный JSON-сериализуемый объект."""
    f = _fernet()
    return f.encrypt(json.dumps(data, ensure_ascii=False).encode('utf-8')).decode('utf-8')


def decrypt_data(enc: str) -> Any:
    """Дешифрует JSON-объект. PERFORMANCE: кэширует результат."""
    if not enc:
        return {}
    if enc in _DECRYPT_CACHE:
        return _DECRYPT_CACHE[enc]
    try:
        f = _fernet()
        result = json.loads(f.decrypt(enc.encode('utf-8')).decode('utf-8'))
        if len(_DECRYPT_CACHE) < _MAX_CACHE_ITEMS:
            _DECRYPT_CACHE[enc] = result
        return result
    except Exception:
        logger.warning('Decrypt data failed')
        return {}


def clear_caches() -> None:
    """Очищает кэши Fernet. Вызывать при смене мастер-ключа."""
    global _FERNET_INSTANCE, _ENCRYPT_CACHE, _DECRYPT_CACHE
    _FERNET_INSTANCE = None
    _ENCRYPT_CACHE.clear()
    _DECRYPT_CACHE.clear()


def check_master_key_security() -> Tuple[str, str]:
    """Проверяет статус безопасности мастер-ключа.
    Returns: (mode, message) где mode: 'dpapi' | 'raw' | 'none'"""
    kd = _key_dir()
    kf = kd / 'master.key'
    if not kf.exists():
        return 'none', 'Мастер-ключ не найден'
    try:
        import win32crypt
        raw = _dpapi_decrypt(kf.read_bytes())
        if raw and len(raw) == 32:
            return 'dpapi', 'Мастер-ключ защищён через Windows DPAPI'
    except Exception:
        pass
    raw = kf.read_bytes()
    if len(raw) == 32:
        return 'raw', 'Мастер-ключ НЕ защищён DPAPI! Хранится в открытом виде в AppData.'
    return 'none', 'Неизвестный формат мастер-ключа'


def create_master_key_backup(backup_dir: Optional[str] = None) -> Tuple[bool, str]:
    """Создаёт ZIP-копию master.key в указанную директорию.
    Returns: (success, path_or_error)"""
    kd = _key_dir()
    kf = kd / 'master.key'
    if not kf.exists():
        return False, 'Мастер-ключ не найден'
    if backup_dir is None:
        backup_dir = str(kd / 'backups')
    backup_path = Path(backup_dir)
    backup_path.mkdir(parents=True, exist_ok=True)
    from datetime import datetime
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_path = backup_path / f'master_key_backup_{ts}.zip'
    try:
        import zipfile
        with zipfile.ZipFile(str(zip_path), 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(str(kf), arcname='master.key')
        logger.info(f'Master key backup created: {zip_path}')
        return True, str(zip_path)
    except Exception as e:
        logger.error(f'Failed to create master key backup: {e}')
        return False, str(e)


def restore_master_key_backup(zip_path: str) -> Tuple[bool, str]:
    """Восстанавливает master.key из ZIP-бэкапа.
    Returns: (success, message)"""
    zpath = Path(zip_path)
    if not zpath.exists():
        return False, 'Файл бэкапа не найден'
    kd = _key_dir()
    kd.mkdir(parents=True, exist_ok=True)
    try:
        import zipfile
        with zipfile.ZipFile(str(zpath), 'r') as zf:
            zf.extract('master.key', str(kd))
        _restrict_file_access(kd / 'master.key')
        global _MASTER_KEY
        _MASTER_KEY = None
        logger.info(f'Master key restored from: {zip_path}')
        return True, 'Мастер-ключ восстановлен'
    except Exception as e:
        return False, str(e)
