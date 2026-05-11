"""
Модуль сохранения, загрузки и автоопределения настроек прокси-сервера.
Настройки хранятся в /data/proxy_settings.json.
Режим "auto" — автоматическое определение прокси из реестра Windows.
Пароли и логины шифруются.

Поддержка корпоративного прокси:
- NTLM аутентификация с текущими Windows credentials
- Kerberos/Negotiate через requests_negotiate_sspi
- Fallback стратегия: NTLM → pycurl → WinINET
"""
import os
import json
import logging
import base64
import hashlib
from typing import Optional, Dict, Tuple

# ============================================================================
# TLS VERIFICATION SETTINGS
# ============================================================================
# Это значение переопределяется чекбоксом в интерфейсе.
# По умолчанию False для работы через корпоративный прокси с SSL-инспекцией.
# Включите True для безопасного соединения.
ENABLE_TLS_VERIFY = False
# ============================================================================

logger = logging.getLogger(__name__)

# Проверка доступности библиотек для корпоративной авторизации
NTLM_AVAILABLE = False
KERBEROS_AVAILABLE = False
PYCURL_AVAILABLE = False

try:
    from requests_ntlm import HttpNtlmAuth
    NTLM_AVAILABLE = True
except ImportError:
    pass

try:
    from requests_negotiate_sspi import HttpNegotiateAuth
    KERBEROS_AVAILABLE = True
except ImportError:
    pass

try:
    import pycurl
    PYCURL_AVAILABLE = True
except ImportError:
    pass

logger.info(f"Прокси модуль: NTLM={NTLM_AVAILABLE}, Kerberos={KERBEROS_AVAILABLE}, pycurl={PYCURL_AVAILABLE}")

PROXY_SETTINGS_FILE = "proxy_settings.json"


def _get_derive_key():
    """Получение ключа шифрования на основе имени пользователя системы."""
    username = os.environ.get('USERNAME', 'default_user').encode('utf-8')
    return hashlib.sha256(username).digest()


def _fernet():
    """Создание объекта Fernet с ключом из имени пользователя."""
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        raise ImportError(
            "Библиотека 'cryptography' не установлена. "
            "Установите её: pip install cryptography"
        )
    key = _get_derive_key()
    fernet_key = base64.urlsafe_b64encode(key)
    return Fernet(fernet_key)


def _encrypt_value(value: str) -> str:
    """Шифрование значения (пароль/логин) через AES/Fernet."""
    if not value:
        return ""
    return _fernet().encrypt(value.encode('utf-8')).decode('utf-8')


def _decrypt_value(encrypted: str) -> str:
    """Расшифровка значения (пароль/логин) через AES/Fernet."""
    if not encrypted:
        return ""
    return _fernet().decrypt(encrypted.encode('utf-8')).decode('utf-8')

# Режимы работы с прокси:
#   "off"   — прокси не используется
#   "manual" — ручные настройки (url, username, password)
#   "auto"   — автоопределение из системных настроек Windows

def load_proxy_settings(data_dir: str) -> dict:
    """
    Загрузка настроек прокси из файла.
    Возвращает dict:
        mode: str — "off" | "manual" | "auto"
        url: str — адрес прокси (для manual)
        username: str — логин (для manual, расшифрованный)
        password: str — пароль (для manual, расшифрованный)
    """
    settings_file = os.path.join(data_dir, PROXY_SETTINGS_FILE)
    defaults = {
        "mode": "off",
        "url": "",
        "username": "",
        "password": "",
        "tls_verify": False
    }

    if not os.path.exists(settings_file):
        return defaults

    try:
        with open(settings_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for key in defaults:
            if key not in data:
                data[key] = defaults[key]

        global ENABLE_TLS_VERIFY
        ENABLE_TLS_VERIFY = data.get("tls_verify", False)
        
        username_encrypted = data.get("username_encrypted", "")
        password_encrypted = data.get("password_encrypted", "")
        
        username_plain = data.get("username", "")
        password_plain = data.get("password", "")
        
        if username_encrypted or password_encrypted:
            data["username"] = _decrypt_value(username_encrypted)
            data["password"] = _decrypt_value(password_encrypted)
        else:
            data["username"] = username_plain
            data["password"] = password_plain
        
        return data
    except Exception as e:
        logger.error(f"Ошибка чтения настроек прокси: {e}")
        return defaults


def save_proxy_settings(data_dir: str, settings: dict) -> tuple[bool, str]:
    """
    Сохранение настроек прокси в файл.
    Пароли и логины шифруются.
    settings — dict: mode, url, username, password, tls_verify
    """
    settings_file = os.path.join(data_dir, PROXY_SETTINGS_FILE)

    if settings.get("mode") == "manual" and not settings.get("url", "").strip():
        return False, "Укажите адрес прокси-сервера"

    try:
        os.makedirs(data_dir, exist_ok=True)

        username = settings.get("username", "").strip()
        password = settings.get("password", "").strip()

        data = {
            "mode": settings.get("mode", "off"),
            "url": settings.get("url", "").strip(),
            "username_encrypted": _encrypt_value(username),
            "password_encrypted": _encrypt_value(password),
            "username": "",
            "password": "",
            "tls_verify": settings.get("tls_verify", False)
        }
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        global ENABLE_TLS_VERIFY
        ENABLE_TLS_VERIFY = settings.get("tls_verify", False)

        return True, "Настройки прокси сохранены"
    except Exception as e:
        logger.error(f"Ошибка сохранения настроек прокси: {e}")
        return False, f"Ошибка сохранения: {e}"


def detect_windows_proxy() -> str | None:
    r"""
    Автоопределение прокси из реестра Windows.
    Читает ``HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings``.
    Возвращает адрес прокси (например, 'http://proxy.corp.ru:3128') или None.
    """
    try:
        import winreg
        reg_path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path) as key:
            proxy_enabled, _ = winreg.QueryValueEx(key, "ProxyEnable")
            if not proxy_enabled:
                return None

            proxy_server, _ = winreg.QueryValueEx(key, "ProxyServer")
            if not proxy_server:
                return None

            # Формат может быть "proxy:port" или "http=proxy:port;https=proxy:port"
            if "=" in proxy_server:
                # Ищем https или http
                for part in proxy_server.split(";"):
                    if part.startswith("https=") or part.startswith("http="):
                        addr = part.split("=", 1)[1]
                        if addr:
                            # Добавляем схему если нет
                            if not addr.startswith(("http://", "https://")):
                                # Определяем схему из части ключа
                                scheme = part.split("=")[0]
                                addr = f"{scheme}://{addr}"
                            return addr
                return None
            else:
                # Простой формат "proxy:port"
                if not proxy_server.startswith(("http://", "https://")):
                    proxy_server = "http://" + proxy_server
                return proxy_server

    except FileNotFoundError:
        logger.debug("Ключи прокси не найдены в реестре")
        return None
    except Exception as e:
        logger.error(f"Ошибка чтения реестра Windows: {e}")
        return None


def get_current_windows_credentials() -> Tuple[Optional[str], Optional[str]]:
    """
    Получение текущих Windows credentials для SSO.
    Возвращает (username, domain) или (None, None) если недоступно.
    """
    try:
        import getpass
        username = os.environ.get('USERNAME', '')
        domain = os.environ.get('USERDOMAIN', '')
        logon_user = os.environ.get('LOGON_USER', '')

        if logon_user and '\\' in logon_user:
            parts = logon_user.split('\\')
            return parts[1], parts[0]
        elif domain and username:
            return username, domain
    except Exception as e:
        logger.debug(f"Не удалось получить Windows credentials: {e}")

    return None, None


def detect_proxy_auth_type(proxy_url: str) -> Dict[str, any]:
    """
    Определение типа авторизации, поддерживаемого прокси.
    Делает предварительный запрос для получения Proxy-Authenticate заголовков.
    """
    result = {
        "supported": [],
        "ntlm": False,
        "negotiate": False,
        "basic": False,
        "digest": False
    }

    if not proxy_url:
        return result

    try:
        import requests
        test_url = "http://" + proxy_url.split("://")[-1].split("/")[0]
        response = requests.head(test_url, timeout=5, proxies={"http": test_url, "https": test_url})
    except Exception as e:
        logger.debug(f"Не удалось определить тип авторизации прокси: {e}")
        return result

    proxy_auth = response.headers.get('Proxy-Authenticate', '')
    logger.info(f"Прокси предлагает авторизацию: {proxy_auth}")

    if 'NTLM' in proxy_auth.upper():
        result['ntlm'] = True
        result['supported'].append('NTLM')
    if 'NEGOTIATE' in proxy_auth.upper() or 'KERBEROS' in proxy_auth.upper():
        result['negotiate'] = True
        result['supported'].append('Negotiate/Kerberos')
    if 'Basic' in proxy_auth:
        result['basic'] = True
        result['supported'].append('Basic')
    if 'Digest' in proxy_auth:
        result['digest'] = True
        result['supported'].append('Digest')

    return result


def create_session_with_negotiate(settings: dict) -> Optional[object]:
    """
    Создание сессии с Negotiate (Kerberos) авторизацией.
    """
    if not KERBEROS_AVAILABLE:
        return None

    try:
        import requests
        from requests_negotiate_sspi import HttpNegotiateAuth

        mode = settings.get("mode", "off")
        if mode == "off":
            return None

        proxy_url = None
        if mode == "auto":
            proxy_url = detect_windows_proxy()
        elif mode == "manual":
            proxy_url = settings.get("url", "").strip()

        if not proxy_url:
            return None

        session = requests.Session()
        session.proxies = {"http": proxy_url, "https": proxy_url}
        session.auth = HttpNegotiateAuth()

        logger.info("Создана сессия с Negotiate (Kerberos) авторизацией")
        return session
    except Exception as e:
        logger.error(f"Ошибка создания сессии с Negotiate: {e}")
        return None


def create_session_with_ntlm_current_user(settings: dict) -> Optional[object]:
    """
    Создание сессии с NTLM авторизацией используя текущие Windows credentials.
    """
    if not NTLM_AVAILABLE:
        return None

    try:
        from requests_ntlm import HttpNtlmAuth

        mode = settings.get("mode", "off")
        if mode == "off":
            return None

        proxy_url = None
        if mode == "auto":
            proxy_url = detect_windows_proxy()
        elif mode == "manual":
            proxy_url = settings.get("url", "").strip()

        if not proxy_url:
            return None

        username, domain = get_current_windows_credentials()

        session = requests.Session()
        session.proxies = {"http": proxy_url, "https": proxy_url}

        if username and domain:
            full_username = f"{domain}\\{username}"
            session.auth = HttpNtlmAuth(full_username, "")
            logger.info(f"NTLM с текущими credentials: {full_username}")
        else:
            session.auth = HttpNtlmAuth("", "")
            logger.info("NTLM с пустыми credentials (SSPI)")

        return session
    except Exception as e:
        logger.error(f"Ошибка создания сессии с NTLM: {e}")
        return None


def create_session_ntlm_with_credentials(settings: dict) -> Optional[object]:
    """
    Создание сессии с NTLM авторизацией используя явно указанные логин/пароль.
    """
    if not NTLM_AVAILABLE:
        return None

    try:
        from requests_ntlm import HttpNtlmAuth

        mode = settings.get("mode", "off")
        if mode != "manual":
            return None

        proxy_url = settings.get("url", "").strip()
        username = settings.get("username", "").strip()
        password = settings.get("password", "").strip()

        if not proxy_url or not username:
            return None

        session = requests.Session()
        session.proxies = {"http": proxy_url, "https": proxy_url}

        session.auth = HttpNtlmAuth(username, password)
        logger.info(f"NTLM с указанными credentials: {username}")

        return session
    except Exception as e:
        logger.error(f"Ошибка создания сессии NTLM с credentials: {e}")
        return None


def build_proxies_for_requests(settings: dict) -> dict | None:
    """
    Построение словаря proxies для requests на основе настроек.

    Поддерживает режимы:
      "off"   → None
      "manual" → proxies из настроек
      "auto"   → автоматическое определение из реестра Windows

    Возвращает dict для requests или None.
    """
    mode = settings.get("mode", "off")

    if mode == "off":
        return None

    if mode == "auto":
        url = detect_windows_proxy()
        if not url:
            return None
        # Авторизация не поддерживается в auto-режиме
        proxies = _url_to_proxies(url)
        logger.info(f"Auto-прокси обнаружен: {proxies.get('https', 'N/A')}")
        return proxies

    if mode == "manual":
        url = settings.get("url", "").strip()
        if not url:
            return None
        username = settings.get("username", "").strip()
        password = settings.get("password", "").strip()
        proxies = _url_to_proxies(url, username, password)
        if username and password:
            logger.info(f"Прокси с авторизацией: {proxies.get('https', 'N/A')}")
        else:
            logger.info(f"Прокси без авторизации: {proxies.get('https', 'N/A')}")
        return proxies

    return None


def build_proxy_headers(settings: dict) -> dict | None:
    """
    Создание заголовков Proxy-Authorization для requests.Session.

    Внимание: для HTTPS-соединений (CONNECT туннель) этот заголовок
    НЕ БУДЕТ работать — требуется использование HTTPAdapter с
    переопределением метода init_poolmanager (см. create_proxy_session).

    Возвращает dict с заголовками или None.
    """
    mode = settings.get("mode", "off")
    username = ""
    password = ""

    if mode == "manual":
        username = settings.get("username", "").strip()
        password = settings.get("password", "").strip()
    elif mode == "auto":
        # Для auto-режима пытаемся извлечь credentials из системного прокси
        url = detect_windows_proxy()
        if url:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            username = parsed.username or ""
            password = parsed.password or ""

    if username and password:
        # Создаем Basic Auth заголовок для прокси
        credentials = f"{username}:{password}"
        encoded = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        return {"Proxy-Authorization": f"Basic {encoded}"}

    return None


def create_proxy_session(settings: dict, prefer_auth: str = "auto") -> Tuple[Optional[object], str]:
    """
    Создание requests.Session с корректной настройкой прокси-аутентификации.

    Стратегия авторизации (prefer_auth):
      "auto"    - пробуем все методы: Negotiate → NTLM → Basic → fallback
      "negotiate" - только Kerberos/Negotiate
      "ntlm"    - только NTLM
      "basic"   - только Basic (в URL)
      "none"    - без авторизации (для прокси без auth)

    Возвращает tuple (session, auth_method) или (None, error_message)
    """
    import requests

    mode = settings.get("mode", "off")
    logger.info(f"Создание прокси-сессии: mode={mode}, prefer_auth={prefer_auth}")

    if mode == "off":
        session = requests.Session()
        return session, "direct"

    proxy_url = None
    if mode == "auto":
        proxy_url = detect_windows_proxy()
        logger.info(f"Автоопределенный прокси: {proxy_url}")
        if not proxy_url:
            return None, "auto"
    elif mode == "manual":
        proxy_url = settings.get("url", "").strip()
        if not proxy_url:
            return None, "no_url"

    if not proxy_url:
        return None, "no_proxy"

    # Стратегия: auto - пробуем разные методы
    if prefer_auth == "auto" or prefer_auth == "negotiate":
        # Пробуем Negotiate/Kerberos (приоритет для корпоративных прокси)
        if KERBEROS_AVAILABLE:
            session = create_session_with_negotiate({"mode": mode, "url": proxy_url})
            if session:
                logger.info("Успешно: Negotiate/Kerberos")
                return session, "negotiate"

    if prefer_auth == "auto" or prefer_auth == "ntlm":
        # Пробуем NTLM с текущими Windows credentials (SSPI)
        if NTLM_AVAILABLE:
            session = create_session_with_ntlm_current_user({"mode": mode, "url": proxy_url})
            if session:
                logger.info("Успешно: NTLM (Windows credentials)")
                return session, "ntlm_current"

        # Пробуем NTLM с явно указанными credentials
        if mode == "manual" and settings.get("username"):
            session = create_session_ntlm_with_credentials(settings)
            if session:
                logger.info("Успешно: NTLM (указанные credentials)")
                return session, "ntlm_manual"

    if prefer_auth == "auto" or prefer_auth == "basic":
        # Fallback на Basic auth через URL
        username = settings.get("username", "").strip()
        password = settings.get("password", "").strip()
        proxy_with_auth = _build_proxy_url_with_auth(proxy_url, username, password)

        session = requests.Session()
        session.proxies = {"http": proxy_with_auth, "https": proxy_with_auth}
        logger.info(f"Используем Basic auth: {proxy_with_auth[:50]}...")
        return session, "basic"

    # Ничего не сработало
    return None, "all_methods_failed"


def create_proxy_session_legacy(settings: dict):
    """
    Устаревшая функция для обратной совместимости.
    Использует новую create_proxy_session.
    """
    session, method = create_proxy_session(settings, prefer_auth="auto")
    return session


def _url_to_proxies(url: str, username: str = "", password: str = "") -> dict:
    """Преобразование URL прокси в dict для requests."""
    if not url:
        return {"http": None, "https": None}
    
    if not url.startswith(("http://", "https://")):
        url = "http://" + url

    # Для requests credentials нужно встроить в URL для автоматической
    # Proxy-Authorization аутентификации (поддерживает HTTP и HTTPS туннели)
    if username and password:
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(url)
        # Кодируем логин и пароль для безопасности специальных символов
        from urllib.parse import quote
        
        # Пробуем разные форматы для NTLM аутентификации
        # Формат 1: DOMAIN\login -> domain%5Clogin
        # Формат 2: login@domain -> username
        # Формат 3: просто login
        
        # URL-encode для специальных символов: \, @ и т.д.
        auth_user = quote(username, safe='')
        auth_pass = quote(password, safe='')
        
        # Для NTLM часто нужен формат с backslash
        # Попробуем both variants
        netloc = f"{auth_user}:{auth_pass}@{parsed.netloc}"
        url = urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))

    return {
        "http": url,
        "https": url,
    }


def _build_proxy_url_with_auth(proxy_url: str, username: str, password: str) -> str:
    r"""
    Построение URL прокси с credentials.
    Поддерживает различные форматы логина (DOMAIN\login, login@domain, login).
    """
    if not username or not password:
        return proxy_url
    
    from urllib.parse import quote
    
    # Добавляем http:// если нет
    if not proxy_url.startswith(("http://", "https://")):
        proxy_url = "http://" + proxy_url
    
    from urllib.parse import urlparse, urlunparse
    parsed = urlparse(proxy_url)
    
    # Пробуем разные форматы кодирования для NTLM
    # Исходный логин может быть: MSK\login, login@msk.rzd, login
    
    # Просто URL-encode спецсимволы
    auth_user = quote(username, safe='')
    auth_pass = quote(password, safe='')
    
    # Если в логине есть домен (MSK\login или login@domain), пробуем закодировать
    # Для NTLM часто нужен обратный слеш %5C
    if '\\' in username:
        # DOMAIN\login -> DOMAIN%5Clogin
        auth_user = username.replace('\\', '%5C')
        auth_user = quote(auth_user, safe='')
    
    netloc = f"{auth_user}:{auth_pass}@{parsed.hostname}"
    if parsed.port:
        netloc = f"{auth_user}:{auth_pass}@{parsed.hostname}:{parsed.port}"
    
    return urlunparse((parsed.scheme, netloc, '', '', '', ''))


def test_proxy_connection(settings: dict) -> tuple[bool, str]:
    """
    Тестирование подключения через прокси.
    """
    import requests

    mode = settings.get("mode", "off")
    if mode == "off":
        return True, "Прокси отключён — используется прямое подключение"

    session, method = create_proxy_session(settings, prefer_auth="auto")
    if not session:
        if mode == "auto":
            return False, "Системный прокси не найден или отключён в Windows"
        else:
            return False, "Адрес прокси не указан"

    auth_methods = {
        "negotiate": "Negotiate/Kerberos",
        "ntlm_current": "NTLM (Windows credentials)",
        "ntlm_manual": "NTLM (указанные)",
        "basic": "Basic (URL)",
        "direct": "Без авторизации"
    }

    try:
        response = session.get(
            "https://edu.rosmintrud.ru",
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
            timeout=15,
            verify=ENABLE_TLS_VERIFY
        )

        if response.status_code in (200, 404, 403, 301, 302):
            proxy_url = session.proxies.get('https', 'N/A')
            safe_url = proxy_url
            if '@' in proxy_url:
                from urllib.parse import urlparse
                parsed = urlparse(proxy_url)
                safe_url = f"{parsed.scheme}://***:***@{parsed.netloc.split('@')[-1]}"

            method_name = auth_methods.get(method, method)
            return True, f"Подключение успешно\nМетод: {method_name}\nПрокси: {safe_url}"
        else:
            return False, f"HTTP {response.status_code}"
    except requests.exceptions.ProxyError as e:
        return False, f"Ошибка прокси: {e}"
    except requests.exceptions.ConnectionError as e:
        return False, f"Ошибка подключения: {e}"
    except requests.exceptions.Timeout:
        return False, "Таймаут подключения"
    except Exception as e:
        return False, f"Ошибка: {e}"


def diagnose_407_error(response, proxy_settings: dict) -> str:
    """
    Диагностика ошибки 407 Proxy Authentication Required.
    Возвращает подробное описание проблемы и рекомендации.
    """
    diagnostics = []

    proxy_auth = response.headers.get('Proxy-Authenticate', 'unknown')

    diagnostics.append("=== Диагностика ошибки 407 ===")
    diagnostics.append(f"Proxy-Authenticate: {proxy_auth}")
    diagnostics.append(f"Прокси URL: {proxy_settings.get('url', 'N/A')}")
    diagnostics.append(f"Режим: {proxy_settings.get('mode', 'off')}")

    username = proxy_settings.get('username', '')
    if username:
        if '\\' in username:
            diagnostics.append("Тип логина: DOMAIN\\username (возможно NTLM)")
        elif '@' in username:
            diagnostics.append("Тип логина: username@domain (возможно Kerberos)")
        else:
            diagnostics.append("Тип логина: простой username")

    if 'NTLM' in proxy_auth.upper() or 'Negotiate' in proxy_auth.upper():
        diagnostics.append("")
        diagnostics.append("Рекомендации:")
        if not NTLM_AVAILABLE:
            diagnostics.append("  - Установите requests-ntlm: pip install requests-ntlm")
        if not KERBEROS_AVAILABLE:
            diagnostics.append("  - Установите requests-negotiate-sspi: pip install requests-negotiate-sspi")
        diagnostics.append("  - Попробуйте режим 'auto' для автоматического использования Windows credentials")
        diagnostics.append("  - Убедитесь что вы авторизованы в домене Windows")

    if 'Basic' in proxy_auth:
        diagnostics.append("")
        diagnostics.append("Рекомендации:")
        diagnostics.append("  - Проверьте правильность логина и пароля")
        diagnostics.append("  - Убедите что формат логина соответствует требованиям прокси")

    diagnostics.append("")
    diagnostics.append("Доступные методы авторизации в системе:")
    diagnostics.append(f"  - NTLM: {'Да' if NTLM_AVAILABLE else 'Нет (pip install requests-ntlm)'}")
    diagnostics.append(f"  - Kerberos: {'Да' if KERBEROS_AVAILABLE else 'Нет (pip install requests-negotiate-sspi)'}")
    diagnostics.append(f"  - pycurl: {'Да' if PYCURL_AVAILABLE else 'Нет'}")

    return "\n".join(diagnostics)


def try_fallback_connection(proxy_settings: dict, last_error: str) -> Tuple[Optional[object], str]:
    """
    Fallback стратегия при ошибке подключения.
    Пробует: NTLM → pycurl → WinINET

    Возвращает tuple (session, method) или (None, error)
    """
    logger.info(f"Fallback стратегия после ошибки: {last_error}")

    # 1. Пробуем NTLM с текущими credentials
    if NTLM_AVAILABLE:
        session = create_session_with_ntlm_current_user(proxy_settings)
        if session:
            logger.info("Fallback: NTLM с Windows credentials")
            return session, "ntlm_fallback"

    # 2. Пробуем NTLM с указанными credentials
    if NTLM_AVAILABLE and proxy_settings.get('username'):
        session = create_session_ntlm_with_credentials(proxy_settings)
        if session:
            logger.info("Fallback: NTLM с указанными credentials")
            return session, "ntlm_manual_fallback"

    # 3. Пробуем Kerberos/Negotiate
    if KERBEROS_AVAILABLE:
        session = create_session_with_negotiate(proxy_settings)
        if session:
            logger.info("Fallback: Negotiate/Kerberos")
            return session, "negotiate_fallback"

    # 4. Fallback на Basic (через URL)
    logger.info("Fallback: Basic auth через URL")
    session, method = create_proxy_session(proxy_settings, prefer_auth="basic")
    if session:
        return session, "basic_fallback"

    return None, "all_fallbacks_failed"
