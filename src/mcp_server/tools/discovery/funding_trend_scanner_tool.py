"""Funding trend scanner tool for identifying patterns and emerging opportunities."""

import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from src.mcp_server.models.grants_schemas import GrantsAPIResponse, OpportunityV1
from src.mcp_server.tools.utils.api_client import APIError, SimplerGrantsAPIClient
from src.mcp_server.tools.utils.cache_manager import InMemoryCache
from src.mcp_server.tools.utils.cache_utils import CacheKeyGenerator

logger = logging.getLogger(__name__)


def analyze_temporal_trends(
    opportunities: List[OpportunityV1],
    time_window_days: int = 90
) -> Dict[str, Any]:
    """
    Analyze temporal trends in grant opportunities.
    
    Args:
        opportunities: List of opportunities to analyze
        time_window_days: Time window for trend analysis
        
    Returns:
        Temporal trend analysis
    """
    now = datetime.now()
    cutoff_date = now - timedelta(days=time_window_days)
    
    trends = {
        "posting_frequency": defaultdict(int),
        "deadline_distribution": defaultdict(int),
        "category_emergence": defaultdict(list),
        "funding_velocity": {
            "recent": 0,
            "older": 0,
            "acceleration": 0
        },
        "seasonal_patterns": defaultdict(int)
    }
    
    recent_opportunities = []
    older_opportunities = []
    
    for opp in opportunities:
        summary = opp.summary
        
        # Parse post date for temporal analysis
        if summary.post_date:
            try:
                post_date = datetime.fromisoformat(summary.post_date.replace("Z", "+00:00"))
                days_ago = (now - post_date).days
                
                # Categorize by recency
                if post_date >= cutoff_date:
                    recent_opportunities.append(opp)
                    week_num = (now - post_date).days // 7
                    trends["posting_frequency"][f"week_{week_num}"] += 1
                else:
                    older_opportunities.append(opp)
                
                # Track category emergence
                if opp.category:
                    trends["category_emergence"][opp.category].append(days_ago)
                
                # Seasonal patterns (by month)
                month_name = post_date.strftime("%B")
                trends["seasonal_patterns"][month_name] += 1
                
            except Exception as e:
                logger.debug(f"Error parsing date for opportunity {opp.opportunity_id}: {e}")
        
        # Deadline distribution
        if summary.close_date:
            try:
                close_date = datetime.fromisoformat(summary.close_date.replace("Z", "+00:00"))
                if close_date > now:
                    days_until = (close_date - now).days
                    if days_until <= 30:
                        trends["deadline_distribution"]["30_days"] += 1
                    elif days_until <= 60:
                        trends["deadline_distribution"]["60_days"] += 1
                    elif days_until <= 90:
                        trends["deadline_distribution"]["90_days"] += 1
                    else:
                        trends["deadline_distribution"]["90_plus_days"] += 1
            except:
                pass
    
    # Calculate funding velocity
    recent_funding = sum(
        opp.summary.estimated_total_program_funding or 0
        for opp in recent_opportunities
    )
    older_funding = sum(
        opp.summary.estimated_total_program_funding or 0
        for opp in older_opportunities
    )
    
    trends["funding_velocity"]["recent"] = recent_funding
    trends["funding_velocity"]["older"] = older_funding
    
    if older_funding > 0:
        trends["funding_velocity"]["acceleration"] = (
            (recent_funding - older_funding) / older_funding * 100
        )
    
    # Identify emerging categories (those with increasing frequency)
    for category, days_list in trends["category_emergence"].items():
        if len(days_list) >= 3:
            # Check if postings are getting more recent
            sorted_days = sorted(days_list)
            if sorted_days[0] < sorted_days[-1] / 2:  # Recent activity is higher
                trends["category_emergence"][category] = "emerging"
            else:
                trends["category_emergence"][category] = "stable"
        else:
            trends["category_emergence"][category] = "limited_data"
    
    # Convert defaultdicts to regular dicts
    trends["posting_frequency"] = dict(trends["posting_frequency"])
    trends["deadline_distribution"] = dict(trends["deadline_distribution"])
    trends["seasonal_patterns"] = dict(trends["seasonal_patterns"])
    trends["category_emergence"] = dict(trends["category_emergence"])
    
    return trends


def identify_funding_patterns(
    opportunities: List[OpportunityV1]
) -> Dict[str, Any]:
    """
    Identify patterns in funding amounts and distributions.
    
    Args:
        opportunities: List of opportunities to analyze
        
    Returns:
        Funding pattern analysis
    """
    patterns = {
        "funding_tiers": {
            "micro": [],  # < $100k
            "small": [],  # $100k - $500k
            "medium": [],  # $500k - $1M
            "large": [],  # $1M - $5M
            "mega": []    # > $5M
        },
        "award_size_trends": defaultdict(list),
        "funding_instruments": defaultdict(int),
        "high_value_opportunities": [],
        "best_roi_opportunities": []  # High funding, low competition
    }
    
    for opp in opportunities:
        summary = opp.summary
        
        # Categorize by funding tier
        if summary.award_ceiling:
            if summary.award_ceiling < 100000:
                patterns["funding_tiers"]["micro"].append(opp)
            elif summary.award_ceiling < 500000:
                patterns["funding_tiers"]["small"].append(opp)
            elif summary.award_ceiling < 1000000:
                patterns["funding_tiers"]["medium"].append(opp)
            elif summary.award_ceiling < 5000000:
                patterns["funding_tiers"]["large"].append(opp)
            else:
                patterns["funding_tiers"]["mega"].append(opp)
            
            # Track award sizes by category
            if opp.category:
                patterns["award_size_trends"][opp.category].append(summary.award_ceiling)
        
        # Track funding instruments
        if summary.funding_instrument:
            patterns["funding_instruments"][summary.funding_instrument] += 1
        
        # Identify high-value opportunities
        if summary.estimated_total_program_funding and summary.estimated_total_program_funding > 1000000:
            patterns["high_value_opportunities"].append({
                "opportunity_id": opp.opportunity_id,
                "title": opp.opportunity_title,
                "total_funding": summary.estimated_total_program_funding,
                "award_ceiling": summary.award_ceiling,
                "close_date": summary.close_date
            })
        
        # Identify best ROI opportunities (high funding, expected few awards)
        if (summary.estimated_total_program_funding and 
            summary.expected_number_of_awards and
            summary.expected_number_of_awards <= 5 and
            summary.estimated_total_program_funding > 500000):
            
            avg_award = summary.estimated_total_program_funding / summary.expected_number_of_awards
            patterns["best_roi_opportunities"].append({
                "opportunity_id": opp.opportunity_id,
                "title": opp.opportunity_title,
                "avg_award": avg_award,
                "num_awards": summary.expected_number_of_awards,
                "close_date": summary.close_date
            })
    
    # Calculate average award sizes by category
    for category, amounts in patterns["award_size_trends"].items():
        if amounts:
            patterns["award_size_trends"][category] = {
                "average": sum(amounts) / len(amounts),
                "min": min(amounts),
                "max": max(amounts),
                "count": len(amounts)
            }
    
    # Sort high-value and ROI opportunities
    patterns["high_value_opportunities"].sort(
        key=lambda x: x["total_funding"],
        reverse=True
    )
    patterns["best_roi_opportunities"].sort(
        key=lambda x: x["avg_award"],
        reverse=True
    )
    
    # Convert funding tiers to counts for summary
    tier_summary = {
        tier: len(opps) 
        for tier, opps in patterns["funding_tiers"].items()
    }
    patterns["funding_tier_summary"] = tier_summary
    
    # Convert defaultdicts
    patterns["funding_instruments"] = dict(patterns["funding_instruments"])
    patterns["award_size_trends"] = dict(patterns["award_size_trends"])
    
    return patterns


def detect_emerging_topics(
    opportunities: List[OpportunityV1]
) -> Dict[str, Any]:
    """
    Detect emerging topics and themes in grant opportunities.
    
    Args:
        opportunities: List of opportunities to analyze
        
    Returns:
        Emerging topics analysis
    """
    topics = {
        "keyword_frequency": defaultdict(int),
        "category_combinations": defaultdict(int),
        "emerging_themes": [],
        "cross_cutting_themes": []
    }
    
    # Common emerging technology and priority keywords
    emerging_keywords = [
        "artificial intelligence", "ai", "machine learning", "ml",
        "climate", "sustainability", "renewable", "clean energy",
        "quantum", "biotechnology", "genomics", "precision medicine",
        "cybersecurity", "data science", "blockchain", "iot",
        "equity", "diversity", "inclusion", "underserved",
        "pandemic", "resilience", "supply chain", "infrastructure"
    ]
    
    keyword_occurrences = defaultdict(list)
    
    for opp in opportunities:
        # Analyze title and description for keywords
        text = (opp.opportunity_title + " " + 
                (opp.summary.summary_description or "") + " " +
                (opp.category_explanation or "")).lower()
        
        for keyword in emerging_keywords:
            if keyword in text:
                topics["keyword_frequency"][keyword] += 1
                keyword_occurrences[keyword].append({
                    "opportunity_id": opp.opportunity_id,
                    "title": opp.opportunity_title,
                    "category": opp.category
                })
        
        # Track category combinations
        if opp.category and opp.agency_code:
            combo = f"{opp.category}_{opp.agency_code}"
            topics["category_combinations"][combo] += 1
    
    # Identify truly emerging themes (high frequency keywords)
    threshold = max(3, len(opportunities) * 0.05)  # At least 5% of opportunities
    
    for keyword, count in topics["keyword_frequency"].items():
        if count >= threshold:
            topics["emerging_themes"].append({
                "theme": keyword,
                "frequency": count,
                "percentage": (count / len(opportunities)) * 100,
                "examples": keyword_occurrences[keyword][:3]  # Top 3 examples
            })
    
    # Identify cross-cutting themes (keywords appearing across multiple categories)
    for keyword, occurrences in keyword_occurrences.items():
        categories = set(occ["category"] for occ in occurrences if occ.get("category"))
        if len(categories) >= 3:
            topics["cross_cutting_themes"].append({
                "theme": keyword,
                "categories": list(categories)[:5],
                "reach": len(categories)
            })
    
    # Sort by relevance
    topics["emerging_themes"].sort(key=lambda x: x["frequency"], reverse=True)
    topics["cross_cutting_themes"].sort(key=lambda x: x["reach"], reverse=True)
    
    # Convert defaultdicts
    topics["keyword_frequency"] = dict(topics["keyword_frequency"])
    topics["category_combinations"] = dict(
        sorted(
            topics["category_combinations"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]  # Top 10 combinations
    )
    
    return topics


def format_funding_trends_report(
    temporal_trends: Dict[str, Any],
    funding_patterns: Dict[str, Any],
    emerging_topics: Dict[str, Any],
    metadata: Dict[str, Any]
) -> str:
    """
    Format the funding trends analysis as a comprehensive report.
    
    Args:
        temporal_trends: Temporal trend analysis
        funding_patterns: Funding pattern analysis
        emerging_topics: Emerging topics analysis
        metadata: Analysis metadata
        
    Returns:
        Formatted report string
    """
    report = """
FUNDING TRENDS ANALYSIS REPORT
==============================

EXECUTIVE SUMMARY
-----------------"""
    
    # Summary stats
    report += f"\nOpportunities Analyzed: {metadata.get('total_opportunities', 0)}"
    report += f"\nTime Period: Last {metadata.get('time_window_days', 90)} days"
    report += f"\nTotal Funding Available: ${metadata.get('total_funding', 0):,.0f}"
    
    # Temporal Trends
    report += "\n\nTEMPORAL TRENDS\n" + "-" * 15
    
    # Posting frequency
    if temporal_trends["posting_frequency"]:
        report += "\n\nPosting Activity (by week):"
        for week, count in sorted(temporal_trends["posting_frequency"].items()):
            report += f"\n  • {week}: {count} opportunities"
    
    # Funding velocity
    velocity = temporal_trends["funding_velocity"]
    if velocity["recent"] or velocity["older"]:
        report += f"\n\nFunding Velocity:"
        report += f"\n  • Recent Period: ${velocity['recent']:,.0f}"
        report += f"\n  • Previous Period: ${velocity['older']:,.0f}"
        if velocity["acceleration"] != 0:
            direction = "↑" if velocity["acceleration"] > 0 else "↓"
            report += f"\n  • Acceleration: {direction} {abs(velocity['acceleration']):.1f}%"
    
    # Deadline distribution
    if temporal_trends["deadline_distribution"]:
        report += "\n\nUpcoming Deadlines:"
        for period, count in sorted(temporal_trends["deadline_distribution"].items()):
            report += f"\n  • {period}: {count} opportunities"
    
    # Funding Patterns
    report += "\n\nFUNDING PATTERNS\n" + "-" * 16
    
    # Funding tiers
    if funding_patterns["funding_tier_summary"]:
        report += "\n\nFunding Tiers Distribution:"
        tiers = funding_patterns["funding_tier_summary"]
        report += f"\n  • Micro (<$100K): {tiers.get('micro', 0)}"
        report += f"\n  • Small ($100K-$500K): {tiers.get('small', 0)}"
        report += f"\n  • Medium ($500K-$1M): {tiers.get('medium', 0)}"
        report += f"\n  • Large ($1M-$5M): {tiers.get('large', 0)}"
        report += f"\n  • Mega (>$5M): {tiers.get('mega', 0)}"
    
    # High-value opportunities
    if funding_patterns["high_value_opportunities"]:
        report += "\n\nTop High-Value Opportunities:"
        for opp in funding_patterns["high_value_opportunities"][:5]:
            report += f"\n  • {opp['title'][:60]}..."
            report += f"\n    Total: ${opp['total_funding']:,.0f}"
            if opp.get('close_date'):
                report += f" | Deadline: {opp['close_date']}"
    
    # Best ROI opportunities
    if funding_patterns["best_roi_opportunities"]:
        report += "\n\nBest ROI Opportunities (Low Competition):"
        for opp in funding_patterns["best_roi_opportunities"][:3]:
            report += f"\n  • {opp['title'][:60]}..."
            report += f"\n    Avg Award: ${opp['avg_award']:,.0f} ({opp['num_awards']} awards)"
    
    # Emerging Topics
    report += "\n\nEMERGING THEMES & TOPICS\n" + "-" * 24
    
    if emerging_topics["emerging_themes"]:
        report += "\n\nTrending Topics:"
        for theme in emerging_topics["emerging_themes"][:5]:
            report += f"\n  • {theme['theme'].title()}: "
            report += f"{theme['frequency']} occurrences ({theme['percentage']:.1f}%)"
    
    if emerging_topics["cross_cutting_themes"]:
        report += "\n\nCross-Cutting Themes:"
        for theme in emerging_topics["cross_cutting_themes"][:3]:
            report += f"\n  • {theme['theme'].title()}: "
            report += f"spans {theme['reach']} categories"
    
    # Recommendations
    report += "\n\nRECOMMENDATIONS\n" + "-" * 15
    
    # Based on trends
    if velocity.get("acceleration", 0) > 10:
        report += "\n• ⚡ Funding is accelerating - consider increasing proposal activity"
    
    if temporal_trends["deadline_distribution"].get("30_days", 0) > 5:
        report += "\n• ⏰ Multiple deadlines approaching - prioritize applications"
    
    if funding_patterns["best_roi_opportunities"]:
        report += "\n• 💰 High-value, low-competition opportunities available"
    
    if emerging_topics["emerging_themes"]:
        top_theme = emerging_topics["emerging_themes"][0]["theme"]
        report += f"\n• 🔬 Consider aligning proposals with '{top_theme}' theme"
    
    report += "\n\n" + "=" * 60
    
    return report


def register_funding_trend_scanner_tool(mcp: Any, context: Dict[str, Any]) -> None:
    """
    Register the funding trend scanner tool with the MCP server.
    
    Args:
        mcp: FastMCP instance
        context: Server context containing cache, API client, etc.
    """
    cache: InMemoryCache = context["cache"]
    api_client: SimplerGrantsAPIClient = context["api_client"]
    
    @mcp.tool
    async def funding_trend_scanner(
        time_window_days: int = 90,
        category_filter: Optional[str] = None,
        agency_filter: Optional[str] = None,
        min_award_amount: Optional[float] = None,
        include_forecasted: bool = True
    ) -> str:
        """
        Scan and analyze funding trends to identify patterns and emerging opportunities.
        
        This tool provides comprehensive trend analysis including temporal patterns,
        funding distributions, and emerging topics in grant opportunities.
        
        Args:
            time_window_days: Number of days to analyze (default: 90)
            category_filter: Filter by specific category
            agency_filter: Filter by specific agency code
            min_award_amount: Minimum award amount filter
            include_forecasted: Include forecasted opportunities (default: True)
            
        Returns:
            Comprehensive funding trends analysis report
        """
        try:
            start_time = time.time()
            
            # Generate optimized cache key using temporal strategy
            cache_key = CacheKeyGenerator.generate_temporal(
                "funding_trend_scanner",
                time_bucket=1800,  # 30-minute buckets for trends
                time_window_days=time_window_days,
                category_filter=category_filter,
                agency_filter=agency_filter,
                min_award_amount=min_award_amount,
                include_forecasted=include_forecasted
            )
            
            # Check cache
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info("Cache hit for funding trends analysis")
                return cached_result["report"]
            
            logger.info(f"Scanning funding trends (window={time_window_days} days)")
            
            # Prepare filters
            filters = {
                "opportunity_status": {
                    "one_of": ["posted"] if not include_forecasted else ["posted", "forecasted"]
                }
            }
            
            if category_filter:
                filters["category"] = category_filter
            
            if agency_filter:
                filters["agency_code"] = agency_filter
            
            if min_award_amount:
                filters["award_ceiling"] = {"min": min_award_amount}
            
            # Note: API doesn't support date range filtering directly
            # We'll fetch opportunities and filter by date in post-processing
            cutoff_date = datetime.now() - timedelta(days=time_window_days)
            
            # Fetch opportunities with larger page size for trend analysis
            all_opportunities = []
            page = 1
            max_pages = 5  # Limit to prevent excessive API calls
            
            while page <= max_pages:
                logger.debug(f"Fetching page {page} for trend analysis")
                
                response = await api_client.search_opportunities(
                    filters=filters,
                    pagination={"page_size": 100, "page_offset": page}
                )
                
                api_response = GrantsAPIResponse(**response)
                opportunities = api_response.get_opportunities()
                
                if not opportunities:
                    break
                
                all_opportunities.extend(opportunities)
                
                # Check if more pages available
                if len(opportunities) < 100:
                    break
                
                page += 1
            
            # Filter opportunities by date range
            filtered_opportunities = []
            for opp in all_opportunities:
                if opp.summary.post_date:
                    try:
                        post_date = datetime.fromisoformat(opp.summary.post_date.replace("Z", "+00:00"))
                        if post_date >= cutoff_date:
                            filtered_opportunities.append(opp)
                    except:
                        # Include opportunities with unparseable dates
                        filtered_opportunities.append(opp)
                else:
                    # Include opportunities without post dates (might be forecasted)
                    if include_forecasted:
                        filtered_opportunities.append(opp)
            
            logger.info(f"Analyzing {len(filtered_opportunities)} opportunities for trends (filtered from {len(all_opportunities)})")
            
            # Perform analyses
            temporal_trends = analyze_temporal_trends(filtered_opportunities, time_window_days)
            funding_patterns = identify_funding_patterns(filtered_opportunities)
            emerging_topics = detect_emerging_topics(filtered_opportunities)
            
            # Calculate metadata
            total_funding = sum(
                opp.summary.estimated_total_program_funding or 0
                for opp in filtered_opportunities
            )
            
            metadata = {
                "total_opportunities": len(filtered_opportunities),
                "opportunities_fetched": len(all_opportunities),
                "time_window_days": time_window_days,
                "total_funding": total_funding,
                "analysis_time": time.time() - start_time
            }
            
            # Generate report
            report = format_funding_trends_report(
                temporal_trends,
                funding_patterns,
                emerging_topics,
                metadata
            )
            
            # Prepare result for caching
            result = {
                "temporal_trends": temporal_trends,
                "funding_patterns": funding_patterns,
                "emerging_topics": emerging_topics,
                "metadata": metadata,
                "report": report
            }
            
            # Cache the result
            cache.set(cache_key, result)
            
            return report
            
        except APIError as e:
            logger.error(f"API error during funding trend analysis: {e}")
            return f"Error analyzing funding trends: {e}"
            
        except Exception as e:
            logger.error(f"Unexpected error during funding trend analysis: {e}", exc_info=True)
            return f"An unexpected error occurred: {e}"
    
    logger.info("Registered funding_trend_scanner tool")