import logging

logger = logging.getLogger(__name__)


class FileTooLargeError(ValueError):
    def __init__(self, file_path: str, size_mb: float, max_size_mb: int):
        self.file_path = file_path
        self.size_mb = size_mb
        self.max_size_mb = max_size_mb
        msg = f"Файл превышает лимит {max_size_mb} МБ ({size_mb:.1f} МБ)"
        logger.warning(f"FileTooLargeError: {msg} — {file_path}")
        super().__init__(msg)


class XmlSecurityError(ValueError):
    def __init__(self, message: str, detail: str = ""):
        self.detail = detail
        logger.warning(f"XmlSecurityError: {message} {detail}")
        super().__init__(message)


class ImportLimitExceededError(ValueError):
    def __init__(self, message: str):
        logger.warning(f"ImportLimitExceededError: {message}")
        super().__init__(message)
