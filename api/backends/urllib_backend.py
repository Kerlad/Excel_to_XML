"""
urllib HTTP backend.
"""
import logging
import ssl
from typing import Dict, Any, Optional

from .base_backend import BaseBackend, BackendRegistry

logger = logging.getLogger(__name__)

# TLS version mapping (using TLSVersion enum for SSLContext.minimum/maximum_version)
URLLIB_TLS_VERSION_MAP = {
    "1.0": ssl.TLSVersion.TLSv1,
    "1.1": ssl.TLSVersion.TLSv1_1,
    "1.2": ssl.TLSVersion.TLSv1_2,
    "1.3": getattr(ssl.TLSVersion, "TLSv1_3", ssl.TLSVersion.TLSv1_2),
}


def _urllib_create_ssl_context(
    verify: bool = False,
    tls_min_version: Optional[str] = None,
    tls_max_version: Optional[str] = None,
    ciphers: Optional[str] = None,
) -> ssl.SSLContext:
    """Create SSL context for urllib with custom TLS configuration."""
    if not verify:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    else:
        ctx = ssl.create_default_context()

    if tls_min_version:
        min_ver = URLLIB_TLS_VERSION_MAP.get(tls_min_version)
        if min_ver:
            ctx.minimum_version = min_ver

    if tls_max_version:
        max_ver = URLLIB_TLS_VERSION_MAP.get(tls_max_version)
        if max_ver:
            ctx.maximum_version = max_ver

    if ciphers:
        ctx.set_ciphers(ciphers)

    return ctx


class URLLibBackend(BaseBackend):
    """HTTP backend using urllib (no external dependencies)."""

    name = "urllib"

    def is_available(self) -> bool:
        """urllib is always available in Python."""
        return True

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
        """Send POST request using urllib."""
        import urllib.request
        import urllib.parse
        import urllib.error

        logger.info(f"URLLibBackend: POST {url}")

        try:
            req_headers = dict(headers) if headers else {}
            req_headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

            body = None
            for field_name, (filename, content, content_type) in files.items():
                import uuid
                boundary = uuid.uuid4().hex

                req_headers['Content-Type'] = f'multipart/form-data; boundary={boundary}'

                body_parts = []
                body_parts.append(f'--{boundary}\r\n'.encode())
                body_parts.append(f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode())
                body_parts.append(f'Content-Type: {content_type}\r\n\r\n'.encode())
                body_parts.append(content + b'\r\n')
                body_parts.append(f'--{boundary}--\r\n'.encode())
                body = b''.join(body_parts)
                break

            req = urllib.request.Request(
                url,
                data=body,
                headers=req_headers,
                method='POST'
            )

            if proxies:
                proxy_handler = urllib.request.ProxyHandler(proxies)
                opener = urllib.request.build_opener(proxy_handler)
            else:
                opener = urllib.request.build_opener()

            # Create SSL context with optional TLS configuration
            tls_min = kwargs.get("tls_min_version")
            tls_max = kwargs.get("tls_max_version")
            ciphers = kwargs.get("ciphers")
            ctx = _urllib_create_ssl_context(
                verify=verify,
                tls_min_version=tls_min,
                tls_max_version=tls_max,
                ciphers=ciphers,
            )
            opener.add_handler(urllib.request.HTTPSHandler(context=ctx))

            response = opener.open(req, timeout=timeout)
            response_bytes = response.read()
            status_code = response.getcode()

            logger.info(f"Response: HTTP {status_code}")
            return True, status_code, response_bytes, ""

        except urllib.error.HTTPError as e:
            logger.error(f"HTTP error: {e.code} - {e.reason}")
            try:
                error_body = e.read()
                return True, e.code, error_body, ""
            except Exception:
                return False, e.code, b"", str(e)
        except urllib.error.URLError as e:
            logger.error(f"URL error: {e.reason}")
            return False, 0, b"", str(e.reason)
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
        """Send GET request using urllib."""
        import urllib.request
        import urllib.parse
        import urllib.error

        logger.info(f"URLLibBackend: GET {url}")

        try:
            if params:
                url_with_params = f"{url}?{urllib.parse.urlencode(params)}"
            else:
                url_with_params = url

            req = urllib.request.Request(url_with_params, headers=headers or {})

            if proxies:
                proxy_handler = urllib.request.ProxyHandler(proxies)
                opener = urllib.request.build_opener(proxy_handler)
            else:
                opener = urllib.request.build_opener()

            tls_min = kwargs.get("tls_min_version")
            tls_max = kwargs.get("tls_max_version")
            ciphers = kwargs.get("ciphers")
            ctx = _urllib_create_ssl_context(
                verify=verify,
                tls_min_version=tls_min,
                tls_max_version=tls_max,
                ciphers=ciphers,
            )
            opener.add_handler(urllib.request.HTTPSHandler(context=ctx))

            response = opener.open(req, timeout=timeout)
            response_bytes = response.read()
            status_code = response.getcode()

            logger.info(f"Response: HTTP {status_code}")
            return True, status_code, response_bytes, ""

        except Exception as e:
            logger.error(f"GET error: {e}")
            return False, 0, b"", str(e)


BackendRegistry.register(URLLibBackend)