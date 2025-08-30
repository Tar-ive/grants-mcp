"""Optimized cache utilities for discovery tools."""

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class CacheKeyGenerator:
    """
    Optimized cache key generator with multiple strategies.
    
    Provides efficient and consistent cache key generation for different
    tool types and use cases.
    """
    
    # Predefined prefixes for different tool types
    TOOL_PREFIXES = {
        "opportunity_discovery": "od",
        "agency_landscape": "al",
        "funding_trend_scanner": "fts",
        "opportunity_density": "oden",
        "eligibility_checker": "ec",
        "strategic_advisor": "sa",
    }
    
    @staticmethod
    def _normalize_value(value: Any) -> Any:
        """
        Normalize values for consistent hashing.
        
        Args:
            value: Value to normalize
            
        Returns:
            Normalized value
        """
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return str(value).lower()
        elif isinstance(value, (list, tuple)):
            # Sort lists for consistent ordering
            return sorted([CacheKeyGenerator._normalize_value(v) for v in value])
        elif isinstance(value, dict):
            # Sort dictionary keys for consistent ordering
            return {
                k: CacheKeyGenerator._normalize_value(v)
                for k, v in sorted(value.items())
            }
        elif isinstance(value, (int, float)):
            return str(value)
        else:
            return str(value)
    
    @classmethod
    def generate_simple(cls, tool_name: str, **params) -> str:
        """
        Generate a simple cache key for basic queries.
        
        This is optimized for common cases with few parameters.
        
        Args:
            tool_name: Name of the tool
            **params: Tool parameters
            
        Returns:
            Cache key string
        """
        # Get tool prefix
        prefix = cls.TOOL_PREFIXES.get(tool_name, tool_name[:3])
        
        # Filter out None values and normalize
        clean_params = {}
        for key, value in params.items():
            if value is not None:
                clean_params[key] = cls._normalize_value(value)
        
        # For simple cases with few params, use a readable format
        if len(clean_params) <= 3:
            param_str = "_".join(
                f"{k}={v}" for k, v in sorted(clean_params.items())
            )
            # Replace problematic characters
            param_str = param_str.replace(" ", "_").replace("/", "_")
            
            # If short enough, use readable key
            if len(param_str) <= 100:
                return f"{prefix}:{param_str}"
        
        # Fall back to hash for complex cases
        return cls.generate_hash(tool_name, **params)
    
    @classmethod
    def generate_hash(cls, tool_name: str, **params) -> str:
        """
        Generate a hashed cache key for complex queries.
        
        This ensures consistent key length regardless of parameter complexity.
        
        Args:
            tool_name: Name of the tool
            **params: Tool parameters
            
        Returns:
            Hashed cache key string
        """
        # Get tool prefix
        prefix = cls.TOOL_PREFIXES.get(tool_name, tool_name[:3])
        
        # Normalize all parameters
        normalized = {}
        for key, value in params.items():
            normalized[key] = cls._normalize_value(value)
        
        # Create stable JSON representation
        key_data = {
            "tool": tool_name,
            "params": normalized
        }
        key_str = json.dumps(key_data, sort_keys=True, separators=(",", ":"))
        
        # Generate hash (using SHA256 for better distribution)
        hash_value = hashlib.sha256(key_str.encode()).hexdigest()[:16]
        
        return f"{prefix}:{hash_value}"
    
    @classmethod
    def generate_compound(
        cls,
        tool_name: str,
        primary_params: Dict[str, Any],
        secondary_params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a compound cache key with primary and secondary parameters.
        
        This is useful for hierarchical caching where some parameters are more
        important for cache invalidation than others.
        
        Args:
            tool_name: Name of the tool
            primary_params: Primary parameters (affect cache validity)
            secondary_params: Secondary parameters (for differentiation)
            
        Returns:
            Compound cache key string
        """
        # Get tool prefix
        prefix = cls.TOOL_PREFIXES.get(tool_name, tool_name[:3])
        
        # Normalize primary parameters
        primary_normalized = {}
        for key, value in primary_params.items():
            if value is not None:
                primary_normalized[key] = cls._normalize_value(value)
        
        # Generate primary hash (shorter)
        primary_str = json.dumps(primary_normalized, sort_keys=True, separators=(",", ":"))
        primary_hash = hashlib.md5(primary_str.encode()).hexdigest()[:8]
        
        # Handle secondary parameters if provided
        if secondary_params:
            secondary_normalized = {}
            for key, value in secondary_params.items():
                if value is not None:
                    secondary_normalized[key] = cls._normalize_value(value)
            
            secondary_str = json.dumps(secondary_normalized, sort_keys=True, separators=(",", ":"))
            secondary_hash = hashlib.md5(secondary_str.encode()).hexdigest()[:8]
            
            return f"{prefix}:{primary_hash}:{secondary_hash}"
        
        return f"{prefix}:{primary_hash}"
    
    @classmethod
    def generate_temporal(
        cls,
        tool_name: str,
        time_bucket: int = 3600,
        **params
    ) -> str:
        """
        Generate a temporal cache key that expires based on time buckets.
        
        This is useful for data that changes over time but can be cached
        within certain time windows.
        
        Args:
            tool_name: Name of the tool
            time_bucket: Time bucket size in seconds (default: 1 hour)
            **params: Tool parameters
            
        Returns:
            Temporal cache key string
        """
        import time
        
        # Get current time bucket
        current_bucket = int(time.time() / time_bucket)
        
        # Get tool prefix
        prefix = cls.TOOL_PREFIXES.get(tool_name, tool_name[:3])
        
        # Generate base key
        base_key = cls.generate_simple(tool_name, **params)
        
        # Combine with time bucket
        return f"{base_key}:t{current_bucket}"
    
    @classmethod
    def invalidate_pattern(cls, tool_name: str) -> str:
        """
        Generate a pattern for invalidating all cache entries for a tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Pattern string for cache invalidation
        """
        prefix = cls.TOOL_PREFIXES.get(tool_name, tool_name[:3])
        return f"{prefix}:*"


class CacheStrategy:
    """
    Cache strategy definitions for different tool types.
    
    Provides recommended caching strategies based on tool characteristics.
    """
    
    # TTL recommendations for different tool types (in seconds)
    TTL_RECOMMENDATIONS = {
        "opportunity_discovery": 300,       # 5 minutes - frequently changing
        "agency_landscape": 3600,          # 1 hour - relatively stable
        "funding_trend_scanner": 1800,     # 30 minutes - moderate change rate
        "opportunity_density": 600,        # 10 minutes - computed data
        "eligibility_checker": 7200,       # 2 hours - stable rules
        "strategic_advisor": 900,          # 15 minutes - analysis results
    }
    
    @classmethod
    def get_ttl(cls, tool_name: str, custom_ttl: Optional[int] = None) -> int:
        """
        Get recommended TTL for a tool.
        
        Args:
            tool_name: Name of the tool
            custom_ttl: Custom TTL override
            
        Returns:
            TTL in seconds
        """
        if custom_ttl is not None:
            return custom_ttl
        
        return cls.TTL_RECOMMENDATIONS.get(tool_name, 300)  # Default 5 minutes
    
    @classmethod
    def should_cache(
        cls,
        tool_name: str,
        result_size: int,
        execution_time: float
    ) -> bool:
        """
        Determine if a result should be cached based on heuristics.
        
        Args:
            tool_name: Name of the tool
            result_size: Size of the result in bytes
            execution_time: Time taken to generate result in seconds
            
        Returns:
            True if result should be cached
        """
        # Don't cache very small results (likely errors)
        if result_size < 100:
            return False
        
        # Don't cache extremely large results (memory concerns)
        if result_size > 10_000_000:  # 10MB
            return False
        
        # Cache if execution took significant time
        if execution_time > 0.5:  # 500ms
            return True
        
        # Tool-specific logic
        if tool_name in ["opportunity_discovery", "funding_trend_scanner"]:
            # Always cache these expensive operations
            return True
        
        if tool_name == "eligibility_checker":
            # Cache only if result is substantial
            return result_size > 1000
        
        # Default: cache if execution was not trivial
        return execution_time > 0.1


def optimize_cache_for_tool(
    cache,
    tool_name: str,
    params: Dict[str, Any],
    generate_key_method: str = "simple"
) -> tuple[str, int]:
    """
    Helper function to optimize cache usage for a specific tool.
    
    Args:
        cache: Cache instance
        tool_name: Name of the tool
        params: Tool parameters
        generate_key_method: Key generation method ("simple", "hash", "compound")
        
    Returns:
        Tuple of (cache_key, recommended_ttl)
    """
    # Generate appropriate cache key
    if generate_key_method == "hash":
        cache_key = CacheKeyGenerator.generate_hash(tool_name, **params)
    elif generate_key_method == "compound":
        # Split params into primary and secondary
        primary_keys = ["keywords", "category", "agency_code", "opportunity_status"]
        primary_params = {k: v for k, v in params.items() if k in primary_keys}
        secondary_params = {k: v for k, v in params.items() if k not in primary_keys}
        cache_key = CacheKeyGenerator.generate_compound(
            tool_name, primary_params, secondary_params
        )
    else:  # simple
        cache_key = CacheKeyGenerator.generate_simple(tool_name, **params)
    
    # Get recommended TTL
    ttl = CacheStrategy.get_ttl(tool_name)
    
    logger.debug(f"Generated cache key for {tool_name}: {cache_key} (TTL: {ttl}s)")
    
    return cache_key, ttl