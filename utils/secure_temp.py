"""
Secure temporary file management for ISPDn.
- Isolated temp directory per process
- Automatic cleanup on process exit
- Secure deletion of PDn-containing temp files
- OS-level temp file access restrictions
"""
import os
import shutil
import logging
import atexit
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_secure_temp_dir: Optional[str] = None
_cleanup_registered = False


def get_secure_temp_dir() -> str:
    """Get or create a secure per-process temp directory with restricted permissions."""
    global _secure_temp_dir, _cleanup_registered
    if _secure_temp_dir is not None and os.path.exists(_secure_temp_dir):
        return _secure_temp_dir

    base = tempfile.gettempdir()
    import uuid
    _secure_temp_dir = os.path.join(base, f"excel_xml_secure_{uuid.uuid4().hex[:12]}")

    os.makedirs(_secure_temp_dir, exist_ok=True)

    try:
        import win32security
        import win32api
        import ntsecuritycon as con
        username = win32api.GetUserName()
        sid, _, _ = win32security.LookupAccountName(None, username)
        sd = win32security.SECURITY_DESCRIPTOR()
        dacl = win32security.ACL()
        dacl.AddAccessAllowedAce(
            win32security.ACL_REVISION,
            con.FILE_GENERIC_READ | con.FILE_GENERIC_WRITE | con.DELETE,
            sid
        )
        sd.SetSecurityDescriptorDacl(1, dacl, 0)
        win32security.SetFileSecurity(
            _secure_temp_dir,
            win32security.DACL_SECURITY_INFORMATION,
            sd
        )
    except ImportError:
        # Restrict access via os.chmod where possible
        try:
            os.chmod(_secure_temp_dir, 0o700)
        except (OSError, PermissionError):
            pass
    except OSError:
        pass

    if not _cleanup_registered:
        atexit.register(_cleanup_secure_temp)
        _cleanup_registered = True

    logger.debug("Secure temp directory created: %s", _secure_temp_dir)
    return _secure_temp_dir


def create_secure_temp_file(suffix: str = ".tmp", prefix: str = "tmp_") -> str:
    """Create a secure temp file in the isolated temp directory."""
    temp_dir = get_secure_temp_dir()
    fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=temp_dir)
    os.close(fd)

    try:
        import win32security
        import win32api
        import ntsecuritycon as con
        username = win32api.GetUserName()
        sid, _, _ = win32security.LookupAccountName(None, username)
        sd = win32security.SECURITY_DESCRIPTOR()
        dacl = win32security.ACL()
        dacl.AddAccessAllowedAce(
            win32security.ACL_REVISION,
            con.FILE_GENERIC_READ | con.FILE_GENERIC_WRITE | con.DELETE,
            sid
        )
        sd.SetSecurityDescriptorDacl(1, dacl, 0)
        win32security.SetFileSecurity(
            path,
            win32security.DACL_SECURITY_INFORMATION,
            sd
        )
    except (ImportError, OSError):
        pass

    return path


def secure_delete_file(file_path: str, passes: int = 3) -> None:
    """Securely delete a file by overwriting before deletion."""
    if not file_path or not os.path.exists(file_path):
        return
    try:
        file_size = os.path.getsize(file_path)
        if file_size > 0:
            with open(file_path, 'wb') as f:
                for _ in range(passes):
                    f.seek(0)
                    f.write(os.urandom(file_size))
                    f.flush()
                    os.fsync(f.fileno())
        os.remove(file_path)
        logger.debug("Securely deleted: %s", file_path)
    except OSError as e:
        logger.warning("Secure deletion failed for %s: %s", file_path, e)
        try:
            os.remove(file_path)
        except OSError:
            pass


def _cleanup_secure_temp() -> None:
    """Cleanup secure temp directory at process exit."""
    global _secure_temp_dir
    if _secure_temp_dir and os.path.exists(_secure_temp_dir):
        try:
            for root, dirs, files in os.walk(_secure_temp_dir, topdown=False):
                for name in files:
                    secure_delete_file(os.path.join(root, name))
                for name in dirs:
                    try:
                        os.rmdir(os.path.join(root, name))
                    except OSError:
                        pass
            os.rmdir(_secure_temp_dir)
            logger.debug("Secure temp directory cleaned up: %s", _secure_temp_dir)
        except OSError as e:
            logger.warning("Secure temp cleanup failed: %s", e)
    _secure_temp_dir = None
