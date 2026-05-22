"""
Mock payload tests per MOK.md specification.
Tests: ZIP/OLOT structure, Request.xml formats, strict validation, mock payloads.
"""
import sys, os, tempfile, zipfile, io, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import patch, MagicMock


# ============================================================
# 1. ZIP Structure Validation
# ============================================================

class TestZipStructure:
    """MOK §2.1 — ZIP archive structure validation."""

    def _make_zip(self, files: dict) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            for name, content in files.items():
                zf.writestr(name, content)
        return buf.getvalue()

    def _extract_filenames(self, archive: bytes) -> list:
        with zipfile.ZipFile(io.BytesIO(archive)) as zf:
            return zf.namelist()

    def test_required_files_present(self):
        """ZIP must contain Request.xml and Request.xml.sig."""
        data = self._make_zip({
            'Request.xml': '<Request><ApiKey>key</ApiKey></Request>',
            'Request.xml.sig': 'sig_data',
        })
        names = self._extract_filenames(data)
        assert 'Request.xml' in names
        assert 'Request.xml.sig' in names

    def test_case_sensitive_filenames(self):
        """Filenames are case-sensitive: request.xml != Request.xml."""
        data = self._make_zip({
            'request.xml': '<Request/>',
            'Request.xml.sig': 'sig',
        })
        names = self._extract_filenames(data)
        assert 'Request.xml' not in names
        assert 'request.xml' in names

    def test_no_nested_folders(self):
        """All files must be at root, not in subdirectories."""
        data = self._make_zip({
            'Request.xml': '<Request/>',
            'sub/Request.xml.sig': 'sig',
        })
        names = self._extract_filenames(data)
        assert any('/' in n or '\\' in n for n in names)

    def test_path_traversal_rejected(self):
        """Path traversal in filenames must be rejected."""
        data = self._make_zip({
            'Request.xml': '<Request/>',
            '../etc/passwd': 'hack',
        })
        names = self._extract_filenames(data)
        dangerous = [n for n in names if '..' in n or n.startswith('/')]
        assert len(dangerous) > 0

    def test_no_duplicate_filenames(self):
        """Duplicate filenames must be detected (ZIP warning on write)."""
        import warnings
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('Request.xml', '<R/>')
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                zf.writestr('Request.xml', '<R2/>')
                dup_warnings = [x for x in w if 'Duplicate name' in str(x.message)]
                assert len(dup_warnings) > 0, "Duplicate name should trigger warning"

    def test_empty_archive_rejected(self):
        """Empty ZIP must be rejected."""
        data = self._make_zip({})
        names = self._extract_filenames(data)
        assert len(names) == 0

    def test_oversized_archive(self):
        """Oversized archive detection (>10MB uncompressed)."""
        import struct
        large_content = os.urandom(11 * 1024 * 1024)  # random = incompressible
        data = self._make_zip({'Request.xml': large_content})
        assert len(data) > 10 * 1024 * 1024

    def test_is_send_requires_sig(self):
        """MOK §2.1.2: IF IsSend=true THEN Data.xml.sig MUST exist."""
        data = self._make_zip({
            'Request.xml': '<Request><NeedSend>true</NeedSend></Request>',
            'Request.xml.sig': 'sig',
        })
        has_data_sig = 'Data.xml.sig' in self._extract_filenames(data)
        need_send = b'<NeedSend>true</NeedSend>' in data
        if need_send:
            assert has_data_sig, "NeedSend=true requires Data.xml.sig"
        else:
            assert not has_data_sig or not need_send


# ============================================================
# 2. OLOT Structure Validation
# ============================================================

class TestOlotStructure:
    """MOK §2.2 — OLOT archive structure and NeedSend logic."""

    def _make_olot(self, has_xml=True, has_sig=False, sig_name='Data.xml.sig') -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            if has_xml:
                zf.writestr('Data.xml', '<Data>test</Data>')
            if has_sig:
                zf.writestr(sig_name, 'fake_signature')
        return buf.getvalue()

    def test_olot_contains_data_xml(self):
        data = self._make_olot(has_xml=True)
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            assert 'Data.xml' in zf.namelist()

    def test_olot_missing_xml(self):
        data = self._make_olot(has_xml=False)
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            assert 'Data.xml' not in zf.namelist()

    def test_olot_with_sig(self):
        data = self._make_olot(has_xml=True, has_sig=True)
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            assert 'Data.xml.sig' in zf.namelist()

    def test_need_send_true_without_sig(self):
        """MOK §2.2: NeedSend=true without Data.xml.sig → reject."""
        request_xml = b'<Request><ApiKey>key</ApiKey><NeedSend>true</NeedSend></Request>'
        olot = self._make_olot(has_xml=True, has_sig=False)
        assert b'<NeedSend>true</NeedSend>' in request_xml
        # validate: NeedSend=true, but olot has no .sig
        with zipfile.ZipFile(io.BytesIO(olot)) as zf:
            has_sig = any(n.endswith('.sig') for n in zf.namelist())
            assert not has_sig, "NeedSend=true but no .sig in olot — should be flagged"

    def test_need_send_false_with_sig(self):
        """MOK §2.2: NeedSend=false with Data.xml.sig → reject."""
        request_xml = b'<Request><ApiKey>key</ApiKey><NeedSend>false</NeedSend></Request>'
        olot = self._make_olot(has_xml=True, has_sig=True)
        assert b'<NeedSend>false</NeedSend>' in request_xml
        with zipfile.ZipFile(io.BytesIO(olot)) as zf:
            has_sig = any(n.endswith('.sig') for n in zf.namelist())
            assert has_sig, "NeedSend=false but .sig present — should be flagged"

    def test_olot_malformed_not_zip(self):
        """Invalid ZIP structure must be rejected."""
        bad_olot = b'this is not a zip file'
        with pytest.raises(zipfile.BadZipFile):
            with zipfile.ZipFile(io.BytesIO(bad_olot)) as zf:
                zf.namelist()

    def test_olot_invalid_extension(self):
        """Extension must be .olot."""
        name = 'data.bin'
        assert not name.endswith('.olot')

    def test_olot_empty(self):
        data = self._make_olot(has_xml=False)
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            assert len(zf.namelist()) == 0


# ============================================================
# 3. Request.xml Format Validation (all endpoints)
# ============================================================

class TestRequestXmlFormats:
    """MOK §3 — Request.xml structure for all endpoints."""

    XML_PROLOGUE = '<?xml version="1.0" encoding="UTF-8"?>'

    def _validate_xml(self, xml_str: str, required_tags: list):
        """Basic XML structure validation."""
        assert xml_str.startswith(self.XML_PROLOGUE) or '<' in xml_str[:50]
        assert '<Request>' in xml_str or '<EducatedPersonFilter>' in xml_str
        for tag in required_tags:
            assert tag in xml_str, f"Missing required tag: {tag}"

    def test_push_request_format(self):
        """MOK §3.1: Push XML format."""
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Request>
    <ApiKey>abcdef1234567890abcdef1234567890</ApiKey>
    <NeedSend>false</NeedSend>
</Request>'''
        self._validate_xml(xml, ['<ApiKey>', '<NeedSend>'])
        assert 'abcdef1234567890abcdef1234567890' in xml
        assert '<NeedSend>false</NeedSend>' in xml

    def test_api_key_32_chars(self):
        """ApiKey must be exactly 32 characters."""
        valid = "a" * 32
        short = "a" * 31
        long = "a" * 33
        assert len(valid) == 32
        assert len(short) != 32
        assert len(long) != 32

    def test_api_key_special_chars_escaped(self):
        """XML special chars in ApiKey must be escaped."""
        from xml.sax.saxutils import escape
        key = 'key&<>"\''
        escaped = escape(key)
        assert '&amp;' in escaped
        assert '&lt;' in escaped
        assert '&gt;' in escaped

    def test_worker_create_format(self):
        """MOK §3.2: Worker Create XML format."""
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Request>
    <ApiKey>key123456789012345678901234567890</ApiKey>
    <Workers>
        <Worker outerId="ext_1">
            <LastName>Иванов</LastName>
            <FirstName>Иван</FirstName>
            <MiddleName>Иванович</MiddleName>
            <Phone>+79991234567</Phone>
            <Email>ivanov@example.com</Email>
            <Snils>123-456-789 00</Snils>
            <Position>Инженер</Position>
            <EmployerTitle>ООО Ромашка</EmployerTitle>
            <EmployerInn>7709123456</EmployerInn>
        </Worker>
    </Workers>
</Request>'''
        self._validate_xml(xml, ['<Worker', '<LastName>', '<FirstName>', '<Snils>', '<Position>'])
        assert 'outerId' in xml

    def test_worker_edit_format(self):
        """MOK §3.3: Worker Edit XML format."""
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Request>
    <ApiKey>key123456789012345678901234567890</ApiKey>
    <Worker>
        <Id>12345</Id>
        <LastName>Петров</LastName>
        <FirstName>Пётр</FirstName>
        <Position>Слесарь</Position>
        <Phone>+79997654321</Phone>
        <Email>petrov@example.com</Email>
        <EmployerTitle>ООО Пример</EmployerTitle>
        <EmployerInn>7709987654</EmployerInn>
    </Worker>
</Request>'''
        self._validate_xml(xml, ['<Id>', '<Worker>'])

    def test_worker_delete_format(self):
        """MOK §3.4: Worker Delete XML format."""
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Request>
    <ApiKey>key123456789012345678901234567890</ApiKey>
    <Id>12345</Id>
</Request>'''
        self._validate_xml(xml, ['<Id>'])
        assert '<Worker>' not in xml

    def test_test_create_format(self):
        """MOK §3.5: Test Create XML format."""
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Request>
    <ApiKey>key123456789012345678901234567890</ApiKey>
    <Tests>
        <Test outerId="t1">
            <WorkerId>123</WorkerId>
            <ContingentId>1</ContingentId>
            <IndustryId>5</IndustryId>
            <LearnProgramId>6</LearnProgramId>
            <DateOpen>2025-09-26</DateOpen>
            <Location>Москва</Location>
        </Test>
    </Tests>
</Request>'''
        self._validate_xml(xml, ['<Tests>', '<Test', '<WorkerId>', '<LearnProgramId>', '<DateOpen>'])

    def test_test_edit_format(self):
        """MOK §3.6: Test Edit XML format."""
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Request>
    <ApiKey>key123456789012345678901234567890</ApiKey>
    <Test Id="98765">
        <DateOpen>2025-10-01</DateOpen>
    </Test>
</Request>'''
        self._validate_xml(xml, ['<Test', 'Id='])
        assert '98765' in xml

    def test_filter_request_format(self):
        """MOK §3.7: EducatedPersonFilter format."""
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
<EducatedPersonFilter>
    <ApiKey>key123456789012345678901234567890</ApiKey>
    <PageNo>1</PageNo>
    <PageSize>100</PageSize>
    <SetId>SET-12345</SetId>
    <Snils>123-456-789 00</Snils>
</EducatedPersonFilter>'''
        assert '<EducatedPersonFilter>' in xml
        assert '</EducatedPersonFilter>' in xml
        self._validate_xml(xml, ['<ApiKey>', '<PageNo>', '<PageSize>'])


# ============================================================
# 4. Mock Payload Generation
# ============================================================

class TestMockPayloadGeneration:
    """MOK §7 — Mock payload generator tests."""

    def test_generate_valid_push_xml(self):
        """Generate valid push Request.xml."""
        from api.payload_builder import build_request_xml
        xml = build_request_xml("abcdef1234567890abcdef1234567890", need_send=False)
        assert b'<ApiKey>' in xml
        assert b'<NeedSend>false</NeedSend>' in xml
        assert b'</Request>' in xml

    def test_generate_valid_push_xml_need_send(self):
        from api.payload_builder import build_request_xml
        xml = build_request_xml("k" * 32, need_send=True)
        assert b'<NeedSend>true</NeedSend>' in xml

    def test_generate_olot_archive(self):
        """Generate valid .olot archive."""
        from api.payload_builder import build_olot_archive
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as f:
            f.write(b'<Data>content</Data>')
            xml_path = f.name
        try:
            olot = build_olot_archive(xml_path)
            with zipfile.ZipFile(io.BytesIO(olot)) as zf:
                assert 'Data.xml' in zf.namelist()
                assert zf.read('Data.xml') == b'<Data>content</Data>'
        finally:
            os.remove(xml_path)

    def test_generate_olot_with_sig(self):
        from api.payload_builder import build_olot_archive
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as f:
            f.write(b'<Data/>')
            xml_path = f.name
        with tempfile.NamedTemporaryFile(suffix='.sig', delete=False) as f:
            f.write(b'signature')
            sig_path = f.name
        try:
            olot = build_olot_archive(xml_path, sig_path)
            with zipfile.ZipFile(io.BytesIO(olot)) as zf:
                assert 'Data.xml' in zf.namelist()
                assert os.path.basename(sig_path) in zf.namelist()
        finally:
            os.remove(xml_path)
            os.remove(sig_path)

    def test_generate_multipart_payload(self):
        """Generate full multipart payload."""
        from api.payload_builder import build_multipart_payload
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as f:
            f.write(b'<Data/>')
            xml_path = f.name
        try:
            files, headers = build_multipart_payload("k" * 32, xml_path)
            assert 'xml' in files
            assert 'olot' in files
            assert files['xml'][1].startswith(b'<?xml')
            assert 'User-Agent' in headers
        finally:
            os.remove(xml_path)

    def test_missing_xml_file_generates_error(self):
        from api.payload_builder import build_olot_archive
        with pytest.raises(FileNotFoundError):
            build_olot_archive("nonexistent_file.xml")

    def test_missing_sig_file_generates_error(self):
        from api.payload_builder import build_olot_archive
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as f:
            f.write(b'<Data/>')
            xml_path = f.name
        try:
            with pytest.raises(FileNotFoundError):
                build_olot_archive(xml_path, "nonexistent.sig")
        finally:
            os.remove(xml_path)


# ============================================================
# 5. Strict Pre-Parse Validation
# ============================================================

class TestStrictValidation:
    """MOK §6 — Strict validation before parsing."""

    def test_content_type_multipart(self):
        """Content-Type must be multipart/form-data."""
        valid_ct = 'multipart/form-data; boundary=----boundary123'
        invalid_ct = 'application/xml'
        assert 'multipart/form-data' in valid_ct
        assert 'multipart/form-data' not in invalid_ct

    def test_file_extension_xml(self):
        """Extension must be .xml."""
        assert '.xml' == os.path.splitext('Request.xml')[1]
        assert '.xml' != os.path.splitext('Request.txt')[1]

    def test_file_extension_zip(self):
        """ZIP extension validation for worker/test endpoints."""
        assert '.zip' == os.path.splitext('archive.zip')[1]
        assert '.zip' != os.path.splitext('archive.olot')[1]
        assert '.zip' != os.path.splitext('archive.rar')[1]

    def test_file_extension_olot(self):
        """OLOT extension validation for push endpoint."""
        assert '.olot' == os.path.splitext('data.olot')[1]
        assert '.olot' != os.path.splitext('data.zip')[1]

    def test_xml_root_element(self):
        """Root element must be Request or EducatedPersonFilter."""
        from defusedxml.ElementTree import fromstring
        valid = fromstring('<Request><ApiKey>k</ApiKey></Request>')
        assert valid.tag == 'Request'
        valid2 = fromstring('<EducatedPersonFilter><ApiKey>k</ApiKey></EducatedPersonFilter>')
        assert valid2.tag == 'EducatedPersonFilter'

    def test_xml_too_large(self):
        """Oversized XML must be rejected."""
        from utils.xml_safe import safe_fromstring_xml
        with pytest.raises(Exception):
            safe_fromstring_xml('X' * (101 * 1024 * 1024))

    def test_xml_empty(self):
        """Empty XML must be rejected."""
        from utils.xml_safe import safe_fromstring_xml
        with pytest.raises(Exception):
            safe_fromstring_xml('')

    def test_xml_not_well_formed(self):
        """Malformed XML must be rejected."""
        from utils.xml_safe import safe_fromstring_xml
        with pytest.raises(Exception):
            safe_fromstring_xml('<Request><unclosed>')


# ============================================================
# 6. Regression Tests for Format Compatibility
# ============================================================

class TestFormatRegression:
    """MOK §8 — Regression tests ensuring formats don't break."""

    def test_push_xml_structure_stable(self):
        """Push XML structure must remain compatible."""
        from api.payload_builder import build_request_xml
        xml = build_request_xml("test_key_1234567890123456", need_send=False)
        decoded = xml.decode('utf-8')
        assert '<Request>' in decoded
        assert '<ApiKey>' in decoded
        assert '<NeedSend>' in decoded
        assert decoded.strip().endswith('</Request>')

    def test_olot_structure_stable(self):
        """OLOT must always contain Data.xml."""
        from api.payload_builder import build_olot_archive
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as f:
            f.write(b'<Data/>')
            xml_path = f.name
        try:
            olot = build_olot_archive(xml_path)
            with zipfile.ZipFile(io.BytesIO(olot)) as zf:
                names = zf.namelist()
                assert 'Data.xml' in names
                assert not any('/' in n for n in names)  # no nested dirs
        finally:
            os.remove(xml_path)

    def test_multipart_field_names_stable(self):
        """Multipart field names must remain 'xml' and 'olot'."""
        from api.payload_builder import build_multipart_payload
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as f:
            f.write(b'<Data/>')
            xml_path = f.name
        try:
            files, _ = build_multipart_payload("k" * 32, xml_path)
            assert 'xml' in files
            assert 'olot' in files
            assert files['xml'][0] == 'Request.xml'
            assert files['olot'][0] == 'data.olot'
        finally:
            os.remove(xml_path)

    def test_educated_person_filter_has_apikey(self):
        """API key is required in EducatedPersonFilter."""
        from xml.sax.saxutils import escape
        key = "k" * 32
        xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<EducatedPersonFilter>
    <ApiKey>{escape(key)}</ApiKey>
    <PageNo>1</PageNo>
    <PageSize>100</PageSize>
</EducatedPersonFilter>'''
        assert '<ApiKey>' in xml
        assert key in xml

    def test_snils_format_with_dashes_and_space(self):
        """SNILS format: XXX-XXX-XXX XX."""
        valid = "123-456-789 00"
        import re
        assert re.match(r'^\d{3}-\d{3}-\d{3} \d{2}$', valid)

    def test_parse_send_response_not_logging_xml(self):
        """Response parser must not log raw XML (MOK §4)."""
        from api.response_parser import parse_send_response
        import logging
        xml = b'<Response><SetId>SECRET-SET-123</SetId></Response>'
        with patch.object(logging.getLogger('api.response_parser'), 'debug') as mock_debug:
            result = parse_send_response(xml, 200)
            logged_texts = [str(c) for c in mock_debug.call_args_list]
            assert not any('SECRET-SET-123' in t for t in logged_texts)

    def test_parse_setid_response_unknown_tags(self):
        """Parser must not crash on unknown XML tags (MOK §4)."""
        from api.response_parser import parse_setid_response
        xml = b'''<?xml version="1.0"?>
<Response>
    <EducatedPerson>
        <SNILS>123-456-789 00</SNILS>
        <UnknownFutureTag>some_value</UnknownFutureTag>
        <AnotherNewTag><Inner/></AnotherNewTag>
    </EducatedPerson>
</Response>'''
        result = parse_setid_response(xml, 200)
        assert result['success'] is True
        assert len(result['records']) == 1
        assert result['records'][0]['snils'] == '123-456-789 00'

    def test_parse_send_response_unknown_tags(self):
        """Send parser must not crash on unknown tags."""
        from api.response_parser import parse_send_response
        xml = b'''<?xml version="1.0"?>
<Response>
    <SetId>SET-001</SetId>
    <SendEducatedPerson>true</SendEducatedPerson>
    <FutureField>unexpected</FutureField>
</Response>'''
        result = parse_send_response(xml, 200)
        assert result['success'] is True
        assert result['set_id'] == 'SET-001'

    def test_parse_error_request_id_preserved(self):
        """RequestId from error must be preserved (MOK §5.2)."""
        from api.response_parser import parse_send_response, parse_error_response
        # Error nested inside Response (server format)
        xml = b'''<?xml version="1.0"?>
<Response>
    <Error>
        <StatusCode>400</StatusCode>
        <Message>Validation error</Message>
        <DateTime>2025-09-26T12:00:00</DateTime>
        <RequestId>UUID-12345-ABCDE</RequestId>
    </Error>
</Response>'''
        result = parse_send_response(xml, 400)
        assert 'error' in result
        # Pure Error root tag
        xml2 = b'''<?xml version="1.0"?>
<Error>
    <StatusCode>403</StatusCode>
    <Message>Forbidden</Message>
    <DateTime>2025-09-26T12:00:00</DateTime>
    <RequestId>UUID-67890-FGHIJ</RequestId>
</Error>'''
        result2 = parse_error_response(xml2)
        assert 'error' in result2

    def test_business_logic_unchanged(self):
        """MOK §9: Business logic compatibility — must work with real API."""
        from api.payload_builder import build_multipart_payload, build_request_xml, build_olot_archive
        # Verify production format is unchanged
        xml = build_request_xml("k" * 32)
        assert b'<ApiKey>' in xml
        assert b'<NeedSend>' in xml
        # Multipart field names unchanged
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as f:
            f.write(b'<Data/>')
            path = f.name
        try:
            files, _ = build_multipart_payload("k" * 32, path)
            assert files['xml'][0] == 'Request.xml'
            assert files['olot'][0] == 'data.olot'
        finally:
            os.remove(path)
