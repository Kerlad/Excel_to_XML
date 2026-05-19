import sqlite3
import os
import logging
import threading
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseManager:
    _instance = None
    _lock = threading.Lock()

    def __init__(self, db_path: str = None):
        self.db_path = db_path
        self._local = threading.local()

    @classmethod
    def get_instance(cls, db_path: str = None) -> 'DatabaseManager':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(db_path)
        elif db_path and cls._instance.db_path != db_path:
            with cls._lock:
                cls._instance.db_path = db_path
        return cls._instance

    def initialize(self):
        if not self.db_path:
            raise RuntimeError("Database path not set")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        conn = getattr(self._local, 'conn', None)
        if conn is None:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            conn = sqlite3.connect(
                self.db_path, check_same_thread=False, timeout=5.0
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn = conn
        else:
            try:
                conn.execute("SELECT 1")
            except sqlite3.ProgrammingError:
                conn = sqlite3.connect(
                    self.db_path, check_same_thread=False, timeout=5.0
                )
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA foreign_keys=ON")
                self._local.conn = conn
        return conn

    @contextmanager
    def get_conn(self):
        conn = self._get_connection()
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise

    @contextmanager
    def transaction(self):
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

    def executemany(self, sql: str, seq: list) -> sqlite3.Cursor:
        with self.get_conn() as conn:
            return conn.executemany(sql, seq)

    def fetchone(self, sql: str, params: tuple = ()):
        with self.get_conn() as conn:
            row = conn.execute(sql, params).fetchone()
            return dict(row) if row else None

    def fetchall(self, sql: str, params: tuple = ()) -> list:
        with self.get_conn() as conn:
            return [dict(row) for row in conn.execute(sql, params).fetchall()]

    def close(self):
        conn = getattr(self._local, 'conn', None)
        if conn:
            try:
                conn.close()
            except Exception:
                pass
            self._local.conn = None

    def close_all(self):
        self.close()
