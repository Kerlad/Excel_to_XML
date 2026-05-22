"""
Unified Mintrud API client.
Main entry point for all API operations.
"""
import os
import json
import re
import time
import logging
from typing import Dict, Any, Optional

# Import payload builder
from xml.sax.saxutils import escape
from .payload_builder import build_multipart_payload, HEADERS

# Import response parser
from .response_parser import parse_send_response, parse_setid_response, parse_snils_response

# Import backends
from .backends import BackendRegistry

# Import proxy manager
import utils.proxy_manager as proxy_manager
from utils.audit import log_audit
from utils.logger import mask_sensitive, filter_sensitive_text

logger = logging.getLogger(__name__)

_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "log")


def _save_error_response(response_bytes: bytes, status_code: int = 0):
    """Сохраняет полный ответ сервера в /log/error_response.txt (UTF-8 BOM).
    Данные фильтруются через SensitiveDataFilter для маскировки PII (СНИЛС, ФИО, ключи)."""
    try:
        os.makedirs(_LOG_DIR, exist_ok=True)
        path = os.path.join(_LOG_DIR, "error_response.txt")
        text = f"HTTP {status_code}\n"
        for enc in ("utf-8", "cp1251"):
            try:
                text += response_bytes.decode(enc)
                break
            except (UnicodeDecodeError, LookupError):
                continue
        else:
            text += str(response_bytes)
        text = filter_sensitive_text(text)
        with open(path, "w", encoding="utf-8-sig") as f:
            f.write(text)
        logger.info("Error response saved")
        log_audit("ERROR_RESPONSE_SAVED", f"status_code={status_code}, size={len(text)}")
    except OSError as e:
        logger.warning(f"Failed to save error response: {e}")


# API endpoints
API_URL = "https://edu.rosmintrud.ru/api/set/push"
GET_URL = "https://edu.rosmintrud.ru/api/GetEducatedPersonXML"

# Default backend order for auto selection
DEFAULT_BACKEND_ORDER = ["requests", "wininet"]

# SSL/TLS error markers for automatic fallback detection
SSL_ERROR_MARKERS = [
    "ssl", "tls", "handshake", "schannel", "sec_e",
    "certificate verify failed", "certificate_verify_failed",
    "ssl_error", "sslerror", "ssl alert",
    "illegal_message", "unable to get local issuer certificate",
]


def _is_ssl_error(error_message: str) -> bool:
    """Check if error indicates SSL/TLS problem (for fallback logic)."""
    if not error_message:
        return False
    msg = error_message.lower()
    return any(marker in msg for marker in SSL_ERROR_MARKERS)


# ============ API Key Management ============

def save_api_key(api_key: str, data_dir: str) -> tuple[bool, str]:
    """Save encrypted API key using DPAPI-backed encryption."""
    try:
        from utils.crypto import encrypt_value
        os.makedirs(data_dir, exist_ok=True)
        key_file = os.path.join(data_dir, "api_key.json")
        encrypted = encrypt_value(api_key)
        with open(key_file, 'w', encoding='utf-8') as f:
            json.dump({"key": encrypted}, f)
        return True, "API ключ сохранён"
    except (OSError, json.JSONDecodeError) as e:
        return False, f"Ошибка сохранения: {e}"


def load_api_key(data_dir: str) -> Optional[str]:
    """Load decrypted API key using DPAPI-backed decryption."""
    key_file = os.path.join(data_dir, "api_key.json")
    if not os.path.exists(key_file):
        return None
    try:
        from utils.crypto import decrypt_value, CryptoPassphraseRequiredError
        with open(key_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        encrypted = data.get('key', '')
        return decrypt_value(encrypted)
    except CryptoPassphraseRequiredError:
        logger.info("API key not loaded - passphrase required")
        return None
    except (OSError, json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to load API key: {e}")
        return None


def validate_api_key(api_key: str) -> tuple[bool, str]:
    """Validate API key format."""
    if not api_key:
        return False, "API ключ не введён"
    if len(api_key) != 32:
        return False, f"Длина ключа: {len(api_key)} (требуется 32 символа)"
    log_audit("LOGIN", "API key validated successfully")
    return True, ""


def validate_api_key_remote(api_key: str, proxy_settings: dict = None) -> tuple[bool, str]:
    """Проверяет API-ключ через тестовый запрос к серверу Минтруда.
    Отправляет GetEducatedPersonXML с PageSize=1 для проверки валидности ключа."""
    try:
        url = f"{GET_URL}?PageSize=1"
        from xml.sax.saxutils import escape
        xml_content = f'''<?xml version="1.0" encoding="utf-8"?>
<EducatedPersonFilter>
    <ApiKey>{escape(api_key)}</ApiKey>
    <PageNo>1</PageNo>
    <PageSize>1</PageSize>
</EducatedPersonFilter>'''
        files = {'file': ('request.xml', xml_content.encode('utf-8'), 'text/xml')}
        try:
            import requests as req
            proxies = None
            verify = True
            if proxy_settings:
                mode = proxy_settings.get('mode', 'off')
                if mode == 'auto':
                    import utils.proxy_manager as pm
                    proxy_url = pm.detect_windows_proxy()
                    if proxy_url:
                        proxies = {'http': proxy_url, 'https': proxy_url}
                elif mode == 'manual':
                    url_str = proxy_settings.get('url', '').strip()
                    if url_str:
                        proxies = {'http': url_str, 'https': url_str}
                verify = proxy_settings.get('tls_verify', True)
            if not verify:
                log_audit("TLS_WARNING", "TLS verification disabled in remote key validation")
            resp = req.post(url, files=files, proxies=proxies, verify=verify, timeout=15)
            if resp.status_code == 200:
                from defusedxml.ElementTree import fromstring as _fromstring
                root = _fromstring(resp.content)
                if root.tag in ('Response', 'EducatedPersons'):
                    return True, 'Ключ действителен'
                elif root.tag == 'Error':
                    msg_elem = root.find('Message')
                    msg = msg_elem.text if msg_elem is not None else 'Ошибка сервера'
                    return False, f'Ключ недействителен: {msg}'
                return True, 'Ключ действителен'
            elif resp.status_code == 401:
                return False, 'Ключ недействителен (HTTP 401)'
            else:
                return False, f'Ошибка сервера (HTTP {resp.status_code})'
        except ImportError:
            return False, 'Библиотека requests не установлена'
        except req.RequestException as e:
            logger.error("Remote validation connection error: %s", e)
            return False, f'Ошибка подключения: {e}'
    except (ValueError, KeyError) as e:
        logger.error("Remote validation config error: %s", e)
        return False, f'Ошибка конфигурации: {e}'
    except req.RequestException as e:
        # Requests errors that may occur outside the inner try (e.g. proxy detection)
        logger.error("Remote validation request error: %s", e)
        return False, f'Ошибка подключения: {e}'
    except (ValueError, KeyError) as e:
        logger.error("Remote validation config error: %s", e)
        return False, f'Ошибка конфигурации: {e}'
    except requests.RequestException as e:
        # Requests errors that may occur outside the inner try (e.g. proxy detection)
        logger.error("Remote validation request error: %s", e)
        return False, f'Ошибка подключения: {e}'
    except Exception as e:
        # Safety net for any unexpected errors (import, proxy detection, XML parse, etc.)
        logger.exception("Remote validation unexpected error")
        return False, f'Внутренняя ошибка: {e}'


# ============ Unified Transport Client ============

class MintrudClient:
    """
    Unified client for Mintrud API operations.
    Supports multiple transport backends with automatic fallback.
    """
    
    def __init__(self, backend: str = "auto", proxy_settings: Optional[Dict] = None):
        """
        Initialize client.
        
        Args:
            backend: Transport backend ("auto", "requests", "wininet")
            proxy_settings: Proxy configuration dict
        """
        self.proxy_settings = proxy_settings or {}
        # Read backend from proxy_settings if not explicitly set
        if backend == "auto" and "backend" in self.proxy_settings:
            backend = self.proxy_settings["backend"]
        self.backend_name = backend
        self._backend = None
        self._init_backend()
    
    def _init_backend(self):
        """Initialize transport backend."""
        import utils.proxy_manager as pm
        
        if self.backend_name == "auto":
            self._backend = self._create_auto_backend()
        else:
            backend_class = BackendRegistry.get_backend(self.backend_name)
            if backend_class:
                self._backend = backend_class()
            else:
                logger.warning(f"Backend {self.backend_name} not found, using auto")
                self._backend = self._create_auto_backend()
    
    def _create_auto_backend(self):
        """Create first available backend in fallback order."""
        for backend_name in DEFAULT_BACKEND_ORDER:
            backend_class = BackendRegistry.get_backend(backend_name)
            if backend_class:
                try:
                    instance = backend_class()
                    if instance.is_available():
                        logger.info(f"Using backend: {backend_name}")
                        return instance
                except (ImportError, RuntimeError) as e:
                    logger.warning(f"Backend {backend_name} not available: {e}")
        
        logger.error("No backends available")
        raise RuntimeError("Не удалось создать ни один HTTP-транспорт. "
                           "Убедитесь, что установлены зависимости (requests).")
    
    def _get_backend_fallback_list(self):
        """
        Get ordered list of (backend_instance, name) tuples for fallback.
        The first entry is the initially selected backend or auto-selected one.
        Subsequent entries are other available backends for SSL fallback.
        """
        backends = []
        seen = set()
        
        # 1. Current backend first
        if self._backend:
            name = getattr(self._backend, 'name', 'unknown')
            backends.append((self._backend, name))
            seen.add(name)
        
        # 2. Other available backends for fallback
        for backend_name in DEFAULT_BACKEND_ORDER:
            if backend_name in seen:
                continue
            backend_class = BackendRegistry.get_backend(backend_name)
            if backend_class:
                try:
                    instance = backend_class()
                    if instance.is_available():
                        backends.append((instance, backend_name))
                        seen.add(backend_name)
                except (ImportError, RuntimeError):
                    continue
        
        return backends
    
    def _get_proxies(self) -> Optional[Dict[str, str]]:
        """Get proxy configuration from settings."""
        mode = self.proxy_settings.get("mode", "off")
        
        if mode == "off":
            return None
        
        proxies = {}
        
        if mode == "auto":
            proxy_url = proxy_manager.detect_windows_proxy()
            if proxy_url:
                proxies['http'] = proxy_url
                proxies['https'] = proxy_url
        elif mode == "manual":
            proxy_url = self.proxy_settings.get("url", "").strip()
            if proxy_url:
                proxies['http'] = proxy_url
                proxies['https'] = proxy_url
        
        return proxies if proxies else None
    
    def _get_verify(self) -> bool:
        """Get SSL verification setting. Default is True (secure)."""
        verify = self.proxy_settings.get("tls_verify", True)
        if not verify:
            logger.warning(
                "SECURITY: TLS verification is DISABLED - connection is insecure. "
                "PDn data is at risk of interception."
            )
            from utils.audit import log_audit
            log_audit("TLS_WARNING", "TLS verification disabled by user")
            # TODO: Organizational measure - require explicit written authorization to disable TLS
        return bool(verify)
    
    # ============ API Methods ============
    
    def send_xml(self, api_key: str, xml_file_path: str) -> Dict[str, Any]:
        """
        Send XML file to server.
        
        Args:
            api_key: API key
            xml_file_path: Path to XML data file
        
        Returns:
            Dict with success, set_id, send_educated_person, message, error
        """
        ok, err = validate_api_key(api_key)
        if not ok:
            return {"success": False, "error": err}
        
        if not os.path.exists(xml_file_path):
            return {"success": False, "error": "Файл XML не найден"}
        
        # Build payload
        files, headers = build_multipart_payload(api_key, xml_file_path)
        proxies = self._get_proxies()
        verify = self._get_verify()
        
        logger.info("Sending XML to API server")
        logger.info("Initial backend: %s", self.backend_name)
        
        # Try backends with SSL fallback
        backends_to_try = self._get_backend_fallback_list()
        last_error = ""
        
        for backend_instance, backend_name in backends_to_try:
            try:
                logger.info("Trying backend: %s", backend_name)
                success, status_code, response_bytes, error_msg = backend_instance.send(
                    url=API_URL,
                    files=files,
                    headers=headers,
                    timeout=60,
                    verify=verify,
                    proxies=proxies
                )
                
                if success:
                    result = parse_send_response(response_bytes, status_code)
                    set_id = result.get("set_id", "")
                    log_audit("SEND_XML", f"set_id={set_id}")
                    return result
                
                last_error = error_msg
                logger.warning("Backend %s failed: %s", backend_name, mask_sensitive(error_msg))
                if response_bytes:
                    _save_error_response(response_bytes, status_code)

                if not _is_ssl_error(error_msg):
                    return {"success": False, "error": error_msg}
                    
                logger.info(f"SSL error detected, trying next backend...")
                
            except requests.RequestException as e:
                last_error = str(e)
                logger.warning("Backend %s request exception: %s", backend_name, mask_sensitive(str(e)))
                if not _is_ssl_error(str(e)):
                    return {"success": False, "error": str(e)}
            except RuntimeError as e:
                last_error = str(e)
                logger.error(f"Backend {backend_name} runtime error: {e}")
                if not _is_ssl_error(str(e)):
                    return {"success": False, "error": str(e)}
        
        return {"success": False, "error": last_error or "All backends failed"}
    
    def send_xml_signed(self, api_key: str, xml_file_path: str, sig_file_path: str) -> Dict[str, Any]:
        """
        Send XML file with electronic signature (.sig) to server for РОЛ.
        
        Args:
            api_key: API key
            xml_file_path: Path to XML data file
            sig_file_path: Path to .sig signature file
        
        Returns:
            Dict with success, set_id, send_educated_person, message, error
        """
        ok, err = validate_api_key(api_key)
        if not ok:
            return {"success": False, "error": err}
        
        if not os.path.exists(xml_file_path):
            return {"success": False, "error": "Файл XML не найден"}
        
        if not sig_file_path or not os.path.exists(sig_file_path):
            return {"success": False, "error": "Файл подписи .sig не найден"}
        
        files, headers = build_multipart_payload(api_key, xml_file_path, need_send=True, sig_file_path=sig_file_path)
        proxies = self._get_proxies()
        verify = self._get_verify()
        
        logger.info("Sending signed XML to API server")
        logger.info("Initial backend: %s", self.backend_name)
        
        backends_to_try = self._get_backend_fallback_list()
        last_error = ""
        
        for backend_instance, backend_name in backends_to_try:
            try:
                logger.info("Trying backend: %s", backend_name)
                success, status_code, response_bytes, error_msg = backend_instance.send(
                    url=API_URL,
                    files=files,
                    headers=headers,
                    timeout=60,
                    verify=verify,
                    proxies=proxies
                )
                
                if success:
                    result = parse_send_response(response_bytes, status_code)
                    set_id = result.get("set_id", "")
                    log_audit("SEND_XML_SIGNED", f"set_id={set_id}")
                    return result
                
                last_error = error_msg
                logger.warning("Backend %s failed: %s", backend_name, mask_sensitive(error_msg))
                if response_bytes:
                    _save_error_response(response_bytes, status_code)

                if not _is_ssl_error(error_msg):
                    return {"success": False, "error": error_msg}
                    
                logger.info(f"SSL error detected, trying next backend...")
                
            except requests.RequestException as e:
                last_error = str(e)
                logger.warning("Backend %s request exception: %s", backend_name, mask_sensitive(str(e)))
                if not _is_ssl_error(str(e)):
                    return {"success": False, "error": str(e)}
            except RuntimeError as e:
                last_error = str(e)
                logger.error(f"Backend {backend_name} runtime error: {e}")
                if not _is_ssl_error(str(e)):
                    return {"success": False, "error": str(e)}
        
        return {"success": False, "error": last_error or "All backends failed"}
    
    def _try_backends(self, api_key: str, xml_content: str, url: str) -> Dict[str, Any]:
        """Try sending request through backends with SSL fallback."""
        files = {'file': ('request.xml', xml_content.encode('utf-8'), 'text/xml')}
        proxies = self._get_proxies()
        verify = self._get_verify()
        
        backends_to_try = self._get_backend_fallback_list()
        last_error = ""
        response_bytes = b""
        status_code = 0
        
        for backend_instance, backend_name in backends_to_try:
            try:
                from urllib.parse import urlparse
                _parsed = urlparse(url)
                logger.info("Trying backend %s for %s://%s%s", backend_name, _parsed.scheme, _parsed.netloc, _parsed.path)
                success, status_code, response_bytes, error_msg = backend_instance.send(
                    url=url,
                    files=files,
                    headers=HEADERS,
                    timeout=60,
                    verify=verify,
                    proxies=proxies
                )
                
                if success:
                    return {"success": True, "status_code": status_code, "response_bytes": response_bytes}
                
                last_error = error_msg
                logger.warning("Backend %s failed: %s", backend_name, mask_sensitive(error_msg))
                if response_bytes:
                    _save_error_response(response_bytes, status_code)

                if not _is_ssl_error(error_msg):
                    return {"success": False, "error": error_msg}

                logger.info(f"SSL error, trying next backend...")
                log_audit("TLS_ERROR", f"SSL connection failed: {str(error_msg)[:100]}")

            except requests.RequestException as e:
                last_error = str(e)
                logger.warning("Backend %s request exception: %s", backend_name, mask_sensitive(str(e)))
                if _is_ssl_error(str(e)):
                    log_audit("TLS_ERROR", f"SSL connection failed: {str(e)[:100]}")
                if not _is_ssl_error(str(e)):
                    return {"success": False, "error": str(e)}
            except RuntimeError as e:
                last_error = str(e)
                logger.error(f"Backend {backend_name} runtime error: {e}")
                if not _is_ssl_error(str(e)):
                    return {"success": False, "error": str(e)}

        if response_bytes:
            _save_error_response(response_bytes, status_code)
        return {"success": False, "error": last_error or "All backends failed"}

    def query_by_setid(self, api_key: str, set_id: str, page_size: int = 5000) -> Dict[str, Any]:
        """
        Query records by SetId.
        
        Args:
            api_key: API key
            set_id: Set ID to query
            page_size: Page size for pagination
        
        Returns:
            Dict with success, records, error
        """
        ok, err = validate_api_key(api_key)
        if not ok:
            return {"success": False, "records": [], "error": err}
        
        if not set_id:
            return {"success": False, "records": [], "error": "SetId не введён"}
        
        all_records = []
        page_no = 1
        
        while True:
            xml_content = f'''<?xml version="1.0" encoding="utf-8"?>
<EducatedPersonFilter>
    <ApiKey>{escape(api_key)}</ApiKey>
    <PageNo>{page_no}</PageNo>
    <PageSize>{page_size}</PageSize>
    <SetId>{escape(set_id)}</SetId>
</EducatedPersonFilter>'''
            
            logger.info("Querying SetId page %d", page_no)

            try_result = self._try_backends(api_key, xml_content, GET_URL)

            if not try_result.get("success"):
                logger.error("Query failed: %s", try_result.get("error", "Unknown error")[:200])
                return {"success": False, "records": [], "error": try_result.get("error", "Unknown error")}
            
            response_bytes = try_result["response_bytes"]
            status_code = try_result["status_code"]
            
            parse_result = parse_setid_response(response_bytes, status_code)

            if not parse_result.get("success"):
                return {"success": False, "records": [], "error": parse_result.get("error", "Unknown error")}

            records = parse_result.get("records", [])
            all_records.extend(records)

            if len(records) < page_size:
                break

            page_no += 1
            time.sleep(0.5)

        log_audit("QUERY_SETID", f"set_id={set_id}, records={len(all_records)}")
        return {"success": True, "records": all_records, "error": None}

    def query_by_snils(self, api_key: str, snils: str, page_size: int = 100) -> Dict[str, Any]:
        """
        Запрос данных по СНИЛС через API.

        Args:
            api_key: API-ключ
            snils: СНИЛС в формате 'xxx-xxx-xxx xx'
            page_size: количество записей на странице

        Returns:
            Dict с ключами: success, records, error
        """
        # Нормализация СНИЛС: удаляем все нецифровые символы
        snils_clean = re.sub(r"\D", "", snils)
        if not re.fullmatch(r"\d{11}", snils_clean):
            logger.error(f"Invalid SNILS format: {mask_sensitive(snils)}")
            return {"success": False, "records": [], "error": "Неверный формат СНИЛС (требуется 11 цифр)"}

        # Сервер ожидает СНИЛС в формате XXX-XXX-XXX XX
        snils_formatted = f"{snils_clean[0:3]}-{snils_clean[3:6]}-{snils_clean[6:9]} {snils_clean[9:11]}"

        all_records = []
        for page_no in range(1, 1000):
            xml_content = f'''<?xml version="1.0" encoding="utf-8"?>
<EducatedPersonFilter>
    <ApiKey>{escape(api_key)}</ApiKey>
    <PageNo>{page_no}</PageNo>
    <PageSize>{page_size}</PageSize>
    <Snils>{escape(snils_formatted)}</Snils>
</EducatedPersonFilter>'''

            logger.info("Querying by SNILS, page %d", page_no)

            try_result = self._try_backends(api_key, xml_content, GET_URL)

            if not try_result.get("success"):
                logger.error("Query failed: %s", str(try_result.get("error", "Unknown error"))[:200])
                return {"success": False, "records": [], "error": try_result.get("error", "Unknown error")}

            response_bytes = try_result["response_bytes"]
            status_code = try_result["status_code"]

            parse_result = parse_snils_response(response_bytes, status_code)

            if not parse_result.get("success"):
                return {"success": False, "records": [], "error": parse_result.get("error", "Unknown error")}
            
            records = parse_result.get("records", [])
            all_records.extend(records)
            
            if len(records) < page_size:
                break
            
            page_no += 1
            time.sleep(0.5)
        
        log_audit("QUERY_SNILS", f"records={len(all_records)}")
        return {"success": True, "records": all_records}


# ============ Legacy API Functions (for backward compatibility) ============

def push_xml(api_key: str, xml_file_path: str, xsd_path=None, proxy_settings=None):
    """Legacy function for sending XML."""
    client = MintrudClient(backend="auto", proxy_settings=proxy_settings)
    return client.send_xml(api_key, xml_file_path)


def push_xml_signed(api_key: str, xml_file_path: str, sig_file_path: str, proxy_settings=None):
    """Legacy function for sending XML with electronic signature."""
    client = MintrudClient(backend="auto", proxy_settings=proxy_settings)
    return client.send_xml_signed(api_key, xml_file_path, sig_file_path)


def get_by_set_id(api_key: str, set_id: str, page_size=5000, proxy_settings=None):
    """Legacy function for querying by SetId."""
    client = MintrudClient(backend="auto", proxy_settings=proxy_settings)
    return client.query_by_setid(api_key, set_id, page_size)


def get_by_snils(api_key: str, snils: str, page_size=100, proxy_settings=None):
    """Legacy function for querying by SNILS."""
    client = MintrudClient(backend="auto", proxy_settings=proxy_settings)
    return client.query_by_snils(api_key, snils, page_size)


def get_by_org_id(api_key: str, org_id: str, limit: int = 0, proxy_settings=None):
    """
    Query records by Organization ID (НСПР).
    
    Note: This endpoint may not be available in all API versions.
    """
    return {
        "success": False,
        "records": [],
        "error": "Запрос по OrgId не поддерживается. Используйте запрос по SetId или СНИЛС."
    }


def export_records_to_xlsx(records, file_path):
    """Export records to Excel file."""
    try:
        from openpyxl import Workbook
    except ImportError:
        return False, "Установите openpyxl: pip install openpyxl"
    
    try:
        wb = Workbook()
        ws = wb.active
        ws.title = "Регистрационные номера"
        
        headers = [
            "Номер записи в реестре", "Фамилия", "Имя", "Отчество",
            "СНИЛС", "Должность", "ИНН работодателя", "Наименование работодателя",
            "Номер программы", "Название программы",
            "Номер протокола", "Дата", "Зачёт"
        ]
        ws.append(headers)

        for rec in records:
            row = [
                rec.get('baseNo', ''),
                rec.get('LastName', ''),
                rec.get('FirstName', ''),
                rec.get('MiddleName', ''),
                rec.get('Snils', ''),
                rec.get('Position', ''),
                rec.get('EmployerInn', ''),
                rec.get('EmployerTitle', ''),
                rec.get('learnProgramId', ''),
                rec.get('LearnProgramTitle', ''),
                rec.get('ProtocolNumber', ''),
                rec.get('Date', ''),
                rec.get('isPassed', ''),
            ]
            ws.append(row)
        
        wb.save(file_path)
        return True, f"Файл сохранён: {file_path}"
    except OSError as e:
        return False, f"Ошибка записи файла: {e}"
    except PermissionError:
        return False, "Нет прав на запись файла"


def get_available_backends() -> list:
    """Get list of available transport backends."""
    # Import all backends to register them
    from . import backends
    return BackendRegistry.get_available_backends()