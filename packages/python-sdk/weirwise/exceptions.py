class WeirwiseError(Exception):
    """Base exception for Weirwise SDK."""

    pass


class AuthenticationError(WeirwiseError):
    """Raised when authentication fails (401/403)."""

    pass


class NotFoundError(WeirwiseError):
    """Raised when a resource is not found (404)."""

    pass


class APIError(WeirwiseError):
    """Raised when the server returns an unexpected error."""

    def __init__(self, status_code: int, message: str):
        super().__init__(f"API Error {status_code}: {message}")
        self.status_code = status_code
        self.message = message


class IngestionTimeoutError(WeirwiseError):
    """Raised when document ingestion times out."""

    def __init__(self, document_id, timeout: float):
        super().__init__(f"Ingestion for document {document_id} timed out after {timeout} seconds")
        self.document_id = document_id
        self.timeout = timeout


class IngestionFailedError(WeirwiseError):
    """Raised when document ingestion fails."""

    def __init__(self, document_id, message: str):
        super().__init__(f"Ingestion failed for document {document_id}: {message}")
        self.document_id = document_id
        self.message = message
