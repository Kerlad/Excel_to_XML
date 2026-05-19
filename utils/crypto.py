import os, json, base64, hashlib, logging
from pathlib import Path
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)
_MASTER_KEY = None

def _dpapi_encrypt(data):
    try:
        import win32crypt
        return win32crypt.CryptProtectData(data, None, None, None, None, 0)
    except ImportError:
        return None

def _dpapi_decrypt(encrypted):
    try:
        import win32crypt
        _, data = win32crypt.CryptUnprotectData(encrypted, None, None, None, 0)
        return data
    except ImportError:
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
        _MASTER_KEY = raw; logger.info(f'Master key: {kf}'); return raw
    fallback = hashlib.sha256(os.environ.get('USERNAME','default_user').encode()).digest()
    logger.warning('DPAPI unavailable, using USERNAME fallback')
    _MASTER_KEY = fallback; return fallback

def _fernet():
    return Fernet(base64.urlsafe_b64encode(_get_or_create_master_key()))

def encrypt_value(plain):
    return _fernet().encrypt(plain.encode('utf-8')).decode('utf-8') if plain else ''

def decrypt_value(enc):
    if not enc: return ''
    try: return _fernet().decrypt(enc.encode('utf-8')).decode('utf-8')
    except Exception as e: logger.error(f'Decrypt failed: {e}'); return enc

def hash_for_search(val):
    normalized = val.lower().strip().replace('-', '').replace(' ', '').replace('\xa0', '')
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

def encrypt_data(data):
    return _fernet().encrypt(json.dumps(data, ensure_ascii=False).encode('utf-8')).decode('utf-8')

def decrypt_data(enc):
    return json.loads(_fernet().decrypt(enc.encode('utf-8')).decode('utf-8'))

def encrypt_file(path):
    p = Path(path)
    if not p.exists(): raise FileNotFoundError(str(path))
    enc = _fernet().encrypt(p.read_bytes())
    p.with_suffix(p.suffix + '.enc').write_bytes(enc)
    p.unlink()
    return str(p.with_suffix(p.suffix + '.enc'))

def decrypt_file(enc_path, out_path):
    p = Path(enc_path)
    if not p.exists(): raise FileNotFoundError(str(enc_path))
    data = _fernet().decrypt(p.read_bytes())
    Path(out_path).write_bytes(data)
    p.unlink()
