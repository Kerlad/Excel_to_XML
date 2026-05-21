"""
Base backend interface for HTTP transport.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseBackend(ABC):
    """Abstract base class for HTTP transport backends."""
    
    name: str = "base"
    
    @abstractmethod
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
        raise NotImplementedError
    
    @abstractmethod
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
        """
        Send HTTP GET request.
        
        Args:
            url: Target URL
            headers: HTTP headers
            params: Query parameters
            timeout: Request timeout in seconds
            verify: SSL verification flag
            proxies: Proxy configuration dict
            **kwargs: Backend-specific options
        
        Returns:
            Tuple of (success, status_code, response_bytes, error_message)
        """
        raise NotImplementedError
    
    def is_available(self) -> bool:
        """
        Check if backend is available (dependencies installed).
        
        Returns:
            True if backend can be used
        """
        return True


class BackendRegistry:
    """Registry for available backends."""
    
    _backends: Dict[str, type] = {}
    
    @classmethod
    def register(cls, backend_class: type):
        """Register a backend class."""
        if issubclass(backend_class, BaseBackend):
            cls._backends[backend_class.name] = backend_class
    
    @classmethod
    def get_backend(cls, name: str) -> Optional[type]:
        """Get backend class by name."""
        return cls._backends.get(name)
    
    @classmethod
    def list_backends(cls) -> list:
        """List all registered backend names."""
        return list(cls._backends.keys())
    
    @classmethod
    def get_available_backends(cls) -> list:
        """List backends that are available (dependencies installed)."""
        available = []
        for name, backend_class in cls._backends.items():
            try:
                instance = backend_class()
                if instance.is_available():
                    available.append(name)
            except (ImportError, RuntimeError):
                continue
        return available