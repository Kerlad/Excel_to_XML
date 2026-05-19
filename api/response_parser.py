"""
Response parser for Mintrud API.
Parses XML responses from the server.
"""
import logging
import xml.etree.ElementTree as ET
from typing import Dict, Any

from utils.logger import mask_sensitive

logger = logging.getLogger(__name__)

ERROR_MAP = {
    "400": "Ошибка валидации XML. Проверьте соответствие схеме XSD",
    "401": "Ошибка авторизации. Проверьте API ключ",
    "403": "Доступ запрещён",
    "500": "Ошибка сервера Минтруда. Повторите попытку позже",
    "503": "Сервис временно недоступен. Повторите попытку позже",
}


def _format_error(status_code: str, message: str) -> str:
    """Format error message from status code."""
    if status_code in ERROR_MAP:
        base_msg = ERROR_MAP[status_code]
    else:
        base_msg = f"Ошибка сервера (код {status_code})"
    
    if message:
        return f"{base_msg}\n\nПодробности: {message}"
    return base_msg


def parse_send_response(response_bytes: bytes, status_code: int = 200) -> Dict[str, Any]:
    """
    Parse response from send XML API.
    
    Args:
        response_bytes: Raw response bytes
        status_code: HTTP status code
    
    Returns:
        Dict with keys: success, set_id, send_educated_person, message, error, raw_response
    """
    try:
        response_text = response_bytes.decode('utf-8')
    except Exception:
        try:
            response_text = response_bytes.decode('cp1251')
        except Exception:
            response_text = str(response_bytes)
    
    logger.info(f"Response (first 500 chars): {mask_sensitive(response_text[:500])}")
    
    try:
        root = ET.fromstring(response_text)
    except ET.ParseError:
        return {
            "success": False,
            "set_id": None,
            "message": None,
            "error": f"HTTP {status_code}: Не удалось разобрать ответ сервера",
            "raw_response": response_text[:1000]
        }
    
    if root.tag == "Response":
        set_id_elem = root.find("SetId")
        send_elem = root.find("SendEducatedPerson")
        msg_elem = root.find("Message")
        
        set_id = set_id_elem.text if set_id_elem is not None else ""
        send_edu = send_elem.text if send_elem is not None else "false"
        msg = msg_elem.text if msg_elem is not None else ""
        
        logger.info(f"Success: SetId={mask_sensitive(set_id)}, SendEducatedPerson={send_edu}")
        
        return {
            "success": True,
            "set_id": set_id,
            "send_educated_person": send_edu.lower() == "true",
            "message": msg,
            "error": None,
            "raw_response": None
        }

    elif root.tag == "Result":
        set_id_elem = root.find("SetId")
        send_elem = root.find("SendEducatedPerson")
        msg_elem = root.find("Message")

        set_id = set_id_elem.text if set_id_elem is not None else ""
        send_edu = send_elem.text if send_elem is not None else "false"
        msg = msg_elem.text if msg_elem is not None else ""

        logger.info(f"Success (Result tag): SetId={mask_sensitive(set_id)}, SendEducatedPerson={send_edu}")

        return {
            "success": True,
            "set_id": set_id,
            "send_educated_person": send_edu.lower() == "true",
            "message": msg,
            "error": None,
            "raw_response": None
        }

    elif root.tag == "Message":
        set_id_elem = root.find("SetId")
        send_elem = root.find("SendEducatedPerson")
        msg_elem = root.find("Text")

        set_id = set_id_elem.text if set_id_elem is not None else ""
        send_edu = send_elem.text if send_elem is not None else "false"
        msg = msg_elem.text if msg_elem is not None else ""

        logger.info(f"Success (Message tag): SetId={mask_sensitive(set_id)}")

        return {
            "success": True,
            "set_id": set_id,
            "send_educated_person": send_edu.lower() == "true",
            "message": msg,
            "error": None,
            "raw_response": None
        }

    elif root.tag == "SetId":
        set_id_elem = root.find("Id")
        send_elem = root.find("SendEducatedPerson")

        set_id = set_id_elem.text if set_id_elem is not None else str(root.tag)
        send_edu = send_elem.text if send_elem is not None else "false"

        return {
            "success": True,
            "set_id": set_id,
            "send_educated_person": send_edu.lower() == "true",
            "message": None,
            "error": None,
            "raw_response": None
        }

    elif root.tag == "Error":
        status_code_elem = root.find("StatusCode")
        msg_elem = root.find("Message")
        
        status_code_str = status_code_elem.text if status_code_elem is not None else "unknown"
        msg = msg_elem.text if msg_elem is not None else ""
        
        error_msg = _format_error(status_code_str, msg)
        logger.error(f"Error: {status_code_str} - {mask_sensitive(msg)}")
        
        return {
            "success": False,
            "set_id": None,
            "message": None,
            "error": error_msg,
            "raw_response": response_text[:1000]
        }
    
    else:
        logger.error(f"Unknown response format: {root.tag}")
        return {
            "success": False,
            "set_id": None,
            "message": None,
            "error": f"Неизвестный формат ответа: {root.tag}",
            "raw_response": response_text[:500]
        }


def parse_setid_response(response_bytes: bytes, status_code: int = 200) -> Dict[str, Any]:
    """
    Parse response from query by SetId API.

    Args:
        response_bytes: Raw response bytes
        status_code: HTTP status code

    Returns:
        Dict with keys: success, records, error, raw_response
    """
    try:
        response_text = response_bytes.decode('utf-8')
    except Exception:
        try:
            response_text = response_bytes.decode('cp1251')
        except Exception:
            response_text = str(response_bytes)

    logger.info(f"parse_setid_response: status={status_code}, text_len={len(response_text)}")

    try:
        root = ET.fromstring(response_text)
    except ET.ParseError:
        logger.error(f"XML parse error: {mask_sensitive(response_text[:500])}")
        return {
            "success": False,
            "records": [],
            "error": f"HTTP {status_code}: Не удалось разобрать ответ",
            "raw_response": response_text[:1000]
        }

    logger.info(f"Root tag: {root.tag}")
    
    if root.tag == "Response":
        records = []
        for person in root.findall("EducatedPerson"):
            record = {
                "snils": person.findtext("SNILS", ""),
                "reg_number": person.findtext("RegNumber", ""),
                "status": person.findtext("Status", ""),
                "message": person.findtext("Message", ""),
                "baseNo": person.findtext("RegNumber", ""),
                "LastName": person.findtext("LastName", ""),
                "FirstName": person.findtext("FirstName", ""),
                "MiddleName": person.findtext("MiddleName", ""),
                "learnProgramId": person.get("learnProgramId", ""),
                "LearnProgramTitle": person.get("learnProgramTitle", ""),
                "ProtocolNumber": person.get("ProtocolNumber", ""),
                "Date": person.get("Date", ""),
            }
            records.append(record)
        return {
            "success": True,
            "records": records,
            "error": None,
            "raw_response": None
        }

    elif root.tag == "EducatedPersons":
        records = []
        for rec in root.findall("RegistryRecord"):
            base_no = rec.get("baseNo", "")
            set_id = rec.get("setId", "")

            snils = ""
            last_name = ""
            first_name = ""
            middle_name = ""
            position = ""
            employer_inn = ""
            employer_title = ""
            program_id = ""
            program_title = ""
            protocol = ""
            date = ""
            is_passed = ""

            for child in rec:
                tag = child.tag
                if tag == "Worker":
                    snils = child.findtext("Snils", "")
                    last_name = child.findtext("LastName", "")
                    first_name = child.findtext("FirstName", "")
                    middle_name = child.findtext("MiddleName", "")
                    position = child.findtext("Position", "")
                    employer_inn = child.findtext("EmployerInn", "")
                    employer_title = child.findtext("EmployerTitle", "")
                elif tag == "EmployerOrganization":
                    if not employer_inn:
                        employer_inn = child.findtext("Inn", "")
                    if not employer_title:
                        employer_title = child.findtext("Title", "")
                elif tag == "Test":
                    program_id = child.get("learnProgramId", "")
                    is_passed = child.get("isPassed", "")
                    program_title = child.findtext("LearnProgramTitle", "")
                    protocol = child.findtext("ProtocolNumber", "")
                    date_raw = child.findtext("Date", "")
                    if date_raw:
                        date = date_raw.split()[0] if ' ' in date_raw else date_raw

            record = {
                "Snils": snils,
                "LastName": last_name,
                "FirstName": first_name,
                "MiddleName": middle_name,
                "Position": position,
                "EmployerInn": employer_inn,
                "EmployerTitle": employer_title,
                "learnProgramId": program_id,
                "LearnProgramTitle": program_title,
                "ProtocolNumber": protocol,
                "Date": date,
                "isPassed": is_passed,
                "baseNo": base_no,
                "setId": set_id,
            }
            records.append(record)

        return {
            "success": True,
            "records": records,
            "error": None,
            "raw_response": None
        }

    elif root.tag == "Error":
        status_code_elem = root.find("StatusCode")
        msg_elem = root.find("Message")
        
        status_code_str = status_code_elem.text if status_code_elem is not None else "unknown"
        msg = msg_elem.text if msg_elem is not None else ""
        
        return {
            "success": False,
            "records": [],
            "error": _format_error(status_code_str, msg),
            "raw_response": response_text[:1000]
        }
    
    else:
        return {
            "success": False,
            "records": [],
            "error": f"Неизвестный формат ответа: {root.tag}",
            "raw_response": response_text[:500]
        }


def parse_snils_response(response_bytes: bytes, status_code: int = 200) -> Dict[str, Any]:
    """
    Parse response from query by SNILS API.
    
    Args:
        response_bytes: Raw response bytes
        status_code: HTTP status code
    
    Returns:
        Dict with keys: success, records, error, raw_response
    """
    return parse_setid_response(response_bytes, status_code)


def parse_error_response(response_bytes: bytes) -> Dict[str, Any]:
    """
    Parse error response from any API call.
    
    Args:
        response_bytes: Raw response bytes
    
    Returns:
        Dict with keys: success, error, raw_response
    """
    try:
        response_text = response_bytes.decode('utf-8')
    except Exception:
        response_text = str(response_bytes)
    
    try:
        root = ET.fromstring(response_text)
    except ET.ParseError:
        return {
            "success": False,
            "error": f"Не удалось разобрать ответ сервера: {response_text[:200]}",
            "raw_response": response_text[:1000]
        }
    
    if root.tag == "Error":
        status_code_elem = root.find("StatusCode")
        msg_elem = root.find("Message")
        
        status_code_str = status_code_elem.text if status_code_elem is not None else "unknown"
        msg = msg_elem.text if msg_elem is not None else ""
        
        return {
            "success": False,
            "error": _format_error(status_code_str, msg),
            "raw_response": response_text[:1000]
        }
    
    return {
        "success": False,
        "error": f"Ошибка: {response_text[:200]}",
        "raw_response": response_text[:1000]
    }