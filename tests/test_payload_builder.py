import sys, os, tempfile, zipfile, io
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from api.payload_builder import (
    build_request_xml, build_olot_archive, build_multipart_payload
)


class TestPayloadBuilder:
    def test_build_request_xml(self):
        api_key = "test_key_1234567890123456"
        xml_bytes = build_request_xml(api_key, need_send=False)
        xml_str = xml_bytes.decode('utf-8')
        assert '<ApiKey>' in xml_str
        assert api_key in xml_str
        assert '<NeedSend>false</NeedSend>' in xml_str

    def test_build_request_xml_need_send_true(self):
        xml_bytes = build_request_xml("key", need_send=True)
        assert b'<NeedSend>true</NeedSend>' in xml_bytes

    def test_build_request_xml_special_chars(self):
        xml_bytes = build_request_xml("key&<>'\"" )
        assert b'&amp;' in xml_bytes
        assert b'&lt;' in xml_bytes

    def test_build_olot_archive(self):
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as f:
            f.write(b'<Data>test</Data>')
            xml_path = f.name
        try:
            archive_bytes = build_olot_archive(xml_path)
            assert len(archive_bytes) > 0
            with zipfile.ZipFile(io.BytesIO(archive_bytes)) as zf:
                names = zf.namelist()
                assert 'Data.xml' in names
                assert zf.read('Data.xml') == b'<Data>test</Data>'
        finally:
            os.remove(xml_path)

    def test_build_olot_archive_with_sig(self):
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as f:
            f.write(b'<Data/>')
            xml_path = f.name
        with tempfile.NamedTemporaryFile(suffix='.sig', delete=False) as f:
            f.write(b'signature_data')
            sig_path = f.name
        try:
            archive_bytes = build_olot_archive(xml_path, sig_path)
            with zipfile.ZipFile(io.BytesIO(archive_bytes)) as zf:
                names = zf.namelist()
                assert 'Data.xml' in names
                assert os.path.basename(sig_path) in names
                assert zf.read(os.path.basename(sig_path)) == b'signature_data'
        finally:
            os.remove(xml_path)
            os.remove(sig_path)

    def test_build_olot_archive_missing_file(self):
        with pytest.raises(FileNotFoundError):
            build_olot_archive("nonexistent.xml")

    def test_build_olot_archive_missing_sig(self):
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as f:
            f.write(b'<Data/>')
            xml_path = f.name
        try:
            with pytest.raises(FileNotFoundError):
                build_olot_archive(xml_path, "nonexistent.sig")
        finally:
            os.remove(xml_path)

    def test_build_multipart_payload(self):
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as f:
            f.write(b'<Data/>')
            xml_path = f.name
        try:
            files, headers = build_multipart_payload("test_key", xml_path)
            assert 'xml' in files
            assert 'olot' in files
            assert files['xml'][0] == 'Request.xml'
            assert files['xml'][2] == 'text/xml'
            assert files['olot'][0] == 'data.olot'
            assert 'User-Agent' in headers
        finally:
            os.remove(xml_path)

    def test_build_multipart_payload_with_sig(self):
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as f:
            f.write(b'<Data/>')
            xml_path = f.name
        with tempfile.NamedTemporaryFile(suffix='.sig', delete=False) as f:
            f.write(b'sig')
            sig_path = f.name
        try:
            files, headers = build_multipart_payload("key", xml_path, need_send=True, sig_file_path=sig_path)
            assert 'xml' in files
            assert 'olot' in files
            with zipfile.ZipFile(io.BytesIO(files['olot'][1])) as zf:
                assert os.path.basename(sig_path) in zf.namelist()
        finally:
            os.remove(xml_path)
            os.remove(sig_path)

    def test_parse_api_url_push(self):
        from api.payload_builder import parse_api_url
        assert 'push' in parse_api_url('push')

    def test_parse_api_url_get(self):
        from api.payload_builder import parse_api_url
        assert 'GetEducatedPersonXML' in parse_api_url('get')

    def test_parse_api_url_default(self):
        from api.payload_builder import parse_api_url
        assert 'push' in parse_api_url('unknown')
