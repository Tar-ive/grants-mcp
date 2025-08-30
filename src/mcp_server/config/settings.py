"""Configuration settings for the Grants Analysis MCP Server."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Settings:
    """Server configuration settings."""
    
    # API Configuration
    api_key: str
    api_base_url: str = "https://api.simpler.grants.gov/v1"
    
    # Cache Configuration
    cache_ttl: int = 300  # Time-to-live in seconds (5 minutes)
    max_cache_size: int = 1000  # Maximum number of cached items
    
    # Rate Limiting Configuration
    rate_limit_requests: int = 100  # Maximum requests per period
    rate_limit_period: int = 60  # Period in seconds
    
    # Server Configuration
    server_name: str = "grantsmanship-mcp"
    server_version: str = "3.0.0"
    server_description: str = "Comprehensive grants analysis and discovery platform"
    
    # Logging Configuration
    log_level: str = "INFO"
    
    # Performance Configuration
    request_timeout: int = 30  # Timeout for API requests in seconds
    max_retries: int = 3  # Maximum number of retries for failed requests
    
    def validate(self) -> None:
        """Validate settings."""
        if not self.api_key:
            raise ValueError("API key is required")
        
        if self.cache_ttl <= 0:
            raise ValueError("Cache TTL must be positive")
        
        if self.max_cache_size <= 0:
            raise ValueError("Max cache size must be positive")
        
        if self.rate_limit_requests <= 0:
            raise ValueError("Rate limit requests must be positive")
        
        if self.rate_limit_period <= 0:
            raise ValueError("Rate limit period must be positive")