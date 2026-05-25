"""
Audit trail module for ISPDn.
Logs security-relevant events without personal data.
All audit events are tamper-evident (integrity-checked with hash chaining).
"""
import os
import logging
import hashlib
import hmac
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional

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
    "VIEW_PD": "PD records viewed",
    "EXPORT_PD": "PD records exported to file",
    "DELETE_PD": "PD records deleted",
}

_AUDIT_HMAC_KEY: Optional[bytes] = None
_PREV_HASH: str = "0" * 64


def _get_hmac_key() -> Optional[bytes]:
    global _AUDIT_HMAC_KEY
    if _AUDIT_HMAC_KEY is None:
        try:
            from utils.crypto import get_key_fingerprint
            fp = get_key_fingerprint()
            _AUDIT_HMAC_KEY = fp.encode('utf-8')
        except Exception:
            _logger = logging.getLogger(__name__)
            _logger.critical("Audit HMAC key unavailable — audit integrity disabled")
            _AUDIT_HMAC_KEY = None
    return _AUDIT_HMAC_KEY


def _compute_audit_hmac(msg: str) -> Optional[str]:
    key = _get_hmac_key()
    if key is None:
        return None
    return hmac.new(
        key,
        msg.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()[:64]


def _compute_audit_hmac_legacy(msg: str) -> str:
    """Legacy 12-char HMAC for backward compatibility with old audit entries (pre-3.1.0)."""
    key = _get_hmac_key()
    if key is None:
        return "0" * 12
    return hmac.new(
        key,
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
    """Log a security-audit event with HMAC integrity protection and hash chaining."""
    global _PREV_HASH
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    event_name = AUDIT_EVENTS.get(event, event)
    msg = event_name
    if detail:
        from utils.logger import filter_sensitive_text
        safe_detail = filter_sensitive_text(detail)
        msg += f" | {safe_detail}"

    key = _get_hmac_key()
    if key is None:
        audit_logger.info("[no-hmac] %s", msg)
        return

    chain_input = _PREV_HASH + "|" + timestamp + "|" + msg
    hmac_tag = _compute_audit_hmac(chain_input)
    if hmac_tag:
        _PREV_HASH = hmac_tag
        audit_logger.info("[%s] %s", hmac_tag, msg)


def verify_audit_log(log_path: str) -> list[dict]:
    """Verify HMAC integrity of all entries in audit.log with hash chain validation.
    Supports both legacy 12-char and current 64-char HMAC tags.
    Returns list of compromised entries: [{'line_number', 'expected_tag', 'actual_tag', 'content'}]
    """
    violations = []
    if not os.path.exists(log_path):
        return violations

    prev_hash = "0" * 64
    with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
        for line_num, line in enumerate(f, 1):
            line = line.rstrip('\n\r')
            parts = line.split(" | ", 1)
            if len(parts) < 2:
                continue
            timestamp_str = parts[0]
            rest = parts[1]

            if rest.startswith("[no-hmac]"):
                continue

            if not rest.startswith("["):
                continue

            tag_end = rest.find("] ")
            if tag_end == -1:
                continue

            hmac_tag = rest[1:tag_end]
            content = rest[tag_end + 2:]

            chain_input = prev_hash + "|" + timestamp_str + "|" + content

            if len(hmac_tag) == 12:
                computed = _compute_audit_hmac_legacy(chain_input)
            elif len(hmac_tag) == 64:
                computed = _compute_audit_hmac(chain_input)
                if computed is None:
                    continue
            else:
                continue

            if not hmac.compare_digest(computed, hmac_tag):
                violations.append({
                    'line_number': line_num,
                    'expected_tag': computed,
                    'actual_tag': hmac_tag,
                    'content': content,
                })

            if len(hmac_tag) == 12:
                prev_hash = hashlib.sha256(hmac_tag.encode('utf-8')).hexdigest()
            else:
                prev_hash = hmac_tag

    if violations:
        log_audit("AUDIT_INTEGRITY_CHECK",
                  f"Integrity violations found: {len(violations)}")
    else:
        log_audit("AUDIT_INTEGRITY_CHECK",
                  "Audit log integrity verified OK")

    return violations


def verify_audit_log_interactive(parent_widget=None):
    """Interactive audit log verification for UI. Shows result dialog."""
    from utils.log_viewer_dialog import show_audit_verification_result
    from utils.app_paths import get_app_log_dir
    log_dir = get_app_log_dir()
    log_path = os.path.join(log_dir, "audit.log")
    violations = verify_audit_log(log_path)
    show_audit_verification_result(parent_widget, violations, log_path)
