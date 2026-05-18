"""
Requests HTTP backend with Windows Integrated Authentication support.
"""
import logging
import ssl
from typing import Dict, Any, Optional

from .base_backend import BaseBackend, BackendRegistry

logger = logging.getLogger(__name__)

# Import proxy manager
import utils.proxy_manager as proxy_manager

# Check for authentication libraries
NTLM_AVAILABLE = False
KERBEROS_AVAILABLE = False
NegotiateAuth = None

try:
    from requests_negotiate_sspi import HttpNegotiateAuth
    NegotiateAuth = HttpNegotiateAuth
    KERBEROS_AVAILABLE = True
except ImportError:
    pass

try:
    from requests_ntlm import HttpNtlmAuth
    NTLM_AVAILABLE = True
except ImportError:
    pass


# TLS version mapping (using TLSVersion enum for SSLContext.minimum/maximum_version)
TLS_VERSION_MAP = {
    "1.0": ssl.TLSVersion.TLSv1,
    "1.1": ssl.TLSVersion.TLSv1_1,
    "1.2": ssl.TLSVersion.TLSv1_2,
    "1.3": getattr(ssl.TLSVersion, "TLSv1_3", ssl.TLSVersion.TLSv1_2),
}


def _create_ssl_context(
    verify: bool = False,
    tls_min_version: Optional[str] = None,
    tls_max_version: Optional[str] = None,
    ciphers: Optional[str] = None,
) -> ssl.SSLContext:
    """Create SSL context with custom TLS configuration."""
    import ssl

    if not verify:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    else:
        ctx = ssl.create_default_context()

    if tls_min_version:
        min_ver = TLS_VERSION_MAP.get(tls_min_version)
        if min_ver:
            ctx.minimum_version = min_ver

    if tls_max_version:
        max_ver = TLS_VERSION_MAP.get(tls_max_version)
        if max_ver:
            ctx.maximum_version = max_ver

    if ciphers:
        ctx.set_ciphers(ciphers)

    return ctx


class RequestsBackend(BaseBackend):
    """HTTP backend using requests library with Negotiate/NTLM support."""
    
    name = "requests"
    
    def is_available(self) -> bool:
        """Check if requests library is available."""
        try:
            import requests
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
        auth=None,
        **kwargs
    ) -> tuple[bool, int, bytes, str]:
        """
        Send POST request using requests library.
        
        Args:
            url: Target URL
            files: Files dict for multipart body
            headers: Additional HTTP headers
            timeout: Request timeout in seconds
            verify: SSL verification flag
            proxies: Proxy configuration dict
            auth: Authentication handler
            tls_min_version: Minimum TLS version ("1.0", "1.1", "1.2", "1.3")
            tls_max_version: Maximum TLS version ("1.0", "1.1", "1.2", "1.3")
            ciphers: OpenSSL cipher suite string
            
        Returns:
            Tuple of (success, status_code, response_bytes, error_message)
        """
        import requests
        
        logger.info(f"RequestsBackend: POST {url}")
        if proxies:
            logger.info(f"Using proxies: {proxies}")

        logger.info(f"Files to send: {list(files.keys())}")
        logger.info(f"Headers: {headers}")
        logger.info(f"Verify: {verify}")

        try:
            session, auth_method = self._create_session(
                proxies,
                tls_min_version=kwargs.pop("tls_min_version", None),
                tls_max_version=kwargs.pop("tls_max_version", None),
                ciphers=kwargs.pop("ciphers", None),
                verify=verify,
            )

            if auth_method:
                logger.info(f"Using auth method: {auth_method}")

            response = session.post(
                url,
                files=files,
                headers=headers,
                timeout=timeout,
                verify=verify,
                **kwargs
            )

            logger.info(f"Response: HTTP {response.status_code}, content_len={len(response.content)}")
            logger.info(f"Response text[:300]: {response.text[:300]}")

            session.close()

            return True, response.status_code, response.content, ""
            
        except requests.exceptions.Timeout:
            logger.error("Request timeout")
            return False, 0, b"", "Таймаут соединения"
        except requests.exceptions.ProxyError as e:
            logger.error(f"Proxy error: {e}")
            return False, 0, b"", f"Ошибка прокси: {e}"
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            return False, 0, b"", f"Ошибка соединения: {e}"
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return False, 0, b"", str(e)
    
    def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None,
        timeout: int = 60,
        verify: bool = True,
        proxies: Optional[Dict[str, str]] = None,
        auth=None,
        **kwargs
    ) -> tuple[bool, int, bytes, str]:
        """
        Send GET request using requests library.
        """
        import requests
        
        logger.info(f"RequestsBackend: GET {url}")
        
        try:
            session, auth_method = self._create_session(
                proxies,
                tls_min_version=kwargs.pop("tls_min_version", None),
                tls_max_version=kwargs.pop("tls_max_version", None),
                ciphers=kwargs.pop("ciphers", None),
                verify=verify,
            )
            
            response = session.get(
                url,
                headers=headers,
                params=params,
                timeout=timeout,
                verify=verify,
                **kwargs
            )
            
            session.close()
            
            logger.info(f"Response: HTTP {response.status_code}")
            return True, response.status_code, response.content, ""
            
        except Exception as e:
            logger.error(f"GET error: {e}")
            return False, 0, b"", str(e)
    
    def _create_session(self, proxies: Optional[Dict[str, str]] = None,
                        tls_min_version: Optional[str] = None,
                        tls_max_version: Optional[str] = None,
                        ciphers: Optional[str] = None,
                        verify: bool = True):
        """
        Create requests session with proper proxy authentication.
        
        Args:
            proxies: Proxy configuration dict
            tls_min_version: Minimum TLS protocol version
            tls_max_version: Maximum TLS protocol version  
            ciphers: OpenSSL cipher suite string
            verify: SSL verification flag
            
        Returns:
            Tuple of (session, auth_method)
        """
        from requests.adapters import HTTPAdapter
        
        session = requests.Session()
        
        if proxies:
            session.proxies = proxies
        
        # Configure custom SSL context if TLS settings specified
        if tls_min_version or tls_max_version or ciphers:
            ctx = _create_ssl_context(
                verify=verify,
                tls_min_version=tls_min_version,
                tls_max_version=tls_max_version,
                ciphers=ciphers,
            )
            
            class CustomSSLAdapter(HTTPAdapter):
                def init_poolmanager(self, *args, **kwargs):
                    kwargs['ssl_context'] = ctx
                    return super().init_poolmanager(*args, **kwargs)
                
                def send(self, request, **kwargs):
                    kwargs.setdefault('verify', verify)
                    return super().send(request, **kwargs)
            
            session.mount('https://', CustomSSLAdapter())
        
        auth_method = None
        
        # Try Negotiate first (preferred for corporate proxies)
        if KERBEROS_AVAILABLE and NegotiateAuth:
            try:
                session.auth = NegotiateAuth()
                auth_method = "Negotiate"
                logger.info("Using Negotiate (Kerberos) authentication")
            except Exception as e:
                logger.warning(f"Failed to setup Negotiate: {e}")
        
        # Fallback to NTLM
        if not auth_method and NTLM_AVAILABLE:
            try:
                from requests_ntlm import HttpNtlmAuth
                session.auth = HttpNtlmAuth("", "")  # Use current Windows credentials
                auth_method = "NTLM"
                logger.info("Using NTLM authentication")
            except Exception as e:
                logger.warning(f"Failed to setup NTLM: {e}")
        
        return session, auth_method


# Register backend
BackendRegistry.register(RequestsBackend)