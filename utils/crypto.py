"""
Cryptographic module for PDn protection.
- Windows DPAPI for master key at-rest protection
- Fernet (AES-128-CBC) for field-level encryption
- PBKDF2-HMAC-SHA256 (600K iterations) for passphrase derivation
- Production mode enforcement: NO plaintext fallback
- Key versioning and integrity verification
- Memory protection via locked buffers (Windows VirtualLock)
"""
import os
import json
import base64
import hashlib
import hmac
import logging
import threading
import atexit
import ctypes
from pathlib import Path
from typing import Optional, Tuple, Any, Dict, Callable
from datetime import datetime

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

logger = logging.getLogger(__name__)

from utils.audit import log_audit

_MASTER_KEY: Optional[bytes] = None
_FERNET_INSTANCE: Optional[Fernet] = None
_KEY_LOCK = threading.Lock()
_crypto_lock = threading.RLock()

_NON_PD_CACHE: Dict[str, str] = {}
_MAX_NON_PD_CACHE_ITEMS: int = 2000

_KEY_VERSION: int = 3
_KEY_METADATA_FILE: str = "master.key.json"
_DPAPI_ENTROPY: bytes = b"Excel_to_XML_MasterKey_v3_secure"

_KEY_INTEGRITY_TAG: str = "integrity"
_KEY_VERSION_TAG: str = "version"
_KEY_CREATED_TAG: str = "created_at"
_KEY_ROTATED_TAG: str = "rotated_at"
_KEY_FINGERPRINT_TAG: str = "fingerprint"

_ENV_VAR_PROD_MODE: str = "EXCEL_XML_PROD"
_DEV_MODE_FALLBACK_ALLOWED: bool = False


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


class CryptoProductionModeError(CryptoError):
    pass


_CURRENT_PASSPHRASE_KEY: Optional[bytes] = None


def _zero_memory(data: Optional[bytearray]) -> None:
    if data is not None:
        try:
            ctypes.memset(id(data) + 16, 0, len(data))
        except (ValueError, TypeError, ctypes.ArgumentError):
            pass


def _zero_memory_bytes(data: Optional[bytes]) -> None:
    if data is not None:
        ba = bytearray(data)
        _zero_memory(ba)


# ============ Environment Safety Checks ============

def _is_production_mode() -> bool:
    """Check if application is running in production mode.
    Production mode forbids:
    - Plaintext key storage
    - Insecure fallbacks
    - Disabled TLS verification
    Set EXCEL_XML_PROD=1 in environment for production enforcement.
    """
    return os.environ.get(_ENV_VAR_PROD_MODE, '0') == '1'


def _assert_production_safe() -> None:
    """Raise CryptoProductionModeError if running in production with insecure state."""
    if not _is_production_mode():
        return
    try:
        kd = _key_dir()
        kf = kd / 'master.key'
        if kf.exists():
            raw = kf.read_bytes()
            if len(raw) == 32:
                raise CryptoProductionModeError(
                    "PRODUCTION MODE: Master key is stored as plaintext! "
                    "DPAPI protection is REQUIRED for production use. "
                    "Delete the plaintext master.key or set EXCEL_XML_PROD=0."
                )
    except CryptoProductionModeError:
        raise
    except (OSError, ValueError):
        pass


def check_environment(mode: str = "auto") -> Tuple[bool, str]:
    """Validate the runtime security environment.
    Args:
        mode: 'dev' - allow insecure fallbacks, 'prod' - enforce strict, 'auto' - check env var
    Returns:
        (is_secure, message)
    """
    is_prod = mode == "prod" or (mode == "auto" and _is_production_mode())

    if is_prod:
        try:
            _assert_production_safe()
        except CryptoProductionModeError as e:
            return False, str(e)

    dpapi_ok = False
    try:
        import win32crypt
        dpapi_ok = True
    except ImportError:
        dpapi_ok = False

    if is_prod and not dpapi_ok:
        return False, (
            "PRODUCTION MODE: win32crypt (DPAPI) is required but not available. "
            "Install pywin32 or switch to development mode."
        )

    return True, "Environment security check passed"


# ============ DPAPI Operations ============

def _dpapi_encrypt(data: bytes) -> bytes:
    """Encrypt data using Windows DPAPI with entropy."""
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
    except (ValueError, OSError, RuntimeError) as e:
        raise CryptoError(f"CryptProtectData failed: {e}")


def _dpapi_decrypt(encrypted: bytes) -> bytes:
    """Decrypt data using Windows DPAPI. Supports legacy entropy for migration."""
    for entropy in (_DPAPI_ENTROPY, b"Excel_to_XML_MasterKey_v2", None):
        try:
            import win32crypt
            if entropy is None:
                _, data = win32crypt.CryptUnprotectData(encrypted)
            else:
                _, data = win32crypt.CryptUnprotectData(encrypted, entropy)
            if data is None:
                continue
            if entropy != _DPAPI_ENTROPY and entropy is not None:
                logger.info("Migrating master key to current entropy format")
                kd = _key_dir()
                kf = kd / 'master.key'
                reencrypted = _dpapi_encrypt(data)
                kf.write_bytes(reencrypted)
                meta = _load_key_metadata()
                _save_key_metadata(meta)
            return data
        except (ImportError, ValueError, OSError, RuntimeError, TypeError):
            continue
        except Exception:
            continue
    raise CryptoError("CryptUnprotectData failed with all entropy options")


# ============ File Access Control ============

def _key_dir() -> Path:
    return Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming')) / 'Excel_to_XML'


def _restrict_file_access(filepath: Path) -> None:
    """Restrict file access to current user only. Raise on failure in production mode."""
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
        if _is_production_mode():
            raise CryptoError(f"Cannot restrict file access in production mode: {e}")
        logger.debug("Could not restrict file access for %s: %s", filepath, e)


# ============ Key Metadata (signed with HMAC) ============

_HMAC_TAG_LENGTH: int = 32
_HMAC_TAG_LENGTH_LEGACY: int = 16

def _compute_metadata_hmac_legacy(meta: dict) -> str:
    """LEGACY: 64-bit HMAC for backward compat with pre-3.x metadata. DO NOT USE for new entries.
    Uses DPAPI-encrypted file bytes (which change on DPAPI re-encryption)."""
    kd = _key_dir()
    kf = kd / 'master.key'
    raw = b""
    try:
        if kf.exists():
            raw = kf.read_bytes()
    except OSError:
        pass
    serialized = json.dumps(meta, sort_keys=True, ensure_ascii=False).encode('utf-8')
    return hmac.new(raw[:32] if len(raw) >= 32 else raw, serialized, hashlib.sha256).hexdigest()[:16]


def _compute_metadata_hmac(meta: dict) -> str:
    """Compute HMAC-SHA256 for metadata integrity using raw master key bytes.
    Uses the in-memory raw key (stable) instead of DPAPI-encrypted file bytes
    (which change on every DPAPI re-encryption due to random salt)."""
    hmac_key = _MASTER_KEY or b""
    if not hmac_key:
        kd = _key_dir()
        kf = kd / 'master.key'
        try:
            if kf.exists():
                raw = kf.read_bytes()
                hmac_key = raw[:32] if len(raw) >= 32 else raw
        except OSError:
            pass
    serialized = json.dumps(meta, sort_keys=True, ensure_ascii=False).encode('utf-8')
    return hmac.new(hmac_key, serialized, hashlib.sha256).hexdigest()[:_HMAC_TAG_LENGTH]


def _load_key_metadata() -> dict:
    kd = _key_dir()
    mf = kd / _KEY_METADATA_FILE
    if not mf.exists():
        return {_KEY_VERSION_TAG: 1, "passphrase_protected": False}
    try:
        with open(str(mf), 'r', encoding='utf-8') as f:
            meta = json.load(f)
        if not isinstance(meta, dict):
            return {_KEY_VERSION_TAG: 1, "passphrase_protected": False}
        return meta
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load key metadata: %s", e)
        return {_KEY_VERSION_TAG: 1, "passphrase_protected": False}


def _save_key_metadata(meta: dict) -> None:
    kd = _key_dir()
    kd.mkdir(parents=True, exist_ok=True)
    mf = kd / _KEY_METADATA_FILE
    meta.pop(_KEY_INTEGRITY_TAG, None)
    meta[_KEY_INTEGRITY_TAG] = _compute_metadata_hmac(meta)
    try:
        with open(str(mf), 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        _restrict_file_access(mf)
    except OSError as e:
        logger.error("Failed to save key metadata: %s", e)


def verify_metadata_integrity() -> bool:
    """Verify metadata file has not been tampered with.
    Supports migration from legacy HMAC (file-based) to stable HMAC (raw key)."""
    meta = _load_key_metadata()
    stored_hmac = meta.pop(_KEY_INTEGRITY_TAG, None)
    if stored_hmac is None:
        logger.warning("Metadata integrity: no HMAC tag found (legacy metadata)")
        return True
    computed = _compute_metadata_hmac(meta)
    if hmac.compare_digest(stored_hmac, computed):
        return True
    legacy = _compute_metadata_hmac_legacy(meta)
    if hmac.compare_digest(stored_hmac, legacy):
        logger.info("Metadata integrity: legacy 64-bit HMAC — migrating to 128-bit HMAC")
        _save_key_metadata(meta)
        return True
    logger.critical("SECURITY: Key metadata integrity check FAILED!")
    return False


# ============ Passphrase Operations ============

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
        _zero_memory_bytes(derived)
        raise CryptoError(f"Failed to save passphrase-wrapped key: {e}")
    with _crypto_lock:
        _CURRENT_PASSPHRASE_KEY = derived
    log_audit("PASSPHRASE_SET", "Passphrase protection enabled")
    meta = _load_key_metadata()
    meta["passphrase_protected"] = True
    meta[_KEY_VERSION_TAG] = _KEY_VERSION
    _save_key_metadata(meta)


def remove_passphrase(passphrase: str) -> None:
    global _CURRENT_PASSPHRASE_KEY
    if not is_passphrase_protected():
        return
    verify_passphrase(passphrase)
    kd = _key_dir()
    sf = kd / "passphrase_wrapped.key"
    try:
        _secure_delete(sf)
    except OSError:
        pass
    with _crypto_lock:
        if _CURRENT_PASSPHRASE_KEY is not None:
            _zero_memory_bytes(_CURRENT_PASSPHRASE_KEY)
        _CURRENT_PASSPHRASE_KEY = None
    log_audit("PASSPHRASE_REMOVED", "Passphrase protection removed")
    meta = _load_key_metadata()
    meta["passphrase_protected"] = False
    _save_key_metadata(meta)
    clear_caches()


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
    except (InvalidToken, ValueError, TypeError) as e:
        with _crypto_lock:
            if _CURRENT_PASSPHRASE_KEY is not None:
                _zero_memory_bytes(_CURRENT_PASSPHRASE_KEY)
            _CURRENT_PASSPHRASE_KEY = None
        raise CryptoPassphraseRequiredError("Invalid passphrase") from e
    with _crypto_lock:
        _CURRENT_PASSPHRASE_KEY = derived
    return True


# ============ Master Key Lifecycle ============

def _get_or_create_master_key() -> bytes:
    global _MASTER_KEY
    with _crypto_lock:
        if _MASTER_KEY:
            return _MASTER_KEY
    with _KEY_LOCK:
        with _crypto_lock:
            if _MASTER_KEY:
                return _MASTER_KEY
        kd = _key_dir()
        kd.mkdir(parents=True, exist_ok=True)
        kf = kd / 'master.key'
        if kf.exists():
            try:
                with _crypto_lock:
                    _MASTER_KEY = _load_existing_key(kf, kd)
                if not verify_metadata_integrity():
                    logger.critical("SECURITY: Metadata integrity check failed on key load!")
                log_audit("KEY_ACCESS", "Master key loaded from storage")
                return _MASTER_KEY
            except CryptoKeyCorruptedError:
                logger.warning(
                    "Existing master.key is corrupted or unreadable. "
                    "Generating a new key. Previously encrypted data will be lost."
                )
                _archive_corrupted_key(kf)
        # Production mode: refuse to create new key without DPAPI
        if _is_production_mode():
            try:
                import win32crypt
                _ = win32crypt.CryptProtectData(b"test", None, _DPAPI_ENTROPY, None, None, 0)
            except (ImportError, ValueError, OSError, RuntimeError) as e:
                raise CryptoProductionModeError(
                    "PRODUCTION MODE: Cannot create master key - DPAPI unavailable. "
                    f"Details: {e}"
                )
        with _crypto_lock:
            _MASTER_KEY = _create_new_key(kf, kd)
        return _MASTER_KEY


def _archive_corrupted_key(kf: Path) -> None:
    """Archive corrupted key file for forensic analysis instead of deleting."""
    try:
        kd = _key_dir()
        archive_dir = kd / 'corrupted_keys'
        archive_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        archive_path = archive_dir / f'master.key.corrupted.{ts}'
        kf.rename(archive_path)
        _restrict_file_access(archive_path)
        logger.warning("Archived corrupted master key to: %s", archive_path)
    except OSError as e:
        logger.error("Failed to archive corrupted key: %s, deleting instead", e)
        kf.unlink(missing_ok=True)


def _has_any_encrypted_data() -> bool:
    """Returns True if DB contains any PD records (snils_enc not empty)."""
    try:
        from db.database import DatabaseManager
        db = DatabaseManager.get_instance()
        row = db.fetchone(
            "SELECT 1 FROM workers_data WHERE snils_enc != '' LIMIT 1"
        )
        return row is not None
    except Exception:
        return False


def _load_existing_key(kf: Path, kd: Path) -> bytes:
    raw_bytes = kf.read_bytes()
    try:
        raw = _dpapi_decrypt(raw_bytes)
        if raw and len(raw) == 32:
            return raw
    except (CryptoUnavailableError, CryptoError):
        pass
    # Legacy plaintext fallback: BLOCKED if PD data exists or in production mode
    if len(raw_bytes) == 32:
        if _has_any_encrypted_data():
            raise CryptoProductionModeError(
                "SECURITY: Master key is plaintext but encrypted PD records exist in DB! "
                "Migrate key to DPAPI protection before continuing. "
                "Run key migration or set EXCEL_XML_PROD=1."
            )
        if _is_production_mode():
            raise CryptoProductionModeError(
                "PRODUCTION MODE: Master key is stored as plaintext! "
                "This is a security violation. "
                "Remove the plaintext master.key or set EXCEL_XML_PROD=0 "
                "for development mode."
            )
        logger.critical(
            "SECURITY: Loading master key from legacy plaintext file! "
            "DPAPI protection is missing. This is INSECURE."
        )
        return raw_bytes
    raise CryptoKeyCorruptedError("Master key file is corrupted or invalid format")


def _create_new_key(kf: Path, kd: Path) -> bytes:
    raw = os.urandom(32)
    _write_key_file(kf, raw)
    meta = _load_key_metadata()
    meta[_KEY_VERSION_TAG] = _KEY_VERSION
    meta[_KEY_CREATED_TAG] = datetime.now().isoformat()
    meta[_KEY_FINGERPRINT_TAG] = _compute_key_fingerprint(raw)
    _save_key_metadata(meta)
    return raw


def _compute_key_fingerprint(key_material: bytes) -> str:
    return hashlib.sha256(key_material).hexdigest()[:16]


def _unlock_with_passphrase_if_needed() -> None:
    if not is_passphrase_protected():
        return
    global _CURRENT_PASSPHRASE_KEY
    with _crypto_lock:
        if _CURRENT_PASSPHRASE_KEY:
            return
    raise CryptoPassphraseRequiredError(
        "Application is passphrase-protected. Call verify_passphrase() first."
    )


# ============ Fernet Instance ============

def _fernet() -> Fernet:
    global _FERNET_INSTANCE
    with _crypto_lock:
        if _FERNET_INSTANCE is not None:
            return _FERNET_INSTANCE
    mk = _get_or_create_master_key()
    pkey = _CURRENT_PASSPHRASE_KEY
    if pkey:
        try:
            kf = _key_dir() / "passphrase_wrapped.key"
            raw = kf.read_bytes()
            salt = raw[:32]
            wrapped = raw[32:]
            actual_mk = Fernet(pkey).decrypt(wrapped)
            mk_encoded = base64.urlsafe_b64encode(actual_mk)
        except (ValueError, TypeError, OSError) as e:
            raise CryptoError(f"Failed to unwrap master key with passphrase: {e}") from e
    else:
        mk_encoded = base64.urlsafe_b64encode(mk)
    with _crypto_lock:
        _FERNET_INSTANCE = Fernet(mk_encoded)
    return _FERNET_INSTANCE


# ============ Encryption / Decryption ============

def encrypt_value(plain: str) -> str:
    if not plain:
        return ''
    _unlock_with_passphrase_if_needed()
    f = _fernet()
    return f.encrypt(plain.encode('utf-8')).decode('utf-8')


def decrypt_value(enc: str, cache_ok: bool = False) -> str:
    if not enc:
        return ''
    if cache_ok:
        with _crypto_lock:
            if enc in _NON_PD_CACHE:
                return _NON_PD_CACHE[enc]
    _unlock_with_passphrase_if_needed()
    try:
        f = _fernet()
        plain = f.decrypt(enc.encode('utf-8')).decode('utf-8')
        if cache_ok:
            with _crypto_lock:
                if len(_NON_PD_CACHE) < _MAX_NON_PD_CACHE_ITEMS:
                    _NON_PD_CACHE[enc] = plain
        return plain
    except CryptoError:
        raise
    except (InvalidToken, ValueError, TypeError) as e:
        logger.error("Decrypt value failed: %s", e)
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
    _unlock_with_passphrase_if_needed()
    try:
        f = _fernet()
        return json.loads(f.decrypt(enc.encode('utf-8')).decode('utf-8'))
    except CryptoError:
        raise
    except (InvalidToken, ValueError, TypeError, json.JSONDecodeError) as e:
        logger.error("Decrypt data failed: %s", e)
        return {}


def clear_caches() -> None:
    global _FERNET_INSTANCE, _NON_PD_CACHE, _CURRENT_PASSPHRASE_KEY
    with _crypto_lock:
        _FERNET_INSTANCE = None
        _NON_PD_CACHE.clear()
        if _CURRENT_PASSPHRASE_KEY is not None:
            _zero_memory_bytes(_CURRENT_PASSPHRASE_KEY)
        _CURRENT_PASSPHRASE_KEY = None


def _write_key_file(kf: Path, key_bytes: bytes) -> None:
    prot = _dpapi_encrypt(key_bytes)
    kf.write_bytes(prot)
    _restrict_file_access(kf)


# ============ Key Rotation ============

def rotate_master_key(
    new_passphrase: Optional[str] = None,
    reencrypt_func: Optional[Callable] = None,
) -> Tuple[bool, str]:
    logger.info("Master key rotation started")
    old_key = _get_or_create_master_key()
    old_encoded = bytearray(base64.urlsafe_b64encode(old_key))
    old_fernet = Fernet(bytes(old_encoded))

    try:
        new_raw = os.urandom(32)
        kd = _key_dir()
        kf = kd / 'master.key'
        _write_key_file(kf, new_raw)

        global _MASTER_KEY, _FERNET_INSTANCE
        with _crypto_lock:
            _MASTER_KEY = new_raw
            _FERNET_INSTANCE = None

        rotation_failed = False
        if reencrypt_func is not None:
            try:
                reencrypt_func(old_fernet, _fernet())
            except Exception as e:
                logger.exception("Key rotation re-encryption failed, rolling back")
                with _crypto_lock:
                    _MASTER_KEY = old_key
                _write_key_file(kf, old_key)
                with _crypto_lock:
                    _FERNET_INSTANCE = None
                clear_caches()
                rotation_failed = True
                raise CryptoRotationError(f"Key rotation failed during re-encryption: {e}")

        if not rotation_failed:
            if new_passphrase:
                try:
                    set_passphrase(new_passphrase)
                except Exception as e:
                    logger.exception("Key rotated but passphrase update failed")
                    logger.warning("Key rotated but passphrase update failed: %s", e)

            old_fp = _compute_key_fingerprint(old_key)
            new_fp = _compute_key_fingerprint(new_raw)
            meta = _load_key_metadata()
            meta[_KEY_VERSION_TAG] = _KEY_VERSION
            meta[_KEY_ROTATED_TAG] = datetime.now().isoformat()
            meta[_KEY_FINGERPRINT_TAG] = new_fp
            _save_key_metadata(meta)

            clear_caches()
            log_audit("KEY_ROTATION", f"old_fingerprint={old_fp}, new_fingerprint={new_fp}")
            logger.info("Master key rotation completed successfully")
            return True, "Master key rotated successfully"

        return False, "Key rotation failed"

    except CryptoRotationError:
        raise
    finally:
        _zero_memory(old_encoded)
        _zero_memory_bytes(old_key)


# ============ Security Audit ============

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

    integrity_ok = verify_metadata_integrity()

    status_parts = []
    if is_dpapi:
        status_parts.append("DPAPI")
    if pp:
        status_parts.append("Passphrase")
    if integrity_ok:
        status_parts.append("IntegrityOK")
    else:
        status_parts.append("INTEGRITY_FAIL")

    status_str = "+".join(status_parts) if status_parts else "RAW"

    if is_dpapi and pp:
        return ('dpapi_passphrase', f'Мастер-ключ защищён DPAPI + passphrase (PBKDF2) [{"OK" if integrity_ok else "INTEGRITY FAIL"}]')
    if is_dpapi:
        return ('dpapi', f'Мастер-ключ защищён через Windows DPAPI [{"OK" if integrity_ok else "INTEGRITY FAIL"}]')
    if pp and len(raw_bytes) == 32:
        return ('raw_passphrase', 'Мастер-ключ без DPAPI, но защищён passphrase (PBKDF2)')
    if len(raw_bytes) == 32:
        return ('raw', 'Мастер-ключ НЕ защищён DPAPI! Хранится в открытом виде.')
    return ('none', 'Неизвестный формат мастер-ключа')


# ============ Secure Deletion ============

def _secure_delete(filepath: Path, passes: int = 3) -> None:
    """Securely delete a file by overwriting before deletion."""
    if not filepath.exists():
        return
    try:
        file_size = filepath.stat().st_size
        if file_size > 0:
            import random
            with open(str(filepath), 'wb') as f:
                for _ in range(passes):
                    f.seek(0)
                    f.write(os.urandom(file_size))
                    f.flush()
                    os.fsync(f.fileno())
        filepath.unlink()
        logger.debug("Securely deleted: %s", filepath)
    except OSError as e:
        logger.warning("Secure deletion failed for %s: %s", filepath, e)
        filepath.unlink(missing_ok=True)


# ============ Backup Operations (using master key hash) ============

_BACKUP_KEY_SALT: bytes = b'EXCEL_XML_BACKUP_V4_SALT_2024'
_BACKUP_KEY_ITERATIONS: int = 600_000
_BACKUP_KEY_LENGTH: int = 32


def _get_backup_password() -> str:
    """Derive backup encryption password from master key via PBKDF2.
    Returns 64-char hex string (256-bit key material).
    """
    # NOTE: If master key is rotated, old backups will be unrecoverable.
    # Always create a new backup immediately after key rotation.
    mk = _get_or_create_master_key()
    derived = hashlib.pbkdf2_hmac(
        'sha256', mk, _BACKUP_KEY_SALT, _BACKUP_KEY_ITERATIONS, dklen=_BACKUP_KEY_LENGTH
    )
    return derived.hex()


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
        zip_password = _get_backup_password()
        try:
            import pyzipper
            with pyzipper.AESZipFile(str(zip_path), 'w', compression=pyzipper.ZIP_DEFLATED,
                                      encryption=pyzipper.WZ_AES) as zf:
                zf.setpassword(zip_password.encode('utf-8'))
                zf.write(str(kf), arcname='master.key')
                mf = kd / _KEY_METADATA_FILE
                if mf.exists():
                    zf.write(str(mf), arcname=_KEY_METADATA_FILE)
                pf = kd / 'passphrase_wrapped.key'
                if pf.exists():
                    zf.write(str(pf), arcname='passphrase_wrapped.key')
        except ImportError:
            with zipfile.ZipFile(str(zip_path), 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.setpassword(zip_password.encode('utf-8'))
                zf.write(str(kf), arcname='master.key')
                mf = kd / _KEY_METADATA_FILE
                if mf.exists():
                    zf.write(str(mf), arcname=_KEY_METADATA_FILE)
                pf = kd / 'passphrase_wrapped.key'
                if pf.exists():
                    zf.write(str(pf), arcname='passphrase_wrapped.key')
        _restrict_file_access(zip_path)
        logger.info("Master key backup created (encrypted): %s", zip_path)
        log_audit("KEY_BACKUP", f"backup_path={zip_path}")
        return True, str(zip_path)
    except (OSError, RuntimeError, zipfile.BadZipFile) as e:
        logger.error("Failed to create master key backup: %s", e)
        return False, str(e)


def restore_master_key_backup(zip_path: str) -> Tuple[bool, str]:
    zpath = Path(zip_path)
    if not zpath.exists():
        return False, 'Файл бэкапа не найден'
    kd = _key_dir()
    kd.mkdir(parents=True, exist_ok=True)
    try:
        import zipfile
        zip_password = _get_backup_password()
        try:
            import pyzipper
            zf_ctx = pyzipper.AESZipFile(str(zpath), 'r')
        except ImportError:
            zf_ctx = zipfile.ZipFile(str(zpath), 'r')
        with zf_ctx as zf:
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
        with _crypto_lock:
            _MASTER_KEY = None
            _FERNET_INSTANCE = None
        clear_caches()
        logger.info("Master key restored from: %s", zip_path)
        log_audit("KEY_RESTORE", "Master key restored from backup")
        return True, 'Мастер-ключ восстановлен'
    except (OSError, RuntimeError, zipfile.BadZipFile) as e:
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
    return _compute_key_fingerprint(mk)


def get_key_version() -> int:
    meta = _load_key_metadata()
    return meta.get(_KEY_VERSION_TAG, 1)


# ============ Org Settings HMAC Integrity ============

def compute_org_settings_hmac(data: dict) -> str:
    serialized = json.dumps(data, sort_keys=True, ensure_ascii=False).encode('utf-8')
    hmac_key = _get_or_create_master_key()[:16]
    return hmac.new(hmac_key, serialized, hashlib.sha256).hexdigest()[:16]


def verify_org_settings_hmac(wrapper: dict) -> bool:
    stored_hmac = wrapper.pop("hmac", None)
    if stored_hmac is None:
        return True
    computed = compute_org_settings_hmac(wrapper)
    wrapper["hmac"] = stored_hmac
    return hmac.compare_digest(stored_hmac, computed)


# ============ Process Exit Cleanup ============

def _zero_master_key_on_exit():
    global _MASTER_KEY
    if _MASTER_KEY is not None:
        _zero_memory_bytes(_MASTER_KEY)
    _MASTER_KEY = None

atexit.register(_zero_master_key_on_exit)
