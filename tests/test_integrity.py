"""
Tests for database integrity and backup integrity.
"""
import os
import sqlite3
import tempfile
import pytest


class TestDatabaseIntegrity:
    """Tests for database integrity features."""

    def test_integrity_check_ok(self):
        """PRAGMA integrity_check returns 'ok' for valid database."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, val TEXT)")
            conn.execute("INSERT INTO test VALUES (1, 'hello')")
            conn.commit()
            
            cursor = conn.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            assert result[0] == 'ok', f"Integrity check failed: {result}"
            conn.close()
        finally:
            os.unlink(db_path)

    def test_integrity_check_corrupt(self):
        """Corrupted database should fail integrity check."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
            f.write(b"Not a valid SQLite database")
        
        conn = None
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            assert result[0] != 'ok', "Expected corruption to be detected"
        except sqlite3.DatabaseError:
            pass  # Expected - database is corrupt
        finally:
            if conn:
                try:
                    conn.close()
                except sqlite3.Error:
                    pass
            try:
                os.unlink(db_path)
            except PermissionError:
                pass

    def test_backup_integrity(self):
        """Verify backup integrity check works."""
        from utils.crypto import verify_backup_integrity
        
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as f:
            import zipfile
            with zipfile.ZipFile(f.name, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('test.txt', 'test data')
        
        try:
            ok, msg = verify_backup_integrity(f.name)
            assert not ok, f"Should fail - no master.key in zip: {msg}"
        finally:
            os.unlink(f.name)
