import logging
from typing import Dict, Any, Optional

from .base_backend import BaseBackend, BackendRegistry

logger = logging.getLogger(__name__)


class RequestsBackend(BaseBackend):
    name = "requests"
    _session = None

    def _get_session(self, proxies):
        import requests
        if self._session is None:
            self._session = requests.Session()
            # Retry policy with backoff
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS"]
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self._session.mount("https://", adapter)
            self._session.mount("http://", adapter)
        if proxies:
            self._session.proxies = proxies
        return self._session

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
        logger.info(f"RequestsBackend: POST {url}")
        try:
            session = self._get_session(proxies)
            response = session.post(url, files=files, headers=headers,
                                    timeout=timeout, verify=verify)
            return True, response.status_code, response.content, ""
        except ImportError:
            return False, 0, b"", "requests not installed"

    def get(
        self, url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None,
        timeout: int = 60, verify: bool = True,
        proxies: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> tuple[bool, int, bytes, str]:
        logger.info(f"RequestsBackend: GET {url}")
        try:
            session = self._get_session(proxies)
            response = session.get(url, headers=headers, params=params,
                                   timeout=timeout, verify=verify)
            return True, response.status_code, response.content, ""
        except Exception as e:
            return False, 0, b"", str(e)


BackendRegistry.register(RequestsBackend)
