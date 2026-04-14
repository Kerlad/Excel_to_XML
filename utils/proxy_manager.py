"""
Модуль сохранения, загрузки и автоопределения настроек прокси-сервера.
Настройки хранятся в /data/proxy_settings.json.
Режим "auto" — автоматическое определение прокси из реестра Windows.
"""
import os
import json
import logging
import base64

logger = logging.getLogger(__name__)

PROXY_SETTINGS_FILE = "proxy_settings.json"

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
        username: str — логин (для manual)
        password: str — пароль (для manual)
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
        return data
    except Exception as e:
        logger.error(f"Ошибка чтения настроек прокси: {e}")
        return defaults


def save_proxy_settings(data_dir: str, settings: dict) -> tuple[bool, str]:
    """
    Сохранение настроек прокси в файл.
    settings — dict: mode, url, username, password
    """
    settings_file = os.path.join(data_dir, PROXY_SETTINGS_FILE)

    if settings.get("mode") == "manual" and not settings.get("url", "").strip():
        return False, "Укажите адрес прокси-сервера"

    try:
        os.makedirs(data_dir, exist_ok=True)
        data = {
            "mode": settings.get("mode", "off"),
            "url": settings.get("url", "").strip(),
            "username": settings.get("username", "").strip(),
            "password": settings.get("password", "").strip()
        }
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True, "Настройки прокси сохранены"
    except Exception as e:
        logger.error(f"Ошибка сохранения настроек прокси: {e}")
        return False, f"Ошибка сохранения: {e}"


def detect_windows_proxy() -> str | None:
    """
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
            logger.info(f"Прокси с авторизацией: {proxies.get('https', 'N/A')} (логин: {username})")
        else:
            logger.info(f"Прокси без авторизации: {proxies.get('https', 'N/A')}")
        return proxies

    return None


def build_proxy_headers(settings: dict) -> dict | None:
    """
    Создание заголовков Proxy-Authorization для requests.Session.
    
    Это необходимо для HTTPS-туннелей (CONNECT метод), где requests/urllib3
    не всегда автоматически отправляет Proxy-Authorization из URL.
    
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


def _url_to_proxies(url: str, username: str = "", password: str = "") -> dict:
    """Преобразование URL прокси в dict для requests."""
    if not url.startswith(("http://", "https://")):
        url = "http://" + url

    # Для requests credentials нужно встроить в URL для автоматической
    # Proxy-Authorization аутентификации (поддерживает HTTP и HTTPS туннели)
    if username and password:
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(url)
        # Кодируем логин и пароль для безопасности специальных символов
        from urllib.parse import quote
        auth_user = quote(username, safe='')
        auth_pass = quote(password, safe='')
        netloc = f"{auth_user}:{auth_pass}@{parsed.netloc}"
        url = urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))

    return {
        "http": url,
        "https": url,
    }


def test_proxy_connection(settings: dict) -> tuple[bool, str]:
    """
    Тестирование подключения через прокси.
    """
    import requests

    proxies = build_proxies_for_requests(settings)
    proxy_headers = build_proxy_headers(settings)

    if not proxies:
        mode = settings.get("mode", "off")
        if mode == "off":
            return True, "Прокси отключён — используется прямое подключение"
        elif mode == "auto":
            return False, "Системный прокси не найден или отключён в Windows"
        else:
            return False, "Адрес прокси не указан"

    try:
        # Используем Session для корректной proxy-аутентификации
        with requests.Session() as session:
            if proxies:
                session.proxies = proxies
            if proxy_headers:
                session.headers.update(proxy_headers)
            
            response = session.get(
                "https://edu.rosmintrud.ru",
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
                timeout=15,
                verify=False
            )
        
        if response.status_code in (200, 404, 403, 301, 302):
            detected_url = list(proxies.values())[0]
            # Скрываем пароль для безопасности
            safe_url = detected_url
            if '@' in detected_url:
                from urllib.parse import urlparse
                parsed = urlparse(detected_url)
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
