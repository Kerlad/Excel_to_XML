import os
import json
import logging
from typing import Optional, Dict

from utils.crypto import encrypt_value, decrypt_value

ENABLE_TLS_VERIFY = True

logger = logging.getLogger(__name__)

PROXY_SETTINGS_FILE = "proxy_settings.json"


def load_proxy_settings(data_dir: str) -> dict:
    settings_file = os.path.join(data_dir, PROXY_SETTINGS_FILE)
    defaults = {"mode": "off", "url": "", "username": "", "password": "", "tls_verify": True}
    if not os.path.exists(settings_file):
        return defaults
    try:
        with open(settings_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for key in defaults:
            if key not in data:
                data[key] = defaults[key]
        global ENABLE_TLS_VERIFY
        ENABLE_TLS_VERIFY = data.get("tls_verify", True)
        ue = data.get("username_encrypted", "")
        pe = data.get("password_encrypted", "")
        if ue or pe:
            data["username"] = decrypt_value(ue)
            data["password"] = decrypt_value(pe)
        else:
            data["username"] = data.get("username", "")
            data["password"] = data.get("password", "")
        return data
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Error loading proxy settings: {e}")
        return defaults


def save_proxy_settings(data_dir: str, settings: dict) -> tuple[bool, str]:
    settings_file = os.path.join(data_dir, PROXY_SETTINGS_FILE)
    if settings.get("mode") == "manual" and not settings.get("url", "").strip():
        return False, "Enter proxy URL"
    try:
        os.makedirs(data_dir, exist_ok=True)
        username = settings.get("username", "").strip()
        password = settings.get("password", "").strip()
        data = {
            "mode": settings.get("mode", "off"),
            "url": settings.get("url", "").strip(),
            "username_encrypted": encrypt_value(username),
            "password_encrypted": encrypt_value(password),
            "username": "",
            "password": "",
            "tls_verify": settings.get("tls_verify", True),
        }
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        global ENABLE_TLS_VERIFY
        ENABLE_TLS_VERIFY = settings.get("tls_verify", True)
        return True, "Proxy settings saved"
    except OSError as e:
        return False, f"Error saving: {e}"


def detect_windows_proxy() -> Optional[str]:
    try:
        import winreg
        reg_path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path) as key:
            enabled, _ = winreg.QueryValueEx(key, "ProxyEnable")
            if not enabled:
                return None
            server, _ = winreg.QueryValueEx(key, "ProxyServer")
            if not server:
                return None
            if "=" in server:
                for part in server.split(";"):
                    if part.startswith("https=") or part.startswith("http="):
                        addr = part.split("=", 1)[1]
                        if addr:
                            if not addr.startswith(("http://", "https://")):
                                scheme = part.split("=")[0]
                                addr = f"{scheme}://{addr}"
                            return addr
                return None
            if not server.startswith(("http://", "https://")):
                server = "http://" + server
            return server
    except (ImportError, OSError):
        return None


def build_proxies_for_requests(settings: dict) -> Optional[Dict[str, str]]:
    mode = settings.get("mode", "off")
    if mode == "off":
        return None
    if mode == "auto":
        url = detect_windows_proxy()
        return {"http": url, "https": url} if url else None
    if mode == "manual":
        url = settings.get("url", "").strip()
        if not url:
            return None
        username = settings.get("username", "").strip()
        password = settings.get("password", "").strip()
        if username and password:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            host = parsed.hostname or url
            port = parsed.port or 3128
            proxies = {
                "http": f"http://{host}:{port}",
                "https": f"http://{host}:{port}",
            }
            proxies["_username"] = username
            proxies["_password"] = password
        else:
            proxies = {"http": url, "https": url}
        return proxies
    return None
