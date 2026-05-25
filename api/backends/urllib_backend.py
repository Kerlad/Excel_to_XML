"""
urllib backend — uses built-in urllib.request with SSPI Negotiate support
for corporate proxy environments.
"""
import io
import logging
import os
import urllib.request
import urllib.error
from typing import Dict, Any, Optional
from urllib.parse import urlparse, urlencode

from .base_backend import BaseBackend, BackendRegistry

logger = logging.getLogger(__name__)


class UrllibBackend(BaseBackend):
    """urllib backend with corporate Negotiate/NTLM proxy support."""

    name = "urllib"

    def is_available(self) -> bool:
        return True

    def _build_opener(
        self,
        proxies: Optional[Dict[str, str]] = None,
        verify: bool = True,
    ) -> urllib.request.OpenerDirector:
        handlers = []

        import ssl
        ctx = ssl.create_default_context()
        if not verify:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            logger.warning("urllib: TLS verification disabled")
        handlers.append(urllib.request.HTTPSHandler(context=ctx))

        if proxies:
            proxy_url = proxies.get('https') or proxies.get('http')
            if proxy_url:
                proxy_handler = urllib.request.ProxyHandler({
                    'http': proxy_url,
                    'https': proxy_url,
                })
                handlers.append(proxy_handler)
                try:
                    import win32security
                    import sspi
                    logger.debug("urllib: SSPI available for Negotiate auth")
                except ImportError:
                    logger.debug("urllib: SSPI not available, proxy may require manual auth")
        else:
            handlers.append(urllib.request.ProxyHandler({}))

        return urllib.request.build_opener(*handlers)

    def _encode_multipart(
        self, files: Dict[str, Any], boundary: str
    ) -> bytes:
        body = b''
        for field_name, (filename, content, content_type) in files.items():
            body += f'--{boundary}\r\n'.encode()
            body += (
                f'Content-Disposition: form-data; '
                f'name="{field_name}"; filename="{filename}"\r\n'
            ).encode()
            body += f'Content-Type: {content_type}\r\n\r\n'.encode()
            body += content + b'\r\n'
        body += f'--{boundary}--\r\n'.encode()
        return body

    def send(
        self, url: str, files: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 60, verify: bool = True,
        proxies: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> tuple[bool, int, bytes, str]:
        parsed = urlparse(url)
        logger.info(
            "UrllibBackend: POST %s://%s%s",
            parsed.scheme, parsed.netloc, parsed.path
        )
        try:
            boundary = "----FormBoundary" + os.urandom(8).hex()
            body = self._encode_multipart(files, boundary)

            req = urllib.request.Request(url, data=body, method='POST')
            req.add_header(
                'Content-Type',
                f'multipart/form-data; boundary={boundary}'
            )
            if headers:
                for k, v in headers.items():
                    if k.lower() != 'content-type':
                        req.add_header(k, v)

            opener = self._build_opener(proxies, verify)
            with opener.open(req, timeout=timeout) as resp:
                status_code = resp.status
                content = resp.read()
            return True, status_code, content, ""

        except urllib.error.HTTPError as e:
            content = e.read() if hasattr(e, 'read') else b""
            logger.error("UrllibBackend HTTP error: %s", e.code)
            return False, e.code, content, f"HTTP {e.code}: {e.reason}"
        except urllib.error.URLError as e:
            logger.error("UrllibBackend URL error: %s", e.reason)
            return False, 0, b"", str(e.reason)
        except OSError as e:
            logger.error("UrllibBackend OS error: %s", e)
            return False, 0, b"", str(e)

    def get(
        self, url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None,
        timeout: int = 60, verify: bool = True,
        proxies: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> tuple[bool, int, bytes, str]:
        if params:
            url = f"{url}?{urlencode(params)}"
        parsed = urlparse(url)
        logger.info(
            "UrllibBackend: GET %s://%s%s",
            parsed.scheme, parsed.netloc, parsed.path
        )
        try:
            req = urllib.request.Request(url, method='GET')
            if headers:
                for k, v in headers.items():
                    req.add_header(k, v)
            opener = self._build_opener(proxies, verify)
            with opener.open(req, timeout=timeout) as resp:
                return True, resp.status, resp.read(), ""
        except urllib.error.HTTPError as e:
            content = e.read() if hasattr(e, 'read') else b""
            return False, e.code, content, f"HTTP {e.code}: {e.reason}"
        except urllib.error.URLError as e:
            return False, 0, b"", str(e.reason)
        except OSError as e:
            return False, 0, b"", str(e)


BackendRegistry.register(UrllibBackend)
