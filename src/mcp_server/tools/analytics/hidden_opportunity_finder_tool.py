"""Hidden Opportunity Finder tool for discovering undersubscribed grants."""

import logging
import time
import uuid
from typing import Any, Dict, List, Optional
import numpy as np

from mcp_server.models.grants_schemas import OpportunityV1, GrantsAPIResponse
from mcp_server.models.analytics_schemas import HiddenOpportunityScore
from mcp_server.tools.analytics.metrics.hidden_metrics import HiddenOpportunityCalculator
from mcp_server.tools.analytics.database.session_manager import AsyncSQLiteManager
from mcp_server.tools.utils.cache_manager import InMemoryCache
from mcp_server.tools.utils.cache_utils import CacheKeyGenerator

logger = logging.getLogger(__name__)


def format_hidden_opportunities_report(
    hidden_opportunities: List[HiddenOpportunityScore],
    search_query: Optional[str] = None,
    analysis_stats: Optional[Dict] = None
) -> str:
    """
    Format hidden opportunities for display.
    
    Args:
        hidden_opportunities: List of HiddenOpportunityScore objects
        search_query: Original search query
        analysis_stats: Analysis statistics
        
    Returns:
        Formatted report string
    """
    if not hidden_opportunities:
        return "No hidden opportunities detected in the current search results."
    
    lines = [
        "HIDDEN OPPORTUNITY ANALYSIS REPORT",
        "=" * 50,
        ""
    ]
    
    if search_query:
        lines.append(f"Search Context: {search_query}")
        lines.append("")
    
    lines.extend([
        f"🔍 DISCOVERED {len(hidden_opportunities)} HIDDEN OPPORTUNITIES",
        "These grants may have reduced competition due to visibility, timing, or specialization factors.",
        ""
    ])
    
    # Group by opportunity type for better organization
    by_type = {}
    for opp in hidden_opportunities:
        opp_type = opp.opportunity_type
        if opp_type not in by_type:
            by_type[opp_type] = []
        by_type[opp_type].append(opp)
    
    # Display by category
    for opp_type, opps in by_type.items():
        lines.extend([
            f"\n📂 {opp_type.upper()} ({len(opps)} opportunities)",
            "-" * (len(opp_type) + 20)
        ])
        
        # Sort by hidden opportunity score (descending)
        opps.sort(key=lambda x: x.hidden_opportunity_score, reverse=True)
        
        for i, opp in enumerate(opps, 1):
            lines.extend([
                f"\n{i}. {opp.opportunity_title}",
                f"   Hidden Opportunity Score: {opp.hidden_opportunity_score:.1f}/100",
                f"   💡 Discovery Insight: {opp.discovery_reason}",
                ""
            ])
            
            # Add component breakdown for top opportunities
            if i <= 2:  # Show details for top 2 in each category
                lines.extend([
                    "   📊 COMPONENT ANALYSIS:",
                    f"   • Visibility Factor: {opp.visibility_index.value:.1f}/100 - {opp.visibility_index.interpretation}",
                    f"   • Undersubscription: {opp.undersubscription_score.value:.1f}/100 - {opp.undersubscription_score.interpretation}",
                    f"   • Cross-Category: {opp.cross_category_score.value:.1f}/100 - {opp.cross_category_score.interpretation}",
                    ""
                ])
    
    # Add strategic insights
    lines.extend([
        "\n🎯 STRATEGIC INSIGHTS",
        "-" * 20
    ])
    
    # Calculate insights
    avg_hidden_score = np.mean([opp.hidden_opportunity_score for opp in hidden_opportunities])
    high_potential = [opp for opp in hidden_opportunities if opp.hidden_opportunity_score > 70]
    interdisciplinary = [opp for opp in hidden_opportunities if 'interdisciplinary' in opp.opportunity_type.lower()]
    
    lines.extend([
        f"• Average Hidden Opportunity Score: {avg_hidden_score:.1f}/100",
        f"• High Potential Opportunities (>70): {len(high_potential)}",
        f"• Interdisciplinary Opportunities: {len(interdisciplinary)}",
        ""
    ])
    
    # Strategic recommendations
    lines.extend([
        "💡 STRATEGIC RECOMMENDATIONS:",
        ""
    ])
    
    if high_potential:
        lines.append(f"• Prioritize the {len(high_potential)} high-potential opportunities (>70 score)")
    
    if interdisciplinary:
        lines.append("• Consider interdisciplinary opportunities - they often have specialized requirements that limit competition")
    
    # Timing recommendations
    tight_deadline_opps = []
    for opp in hidden_opportunities:
        if 'tight deadline' in opp.discovery_reason.lower():
            tight_deadline_opps.append(opp)
    
    if tight_deadline_opps:
        lines.append(f"• {len(tight_deadline_opps)} opportunities have tight deadlines creating timing advantages")
    
    # Agency diversity
    agencies = set()
    for opp in hidden_opportunities:
        # Extract agency from opportunity_id or title (simplified)
        agencies.add("Various")  # Would extract actual agency info
    
    lines.extend([
        f"• Opportunities span multiple agencies for portfolio diversification",
        "",
        "⚠️  IMPORTANT NOTES:",
        "• 'Hidden' doesn't mean easy - still requires competitive applications",
        "• Lower visibility may indicate specialized requirements",
        "• Verify eligibility carefully for cross-category opportunities",
        "• Consider collaboration for interdisciplinary grants"
    ])
    
    return "\n".join(lines)


def format_detailed_hidden_analysis(hidden_opp: HiddenOpportunityScore) -> str:
    """
    Format detailed analysis for a single hidden opportunity.
    
    Args:
        hidden_opp: HiddenOpportunityScore to format
        
    Returns:
        Detailed formatted string
    """
    lines = [
        f"DETAILED HIDDEN OPPORTUNITY ANALYSIS",
        "=" * 60,
        f"Opportunity: {hidden_opp.opportunity_title}",
        f"ID: {hidden_opp.opportunity_id}",
        f"Overall Hidden Score: {hidden_opp.hidden_opportunity_score:.1f}/100",
        f"Opportunity Type: {hidden_opp.opportunity_type}",
        f"Analysis Date: {hidden_opp.calculated_at.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "🔍 DISCOVERY ANALYSIS",
        "-" * 20,
        hidden_opp.discovery_reason,
        ""
    ]
    
    # Visibility Analysis
    lines.extend([
        "👁️  VISIBILITY ANALYSIS",
        "-" * 21,
        f"Visibility Score: {hidden_opp.visibility_index.value:.1f}/100",
        f"Calculation: {hidden_opp.visibility_index.calculation}",
        f"Interpretation: {hidden_opp.visibility_index.interpretation}",
        ""
    ])
    
    if hidden_opp.visibility_index.components:
        lines.append("Components:")
        for key, value in hidden_opp.visibility_index.components.items():
            lines.append(f"  • {key.replace('_', ' ').title()}: {value}")
        lines.append("")
    
    # Undersubscription Analysis
    lines.extend([
        "📉 UNDERSUBSCRIPTION ANALYSIS",
        "-" * 29,
        f"Undersubscription Score: {hidden_opp.undersubscription_score.value:.1f}/100",
        f"Calculation: {hidden_opp.undersubscription_score.calculation}",
        f"Interpretation: {hidden_opp.undersubscription_score.interpretation}",
        ""
    ])
    
    if hidden_opp.undersubscription_score.components:
        lines.append("Components:")
        for key, value in hidden_opp.undersubscription_score.components.items():
            lines.append(f"  • {key.replace('_', ' ').title()}: {value}")
        lines.append("")
    
    # Cross-Category Analysis
    lines.extend([
        "🔄 CROSS-CATEGORY ANALYSIS",
        "-" * 26,
        f"Cross-Category Score: {hidden_opp.cross_category_score.value:.1f}/100",
        f"Calculation: {hidden_opp.cross_category_score.calculation}",
        f"Interpretation: {hidden_opp.cross_category_score.interpretation}",
        ""
    ])
    
    if hidden_opp.cross_category_score.components:
        lines.append("Components:")
        for key, value in hidden_opp.cross_category_score.components.items():
            lines.append(f"  • {key.replace('_', ' ').title()}: {value}")
        lines.append("")
    
    # Strategic Recommendations
    lines.extend([
        "💡 STRATEGIC RECOMMENDATIONS",
        "-" * 28,
        ""
    ])
    
    if hidden_opp.hidden_opportunity_score > 80:
        lines.append("🎯 HIGH PRIORITY - Excellent hidden opportunity with multiple advantage factors")
    elif hidden_opp.hidden_opportunity_score > 60:
        lines.append("✅ RECOMMENDED - Strong hidden opportunity worth investigating")
    elif hidden_opp.hidden_opportunity_score > 40:
        lines.append("⚠️ MODERATE - Some hidden opportunity factors, consider if aligned with goals")
    else:
        lines.append("ℹ️ LOW PRIORITY - Limited hidden opportunity advantages")
    
    # Specific recommendations based on type
    if "interdisciplinary" in hidden_opp.opportunity_type.lower():
        lines.append("• Consider forming interdisciplinary team to leverage cross-field expertise")
    
    if "undersubscribed" in hidden_opp.opportunity_type.lower():
        lines.append("• Focus on meeting basic requirements rather than exceptional innovation")
    
    if "low visibility" in hidden_opp.opportunity_type.lower():
        lines.append("• Investigate requirements carefully as they may be specialized")
    
    lines.extend([
        "",
        "⚠️ VALIDATION CHECKLIST:",
        "□ Verify eligibility requirements carefully",
        "□ Assess technical/resource requirements",
        "□ Check for hidden compliance requirements", 
        "□ Consider collaboration opportunities",
        "□ Evaluate timing against other opportunities"
    ])
    
    return "\n".join(lines)


def register_hidden_opportunity_finder_tool(mcp: Any, context: Dict[str, Any]) -> None:
    """
    Register the hidden opportunity finder tool with the MCP server.
    
    Args:
        mcp: FastMCP instance
        context: Server context containing cache, API client, etc.
    """
    cache: InMemoryCache = context["cache"]
    api_client = context["api_client"]
    
    # Initialize components
    db_manager = AsyncSQLiteManager("grants_analytics.db")
    hidden_calculator = HiddenOpportunityCalculator()
    
    @mcp.tool
    async def hidden_opportunity_finder(
        search_query: Optional[str] = None,
        search_filters: Optional[Dict] = None,
        user_profile: Optional[Dict] = None,
        min_hidden_score: float = 40.0,
        max_results: int = 100,
        detailed_analysis: bool = False
    ) -> str:
        """
        Discover potentially undersubscribed grant opportunities.
        
        Uses advanced analysis to identify grants that may have reduced competition due to:
        - Low visibility/discoverability
        - Specialized or technical requirements
        - Cross-disciplinary nature
        - Timing factors
        - Agency-specific patterns
        
        Args:
            search_query: Search query to find opportunities
            search_filters: Advanced search filters
            user_profile: User research profile for personalized analysis
            min_hidden_score: Minimum hidden opportunity score threshold (0-100)
            max_results: Maximum opportunities to analyze
            detailed_analysis: Include detailed breakdown for top opportunities
            
        Returns:
            Report of hidden opportunities with strategic insights
        """
        try:
            start_time = time.time()
            
            await db_manager.initialize()
            
            logger.info(f"Starting hidden opportunity analysis: {search_query}")
            
            # Generate cache key
            cache_key = CacheKeyGenerator.generate_simple(
                "hidden_opportunity_search",
                query=search_query,
                filters=search_filters,
                min_score=min_hidden_score,
                max_results=max_results
            )
            
            # Check cache first
            cached_result = cache.get(cache_key)
            if cached_result:
                opportunities = cached_result["opportunities"]
                logger.info(f"Using cached search results: {len(opportunities)} opportunities")
            else:
                # Search for opportunities
                search_filters_api = search_filters or {}
                
                # Default to current and forecasted opportunities
                if "opportunity_status" not in search_filters_api:
                    search_filters_api["opportunity_status"] = {
                        "one_of": ["posted", "forecasted"]
                    }
                
                # Use larger page size for hidden opportunity analysis
                pagination_params = {
                    "page_size": min(max_results, 100),
                    "page_offset": 1,
                    "order_by": "opportunity_id",
                    "sort_direction": "descending"
                }
                
                response_data = await api_client.search_opportunities(
                    query=search_query,
                    filters=search_filters_api,
                    pagination=pagination_params
                )
                
                api_response = GrantsAPIResponse(**response_data)
                opportunities = api_response.get_opportunities()
                
                # Cache the results
                cache.set(cache_key, {
                    "opportunities": opportunities,
                    "total_found": api_response.pagination_info.total_records,
                    "search_time": time.time() - start_time
                }, ttl=1800)  # 30 minute cache for hidden opportunity analysis
            
            if not opportunities:
                return "No opportunities found to analyze. Please adjust your search criteria."
            
            logger.info(f"Analyzing {len(opportunities)} opportunities for hidden potential")
            
            # Analyze each opportunity for hidden potential
            hidden_opportunities = []
            
            for i, opportunity in enumerate(opportunities):
                try:
                    search_context = {
                        'search_position': i + 1,
                        'total_results': len(opportunities)
                    }
                    
                    hidden_score = hidden_calculator.calculate_hidden_opportunity_score(
                        opportunity, user_profile, search_context
                    )
                    
                    # Only include if above threshold
                    if hidden_score.hidden_opportunity_score >= min_hidden_score:
                        hidden_opportunities.append(hidden_score)
                    
                except Exception as e:
                    logger.error(f"Error analyzing opportunity {opportunity.opportunity_id}: {e}")
                    continue
            
            # Store results in database
            for hidden_opp in hidden_opportunities:
                await db_manager.store_hidden_opportunity(
                    hidden_opp.opportunity_id,
                    hidden_opp.opportunity_title,
                    hidden_opp.hidden_opportunity_score,
                    {
                        'visibility_index': hidden_opp.visibility_index.value,
                        'undersubscription_score': hidden_opp.undersubscription_score.value,
                        'cross_category_score': hidden_opp.cross_category_score.value
                    },
                    hidden_opp.opportunity_type,
                    hidden_opp.discovery_reason
                )
            
            # Sort by hidden opportunity score
            hidden_opportunities.sort(key=lambda x: x.hidden_opportunity_score, reverse=True)
            
            analysis_time = time.time() - start_time
            
            analysis_stats = {
                'total_analyzed': len(opportunities),
                'hidden_found': len(hidden_opportunities),
                'analysis_time_ms': analysis_time * 1000,
                'min_threshold': min_hidden_score
            }
            
            # Format results
            if detailed_analysis and hidden_opportunities:
                # Show detailed analysis for top opportunity
                result = format_detailed_hidden_analysis(hidden_opportunities[0])
                
                if len(hidden_opportunities) > 1:
                    result += "\n\n" + "=" * 80 + "\n\n"
                    result += format_hidden_opportunities_report(
                        hidden_opportunities[1:], search_query, analysis_stats
                    )
            else:
                result = format_hidden_opportunities_report(
                    hidden_opportunities, search_query, analysis_stats
                )
            
            # Add performance summary
            result += f"\n\n📊 ANALYSIS SUMMARY"
            result += f"\n" + "=" * 18
            result += f"\n• Opportunities Analyzed: {analysis_stats['total_analyzed']}"
            result += f"\n• Hidden Opportunities Found: {analysis_stats['hidden_found']}"
            result += f"\n• Analysis Time: {analysis_stats['analysis_time_ms']:.0f}ms"
            result += f"\n• Detection Threshold: {min_hidden_score}/100"
            
            logger.info(f"Hidden opportunity analysis completed: found {len(hidden_opportunities)} opportunities")
            return result
            
        except Exception as e:
            logger.error(f"Error in hidden opportunity finder: {e}", exc_info=True)
            return f"Error analyzing hidden opportunities: {str(e)}"
    
    @mcp.tool
    async def get_top_hidden_opportunities(
        limit: int = 10,
        days_back: int = 7
    ) -> str:
        """
        Get top hidden opportunities from recent analysis.
        
        Args:
            limit: Maximum number of opportunities to return
            days_back: Days of history to include
            
        Returns:
            List of top hidden opportunities from database
        """
        try:
            await db_manager.initialize()
            
            top_opportunities = await db_manager.get_top_hidden_opportunities(limit)
            
            if not top_opportunities:
                return "No hidden opportunities in database. Run hidden_opportunity_finder first."
            
            lines = [
                "TOP HIDDEN OPPORTUNITIES (FROM DATABASE)",
                "=" * 45,
                f"Showing top {len(top_opportunities)} opportunities from recent analyses",
                ""
            ]
            
            for i, opp in enumerate(top_opportunities, 1):
                lines.extend([
                    f"{i}. {opp['opportunity_title']}",
                    f"   Hidden Score: {opp['hidden_score']:.1f}/100",
                    f"   Type: {opp['opportunity_type']}",
                    f"   Discovered: {opp['calculated_at']}",
                    f"   Reason: {opp['discovery_reason']}",
                    ""
                ])
            
            lines.extend([
                "💡 Use hidden_opportunity_finder for fresh analysis",
                "📊 Use explain_grant_score for detailed scoring breakdown"
            ])
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Error getting top hidden opportunities: {e}")
            return f"Error retrieving opportunities: {str(e)}"
    
    logger.info("Registered hidden_opportunity_finder and get_top_hidden_opportunities tools")