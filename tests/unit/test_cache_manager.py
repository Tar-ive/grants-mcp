"""Unit tests for the in-memory cache manager."""

import time
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from mcp_server.tools.utils.cache_manager import InMemoryCache


class TestInMemoryCache:
    """Test the InMemoryCache implementation."""
    
    def test_cache_stores_and_retrieves_data(self):
        """Test basic cache storage and retrieval."""
        cache = InMemoryCache(ttl=60, max_size=10)
        
        # Store data
        cache.set("key1", {"data": "test value"})
        
        # Retrieve data
        result = cache.get("key1")
        assert result == {"data": "test value"}
    
    def test_cache_returns_none_for_missing_key(self):
        """Test cache returns None for non-existent keys."""
        cache = InMemoryCache(ttl=60, max_size=10)
        
        result = cache.get("nonexistent")
        assert result is None
    
    def test_cache_expires_after_ttl(self):
        """Test cache expiration after TTL."""
        cache = InMemoryCache(ttl=1, max_size=10)  # 1 second TTL
        
        # Store data
        cache.set("key1", {"data": "test"})
        assert cache.get("key1") == {"data": "test"}
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should return None after expiration
        assert cache.get("key1") is None
    
    def test_cache_evicts_oldest_when_full(self):
        """Test LRU eviction when cache is full."""
        cache = InMemoryCache(ttl=60, max_size=3)
        
        # Fill cache
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # Access key1 to make it recently used
        cache.get("key1")
        
        # Add new item (should evict key2 as it's least recently used)
        cache.set("key4", "value4")
        
        # Check eviction
        assert cache.get("key1") == "value1"  # Still exists (recently used)
        assert cache.get("key2") is None  # Evicted
        assert cache.get("key3") == "value3"  # Still exists
        assert cache.get("key4") == "value4"  # Newly added
    
    def test_cache_handles_concurrent_access(self):
        """Test thread-safe cache operations."""
        cache = InMemoryCache(ttl=60, max_size=100)
        results = []
        
        def write_to_cache(key, value):
            cache.set(key, value)
            results.append(("write", key, value))
        
        def read_from_cache(key):
            value = cache.get(key)
            results.append(("read", key, value))
        
        # Perform concurrent operations
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            
            # Submit write operations
            for i in range(50):
                futures.append(
                    executor.submit(write_to_cache, f"key{i}", f"value{i}")
                )
            
            # Submit read operations
            for i in range(50):
                futures.append(
                    executor.submit(read_from_cache, f"key{i}")
                )
            
            # Wait for all operations to complete
            for future in futures:
                future.result()
        
        # Verify cache integrity
        for i in range(50):
            assert cache.get(f"key{i}") == f"value{i}"
    
    def test_cache_generate_key(self):
        """Test cache key generation."""
        # Same arguments should produce same key
        key1 = InMemoryCache.generate_cache_key("search", query="test", page=1)
        key2 = InMemoryCache.generate_cache_key("search", query="test", page=1)
        assert key1 == key2
        
        # Different arguments should produce different keys
        key3 = InMemoryCache.generate_cache_key("search", query="test", page=2)
        assert key1 != key3
        
        # Order of kwargs shouldn't matter
        key4 = InMemoryCache.generate_cache_key("search", page=1, query="test")
        assert key1 == key4
    
    def test_cache_invalidate(self):
        """Test cache invalidation."""
        cache = InMemoryCache(ttl=60, max_size=10)
        
        # Store data
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        # Invalidate specific key
        result = cache.invalidate("key1")
        assert result is True
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        
        # Try to invalidate non-existent key
        result = cache.invalidate("nonexistent")
        assert result is False
    
    def test_cache_clear(self):
        """Test clearing all cache entries."""
        cache = InMemoryCache(ttl=60, max_size=10)
        
        # Store multiple items
        for i in range(5):
            cache.set(f"key{i}", f"value{i}")
        
        assert len(cache) == 5
        
        # Clear cache
        cache.clear()
        
        assert len(cache) == 0
        for i in range(5):
            assert cache.get(f"key{i}") is None
    
    def test_cache_statistics(self):
        """Test cache statistics tracking."""
        cache = InMemoryCache(ttl=60, max_size=10)
        
        # Initial stats
        stats = cache.get_stats()
        assert stats["size"] == 0
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        
        # Generate some activity
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        # Cache hits
        cache.get("key1")
        cache.get("key2")
        
        # Cache misses
        cache.get("key3")
        cache.get("key4")
        
        # Check updated stats
        stats = cache.get_stats()
        assert stats["size"] == 2
        assert stats["hits"] == 2
        assert stats["misses"] == 2
        assert stats["hit_rate"] == 0.5
        assert stats["total_requests"] == 4
    
    def test_cache_max_size_enforcement(self):
        """Test that cache respects maximum size."""
        cache = InMemoryCache(ttl=60, max_size=5)
        
        # Add more items than max size
        for i in range(10):
            cache.set(f"key{i}", f"value{i}")
        
        # Cache should not exceed max size
        assert len(cache) <= 5
        
        # Most recent items should be in cache
        assert cache.get("key9") == "value9"
        assert cache.get("key8") == "value8"
        
        # Oldest items should be evicted
        assert cache.get("key0") is None
        assert cache.get("key1") is None
    
    def test_cache_cleanup_expired(self):
        """Test automatic cleanup of expired entries."""
        cache = InMemoryCache(ttl=1, max_size=100)
        
        # Add items at different times
        cache.set("key1", "value1")
        time.sleep(0.5)
        cache.set("key2", "value2")
        time.sleep(0.6)  # key1 should be expired now
        
        # Trigger cleanup by adding many items
        for i in range(15):
            cache.set(f"new_key{i}", f"new_value{i}")
        
        # key1 should be cleaned up, key2 should still exist
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
    
    def test_cache_contains(self):
        """Test cache containment check."""
        cache = InMemoryCache(ttl=60, max_size=10)
        
        cache.set("key1", "value1")
        
        assert "key1" in cache
        assert "key2" not in cache
    
    def test_cache_repr(self):
        """Test cache string representation."""
        cache = InMemoryCache(ttl=60, max_size=10)
        
        cache.set("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss
        
        repr_str = repr(cache)
        assert "InMemoryCache" in repr_str
        assert "size=1/10" in repr_str
        assert "ttl=60s" in repr_str
        assert "hit_rate" in repr_str


class TestCachePerformance:
    """Performance tests for the cache."""
    
    def test_cache_improves_response_time(self, benchmark):
        """Test that cache significantly improves performance."""
        cache = InMemoryCache(ttl=60, max_size=100)
        
        # Simulate expensive operation
        def expensive_operation():
            time.sleep(0.01)  # 10ms operation
            return {"result": "expensive data"}
        
        def cached_operation(key):
            result = cache.get(key)
            if result is None:
                result = expensive_operation()
                cache.set(key, result)
            return result
        
        # First call (cache miss)
        start = time.time()
        result1 = cached_operation("test_key")
        uncached_time = time.time() - start
        
        # Second call (cache hit)
        start = time.time()
        result2 = cached_operation("test_key")
        cached_time = time.time() - start
        
        # Cache should be at least 10x faster
        assert cached_time < uncached_time * 0.1
        assert result1 == result2
    
    def test_cache_key_generation_performance(self):
        """Test cache key generation is fast."""
        start = time.time()
        
        # Generate many cache keys
        for i in range(1000):
            InMemoryCache.generate_cache_key(
                "search",
                query=f"test{i}",
                filters={"status": "active"},
                page=i
            )
        
        duration = time.time() - start
        
        # Should generate 1000 keys in less than 100ms
        assert duration < 0.1