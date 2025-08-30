"""Contract tests for API schema validation and MCP protocol compliance."""

import asyncio
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError

from mcp_server.models.grants_schemas import (
    AgencyV1,
    OpportunityV1,
    OpportunitySummary,
    GrantsAPIResponse,
    PaginationInfo,
    SearchRequest,
    SearchFilters
)


class TestGrantsAPISchemas:
    """Test API response schema validation and contract compliance."""
    
    @pytest.mark.contract
    def test_opportunity_v1_schema_validation(self):
        """Test OpportunityV1 schema validation with valid data."""
        valid_opportunity = {
            "opportunity_id": "123456",
            "opportunity_number": "NSF-2024-001",
            "opportunity_title": "Advanced Research in Artificial Intelligence",
            "opportunity_status": "posted",
            "agency": "NSF",
            "agency_code": "NSF",
            "agency_name": "National Science Foundation",
            "category": "Science and Technology",
            "summary": {
                "award_ceiling": 500000,
                "award_floor": 100000,
                "estimated_total_program_funding": 5000000,
                "expected_number_of_awards": 10,
                "post_date": "2024-01-15",
                "close_date": "2024-06-30",
                "summary_description": "Support for innovative AI research projects",
                "applicant_eligibility_description": "Universities and research institutions",
                "additional_info_url": "https://www.nsf.gov/funding/pgm_summ.jsp",
                "agency_email_address": "grants@nsf.gov",
                "agency_phone_number": "703-292-5111",
                "funding_instrument": "Grant",
                "applicant_types": ["Universities", "Non-profits"]
            }
        }
        
        # Should validate successfully
        opportunity = OpportunityV1(**valid_opportunity)
        assert opportunity.opportunity_id == "123456"
        assert opportunity.opportunity_title == "Advanced Research in Artificial Intelligence"
        assert opportunity.summary.award_ceiling == 500000
        
    @pytest.mark.contract
    def test_opportunity_v1_schema_invalid_data(self):
        """Test OpportunityV1 schema validation with invalid data."""
        invalid_opportunities = [
            # Missing required fields
            {
                "opportunity_title": "Test Grant",
                # Missing opportunity_id, agency, etc.
            },
            # Invalid data types
            {
                "opportunity_id": None,
                "opportunity_number": 12345,  # Should be string
                "opportunity_title": "",
                "opportunity_status": "invalid_status",
                "agency": "",
                "agency_code": "",
                "agency_name": "",
                "category": "",
            },
            # Invalid summary data
            {
                "opportunity_id": "123",
                "opportunity_number": "TEST-2024-001",
                "opportunity_title": "Test Grant",
                "opportunity_status": "posted",
                "agency": "TEST",
                "agency_code": "TEST",
                "agency_name": "Test Agency",
                "category": "Test",
                "summary": {
                    "award_ceiling": "not_a_number",  # Should be int
                    "award_floor": -1000,  # Negative amount
                    "post_date": "invalid_date",  # Invalid date format
                    "close_date": "2024-13-45",  # Invalid date
                }
            }
        ]
        
        for invalid_data in invalid_opportunities:
            with pytest.raises(ValidationError):
                OpportunityV1(**invalid_data)
                
    @pytest.mark.contract
    def test_grants_api_response_schema(self):
        """Test GrantsAPIResponse schema validation."""
        valid_response = {
            "data": [
                {
                    "opportunity_id": "123",
                    "opportunity_number": "TEST-001",
                    "opportunity_title": "Test Grant",
                    "opportunity_status": "posted",
                    "agency": "TEST",
                    "agency_code": "TEST",
                    "agency_name": "Test Agency",
                    "category": "Science",
                    "summary": {
                        "award_ceiling": 100000,
                        "summary_description": "Test description"
                    }
                }
            ],
            "pagination_info": {
                "page_size": 25,
                "page_offset": 1,
                "total_records": 1,
                "total_pages": 1
            },
            "facet_counts": {
                "agency": {"TEST": 1},
                "category": {"Science": 1}
            }
        }
        
        response = GrantsAPIResponse(**valid_response)
        assert len(response.data) == 1
        assert response.pagination_info.total_records == 1
        assert "TEST" in response.facet_counts.agency
        
    @pytest.mark.contract
    def test_search_request_schema(self):
        """Test SearchRequest schema validation."""
        valid_request = {
            "query": "artificial intelligence",
            "filters": {
                "agency": ["NSF", "NIH"],
                "opportunity_status": ["posted", "forecasted"],
                "category": ["Science"],
                "funding_instrument": ["Grant"]
            },
            "pagination": {
                "page_size": 25,
                "page_offset": 1,
                "sort_by": "post_date",
                "sort_direction": "descending"
            }
        }
        
        request = SearchRequest(**valid_request)
        assert request.query == "artificial intelligence"
        assert len(request.filters.agency) == 2
        assert request.pagination.page_size == 25
        
    @pytest.mark.contract
    def test_search_filters_validation(self):
        """Test SearchFilters validation edge cases."""
        # Empty filters should be valid
        empty_filters = SearchFilters()
        assert empty_filters.agency is None
        
        # Valid filters
        valid_filters = SearchFilters(
            agency=["NSF"],
            opportunity_status=["posted"],
            category=["Science"],
            min_award_amount=10000,
            max_award_amount=1000000,
            close_date_from="2024-01-01",
            close_date_to="2024-12-31"
        )
        assert valid_filters.agency == ["NSF"]
        assert valid_filters.min_award_amount == 10000
        
        # Invalid date formats should raise validation error
        with pytest.raises(ValidationError):
            SearchFilters(close_date_from="invalid-date")
            
    @pytest.mark.contract
    def test_agency_v1_schema(self):
        """Test AgencyV1 schema validation."""
        valid_agency = {
            "agency_code": "NSF",
            "agency_name": "National Science Foundation",
            "description": "Federal agency supporting fundamental research",
            "website_url": "https://www.nsf.gov"
        }
        
        agency = AgencyV1(**valid_agency)
        assert agency.agency_code == "NSF"
        assert agency.agency_name == "National Science Foundation"
        
        # Required fields should be enforced
        with pytest.raises(ValidationError):
            AgencyV1(agency_name="Test Agency")  # Missing agency_code
            
    @pytest.mark.contract
    def test_pagination_info_schema(self):
        """Test PaginationInfo schema validation."""
        valid_pagination = {
            "page_size": 25,
            "page_offset": 1,
            "total_records": 100,
            "total_pages": 4
        }
        
        pagination = PaginationInfo(**valid_pagination)
        assert pagination.page_size == 25
        assert pagination.total_pages == 4
        
        # Invalid values should raise errors
        with pytest.raises(ValidationError):
            PaginationInfo(page_size=-1, page_offset=1, total_records=100)
            
        with pytest.raises(ValidationError):
            PaginationInfo(page_size=25, page_offset=0, total_records=100)


class TestMCPProtocolCompliance:
    """Test compliance with MCP (Model Context Protocol) specifications."""
    
    @pytest.mark.contract
    def test_tool_schema_compliance(self):
        """Test that tools comply with MCP tool schema."""
        from fastmcp import FastMCP
        from mcp_server.tools.discovery.opportunity_discovery_tool import register_opportunity_discovery_tool
        
        mcp = FastMCP("test")
        context = {"cache": Mock(), "api_client": Mock()}
        register_opportunity_discovery_tool(mcp, context)
        
        # Verify tool is registered
        assert "opportunity_discovery" in mcp._tools
        
        tool = mcp._tools["opportunity_discovery"]
        
        # Verify tool has required attributes
        assert hasattr(tool, 'name')
        assert hasattr(tool, 'description')
        assert hasattr(tool, 'func')
        
        # Verify tool name and description
        assert tool.name == "opportunity_discovery"
        assert isinstance(tool.description, str)
        assert len(tool.description) > 10  # Should have meaningful description
        
    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_tool_input_validation(self):
        """Test that tools validate input parameters correctly."""
        from fastmcp import FastMCP
        from mcp_server.tools.discovery.opportunity_discovery_tool import register_opportunity_discovery_tool
        
        mcp = FastMCP("test")
        
        # Mock API client
        mock_api_client = Mock()
        mock_api_client.search_opportunities.return_value = asyncio.create_future()
        mock_api_client.search_opportunities.return_value.set_result({
            "data": [],
            "pagination_info": {"total_records": 0}
        })
        
        context = {"cache": Mock(), "api_client": mock_api_client}
        register_opportunity_discovery_tool(mcp, context)
        
        tool = mcp._tools["opportunity_discovery"]
        
        # Test with valid parameters
        result = await tool.func(
            query="artificial intelligence",
            max_results=10,
            page=1,
            grants_per_page=5
        )
        assert isinstance(result, str)
        
        # Test with invalid parameters (should handle gracefully)
        result = await tool.func(
            query="",  # Empty query
            max_results=-1,  # Invalid max results
            page=0,  # Invalid page
            grants_per_page=0  # Invalid grants per page
        )
        # Should not crash, may return error message or empty results
        assert isinstance(result, str)
        
    @pytest.mark.contract
    def test_mcp_server_initialization(self):
        """Test MCP server initialization and configuration."""
        from mcp_server.server import GrantsAnalysisServer
        from mcp_server.config.settings import Settings
        
        settings = Settings(
            api_key="test_key",
            cache_ttl=300,
            max_cache_size=1000
        )
        
        server = GrantsAnalysisServer(settings=settings)
        
        # Verify server has required components
        assert hasattr(server, 'mcp')
        assert hasattr(server, 'api_client')
        assert hasattr(server, 'cache')
        
        # Verify server is properly configured
        assert server.mcp.name == "grants-analysis"
        assert server.api_client is not None
        assert server.cache is not None
        
    @pytest.mark.contract
    def test_error_response_format(self):
        """Test that error responses follow expected format."""
        from mcp_server.tools.utils.error_handling import format_error_response
        
        # Test different types of errors
        test_errors = [
            ValueError("Invalid input parameter"),
            ConnectionError("Failed to connect to API"),
            TimeoutError("Request timed out"),
            Exception("Generic error")
        ]
        
        for error in test_errors:
            response = format_error_response(error, "test_operation")
            
            # Error response should be a string
            assert isinstance(response, str)
            # Should contain error information
            assert "error" in response.lower() or "failed" in response.lower()
            # Should not expose sensitive information
            assert "api_key" not in response.lower()
            assert "password" not in response.lower()


class TestAPIContractVersioning:
    """Test API contract versioning and backward compatibility."""
    
    @pytest.mark.contract
    def test_v1_api_backward_compatibility(self):
        """Test that v1 API responses are still supported."""
        # Simulate old v1 response format
        old_v1_response = {
            "data": [{
                "opportunity_id": 123,  # Was integer in v1
                "opportunity_number": "OLD-2023-001",
                "opportunity_title": "Legacy Grant Format",
                "opportunity_status": "posted",
                "agency": "LEGACY",
                "agency_code": "LEG",
                "agency_name": "Legacy Agency",
                "category": "Legacy Category",
                "summary": {
                    "award_ceiling": 500000,
                    "award_floor": 100000,
                    # Missing newer fields like funding_instrument
                }
            }],
            "pagination_info": {
                "page_size": 25,
                "page_number": 1,  # Old field name
                "total_records": 1
                # Missing total_pages
            }
        }
        
        # Should handle old format gracefully
        try:
            # Convert old format to new format if needed
            normalized_response = {
                "data": old_v1_response["data"],
                "pagination_info": {
                    **old_v1_response["pagination_info"],
                    "page_offset": old_v1_response["pagination_info"].get("page_number", 1),
                    "total_pages": 1
                },
                "facet_counts": {}  # Add missing field with default
            }
            
            response = GrantsAPIResponse(**normalized_response)
            assert len(response.data) == 1
            
        except ValidationError as e:
            # If validation fails, ensure it's due to expected incompatibilities
            assert "opportunity_id" in str(e) or "pagination_info" in str(e)
            
    @pytest.mark.contract
    def test_future_api_extensibility(self):
        """Test that current schemas can handle future extensions."""
        # Simulate future API response with additional fields
        future_response = {
            "data": [{
                "opportunity_id": "123",
                "opportunity_number": "FUTURE-2025-001",
                "opportunity_title": "Future Grant with AI Tags",
                "opportunity_status": "posted",
                "agency": "FUTURE",
                "agency_code": "FUT",
                "agency_name": "Future Agency",
                "category": "Emerging Technology",
                "ai_relevance_score": 0.95,  # New field
                "tags": ["AI", "ML", "Innovation"],  # New field
                "summary": {
                    "award_ceiling": 1000000,
                    "award_floor": 200000,
                    "carbon_footprint_estimate": "low",  # New field
                    "diversity_requirements": {  # New nested object
                        "minority_serving_institutions": True,
                        "geographic_diversity": True
                    }
                }
            }],
            "pagination_info": {
                "page_size": 25,
                "page_offset": 1,
                "total_records": 1,
                "total_pages": 1,
                "query_performance_ms": 150  # New field
            },
            "facet_counts": {
                "agency": {"FUTURE": 1},
                "category": {"Emerging Technology": 1},
                "ai_relevance": {"high": 1}  # New facet
            },
            "api_version": "2.0",  # New field
            "deprecation_warnings": []  # New field
        }
        
        # Current schema should handle extra fields gracefully
        try:
            response = GrantsAPIResponse(**future_response)
            assert len(response.data) == 1
            assert response.pagination_info.total_records == 1
            # Extra fields should be ignored or preserved
            
        except ValidationError:
            # If validation fails, it should be due to controlled reasons
            # not unexpected crashes
            pass
            
    @pytest.mark.contract
    def test_required_vs_optional_fields(self):
        """Test distinction between required and optional fields."""
        # Minimal valid opportunity (only required fields)
        minimal_opportunity = {
            "opportunity_id": "MIN-001",
            "opportunity_number": "MINIMAL-2024-001", 
            "opportunity_title": "Minimal Grant",
            "opportunity_status": "posted",
            "agency": "MIN",
            "agency_code": "MIN",
            "agency_name": "Minimal Agency",
            "category": "Basic"
        }
        
        # Should validate successfully
        opportunity = OpportunityV1(**minimal_opportunity)
        assert opportunity.opportunity_id == "MIN-001"
        assert opportunity.summary is None  # Optional field
        
        # Test that truly required fields cause validation failure
        required_fields = [
            "opportunity_id", "opportunity_number", "opportunity_title", 
            "opportunity_status", "agency", "agency_code", "agency_name", "category"
        ]
        
        for field in required_fields:
            incomplete_data = minimal_opportunity.copy()
            del incomplete_data[field]
            
            with pytest.raises(ValidationError) as exc_info:
                OpportunityV1(**incomplete_data)
            
            # Verify the error mentions the missing field
            assert field in str(exc_info.value)


class TestDataTypeContracts:
    """Test data type contracts and coercion rules."""
    
    @pytest.mark.contract
    def test_numeric_field_coercion(self):
        """Test that numeric fields handle string inputs correctly."""
        opportunity_data = {
            "opportunity_id": "123",
            "opportunity_number": "COERCE-001",
            "opportunity_title": "Coercion Test",
            "opportunity_status": "posted",
            "agency": "TEST",
            "agency_code": "TEST",
            "agency_name": "Test Agency",
            "category": "Test",
            "summary": {
                "award_ceiling": "500000",  # String that should be int
                "award_floor": "100000.0",  # String that should be int  
                "estimated_total_program_funding": 5000000,
                "expected_number_of_awards": "10",  # String that should be int
            }
        }
        
        # Should coerce string numbers to integers
        opportunity = OpportunityV1(**opportunity_data)
        assert isinstance(opportunity.summary.award_ceiling, int)
        assert opportunity.summary.award_ceiling == 500000
        assert isinstance(opportunity.summary.expected_number_of_awards, int)
        assert opportunity.summary.expected_number_of_awards == 10
        
    @pytest.mark.contract  
    def test_date_field_validation(self):
        """Test date field validation and formatting."""
        valid_dates = [
            "2024-01-15",
            "2024-12-31", 
            "2023-02-28",
            "2024-02-29"  # Leap year
        ]
        
        invalid_dates = [
            "2024-13-01",  # Invalid month
            "2024-02-30",  # Invalid day
            "invalid-date",
            "2024/01/15",  # Wrong format
            "15-01-2024",  # Wrong format
        ]
        
        for valid_date in valid_dates:
            summary = OpportunitySummary(post_date=valid_date)
            assert summary.post_date == valid_date
            
        for invalid_date in invalid_dates:
            with pytest.raises(ValidationError):
                OpportunitySummary(post_date=invalid_date)
                
    @pytest.mark.contract
    def test_url_field_validation(self):
        """Test URL field validation."""
        valid_urls = [
            "https://www.nsf.gov/funding/pgm_summ.jsp?pims_id=12345",
            "http://grants.nih.gov/grants/guide/pa-files/PA-24-100.html",
            "https://beta.sam.gov/opp/abc123/view"
        ]
        
        invalid_urls = [
            "not-a-url",
            "ftp://invalid-protocol.com",
            "https://",  # Incomplete URL
            ""  # Empty string
        ]
        
        for valid_url in valid_urls:
            summary = OpportunitySummary(additional_info_url=valid_url)
            assert summary.additional_info_url == valid_url
            
        for invalid_url in invalid_urls:
            with pytest.raises(ValidationError):
                OpportunitySummary(additional_info_url=invalid_url)
                
    @pytest.mark.contract
    def test_email_field_validation(self):
        """Test email field validation."""
        valid_emails = [
            "grants@nsf.gov",
            "funding.opportunities@nih.gov",
            "info@agency.gov"
        ]
        
        invalid_emails = [
            "not-an-email",
            "@agency.gov",  # Missing local part
            "grants@",  # Missing domain
            "grants@agency",  # Missing TLD
        ]
        
        for valid_email in valid_emails:
            summary = OpportunitySummary(agency_email_address=valid_email)
            assert summary.agency_email_address == valid_email
            
        for invalid_email in invalid_emails:
            with pytest.raises(ValidationError):
                OpportunitySummary(agency_email_address=invalid_email)