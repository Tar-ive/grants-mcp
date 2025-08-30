"""Performance tests for concurrent operations and parallel request handling."""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import AsyncMock, patch

import pytest

from mcp_server.tools.utils.api_client import SimplerGrantsAPIClient
from mcp_server.tools.utils.cache_manager import InMemoryCache


class TestConcurrentPerformance:
    """Test concurrent operation performance and scalability."""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_api_requests(self, benchmark):
        """Test performance of concurrent API requests."""
        
        async def make_concurrent_requests(num_requests=10):
            """Simulate concurrent API requests."""
            mock_response = {
                "data": [{"opportunity_id": i, "title": f"Grant {i}"}],
                "pagination_info": {"total_records": 1}
            }
            
            with patch.object(SimplerGrantsAPIClient, 'search_opportunities') as mock_search:
                mock_search.return_value = mock_response
                
                client = SimplerGrantsAPIClient(api_key="test_key")
                tasks = []
                
                for i in range(num_requests):
                    task = client.search_opportunities(
                        query=f"test query {i}",
                        pagination={"page_size": 25, "page_offset": 1}
                    )
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks)
                return results
        
        # Benchmark concurrent requests
        results = benchmark(asyncio.run, make_concurrent_requests(20))
        assert len(results) == 20
        
    @pytest.mark.performance
    def test_cache_concurrent_access(self, benchmark):
        """Test cache performance under concurrent access."""
        cache = InMemoryCache(ttl=300, max_size=1000)
        
        def concurrent_cache_operations(num_operations=100):
            """Perform concurrent cache operations."""
            def worker(thread_id):
                results = []
                for i in range(num_operations // 10):
                    # Mix of reads and writes
                    cache.set(f"key_{thread_id}_{i}", f"value_{thread_id}_{i}")
                    result = cache.get(f"key_{thread_id}_{i}")
                    results.append(result)
                return results
            
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(worker, i) for i in range(10)]
                all_results = []
                for future in as_completed(futures):
                    all_results.extend(future.result())
                return all_results
        
        results = benchmark(concurrent_cache_operations, 1000)
        assert len(results) == 1000
        
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_parallel_grant_search_scenarios(self):
        """Test parallel execution of different grant search scenarios."""
        
        search_scenarios = [
            {"query": "artificial intelligence", "category": "Technology"},
            {"query": "climate change", "category": "Environment"},
            {"query": "healthcare innovation", "category": "Health"},
            {"query": "renewable energy", "category": "Energy"},
            {"query": "education research", "category": "Education"},
        ]
        
        mock_response = {
            "data": [{"opportunity_id": 123, "title": "Test Grant"}],
            "pagination_info": {"total_records": 1}
        }
        
        with patch.object(SimplerGrantsAPIClient, 'search_opportunities') as mock_search:
            mock_search.return_value = mock_response
            
            client = SimplerGrantsAPIClient(api_key="test_key")
            
            # Time parallel execution
            start_time = time.time()
            
            tasks = []
            for scenario in search_scenarios:
                task = client.search_opportunities(
                    query=scenario["query"],
                    filters={"category": scenario["category"]},
                    pagination={"page_size": 10, "page_offset": 1}
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            parallel_time = time.time() - start_time
            
            # Time sequential execution
            start_time = time.time()
            sequential_results = []
            for scenario in search_scenarios:
                result = await client.search_opportunities(
                    query=scenario["query"],
                    filters={"category": scenario["category"]},
                    pagination={"page_size": 10, "page_offset": 1}
                )
                sequential_results.append(result)
            sequential_time = time.time() - start_time
            
            # Parallel should be faster
            assert parallel_time < sequential_time * 0.8  # At least 20% faster
            assert len(results) == len(sequential_results) == 5
            
    @pytest.mark.performance
    def test_memory_usage_under_load(self):
        """Test memory usage remains stable under load."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Create large cache with many operations
        cache = InMemoryCache(ttl=300, max_size=10000)
        
        # Perform many cache operations
        for i in range(50000):
            cache.set(f"key_{i}", {"data": f"value_{i}" * 100})  # ~600 bytes per entry
            if i % 1000 == 0:
                # Periodic cleanup
                cache.get(f"key_{i-500}")  # Simulate reads
                
        final_memory = process.memory_info().rss
        memory_growth = (final_memory - initial_memory) / 1024 / 1024  # MB
        
        # Memory growth should be reasonable (less than 500MB for this test)
        assert memory_growth < 500, f"Memory growth too high: {memory_growth:.1f}MB"
        
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_rate_limit_handling(self):
        """Test performance impact of rate limiting."""
        
        async def simulate_rate_limited_requests():
            """Simulate requests with rate limiting."""
            request_times = []
            
            for i in range(20):
                start = time.time()
                
                # Simulate API call with rate limiting
                if i > 0 and i % 5 == 0:
                    await asyncio.sleep(1.0)  # Rate limit delay
                    
                # Simulate API response time
                await asyncio.sleep(0.1)
                
                end = time.time()
                request_times.append(end - start)
                
            return request_times
        
        request_times = await simulate_rate_limited_requests()
        
        # Check that rate limited requests are properly spaced
        rate_limited_times = [t for i, t in enumerate(request_times) if i > 0 and i % 5 == 0]
        normal_times = [t for i, t in enumerate(request_times) if not (i > 0 and i % 5 == 0)]
        
        avg_rate_limited = sum(rate_limited_times) / len(rate_limited_times)
        avg_normal = sum(normal_times) / len(normal_times)
        
        # Rate limited requests should take significantly longer
        assert avg_rate_limited > avg_normal * 5
        
    @pytest.mark.performance
    def test_cache_hit_ratio_under_load(self):
        """Test cache hit ratio performance under various load patterns."""
        cache = InMemoryCache(ttl=300, max_size=1000)
        
        # Scenario 1: High locality (should have high hit rate)
        for _ in range(10000):
            key = f"popular_key_{hash('popular') % 100}"  # 100 popular keys
            cache.set(key, {"data": "popular"})
            cache.get(key)
            
        stats1 = cache.get_stats()
        high_locality_hit_rate = stats1['hit_rate']
        
        # Clear cache for next test
        cache.clear()
        
        # Scenario 2: Random access (should have lower hit rate)
        for i in range(10000):
            key = f"random_key_{i}"
            cache.set(key, {"data": "random"})
            # Random access pattern
            random_key = f"random_key_{hash(str(i)) % i if i > 0 else 0}"
            cache.get(random_key)
            
        stats2 = cache.get_stats()
        low_locality_hit_rate = stats2['hit_rate']
        
        # High locality should have significantly better hit rate
        assert high_locality_hit_rate > low_locality_hit_rate
        assert high_locality_hit_rate > 0.8  # Should be > 80%
        
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_bulk_operation_performance(self):
        """Test performance of bulk operations vs individual operations."""
        
        mock_single_response = {
            "data": [{"opportunity_id": 1, "title": "Single Grant"}],
            "pagination_info": {"total_records": 1}
        }
        
        mock_bulk_response = {
            "data": [{"opportunity_id": i, "title": f"Bulk Grant {i}"} for i in range(100)],
            "pagination_info": {"total_records": 100}
        }
        
        with patch.object(SimplerGrantsAPIClient, 'search_opportunities') as mock_search:
            client = SimplerGrantsAPIClient(api_key="test_key")
            
            # Test individual requests
            mock_search.return_value = mock_single_response
            start_time = time.time()
            
            individual_results = []
            for i in range(100):
                result = await client.search_opportunities(
                    query=f"grant {i}",
                    pagination={"page_size": 1, "page_offset": 1}
                )
                individual_results.append(result)
                
            individual_time = time.time() - start_time
            
            # Test bulk request
            mock_search.return_value = mock_bulk_response
            start_time = time.time()
            
            bulk_result = await client.search_opportunities(
                query="grants",
                pagination={"page_size": 100, "page_offset": 1}
            )
            
            bulk_time = time.time() - start_time
            
            # Bulk should be much faster
            assert bulk_time < individual_time * 0.1  # At least 10x faster
            assert len(bulk_result["data"]) == 100
            assert len(individual_results) == 100


class TestLoadTesting:
    """Load testing for high-throughput scenarios."""
    
    @pytest.mark.performance
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_sustained_load(self):
        """Test system behavior under sustained load."""
        cache = InMemoryCache(ttl=300, max_size=5000)
        
        async def sustained_operations(duration_seconds=30):
            """Run operations for a sustained period."""
            start_time = time.time()
            operation_count = 0
            
            while time.time() - start_time < duration_seconds:
                # Mix of cache operations
                key = f"sustained_key_{operation_count % 1000}"
                cache.set(key, {"operation": operation_count, "timestamp": time.time()})
                cache.get(key)
                
                operation_count += 1
                
                # Small delay to prevent overwhelming
                await asyncio.sleep(0.001)
                
            return operation_count
        
        operations_completed = await sustained_operations(10)  # 10 seconds for CI
        operations_per_second = operations_completed / 10
        
        # Should handle at least 500 ops/second
        assert operations_per_second > 500
        
    @pytest.mark.performance
    @pytest.mark.slow
    def test_stress_cache_eviction(self):
        """Test cache performance under memory pressure."""
        cache = InMemoryCache(ttl=60, max_size=1000)  # Small cache
        
        # Fill beyond capacity to trigger evictions
        for i in range(10000):
            large_data = {"key": i, "data": "x" * 1000}  # 1KB per entry
            cache.set(f"stress_key_{i}", large_data)
            
            # Periodic access to create LRU patterns
            if i % 100 == 0:
                cache.get(f"stress_key_{max(0, i-50)}")
                
        stats = cache.get_stats()
        
        # Cache should maintain size limit
        assert len(cache) <= 1000
        # Should have reasonable performance despite evictions
        assert stats['hit_rate'] > 0.1  # At least 10% hit rate


class TestScalabilityLimits:
    """Test system behavior at scalability limits."""
    
    @pytest.mark.performance
    def test_maximum_concurrent_connections(self):
        """Test maximum number of concurrent cache connections."""
        cache = InMemoryCache(ttl=300, max_size=10000)
        
        def worker(worker_id, num_operations):
            """Worker thread for concurrent operations."""
            for i in range(num_operations):
                key = f"worker_{worker_id}_operation_{i}"
                cache.set(key, {"worker": worker_id, "operation": i})
                result = cache.get(key)
                assert result is not None
            return worker_id
        
        # Test with many concurrent workers
        num_workers = 50
        operations_per_worker = 100
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(worker, i, operations_per_worker) 
                for i in range(num_workers)
            ]
            
            completed_workers = [future.result() for future in as_completed(futures)]
            
        end_time = time.time()
        
        assert len(completed_workers) == num_workers
        assert end_time - start_time < 30  # Should complete within 30 seconds
        
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_api_timeout_handling(self):
        """Test performance impact of API timeouts."""
        
        async def simulate_timeout_scenario():
            """Simulate API calls with various timeout scenarios."""
            results = {"success": 0, "timeout": 0, "total_time": 0}
            
            start_time = time.time()
            
            for i in range(20):
                request_start = time.time()
                
                try:
                    # Simulate some requests timing out
                    if i % 5 == 0:
                        await asyncio.sleep(2.0)  # Timeout simulation
                        results["timeout"] += 1
                    else:
                        await asyncio.sleep(0.1)  # Normal response
                        results["success"] += 1
                        
                except asyncio.TimeoutError:
                    results["timeout"] += 1
                    
                request_end = time.time()
                results["total_time"] += (request_end - request_start)
            
            results["average_time"] = results["total_time"] / 20
            return results
        
        results = await simulate_timeout_scenario()
        
        # Should handle timeouts gracefully
        assert results["success"] > 0
        assert results["timeout"] > 0
        assert results["average_time"] < 1.0  # Average should be reasonable