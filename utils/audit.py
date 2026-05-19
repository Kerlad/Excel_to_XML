"""
Audit trail module.
Logs security-relevant events without personal data.
"""
import os
import logging
from datetime import datetime

audit_logger = logging.getLogger("audit")

AUDIT_EVENTS = {
    "SEND_XML": "XML sent to server",
    "QUERY_SETID": "Query by SetId",
    "QUERY_SNILS": "Query by SNILS",
    "IMPORT_XLSX": "Import from XLSX",
    "IMPORT_XML": "Import from XML",
    "EXPORT_XML": "Export to XML",
    "LOGIN": "API key used",
    "BACKUP": "Database backup created",
    "EXPORT_XLSX": "Export to XLSX",
}


def setup_audit_log(log_dir: str):
    from utils.logger import SensitiveDataFilter
    log_path = os.path.join(log_dir, "audit.log")
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    ))
    handler.setLevel(logging.INFO)
    handler.addFilter(SensitiveDataFilter())
    audit_logger.addHandler(handler)
    audit_logger.setLevel(logging.INFO)
    audit_logger.propagate = False
    return log_path


def log_audit(event: str, detail: str = ""):
    msg = f"{AUDIT_EVENTS.get(event, event)}"
    if detail:
        msg += f" | {detail}"
    audit_logger.info(msg)
