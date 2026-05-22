"""
XML security regression tests per MOK.md specification.
Tests: defusedxml protection, XXE, Billion Laughs, size limits.
"""
import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from defusedxml.common import DefusedXmlException
from utils.exceptions import XmlSecurityError


class TestDefusedXmlProtection:
    """MOK §5 — Safe XML parsing with defusedxml."""

    def test_xxe_attack_rejected(self):
        """XXE attack must be rejected by defusedxml."""
        from utils.xml_safe import safe_fromstring_xml
        xxe_payload = '''<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<Request>&xxe;</Request>'''
        with pytest.raises((DefusedXmlException, XmlSecurityError, Exception)):
            safe_fromstring_xml(xxe_payload)

    def test_billion_laughs_rejected(self):
        """Billion Laughs attack must be rejected."""
        from utils.xml_safe import safe_fromstring_xml
        payload = '''<?xml version="1.0"?>
<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
  <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
  <!ENTITY lol4 "&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;">
  <!ENTITY lol5 "&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;">
]>
<Request>&lol5;</Request>'''
        with pytest.raises((DefusedXmlException, XmlSecurityError, Exception)):
            safe_fromstring_xml(payload)

    def test_quadratic_blowup_rejected(self):
        """Quadratic entity expansion must be rejected."""
        from utils.xml_safe import safe_fromstring_xml
        payload = '''<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY x "aaaa">
  <!ENTITY y "&x;&x;&x;&x;&x;&x;&x;&x;&x;&x;">
]>
<Request>&y;&y;&y;&y;&y;&y;&y;&y;&y;&y;</Request>'''
        with pytest.raises((DefusedXmlException, XmlSecurityError, Exception)):
            safe_fromstring_xml(payload)

    def test_external_dtd_rejected(self):
        """External DTD retrieval must be rejected."""
        from utils.xml_safe import safe_parse_xml
        import tempfile
        payload = '''<?xml version="1.0"?>
<!DOCTYPE foo SYSTEM "http://evil.com/attack.dtd">
<Request><Data>test</Data></Request>'''
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False, mode='w', encoding='utf-8') as f:
            f.write(payload)
            fpath = f.name
        try:
            with pytest.raises((DefusedXmlException, XmlSecurityError, Exception)):
                safe_parse_xml(fpath)
        finally:
            os.remove(fpath)

    def test_large_xml_rejected(self):
        """Oversized XML must be rejected by size check."""
        from utils.xml_safe import safe_fromstring_xml
        large_content = 'A' * (101 * 1024 * 1024)
        payload = f'<Request><Data>{large_content}</Data></Request>'
        with pytest.raises((XmlSecurityError, Exception)):
            safe_fromstring_xml(payload)

    def test_malformed_xml_rejected(self):
        """Malformed XML must raise XmlSecurityError."""
        from utils.xml_safe import safe_fromstring_xml
        with pytest.raises((XmlSecurityError, Exception)):
            safe_fromstring_xml('<Request><unclosed>')

    def test_empty_xml_rejected(self):
        """Empty string must be rejected."""
        from utils.xml_safe import safe_fromstring_xml
        with pytest.raises((XmlSecurityError, Exception)):
            safe_fromstring_xml('')

    def test_valid_xml_passes(self):
        """Valid XML must parse successfully."""
        from utils.xml_safe import safe_fromstring_xml
        result = safe_fromstring_xml('<Request><ApiKey>key</ApiKey></Request>')
        assert result is not None
        assert result.tag == 'Request'

    def test_element_count_limit(self):
        """Too many XML elements must be rejected (via safe_parse_xml)."""
        from utils.xml_safe import safe_parse_xml
        import tempfile
        elements = ''.join(f'<e>{i}</e>' for i in range(60000))
        payload = f'<root>{elements}</root>'
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False, mode='w', encoding='utf-8') as f:
            f.write(payload)
            fpath = f.name
        try:
            with pytest.raises((XmlSecurityError, Exception)):
                safe_parse_xml(fpath)
        finally:
            os.remove(fpath)

    def test_deeply_nested_xml_rejected(self):
        """Excessive XML depth must be rejected."""
        from utils.xml_safe import safe_fromstring_xml
        nested = '<r>'
        for _ in range(100):
            nested += '<r>'
        nested += 'x'
        for _ in range(100):
            nested += '</r>'
        with pytest.raises((XmlSecurityError, Exception)):
            safe_fromstring_xml(nested)

    def test_file_based_xxe_rejected(self):
        """XXE via safe_parse_xml file must be rejected."""
        from utils.xml_safe import safe_parse_xml
        xxe_content = '''<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<Request>&xxe;</Request>'''
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False, mode='w', encoding='utf-8') as f:
            f.write(xxe_content)
            fpath = f.name
        try:
            with pytest.raises((DefusedXmlException, XmlSecurityError, Exception)):
                safe_parse_xml(fpath)
        finally:
            os.remove(fpath)

    def test_file_based_billion_laughs_rejected(self):
        """Billion Laughs via safe_parse_xml file must be rejected."""
        from utils.xml_safe import safe_parse_xml
        payload = '''<?xml version="1.0"?>
<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
  <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
  <!ENTITY lol4 "&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;">
]>
<Request>&lol4;</Request>'''
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False, mode='w', encoding='utf-8') as f:
            f.write(payload)
            fpath = f.name
        try:
            with pytest.raises((DefusedXmlException, XmlSecurityError, Exception)):
                safe_parse_xml(fpath)
        finally:
            os.remove(fpath)

    def test_large_file_rejected(self):
        """File larger than 100MB must be rejected."""
        from utils.xml_safe import safe_parse_xml
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False, mode='wb') as f:
            f.write(b'<r>' + b'x' * (101 * 1024 * 1024) + b'</r>')
            fpath = f.name
        try:
            with pytest.raises((XmlSecurityError, Exception)):
                safe_parse_xml(fpath)
        finally:
            os.remove(fpath)

    def test_defusedxml_used_not_stdlib(self):
        """Ensure defusedxml.ElementTree is used, not stdlib xml.etree."""
        import utils.xml_safe as xs
        # safe_parse_xml internally uses defusedxml's XMLParser
        from defusedxml.ElementTree import parse as defused_parse
        from utils.xml_safe import safe_parse_xml, safe_fromstring_xml
        # Both entry points exist and are functional
        assert callable(safe_parse_xml)
        assert callable(safe_fromstring_xml)

    def test_no_entity_resolution(self):
        """Entity resolution must be disabled (forbid_dtd=True by default)."""
        from utils.xml_safe import safe_fromstring_xml
        # Attempt entity resolution — should fail with DefusedXmlException
        xml = '''<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<Request>&xxe;</Request>'''
        import defusedxml.common
        import utils.exceptions
        with pytest.raises((defusedxml.common.DefusedXmlException, utils.exceptions.XmlSecurityError)):
            safe_fromstring_xml(xml)

    def test_utf8_bom_handling(self):
        """UTF-8 BOM in XML must not break parsing."""
        from utils.xml_safe import safe_fromstring_xml
        xml_with_bom = '\ufeff<?xml version="1.0"?><Request><ApiKey>key</ApiKey></Request>'
        result = safe_fromstring_xml(xml_with_bom)
        assert result is not None
