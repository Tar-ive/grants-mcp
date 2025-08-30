"""Opportunity discovery tool for searching and analyzing grant opportunities."""

import logging
import time
from typing import Any, Dict, List, Optional

from src.mcp_server.models.grants_schemas import GrantsAPIResponse, OpportunityV1
from src.mcp_server.tools.utils.api_client import APIError
from src.mcp_server.tools.utils.cache_manager import InMemoryCache
from src.mcp_server.tools.utils.cache_utils import CacheKeyGenerator

logger = logging.getLogger(__name__)


def format_grant_details(grant: OpportunityV1) -> str:
    """
    Format grant details for display (matching TypeScript version).
    
    Args:
        grant: Grant opportunity
        
    Returns:
        Formatted grant details string
    """
    summary = grant.summary
    
    # Format funding amounts
    award_floor = f"${summary.award_floor:,.0f}" if summary.award_floor else "Not specified"
    award_ceiling = f"${summary.award_ceiling:,.0f}" if summary.award_ceiling else "Not specified"
    
    # Clean up HTML in descriptions
    eligibility = summary.applicant_eligibility_description or "Eligibility information not provided"
    if eligibility and eligibility != "Eligibility information not provided":
        eligibility = eligibility.replace('<br/>', '\n').strip()
    
    description = summary.summary_description or "No description available"
    if description and description != "No description available":
        description = description.replace('<br/>', '\n').strip()
    
    return f"""
OPPORTUNITY DETAILS
------------------
Title: {grant.opportunity_title}
Opportunity Number: {grant.opportunity_number}
Agency: {grant.agency_name} ({grant.agency_code})
Status: {grant.opportunity_status}

FUNDING INFORMATION
------------------
Award Floor: {award_floor}
Award Ceiling: {award_ceiling}
Category: {grant.category or 'Not specified'}

DATES AND DEADLINES
------------------
Posted Date: {summary.post_date or 'N/A'}
Close Date: {summary.close_date or 'N/A'}

CONTACT INFORMATION
------------------
Agency Contact: {summary.agency_contact_description or 'Not provided'}
Email: {summary.agency_email_address or 'Not provided'}
Phone: {summary.agency_phone_number or 'Not provided'}

ELIGIBILITY
------------------
{eligibility}

ADDITIONAL INFORMATION
------------------
More Details URL: {summary.additional_info_url or 'Not available'}

Description:
{description}

{'=' * 74}
"""


def create_summary(
    opportunities: List[OpportunityV1],
    search_query: str,
    page: int = 1,
    grants_per_page: int = 3,
    total_found: int = 0
) -> str:
    """
    Create a summary of search results (matching TypeScript version).
    
    Args:
        opportunities: List of opportunities
        search_query: Search query used
        page: Current page number
        grants_per_page: Grants per page
        total_found: Total opportunities found
        
    Returns:
        Formatted summary string
    """
    start_idx = (page - 1) * grants_per_page
    end_idx = min(start_idx + grants_per_page, len(opportunities))
    displayed_grants = opportunities[start_idx:end_idx]
    total_pages = (len(opportunities) + grants_per_page - 1) // grants_per_page
    
    formatted_grants = "\n".join(format_grant_details(grant) for grant in displayed_grants)
    
    return f"""Search Results for "{search_query}":

OVERVIEW
--------
Total Grants Found: {total_found}
Showing grants {start_idx + 1} to {end_idx} of {len(opportunities)}
Page {page} of {total_pages}

DETAILED GRANT LISTINGS
----------------------
{formatted_grants}

Note: Showing {grants_per_page} grants per page. Total grants available: {total_found}
"""


def calculate_summary_statistics(opportunities: List[OpportunityV1]) -> Dict[str, Any]:
    """
    Calculate summary statistics for opportunities.
    
    Args:
        opportunities: List of opportunities
        
    Returns:
        Summary statistics
    """
    stats = {
        "agencies": {},
        "funding_ranges": {
            "min_floor": None,
            "max_ceiling": None,
            "avg_award": None,
        },
        "deadline_distribution": {},
        "category_breakdown": {},
        "status_breakdown": {},
    }
    
    total_awards = []
    
    for opp in opportunities:
        # Agency stats
        agency = opp.agency_code
        stats["agencies"][agency] = stats["agencies"].get(agency, 0) + 1
        
        # Category stats
        category = opp.category or "Uncategorized"
        stats["category_breakdown"][category] = stats["category_breakdown"].get(category, 0) + 1
        
        # Status stats
        status = opp.opportunity_status
        stats["status_breakdown"][status] = stats["status_breakdown"].get(status, 0) + 1
        
        # Funding stats
        if opp.summary.award_floor:
            if stats["funding_ranges"]["min_floor"] is None:
                stats["funding_ranges"]["min_floor"] = opp.summary.award_floor
            else:
                stats["funding_ranges"]["min_floor"] = min(
                    stats["funding_ranges"]["min_floor"],
                    opp.summary.award_floor
                )
        
        if opp.summary.award_ceiling:
            if stats["funding_ranges"]["max_ceiling"] is None:
                stats["funding_ranges"]["max_ceiling"] = opp.summary.award_ceiling
            else:
                stats["funding_ranges"]["max_ceiling"] = max(
                    stats["funding_ranges"]["max_ceiling"],
                    opp.summary.award_ceiling
                )
            total_awards.append(opp.summary.award_ceiling)
        
        # Deadline distribution
        if opp.summary.close_date:
            # Extract month from close date
            try:
                month = opp.summary.close_date.split("-")[1] if "-" in opp.summary.close_date else "Unknown"
                stats["deadline_distribution"][month] = stats["deadline_distribution"].get(month, 0) + 1
            except:
                pass
    
    # Calculate average award
    if total_awards:
        stats["funding_ranges"]["avg_award"] = sum(total_awards) / len(total_awards)
    
    return stats


def register_opportunity_discovery_tool(mcp: Any, context: Dict[str, Any]) -> None:
    """
    Register the opportunity discovery tool with the MCP server.
    
    Args:
        mcp: FastMCP instance
        context: Server context containing cache, API client, etc.
    """
    cache: InMemoryCache = context["cache"]
    api_client = context["api_client"]
    search_history = context["search_history"]
    
    @mcp.tool
    async def opportunity_discovery(
        query: Optional[str] = None,
        filters: Optional[Dict] = None,
        max_results: int = 100,
        page: int = 1,
        grants_per_page: int = 3,
    ) -> str:
        """
        Search for grant opportunities and provide detailed analysis.
        
        This tool searches the Simpler Grants API for current and forecasted
        opportunities, providing comprehensive details and summary statistics.
        
        Args:
            query: Search keywords (e.g., "renewable energy", "climate change")
            filters: Advanced filter parameters for the API
            max_results: Maximum number of results to retrieve (default: 100)
            page: Page number for display pagination (default: 1)
            grants_per_page: Number of grants to display per page (default: 3)
            
        Returns:
            Formatted search results with statistics and detailed grant information
        """
        try:
            start_time = time.time()
            
            # Generate optimized cache key
            cache_key = CacheKeyGenerator.generate_simple(
                "opportunity_discovery",
                query=query,
                filters=filters,
                max_results=max_results
            )
            
            # Check cache
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info(f"Cache hit for query: {query}")
                # Format cached results for display
                opportunities = cached_result["opportunities"]
                
                # For compatibility with TypeScript version, return formatted string
                return create_summary(
                    opportunities[:max_results],
                    query or "all opportunities",
                    page,
                    grants_per_page,
                    cached_result["total_found"]
                )
            
            # Prepare API call parameters
            search_filters = filters or {}
            
            # Default to current and forecasted opportunities
            if "opportunity_status" not in search_filters:
                search_filters["opportunity_status"] = {
                    "one_of": ["posted", "forecasted"]
                }
            
            pagination_params = {
                "page_size": min(max_results, 100),  # API limit
                "page_offset": 1,
                "order_by": "opportunity_id",
                "sort_direction": "descending"
            }
            
            # Make API call
            logger.info(f"Searching opportunities with query: {query}")
            response_data = await api_client.search_opportunities(
                query=query,
                filters=search_filters,
                pagination=pagination_params
            )
            
            # Parse response
            api_response = GrantsAPIResponse(**response_data)
            opportunities = api_response.get_opportunities()
            
            # Calculate statistics
            summary_stats = calculate_summary_statistics(opportunities)
            
            # Prepare result for caching
            result = {
                "opportunities": opportunities,
                "total_found": api_response.pagination_info.total_records,
                "search_parameters": {
                    "query": query,
                    "filters": search_filters,
                    "max_results": max_results
                },
                "summary_stats": summary_stats,
                "metadata": {
                    "search_time": time.time() - start_time,
                    "api_status": "success",
                    "cache_used": False
                }
            }
            
            # Cache the result
            cache.set(cache_key, result)
            
            # Track search history
            search_history.append({
                "timestamp": time.time(),
                "query": query,
                "filters": search_filters,
                "results_count": len(opportunities),
                "total_found": api_response.pagination_info.total_records
            })
            
            # Return formatted summary (matching TypeScript output format)
            return create_summary(
                opportunities[:max_results],
                query or "all opportunities",
                page,
                grants_per_page,
                api_response.pagination_info.total_records
            )
            
        except APIError as e:
            logger.error(f"API error during opportunity search: {e}")
            
            # Try to return cached data if available
            any_cached = None
            for key in cache._cache:
                if key.startswith("discovery"):
                    any_cached = cache.get(key)
                    if any_cached:
                        break
            
            if any_cached:
                logger.info("Returning stale cached data due to API error")
                opportunities = any_cached["opportunities"]
                return f"⚠️ API Error - Showing cached results (may be outdated)\n\n" + \
                       create_summary(
                           opportunities[:max_results],
                           query or "all opportunities",
                           page,
                           grants_per_page,
                           any_cached["total_found"]
                       )
            
            return f"Error searching for opportunities: {e}"
            
        except Exception as e:
            logger.error(f"Unexpected error during opportunity search: {e}", exc_info=True)
            return f"An unexpected error occurred: {e}"
    
    logger.info("Registered opportunity_discovery tool")