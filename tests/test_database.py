import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from db.database import DatabaseManager
from db.schema import create_schema
from utils.crypto import _get_backup_password


@pytest.fixture(autouse=True)
def setup_db():
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    db = DatabaseManager.get_instance(db_path)
    db.initialize()
    create_schema()
    yield db
    db.close_all()
    if os.path.exists(db_path):
        os.remove(db_path)
    db_dir = os.path.dirname(db_path)
    backup_dir = os.path.join(db_dir, 'backups')
    if os.path.exists(backup_dir):
        import shutil
        shutil.rmtree(backup_dir, ignore_errors=True)


class TestDatabaseManager:
    def test_tables_created(self):
        db = DatabaseManager.get_instance()
        tables = db.fetchall("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        names = [t['name'] for t in tables]
        assert 'employees' in names
        assert 'employee_programs' in names
        assert 'workers_data' in names
        assert 'exam_journal' in names

    def test_transaction_commit(self):
        db = DatabaseManager.get_instance()
        with db.transaction() as conn:
            conn.execute("INSERT INTO employees (snils_enc, snils_hash) VALUES (?, ?)",
                         ("test_enc", "test_hash"))
        result = db.fetchone("SELECT snils_enc FROM employees WHERE snils_hash = ?", ("test_hash",))
        assert result and result['snils_enc'] == 'test_enc'

    def test_transaction_rollback_on_error(self):
        db = DatabaseManager.get_instance()
        try:
            with db.transaction() as conn:
                conn.execute("INSERT INTO employees (snils_enc, snils_hash) VALUES (?, ?)",
                             ("should_rollback", "rollback_hash"))
                raise RuntimeError("force rollback")
        except RuntimeError:
            pass
        count = db.fetchone("SELECT COUNT(*) as cnt FROM employees WHERE snils_hash = ?", ("rollback_hash",))['cnt']
        assert count == 0

    def test_execute_and_fetchone(self):
        db = DatabaseManager.get_instance()
        db.execute("INSERT INTO employees (snils_enc, snils_hash) VALUES (?, ?)",
                   ("enc1", "hash1"))
        row = db.fetchone("SELECT * FROM employees WHERE snils_hash = ?", ("hash1",))
        assert row is not None
        assert row['snils_enc'] == 'enc1'

    def test_fetchall(self):
        db = DatabaseManager.get_instance()
        for i in range(3):
            db.execute("INSERT INTO employees (snils_enc, snils_hash) VALUES (?, ?)",
                       (f"enc{i}", f"hash{i}"))
        rows = db.fetchall("SELECT * FROM employees ORDER BY id")
        assert len(rows) == 3

    def test_singleton_pattern(self):
        db1 = DatabaseManager.get_instance()
        db2 = DatabaseManager.get_instance()
        assert db1 is db2

    def test_optimize(self):
        db = DatabaseManager.get_instance()
        db.optimize()

    def test_backup_creation(self):
        db = DatabaseManager.get_instance()
        db.execute("INSERT INTO employees (snils_enc, snils_hash) VALUES (?, ?)",
                   ("backup_test", "backup_hash"))
        path = db.create_backup()
        assert path != ''
        assert os.path.exists(path)

    def test_get_conn_context(self):
        db = DatabaseManager.get_instance()
        with db.get_conn() as conn:
            cur = conn.execute("SELECT 1 as val")
            row = cur.fetchone()
            assert row['val'] == 1

    def test_executemany(self):
        db = DatabaseManager.get_instance()
        data = [("e1", "h1"), ("e2", "h2"), ("e3", "h3")]
        db2 = DatabaseManager.get_instance()
        db2.executemany(
            "INSERT INTO employees (snils_enc, snils_hash) VALUES (?, ?)", data
        )
        assert db2.fetchone("SELECT COUNT(*) as cnt FROM employees")['cnt'] == 3

    def test_backup_password_length(self):
        pwd = _get_backup_password()
        assert len(pwd) == 64
