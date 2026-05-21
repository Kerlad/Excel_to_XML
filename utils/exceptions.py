import logging

logger = logging.getLogger(__name__)


class FileTooLargeError(ValueError):
    def __init__(self, file_path: str, size_mb: float, max_size_mb: int):
        self.file_path = file_path
        self.size_mb = size_mb
        self.max_size_mb = max_size_mb
        msg = f"Файл превышает лимит {max_size_mb} МБ ({size_mb:.1f} МБ)"
        logger.warning("FileTooLargeError: size %.1f MB (max %d MB)", size_mb, max_size_mb)
        super().__init__(msg)


class XmlSecurityError(ValueError):
    def __init__(self, message: str, detail: str = ""):
        self.detail = detail
        logger.warning("XmlSecurityError: %s", message)
        super().__init__(message)


class ImportLimitExceededError(ValueError):
    def __init__(self, message: str):
        logger.warning("ImportLimitExceededError: %s", message)
        super().__init__(message)


class ImportCancelledError(Exception):
    """Raised when the user cancels an import operation."""
    def __init__(self, message: str = "Import cancelled by user"):
        logger.info("ImportCancelledError: %s", message)
        super().__init__(message)
