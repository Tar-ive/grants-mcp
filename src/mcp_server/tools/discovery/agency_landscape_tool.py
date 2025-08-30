"""Agency landscape analysis tool for mapping agencies and their funding focus areas."""

import logging
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

from src.mcp_server.models.grants_schemas import AgencyV1, GrantsAPIResponse, OpportunityV1
from src.mcp_server.tools.utils.api_client import APIError, SimplerGrantsAPIClient
from src.mcp_server.tools.utils.cache_manager import InMemoryCache
from src.mcp_server.tools.utils.cache_utils import CacheKeyGenerator

logger = logging.getLogger(__name__)


def analyze_agency_portfolio(
    agency_code: str,
    opportunities: List[OpportunityV1]
) -> Dict[str, Any]:
    """
    Analyze an agency's grant portfolio.
    
    Args:
        agency_code: Agency code to analyze
        opportunities: List of opportunities from this agency
        
    Returns:
        Analysis of the agency's portfolio
    """
    portfolio = {
        "agency_code": agency_code,
        "total_opportunities": len(opportunities),
        "status_breakdown": defaultdict(int),
        "category_breakdown": defaultdict(int),
        "funding_stats": {
            "total_estimated_funding": 0,
            "average_award_ceiling": 0,
            "average_award_floor": 0,
            "min_award": None,
            "max_award": None,
        },
        "deadline_distribution": defaultdict(int),
        "eligibility_patterns": defaultdict(int),
    }
    
    award_ceilings = []
    award_floors = []
    total_funding = 0
    
    for opp in opportunities:
        # Status breakdown
        portfolio["status_breakdown"][opp.opportunity_status] += 1
        
        # Category breakdown
        if opp.category:
            portfolio["category_breakdown"][opp.category] += 1
        
        # Funding analysis
        summary = opp.summary
        if summary.award_ceiling:
            award_ceilings.append(summary.award_ceiling)
            if portfolio["funding_stats"]["max_award"] is None:
                portfolio["funding_stats"]["max_award"] = summary.award_ceiling
            else:
                portfolio["funding_stats"]["max_award"] = max(
                    portfolio["funding_stats"]["max_award"],
                    summary.award_ceiling
                )
        
        if summary.award_floor:
            award_floors.append(summary.award_floor)
            if portfolio["funding_stats"]["min_award"] is None:
                portfolio["funding_stats"]["min_award"] = summary.award_floor
            else:
                portfolio["funding_stats"]["min_award"] = min(
                    portfolio["funding_stats"]["min_award"],
                    summary.award_floor
                )
        
        if summary.estimated_total_program_funding:
            total_funding += summary.estimated_total_program_funding
        
        # Deadline distribution
        if summary.close_date:
            try:
                # Extract month from close date
                month = summary.close_date.split("-")[1] if "-" in summary.close_date else "Unknown"
                portfolio["deadline_distribution"][f"Month_{month}"] += 1
            except:
                pass
        
        # Eligibility patterns (simplified)
        if summary.applicant_types:
            for applicant_type in summary.applicant_types:
                portfolio["eligibility_patterns"][applicant_type] += 1
    
    # Calculate averages
    if award_ceilings:
        portfolio["funding_stats"]["average_award_ceiling"] = sum(award_ceilings) / len(award_ceilings)
    if award_floors:
        portfolio["funding_stats"]["average_award_floor"] = sum(award_floors) / len(award_floors)
    portfolio["funding_stats"]["total_estimated_funding"] = total_funding
    
    # Convert defaultdicts to regular dicts for JSON serialization
    portfolio["status_breakdown"] = dict(portfolio["status_breakdown"])
    portfolio["category_breakdown"] = dict(portfolio["category_breakdown"])
    portfolio["deadline_distribution"] = dict(portfolio["deadline_distribution"])
    portfolio["eligibility_patterns"] = dict(portfolio["eligibility_patterns"])
    
    return portfolio


def identify_cross_agency_patterns(
    agency_profiles: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Identify patterns across multiple agencies.
    
    Args:
        agency_profiles: Dictionary of agency profiles
        
    Returns:
        Cross-agency analysis
    """
    patterns = {
        "overlap_areas": [],
        "unique_specializations": {},
        "collaboration_patterns": {},
        "funding_comparison": {},
    }
    
    # Find overlapping categories
    all_categories = defaultdict(list)
    for agency_code, profile in agency_profiles.items():
        for category in profile.get("category_breakdown", {}).keys():
            all_categories[category].append(agency_code)
    
    # Identify overlaps and unique specializations
    for category, agencies in all_categories.items():
        if len(agencies) > 1:
            patterns["overlap_areas"].append({
                "category": category,
                "agencies": agencies,
                "count": len(agencies)
            })
        elif len(agencies) == 1:
            agency = agencies[0]
            if agency not in patterns["unique_specializations"]:
                patterns["unique_specializations"][agency] = []
            patterns["unique_specializations"][agency].append(category)
    
    # Compare funding levels
    for agency_code, profile in agency_profiles.items():
        funding_stats = profile.get("funding_stats", {})
        patterns["funding_comparison"][agency_code] = {
            "average_ceiling": funding_stats.get("average_award_ceiling", 0),
            "average_floor": funding_stats.get("average_award_floor", 0),
            "total_opportunities": profile.get("total_opportunities", 0),
        }
    
    return patterns


def format_agency_landscape_report(
    agencies: List[AgencyV1],
    agency_profiles: Dict[str, Dict[str, Any]],
    cross_agency_analysis: Dict[str, Any],
    funding_landscape: Dict[str, Any]
) -> str:
    """
    Format the agency landscape analysis as a readable report.
    
    Args:
        agencies: List of agencies
        agency_profiles: Individual agency analyses
        cross_agency_analysis: Cross-agency patterns
        funding_landscape: Overall funding landscape
        
    Returns:
        Formatted report string
    """
    report = """
AGENCY LANDSCAPE ANALYSIS
=========================

OVERVIEW
--------"""
    
    report += f"\nTotal Active Agencies: {funding_landscape['total_active_agencies']}"
    report += f"\nTotal Opportunities Analyzed: {sum(p['total_opportunities'] for p in agency_profiles.values())}"
    
    # Top agencies by opportunity count
    top_agencies = sorted(
        agency_profiles.items(),
        key=lambda x: x[1]['total_opportunities'],
        reverse=True
    )[:5]
    
    report += "\n\nTOP AGENCIES BY OPPORTUNITY COUNT\n" + "-" * 35
    for agency_code, profile in top_agencies:
        agency_name = next((a.agency_name for a in agencies if a.agency_code == agency_code), agency_code)
        report += f"\n{agency_code}: {agency_name}"
        report += f"\n  • Opportunities: {profile['total_opportunities']}"
        report += f"\n  • Categories: {', '.join(profile['category_breakdown'].keys())[:100]}"
        if profile['funding_stats']['average_award_ceiling']:
            report += f"\n  • Avg Award Ceiling: ${profile['funding_stats']['average_award_ceiling']:,.0f}"
    
    # Cross-agency patterns
    if cross_agency_analysis['overlap_areas']:
        report += "\n\nCROSS-AGENCY COLLABORATION AREAS\n" + "-" * 33
        for overlap in cross_agency_analysis['overlap_areas'][:5]:
            report += f"\n• {overlap['category']}: {', '.join(overlap['agencies'])}"
    
    # Unique specializations
    if cross_agency_analysis['unique_specializations']:
        report += "\n\nUNIQUE AGENCY SPECIALIZATIONS\n" + "-" * 30
        for agency, specializations in list(cross_agency_analysis['unique_specializations'].items())[:5]:
            report += f"\n{agency}: {', '.join(specializations[:3])}"
    
    # Funding distribution
    report += "\n\nFUNDING LANDSCAPE\n" + "-" * 17
    total_funding = sum(
        p['funding_stats']['total_estimated_funding'] 
        for p in agency_profiles.values()
    )
    if total_funding > 0:
        report += f"\nTotal Estimated Funding: ${total_funding:,.0f}"
    
    # Category distribution
    if funding_landscape.get('category_specialization'):
        report += "\n\nFUNDING BY CATEGORY\n" + "-" * 19
        for category, count in list(funding_landscape['category_specialization'].items())[:5]:
            report += f"\n• {category}: {count} opportunities"
    
    report += "\n\n" + "=" * 60
    
    return report


def register_agency_landscape_tool(mcp: Any, context: Dict[str, Any]) -> None:
    """
    Register the agency landscape tool with the MCP server.
    
    Args:
        mcp: FastMCP instance
        context: Server context containing cache, API client, etc.
    """
    cache: InMemoryCache = context["cache"]
    api_client: SimplerGrantsAPIClient = context["api_client"]
    
    @mcp.tool
    async def agency_landscape(
        include_opportunities: bool = True,
        focus_agencies: Optional[List[str]] = None,
        funding_category: Optional[str] = None,
        max_agencies: int = 10
    ) -> str:
        """
        Map agencies and their funding focus areas with comprehensive analysis.
        
        This tool provides insights into agency funding patterns, specializations,
        and cross-agency collaboration opportunities.
        
        Args:
            include_opportunities: Include opportunity analysis (default: True)
            focus_agencies: Specific agency codes to analyze (e.g., ["NSF", "NIH"])
            funding_category: Filter by funding category
            max_agencies: Maximum number of agencies to analyze (default: 10)
            
        Returns:
            Comprehensive agency landscape analysis report
        """
        try:
            start_time = time.time()
            
            # Generate optimized cache key
            cache_key = CacheKeyGenerator.generate_simple(
                "agency_landscape",
                include_opportunities=include_opportunities,
                focus_agencies=focus_agencies,
                funding_category=funding_category,
                max_agencies=max_agencies
            )
            
            # Check cache
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info("Cache hit for agency landscape analysis")
                return cached_result["report"]
            
            logger.info(f"Analyzing agency landscape (max_agencies={max_agencies})")
            
            # Prepare filters for agency search
            agency_filters = {}
            if focus_agencies:
                # Note: API might not support direct agency code filtering in agency search
                # We'll filter the results manually
                pass
            
            # Search for agencies
            logger.debug("Fetching agencies from API")
            agency_response = await api_client.search_agencies(
                filters=agency_filters,
                pagination={"page_size": 100, "page_offset": 1}
            )
            
            # Parse response
            api_response = GrantsAPIResponse(**agency_response)
            all_agencies = api_response.get_agencies()
            
            # Filter agencies if specific ones requested
            if focus_agencies:
                agencies = [a for a in all_agencies if a.agency_code in focus_agencies]
            else:
                agencies = all_agencies[:max_agencies]
            
            logger.info(f"Analyzing {len(agencies)} agencies")
            
            # Analyze each agency's opportunities
            agency_profiles = {}
            
            if include_opportunities:
                for agency in agencies:
                    try:
                        # Search for opportunities from this agency
                        opp_filters = {
                            "agency_code": agency.agency_code,
                            "opportunity_status": {
                                "one_of": ["posted", "forecasted"]
                            }
                        }
                        
                        if funding_category:
                            opp_filters["category"] = funding_category
                        
                        opp_response = await api_client.search_opportunities(
                            filters=opp_filters,
                            pagination={"page_size": 50, "page_offset": 1}
                        )
                        
                        opp_api_response = GrantsAPIResponse(**opp_response)
                        opportunities = opp_api_response.get_opportunities()
                        
                        # Analyze this agency's portfolio
                        agency_profiles[agency.agency_code] = analyze_agency_portfolio(
                            agency.agency_code,
                            opportunities
                        )
                        agency_profiles[agency.agency_code]["agency_name"] = agency.agency_name
                        
                    except Exception as e:
                        logger.warning(f"Error analyzing agency {agency.agency_code}: {e}")
                        # Create minimal profile
                        agency_profiles[agency.agency_code] = {
                            "agency_code": agency.agency_code,
                            "agency_name": agency.agency_name,
                            "total_opportunities": 0,
                            "error": str(e)
                        }
            
            # Cross-agency analysis
            cross_agency_analysis = identify_cross_agency_patterns(agency_profiles)
            
            # Overall funding landscape
            funding_landscape = {
                "total_active_agencies": len(agencies),
                "funding_distribution": {},
                "category_specialization": defaultdict(int),
            }
            
            # Aggregate category specialization
            for profile in agency_profiles.values():
                for category, count in profile.get("category_breakdown", {}).items():
                    funding_landscape["category_specialization"][category] += count
            
            funding_landscape["category_specialization"] = dict(
                sorted(
                    funding_landscape["category_specialization"].items(),
                    key=lambda x: x[1],
                    reverse=True
                )
            )
            
            # Generate report
            report = format_agency_landscape_report(
                agencies,
                agency_profiles,
                cross_agency_analysis,
                funding_landscape
            )
            
            # Prepare result for caching
            result = {
                "agencies": agencies,
                "agency_profiles": agency_profiles,
                "cross_agency_analysis": cross_agency_analysis,
                "funding_landscape": funding_landscape,
                "report": report,
                "metadata": {
                    "analysis_time": time.time() - start_time,
                    "agencies_analyzed": len(agencies),
                    "cache_used": False
                }
            }
            
            # Cache the result
            cache.set(cache_key, result)
            
            return report
            
        except APIError as e:
            logger.error(f"API error during agency landscape analysis: {e}")
            return f"Error analyzing agency landscape: {e}"
            
        except Exception as e:
            logger.error(f"Unexpected error during agency landscape analysis: {e}", exc_info=True)
            return f"An unexpected error occurred: {e}"
    
    logger.info("Registered agency_landscape tool")