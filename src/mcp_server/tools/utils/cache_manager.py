"""In-memory cache manager with TTL support."""

import hashlib
import json
import logging
import threading
import time
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class InMemoryCache:
    """
    Thread-safe in-memory cache with TTL (Time-To-Live) support.
    
    Simple ephemeral cache for API responses to reduce redundant calls
    and improve performance.
    """
    
    def __init__(self, ttl: int = 300, max_size: int = 1000):
        """
        Initialize the cache.
        
        Args:
            ttl: Time-to-live in seconds (default: 300 = 5 minutes)
            max_size: Maximum number of items to cache (default: 1000)
        """
        self.ttl = ttl
        self.max_size = max_size
        self._cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0,
        }
        
        logger.info(f"Initialized cache with TTL={ttl}s, max_size={max_size}")
    
    def _is_expired(self, timestamp: float) -> bool:
        """Check if a cache entry has expired."""
        return time.time() - timestamp > self.ttl
    
    def _evict_oldest(self):
        """Evict the oldest entry from cache (LRU)."""
        if self._cache:
            evicted_key, _ = self._cache.popitem(last=False)
            self._stats["evictions"] += 1
            logger.debug(f"Evicted oldest cache entry: {evicted_key}")
    
    def _cleanup_expired(self):
        """Remove all expired entries from cache."""
        expired_keys = []
        current_time = time.time()
        
        for key, (_, timestamp) in self._cache.items():
            if current_time - timestamp > self.ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
            self._stats["expirations"] += 1
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired entries")
    
    @staticmethod
    def generate_cache_key(*args, **kwargs) -> str:
        """
        Generate a cache key from arguments.
        
        Creates a deterministic hash from the provided arguments.
        """
        # Combine all arguments into a single string representation
        key_data = {
            "args": args,
            "kwargs": kwargs
        }
        
        # Create a stable JSON representation
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        
        # Generate hash for the key
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value if found and not expired, None otherwise
        """
        with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                
                if self._is_expired(timestamp):
                    # Entry has expired
                    del self._cache[key]
                    self._stats["expirations"] += 1
                    self._stats["misses"] += 1
                    logger.debug(f"Cache miss (expired): {key}")
                    return None
                
                # Move to end (most recently used)
                self._cache.move_to_end(key)
                self._stats["hits"] += 1
                logger.debug(f"Cache hit: {key}")
                return value
            
            self._stats["misses"] += 1
            logger.debug(f"Cache miss: {key}")
            return None
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        with self._lock:
            # Clean up expired entries periodically
            if len(self._cache) > self.max_size * 1.1:  # 10% buffer
                self._cleanup_expired()
            
            # Evict oldest if at capacity
            if len(self._cache) >= self.max_size:
                self._evict_oldest()
            
            # Store value with current timestamp
            self._cache[key] = (value, time.time())
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            
            logger.debug(f"Cached value for key: {key}")
    
    def invalidate(self, key: str) -> bool:
        """
        Invalidate (remove) a specific cache entry.
        
        Args:
            key: Cache key to invalidate
            
        Returns:
            True if entry was found and removed, False otherwise
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Invalidated cache entry: {key}")
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cleared cache ({count} entries)")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary containing cache statistics
        """
        with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = (
                self._stats["hits"] / total_requests if total_requests > 0 else 0
            )
            
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "ttl_seconds": self.ttl,
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "evictions": self._stats["evictions"],
                "expirations": self._stats["expirations"],
                "hit_rate": round(hit_rate, 3),
                "total_requests": total_requests,
            }
    
    def get_size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)
    
    def __contains__(self, key: str) -> bool:
        """Check if key exists in cache (even if expired)."""
        with self._lock:
            return key in self._cache
    
    def __len__(self) -> int:
        """Get cache size."""
        return self.get_size()
    
    def __repr__(self) -> str:
        """String representation of cache."""
        stats = self.get_stats()
        return (
            f"InMemoryCache(size={stats['size']}/{stats['max_size']}, "
            f"ttl={stats['ttl_seconds']}s, hit_rate={stats['hit_rate']:.1%})"
        )