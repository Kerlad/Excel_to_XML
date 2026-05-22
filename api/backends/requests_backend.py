import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .base_backend import BaseBackend, BackendRegistry

logger = logging.getLogger(__name__)


@dataclass
class SessionConfig:
    total_retries: int = 3
    backoff_factor: float = 1.0
    status_forcelist: tuple = (429, 500, 502, 503, 504)
    allowed_methods: tuple = ("HEAD", "GET", "OPTIONS", "POST")
    timeout: int = 60


class RequestsBackend(BaseBackend):
    name = "requests"

    def __init__(self):
        self._config = SessionConfig()

    def _create_session(
        self,
        proxies: Optional[Dict[str, str]] = None,
        verify: bool = True,
    ) -> requests.Session:
        session = requests.Session()
        session.verify = verify
        if proxies:
            session.proxies.update(proxies)
        retry_strategy = Retry(
            total=self._config.total_retries,
            backoff_factor=self._config.backoff_factor,
            status_forcelist=list(self._config.status_forcelist),
            allowed_methods=list(self._config.allowed_methods),
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def is_available(self) -> bool:
        try:
            import requests as _
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
        parsed = urlparse(url)
        logger.info("RequestsBackend: POST %s://%s%s", parsed.scheme, parsed.netloc, parsed.path)
        session = self._create_session(proxies, verify)
        try:
            response = session.post(
                url, files=files, headers=headers,
                timeout=timeout, verify=verify
            )
            return True, response.status_code, response.content, ""
        except requests.ConnectionError as e:
            logger.error(f"RequestsBackend connection error: {e}")
            return False, 0, b"", str(e)
        except requests.Timeout as e:
            logger.error(f"RequestsBackend timeout: {e}")
            return False, 0, b"", str(e)
        except requests.RequestException as e:
            logger.error(f"RequestsBackend request error: {e}")
            return False, 0, b"", str(e)
        finally:
            session.close()

    def get(
        self, url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None,
        timeout: int = 60, verify: bool = True,
        proxies: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> tuple[bool, int, bytes, str]:
        parsed = urlparse(url)
        logger.info("RequestsBackend: GET %s://%s%s", parsed.scheme, parsed.netloc, parsed.path)
        session = self._create_session(proxies, verify)
        try:
            response = session.get(
                url, headers=headers, params=params,
                timeout=timeout, verify=verify
            )
            return True, response.status_code, response.content, ""
        except requests.ConnectionError as e:
            logger.error(f"RequestsBackend connection error: {e}")
            return False, 0, b"", str(e)
        except requests.Timeout as e:
            logger.error(f"RequestsBackend timeout: {e}")
            return False, 0, b"", str(e)
        except requests.RequestException as e:
            logger.error(f"RequestsBackend request error: {e}")
            return False, 0, b"", str(e)
        finally:
            session.close()


BackendRegistry.register(RequestsBackend)
