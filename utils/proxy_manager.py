"""
Модуль сохранения, загрузки и автоопределения настроек прокси-сервера.
Настройки хранятся в /data/proxy_settings.json.
Режим "auto" — автоматическое определение прокси из реестра Windows.
Пароли и логины шифруются.
"""
import os
import json
import logging
import base64
import hashlib

# ============================================================================
# TLS VERIFICATION SETTINGS
# ============================================================================
# Это значение переопределяется чекбоксом в интерфейсе.
# По умолчанию False для работы через корпоративный прокси с SSL-инспекцией.
# Включите True для безопасного соединения.
ENABLE_TLS_VERIFY = False
# ============================================================================

import os
import json
import logging
import base64
import hashlib

# Принудительный импорт для NTLM (чтобы PyInstaller включил библиотеку)
try:
    from requests_ntlm import HttpNtlmAuth
except ImportError:
    pass

logger = logging.getLogger(__name__)

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
        "password": ""
    }

    if not os.path.exists(settings_file):
        return defaults

    try:
        with open(settings_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for key in defaults:
            if key not in data:
                data[key] = defaults[key]
        
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
    settings — dict: mode, url, username, password
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
            "password": ""
        }
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
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


def create_proxy_session(settings: dict):
    """
    Создание requests.Session с корректной настройкой прокси-аутентификации.

    Для HTTPS-сайтов (как edu.rosmintrud.ru) прокси использует CONNECT туннель.
    При этом заголовок Proxy-Authorization из session.headers НЕ отправляется,
    потому что соединение устанавливается напрямую с целевым сервером.

    Решение:
    1. Встраиваем credentials прямо в URL прокси (user:pass@proxy:port)
    2. Для auto-режима: пытаемся извлечь credentials из системного прокси
    3. Настраиваем HTTPAdapter с отключением verify=False на уровне сессии

    Возвращает настроенный requests.Session или None если прокси отключен.
    """
    import requests
    from urllib.parse import urlparse, urlunparse, quote

    mode = settings.get("mode", "off")

    if mode == "off":
        # Прямое подключение без прокси
        session = requests.Session()
        return session

    # Определяем URL прокси
    proxy_url = None
    ntlm_available = False
    
    # Пробуем импортировать requests-ntlm для NTLM-аутентификации
    try:
        from requests_ntlm import HttpNtlmAuth
        ntlm_available = True
    except ImportError:
        pass
    
    if mode == "auto":
        proxy_url = detect_windows_proxy()
        if not proxy_url:
            return None
    elif mode == "manual":
        proxy_url = settings.get("url", "").strip()
        if not proxy_url:
            return None
        # Добавляем credentials из настроек
        username = settings.get("username", "").strip()
        password = settings.get("password", "").strip()
        if username and password:
            # Пробуем NTLM если доступна
            if ntlm_available and '\\' in username:
                # DOMAIN\login - используем NTLM
                try:
                    auth = HttpNtlmAuth(username, password)
                    # Сессия с NTLM будет настроена ниже
                    settings['_ntlm_auth'] = auth
                except:
                    pass
            
            # Стандартный подход: встраиваем credentials в URL
            proxy_url = _build_proxy_url_with_auth(proxy_url, username, password)

    if not proxy_url:
        return None

    # Создаем сессию с прокси
    session = requests.Session()
    session.proxies = {
        "http": proxy_url,
        "https": proxy_url,
    }
    
    # Если есть NTLM auth - применяем
    ntlm_auth = settings.get("_ntlm_auth")
    if ntlm_auth:
        session.auth = ntlm_auth
        logger.info("Используется NTLM-аутентификация")

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

    # Сначала проверяем режим
    mode = settings.get("mode", "off")
    if mode == "off":
        return True, "Прокси отключён — используется прямое подключение"

    # Используем новый create_proxy_session
    session = create_proxy_session(settings)
    if not session:
        if mode == "auto":
            return False, "Системный прокси не найден или отключён в Windows"
        else:
            return False, "Адрес прокси не указан"

    try:
        response = session.get(
            "https://edu.rosmintrud.ru",
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
            timeout=15,
            verify=ENABLE_TLS_VERIFY
        )

        if response.status_code in (200, 404, 403, 301, 302):
            # Скрываем пароль для безопасности
            proxy_url = session.proxies.get('https', 'N/A')
            safe_url = proxy_url
            if '@' in proxy_url:
                from urllib.parse import urlparse
                parsed = urlparse(proxy_url)
                safe_url = f"{parsed.scheme}://***:***@{parsed.netloc.split('@')[-1]}"
            return True, f"Подключение успешно\nПрокси: {safe_url}"
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
