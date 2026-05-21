"""
Audit trail module for ISPDn.
Logs security-relevant events without personal data.
All audit events are tamper-evident (integrity-checked).
"""
import os
import logging
import hashlib
import hmac
from datetime import datetime
from logging.handlers import RotatingFileHandler

audit_logger = logging.getLogger("audit")

AUDIT_EVENTS = {
    "SEND_XML": "XML sent to server",
    "SEND_XML_SIGNED": "Signed XML sent to server",
    "QUERY_SETID": "Query by SetId",
    "QUERY_SNILS": "Query by SNILS",
    "IMPORT_XLSX": "Import from XLSX",
    "IMPORT_XML": "Import from XML",
    "EXPORT_XML": "Export to XML",
    "EXPORT_XLSX": "Export to XLSX",
    "LOGIN": "API key used",
    "BACKUP": "Database backup created",
    "KEY_ACCESS": "Master key accessed",
    "KEY_ROTATION": "Master key rotated",
    "KEY_BACKUP": "Master key backup created",
    "KEY_RESTORE": "Master key restored from backup",
    "PASSPHRASE_SET": "Passphrase protection enabled",
    "PASSPHRASE_REMOVED": "Passphrase protection removed",
    "TLS_WARNING": "TLS verification disabled",
    "TLS_ERROR": "TLS connection error",
    "XML_VALIDATION_ERROR": "XML/XSD validation error",
    "XML_SECURITY_ERROR": "XML security violation detected",
    "EXPORT_PLAN": "Training plan exported",
    "EXPORT_SNAPSHOT": "Current snapshot exported",
    "EXPORT_TRAINED_REPORT": "Trained employees report exported",
    "IMPORT_CANCELLED": "Import cancelled by user",
    "SECURITY_WARNING": "Security policy violation detected",
    "STARTUP": "Application started",
    "SHUTDOWN": "Application shutdown",
    "CRASH": "Application crash",
    "ERROR_RESPONSE_SAVED": "Server error response saved",
    "PROXY_CHANGE": "Proxy configuration changed",
    "BACKEND_CHANGE": "Transport backend changed",
    "AUDIT_INTEGRITY_CHECK": "Audit log integrity check",
    "SESSION_LOCK": "Session locked due to inactivity",
    "SESSION_UNLOCK": "Session unlocked via passphrase",
}

_AUDIT_HMAC_KEY = b""


def _get_hmac_key() -> bytes:
    global _AUDIT_HMAC_KEY
    if not _AUDIT_HMAC_KEY:
        try:
            from utils.crypto import get_key_fingerprint
            fp = get_key_fingerprint()
            _AUDIT_HMAC_KEY = fp.encode('utf-8')
        except Exception:
            _AUDIT_HMAC_KEY = b"EXCEL_XML_AUDIT_V3"
    return _AUDIT_HMAC_KEY


def _compute_audit_hmac(msg: str) -> str:
    return hmac.new(
        _get_hmac_key(),
        msg.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()[:12]


def setup_audit_log(log_dir: str):
    from utils.logger import SensitiveDataFilter
    log_path = os.path.join(log_dir, "audit.log")
    handler = RotatingFileHandler(
        log_path, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
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
    """Log a security-audit event with HMAC integrity protection."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    event_name = AUDIT_EVENTS.get(event, event)
    msg = event_name
    if detail:
        # Mask any sensitive data in detail
        from utils.logger import filter_sensitive_text
        safe_detail = filter_sensitive_text(detail)
        msg += f" | {safe_detail}"
    hmac_tag = _compute_audit_hmac(f"{timestamp}|{msg}")
    audit_logger.info("[%s] %s", hmac_tag, msg)
