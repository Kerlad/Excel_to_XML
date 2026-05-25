"""
WinINET HTTP backend using WinHTTP COM object (WinHttp.WinHttpRequest.5.1).
Available on all Windows systems via win32com.
"""
import logging
import os
from typing import Dict, Any, Optional
from urllib.parse import urlparse

from .base_backend import BaseBackend, BackendRegistry

logger = logging.getLogger(__name__)

WININET_AVAILABLE = False

try:
    import win32com.client
    WININET_AVAILABLE = True
except ImportError:
    pass

WINHTTP_ACCESS_TYPE_DEFAULT_PROXY = 0
WINHTTP_ACCESS_TYPE_NO_PROXY = 1
WINHTTP_ACCESS_TYPE_NAMED_PROXY = 3

WINHTTP_AUTOLOGON_POLICY_ALWAYS = 0
WINHTTP_AUTOLOGON_POLICY_ONLY_IF_CHALLENGED = 1
WINHTTP_AUTOLOGON_POLICY_NEVER = 2

WINHTTP_OPTION_SECURITY_FLAGS = 31
SECURITY_FLAG_IGNORE_UNKNOWN_CA = 0x00000100
SECURITY_FLAG_IGNORE_CERT_CN_INVALID = 0x00001000
SECURITY_FLAG_IGNORE_CERT_DATE_INVALID = 0x00002000
SECURITY_FLAG_IGNORE_ALL_CERT_ERRORS = (
    SECURITY_FLAG_IGNORE_UNKNOWN_CA |
    SECURITY_FLAG_IGNORE_CERT_CN_INVALID |
    SECURITY_FLAG_IGNORE_CERT_DATE_INVALID
)


def _make_request(
    method: str,
    url: str,
    body: Optional[bytes] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 60,
    verify: bool = True,
    proxies: Optional[Dict[str, str]] = None,
) -> tuple[bool, int, bytes, str]:
    """Execute HTTP request via WinHTTP COM object."""
    try:
        http = win32com.client.Dispatch("WinHttp.WinHttpRequest.5.1")
        http.SetTimeouts(timeout * 1000, timeout * 1000, timeout * 1000, timeout * 1000)
        http.Open(method, url, False)

        http.SetAutoLogonPolicy(WINHTTP_AUTOLOGON_POLICY_ALWAYS)

        if not verify:
            try:
                http.Option[WINHTTP_OPTION_SECURITY_FLAGS] = SECURITY_FLAG_IGNORE_ALL_CERT_ERRORS
                logger.warning(
                    "WinINET: TLS certificate verification disabled "
                    "(corporate SSL inspection mode)"
                )
            except AttributeError:
                logger.debug("WinINET: cannot set SECURITY_FLAGS (COM limitation)")

        if proxies:
            proxy_url = proxies.get('https') or proxies.get('http')
            if proxy_url:
                http.SetProxy(WINHTTP_ACCESS_TYPE_NAMED_PROXY, proxy_url, "")
                logger.debug("WinINET: using proxy %s", proxy_url)
        else:
            http.SetProxy(WINHTTP_ACCESS_TYPE_DEFAULT_PROXY, "", "")

        if headers:
            for k, v in headers.items():
                http.SetRequestHeader(k, v)

        if body:
            http.Send(body)
        else:
            http.Send()

        status_code = http.Status
        response_bytes = bytes(http.ResponseBody)

        if status_code >= 400:
            err_text = f"HTTP {status_code}"
            try:
                err_text += f": {http.StatusText}"
            except AttributeError:
                pass
            return False, status_code, response_bytes, err_text

        return True, status_code, response_bytes, ""

    except AttributeError as e:
        logger.error(f"WinHTTP COM error: {e}")
        return False, 0, b"", str(e)
    except OSError as e:
        logger.error(f"WinHTTP network error: {e}")
        return False, 0, b"", str(e)
    except ValueError as e:
        logger.error(f"WinHTTP value error: {e}")
        return False, 0, b"", str(e)


class WinINETBackend(BaseBackend):
    """HTTP backend using WinHTTP COM (best for Windows/corporate proxy)."""

    name = "wininet"

    def is_available(self) -> bool:
        """Check if WinHTTP COM is available (Windows only)."""
        return WININET_AVAILABLE and os.name == 'nt'

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
        """Send POST request using WinHTTP COM."""
        if not WININET_AVAILABLE:
            return False, 0, b"", "WinINET not available"

        parsed = urlparse(url)
        logger.info("WinINETBackend: POST %s://%s%s", parsed.scheme, parsed.netloc, parsed.path)

        try:
            boundary = "----FormBoundary" + os.urandom(8).hex()

            body = b''
            for field_name, (filename, content, content_type) in files.items():
                body += f'--{boundary}\r\n'.encode()
                body += f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode()
                body += f'Content-Type: {content_type}\r\n\r\n'.encode()
                body += content + b'\r\n'
            body += f'--{boundary}--\r\n'.encode()

            req_headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
            if headers:
                for k, v in headers.items():
                    if k.lower() != 'content-type':
                        req_headers[k] = v

            return _make_request("POST", url, body, req_headers, timeout, verify, proxies)

        except (ValueError, OSError) as e:
            logger.error(f"WinINET error: {e}")
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
        """Send GET request using WinHTTP COM."""
        if not WININET_AVAILABLE:
            return False, 0, b"", "WinINET not available"

        import urllib.parse

        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"

        parsed = urlparse(url)
        logger.info("WinINETBackend: GET %s://%s%s", parsed.scheme, parsed.netloc, parsed.path)

        try:
            return _make_request("GET", url, None, headers, timeout, verify, proxies)
        except (ValueError, OSError) as e:
            logger.error(f"WinINET error: {e}")
            return False, 0, b"", str(e)


BackendRegistry.register(WinINETBackend)
