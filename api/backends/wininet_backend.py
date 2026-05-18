"""
WinINET HTTP backend using Windows Internet API.
"""
import logging
import os
from typing import Dict, Any, Optional
from urllib.parse import urlparse

from .base_backend import BaseBackend, BackendRegistry
from api.payload_builder import build_request_xml, build_olot_archive, HEADERS as API_HEADERS

logger = logging.getLogger(__name__)

WININET_AVAILABLE = False

try:
    import win32inet
    import win32con
    WININET_AVAILABLE = True
except ImportError:
    pass


# WinINET constants (not defined in pywin32)
INTERNET_OPEN_TYPE_PRECONFIG = 0
INTERNET_OPEN_TYPE_DIRECT = 1
INTERNET_OPEN_TYPE_PROXY = 3


def _parse_proxy_for_wininet(proxy_url: str):
    """
    Parse proxy URL for WinINET API.
    Returns (access_type, proxy_name, proxy_bypass) tuple.
    """
    if not proxy_url:
        return INTERNET_OPEN_TYPE_PRECONFIG, None, None

    parsed = urlparse(proxy_url)
    host = parsed.hostname or ""
    port = parsed.port or 3128
    proxy_name = f"{host}:{port}"
    return INTERNET_OPEN_TYPE_PROXY, proxy_name, ""


class WinINETBackend(BaseBackend):
    """HTTP backend using Windows WinINET API (best for corporate proxy)."""

    name = "wininet"

    def is_available(self) -> bool:
        """Check if WinINET is available (Windows only)."""
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
        """Send POST request using WinINET."""
        if not WININET_AVAILABLE:
            return False, 0, b"", "WinINET not available"

        import win32inet
        import win32con

        logger.info(f"WinINETBackend: POST {url}")

        try:
            boundary = "----FormBoundary" + os.urandom(8).hex()

            body = b''
            for field_name, (filename, content, content_type) in files.items():
                body += f'--{boundary}\r\n'.encode()
                body += f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode()
                body += f'Content-Type: {content_type}\r\n\r\n'.encode()
                body += content + b'\r\n'
            body += f'--{boundary}--\r\n'.encode()

            header_list = ["Content-Type: multipart/form-data; boundary=" + boundary]
            if headers:
                for k, v in headers.items():
                    if k.lower() != 'content-type':
                        header_list.append(f"{k}: {v}")

            flags = win32con.INTERNET_FLAG_RELOAD | win32con.INTERNET_FLAG_NO_CACHE_WRITE

            if not verify:
                flags |= win32con.INTERNET_FLAG_IGNORE_CERTIFICATE_ERRORS

            # Use custom proxy if provided, otherwise fall back to system settings
            access_type = INTERNET_OPEN_TYPE_PRECONFIG
            proxy_name = None
            proxy_bypass = None

            if proxies:
                proxy_url = proxies.get('https') or proxies.get('http')
                if proxy_url:
                    access_type, proxy_name, proxy_bypass = _parse_proxy_for_wininet(proxy_url)
                    logger.info(f"WinINET using proxy: {proxy_url}")

            hInternet = win32inet.InternetOpen(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                access_type,
                proxy_name,
                proxy_bypass,
                0
            )

            if not hInternet:
                return False, 0, b"", "Failed to initialize WinINET"

            try:
                host = url.split('://')[1].split('/')[0]
                path = '/' + url.split('://')[1].split('/', 1)[1] if '/' in url.split('://')[1] else '/'

                hConnection = win32inet.InternetConnect(
                    hInternet,
                    host,
                    None,
                    None,
                    None,
                    win32con.INTERNET_SERVICE_HTTP,
                    0,
                    0
                )

                if not hConnection:
                    return False, 0, b"", "Failed to connect"

                try:
                    hRequest = win32inet.HttpOpenRequest(
                        hConnection,
                        b"POST",
                        path,
                        None,
                        None,
                        ["Accept: */*"],
                        flags,
                        0
                    )

                    if not hRequest:
                        return False, 0, b"", "Failed to open request"

                    success = win32inet.HttpSendRequest(
                        hRequest,
                        "\r\n".join(header_list),
                        len("\r\n".join(header_list)),
                        body,
                        len(body)
                    )

                    if not success:
                        return False, 0, b"", "Failed to send request"

                    status_code = 0
                    try:
                        status_code = win32inet.HttpQueryInfo(
                            hRequest,
                            win32con.HTTP_QUERY_STATUS_CODE | win32con.HTTP_QUERY_FLAG_NUMBER
                        )
                    except Exception as e:
                        logger.debug(f"Could not get status code: {e}")

                    response_bytes = b''
                    while True:
                        buffer, size = win32inet.InternetReadFile(hRequest, 8192)
                        if not buffer or size == 0:
                            break
                        response_bytes += buffer

                    logger.info(f"Response: HTTP {status_code}")
                    return True, status_code, response_bytes, ""

                finally:
                    try:
                        win32inet.InternetCloseHandle(hConnection)
                    except Exception:
                        pass
            finally:
                try:
                    win32inet.InternetCloseHandle(hInternet)
                except Exception:
                    pass

        except ImportError:
            return False, 0, b"", "pywin32 not installed"
        except Exception as e:
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
        """Send GET request using WinINET."""
        if not WININET_AVAILABLE:
            return False, 0, b"", "WinINET not available"

        import win32inet
        import win32con
        import urllib.parse

        logger.info(f"WinINETBackend: GET {url}")

        try:
            if params:
                url_with_params = f"{url}?{urllib.parse.urlencode(params)}"
            else:
                url_with_params = url

            flags = win32con.INTERNET_FLAG_RELOAD

            if not verify:
                flags |= win32con.INTERNET_FLAG_IGNORE_CERTIFICATE_ERRORS

            # Use custom proxy if provided
            access_type = INTERNET_OPEN_TYPE_PRECONFIG
            proxy_name = None
            proxy_bypass = None

            if proxies:
                proxy_url = proxies.get('https') or proxies.get('http')
                if proxy_url:
                    access_type, proxy_name, proxy_bypass = _parse_proxy_for_wininet(proxy_url)

            hInternet = win32inet.InternetOpen(
                "Mozilla/5.0",
                access_type,
                proxy_name,
                proxy_bypass,
                0
            )

            hFile = win32inet.InternetOpenUrl(hInternet, url_with_params, None, flags)

            if not hFile:
                return False, 0, b"", "Failed to open URL"

            try:
                status_code = 0
                try:
                    status_code = win32inet.HttpQueryInfo(
                        hFile,
                        win32con.HTTP_QUERY_STATUS_CODE | win32con.HTTP_QUERY_FLAG_NUMBER
                    )
                except Exception as e:
                    logger.debug(f"Could not get status code: {e}")

                response_bytes = b''
                while True:
                    buffer, size = win32inet.InternetReadFile(hFile, 8192)
                    if not buffer or size == 0:
                        break
                    response_bytes += buffer

                return True, status_code, response_bytes, ""
            finally:
                win32inet.InternetCloseHandle(hFile)
                win32inet.InternetCloseHandle(hInternet)

        except Exception as e:
            logger.error(f"GET error: {e}")
            return False, 0, b"", str(e)


BackendRegistry.register(WinINETBackend)