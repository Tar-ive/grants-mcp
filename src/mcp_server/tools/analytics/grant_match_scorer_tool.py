"""Grant Match Scorer tool for intelligent grant scoring and recommendation."""

import logging
import time
import json
import uuid
from typing import Any, Dict, List, Optional

from mcp_server.models.grants_schemas import OpportunityV1, GrantsAPIResponse
from mcp_server.models.analytics_schemas import ScoreCalculationRequest, BatchScoreResult
from mcp_server.tools.analytics.scoring_engine import GrantScoringEngine
from mcp_server.tools.analytics.database.session_manager import AsyncSQLiteManager
from mcp_server.tools.utils.cache_manager import InMemoryCache
from mcp_server.tools.utils.cache_utils import CacheKeyGenerator

logger = logging.getLogger(__name__)


def format_score_summary(scores: List['GrantScore']) -> str:
    """
    Format grant scores for display.
    
    Args:
        scores: List of GrantScore objects
        
    Returns:
        Formatted summary string
    """
    if not scores:
        return "No opportunities scored."
    
    summary_lines = [
        "GRANT MATCH SCORING RESULTS",
        "=" * 50,
        f"Total Opportunities Analyzed: {len(scores)}",
        ""
    ]
    
    # Top opportunities
    top_scores = sorted(scores, key=lambda x: x.overall_score, reverse=True)[:5]
    
    summary_lines.extend([
        "TOP RECOMMENDED OPPORTUNITIES",
        "-" * 30
    ])
    
    for i, score in enumerate(top_scores, 1):
        summary_lines.append(f"\n{i}. {score.opportunity_title}")
        summary_lines.append(f"   Overall Score: {score.overall_score:.1f}/100")
        summary_lines.append(f"   Competition: {score.competition_index.value:.1f}/100 ({score.competition_index.interpretation})")
        summary_lines.append(f"   Success Probability: {score.success_probability.value:.1f}% ({score.success_probability.interpretation})")
        summary_lines.append(f"   ROI Score: {score.roi_score.value:.1f}/100 ({score.roi_score.interpretation})")
        summary_lines.append(f"   Timing: {score.timing_score.value:.1f}/100 ({score.timing_score.interpretation})")
        summary_lines.append(f"   📋 Recommendation: {score.recommendation}")
    
    # Score distribution summary
    scores_values = [s.overall_score for s in scores]
    avg_score = sum(scores_values) / len(scores_values)
    high_priority = len([s for s in scores if s.overall_score >= 80])
    recommended = len([s for s in scores if 60 <= s.overall_score < 80])
    conditional = len([s for s in scores if 40 <= s.overall_score < 60])
    not_recommended = len([s for s in scores if s.overall_score < 40])
    
    summary_lines.extend([
        "",
        "SCORE DISTRIBUTION ANALYSIS",
        "-" * 30,
        f"Average Score: {avg_score:.1f}/100",
        f"🎯 High Priority (80+): {high_priority} opportunities",
        f"✅ Recommended (60-79): {recommended} opportunities", 
        f"⚠️ Conditional (40-59): {conditional} opportunities",
        f"❌ Not Recommended (<40): {not_recommended} opportunities",
        "",
        "METHODOLOGY NOTES",
        "-" * 17,
        "• Competition Index based on NIH/NSF methodologies",
        "• Success Probability includes technical fit and eligibility",
        "• ROI calculated with effort-adjusted and risk factors",
        "• Timing considers preparation adequacy and deadline competition",
        "• All calculations include transparent component breakdowns",
        "",
        "💡 TIP: Use detailed view for specific opportunities to see full calculation breakdowns"
    ])
    
    return "\n".join(summary_lines)


def format_detailed_score(score: 'GrantScore') -> str:
    """
    Format a detailed individual score breakdown.
    
    Args:
        score: GrantScore to format
        
    Returns:
        Detailed formatted string
    """
    lines = [
        f"DETAILED ANALYSIS: {score.opportunity_title}",
        "=" * 80,
        f"Overall Score: {score.overall_score:.1f}/100",
        f"Opportunity ID: {score.opportunity_id}",
        f"Analysis Date: {score.calculated_at.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "COMPONENT BREAKDOWN",
        "-" * 20
    ]
    
    # Technical Fit
    lines.extend([
        f"🔬 TECHNICAL FIT: {score.technical_fit_score.value:.1f}/100",
        f"   Calculation: {score.technical_fit_score.calculation}",
        f"   Interpretation: {score.technical_fit_score.interpretation}",
        ""
    ])
    
    # Competition Index
    lines.extend([
        f"🏆 COMPETITION INDEX: {score.competition_index.value:.1f}/100",
        f"   Calculation: {score.competition_index.calculation}",
        f"   Components: {json.dumps(score.competition_index.components, indent=6)}",
        f"   Interpretation: {score.competition_index.interpretation}",
        f"   Industry Benchmark: {score.competition_index.industry_benchmark or 'N/A'}",
        ""
    ])
    
    # Success Probability
    lines.extend([
        f"📈 SUCCESS PROBABILITY: {score.success_probability.value:.1f}%",
        f"   Calculation: {score.success_probability.calculation}",
        f"   Components: {json.dumps(score.success_probability.components, indent=6)}",
        f"   Interpretation: {score.success_probability.interpretation}",
        f"   Industry Benchmark: {score.success_probability.industry_benchmark or 'N/A'}",
        ""
    ])
    
    # ROI Score
    lines.extend([
        f"💰 ROI SCORE: {score.roi_score.value:.1f}/100",
        f"   Calculation: {score.roi_score.calculation}",
        f"   Components: {json.dumps(score.roi_score.components, indent=6)}",
        f"   Interpretation: {score.roi_score.interpretation}",
        f"   Industry Benchmark: {score.roi_score.industry_benchmark or 'N/A'}",
        ""
    ])
    
    # Timing Score
    lines.extend([
        f"⏰ TIMING SCORE: {score.timing_score.value:.1f}/100",
        f"   Calculation: {score.timing_score.calculation}",
        f"   Components: {json.dumps(score.timing_score.components, indent=6)}",
        f"   Interpretation: {score.timing_score.interpretation}",
        f"   Industry Benchmark: {score.timing_score.industry_benchmark or 'N/A'}",
        ""
    ])
    
    # Strategic Recommendation
    lines.extend([
        "STRATEGIC RECOMMENDATION",
        "-" * 25,
        score.recommendation,
        "",
        "TRANSPARENCY NOTES",
        "-" * 17,
        "• All scores use industry-standard methodologies (NIH, NSF)",
        "• Component calculations are fully transparent and auditable",
        "• Weights can be customized based on user preferences",
        "• Historical data improves accuracy over time"
    ])
    
    return "\n".join(lines)


def register_grant_match_scorer_tool(mcp: Any, context: Dict[str, Any]) -> None:
    """
    Register the grant match scorer tool with the MCP server.
    
    Args:
        mcp: FastMCP instance
        context: Server context containing cache, API client, etc.
    """
    cache: InMemoryCache = context["cache"]
    api_client = context["api_client"]
    
    # Initialize database manager
    db_manager = AsyncSQLiteManager("grants_analytics.db")
    
    # Initialize scoring engine
    scoring_engine = GrantScoringEngine(db_manager)
    
    @mcp.tool
    async def grant_match_scorer(
        opportunity_ids: Optional[List[str]] = None,
        search_query: Optional[str] = None,
        search_filters: Optional[Dict] = None,
        user_profile: Optional[Dict] = None,
        scoring_weights: Optional[Dict[str, float]] = None,
        max_results: int = 50,
        detailed_view: bool = False,
        include_hidden: bool = True
    ) -> str:
        """
        Intelligent grant scoring system with multi-dimensional analysis.
        
        Evaluates grant opportunities across five key dimensions:
        - Technical Fit: Alignment with research interests/expertise
        - Competition Index: Using NIH/NSF methodologies
        - Success Probability: Likelihood of winning based on multiple factors
        - ROI Score: Return on investment considering effort and risk
        - Timing Score: Preparation adequacy and deadline competition
        
        Args:
            opportunity_ids: Specific opportunity IDs to score (optional)
            search_query: Search for opportunities to score (optional)
            search_filters: Advanced search filters (optional)
            user_profile: Research profile for personalized scoring
            scoring_weights: Custom weights for scoring dimensions
            max_results: Maximum opportunities to analyze (default: 50)
            detailed_view: Show detailed breakdowns (default: False)
            include_hidden: Include hidden opportunity analysis (default: True)
            
        Returns:
            Comprehensive scoring analysis with transparent calculations
        """
        try:
            start_time = time.time()
            
            # Initialize database
            await db_manager.initialize()
            
            # Create session ID for tracking
            session_id = str(uuid.uuid4())
            
            opportunities = []
            
            # Get opportunities to score
            if opportunity_ids:
                # Score specific opportunities (would need to fetch details)
                logger.info(f"Scoring specific opportunities: {opportunity_ids}")
                # For now, return message about needing opportunity details
                return "Scoring specific opportunity IDs requires additional implementation to fetch opportunity details."
                
            else:
                # Search for opportunities to score
                logger.info(f"Searching and scoring opportunities: {search_query}")
                
                # Generate cache key
                cache_key = CacheKeyGenerator.generate_simple(
                    "grant_scorer_search",
                    query=search_query,
                    filters=search_filters,
                    max_results=max_results
                )
                
                # Check cache
                cached_result = cache.get(cache_key)
                if cached_result:
                    opportunities = cached_result["opportunities"]
                    logger.info(f"Using cached search results: {len(opportunities)} opportunities")
                else:
                    # Make API search
                    search_filters_api = search_filters or {}
                    
                    # Default to current and forecasted opportunities
                    if "opportunity_status" not in search_filters_api:
                        search_filters_api["opportunity_status"] = {
                            "one_of": ["posted", "forecasted"]
                        }
                    
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
                    })
            
            if not opportunities:
                return "No opportunities found to score. Please adjust your search criteria."
            
            # Create search session in database
            await db_manager.create_search_session(
                session_id,
                search_query or "Direct opportunity scoring",
                search_filters or {},
                user_profile
            )
            
            # Batch score all opportunities
            logger.info(f"Starting batch scoring of {len(opportunities)} opportunities")
            
            batch_result = await scoring_engine.batch_score_opportunities(
                opportunities[:max_results],  # Limit to max_results
                user_profile,
                scoring_weights,
                include_hidden,
                session_id
            )
            
            # Store hidden opportunities in database
            for hidden_opp in batch_result.hidden_opportunities:
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
            
            # Format results
            if detailed_view and batch_result.scores:
                # Show detailed breakdown for top opportunity
                top_score = batch_result.scores[0]
                result = format_detailed_score(top_score)
                
                # Add summary for other opportunities
                if len(batch_result.scores) > 1:
                    result += "\n\n" + "=" * 80 + "\n\n"
                    result += format_score_summary(batch_result.scores[1:])
                    
            else:
                # Show summary for all opportunities
                result = format_score_summary(batch_result.scores)
            
            # Add hidden opportunities section
            if include_hidden and batch_result.hidden_opportunities:
                result += "\n\n"
                result += "HIDDEN OPPORTUNITIES DETECTED"
                result += "\n" + "=" * 33 + "\n"
                result += f"Found {len(batch_result.hidden_opportunities)} potentially undersubscribed opportunities:\n"
                
                for i, hidden in enumerate(batch_result.hidden_opportunities[:3], 1):  # Show top 3
                    result += f"\n{i}. {hidden.opportunity_title}"
                    result += f"\n   Hidden Score: {hidden.hidden_opportunity_score:.1f}/100"
                    result += f"\n   Type: {hidden.opportunity_type}"
                    result += f"\n   Reason: {hidden.discovery_reason}"
            
            # Add performance metrics
            result += "\n\n"
            result += "ANALYSIS PERFORMANCE"
            result += "\n" + "-" * 20 + "\n"
            result += f"Total Opportunities Analyzed: {batch_result.total_opportunities}"
            result += f"\nScoring Time: {batch_result.scoring_time_ms:.0f}ms"
            result += f"\nAnalysis Method: Multi-dimensional scoring with NIH/NSF methodologies"
            result += f"\nSession ID: {session_id} (for reference)"
            
            logger.info(f"Grant match scoring completed for session {session_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error in grant match scorer: {e}", exc_info=True)
            return f"Error analyzing opportunities: {str(e)}"
    
    # Additional tool for explaining specific scores
    @mcp.tool
    async def explain_grant_score(
        opportunity_id: str
    ) -> str:
        """
        Get detailed explanation of how a grant opportunity was scored.
        
        Args:
            opportunity_id: ID of the opportunity to explain
            
        Returns:
            Detailed scoring explanation with calculation breakdowns
        """
        try:
            await db_manager.initialize()
            
            explanation = await scoring_engine.get_scoring_explanation(opportunity_id)
            
            if not explanation:
                return f"No scoring data found for opportunity ID: {opportunity_id}. Run grant_match_scorer first."
            
            lines = [
                f"SCORING EXPLANATION FOR: {opportunity_id}",
                "=" * 60,
                f"Overall Score: {explanation['overall_score']:.1f}/100",
                f"Calculated: {explanation['calculated_at']}",
                "",
                "COMPONENT SCORES:",
                f"• Technical Fit: {explanation['component_scores']['technical_fit']:.1f}/100",
                f"• Competition Index: {explanation['component_scores']['competition']:.1f}/100", 
                f"• ROI Score: {explanation['component_scores']['roi']:.1f}/100",
                f"• Timing Score: {explanation['component_scores']['timing']:.1f}/100",
                f"• Success Probability: {explanation['component_scores']['success_probability']:.1f}%",
                "",
                "RECOMMENDATION:",
                explanation['recommendation'],
                "",
                "DETAILED CALCULATIONS:",
                json.dumps(explanation['calculation_details'], indent=2) if explanation['calculation_details'] else "See full analysis for calculation details"
            ]
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Error explaining grant score: {e}")
            return f"Error retrieving explanation: {str(e)}"
    
    logger.info("Registered grant_match_scorer and explain_grant_score tools")