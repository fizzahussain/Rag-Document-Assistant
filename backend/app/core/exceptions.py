class RAGException(Exception):
    """Base exception class for all custom application errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        details: dict | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class ValidationError(RAGException):
    """Raised when file validation or payload validation fails."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(
            message=message, error_code="VALIDATION_ERROR", details=details
        )


class StorageError(RAGException):
    """Raised when file storage operations fail."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message=message, error_code="STORAGE_ERROR", details=details)


class ExtractionError(RAGException):
    """Raised when text extraction from a file fails."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(
            message=message, error_code="EXTRACTION_ERROR", details=details
        )


class OCRRequiredError(ExtractionError):
    """Raised when a PDF contains no extractable text (e.g. scanned image-only PDF)."""

    def __init__(
        self,
        message: str = "Scanned PDF detected: Image-only file requires OCR processing.",
    ):
        super().__init__(message=message, details={"ocr_required": True})


class VectorDBError(RAGException):
    """Raised when operations on Qdrant vector database fail."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message=message, error_code="VECTOR_DB_ERROR", details=details)


class NotFoundError(RAGException):
    """Raised when a requested resource (document, conversation, message) is not found."""

    def __init__(self, message: str = "Resource not found."):
        super().__init__(message=message, error_code="NOT_FOUND")
