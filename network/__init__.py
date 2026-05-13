"""
Network module - Windows Integrated Authentication support.
"""
from .client import (
    NegotiateSession,
    create_negotiate_session,
    test_external_access,
    get_network_diagnostics,
    NetworkStatus,
    get_windows_proxy,
    get_windows_user,
    KERBEROS_AVAILABLE
)

__all__ = [
    'NegotiateSession',
    'create_negotiate_session',
    'test_external_access',
    'get_network_diagnostics',
    'NetworkStatus',
    'get_windows_proxy',
    'get_windows_user',
    'KERBEROS_AVAILABLE'
]