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
    except Exception as e:
        msg = str(e)
        if "Timeout" in msg:
            return NetworkStatus.TIMEOUT, "Connection timeout"
        if "Connection" in msg:
            return NetworkStatus.NETWORK_ERROR, f"Connection error: {e}"
        return NetworkStatus.UNKNOWN_ERROR, str(e)


def get_network_diagnostics() -> dict:
    return {
        "negotiate_available": False,
        "detected_proxy": None,
        "auth_method": "None",
        "windows_user": os.environ.get('USERNAME', ''),
    }
