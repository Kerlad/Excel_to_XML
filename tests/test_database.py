import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from db import DatabaseManager, create_schema


@pytest.fixture
def db():
    tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = tmp.name
    tmp.close()
    DatabaseManager._instance = None
    manager = DatabaseManager.get_instance(db_path)
    manager.initialize()
    create_schema()
    yield manager
    manager.close()
    DatabaseManager._instance = None
    os.unlink(db_path)


class TestDatabase:
    def test_create_db(self, db):
        with db.get_conn() as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        assert len(tables) >= 3

    def test_insert_employee(self, db):
        with db.transaction() as conn:
            conn.execute(
                "INSERT INTO employees (snils_enc, snils_hash, last_name_enc, first_name_enc, middle_name_enc) VALUES (?, ?, ?, ?, ?)",
                ("enc_snils", "hash123", "enc_last", "enc_first", "enc_middle")
            )
        row = db.fetchone("SELECT * FROM employees WHERE snils_hash = ?", ("hash123",))
        assert row is not None
        assert row['last_name_enc'] == 'enc_last'

    def test_retrieve_employee(self, db):
        with db.transaction() as conn:
            conn.execute(
                "INSERT INTO employees (snils_enc, snils_hash, last_name_enc, first_name_enc, middle_name_enc) VALUES (?, ?, ?, ?, ?)",
                ("enc_snils2", "hash456", "enc1", "enc2", "enc3")
            )
        row = db.fetchone("SELECT * FROM employees WHERE snils_hash = ?", ("hash456",))
        assert row['last_name_enc'] == 'enc1'
        assert row['first_name_enc'] == 'enc2'
        assert row['middle_name_enc'] == 'enc3'

    def test_encrypted_fields_persist(self, db):
        from utils.crypto import encrypt_value, decrypt_value
        encrypted_name = encrypt_value("Сидоров")
        with db.transaction() as conn:
            conn.execute(
                "INSERT INTO employees (snils_enc, snils_hash, last_name_enc, first_name_enc, middle_name_enc) VALUES (?, ?, ?, ?, ?)",
                ("enc_snils3", "hash789", encrypted_name, "enc_first", "enc_middle")
            )
        row = db.fetchone("SELECT last_name_enc FROM employees WHERE snils_hash = ?", ("hash789",))
        assert decrypt_value(row['last_name_enc']) == "Сидоров"
