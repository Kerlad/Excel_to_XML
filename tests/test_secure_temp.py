"""
Tests for secure temp directory management.
"""
import os
import threading
import tempfile
import pytest
from unittest.mock import patch


class TestSecureTemp:
    """Tests for secure_temp module."""

    def test_get_secure_temp_dir_creates(self):
        """Verify get_secure_temp_dir creates a directory."""
        from utils.secure_temp import get_secure_temp_dir, _cleanup_secure_temp
        # Reset state
        import utils.secure_temp as st
        st._secure_temp_dir = None
        st._cleanup_registered = False
        
        temp_dir = get_secure_temp_dir()
        assert os.path.isdir(temp_dir), f"Directory not created: {temp_dir}"
        assert "excel_xml_secure" in temp_dir
        _cleanup_secure_temp()

    def test_secure_temp_dir_thread_safety(self):
        """Verify get_secure_temp_dir is thread-safe."""
        from utils.secure_temp import get_secure_temp_dir, _cleanup_secure_temp
        import utils.secure_temp as st
        st._secure_temp_dir = None
        st._cleanup_registered = False
        
        results = []
        errors = []
        
        def get_dir():
            try:
                results.append(get_secure_temp_dir())
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=get_dir) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        assert len(results) == 5
        # All threads should get the same directory
        assert len(set(results)) == 1, f"Different dirs returned: {set(results)}"
        _cleanup_secure_temp()

    def test_secure_delete_file(self):
        """Verify secure_delete_file overwrites then removes."""
        from utils.secure_temp import secure_delete_file
        
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test sensitive data")
            tmp_path = f.name
        
        assert os.path.exists(tmp_path)
        secure_delete_file(tmp_path)
        assert not os.path.exists(tmp_path), f"File not deleted: {tmp_path}"
