import os
import logging
from typing import Tuple
from enum import Enum

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

logger = logging.getLogger(__name__)


class NetworkStatus(Enum):
    SUCCESS = "SUCCESS"
    TIMEOUT = "TIMEOUT"
    NETWORK_ERROR = "NETWORK_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


def test_external_access(
    url: str = "https://edu.rosmintrud.ru",
    timeout: int = 30,
    tls_verify: bool = True
) -> Tuple[NetworkStatus, str]:
    if not REQUESTS_AVAILABLE:
        return NetworkStatus.UNKNOWN_ERROR, "Module 'requests' not available"
    try:
        response = requests.get(url, timeout=timeout, verify=tls_verify)
        if response.status_code in (200, 201, 301, 302, 403, 404):
            return NetworkStatus.SUCCESS, f"HTTP {response.status_code}"
        return NetworkStatus.NETWORK_ERROR, f"HTTP {response.status_code}"
    except requests.Timeout:
        return NetworkStatus.TIMEOUT, "Connection timeout"
    except requests.ConnectionError as e:
        return NetworkStatus.NETWORK_ERROR, f"Connection error: {e}"
    except requests.RequestException as e:
        logger.exception("Unexpected requests error")
        return NetworkStatus.UNKNOWN_ERROR, str(e)
    except Exception as e:
        # Safety net: any non-requests exception (mock tests, edge cases, etc.)
        logger.exception("Unexpected network error")
        return NetworkStatus.UNKNOWN_ERROR, str(e)


def get_network_diagnostics() -> dict:
    """
    Check proxy availability and TLS to edu.rosmintrud.ru.
    Returns dict without PII (no username, hostname).
    """
    result = {
        "negotiate_available": False,
        "detected_proxy": None,
        "auth_method": "None",
        "tls_ok": False,
        "proxy_auth_ok": False,
        "error": None,
        "recommendation": None,
    }

    try:
        import utils.proxy_manager as pm
        proxy_url = pm.detect_windows_proxy()
        if proxy_url:
            from urllib.parse import urlparse
            parsed = urlparse(proxy_url)
            result["detected_proxy"] = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
            result["auth_method"] = "Negotiate/Kerberos (Squid)"
    except Exception as e:
        result["error"] = f"Proxy detection error: {e}"

    try:
        import win32security
        result["negotiate_available"] = True
    except ImportError:
        result["negotiate_available"] = False

    try:
        import urllib.request
        import ssl
        ctx = ssl.create_default_context()
        for verify in (True, False):
            ctx.check_hostname = verify
            ctx.verify_mode = ssl.CERT_REQUIRED if verify else ssl.CERT_NONE
            try:
                if proxy_url := result.get("detected_proxy"):
                    opener = urllib.request.build_opener(
                        urllib.request.ProxyHandler({
                            'http': proxy_url, 'https': proxy_url
                        }),
                        urllib.request.HTTPSHandler(context=ctx),
                    )
                else:
                    opener = urllib.request.build_opener(
                        urllib.request.HTTPSHandler(context=ctx)
                    )
                req = urllib.request.Request(
                    "https://edu.rosmintrud.ru",
                    method="HEAD"
                )
                with opener.open(req, timeout=10) as resp:
                    result["tls_ok"] = True
                    result["proxy_auth_ok"] = True
                    if not verify:
                        result["recommendation"] = (
                            "SSL Inspection: включите опцию "
                            "'Не проверять TLS сертификат' в настройках прокси"
                        )
                    break
            except urllib.error.HTTPError as e:
                if e.code in (200, 301, 302, 403):
                    result["tls_ok"] = True
                    result["proxy_auth_ok"] = True
                    break
                elif e.code == 407:
                    result["proxy_auth_ok"] = False
                    result["recommendation"] = (
                        "Прокси требует авторизацию. "
                        "Попробуйте режим 'Авто (системные)' — "
                        "приложение передаст Windows-токен автоматически."
                    )
                    break
            except ssl.SSLError as e:
                if verify:
                    continue
                result["error"] = f"TLS error: {e}"
                result["recommendation"] = (
                    "Корпоративный прокси подменяет TLS-сертификат. "
                    "Включите 'Не проверять TLS' в настройках прокси или "
                    "установите корпоративный CA-сертификат в Windows."
                )
            except Exception as e:
                result["error"] = str(e)[:200]
    except Exception as e:
        result["error"] = f"Diagnostics error: {e}"

    return result
