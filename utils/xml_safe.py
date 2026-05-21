"""
Secure XML parsing module for ISPDn.
- defusedxml for protection against XXE, Billion Laughs, entity expansion
- Strict limits: element count, depth, file size
- Network access disabled
- Entity resolution disabled
"""
import logging
from typing import Optional

import xml.etree.ElementTree as etree
from defusedxml.ElementTree import parse, fromstring, XMLParser
from defusedxml.common import DefusedXmlException

from utils.constants import MAX_XML_ELEMENTS, MAX_XML_DEPTH
from utils.exceptions import XmlSecurityError
from utils.audit import log_audit

logger = logging.getLogger(__name__)

_MAX_XML_SIZE_BYTES = 100 * 1024 * 1024


class LimitedXMLParser(XMLParser):
    """XML parser with strict limits on element count, depth, and entity expansion.
    Uses defusedxml as base for XXE/Billion Laughs protection.
    DefusedXMLParser inherently prohibits XXE, entity expansion, and DTD retrieval.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._element_count = 0
        self._max_depth = 0
        self._current_depth = 0

    def start(self, tag, attrib):
        self._element_count += 1
        self._current_depth += 1
        if self._current_depth > self._max_depth:
            self._max_depth = self._current_depth
        if self._element_count > MAX_XML_ELEMENTS:
            log_audit("XML_SECURITY_ERROR", f"Element limit exceeded: {MAX_XML_ELEMENTS}")
            raise XmlSecurityError(
                f"Превышен лимит элементов XML: {MAX_XML_ELEMENTS}"
            )
        if self._current_depth > MAX_XML_DEPTH:
            log_audit("XML_SECURITY_ERROR", f"Depth limit exceeded: {MAX_XML_DEPTH}")
            raise XmlSecurityError(
                f"Превышена максимальная глубина XML: {MAX_XML_DEPTH}"
            )
        return super().start(tag, attrib)

    def end(self, tag):
        self._current_depth -= 1
        return super().end(tag)

    def close(self):
        return super().close()


def safe_parse_xml(file_path: str) -> object:
    """Safely parse XML file with security limits and XXE protection."""
    if not file_path or not isinstance(file_path, str):
        raise ValueError("file_path must be a non-empty string")
    import os
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"XML file not found: {file_path}")
    fsize = os.path.getsize(file_path)
    if fsize > _MAX_XML_SIZE_BYTES:
        from utils.exceptions import FileTooLargeError
        raise FileTooLargeError(
            file_path,
            fsize / (1024 * 1024),
            _MAX_XML_SIZE_BYTES // (1024 * 1024)
        )
    try:
        parser = LimitedXMLParser()
        tree = parse(file_path, parser=parser)
        return tree
    except (DefusedXmlException, XmlSecurityError):
        log_audit("XML_SECURITY_ERROR", "defusedxml/security exception during parse")
        raise
    except OSError:
        raise
    except (etree.ParseError, ValueError) as e:
        logger.error("XML parse error for %s: %s", file_path, e)
        log_audit("XML_VALIDATION_ERROR", f"Parse error: {e}")
        raise XmlSecurityError(f"Ошибка парсинга XML: {e}")


def safe_fromstring_xml(data: str) -> object:
    """Safely parse XML from string with security limits and XXE protection."""
    if not isinstance(data, str):
        data = data.decode("utf-8") if isinstance(data, bytes) else str(data)
    if len(data.encode("utf-8")) > _MAX_XML_SIZE_BYTES:
        log_audit("XML_SECURITY_ERROR", "XML data size limit exceeded")
        raise XmlSecurityError("Размер XML превышает допустимый лимит")
    try:
        return fromstring(data)
    except (DefusedXmlException, XmlSecurityError):
        log_audit("XML_SECURITY_ERROR", "defusedxml/security exception during fromstring")
        raise
    except (etree.ParseError, ValueError) as e:
        logger.error("XML fromstring error: %s", e)
        log_audit("XML_VALIDATION_ERROR", f"Fromstring error: {e}")
        raise XmlSecurityError(f"Ошибка парсинга XML: {e}")
