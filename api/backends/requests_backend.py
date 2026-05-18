import logging
from typing import Dict, Any, Optional

from .base_backend import BaseBackend, BackendRegistry

logger = logging.getLogger(__name__)


class RequestsBackend(BaseBackend):
    name = "requests"

    def is_available(self) -> bool:
        try:
            import requests
            return True
        except ImportError:
            return False

    def send(
        self, url: str, files: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 60, verify: bool = True,
        proxies: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> tuple[bool, int, bytes, str]:
        import requests
        logger.info(f"RequestsBackend: POST {url}")
        try:
            session = requests.Session()
            if proxies:
                session.proxies = proxies
            response = session.post(url, files=files, headers=headers,
                                    timeout=timeout, verify=verify)
            session.close()
            return True, response.status_code, response.content, ""
        except requests.exceptions.Timeout:
            return False, 0, b"", "Request timeout"
        except requests.exceptions.ProxyError as e:
            return False, 0, b"", f"Proxy error: {e}"
        except requests.exceptions.ConnectionError as e:
            return False, 0, b"", f"Connection error: {e}"
        except Exception as e:
            return False, 0, b"", str(e)

    def get(
        self, url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None,
        timeout: int = 60, verify: bool = True,
        proxies: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> tuple[bool, int, bytes, str]:
        import requests
        logger.info(f"RequestsBackend: GET {url}")
        try:
            session = requests.Session()
            if proxies:
                session.proxies = proxies
            response = session.get(url, headers=headers, params=params,
                                   timeout=timeout, verify=verify)
            session.close()
            return True, response.status_code, response.content, ""
        except Exception as e:
            return False, 0, b"", str(e)


BackendRegistry.register(RequestsBackend)
