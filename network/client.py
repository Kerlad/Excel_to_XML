"""
Network module for Windows Integrated Authentication (Negotiate/Kerberos).
Provides HTTP client with automatic proxy detection and Windows SSO support.

Requirements:
- requests
- requests-negotiate-sspi
- pywin32 (for Windows API access)
"""
import os
import sys
import logging
from typing import Optional, Dict, Tuple
from enum import Enum

# Network diagnostics
class NetworkStatus(Enum):
    SUCCESS = "SUCCESS"
    PROXY_AUTH_FAILED = "PROXY_AUTH_FAILED"
    TIMEOUT = "TIMEOUT"
    NETWORK_ERROR = "NETWORK_ERROR"
    NEGOTIATE_NOT_AVAILABLE = "NEGOTIATE_NOT_AVAILABLE"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"

# Create logs directory
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "log")
os.makedirs(LOG_DIR, exist_ok=True)

# Network logger
network_logger = logging.getLogger("network")
network_logger.setLevel(logging.INFO)

# File handler for network logs
network_handler = logging.FileHandler(os.path.join(LOG_DIR, "network.log"), encoding='utf-8')
network_handler.setLevel(logging.INFO)
network_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
network_handler.setFormatter(network_formatter)
network_logger.addHandler(network_handler)

# Check for required libraries
KERBEROS_AVAILABLE = False
NegotiateAuth = None

try:
    from requests_negotiate_sspi import HttpNegotiateAuth
    NegotiateAuth = HttpNegotiateAuth
    KERBEROS_AVAILABLE = True
    network_logger.info("Negotiate/SSPI library available")
except ImportError as e:
    network_logger.error(f"requests-negotiate-sspi not available: {e}")

# Import requests
import requests


def get_windows_proxy() -> Optional[str]:
    """
    Detect Windows system proxy from registry.
    Returns proxy URL or None.
    """
    try:
        import winreg
        reg_path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
        
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path) as key:
            proxy_enabled, _ = winreg.QueryValueEx(key, "ProxyEnable")
            if not proxy_enabled:
                network_logger.info("Windows proxy disabled")
                return None
            
            proxy_server, _ = winreg.QueryValueEx(key, "ProxyServer")
            if not proxy_server:
                network_logger.info("No proxy server configured in Windows")
                return None
            
            # Handle different formats
            if "=" in proxy_server:
                for part in proxy_server.split(";"):
                    if part.startswith("https="):
                        addr = part.split("=", 1)[1]
                        if addr:
                            if not addr.startswith("http"):
                                addr = f"https://{addr}"
                            return addr
                    elif part.startswith("http="):
                        addr = part.split("=", 1)[1]
                        if addr:
                            if not addr.startswith("http"):
                                addr = f"http://{addr}"
                            return addr
                # Return first available if no https/http specified
                for part in proxy_server.split(";"):
                    if "=" in part:
                        addr = part.split("=", 1)[1]
                        if addr:
                            if not addr.startswith("http"):
                                return f"http://{addr}"
                            return addr
                return None
            else:
                if not proxy_server.startswith("http"):
                    return f"http://{proxy_server}"
                return proxy_server
    except Exception as e:
        network_logger.error(f"Error detecting Windows proxy: {e}")
        return None


def get_windows_user() -> Optional[str]:
    """Get current Windows username."""
    try:
        username = os.environ.get('USERNAME', '')
        domain = os.environ.get('USERDOMAIN', '')
        if username:
            if domain:
                return f"{domain}\\{username}"
            return username
    except Exception as e:
        network_logger.warning(f"Could not get Windows user: {e}")
    return None


def test_external_access(url: str = "https://edu.rosmintrud.ru", 
                         timeout: int = 30) -> Tuple[NetworkStatus, str]:
    """
    Test external network access using Windows Integrated Authentication.
    
    Returns:
        Tuple of (NetworkStatus, message)
    """
    network_logger.info(f"Testing external access to {url}")
    
    # Check if Negotiate is available
    if not KERBEROS_AVAILABLE:
        error_msg = "requests-negotiate-sspi not installed"
        network_logger.error(error_msg)
        return NetworkStatus.NEGOTIATE_NOT_AVAILABLE, error_msg
    
    # Detect proxy
    proxy_url = get_windows_proxy()
    if proxy_url:
        network_logger.info(f"Using proxy: {proxy_url}")
    else:
        network_logger.info("No proxy detected, using direct connection")
    
    # Get Windows user
    windows_user = get_windows_user()
    network_logger.info(f"Windows user: {windows_user}")
    
    # Create session with Negotiate auth
    session = requests.Session()
    session.trust_env = False  # Don't use system environment variables
    
    # Configure proxy
    proxies = None
    if proxy_url:
        proxies = {"http": proxy_url, "https": proxy_url}
    
    # Configure Negotiate authentication
    auth = NegotiateAuth()
    network_logger.info("Using Negotiate authentication (Windows SSO)")
    
    try:
        network_logger.info(f"GET {url}")
        response = session.get(
            url,
            proxies=proxies,
            auth=auth,
            timeout=timeout,
            verify=False  # Disable SSL verification for corporate proxies with SSL inspection
        )
        
        network_logger.info(f"Response: {response.status_code}")
        
        if response.status_code in [200, 201]:
            network_logger.info("Connection successful")
            return NetworkStatus.SUCCESS, f"HTTP {response.status_code} - Connection successful"
        elif response.status_code == 407:
            network_logger.error("Proxy authentication failed (407)")
            return NetworkStatus.PROXY_AUTH_FAILED, "Proxy authentication failed (407)"
        elif response.status_code == 401:
            # 401 means we reached the server but auth is needed
            network_logger.warning("Server requires authentication (401)")
            return NetworkStatus.SUCCESS, f"HTTP {response.status_code} - Server reached"
        else:
            network_logger.warning(f"Unexpected status: {response.status_code}")
            return NetworkStatus.SUCCESS, f"HTTP {response.status_code}"
            
    except requests.exceptions.Timeout:
        network_logger.error("Request timeout")
        return NetworkStatus.TIMEOUT, "Connection timeout"
    except requests.exceptions.ProxyError as e:
        error_str = str(e)
        network_logger.error(f"Proxy error: {error_str}")
        if "407" in error_str:
            return NetworkStatus.PROXY_AUTH_FAILED, "Proxy authentication failed (407)"
        return NetworkStatus.PROXY_AUTH_FAILED, f"Proxy error: {error_str}"
    except requests.exceptions.ConnectionError as e:
        network_logger.error(f"Connection error: {e}")
        return NetworkStatus.NETWORK_ERROR, f"Connection error: {str(e)}"
    except Exception as e:
        network_logger.error(f"Unexpected error: {type(e).__name__}: {e}")
        return NetworkStatus.UNKNOWN_ERROR, f"Error: {str(e)}"


class NegotiateSession:
    """
    HTTP session with Windows Integrated Authentication (Negotiate/Kerberos).
    """
    
    def __init__(self, timeout: int = 60):
        """
        Initialize session with Windows SSO.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.trust_env = False  # Disable environment proxy detection
        
        # Disable SSL verification for corporate proxies with SSL inspection
        self.session.verify = False
        
        # Detect proxy
        self.proxy_url = get_windows_proxy()
        if self.proxy_url:
            self.session.proxies = {"http": self.proxy_url, "https": self.proxy_url}
            network_logger.info(f"Using proxy: {self.proxy_url}")
        else:
            self.session.proxies = None
            network_logger.info("No proxy detected")
        
        # Configure Negotiate authentication
        if KERBEROS_AVAILABLE and NegotiateAuth:
            self.auth = NegotiateAuth()
            network_logger.info("Negotiate authentication configured")
        else:
            self.auth = None
            network_logger.warning("Negotiate not available")
        
        # Windows user
        self.windows_user = get_windows_user()
        network_logger.info(f"Windows user: {self.windows_user}")
    
    def get(self, url: str, **kwargs) -> requests.Response:
        """Send GET request."""
        kwargs.setdefault('timeout', self.timeout)
        kwargs.setdefault('auth', self.auth)
        kwargs.setdefault('verify', False)
        
        network_logger.info(f"GET {url}")
        
        response = self.session.get(url, **kwargs)
        network_logger.info(f"GET {url} -> {response.status_code}")
        return response
    
    def post(self, url: str, **kwargs) -> requests.Response:
        """Send POST request."""
        kwargs.setdefault('timeout', self.timeout)
        kwargs.setdefault('auth', self.auth)
        kwargs.setdefault('verify', False)
        
        network_logger.info(f"POST {url}")
        
        response = self.session.post(url, **kwargs)
        network_logger.info(f"POST {url} -> {response.status_code}")
        return response
    
    def close(self):
        """Close session."""
        self.session.close()


def create_negotiate_session() -> Tuple[Optional[NegotiateSession], str]:
    """
    Factory function to create session with Negotiate auth.
    
    Returns:
        Tuple of (NegotiateSession, status_message)
    """
    network_logger.info("Creating Negotiate session")
    
    if not KERBEROS_AVAILABLE:
        return None, "requests-negotiate-sspi not installed"
    
    try:
        session = NegotiateSession()
        return session, "OK"
    except Exception as e:
        network_logger.error(f"Failed to create session: {e}")
        return None, str(e)


def get_network_diagnostics() -> Dict[str, any]:
    """
    Get current network diagnostics information.
    
    Returns:
        Dict with diagnostics data
    """
    diagnostics = {
        "negotiate_available": KERBEROS_AVAILABLE,
        "detected_proxy": get_windows_proxy(),
        "auth_method": "Negotiate" if KERBEROS_AVAILABLE else "None",
        "windows_user": get_windows_user(),
        "windows_user_authenticated": KERBEROS_AVAILABLE
    }
    
    network_logger.info(f"Diagnostics: {diagnostics}")
    return diagnostics


# Suppress SSL warnings for corporate proxies
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    pass


if __name__ == "__main__":
    print("Network Diagnostics:")
    print("-" * 40)
    diag = get_network_diagnostics()
    for key, value in diag.items():
        print(f"  {key}: {value}")
    
    print("\nTesting external access to edu.rosmintrud.ru...")
    status, message = test_external_access("https://edu.rosmintrud.ru", timeout=30)
    print(f"  Status: {status.value}")
    print(f"  Message: {message}")