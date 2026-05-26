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


SCHANNEL_ERROR_MARKERS = [
    "schannel", "10013", "0x80090326", "sec_e_illegal_message",
    "tls", "ssl", "certificate",
]


def _is_schannel_error(error_message: str) -> bool:
    if not error_message:
        return False
    msg = error_message.lower()
    return any(marker in msg for marker in SCHANNEL_ERROR_MARKERS)


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

        # SECURITY_FLAG must be set BEFORE Open() for some WinHTTP versions
        # Set it both before and after Open() for reliability
        if not verify:
            for _attempt in range(2):
                try:
                    http.Option[WINHTTP_OPTION_SECURITY_FLAGS] = SECURITY_FLAG_IGNORE_ALL_CERT_ERRORS
                except (AttributeError, TypeError):
                    pass
            logger.warning(
                "WinINET: TLS certificate verification disabled "
                "(corporate SSL inspection mode)"
            )

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
        raw_bytes = http.ResponseBody
        response_bytes = bytes(raw_bytes) if raw_bytes is not None else b""

        if status_code >= 400:
            err_text = "HTTP %d" % status_code
            try:
                status_text = str(http.StatusText)
                if status_text:
                    err_text += ": " + status_text
            except (AttributeError, TypeError):
                pass
            return False, status_code, response_bytes, err_text

        return True, status_code, response_bytes, ""

    except AttributeError as e:
        logger.error("WinHTTP COM error: %s", str(e))
        return False, 0, b"", str(e)
    except OSError as e:
        err_msg = str(e)
        logger.error("WinHTTP network error: %s", err_msg)
        return False, 0, b"", err_msg
    except ValueError as e:
        logger.error("WinHTTP value error: %s", str(e))
        return False, 0, b"", str(e)
    except Exception as e:
        err_msg = str(e)
        logger.error("WinHTTP unexpected error: %s", err_msg)
        return False, 0, b"", err_msg


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

            body_parts = []
            for field_name, (filename, content, content_type) in files.items():
                part = b''
                part += b'--' + boundary.encode() + b'\r\n'
                cd_header = 'Content-Disposition: form-data; name="%s"; filename="%s"\r\n' % (field_name, filename)
                part += cd_header.encode()
                part += ('Content-Type: %s\r\n\r\n' % content_type).encode()
                part += content.encode() if isinstance(content, str) else content
                part += b'\r\n'
                body_parts.append(part)

            body = b''.join(body_parts)
            body += b'--' + boundary.encode() + b'--\r\n'

            req_headers = {"Content-Type": "multipart/form-data; boundary=%s" % boundary}
            if headers:
                for k, v in headers.items():
                    if k.lower() != 'content-type':
                        req_headers[k] = v

            return _make_request("POST", url, body, req_headers, timeout, verify, proxies)

        except (ValueError, OSError, TypeError) as e:
            logger.error("WinINET error: %s", str(e))
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
        except (ValueError, OSError, TypeError) as e:
            logger.error("WinINET error: %s", str(e))
            return False, 0, b"", str(e)


BackendRegistry.register(WinINETBackend)
