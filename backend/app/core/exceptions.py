from typing import Any


class RAGException(Exception):
    """Base exception for application errors"""

    error_code = "INTERNAL_ERROR"
    default_message = "An unexpected application error occurred"

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        resolved_message = message or self.default_message

        super().__init__(resolved_message)

        self.message = resolved_message
        self.details = details or {}

    def __str__(self) -> str:
        return self.message


class AuthenticationError(RAGException):
    """Raised when authentication credentials are missing or invalid"""

    error_code = "AUTHENTICATION_ERROR"
    default_message = "Authentication credentials are invalid or missing"


class AuthorizationError(RAGException):
    """Raised when a user cannot access a protected resource"""

    error_code = "AUTHORIZATION_ERROR"
    default_message = "You do not have permission to access this resource"


class ValidationError(RAGException):
    """Raised when request data or uploaded content is invalid"""

    error_code = "VALIDATION_ERROR"
    default_message = "The provided data is invalid"


class ConflictError(RAGException):
    """Raised when a request conflicts with an existing resource"""

    error_code = "CONFLICT_ERROR"
    default_message = "The requested operation conflicts with an existing resource"


class NotFoundError(RAGException):
    """Raised when a requested resource cannot be found"""

    error_code = "NOT_FOUND"
    default_message = "The requested resource was not found"


class StorageError(RAGException):
    """Raised when file storage operations fail"""

    error_code = "STORAGE_ERROR"
    default_message = "A file storage operation failed"


class ExtractionError(RAGException):
    """Raised when document text extraction fails"""

    error_code = "EXTRACTION_ERROR"
    default_message = "Document content could not be extracted"


class OCRRequiredError(ExtractionError):
    """Raised when a document requires optical character recognition"""

    error_code = "OCR_REQUIRED"
    default_message = "This document contains little or no extractable text and requires OCR"

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        resolved_details = {
            "ocr_required": True,
            **(details or {}),
        }

        super().__init__(
            message=message or self.default_message,
            details=resolved_details,
        )


class VectorDBError(RAGException):
    """Raised when vector storage or retrieval operations fail"""

    error_code = "VECTOR_DB_ERROR"
    default_message = "A vector database operation failed"


class DatabaseError(RAGException):
    """Raised when a relational database operation fails"""

    error_code = "DATABASE_ERROR"
    default_message = "A database operation failed"


class ProcessingError(RAGException):
    """Raised when document processing fails"""

    error_code = "PROCESSING_ERROR"
    default_message = "Document processing failed"


class EmbeddingError(ProcessingError):
    """Raised when document embedding generation fails"""

    error_code = "EMBEDDING_ERROR"
    default_message = "Document embeddings could not be generated"


class RetrievalError(RAGException):
    """Raised when document retrieval fails"""

    error_code = "RETRIEVAL_ERROR"
    default_message = "Relevant document content could not be retrieved"


class LLMServiceError(RAGException):
    """Raised when the language model service fails"""

    error_code = "LLM_SERVICE_ERROR"
    default_message = "The language model service could not complete the request"


class ServiceUnavailableError(RAGException):
    """Raised when a required external service is unavailable"""

    error_code = "SERVICE_UNAVAILABLE"
    default_message = "A required service is currently unavailable"


class RateLimitError(RAGException):
    """Raised when a request exceeds an allowed usage limit"""

    error_code = "RATE_LIMIT_EXCEEDED"
    default_message = "Too many requests were submitted"


class FileTooLargeError(ValidationError):
    """Raised when an uploaded file exceeds the configured size limit"""

    error_code = "FILE_TOO_LARGE"
    default_message = "The uploaded file exceeds the allowed size limit"


class UnsupportedFileTypeError(ValidationError):
    """Raised when an uploaded file type is not supported"""

    error_code = "UNSUPPORTED_FILE_TYPE"
    default_message = "The uploaded file type is not supported"


class DuplicateDocumentError(ConflictError):
    """Raised when the same document has already been uploaded"""

    error_code = "DUPLICATE_DOCUMENT"
    default_message = "This document has already been uploaded"
