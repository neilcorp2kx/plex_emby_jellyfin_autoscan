"""
Custom exceptions for the application.

This module provides a hierarchy of custom exceptions for consistent
error handling across the application.
"""


class APIError(Exception):
    """
    Custom API error for consistent error responses.

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code
        error_code: Machine-readable error code
    """

    def __init__(self, message: str, status_code: int = 500, error_code: str = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or 'INTERNAL_ERROR'
        super().__init__(self.message)


class ValidationError(APIError):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: str = None):
        error_code = f'VALIDATION_ERROR_{field.upper()}' if field else 'VALIDATION_ERROR'
        super().__init__(message, status_code=400, error_code=error_code)
        self.field = field


class AuthenticationError(APIError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, status_code=401, error_code='AUTHENTICATION_ERROR')


class AuthorizationError(APIError):
    """Raised when authorization fails."""

    def __init__(self, message: str = "Access denied"):
        super().__init__(message, status_code=403, error_code='AUTHORIZATION_ERROR')


class NotFoundError(APIError):
    """Raised when a resource is not found."""

    def __init__(self, message: str = "Resource not found", resource: str = None):
        error_code = f'{resource.upper()}_NOT_FOUND' if resource else 'NOT_FOUND'
        super().__init__(message, status_code=404, error_code=error_code)
        self.resource = resource


class ServiceUnavailableError(APIError):
    """Raised when an external service is unavailable."""

    def __init__(self, message: str, service: str = None):
        error_code = f'{service.upper()}_UNAVAILABLE' if service else 'SERVICE_UNAVAILABLE'
        super().__init__(message, status_code=503, error_code=error_code)
        self.service = service
