"""
pycurl HTTP backend for high-performance transfers.
"""
import logging
import os
import tempfile
from typing import Dict, Any, Optional

from .base_backend import BaseBackend, BackendRegistry

logger = logging.getLogger(__name__)

PYCURL_AVAILABLE = False

try:
    import pycurl
    PYCURL_AVAILABLE = True
except ImportError:
    pass


class PyCurlBackend(BaseBackend):
    """HTTP backend using pycurl library."""

    name = "pycurl"

    def is_available(self) -> bool:
        """Check if pycurl library is available."""
        return PYCURL_AVAILABLE

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
        """Send POST request using pycurl."""
        if not PYCURL_AVAILABLE:
            return False, 0, b"", "pycurl not installed"

        import pycurl
        from io import BytesIO

        logger.info(f"PyCurlBackend: POST {url}")

        temp_files = []

        try:
            buffer = BytesIO()

            c = pycurl.Curl()
            c.setopt(pycurl.URL, url)
            c.setopt(pycurl.POST, True)
            c.setopt(pycurl.WRITEDATA, buffer)
            c.setopt(pycurl.CONNECTTIMEOUT, timeout)
            c.setopt(pycurl.TIMEOUT, timeout)
            c.setopt(pycurl.NOSIGNAL, 1)
            c.setopt(pycurl.USERAGENT, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

            # SSL verification (enabled by default)
            if verify:
                c.setopt(pycurl.SSL_VERIFYPEER, 1)
                c.setopt(pycurl.SSL_VERIFYHOST, 2)
            else:
                c.setopt(pycurl.SSL_VERIFYPEER, 0)
                c.setopt(pycurl.SSL_VERIFYHOST, 0)

            # Proxy settings
            if proxies:
                proxy_url = proxies.get('http') or proxies.get('https', '')
                if proxy_url:
                    c.setopt(pycurl.PROXY, proxy_url)

            # Build multipart form data using temporary files
            post_fields = []
            for field_name, (filename, content, content_type) in files.items():
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.bin')
                tmp.write(content)
                tmp.close()
                temp_files.append(tmp.name)

                post_fields.append((
                    field_name,
                    (pycurl.FORM_FILE, tmp.name),
                    pycurl.FORM_CONTENTTYPE, content_type,
                    pycurl.FORM_FILENAME, filename
                ))

            if post_fields:
                c.setopt(pycurl.HTTPPOST, post_fields)

            # Custom headers
            if headers:
                header_list = [f"{k}: {v}" for k, v in headers.items()]
                c.setopt(pycurl.HTTPHEADER, header_list)

            c.perform()
            status_code = c.getinfo(pycurl.HTTP_CODE)
            c.close()

            response_bytes = buffer.getvalue()
            logger.info(f"Response: HTTP {status_code}")
            return True, status_code, response_bytes, ""

        except pycurl.error as e:
            logger.error(f"pycurl error: {e}")
            return False, 0, b"", str(e)
        except Exception as e:
            logger.error(f"Error: {e}")
            return False, 0, b"", str(e)
        finally:
            for tf in temp_files:
                try:
                    os.unlink(tf)
                except Exception:
                    pass

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
        """Send GET request using pycurl."""
        if not PYCURL_AVAILABLE:
            return False, 0, b"", "pycurl not installed"

        import pycurl
        from io import BytesIO
        import urllib.parse

        logger.info(f"PyCurlBackend: GET {url}")

        try:
            if params:
                url_with_params = f"{url}?{urllib.parse.urlencode(params)}"
            else:
                url_with_params = url

            buffer = BytesIO()

            c = pycurl.Curl()
            c.setopt(pycurl.URL, url_with_params)
            c.setopt(pycurl.WRITEDATA, buffer)
            c.setopt(pycurl.CONNECTTIMEOUT, timeout)
            c.setopt(pycurl.TIMEOUT, timeout)
            c.setopt(pycurl.NOSIGNAL, 1)
            c.setopt(pycurl.USERAGENT, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

            if verify:
                c.setopt(pycurl.SSL_VERIFYPEER, 1)
                c.setopt(pycurl.SSL_VERIFYHOST, 2)
            else:
                c.setopt(pycurl.SSL_VERIFYPEER, 0)
                c.setopt(pycurl.SSL_VERIFYHOST, 0)

            if proxies:
                proxy_url = proxies.get('http') or proxies.get('https', '')
                if proxy_url:
                    c.setopt(pycurl.PROXY, proxy_url)

            if headers:
                header_list = [f"{k}: {v}" for k, v in headers.items()]
                c.setopt(pycurl.HTTPHEADER, header_list)

            c.perform()
            status_code = c.getinfo(pycurl.HTTP_CODE)
            c.close()

            response_bytes = buffer.getvalue()
            logger.info(f"Response: HTTP {status_code}")
            return True, status_code, response_bytes, ""

        except Exception as e:
            logger.error(f"GET error: {e}")
            return False, 0, b"", str(e)


BackendRegistry.register(PyCurlBackend)