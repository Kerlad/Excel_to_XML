import os
import logging
from typing import Tuple, Optional
from enum import Enum

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

logger = logging.getLogger(__name__)

SCHANNEL_10013_MARKERS = [
    "schannel", "10013", "0x80090326",
    "не удалось создать защищенный канал",
    "ssl/tls",
    "ssl handshake",
]


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


def is_schannel_10013_error(error_text: str) -> bool:
    if not error_text:
        return False
    text = error_text.lower().replace("ё", "е")
    return any(marker in text for marker in SCHANNEL_10013_MARKERS)


def get_schannel_recommendation() -> str:
    return (
        "Обнаружена SSL-инспекция корпоративного прокси (Schannel 10013). "
        "Сертификат edu.rosmintrud.ru подменяется корпоративным ЦС, "
        "который не добавлен в доверенные корневые центры сертификации.\n\n"
        "Рекомендации:\n"
        "1. В настройках приложения включите 'Авто (системные)' прокси.\n"
        "2. Отключите 'TLS верификацию' (с подтверждением).\n"
        "3. Либо установите корпоративный CA-сертификат "
        "в 'Доверенные корневые центры сертификации' Windows.\n\n"
        "Внимание: отключение TLS-верификации снижает защиту ПДн."
    )


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
        "is_corporate_env": False,
        "schannel_10013_detected": False,
        "ssl_inspection_detected": False,
    }

    try:
        import utils.proxy_manager as pm
        proxy_url = pm.detect_windows_proxy()
        if proxy_url:
            from urllib.parse import urlparse
            parsed = urlparse(proxy_url)
            result["detected_proxy"] = "%s://%s:%s" % (parsed.scheme, parsed.hostname, parsed.port)
            result["auth_method"] = "Negotiate/Kerberos (Squid)"
            result["is_corporate_env"] = pm.is_corporate_proxy(proxy_url)
    except Exception as e:
        result["error"] = "Proxy detection error: %s" % str(e)[:200]

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
                err_text = str(e)
                result["schannel_10013_detected"] = is_schannel_10013_error(err_text)
                result["ssl_inspection_detected"] = True
                if verify:
                    continue
                result["error"] = "TLS error: %s" % err_text[:200]
                result["recommendation"] = get_schannel_recommendation()
            except urllib.error.URLError as e:
                err_text = str(e.reason) if hasattr(e, 'reason') else str(e)
                result["schannel_10013_detected"] = is_schannel_10013_error(err_text)
                result["ssl_inspection_detected"] = result["schannel_10013_detected"]
                if verify:
                    continue
                result["error"] = "Connection error: %s" % err_text[:200]
            except Exception as e:
                result["error"] = str(e)[:200]
    except Exception as e:
        result["error"] = f"Diagnostics error: {e}"

    return result
