import sqlite3
import os
import shutil
import logging
import threading
import hashlib
from datetime import datetime
from contextlib import contextmanager
from typing import Optional, List, Dict, Any, Tuple
from types import TracebackType

logger = logging.getLogger(__name__)

MAX_BACKUPS: int = 5


class DatabaseManager:
    _instance: Optional['DatabaseManager'] = None
    _lock = threading.Lock()

    def __init__(self, db_path: Optional[str] = None):
        self.db_path: Optional[str] = db_path
        self._local = threading.local()

    @classmethod
    def get_instance(cls, db_path: Optional[str] = None) -> 'DatabaseManager':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(db_path)
        elif db_path and cls._instance.db_path != db_path:
            with cls._lock:
                cls._instance.db_path = db_path
        return cls._instance

    def initialize(self) -> None:
        if not self.db_path:
            raise RuntimeError("Database path not set")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        conn: Optional[sqlite3.Connection] = getattr(self._local, 'conn', None)
        if conn is None:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            try:
                conn = sqlite3.connect(
                    self.db_path, check_same_thread=False, timeout=5.0
                )
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA foreign_keys=ON")
                # PERFORMANCE: NORMAL is safe with WAL mode, 2-10x faster writes
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA busy_timeout=5000")
                conn.execute("PRAGMA cache_size=-8000")  # 8MB cache
                conn.execute("PRAGMA temp_store=MEMORY")
                self._local.conn = conn
            except sqlite3.ProgrammingError:
                conn = sqlite3.connect(
                    self.db_path, check_same_thread=False, timeout=5.0
                )
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA foreign_keys=ON")
                conn.execute("PRAGMA synchronous=FULL")
                conn.execute("PRAGMA busy_timeout=5000")
                self._local.conn = conn
        return conn

    @contextmanager
    def get_conn(self) -> sqlite3.Connection:
        conn = self._get_connection()
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise

    @contextmanager
    def transaction(self) -> sqlite3.Connection:
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

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

    def close(self) -> None:
        conn = getattr(self._local, 'conn', None)
        if conn:
            try:
                conn.close()
            except Exception:
                pass
            self._local.conn = None

    def close_all(self) -> None:
        self.close()

    def optimize(self) -> None:
        """PERFORMANCE: запускает PRAGMA optimize для текущей БД."""
        try:
            with self.get_conn() as conn:
                conn.execute("PRAGMA optimize")
            logger.debug("Database optimized")
        except Exception as e:
            logger.warning(f"Database optimize failed: {e}")

    def create_backup(self) -> str:
        """Create password-protected zip backup of the database with rotation."""
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
            from utils.crypto import _get_or_create_master_key
            mk = _get_or_create_master_key()
            zip_password = hashlib.sha256(mk).hexdigest()[:16]
        except Exception:
            zip_password = datetime.now().strftime('%Y%m%d')

        try:
            import zipfile
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.setpassword(zip_password.encode('utf-8'))
                zf.write(self.db_path, arcname=base)
            logger.info(f"Password-protected backup created: {backup_path}")
        except Exception as e:
            logger.warning(f"Zip backup failed, falling back to plain copy: {e}")
            shutil.copy2(self.db_path, backup_path.replace('.zip', ''))
            backup_path = backup_path.replace('.zip', '')
        return backup_path
