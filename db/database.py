import sqlite3
import os
import logging
import threading
import atexit
from contextlib import contextmanager

from utils.crypto import encrypt_file, decrypt_file, backup_file

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
        enc_path = self.db_path + '.enc'
        if os.path.exists(enc_path):
            backup_file(enc_path)
            decrypt_file(enc_path, self.db_path)
            logger.info("DB decrypted from .enc")
        elif not os.path.exists(self.db_path):
            logger.info("No existing DB found, will create new")
        else:
            logger.info("Using existing plaintext DB (no .enc found)")
        atexit.register(self.secure_shutdown)

    def secure_shutdown(self):
        if not self.db_path or not os.path.exists(self.db_path):
            return
        try:
            self.close_all()
            encrypt_file(self.db_path)
            logger.info("DB encrypted on shutdown")
        except Exception as e:
            logger.error(f"Failed to encrypt DB on shutdown: {e}")

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            if not self.db_path:
                raise RuntimeError("Database path not set")
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA foreign_keys=ON")
        return self._local.conn

    @contextmanager
    def get_conn(self):
        conn = self._get_connection()
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        finally:
            pass

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
            return conn.execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: tuple = ()) -> list:
        with self.get_conn() as conn:
            return conn.execute(sql, params).fetchall()

    def close(self):
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None

    def close_all(self):
        self.close()
