"""
HTTPX HTTP backend.
"""
import logging
from typing import Dict, Any, Optional

from .base_backend import BaseBackend, BackendRegistry

logger = logging.getLogger(__name__)


class HTTPXBackend(BaseBackend):
    """HTTP backend using httpx library."""
    
    name = "httpx"
    
    def is_available(self) -> bool:
        """Check if httpx library is available."""
        try:
            import httpx
            return True
        except ImportError:
            return False
    
    def send(
        self,
        url: str,
        files: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 60,
        verify: bool = True,
        proxies: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> tuple[bool, int, bytes, str]:
        """Send POST request using httpx."""
        import httpx
        
        logger.info(f"HTTPXBackend: POST {url}")
        
        try:
            client = httpx.Client(
                timeout=timeout,
                verify=verify,
                proxy=proxies.get('http') if proxies else None,
                **kwargs
            )
            
            response = client.post(url, files=files, headers=headers)
            client.close()
            
            logger.info(f"Response: HTTP {response.status_code}")
            return True, response.status_code, response.content, ""
            
        except httpx.TimeoutException:
            logger.error("Request timeout")
            return False, 0, b"", "Таймаут соединения"
        except httpx.ProxyError as e:
            logger.error(f"Proxy error: {e}")
            return False, 0, b"", f"Ошибка прокси: {e}"
        except Exception as e:
            logger.error(f"Error: {e}")
            return False, 0, b"", str(e)
    
    def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None,
        timeout: int = 60,
        verify: bool = True,
        proxies: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> tuple[bool, int, bytes, str]:
        """Send GET request using httpx."""
        import httpx
        
        logger.info(f"HTTPXBackend: GET {url}")
        
        try:
            client = httpx.Client(
                timeout=timeout,
                verify=verify,
                proxy=proxies.get('http') if proxies else None,
                **kwargs
            )
            
            response = client.get(url, headers=headers, params=params)
            client.close()
            
            logger.info(f"Response: HTTP {response.status_code}")
            return True, response.status_code, response.content, ""
            
        except Exception as e:
            logger.error(f"GET error: {e}")
            return False, 0, b"", str(e)


BackendRegistry.register(HTTPXBackend)