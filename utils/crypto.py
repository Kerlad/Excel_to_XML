import os
import json
import base64
import hashlib
import hmac
import logging
import threading
from pathlib import Path
from typing import Optional, Tuple, Any, Dict
from datetime import datetime

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

logger = logging.getLogger(__name__)

_MASTER_KEY: Optional[bytes] = None
_FERNET_INSTANCE: Optional[Fernet] = None
_KEY_LOCK = threading.Lock()

_ENCRYPT_CACHE: Dict[str, str] = {}
_DECRYPT_CACHE: Dict[str, str] = {}
_MAX_CACHE_ITEMS: int = 2000

_KEY_VERSION: int = 2
_KEY_METADATA_FILE: str = "master.key.json"
_DPAPI_ENTROPY: bytes = b"Excel_to_XML_MasterKey_v2"


class CryptoError(RuntimeError):
    pass


class CryptoUnavailableError(CryptoError):
    pass


class CryptoPassphraseRequiredError(CryptoError):
    pass


class CryptoKeyCorruptedError(CryptoError):
    pass


class CryptoRotationError(CryptoError):
    pass


_CURRENT_PASSPHRASE_KEY: Optional[bytes] = None


def _dpapi_encrypt(data: bytes) -> bytes:
    try:
        import win32crypt
        result = win32crypt.CryptProtectData(
            data, None, _DPAPI_ENTROPY, None, None, 0
        )
        if result is None:
            raise CryptoError("CryptProtectData returned None")
        return result
    except ImportError:
        raise CryptoUnavailableError("win32crypt not installed")
    except Exception as e:
        raise CryptoError(f"CryptProtectData failed: {e}")


def _dpapi_decrypt(encrypted: bytes) -> bytes:
    for entropy in (_DPAPI_ENTROPY, None):
        try:
            import win32crypt
            if entropy is None:
                _, data = win32crypt.CryptUnprotectData(encrypted)
            else:
                _, data = win32crypt.CryptUnprotectData(encrypted, entropy)
            if data is None:
                continue
            if entropy is None:
                logger.info("Migrating master key to new entropy-protected format")
                kd = _key_dir()
                kf = kd / 'master.key'
                reencrypted = _dpapi_encrypt(data)
                kf.write_bytes(reencrypted)
            return data
        except (ImportError, ValueError, OSError, RuntimeError, TypeError):
            continue
    raise CryptoError("CryptUnprotectData failed with all entropy options")


def _key_dir() -> Path:
    return Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming')) / 'Excel_to_XML'


def _restrict_file_access(filepath: Path) -> None:
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
    except (ImportError, OSError) as e:
        logger.debug(f"Could not restrict file access for {filepath}: {e}")


def _load_key_metadata() -> dict:
    kd = _key_dir()
    mf = kd / _KEY_METADATA_FILE
    if not mf.exists():
        return {"version": 1, "passphrase_protected": False}
    try:
        with open(str(mf), 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to load key metadata: {e}")
        return {"version": 1, "passphrase_protected": False}


def _save_key_metadata(meta: dict) -> None:
    kd = _key_dir()
    kd.mkdir(parents=True, exist_ok=True)
    mf = kd / _KEY_METADATA_FILE
    try:
        with open(str(mf), 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        _restrict_file_access(mf)
    except OSError as e:
        logger.error(f"Failed to save key metadata: {e}")


def _derive_key_from_passphrase(passphrase: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600000,
    )
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode('utf-8')))


def is_passphrase_protected() -> bool:
    meta = _load_key_metadata()
    return meta.get("passphrase_protected", False)


def set_passphrase(passphrase: str) -> None:
    global _CURRENT_PASSPHRASE_KEY
    kd = _key_dir()
    kd.mkdir(parents=True, exist_ok=True)
    salt = os.urandom(32)
    derived = _derive_key_from_passphrase(passphrase, salt)
    mk = _get_or_create_master_key()
    wrapped = Fernet(derived).encrypt(mk)
    sf = kd / "passphrase_wrapped.key"
    try:
        sf.write_bytes(salt + wrapped)
        _restrict_file_access(sf)
    except OSError as e:
        raise CryptoError(f"Failed to save passphrase-wrapped key: {e}")
    _CURRENT_PASSPHRASE_KEY = derived
    meta = _load_key_metadata()
    meta["passphrase_protected"] = True
    meta["version"] = _KEY_VERSION
    _save_key_metadata(meta)
    logger.info("Passphrase protection enabled")


def remove_passphrase(passphrase: str) -> None:
    global _CURRENT_PASSPHRASE_KEY
    if not is_passphrase_protected():
        return
    verify_passphrase(passphrase)
    kd = _key_dir()
    sf = kd / "passphrase_wrapped.key"
    try:
        sf.unlink()
    except OSError:
        pass
    _CURRENT_PASSPHRASE_KEY = None
    meta = _load_key_metadata()
    meta["passphrase_protected"] = False
    _save_key_metadata(meta)
    clear_caches()
    logger.info("Passphrase protection removed")


def verify_passphrase(passphrase: str) -> bool:
    global _CURRENT_PASSPHRASE_KEY
    kd = _key_dir()
    sf = kd / "passphrase_wrapped.key"
    if not sf.exists():
        raise CryptoPassphraseRequiredError("Passphrase is not set")
    try:
        raw = sf.read_bytes()
    except OSError as e:
        raise CryptoError(f"Failed to read passphrase key file: {e}")
    if len(raw) < 33:
        raise CryptoKeyCorruptedError("Passphrase key file too short")
    salt = raw[:32]
    wrapped = raw[32:]
    derived = _derive_key_from_passphrase(passphrase, salt)
    try:
        Fernet(derived).decrypt(wrapped)
    except (ValueError, TypeError) as e:
        _CURRENT_PASSPHRASE_KEY = None
        raise CryptoPassphraseRequiredError("Invalid passphrase") from e
    _CURRENT_PASSPHRASE_KEY = derived
    return True


def _get_or_create_master_key() -> bytes:
    global _MASTER_KEY
    if _MASTER_KEY:
        return _MASTER_KEY
    with _KEY_LOCK:
        if _MASTER_KEY:
            return _MASTER_KEY
        kd = _key_dir()
        kd.mkdir(parents=True, exist_ok=True)
        kf = kd / 'master.key'
        if kf.exists():
            try:
                _MASTER_KEY = _load_existing_key(kf, kd)
                return _MASTER_KEY
            except CryptoKeyCorruptedError:
                logger.warning(
                    "Existing master.key is corrupted or unreadable. "
                    "Generating a new key. Previously encrypted data will be lost."
                )
                kf.unlink(missing_ok=True)
        _MASTER_KEY = _create_new_key(kf, kd)
        return _MASTER_KEY


def _load_existing_key(kf: Path, kd: Path) -> bytes:
    raw_bytes = kf.read_bytes()
    try:
        raw = _dpapi_decrypt(raw_bytes)
        if raw and len(raw) == 32:
            return raw
    except (CryptoUnavailableError, CryptoError):
        pass
    if len(raw_bytes) == 32:
        logger.warning("Loading master key in plaintext (DPAPI unavailable)")
        return raw_bytes
    raise CryptoKeyCorruptedError("Master key file is corrupted or invalid format")


def _create_new_key(kf: Path, kd: Path) -> bytes:
    raw = os.urandom(32)
    dpapi_ok = _write_key_file(kf, raw)
    meta = _load_key_metadata()
    meta["version"] = _KEY_VERSION
    _save_key_metadata(meta)
    if dpapi_ok:
        logger.info('Master key created with DPAPI protection')
    else:
        logger.warning(
            'DPAPI unavailable — master key saved as plaintext. '
            'Set a passphrase for additional protection.'
        )
    return raw


def _unlock_with_passphrase_if_needed() -> None:
    if not is_passphrase_protected():
        return
    global _CURRENT_PASSPHRASE_KEY
    if _CURRENT_PASSPHRASE_KEY:
        return
    raise CryptoPassphraseRequiredError(
        "Application is passphrase-protected. Call verify_passphrase() first."
    )


def _fernet() -> Fernet:
    global _FERNET_INSTANCE
    if _FERNET_INSTANCE is None:
        mk = _get_or_create_master_key()
        pkey = _CURRENT_PASSPHRASE_KEY
        if pkey:
            try:
                kf = Path(str(_key_dir()) / "passphrase_wrapped.key")
                raw = kf.read_bytes()
                salt = raw[:32]
                wrapped = raw[32:]
                actual_mk = Fernet(pkey).decrypt(wrapped)
                mk_encoded = base64.urlsafe_b64encode(actual_mk)
            except (ValueError, TypeError, OSError) as e:
                raise CryptoError(f"Failed to unwrap master key with passphrase: {e}") from e
        else:
            mk_encoded = base64.urlsafe_b64encode(mk)
        _FERNET_INSTANCE = Fernet(mk_encoded)
    return _FERNET_INSTANCE


def encrypt_value(plain: str) -> str:
    if not plain:
        return ''
    if plain in _ENCRYPT_CACHE:
        return _ENCRYPT_CACHE[plain]
    _unlock_with_passphrase_if_needed()
    f = _fernet()
    result = f.encrypt(plain.encode('utf-8')).decode('utf-8')
    if len(_ENCRYPT_CACHE) < _MAX_CACHE_ITEMS:
        _ENCRYPT_CACHE[plain] = result
    return result


def decrypt_value(enc: str) -> str:
    if not enc:
        return ''
    if enc in _DECRYPT_CACHE:
        return _DECRYPT_CACHE[enc]
    _unlock_with_passphrase_if_needed()
    try:
        f = _fernet()
        result = f.decrypt(enc.encode('utf-8')).decode('utf-8')
        if len(_DECRYPT_CACHE) < _MAX_CACHE_ITEMS:
            _DECRYPT_CACHE[enc] = result
        return result
    except CryptoError:
        raise
    except Exception as e:
        logger.error(f'Decrypt value failed: {e}')
        return ''


def hash_for_search(val: str) -> str:
    normalized = val.lower().strip().replace('-', '').replace(' ', '').replace('\xa0', '')
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def encrypt_data(data: Any) -> str:
    _unlock_with_passphrase_if_needed()
    f = _fernet()
    return f.encrypt(json.dumps(data, ensure_ascii=False).encode('utf-8')).decode('utf-8')


def decrypt_data(enc: str) -> Any:
    if not enc:
        return {}
    if enc in _DECRYPT_CACHE:
        return _DECRYPT_CACHE[enc]
    _unlock_with_passphrase_if_needed()
    try:
        f = _fernet()
        result = json.loads(f.decrypt(enc.encode('utf-8')).decode('utf-8'))
        if len(_DECRYPT_CACHE) < _MAX_CACHE_ITEMS:
            _DECRYPT_CACHE[enc] = result
        return result
    except CryptoError:
        raise
    except Exception as e:
        logger.error(f'Decrypt data failed: {e}')
        return {}


def clear_caches() -> None:
    global _FERNET_INSTANCE, _ENCRYPT_CACHE, _DECRYPT_CACHE
    _FERNET_INSTANCE = None
    _ENCRYPT_CACHE.clear()
    _DECRYPT_CACHE.clear()


def _write_key_file(kf: Path, key_bytes: bytes) -> bool:
    try:
        prot = _dpapi_encrypt(key_bytes)
        kf.write_bytes(prot)
        _restrict_file_access(kf)
        return True
    except CryptoUnavailableError:
        kf.write_bytes(key_bytes)
        _restrict_file_access(kf)
        logger.warning("DPAPI unavailable—writing key as plaintext")
        return False


def rotate_master_key(
    new_passphrase: Optional[str] = None,
    reencrypt_func: Optional[callable] = None,
) -> Tuple[bool, str]:
    logger.info("Master key rotation started")
    old_key = _get_or_create_master_key()
    old_encoded = base64.urlsafe_b64encode(old_key)
    old_fernet = Fernet(old_encoded)

    new_raw = os.urandom(32)
    kd = _key_dir()
    kf = kd / 'master.key'
    _write_key_file(kf, new_raw)

    global _MASTER_KEY, _FERNET_INSTANCE
    _MASTER_KEY = new_raw
    _FERNET_INSTANCE = None

    if reencrypt_func is not None:
        try:
            reencrypt_func(old_fernet, _fernet())
        except Exception as e:
            _MASTER_KEY = old_key
            _write_key_file(kf, old_key)
            _FERNET_INSTANCE = None
            clear_caches()
            raise CryptoRotationError(f"Key rotation failed during re-encryption: {e}")

    if new_passphrase:
        try:
            set_passphrase(new_passphrase)
        except Exception as e:
            logger.warning(f"Key rotated but passphrase update failed: {e}")

    meta = _load_key_metadata()
    meta["version"] = _KEY_VERSION
    meta["rotated_at"] = datetime.now().isoformat()
    _save_key_metadata(meta)

    clear_caches()
    logger.info("Master key rotation completed successfully")
    return True, "Master key rotated successfully"


def check_master_key_security() -> Tuple[str, str]:
    kd = _key_dir()
    kf = kd / 'master.key'
    if not kf.exists():
        return 'none', 'Мастер-ключ не найден'
    raw_bytes = kf.read_bytes()
    is_dpapi = False
    try:
        _dpapi_decrypt(raw_bytes)
        is_dpapi = True
    except (CryptoUnavailableError, CryptoError):
        pass
    meta = _load_key_metadata()
    pp = meta.get("passphrase_protected", False)
    if is_dpapi and pp:
        return 'dpapi_passphrase', 'Мастер-ключ защищён DPAPI + passphrase (PBKDF2)'
    if is_dpapi:
        return 'dpapi', 'Мастер-ключ защищён через Windows DPAPI'
    if pp and len(raw_bytes) == 32:
        return 'raw_passphrase', 'Мастер-ключ без DPAPI, но защищён passphrase (PBKDF2)'
    if len(raw_bytes) == 32:
        return 'raw', 'Мастер-ключ НЕ защищён DPAPI! Хранится в открытом виде.'
    return 'none', 'Неизвестный формат мастер-ключа'


_BACKUP_PASSWORD_SECRET = b"Excel_to_XML_backup_v2_constant"


def _backup_zip_password() -> str:
    return hashlib.sha256(_BACKUP_PASSWORD_SECRET).hexdigest()[:16]


def create_master_key_backup(backup_dir: Optional[str] = None) -> Tuple[bool, str]:
    kd = _key_dir()
    kf = kd / 'master.key'
    if not kf.exists():
        return False, 'Мастер-ключ не найден'
    if backup_dir is None:
        backup_dir = str(kd / 'backups')
    backup_path = Path(backup_dir)
    backup_path.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_path = backup_path / f'master_key_backup_{ts}.zip'
    try:
        import zipfile
        zip_password = _backup_zip_password()
        with zipfile.ZipFile(str(zip_path), 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.setpassword(zip_password.encode('utf-8'))
            zf.write(str(kf), arcname='master.key')
            mf = kd / _KEY_METADATA_FILE
            if mf.exists():
                zf.write(str(mf), arcname=_KEY_METADATA_FILE)
            pf = kd / 'passphrase_wrapped.key'
            if pf.exists():
                zf.write(str(pf), arcname='passphrase_wrapped.key')
        logger.info(f'Master key backup created (encrypted): {zip_path}')
        return True, str(zip_path)
    except (zipfile.BadZipFile, OSError) as e:
        logger.error(f'Failed to create master key backup: {e}')
        return False, str(e)


def restore_master_key_backup(zip_path: str) -> Tuple[bool, str]:
    zpath = Path(zip_path)
    if not zpath.exists():
        return False, 'Файл бэкапа не найден'
    kd = _key_dir()
    kd.mkdir(parents=True, exist_ok=True)
    try:
        import zipfile
        zip_password = _backup_zip_password()
        with zipfile.ZipFile(str(zpath), 'r') as zf:
            zf.setpassword(zip_password.encode('utf-8'))
            zf.extract('master.key', str(kd))
            if 'passphrase_wrapped.key' in zf.namelist():
                zf.extract('passphrase_wrapped.key', str(kd))
            if _KEY_METADATA_FILE in zf.namelist():
                zf.extract(_KEY_METADATA_FILE, str(kd))
        for fname in ['master.key', 'passphrase_wrapped.key', _KEY_METADATA_FILE]:
            fp = kd / fname
            if fp.exists():
                _restrict_file_access(fp)
        global _MASTER_KEY, _FERNET_INSTANCE
        _MASTER_KEY = None
        _FERNET_INSTANCE = None
        clear_caches()
        logger.info(f'Master key restored from: {zip_path}')
        return True, 'Мастер-ключ восстановлен'
    except (zipfile.BadZipFile, OSError, RuntimeError) as e:
        return False, str(e)


def verify_backup_integrity(zip_path: str) -> Tuple[bool, str]:
    zpath = Path(zip_path)
    if not zpath.exists():
        return False, 'Файл не найден'
    try:
        import zipfile
        with zipfile.ZipFile(str(zpath), 'r') as zf:
            names = zf.namelist()
            if 'master.key' not in names:
                return False, 'Бэкап не содержит master.key'
            if zf.getinfo('master.key').file_size == 0:
                return False, 'master.key в бэкапе пуст'
        return True, 'Бэкап корректен'
    except (zipfile.BadZipFile, OSError) as e:
        return False, f'Бэкап повреждён: {e}'


def get_key_fingerprint() -> str:
    mk = _get_or_create_master_key()
    return hashlib.sha256(mk).hexdigest()[:16]


def get_key_version() -> int:
    meta = _load_key_metadata()
    return meta.get("version", 1)
