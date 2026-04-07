# ---------------------------------------------------------------
# Copyright (c) 2025-2026, NVIDIA CORPORATION. All rights reserved.
# ---------------------------------------------------------------


"""
Custom exceptions for the Boltz-2 Python client.

This module defines exception classes that provide specific error handling
for different types of failures that can occur when using the Boltz-2 API.
"""

from typing import Optional, Dict, Any


class Boltz2Error(Exception):
    """Base exception class for all Boltz-2 client errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message


# Alias for backward compatibility
Boltz2ClientError = Boltz2Error


class Boltz2APIError(Boltz2Error):
    """Exception raised when the API returns an error response."""
    
    def __init__(
        self, 
        message: str, 
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details)
        self.status_code = status_code
        self.response_data = response_data or {}
    
    def __str__(self) -> str:
        parts = [self.message]
        if self.status_code:
            parts.append(f"Status: {self.status_code}")
        if self.response_data:
            parts.append(f"Response: {self.response_data}")
        if self.details:
            parts.append(f"Details: {self.details}")
        return " | ".join(parts)


class Boltz2TimeoutError(Boltz2Error):
    """Exception raised when a request times out."""
    
    def __init__(self, message: str, timeout_seconds: Optional[float] = None):
        super().__init__(message)
        self.timeout_seconds = timeout_seconds
    
    def __str__(self) -> str:
        if self.timeout_seconds:
            return f"{self.message} (Timeout: {self.timeout_seconds}s)"
        return self.message


class Boltz2ConnectionError(Boltz2Error):
    """Exception raised when there are connection issues."""
    
    def __init__(self, message: str, endpoint: Optional[str] = None):
        super().__init__(message)
        self.endpoint = endpoint
    
    def __str__(self) -> str:
        if self.endpoint:
            return f"{self.message} (Endpoint: {self.endpoint})"
        return self.message


class Boltz2ValidationError(Boltz2Error):
    """Exception raised when input validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.field = field
        self.value = value
    
    def __str__(self) -> str:
        parts = [self.message]
        if self.field:
            parts.append(f"Field: {self.field}")
        if self.value is not None:
            parts.append(f"Value: {self.value}")
        if self.details:
            parts.append(f"Details: {self.details}")
        return " | ".join(parts)


class Boltz2AuthenticationError(Boltz2Error):
    """Exception raised when authentication fails."""
    pass


class Boltz2RateLimitError(Boltz2APIError):
    """Exception raised when rate limits are exceeded."""
    
    def __init__(
        self, 
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after
    
    def __str__(self) -> str:
        base_str = super().__str__()
        if self.retry_after:
            return f"{base_str} | Retry after: {self.retry_after}s"
        return base_str


class Boltz2ServiceUnavailableError(Boltz2APIError):
    """Exception raised when the service is unavailable."""
    
    def __init__(self, message: str = "Service temporarily unavailable", **kwargs):
        super().__init__(message, **kwargs)


class Boltz2InvalidResponseError(Boltz2Error):
    """Exception raised when the API returns an invalid or unexpected response."""
    
    def __init__(self, message: str, response_content: Optional[str] = None):
        super().__init__(message)
        self.response_content = response_content
    
    def __str__(self) -> str:
        if self.response_content:
            # Truncate very long responses
            content = self.response_content[:500]
            if len(self.response_content) > 500:
                content += "..."
            return f"{self.message} | Response: {content}"
        return self.message


class Boltz2ConfigurationError(Boltz2Error):
    """Exception raised when there are configuration issues."""
    pass


# Convenience function to create appropriate exceptions from HTTP responses
def create_api_exception(
    status_code: int,
    response_text: str,
    endpoint: Optional[str] = None
) -> Boltz2APIError:
    """
    Create an appropriate API exception based on the HTTP status code.
    
    Args:
        status_code: HTTP status code
        response_text: Response body text
        endpoint: API endpoint that was called
        
    Returns:
        Appropriate Boltz2APIError subclass
    """
    details = {"endpoint": endpoint} if endpoint else {}
    
    if status_code == 401:
        return Boltz2AuthenticationError(
            "Authentication failed", 
            details=details
        )
    elif status_code == 429:
        return Boltz2RateLimitError(
            "Rate limit exceeded",
            status_code=status_code,
            response_data={"text": response_text},
            details=details
        )
    elif status_code == 503:
        return Boltz2ServiceUnavailableError(
            "Service unavailable",
            status_code=status_code,
            response_data={"text": response_text},
            details=details
        )
    elif 400 <= status_code < 500:
        return Boltz2ValidationError(
            f"Client error: {response_text}",
            details={**details, "status_code": status_code}
        )
    elif 500 <= status_code < 600:
        return Boltz2APIError(
            f"Server error: {response_text}",
            status_code=status_code,
            response_data={"text": response_text},
            details=details
        )
    else:
        return Boltz2APIError(
            f"Unexpected status code {status_code}: {response_text}",
            status_code=status_code,
            response_data={"text": response_text},
            details=details
        ) 