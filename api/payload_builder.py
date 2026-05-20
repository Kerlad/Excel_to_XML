"""
Payload builder for Mintrud API.
Builds Request.xml, .olot archives, and multipart payloads.
"""
import os
import io
import zipfile
from xml.sax.saxutils import escape
from typing import Dict, Any, Optional

API_URL = "https://edu.rosmintrud.ru/api/set/push"
GET_URL = "https://edu.rosmintrud.ru/api/GetEducatedPersonXML"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}


def build_request_xml(api_key: str, need_send: bool = False) -> bytes:
    """
    Build Request.xml with ApiKey and NeedSend fields.
    
    Args:
        api_key: API key for authentication
        need_send: Whether to send immediately (default False)
    
    Returns:
        XML bytes encoded as UTF-8
    """
    need_send_str = "true" if need_send else "false"
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Request>
    <ApiKey>{escape(api_key)}</ApiKey>
    <NeedSend>{need_send_str}</NeedSend>
</Request>'''
    return xml.encode('utf-8')


def build_olot_archive(xml_file_path: str, sig_file_path: str = None) -> bytes:
    """
    Build .olot archive (ZIP with Data.xml inside).
    Optionally includes .sig signature file for РОЛ sending.
    Server requires Data.xml with capital D.
    
    Args:
        xml_file_path: Path to the XML data file
        sig_file_path: Optional path to .sig signature file
    
    Returns:
        Bytes of the .olot archive
    
    Raises:
        FileNotFoundError: If xml_file_path doesn't exist
    """
    with open(xml_file_path, 'rb') as f:
        data_xml_content = f.read()
    
    olot_buffer = io.BytesIO()
    with zipfile.ZipFile(olot_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('Data.xml', data_xml_content)
        if sig_file_path:
            if not os.path.exists(sig_file_path):
                raise FileNotFoundError(f"Файл подписи не найден: {sig_file_path}")
            sig_filename = os.path.basename(sig_file_path)
            with open(sig_file_path, 'rb') as f:
                sig_content = f.read()
            zf.writestr(sig_filename, sig_content)
    
    return olot_buffer.getvalue()


def build_multipart_payload(
    api_key: str,
    xml_file_path: str,
    need_send: bool = False,
    sig_file_path: str = None
) -> tuple[Dict[str, tuple], Dict[str, str]]:
    """
    Build complete multipart/form-data payload for API request.
    
    Args:
        api_key: API key for authentication
        xml_file_path: Path to the XML data file
        need_send: Whether to send immediately
        sig_file_path: Optional path to .sig signature file for РОЛ
    
    Returns:
        Tuple of (files_dict, headers_dict):
        - files_dict: Dictionary for requests library files parameter
        - headers_dict: Additional headers
    """
    request_xml = build_request_xml(api_key, need_send)
    olot_data = build_olot_archive(xml_file_path, sig_file_path=sig_file_path)
    
    files = {
        'xml': ('Request.xml', request_xml, 'text/xml'),
        'olot': ('data.olot', olot_data, 'application/octet-stream'),
    }
    
    return files, HEADERS


def parse_api_url(action: str = "push") -> str:
    """
    Get API URL for the specified action.
    
    Args:
        action: "push" for sending, "get" for querying
    
    Returns:
        Full URL for the API endpoint
    """
    if action == "push":
        return API_URL
    elif action == "get":
        return GET_URL
    else:
        return API_URL