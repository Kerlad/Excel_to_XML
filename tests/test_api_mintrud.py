import sys, os, tempfile, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import patch, MagicMock, ANY


class TestMintrudClientMocked:
    """Tests MintrudClient using mocked HTTP backends."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.api_key = "abcdef1234567890abcdef1234567890"
        self.temp_xml = tempfile.NamedTemporaryFile(suffix='.xml', delete=False, mode='w', encoding='utf-8')
        self.temp_xml.write('<Data/>')
        self.temp_xml.close()

    def teardown_method(self):
        if os.path.exists(self.temp_xml.name):
            os.remove(self.temp_xml.name)

    def _make_backend_mock(self, success=True, status_code=200, response_body=b"", error=""):
        mock_backend = MagicMock()
        mock_backend.name = "test_backend"
        mock_backend.is_available.return_value = True
        mock_backend.send.return_value = (success, status_code, response_body, error)
        return mock_backend

    def test_send_xml_success(self):
        from api.mintrud_api import MintrudClient
        from api.response_parser import parse_send_response

        response_xml = b'''<?xml version="1.0"?><Response><SetId>SET-TEST-123</SetId><SendEducatedPerson>true</SendEducatedPerson><Message>Success</Message></Response>'''
        mock_backend = self._make_backend_mock(success=True, status_code=200, response_body=response_xml)

        client = MintrudClient(backend="auto")
        client._init_backend = MagicMock()
        client._backend = mock_backend
        client._get_backend_fallback_list = MagicMock(return_value=[(mock_backend, "test_backend")])
        client._get_proxies = MagicMock(return_value=None)
        client._get_verify = MagicMock(return_value=True)

        result = client.send_xml(self.api_key, self.temp_xml.name)
        assert result['success'] is True
        assert result['set_id'] == 'SET-TEST-123'
        assert result['send_educated_person'] is True

    def test_send_xml_invalid_key(self):
        from api.mintrud_api import MintrudClient
        client = MintrudClient(backend="requests")
        result = client.send_xml("short", self.temp_xml.name)
        assert result['success'] is False
        assert '32' in result.get('error', '')

    def test_send_xml_file_not_found(self):
        from api.mintrud_api import MintrudClient
        client = MintrudClient(backend="requests")
        result = client.send_xml(self.api_key, "nonexistent.xml")
        assert result['success'] is False
        assert 'не найден' in result.get('error', '').lower()

    def test_send_xml_backend_failure(self):
        from api.mintrud_api import MintrudClient

        mock_backend = self._make_backend_mock(success=False, status_code=0, response_body=b"", error="Connection refused")

        client = MintrudClient(backend="auto")
        client._init_backend = MagicMock()
        client._backend = mock_backend
        client._get_backend_fallback_list = MagicMock(return_value=[(mock_backend, "test_backend")])

        result = client.send_xml(self.api_key, self.temp_xml.name)
        assert result['success'] is False

    def test_send_xml_ssl_fallback(self):
        from api.mintrud_api import MintrudClient

        ssl_backend = self._make_backend_mock(success=False, status_code=0, response_body=b"", error="SSL: certificate verify failed")
        good_backend = self._make_backend_mock(success=True, status_code=200,
                                               response_body=b'<?xml version="1.0"?><Response><SetId>FALLBACK-SET</SetId></Response>')

        client = MintrudClient(backend="auto")
        client._init_backend = MagicMock()
        client._backend = ssl_backend
        client._get_backend_fallback_list = MagicMock(return_value=[(ssl_backend, "ssl_bad"), (good_backend, "good")])
        client._get_proxies = MagicMock(return_value=None)
        client._get_verify = MagicMock(return_value=True)

        result = client.send_xml(self.api_key, self.temp_xml.name)
        assert result['success'] is True
        assert result['set_id'] == 'FALLBACK-SET'

    def test_send_xml_signed_success(self):
        from api.mintrud_api import MintrudClient

        with tempfile.NamedTemporaryFile(suffix='.sig', delete=False) as f:
            f.write(b'sig')
            sig_path = f.name
        try:
            response_xml = b'''<?xml version="1.0"?><Response><SetId>SIGNED-SET</SetId></Response>'''
            mock_backend = self._make_backend_mock(success=True, status_code=200, response_body=response_xml)

            client = MintrudClient(backend="auto")
            client._init_backend = MagicMock()
            client._backend = mock_backend
            client._get_backend_fallback_list = MagicMock(return_value=[(mock_backend, "test_backend")])
            client._get_proxies = MagicMock(return_value=None)
            client._get_verify = MagicMock(return_value=True)

            result = client.send_xml_signed(self.api_key, self.temp_xml.name, sig_path)
            assert result['success'] is True
            assert result['set_id'] == 'SIGNED-SET'
        finally:
            os.remove(sig_path)

    def test_send_xml_signed_missing_sig(self):
        from api.mintrud_api import MintrudClient
        client = MintrudClient(backend="requests")
        result = client.send_xml_signed(self.api_key, self.temp_xml.name, "nonexistent.sig")
        assert result['success'] is False
        assert 'sig' in result.get('error', '').lower() or 'подпис' in result.get('error', '').lower() or 'файл' in result.get('error', '').lower()

    def test_query_by_setid_success(self):
        from api.mintrud_api import MintrudClient

        response_xml = b'''<?xml version="1.0"?><EducatedPersons><RegistryRecord baseNo="BN-001"><Worker><LastName>Test</LastName><FirstName>User</FirstName><Snils>123-456-789 00</Snils><Position>Engineer</Position><EmployerInn>7701</EmployerInn><EmployerTitle>LLC</EmployerTitle></Worker><Test isPassed="true" learnProgramId="1"><LearnProgramTitle>First Aid</LearnProgramTitle><ProtocolNumber>P-1</ProtocolNumber><Date>2025-09-25</Date></Test></RegistryRecord></EducatedPersons>'''
        mock_backend = self._make_backend_mock(success=True, status_code=200, response_body=b'HTTP...')

        client = MintrudClient(backend="auto")
        client._init_backend = MagicMock()

        def try_backends(api_key, xml_content, url):
            from api.response_parser import parse_setid_response
            return {"success": True, "status_code": 200, "response_bytes": response_xml}

        client._try_backends = try_backends

        result = client.query_by_setid(self.api_key, "SET-001")
        assert result['success'] is True
        assert len(result['records']) == 1

    def test_query_by_setid_empty_setid(self):
        from api.mintrud_api import MintrudClient
        client = MintrudClient(backend="requests")
        result = client.query_by_setid(self.api_key, "")
        assert result['success'] is False
        assert 'SetId' in result.get('error', '')

    def test_query_by_snils_success(self):
        from api.mintrud_api import MintrudClient

        response_xml = b'''<?xml version="1.0"?><EducatedPersons><RegistryRecord baseNo="BN-001"><Worker><LastName>Petrov</LastName><FirstName>Petr</FirstName><Snils>123-456-789 00</Snils></Worker><Test isPassed="true" learnProgramId="2"><Date>2025-09-25</Date></Test></RegistryRecord></EducatedPersons>'''
        client = MintrudClient(backend="auto")
        client._init_backend = MagicMock()
        client._try_backends = MagicMock(return_value={"success": True, "status_code": 200, "response_bytes": response_xml})

        result = client.query_by_snils(self.api_key, "123-456-789 00")
        assert result['success'] is True
        assert len(result['records']) == 1

    def test_query_by_snils_invalid_format(self):
        from api.mintrud_api import MintrudClient
        client = MintrudClient(backend="requests")
        result = client.query_by_snils(self.api_key, "123")
        assert result['success'] is False
        assert '11' in result.get('error', '')


class TestApiKeyManagement:
    def test_validate_api_key_valid(self):
        from api.mintrud_api import validate_api_key
        ok, msg = validate_api_key("a" * 32)
        assert ok
        assert msg == ""

    def test_validate_api_key_empty(self):
        from api.mintrud_api import validate_api_key
        ok, msg = validate_api_key("")
        assert not ok
        assert 'не введён' in msg

    def test_validate_api_key_wrong_length(self):
        from api.mintrud_api import validate_api_key
        ok, msg = validate_api_key("short")
        assert not ok
        assert '32' in msg or 'длина' in msg.lower()

    def test_save_and_load_api_key(self):
        from api.mintrud_api import save_api_key, load_api_key
        with tempfile.TemporaryDirectory() as tmpdir:
            success, msg = save_api_key("test_key_1234567890123456", tmpdir)
            assert success
            assert os.path.exists(os.path.join(tmpdir, "api_key.json"))
            loaded = load_api_key(tmpdir)
            assert loaded == "test_key_1234567890123456"

    def test_load_api_key_missing(self):
        from api.mintrud_api import load_api_key
        with tempfile.TemporaryDirectory() as tmpdir:
            loaded = load_api_key(tmpdir)
            assert loaded is None

    def test_ssl_error_detection(self):
        from api.mintrud_api import _is_ssl_error
        assert _is_ssl_error("SSL certificate verify failed")
        assert _is_ssl_error("TLS handshake failed")
        assert _is_ssl_error("certificate_verify_failed")
        assert not _is_ssl_error("Connection refused")
        assert not _is_ssl_error("")


class TestValidateApiKeyRemote:
    """Tests validate_api_key_remote (local length-only check)."""

    def _call_validate(self, api_key="abcdef1234567890abcdef1234567890", proxy_settings=None):
        from api.mintrud_api import validate_api_key_remote
        return validate_api_key_remote(api_key, proxy_settings)

    def test_remote_valid_key(self):
        """32-char key → valid."""
        ok, msg = self._call_validate("a" * 32)
        assert ok

    def test_remote_empty_key(self):
        """Empty key → invalid."""
        ok, msg = self._call_validate("")
        assert not ok

    def test_remote_short_key(self):
        """Short key → invalid."""
        ok, msg = self._call_validate("short")
        assert not ok

    def test_remote_long_key(self):
        """33-char key → invalid."""
        ok, msg = self._call_validate("a" * 33)
        assert not ok

    def test_remote_proxy_settings_ignored(self):
        """proxy_settings parameter is accepted but ignored."""
        ok, msg = self._call_validate("a" * 32, proxy_settings={'mode': 'auto'})
        assert ok


class TestBackendRegistry:
    def test_registry_has_backends(self):
        from api.backends import BackendRegistry
        names = BackendRegistry.list_backends()
        assert 'requests' in names

    def test_get_available_backends(self):
        from api.mintrud_api import get_available_backends
        backends = get_available_backends()
        assert 'requests' in backends


class TestLegacyFunctions:
    def test_push_xml(self):
        from api.mintrud_api import push_xml
        result = push_xml("short", "nonexistent.xml")
        assert 'success' in result

    def test_get_by_set_id(self):
        from api.mintrud_api import get_by_set_id
        result = get_by_set_id("test_key_1234567890123456", "")
        assert 'success' in result

    def test_get_by_snils(self):
        from api.mintrud_api import get_by_snils
        result = get_by_snils("test_key_1234567890123456", "123")
        assert 'success' in result


class TestExportRecords:
    def test_export_records_to_xlsx(self):
        from api.mintrud_api import export_records_to_xlsx
        records = [{"baseNo": "001", "LastName": "Test"}]
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            path = f.name
        try:
            success, msg = export_records_to_xlsx(records, path)
            assert success
            assert os.path.exists(path)
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_export_records_to_xlsx_empty(self):
        from api.mintrud_api import export_records_to_xlsx
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            path = f.name
        try:
            success, msg = export_records_to_xlsx([], path)
            assert success
        finally:
            if os.path.exists(path):
                os.remove(path)
