import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from api.response_parser import (
    parse_send_response, parse_setid_response, parse_snils_response, parse_error_response
)


class TestParseSendResponse:
    def test_response_tag_success(self):
        xml = b'''<?xml version="1.0"?><Response><SetId>SET-12345</SetId><SendEducatedPerson>true</SendEducatedPerson><Message>OK</Message></Response>'''
        result = parse_send_response(xml, 200)
        assert result['success'] is True
        assert result['set_id'] == 'SET-12345'
        assert result['send_educated_person'] is True
        assert result['message'] == 'OK'

    def test_response_tag_no_setid(self):
        xml = b'''<?xml version="1.0"?><Response><SendEducatedPerson>false</SendEducatedPerson></Response>'''
        result = parse_send_response(xml, 200)
        assert result['success'] is True
        assert result['set_id'] == ''
        assert result['send_educated_person'] is False

    def test_result_tag(self):
        xml = b'''<?xml version="1.0"?><Result><SetId>R-001</SetId><SendEducatedPerson>true</SendEducatedPerson></Result>'''
        result = parse_send_response(xml, 200)
        assert result['success'] is True
        assert result['set_id'] == 'R-001'

    def test_message_tag(self):
        xml = b'''<?xml version="1.0"?><Message><SetId>MSG-001</SetId><SendEducatedPerson>false</SendEducatedPerson><Text>Processing</Text></Message>'''
        result = parse_send_response(xml, 200)
        assert result['success'] is True
        assert result['set_id'] == 'MSG-001'
        assert result['message'] == 'Processing'

    def test_setid_tag(self):
        xml = b'''<?xml version="1.0"?><SetId><Id>ID-001</Id><SendEducatedPerson>true</SendEducatedPerson></SetId>'''
        result = parse_send_response(xml, 200)
        assert result['success'] is True
        assert result['set_id'] == 'ID-001'

    def test_error_tag(self):
        xml = b'''<?xml version="1.0"?><Error><StatusCode>401</StatusCode><Message>Invalid API key</Message></Error>'''
        result = parse_send_response(xml, 401)
        assert result['success'] is False
        assert '401' in result['error'] or 'ключ' in result['error'].lower()

    def test_unknown_tag(self):
        xml = b'''<?xml version="1.0"?><Unknown><Data>test</Data></Unknown>'''
        result = parse_send_response(xml, 200)
        assert result['success'] is False
        assert 'Неизвестный' in result['error']

    def test_invalid_xml(self):
        result = parse_send_response(b'not xml at all', 200)
        assert result['success'] is False
        assert 'разобрать' in result['error'].lower()

    def test_error_status_code_400(self):
        xml = b'''<?xml version="1.0"?><Error><StatusCode>400</StatusCode><Message>Validation failed</Message></Error>'''
        result = parse_send_response(xml, 400)
        assert result['success'] is False
        assert 'валидации' in result['error'].lower()

    def test_error_status_code_500(self):
        xml = b'''<?xml version="1.0"?><Error><StatusCode>500</StatusCode><Message>Server error</Message></Error>'''
        result = parse_send_response(xml, 500)
        assert result['success'] is False

    def test_response_without_setid_send(self):
        xml = b'''<?xml version="1.0"?><Response></Response>'''
        result = parse_send_response(xml, 200)
        assert result['set_id'] == ''
        assert result['send_educated_person'] is False


class TestParseSetidResponse:
    def test_response_tag(self):
        xml = '''<?xml version="1.0"?><Response><EducatedPerson><SNILS>123-456-789 00</SNILS><RegNumber>RN-001</RegNumber><Status>trained</Status><LastName>Иванов</LastName><FirstName>Иван</FirstName><Message>OK</Message></EducatedPerson></Response>'''.encode('utf-8')
        result = parse_setid_response(xml, 200)
        assert result['success'] is True
        assert len(result['records']) == 1
        assert result['records'][0]['snils'] == '123-456-789 00'
        assert result['records'][0]['reg_number'] == 'RN-001'

    def test_educated_persons_tag(self):
        xml = '<?xml version="1.0"?><EducatedPersons><RegistryRecord baseNo="BN-001" setId="S-1"><Worker><LastName>Петров</LastName><FirstName>Петр</FirstName><Snils>111-222-333 44</Snils><Position>Инженер</Position><EmployerInn>7701</EmployerInn><EmployerTitle>ООО</EmployerTitle></Worker><Test isPassed="true" learnProgramId="1"><LearnProgramTitle>Первая помощь</LearnProgramTitle><ProtocolNumber>П-1</ProtocolNumber><Date>2025-09-25</Date></Test></RegistryRecord></EducatedPersons>'.encode('utf-8')
        result = parse_setid_response(xml, 200)
        assert result['success'] is True
        assert len(result['records']) == 1
        assert result['records'][0]['LastName'] == 'Петров'
        assert result['records'][0]['isPassed'] == 'true'
        assert result['records'][0]['learnProgramId'] == '1'
        assert result['records'][0]['FirstName'] == 'Петр'
        assert result['records'][0]['EmployerInn'] == '7701'
        assert result['records'][0]['EmployerTitle'] == 'ООО'
        assert result['records'][0]['ProtocolNumber'] == 'П-1'
        assert result['records'][0]['Date'] == '2025-09-25'
        assert result['records'][0]['LearnProgramTitle'] == 'Первая помощь'
        assert result['records'][0]['Snils'] == '111-222-333 44'

    def test_educated_persons_missing_optional_fields(self):
        """Missing optional fields should not cause errors."""
        xml = '<?xml version="1.0"?><EducatedPersons><RegistryRecord><Worker><LastName>Иванов</LastName></Worker></RegistryRecord></EducatedPersons>'.encode('utf-8')
        result = parse_setid_response(xml, 200)
        assert result['success'] is True
        assert len(result['records']) == 1

    def test_error_tag(self):
        xml = b'''<?xml version="1.0"?><Error><StatusCode>404</StatusCode><Message>Not found</Message></Error>'''
        result = parse_setid_response(xml, 404)
        assert result['success'] is False
        assert len(result['records']) == 0

    def test_unknown_tag(self):
        xml = b'''<?xml version="1.0"?><SomethingElse/>'''
        result = parse_setid_response(xml, 200)
        assert result['success'] is False
        assert 'Неизвестный' in result['error']

    def test_empty_records(self):
        xml = b'''<?xml version="1.0"?><Response/>'''
        result = parse_setid_response(xml, 200)
        assert result['success'] is True
        assert len(result['records']) == 0

    def test_educated_person_tag_full_fields(self):
        """EducationalPerson path with all fields extracted (child elements, not attributes)."""
        xml = '''<?xml version="1.0"?><Response><EducatedPerson><SNILS>999-888-777 66</SNILS><RegNumber>RN-999</RegNumber><Status>trained</Status><LastName>Сидоров</LastName><FirstName>Сидр</FirstName><MiddleName>Сидорович</MiddleName><Message>OK</Message></EducatedPerson></Response>'''.encode('utf-8')
        result = parse_setid_response(xml, 200)
        assert result['success'] is True
        assert len(result['records']) == 1
        assert result['records'][0]['snils'] == '999-888-777 66'
        assert result['records'][0]['reg_number'] == 'RN-999'
        assert result['records'][0]['status'] == 'trained'
        assert result['records'][0]['message'] == 'OK'
        assert result['records'][0]['LastName'] == 'Сидоров'
        assert result['records'][0]['FirstName'] == 'Сидр'
        assert result['records'][0]['MiddleName'] == 'Сидорович'

    def test_invalid_xml(self):
        result = parse_setid_response(b'invalid', 200)
        assert result['success'] is False


class TestParseSnilsResponse:
    def test_delegates_to_setid_parser(self):
        xml = b'''<?xml version="1.0"?><Response><EducatedPerson><SNILS>123-456-789 00</SNILS><RegNumber>RN-001</RegNumber></EducatedPerson></Response>'''
        result = parse_snils_response(xml, 200)
        assert result['success'] is True
        assert len(result['records']) == 1
        assert result['records'][0]['snils'] == '123-456-789 00'
        assert result['records'][0]['reg_number'] == 'RN-001'

    def test_snils_no_records(self):
        xml = b'''<?xml version="1.0"?><Response/>'''
        result = parse_snils_response(xml, 200)
        assert result['success'] is True
        assert len(result['records']) == 0


class TestParseErrorResponse:
    def test_error_tag(self):
        xml = b'''<?xml version="1.0"?><Error><StatusCode>403</StatusCode><Message>Forbidden</Message></Error>'''
        result = parse_error_response(xml)
        assert result['success'] is False
        assert '403' in result['error'] or 'Forbidden' in result['error']

    def test_unknown_format(self):
        xml = b'''<?xml version="1.0"?><RandomTag/>'''
        result = parse_error_response(xml)
        assert result['success'] is False

    def test_invalid_bytes(self):
        result = parse_error_response(b'\xff\xfe\x00\x01')
        assert result['success'] is False
