"""Edge case tests for error handling, network failures, and malformed data."""

import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta

import pytest
import aiohttp

from mcp_server.tools.utils.api_client import SimplerGrantsAPIClient
from mcp_server.tools.utils.cache_manager import InMemoryCache
from mcp_server.config.settings import Settings


class TestNetworkFailures:
    """Test handling of various network failure scenarios."""
    
    @pytest.mark.edge_case
    @pytest.mark.asyncio
    async def test_connection_timeout_handling(self):
        """Test handling of connection timeouts."""
        
        async def timeout_side_effect(*args, **kwargs):
            raise asyncio.TimeoutError("Connection timeout")
        
        client = SimplerGrantsAPIClient(api_key="test_key")
        
        with patch.object(client, '_make_request', side_effect=timeout_side_effect):
            with pytest.raises(asyncio.TimeoutError):
                await client.search_opportunities(query="test")
                
    @pytest.mark.edge_case
    @pytest.mark.asyncio
    async def test_connection_error_handling(self):
        """Test handling of connection errors."""
        
        async def connection_error_side_effect(*args, **kwargs):
            raise aiohttp.ClientConnectorError(
                connection_key=None,
                os_error=OSError("Connection refused")
            )
        
        client = SimplerGrantsAPIClient(api_key="test_key")
        
        with patch.object(client, '_make_request', side_effect=connection_error_side_effect):
            with pytest.raises(aiohttp.ClientConnectorError):
                await client.search_opportunities(query="test")
                
    @pytest.mark.edge_case
    @pytest.mark.asyncio
    async def test_ssl_certificate_error(self):
        """Test handling of SSL certificate errors."""
        
        async def ssl_error_side_effect(*args, **kwargs):
            raise aiohttp.ClientSSLError("SSL certificate verification failed")
        
        client = SimplerGrantsAPIClient(api_key="test_key")
        
        with patch.object(client, '_make_request', side_effect=ssl_error_side_effect):
            with pytest.raises(aiohttp.ClientSSLError):
                await client.search_opportunities(query="test")
                
    @pytest.mark.edge_case
    @pytest.mark.asyncio
    async def test_dns_resolution_failure(self):
        """Test handling of DNS resolution failures."""
        
        async def dns_error_side_effect(*args, **kwargs):
            raise aiohttp.ClientConnectorError(
                connection_key=None,
                os_error=OSError("Name or service not known")
            )
        
        client = SimplerGrantsAPIClient(api_key="test_key")
        
        with patch.object(client, '_make_request', side_effect=dns_error_side_effect):
            with pytest.raises(aiohttp.ClientConnectorError):
                await client.search_opportunities(query="test")


class TestAPIErrorResponses:
    """Test handling of various API error responses."""
    
    @pytest.mark.edge_case
    @pytest.mark.asyncio
    async def test_http_401_unauthorized(self):
        """Test handling of 401 Unauthorized responses."""
        
        mock_response = Mock()
        mock_response.status = 401
        mock_response.json.return_value = asyncio.create_future()
        mock_response.json.return_value.set_result({"error": "Invalid API key"})
        
        async def unauthorized_side_effect(*args, **kwargs):
            raise aiohttp.ClientResponseError(
                request_info=None,
                history=(),
                status=401,
                message="Unauthorized"
            )
        
        client = SimplerGrantsAPIClient(api_key="invalid_key")
        
        with patch.object(client, '_make_request', side_effect=unauthorized_side_effect):
            with pytest.raises(aiohttp.ClientResponseError) as exc_info:
                await client.search_opportunities(query="test")
            assert exc_info.value.status == 401
            
    @pytest.mark.edge_case
    @pytest.mark.asyncio
    async def test_http_403_forbidden(self):
        """Test handling of 403 Forbidden responses."""
        
        async def forbidden_side_effect(*args, **kwargs):
            raise aiohttp.ClientResponseError(
                request_info=None,
                history=(),
                status=403,
                message="Forbidden"
            )
        
        client = SimplerGrantsAPIClient(api_key="test_key")
        
        with patch.object(client, '_make_request', side_effect=forbidden_side_effect):
            with pytest.raises(aiohttp.ClientResponseError) as exc_info:
                await client.search_opportunities(query="test")
            assert exc_info.value.status == 403
            
    @pytest.mark.edge_case
    @pytest.mark.asyncio
    async def test_http_429_rate_limit(self):
        """Test handling of 429 Rate Limit Exceeded responses."""
        
        async def rate_limit_side_effect(*args, **kwargs):
            raise aiohttp.ClientResponseError(
                request_info=None,
                history=(),
                status=429,
                message="Rate Limit Exceeded",
                headers={"Retry-After": "60"}
            )
        
        client = SimplerGrantsAPIClient(api_key="test_key")
        
        with patch.object(client, '_make_request', side_effect=rate_limit_side_effect):
            with pytest.raises(aiohttp.ClientResponseError) as exc_info:
                await client.search_opportunities(query="test")
            assert exc_info.value.status == 429
            
    @pytest.mark.edge_case
    @pytest.mark.asyncio
    async def test_http_500_internal_server_error(self):
        """Test handling of 500 Internal Server Error responses."""
        
        async def server_error_side_effect(*args, **kwargs):
            raise aiohttp.ClientResponseError(
                request_info=None,
                history=(),
                status=500,
                message="Internal Server Error"
            )
        
        client = SimplerGrantsAPIClient(api_key="test_key")
        
        with patch.object(client, '_make_request', side_effect=server_error_side_effect):
            with pytest.raises(aiohttp.ClientResponseError) as exc_info:
                await client.search_opportunities(query="test")
            assert exc_info.value.status == 500
            
    @pytest.mark.edge_case
    @pytest.mark.asyncio
    async def test_http_503_service_unavailable(self):
        """Test handling of 503 Service Unavailable responses."""
        
        async def service_unavailable_side_effect(*args, **kwargs):
            raise aiohttp.ClientResponseError(
                request_info=None,
                history=(),
                status=503,
                message="Service Unavailable"
            )
        
        client = SimplerGrantsAPIClient(api_key="test_key")
        
        with patch.object(client, '_make_request', side_effect=service_unavailable_side_effect):
            with pytest.raises(aiohttp.ClientResponseError) as exc_info:
                await client.search_opportunities(query="test")
            assert exc_info.value.status == 503


class TestMalformedDataHandling:
    """Test handling of malformed or unexpected data."""
    
    @pytest.mark.edge_case
    @pytest.mark.asyncio
    async def test_invalid_json_response(self):
        """Test handling of invalid JSON responses."""
        
        async def invalid_json_side_effect(*args, **kwargs):
            mock_response = Mock()
            mock_response.status = 200
            mock_response.json.side_effect = json.JSONDecodeError("Expecting value", "doc", 0)
            mock_response.text.return_value = asyncio.create_future()
            mock_response.text.return_value.set_result("Invalid JSON response")
            return mock_response
        
        client = SimplerGrantsAPIClient(api_key="test_key")
        
        with patch.object(client, '_make_request', side_effect=invalid_json_side_effect):
            with pytest.raises(json.JSONDecodeError):
                await client.search_opportunities(query="test")
                
    @pytest.mark.edge_case
    @pytest.mark.asyncio
    async def test_missing_required_fields(self):
        """Test handling of API responses missing required fields."""
        
        malformed_responses = [
            {},  # Empty response
            {"data": None},  # Missing data
            {"data": []},  # Empty data, missing pagination_info
            {"pagination_info": {"total_records": 10}},  # Missing data field
            {"data": [{"opportunity_id": 123}]},  # Missing pagination_info
        ]
        
        client = SimplerGrantsAPIClient(api_key="test_key")
        
        for response in malformed_responses:
            async def malformed_side_effect(*args, **kwargs):
                mock_response = Mock()
                mock_response.status = 200
                mock_response.json.return_value = asyncio.create_future()
                mock_response.json.return_value.set_result(response)
                return mock_response
            
            with patch.object(client, '_make_request', side_effect=malformed_side_effect):
                result = await client.search_opportunities(query="test")
                # Client should handle gracefully, possibly returning empty results
                assert isinstance(result, dict)
                
    @pytest.mark.edge_case
    @pytest.mark.asyncio
    async def test_malformed_opportunity_data(self):
        """Test handling of opportunities with malformed data."""
        
        malformed_opportunity = {
            "opportunity_id": None,  # Invalid ID
            "opportunity_title": "",  # Empty title
            "opportunity_status": "invalid_status",  # Invalid status
            "agency": None,  # Missing agency
            "summary": {
                "award_ceiling": "not_a_number",  # Invalid number
                "close_date": "invalid_date",  # Invalid date
                "applicant_eligibility_description": None,  # Null description
            }
        }
        
        malformed_response = {
            "data": [malformed_opportunity],
            "pagination_info": {"total_records": 1}
        }
        
        client = SimplerGrantsAPIClient(api_key="test_key")
        
        async def malformed_side_effect(*args, **kwargs):
            mock_response = Mock()
            mock_response.status = 200
            mock_response.json.return_value = asyncio.create_future()
            mock_response.json.return_value.set_result(malformed_response)
            return mock_response
        
        with patch.object(client, '_make_request', side_effect=malformed_side_effect):
            result = await client.search_opportunities(query="test")
            assert "data" in result
            assert len(result["data"]) == 1
            # Verify the malformed data is preserved but doesn't break processing
            
    @pytest.mark.edge_case
    def test_cache_with_malformed_keys(self):
        """Test cache handling of malformed or problematic keys."""
        cache = InMemoryCache(ttl=60, max_size=100)
        
        problematic_keys = [
            None,  # None key
            "",  # Empty string
            " ",  # Whitespace only
            "key with spaces and special chars !@#$%^&*()",
            "very_long_key_" + "x" * 1000,  # Very long key
            "unicode_key_ñáéíóú_🎉",  # Unicode characters
            {"not": "a_string"},  # Non-string key (should be converted)
        ]
        
        for key in problematic_keys:
            try:
                cache.set(key, f"value_for_{key}")
                result = cache.get(key)
                # Should either work or fail gracefully
                assert result is None or isinstance(result, str)
            except Exception as e:
                # Should not raise unexpected exceptions
                assert isinstance(e, (TypeError, ValueError, KeyError))
                
    @pytest.mark.edge_case
    def test_cache_with_malformed_values(self):
        """Test cache handling of malformed or problematic values."""
        cache = InMemoryCache(ttl=60, max_size=100)
        
        problematic_values = [
            None,  # None value
            "",  # Empty string
            [],  # Empty list
            {},  # Empty dict
            float('inf'),  # Infinity
            float('nan'),  # NaN
            {"circular": None},  # Circular reference (simulated)
        ]
        
        # Add circular reference
        circular = {"ref": None}
        circular["ref"] = circular
        problematic_values.append(circular)
        
        for i, value in enumerate(problematic_values):
            try:
                cache.set(f"key_{i}", value)
                result = cache.get(f"key_{i}")
                # Should handle gracefully
                assert result is not None or value is None
            except Exception as e:
                # Should not raise unexpected exceptions
                assert isinstance(e, (TypeError, ValueError, RecursionError))


class TestBoundaryValues:
    """Test handling of boundary values and edge cases."""
    
    @pytest.mark.edge_case
    @pytest.mark.asyncio
    async def test_zero_page_size_request(self):
        """Test API request with zero page size."""
        client = SimplerGrantsAPIClient(api_key="test_key")
        
        # Should handle gracefully or raise appropriate error
        with pytest.raises((ValueError, aiohttp.ClientResponseError)):
            await client.search_opportunities(
                query="test",
                pagination={"page_size": 0, "page_offset": 1}
            )
            
    @pytest.mark.edge_case
    @pytest.mark.asyncio
    async def test_negative_page_offset(self):
        """Test API request with negative page offset."""
        client = SimplerGrantsAPIClient(api_key="test_key")
        
        # Should handle gracefully or raise appropriate error
        with pytest.raises((ValueError, aiohttp.ClientResponseError)):
            await client.search_opportunities(
                query="test",
                pagination={"page_size": 10, "page_offset": -1}
            )
            
    @pytest.mark.edge_case
    @pytest.mark.asyncio
    async def test_extremely_large_page_size(self):
        """Test API request with extremely large page size."""
        client = SimplerGrantsAPIClient(api_key="test_key")
        
        # Should handle gracefully or raise appropriate error
        with pytest.raises((ValueError, aiohttp.ClientResponseError)):
            await client.search_opportunities(
                query="test",
                pagination={"page_size": 999999, "page_offset": 1}
            )
            
    @pytest.mark.edge_case
    def test_cache_zero_ttl(self):
        """Test cache behavior with zero TTL."""
        cache = InMemoryCache(ttl=0, max_size=100)
        
        cache.set("key", "value")
        # With zero TTL, values should expire immediately
        result = cache.get("key")
        assert result is None
        
    @pytest.mark.edge_case
    def test_cache_zero_max_size(self):
        """Test cache behavior with zero max size."""
        cache = InMemoryCache(ttl=60, max_size=0)
        
        cache.set("key", "value")
        # With zero max size, nothing should be cached
        result = cache.get("key")
        assert result is None
        assert len(cache) == 0
        
    @pytest.mark.edge_case
    def test_empty_search_query(self):
        """Test handling of empty search queries."""
        from mcp_server.tools.discovery.opportunity_discovery_tool import format_search_results
        
        empty_results = {
            "data": [],
            "pagination_info": {"total_records": 0}
        }
        
        # Should handle empty results gracefully
        formatted = format_search_results(empty_results, "", {}, 1, 10)
        assert "No grants found" in formatted or "0 grants" in formatted
        
    @pytest.mark.edge_case
    def test_very_long_search_query(self):
        """Test handling of extremely long search queries."""
        very_long_query = "artificial intelligence " * 1000  # ~21KB query
        
        # Test cache key generation with long query
        key = InMemoryCache.generate_cache_key("search", query=very_long_query)
        assert isinstance(key, str)
        assert len(key) < 1000  # Should be hashed to manageable size


class TestRateLimitingEdgeCases:
    """Test rate limiting edge cases and scenarios."""
    
    @pytest.mark.edge_case
    @pytest.mark.asyncio
    async def test_burst_requests_handling(self):
        """Test handling of burst requests that exceed rate limits."""
        
        call_count = 0
        
        async def rate_limited_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count <= 5:
                # First 5 requests succeed
                return Mock(status=200, json=AsyncMock(return_value={"data": [], "pagination_info": {"total_records": 0}}))
            else:
                # Subsequent requests are rate limited
                raise aiohttp.ClientResponseError(
                    request_info=None,
                    history=(),
                    status=429,
                    message="Rate Limit Exceeded"
                )
        
        client = SimplerGrantsAPIClient(api_key="test_key")
        
        with patch.object(client, '_make_request', side_effect=rate_limited_side_effect):
            # Make burst of requests
            results = []
            errors = []
            
            for i in range(10):
                try:
                    result = await client.search_opportunities(query=f"test {i}")
                    results.append(result)
                except aiohttp.ClientResponseError as e:
                    errors.append(e)
            
            # Should have some successful and some rate-limited requests
            assert len(results) == 5  # First 5 succeeded
            assert len(errors) == 5   # Last 5 were rate limited
            assert all(e.status == 429 for e in errors)
            
    @pytest.mark.edge_case
    def test_concurrent_rate_limit_tracking(self):
        """Test rate limit tracking with concurrent requests."""
        
        # This would be implemented if we had actual rate limiting logic
        # For now, we test that concurrent operations don't break
        
        cache = InMemoryCache(ttl=60, max_size=100)
        
        import threading
        import time
        
        def worker(worker_id):
            """Simulate concurrent API usage tracking."""
            for i in range(100):
                # Simulate rate limit tracking
                key = f"rate_limit_{time.time()}"
                cache.set(key, {"worker": worker_id, "request": i, "timestamp": time.time()})
                
        threads = []
        for i in range(10):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
            
        for thread in threads:
            thread.join()
            
        # Should handle concurrent rate limit tracking without issues
        stats = cache.get_stats()
        assert stats["size"] > 0
        
    @pytest.mark.edge_case
    @pytest.mark.asyncio 
    async def test_retry_logic_edge_cases(self):
        """Test retry logic with various edge cases."""
        
        attempt_count = 0
        
        async def intermittent_failure_side_effect(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            
            if attempt_count < 3:
                # First 2 attempts fail
                raise aiohttp.ClientConnectorError(
                    connection_key=None,
                    os_error=OSError("Connection refused")
                )
            else:
                # Third attempt succeeds
                mock_response = Mock()
                mock_response.status = 200
                mock_response.json.return_value = asyncio.create_future()
                mock_response.json.return_value.set_result({"data": [], "pagination_info": {"total_records": 0}})
                return mock_response
        
        # This would test actual retry logic if implemented
        # For now, we just test that the function signature works
        client = SimplerGrantsAPIClient(api_key="test_key")
        
        with patch.object(client, '_make_request', side_effect=intermittent_failure_side_effect):
            # If retry logic existed, this would eventually succeed
            # For now, it will fail on first attempt
            with pytest.raises(aiohttp.ClientConnectorError):
                await client.search_opportunities(query="test")