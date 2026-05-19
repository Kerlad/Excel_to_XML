import os, json, base64, hashlib, logging
from pathlib import Path
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)
_MASTER_KEY = None

def _dpapi_encrypt(data):
    try:
        import win32crypt
        return win32crypt.CryptProtectData(data, None, None, None, None, 0)
    except Exception:
        return None

def _dpapi_decrypt(encrypted):
    try:
        import win32crypt
        _, data = win32crypt.CryptUnprotectData(encrypted, None, None, None, 0)
        return data
    except Exception:
        return None

def _key_dir():
    return Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming')) / 'Excel_to_XML'

def _get_or_create_master_key():
    global _MASTER_KEY
    if _MASTER_KEY:
        return _MASTER_KEY
    kd = _key_dir(); kd.mkdir(parents=True, exist_ok=True)
    kf = kd / 'master.key'
    if kf.exists():
        try:
            raw = _dpapi_decrypt(kf.read_bytes())
            if raw and len(raw) == 32:
                _MASTER_KEY = raw; return raw
        except Exception as e:
            logger.warning(f'Key load failed: {e}')
    raw = os.urandom(32)
    prot = _dpapi_encrypt(raw)
    if prot:
        kf.write_bytes(prot)
        _MASTER_KEY = raw; logger.info(f'Master key created: {kf}'); return raw
    # DPAPI unavailable — store raw key in AppData (less secure, but random)
    kf.write_bytes(raw)
    logger.warning('DPAPI unavailable, using local fallback key (reduced security)')
    _MASTER_KEY = raw; return raw

def _fernet():
    return Fernet(base64.urlsafe_b64encode(_get_or_create_master_key()))

def encrypt_value(plain):
    return _fernet().encrypt(plain.encode('utf-8')).decode('utf-8') if plain else ''

def decrypt_value(enc):
    if not enc: return ''
    try: return _fernet().decrypt(enc.encode('utf-8')).decode('utf-8')
    except Exception: logger.warning('Decrypt failed'); return ''

def hash_for_search(val):
    normalized = val.lower().strip().replace('-', '').replace(' ', '').replace('\xa0', '')
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

def encrypt_data(data):
    return _fernet().encrypt(json.dumps(data, ensure_ascii=False).encode('utf-8')).decode('utf-8')

def decrypt_data(enc):
    if not enc: return {}
    try:
        return json.loads(_fernet().decrypt(enc.encode('utf-8')).decode('utf-8'))
    except Exception:
        logger.warning('Decrypt failed')
        return {}


