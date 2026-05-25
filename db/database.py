import sqlite3
import os
import shutil
import logging
import threading
import hashlib
import time
import atexit
from datetime import datetime
from contextlib import contextmanager
from typing import Optional, List, Dict, Any

from utils.audit import log_audit

logger = logging.getLogger(__name__)

MAX_BACKUPS: int = 5
_BUSY_RETRIES: int = 3
_BUSY_RETRY_DELAY: float = 0.1


class DatabaseLockError(RuntimeError):
    pass


class DatabaseManager:
    _instance: Optional['DatabaseManager'] = None
    _lock = threading.Lock()
    _thread_connections: Dict[int, sqlite3.Connection] = {}
    _connections_lock = threading.Lock()

    def __init__(self, db_path: Optional[str] = None):
        self.db_path: Optional[str] = db_path
        self._local = threading.local()

    @classmethod
    def get_instance(cls, db_path: Optional[str] = None) -> 'DatabaseManager':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(db_path)
                    atexit.register(cls.close_all)
        elif db_path and cls._instance.db_path != db_path:
            with cls._lock:
                cls._instance.db_path = db_path
        return cls._instance

    def initialize(self) -> None:
        if not self.db_path:
            raise RuntimeError("Database path not set")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._check_integrity()

    def _check_integrity(self) -> None:
        try:
            conn = self._get_connection()
            cursor = conn.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            if result and result[0] != 'ok':
                logger.critical("Database integrity check FAILED: %s", result[0])
                log_audit("SECURITY_WARNING", f"Database integrity check failed: {result[0]}")
            else:
                logger.info("Database integrity check: OK")
        except sqlite3.Error as e:
            logger.warning("Database integrity check error: %s", e)

    def _get_connection(self) -> sqlite3.Connection:
        conn: Optional[sqlite3.Connection] = getattr(self._local, 'conn', None)
        if conn is None:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            conn = sqlite3.connect(
                self.db_path, check_same_thread=False, timeout=5.0
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("PRAGMA cache_size=-8000")
            conn.execute("PRAGMA temp_store=MEMORY")
            self._local.conn = conn
            tid = threading.get_ident()
            with DatabaseManager._connections_lock:
                DatabaseManager._thread_connections[tid] = conn
            logger.debug(f"Connection opened for thread {tid}")
        return conn

    @contextmanager
    def get_conn(self) -> sqlite3.Connection:
        conn = self._get_connection()
        try:
            yield conn
        except sqlite3.DatabaseError:
            conn.rollback()
            logger.error("Database error in get_conn, rolling back")
            raise
        conn.commit()

    @contextmanager
    def transaction(self) -> sqlite3.Connection:
        conn = self._get_connection()
        for attempt in range(_BUSY_RETRIES):
            try:
                conn.execute("BEGIN IMMEDIATE")
                yield conn
                conn.commit()
                return
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < _BUSY_RETRIES - 1:
                    logger.warning(
                        "Database locked, retrying (%d/%d): %s",
                        attempt + 1, _BUSY_RETRIES, e,
                    )
                    time.sleep(_BUSY_RETRY_DELAY)
                else:
                    conn.rollback()
                    logger.error("Transaction rollback after operational error: %s", e)
                    raise DatabaseLockError(
                        f"Transaction failed after {_BUSY_RETRIES} retries: {e}"
                    )
                continue
            except sqlite3.DatabaseError:
                conn.rollback()
                logger.error("Transaction rollback after database error")
                raise
            except Exception:
                conn.rollback()
                raise
        conn.rollback()
        raise DatabaseLockError("Transaction failed after retries")

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self.get_conn() as conn:
            return conn.execute(sql, params)

    def executemany(self, sql: str, seq: List[tuple]) -> sqlite3.Cursor:
        with self.get_conn() as conn:
            return conn.executemany(sql, seq)

    def fetchone(self, sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        with self.get_conn() as conn:
            row = conn.execute(sql, params).fetchone()
            return dict(row) if row else None

    def fetchall(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        with self.get_conn() as conn:
            return [dict(row) for row in conn.execute(sql, params).fetchall()]

    @classmethod
    def close_thread_connection(cls) -> None:
        inst = cls._instance
        if inst is None:
            return
        conn: Optional[sqlite3.Connection] = getattr(inst._local, 'conn', None)
        if conn is None:
            return
        tid = threading.get_ident()
        try:
            conn.close()
            logger.debug("Connection closed for thread %d", tid)
        except sqlite3.Error as e:
            logger.warning("Error closing thread %d connection: %s", tid, e)
        inst._local.conn = None
        with cls._connections_lock:
            cls._thread_connections.pop(tid, None)

    def close(self) -> None:
        DatabaseManager.close_thread_connection()

    @classmethod
    def close_all(cls) -> None:
        logger.info("Closing all database connections...")
        with cls._connections_lock:
            for tid, conn in list(cls._thread_connections.items()):
                try:
                    conn.close()
                    logger.debug("Connection closed for thread %d", tid)
                except sqlite3.Error as e:
                    logger.warning("Error closing thread %d connection: %s", tid, e)
            cls._thread_connections.clear()
        inst = cls._instance
        if inst is not None:
            inst._local.conn = None
        logger.info("All database connections closed")

    def optimize(self) -> None:
        try:
            with self.get_conn() as conn:
                conn.execute("PRAGMA optimize")
            logger.debug("Database optimized")
        except sqlite3.Error as e:
            logger.warning("Database optimize failed: %s", e)

    def secure_vacuum(self) -> None:
        try:
            with self.get_conn() as conn:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            import sqlite3 as _sqlite3
            vacuum_conn = _sqlite3.connect(self.db_path, timeout=30.0)
            vacuum_conn.execute("VACUUM")
            vacuum_conn.close()
            logger.info("Database VACUUM completed after PD deletion")
            log_audit("SECURITY_WARNING",
                      "VACUUM executed — freed pages overwritten after PD deletion")
        except Exception as e:
            logger.error("VACUUM failed: %s", e)

    def create_backup(self) -> str:
        # NOTE: If master key is rotated, old backups will be unrecoverable.
        # Always create a new backup immediately after key rotation.
        if not self.db_path or not os.path.exists(self.db_path):
            return ""
        backup_dir = os.path.join(os.path.dirname(self.db_path), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        base = os.path.basename(self.db_path)
        for num in range(MAX_BACKUPS - 1, 0, -1):
            old = os.path.join(backup_dir, f"{base}.backup.{num}.zip")
            new = os.path.join(backup_dir, f"{base}.backup.{num + 1}.zip")
            if os.path.exists(old):
                if os.path.exists(new):
                    os.remove(new)
                shutil.move(old, new)
        backup_path = os.path.join(backup_dir, f"{base}.backup.1.zip")

        try:
            from utils.crypto import get_key_fingerprint
            zip_password = get_key_fingerprint()
        except (OSError, ValueError) as e:
            logger.warning("Cannot derive backup password from master key: %s", e)
            from utils.crypto import _get_backup_password
            try:
                zip_password = _get_backup_password()
            except Exception:
                import secrets
                zip_password = secrets.token_hex(32)
                logger.warning(
                    "Cannot derive backup password from master key. "
                    "Using random password. This backup cannot be restored without the original master key."
                )

        try:
            import zipfile
            try:
                import pyzipper
                with pyzipper.AESZipFile(backup_path, 'w', compression=pyzipper.ZIP_DEFLATED,
                                          encryption=pyzipper.WZ_AES) as zf:
                    zf.setpassword(zip_password.encode('utf-8'))
                    zf.write(self.db_path, arcname=base)
            except ImportError:
                with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    zf.setpassword(zip_password.encode('utf-8'))
                    zf.write(self.db_path, arcname=base)
            logger.info("Password-protected backup created: %s", backup_path)
        except (zipfile.BadZipFile, OSError) as e:
            logger.warning("Zip backup failed, falling back to plain copy: %s", e)
            shutil.copy2(self.db_path, backup_path.replace('.zip', ''))
            backup_path = backup_path.replace('.zip', '')
        if os.path.exists(backup_path):
            size_mb = os.path.getsize(backup_path) / (1024 * 1024)
            log_audit("BACKUP", f"backup_path={backup_path}, size={size_mb:.1f}MB")
        return backup_path
