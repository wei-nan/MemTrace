class MemTraceError(Exception):
    """Base exception class for MemTrace SDK."""
    pass

class AuthenticationError(MemTraceError):
    """Raised when authentication fails (401)."""
    pass

class NotFoundError(MemTraceError):
    """Raised when a resource is not found (404)."""
    pass

class APIError(MemTraceError):
    """Raised when the API returns an error response (non-2xx)."""
    def __init__(self, message: str, status_code: int, response_body: str = ""):
        super().__init__(f"{message} (Status: {status_code})")
        self.status_code = status_code
        self.response_body = response_body
