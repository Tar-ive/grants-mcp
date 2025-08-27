"""API client for the Simpler Grants API."""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base exception for API errors."""
    
    def __init__(self, status_code: int, message: str, response_data: Any = None):
        self.status_code = status_code
        self.message = message
        self.response_data = response_data
        super().__init__(f"API Error {status_code}: {message}")


class RateLimitError(APIError):
    """Exception for rate limit errors."""
    pass


class SimplerGrantsAPIClient:
    """
    Async HTTP client for the Simpler Grants API.
    
    Handles authentication, rate limiting, retries, and error handling.
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.simpler.grants.gov/v1",
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        Initialize the API client.
        
        Args:
            api_key: API key for authentication
            base_url: Base URL for the API
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Rate limit tracking
        self.rate_limit_remaining: Optional[int] = None
        self.rate_limit_reset: Optional[int] = None
        
        # HTTP client
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={
                "accept": "application/json",
                "X-Auth": api_key,
                "Content-Type": "application/json",
            },
        )
        
        logger.info(f"Initialized API client for {base_url}")
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    def _update_rate_limits(self, headers: httpx.Headers):
        """Update rate limit information from response headers."""
        if "X-RateLimit-Remaining" in headers:
            try:
                self.rate_limit_remaining = int(headers["X-RateLimit-Remaining"])
            except (ValueError, TypeError):
                pass
        
        if "X-RateLimit-Reset" in headers:
            try:
                self.rate_limit_reset = int(headers["X-RateLimit-Reset"])
            except (ValueError, TypeError):
                pass
    
    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to the API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            json_data: JSON body data
            
        Returns:
            Parsed JSON response
            
        Raises:
            APIError: For API errors
            RateLimitError: For rate limit errors
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = await self.client.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
            )
            
            # Update rate limit information
            self._update_rate_limits(response.headers)
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After", "60")
                logger.warning(f"Rate limited. Retry after {retry_after} seconds")
                raise RateLimitError(
                    429,
                    f"Rate limit exceeded. Retry after {retry_after} seconds",
                    {"retry_after": retry_after}
                )
            
            # Handle other errors
            if response.status_code >= 400:
                error_data = None
                try:
                    error_data = response.json()
                except Exception:
                    pass
                
                raise APIError(
                    response.status_code,
                    response.text[:500],  # Truncate long error messages
                    error_data
                )
            
            # Parse JSON response
            return response.json()
            
        except httpx.TimeoutException as e:
            logger.error(f"Request timeout: {url}")
            raise APIError(0, f"Request timeout: {e}")
        except httpx.NetworkError as e:
            logger.error(f"Network error: {url}")
            raise APIError(0, f"Network error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise
    
    async def check_health(self) -> Dict[str, Any]:
        """
        Check API health status.
        
        Returns:
            Health status information
        """
        try:
            start_time = time.time()
            
            # Make a minimal request to check API availability
            response = await self._make_request(
                "POST",
                "/opportunities/search",
                json_data={"pagination": {"page_size": 1, "page_offset": 1}}
            )
            
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            return {
                "status": "healthy",
                "response_time": round(response_time, 2),
                "rate_limit_remaining": self.rate_limit_remaining,
            }
            
        except APIError as e:
            if e.status_code == 503:
                return {"status": "down", "error": str(e)}
            elif e.status_code == 429:
                return {"status": "rate_limited", "error": str(e)}
            else:
                return {"status": "degraded", "error": str(e)}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def search_opportunities(
        self,
        query: Optional[str] = None,
        filters: Optional[Dict] = None,
        pagination: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Search for grant opportunities.
        
        Args:
            query: Search query string
            filters: Filter parameters
            pagination: Pagination parameters
            
        Returns:
            Search results with opportunities
        """
        # Build request body
        request_body = {}
        
        if query:
            request_body["query"] = query
        
        if filters:
            request_body["filters"] = filters
        else:
            # Default to current and forecasted opportunities
            request_body["filters"] = {
                "opportunity_status": {
                    "one_of": ["posted", "forecasted"]
                }
            }
        
        if pagination:
            # Ensure page_offset is present (required field)
            if "page_offset" not in pagination:
                pagination["page_offset"] = 1
            request_body["pagination"] = pagination
        else:
            # Default pagination
            request_body["pagination"] = {
                "page_size": 25,
                "page_offset": 1,
                "order_by": "opportunity_id",
                "sort_direction": "descending"
            }
        
        logger.debug(f"Searching opportunities with params: {request_body}")
        
        response = await self._make_request(
            "POST",
            "/opportunities/search",
            json_data=request_body
        )
        
        # Log summary
        total = response.get("pagination_info", {}).get("total_records", 0)
        returned = len(response.get("data", []))
        logger.info(f"Found {total} opportunities, returned {returned}")
        
        return response
    
    async def get_opportunity(self, opportunity_id: str) -> Dict[str, Any]:
        """
        Get a specific opportunity by ID.
        
        Args:
            opportunity_id: Opportunity ID
            
        Returns:
            Opportunity details
        """
        logger.debug(f"Fetching opportunity: {opportunity_id}")
        
        response = await self._make_request(
            "GET",
            f"/opportunities/{opportunity_id}"
        )
        
        return response
    
    async def search_agencies(
        self,
        query: Optional[str] = None,
        filters: Optional[Dict] = None,
        pagination: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Search for agencies.
        
        Args:
            query: Search query string
            filters: Filter parameters
            pagination: Pagination parameters
            
        Returns:
            Search results with agencies
        """
        # Build request body
        request_body = {}
        
        if query:
            request_body["query"] = query
        
        if filters:
            request_body["filters"] = filters
        
        if pagination:
            request_body["pagination"] = pagination
        else:
            request_body["pagination"] = {
                "page_size": 25,
                "page_offset": 1
            }
        
        logger.debug(f"Searching agencies with params: {request_body}")
        
        response = await self._make_request(
            "POST",
            "/agencies/search",
            json_data=request_body
        )
        
        return response