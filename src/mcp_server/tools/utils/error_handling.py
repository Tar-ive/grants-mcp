"""Comprehensive error handling utilities for the MCP server."""

import logging
import traceback
from datetime import datetime
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)


class MCPError(Exception):
    """Base exception for MCP-related errors."""
    
    def __init__(self, message: str, error_code: str = "INTERNAL_ERROR", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()


class APIError(MCPError):
    """Exception for external API errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        super().__init__(message, "API_ERROR")
        self.status_code = status_code
        self.response_data = response_data


class ValidationError(MCPError):
    """Exception for data validation errors."""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Any = None):
        super().__init__(message, "VALIDATION_ERROR")
        self.field = field
        self.value = value


class CacheError(MCPError):
    """Exception for cache-related errors."""
    
    def __init__(self, message: str, operation: Optional[str] = None):
        super().__init__(message, "CACHE_ERROR")
        self.operation = operation


class NetworkError(MCPError):
    """Exception for network-related errors."""
    
    def __init__(self, message: str, url: Optional[str] = None):
        super().__init__(message, "NETWORK_ERROR")
        self.url = url


class RateLimitError(MCPError):
    """Exception for rate limiting errors."""
    
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message, "RATE_LIMIT_ERROR")
        self.retry_after = retry_after


def format_error_response(error: Exception, operation: str = "unknown") -> str:
    """
    Format an error into a user-friendly response string.
    
    Args:
        error: The exception that occurred
        operation: The operation being performed when error occurred
        
    Returns:
        Formatted error message string
    """
    error_type = type(error).__name__
    error_message = str(error)
    
    # Sanitize sensitive information
    sanitized_message = sanitize_error_message(error_message)
    
    # Format different types of errors
    if isinstance(error, APIError):
        if error.status_code:
            return f"API Error ({error.status_code}): {sanitized_message}"
        return f"API Error: {sanitized_message}"
        
    elif isinstance(error, ValidationError):
        if error.field:
            return f"Validation Error in field '{error.field}': {sanitized_message}"
        return f"Validation Error: {sanitized_message}"
        
    elif isinstance(error, NetworkError):
        return f"Network Error: Unable to connect to grants API. Please check your internet connection and try again."
        
    elif isinstance(error, RateLimitError):
        if error.retry_after:
            return f"Rate Limit Exceeded: Please wait {error.retry_after} seconds before trying again."
        return "Rate Limit Exceeded: Too many requests. Please try again later."
        
    elif isinstance(error, CacheError):
        return f"Cache Error during {operation}: {sanitized_message}"
        
    elif hasattr(error, 'status') and hasattr(error, 'message'):
        # Handle aiohttp errors
        status = getattr(error, 'status', None)
        if status == 401:
            return "Authentication Error: Invalid API key. Please check your API key configuration."
        elif status == 403:
            return "Authorization Error: Access denied. Please verify your API permissions."
        elif status == 404:
            return "Resource Not Found: The requested resource could not be found."
        elif status == 429:
            return "Rate Limit Exceeded: Too many requests. Please try again later."
        elif status == 500:
            return "Server Error: The grants API is experiencing issues. Please try again later."
        elif status == 503:
            return "Service Unavailable: The grants API is temporarily unavailable. Please try again later."
        else:
            return f"HTTP Error ({status}): {sanitized_message}"
            
    elif 'timeout' in error_message.lower():
        return f"Request Timeout: The operation took too long to complete. Please try again."
        
    elif 'connection' in error_message.lower():
        return f"Connection Error: Unable to connect to the grants API. Please check your network connection."
        
    else:
        # Generic error handling
        logger.error(f"Unexpected error in {operation}: {error_type}: {error_message}")
        logger.debug(f"Full traceback: {traceback.format_exc()}")
        return f"An unexpected error occurred during {operation}. Please try again or contact support if the issue persists."


def sanitize_error_message(message: str) -> str:
    """
    Remove sensitive information from error messages.
    
    Args:
        message: Original error message
        
    Returns:
        Sanitized error message
    """
    # List of sensitive patterns to remove or replace
    sensitive_patterns = [
        ('api_key', '***API_KEY***'),
        ('apikey', '***API_KEY***'),
        ('password', '***PASSWORD***'),
        ('token', '***TOKEN***'),
        ('secret', '***SECRET***'),
        ('auth', '***AUTH***'),
        ('bearer', '***BEARER***'),
    ]
    
    sanitized = message
    
    for pattern, replacement in sensitive_patterns:
        # Case-insensitive replacement
        import re
        sanitized = re.sub(
            rf'{pattern}[=:]\s*[^\s&]+',
            f'{pattern}={replacement}',
            sanitized,
            flags=re.IGNORECASE
        )
    
    return sanitized


def log_error_context(error: Exception, operation: str, context: Optional[Dict[str, Any]] = None):
    """
    Log error with additional context for debugging.
    
    Args:
        error: The exception that occurred
        operation: The operation being performed
        context: Additional context information
    """
    context = context or {}
    
    log_data = {
        'operation': operation,
        'error_type': type(error).__name__,
        'error_message': str(error),
        'timestamp': datetime.now().isoformat(),
        **context
    }
    
    # Remove sensitive data from log context
    sanitized_context = {
        k: '***REDACTED***' if 'api_key' in k.lower() or 'password' in k.lower() or 'token' in k.lower() else v
        for k, v in log_data.items()
    }
    
    if isinstance(error, MCPError):
        logger.error(f"MCP Error in {operation}: {error.error_code} - {error.message}", extra=sanitized_context)
    else:
        logger.error(f"Unexpected error in {operation}: {type(error).__name__} - {str(error)}", extra=sanitized_context)
        logger.debug(f"Full traceback: {traceback.format_exc()}")


def handle_api_error(error: Exception, url: str = "", operation: str = "API call") -> str:
    """
    Handle API-specific errors with appropriate user messages.
    
    Args:
        error: The API error that occurred
        url: The URL that was being accessed
        operation: Description of the operation
        
    Returns:
        User-friendly error message
    """
    # Log the error for debugging
    log_error_context(error, operation, {"url": url})
    
    # Handle specific HTTP status codes
    if hasattr(error, 'status'):
        status_code = error.status
        
        status_messages = {
            400: "Invalid request parameters. Please check your search criteria.",
            401: "Authentication failed. Please verify your API key is correct and active.",
            403: "Access denied. Your API key may not have permission for this operation.",
            404: "The requested resource was not found. The API endpoint may have changed.",
            429: "Too many requests. Please wait before trying again to avoid rate limits.",
            500: "The grants API is experiencing technical difficulties. Please try again later.",
            502: "The grants API gateway is unavailable. Please try again in a few minutes.",
            503: "The grants API is temporarily unavailable for maintenance. Please try again later.",
            504: "The grants API request timed out. Please try again with a simpler query."
        }
        
        if status_code in status_messages:
            return status_messages[status_code]
        elif 400 <= status_code < 500:
            return f"Client error ({status_code}): There was an issue with the request. Please check your parameters and try again."
        elif 500 <= status_code < 600:
            return f"Server error ({status_code}): The grants API is having issues. Please try again later."
    
    # Handle network-related errors
    error_message = str(error).lower()
    
    if 'timeout' in error_message:
        return "The request took too long to complete. Please try again or simplify your search."
    elif 'connection' in error_message or 'network' in error_message:
        return "Unable to connect to the grants API. Please check your internet connection."
    elif 'ssl' in error_message or 'certificate' in error_message:
        return "SSL/TLS error connecting to the grants API. This may be a temporary network issue."
    elif 'dns' in error_message or 'resolve' in error_message:
        return "Unable to resolve the grants API hostname. Please check your DNS settings."
    else:
        return "An unexpected error occurred while accessing the grants API. Please try again."


def create_error_response(error: Exception, request_id: Optional[Union[str, int]] = None) -> Dict[str, Any]:
    """
    Create a standardized error response dictionary.
    
    Args:
        error: The exception that occurred
        request_id: Optional request identifier
        
    Returns:
        Standardized error response dictionary
    """
    response = {
        "jsonrpc": "2.0",
        "error": {
            "code": -32000,  # Default JSON-RPC error code
            "message": format_error_response(error),
            "data": {
                "type": type(error).__name__,
                "timestamp": datetime.now().isoformat()
            }
        }
    }
    
    if request_id is not None:
        response["id"] = request_id
    
    # Add specific error codes for different error types
    if isinstance(error, ValidationError):
        response["error"]["code"] = -32602  # Invalid params
    elif isinstance(error, APIError):
        response["error"]["code"] = -32001  # Custom: API error
        if error.status_code:
            response["error"]["data"]["status_code"] = error.status_code
    elif isinstance(error, NetworkError):
        response["error"]["code"] = -32002  # Custom: Network error
    elif isinstance(error, RateLimitError):
        response["error"]["code"] = -32003  # Custom: Rate limit error
        if error.retry_after:
            response["error"]["data"]["retry_after"] = error.retry_after
    elif isinstance(error, CacheError):
        response["error"]["code"] = -32004  # Custom: Cache error
    
    return response


class ErrorHandler:
    """Context manager for comprehensive error handling."""
    
    def __init__(self, operation: str, context: Optional[Dict[str, Any]] = None):
        self.operation = operation
        self.context = context or {}
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            log_error_context(exc_val, self.operation, self.context)
        return False  # Don't suppress exceptions
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            log_error_context(exc_val, self.operation, self.context)
        return False


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
    """
    Decorator for retrying operations with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            import asyncio
            import random
            
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    # Don't retry on certain error types
                    if isinstance(e, (ValidationError, MCPError)) and e.error_code in ['VALIDATION_ERROR']:
                        raise
                        
                    if attempt >= max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded for {func.__name__}")
                        raise
                    
                    # Calculate delay with exponential backoff and jitter
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    jitter = random.uniform(0, 0.1) * delay  # Add up to 10% jitter
                    total_delay = delay + jitter
                    
                    logger.warning(f"Retry {attempt + 1}/{max_retries} for {func.__name__} after {total_delay:.2f}s: {str(e)}")
                    await asyncio.sleep(total_delay)
            
            # This should never be reached, but just in case
            raise last_exception
            
        return wrapper
    return decorator