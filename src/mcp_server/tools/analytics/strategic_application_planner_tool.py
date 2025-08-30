"""Strategic Application Planner tool for portfolio optimization and timeline management."""

import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from mcp_server.models.grants_schemas import OpportunityV1, GrantsAPIResponse
from mcp_server.models.analytics_schemas import StrategicRecommendation, GrantScore
from mcp_server.tools.analytics.scoring_engine import GrantScoringEngine
from mcp_server.tools.analytics.database.session_manager import AsyncSQLiteManager
from mcp_server.tools.utils.cache_manager import InMemoryCache
from mcp_server.tools.utils.cache_utils import CacheKeyGenerator

logger = logging.getLogger(__name__)


class PortfolioOptimizer:
    """Optimize grant application portfolio using strategic planning algorithms."""
    
    def __init__(self):
        pass
    
    def categorize_opportunities(
        self,
        scored_opportunities: List[GrantScore],
        user_profile: Optional[Dict] = None
    ) -> Tuple[List[str], List[str], List[str]]:
        """
        Categorize opportunities into reach, match, and safety buckets.
        
        Args:
            scored_opportunities: List of scored opportunities
            user_profile: User research profile
            
        Returns:
            Tuple of (reach_grant_ids, match_grant_ids, safety_grant_ids)
        """
        reach_grants = []
        match_grants = []
        safety_grants = []
        
        # Sort by overall score
        sorted_scores = sorted(scored_opportunities, key=lambda x: x.overall_score, reverse=True)
        
        for score in sorted_scores:
            overall = score.overall_score
            success_prob = score.success_probability.value
            competition = score.competition_index.value
            
            # Reach grants: High value but challenging (low success probability or high competition)
            if overall >= 70 and (success_prob < 25 or competition < 40):
                reach_grants.append(score.opportunity_id)
            
            # Safety grants: Good success probability and manageable competition
            elif success_prob >= 40 and competition >= 60 and overall >= 50:
                safety_grants.append(score.opportunity_id)
            
            # Match grants: Balanced profile
            else:
                match_grants.append(score.opportunity_id)
        
        return reach_grants, match_grants, safety_grants
    
    def optimize_timeline(
        self,
        opportunities: List[OpportunityV1],
        user_capacity: int = 3,
        max_concurrent: int = 2
    ) -> Dict[str, Any]:
        """
        Optimize application timeline to maximize success while respecting constraints.
        
        Args:
            opportunities: List of opportunities to schedule
            user_capacity: Maximum applications per year
            max_concurrent: Maximum concurrent applications
            
        Returns:
            Optimized timeline dictionary
        """
        timeline = {
            'recommended_sequence': [],
            'timeline_months': {},
            'workload_distribution': {},
            'risk_mitigation': []
        }
        
        # Parse deadlines and sort by date
        deadline_opportunities = []
        
        for opp in opportunities:
            close_date = opp.summary.close_date
            if close_date:
                try:
                    # Parse various date formats
                    if 'T' in close_date:
                        deadline = datetime.strptime(close_date.split('T')[0], '%Y-%m-%d')
                    else:
                        deadline = datetime.strptime(close_date, '%Y-%m-%d')
                    
                    deadline_opportunities.append((deadline, opp))
                except ValueError:
                    logger.warning(f"Could not parse deadline: {close_date}")
                    continue
        
        # Sort by deadline
        deadline_opportunities.sort(key=lambda x: x[0])
        
        # Optimize sequence with constraints
        selected_opportunities = []
        current_workload = {}
        
        for deadline, opp in deadline_opportunities:
            # Check if we can fit this opportunity
            month_key = deadline.strftime('%Y-%m')
            current_month_load = current_workload.get(month_key, 0)
            
            # Check concurrent limit
            if current_month_load < max_concurrent and len(selected_opportunities) < user_capacity:
                selected_opportunities.append(opp)
                current_workload[month_key] = current_month_load + 1
                
                timeline['recommended_sequence'].append({
                    'opportunity_id': opp.opportunity_id,
                    'title': opp.opportunity_title,
                    'deadline': deadline.isoformat(),
                    'month_slot': month_key
                })
        
        timeline['timeline_months'] = current_workload
        timeline['workload_distribution'] = self._calculate_workload_distribution(selected_opportunities)
        timeline['risk_mitigation'] = self._generate_risk_mitigation_strategies(selected_opportunities)
        
        return timeline
    
    def _calculate_workload_distribution(self, opportunities: List[OpportunityV1]) -> Dict[str, float]:
        """Calculate workload distribution across selected opportunities."""
        total_estimated_hours = 0
        distribution = {}
        
        for opp in opportunities:
            # Estimate hours based on award size (simplified)
            award_ceiling = opp.summary.award_ceiling or 100000
            
            if award_ceiling < 50000:
                hours = 40
            elif award_ceiling < 500000:
                hours = 100
            else:
                hours = 150
            
            total_estimated_hours += hours
            distribution[opp.opportunity_id] = hours
        
        # Convert to percentages
        if total_estimated_hours > 0:
            for opp_id in distribution:
                distribution[opp_id] = (distribution[opp_id] / total_estimated_hours) * 100
        
        return distribution
    
    def _generate_risk_mitigation_strategies(self, opportunities: List[OpportunityV1]) -> List[str]:
        """Generate risk mitigation strategies for the portfolio."""
        strategies = []
        
        # Check for agency concentration risk
        agencies = [opp.agency_code for opp in opportunities]
        unique_agencies = set(agencies)
        
        if len(agencies) - len(unique_agencies) > 1:
            strategies.append("Consider diversifying across more agencies to reduce concentration risk")
        
        # Check for tight deadlines
        tight_deadlines = 0
        for opp in opportunities:
            if opp.summary.close_date:
                try:
                    deadline = datetime.strptime(opp.summary.close_date.split('T')[0], '%Y-%m-%d')
                    days_until = (deadline - datetime.utcnow()).days
                    if days_until < 45:
                        tight_deadlines += 1
                except ValueError:
                    pass
        
        if tight_deadlines > 1:
            strategies.append(f"Portfolio has {tight_deadlines} tight deadlines - consider starting preparation early")
        
        # Check for collaboration opportunities
        interdisciplinary_count = sum(
            1 for opp in opportunities 
            if any(word in (opp.summary.summary_description or "").lower() 
                  for word in ['collaboration', 'partnership', 'interdisciplinary'])
        )
        
        if interdisciplinary_count > 0:
            strategies.append("Consider forming collaborations for interdisciplinary opportunities")
        
        return strategies
    
    def calculate_portfolio_metrics(
        self,
        reach_grants: List[str],
        match_grants: List[str], 
        safety_grants: List[str],
        scored_opportunities: List[GrantScore]
    ) -> Dict[str, float]:
        """Calculate portfolio-level metrics."""
        
        # Create lookup for scores
        score_lookup = {score.opportunity_id: score for score in scored_opportunities}
        
        # Calculate diversity score
        total_grants = len(reach_grants) + len(match_grants) + len(safety_grants)
        if total_grants == 0:
            return {'diversity_score': 0.0, 'expected_success_rate': 0.0}
        
        # Ideal distribution: 30% reach, 50% match, 20% safety
        ideal_reach = 0.3 * total_grants
        ideal_match = 0.5 * total_grants
        ideal_safety = 0.2 * total_grants
        
        # Calculate deviation from ideal
        reach_deviation = abs(len(reach_grants) - ideal_reach) / total_grants
        match_deviation = abs(len(match_grants) - ideal_match) / total_grants
        safety_deviation = abs(len(safety_grants) - ideal_safety) / total_grants
        
        diversity_score = 100 * (1 - (reach_deviation + match_deviation + safety_deviation) / 3)
        
        # Calculate expected success rate
        total_success_prob = 0
        grant_count = 0
        
        for grant_list in [reach_grants, match_grants, safety_grants]:
            for grant_id in grant_list:
                if grant_id in score_lookup:
                    total_success_prob += score_lookup[grant_id].success_probability.value
                    grant_count += 1
        
        expected_success_rate = total_success_prob / grant_count if grant_count > 0 else 0
        
        return {
            'diversity_score': max(0, min(100, diversity_score)),
            'expected_success_rate': expected_success_rate
        }


def format_strategic_plan(
    recommendation: StrategicRecommendation,
    scored_opportunities: List[GrantScore],
    timeline: Dict[str, Any]
) -> str:
    """
    Format strategic plan for display.
    
    Args:
        recommendation: Strategic recommendation
        scored_opportunities: List of scored opportunities  
        timeline: Timeline optimization results
        
    Returns:
        Formatted strategic plan
    """
    # Create lookup for opportunity details
    score_lookup = {score.opportunity_id: score for score in scored_opportunities}
    
    lines = [
        "STRATEGIC APPLICATION PLAN",
        "=" * 50,
        f"Generated: {recommendation.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Portfolio Diversity Score: {recommendation.portfolio_diversity_score:.1f}/100",
        f"Expected Success Rate: {recommendation.expected_success_rate:.1f}%",
        "",
        "📈 PORTFOLIO STRATEGY",
        "-" * 20
    ]
    
    # Risk assessment
    lines.extend([
        f"Risk Assessment: {recommendation.risk_assessment}",
        ""
    ])
    
    # Portfolio composition
    lines.extend([
        "🎯 REACH GRANTS (High Impact, Challenging)",
        f"   {len(recommendation.reach_grants)} opportunities - Target 1-2 awards",
        ""
    ])
    
    for i, grant_id in enumerate(recommendation.reach_grants[:3], 1):  # Show top 3
        if grant_id in score_lookup:
            score = score_lookup[grant_id]
            lines.append(f"   {i}. {score.opportunity_title}")
            lines.append(f"      Score: {score.overall_score:.1f}/100, Success Prob: {score.success_probability.value:.1f}%")
        lines.append("")
    
    lines.extend([
        "✅ MATCH GRANTS (Good Fit, Balanced Risk)",
        f"   {len(recommendation.match_grants)} opportunities - Target 2-3 awards",
        ""
    ])
    
    for i, grant_id in enumerate(recommendation.match_grants[:3], 1):
        if grant_id in score_lookup:
            score = score_lookup[grant_id]
            lines.append(f"   {i}. {score.opportunity_title}")
            lines.append(f"      Score: {score.overall_score:.1f}/100, Success Prob: {score.success_probability.value:.1f}%")
        lines.append("")
    
    lines.extend([
        "🛡️ SAFETY GRANTS (High Success Probability)",
        f"   {len(recommendation.safety_grants)} opportunities - Target 1-2 awards",
        ""
    ])
    
    for i, grant_id in enumerate(recommendation.safety_grants[:3], 1):
        if grant_id in score_lookup:
            score = score_lookup[grant_id]
            lines.append(f"   {i}. {score.opportunity_title}")
            lines.append(f"      Score: {score.overall_score:.1f}/100, Success Prob: {score.success_probability.value:.1f}%")
        lines.append("")
    
    # Timeline optimization
    lines.extend([
        "📅 TIMELINE OPTIMIZATION",
        "-" * 23
    ])
    
    if timeline.get('recommended_sequence'):
        lines.append("Recommended Application Sequence:")
        for i, item in enumerate(timeline['recommended_sequence'], 1):
            deadline_date = datetime.fromisoformat(item['deadline']).strftime('%Y-%m-%d')
            lines.append(f"   {i}. {item['title'][:50]}... (Due: {deadline_date})")
        lines.append("")
    
    # Workload distribution
    if timeline.get('workload_distribution'):
        lines.extend([
            "Workload Distribution:",
            f"   Total estimated effort across all applications",
            ""
        ])
    
    # Resource allocation
    lines.extend([
        "💰 RESOURCE ALLOCATION",
        "-" * 21
    ])
    
    total_resources = sum(recommendation.resource_allocation.values())
    for category, allocation in recommendation.resource_allocation.items():
        percentage = (allocation / total_resources * 100) if total_resources > 0 else 0
        lines.append(f"   {category.replace('_', ' ').title()}: {percentage:.1f}% of effort")
    
    lines.append("")
    
    # Collaboration opportunities
    if recommendation.collaboration_opportunities:
        lines.extend([
            "🤝 COLLABORATION OPPORTUNITIES",
            "-" * 30
        ])
        
        for collab in recommendation.collaboration_opportunities:
            lines.append(f"   • {collab.get('description', 'Collaboration opportunity')}")
        lines.append("")
    
    # Risk mitigation
    if timeline.get('risk_mitigation'):
        lines.extend([
            "⚠️ RISK MITIGATION STRATEGIES",
            "-" * 28
        ])
        
        for strategy in timeline['risk_mitigation']:
            lines.append(f"   • {strategy}")
        lines.append("")
    
    # Action items
    lines.extend([
        "✅ IMMEDIATE ACTION ITEMS",
        "-" * 25,
        "   □ Review and validate opportunity selection",
        "   □ Begin preliminary research for reach grants", 
        "   □ Identify potential collaborators",
        "   □ Create detailed timeline with milestones",
        "   □ Set up tracking system for deadlines",
        "   □ Allocate resources according to plan",
        ""
    ])
    
    # Success metrics
    lines.extend([
        "📊 SUCCESS METRICS TO TRACK",
        "-" * 26,
        "   • Application submission rate vs. plan",
        "   • Quality scores from internal review",
        "   • Time spent vs. budgeted hours",
        "   • Collaboration formation success",
        "   • Ultimate award success rate"
    ])
    
    return "\n".join(lines)


def register_strategic_application_planner_tool(mcp: Any, context: Dict[str, Any]) -> None:
    """
    Register the strategic application planner tool with the MCP server.
    
    Args:
        mcp: FastMCP instance  
        context: Server context containing cache, API client, etc.
    """
    cache: InMemoryCache = context["cache"]
    api_client = context["api_client"]
    
    # Initialize components
    db_manager = AsyncSQLiteManager("grants_analytics.db")
    scoring_engine = GrantScoringEngine(db_manager)
    portfolio_optimizer = PortfolioOptimizer()
    
    @mcp.tool
    async def strategic_application_planner(
        search_query: Optional[str] = None,
        search_filters: Optional[Dict] = None,
        user_profile: Optional[Dict] = None,
        max_applications: int = 6,
        max_concurrent: int = 2,
        planning_horizon_months: int = 12,
        include_scoring: bool = True
    ) -> str:
        """
        Create strategic grant application plan with portfolio optimization.
        
        Analyzes opportunities and creates a comprehensive strategic plan including:
        - Portfolio diversification (reach/match/safety grants)
        - Timeline optimization and workload management  
        - Resource allocation recommendations
        - Collaboration opportunity identification
        - Risk mitigation strategies
        
        Args:
            search_query: Search query to find opportunities
            search_filters: Advanced search filters
            user_profile: User research profile for personalization
            max_applications: Maximum applications to include in plan
            max_concurrent: Maximum concurrent applications
            planning_horizon_months: Planning horizon in months
            include_scoring: Whether to include detailed scoring analysis
            
        Returns:
            Comprehensive strategic application plan
        """
        try:
            start_time = time.time()
            
            await db_manager.initialize()
            
            logger.info(f"Starting strategic planning analysis: {search_query}")
            
            # Generate cache key
            cache_key = CacheKeyGenerator.generate_simple(
                "strategic_planning",
                query=search_query,
                filters=search_filters,
                max_apps=max_applications,
                horizon=planning_horizon_months
            )
            
            # Check cache
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
                
                # Use larger search for strategic planning
                pagination_params = {
                    "page_size": min(max_applications * 3, 100),  # Get more options for optimization
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
                }, ttl=3600)  # 1 hour cache for strategic planning
            
            if not opportunities:
                return "No opportunities found for strategic planning. Please adjust your search criteria."
            
            logger.info(f"Found {len(opportunities)} opportunities for strategic planning")
            
            # Score opportunities if requested
            scored_opportunities = []
            if include_scoring:
                session_id = str(uuid.uuid4())
                
                await db_manager.create_search_session(
                    session_id,
                    search_query or "Strategic planning analysis",
                    search_filters or {},
                    user_profile
                )
                
                batch_result = await scoring_engine.batch_score_opportunities(
                    opportunities[:max_applications * 2],  # Score more than we need for selection
                    user_profile,
                    None,  # Use default weights
                    False,  # Skip hidden opportunity analysis for planning
                    session_id
                )
                
                scored_opportunities = batch_result.scores
                
                # Filter to top opportunities for planning
                scored_opportunities.sort(key=lambda x: x.overall_score, reverse=True)
                scored_opportunities = scored_opportunities[:max_applications]
            
            else:
                # Create minimal scores for planning (simplified)
                for opp in opportunities[:max_applications]:
                    # Would create simplified GrantScore objects here
                    pass
            
            # Portfolio optimization
            reach_grants, match_grants, safety_grants = portfolio_optimizer.categorize_opportunities(
                scored_opportunities, user_profile
            )
            
            # Timeline optimization
            selected_opportunities = [
                opp for opp in opportunities 
                if opp.opportunity_id in (reach_grants + match_grants + safety_grants)
            ]
            
            timeline = portfolio_optimizer.optimize_timeline(
                selected_opportunities, max_applications, max_concurrent
            )
            
            # Calculate portfolio metrics
            portfolio_metrics = portfolio_optimizer.calculate_portfolio_metrics(
                reach_grants, match_grants, safety_grants, scored_opportunities
            )
            
            # Generate collaboration opportunities (simplified)
            collaboration_opportunities = []
            interdisciplinary_grants = [
                opp for opp in selected_opportunities
                if any(word in (opp.summary.summary_description or "").lower() 
                      for word in ['collaboration', 'partnership', 'interdisciplinary'])
            ]
            
            if interdisciplinary_grants:
                collaboration_opportunities.append({
                    'description': f'Consider partnerships for {len(interdisciplinary_grants)} interdisciplinary opportunities'
                })
            
            # Generate resource allocation (simplified)
            total_grants = len(reach_grants) + len(match_grants) + len(safety_grants)
            resource_allocation = {
                'reach_grants': len(reach_grants) / total_grants * 100 if total_grants > 0 else 0,
                'match_grants': len(match_grants) / total_grants * 100 if total_grants > 0 else 0,
                'safety_grants': len(safety_grants) / total_grants * 100 if total_grants > 0 else 0
            }
            
            # Assess overall risk
            if portfolio_metrics['diversity_score'] > 70:
                risk_assessment = "Low Risk - Well-diversified portfolio"
            elif portfolio_metrics['diversity_score'] > 50:
                risk_assessment = "Moderate Risk - Reasonable diversification"
            else:
                risk_assessment = "High Risk - Consider more diversification"
            
            # Create strategic recommendation
            recommendation = StrategicRecommendation(
                reach_grants=reach_grants,
                match_grants=match_grants,
                safety_grants=safety_grants,
                optimal_timeline=timeline,
                resource_allocation=resource_allocation,
                collaboration_opportunities=collaboration_opportunities,
                portfolio_diversity_score=portfolio_metrics['diversity_score'],
                expected_success_rate=portfolio_metrics['expected_success_rate'],
                risk_assessment=risk_assessment
            )
            
            # Format and return results
            result = format_strategic_plan(recommendation, scored_opportunities, timeline)
            
            planning_time = time.time() - start_time
            result += f"\n\n📊 PLANNING SUMMARY"
            result += f"\n" + "=" * 17
            result += f"\nOpportunities Analyzed: {len(opportunities)}"
            result += f"\nSelected for Portfolio: {total_grants}"
            result += f"\nPlanning Time: {planning_time:.1f}s"
            result += f"\nPlanning Horizon: {planning_horizon_months} months"
            
            logger.info(f"Strategic planning completed in {planning_time:.1f}s")
            return result
            
        except Exception as e:
            logger.error(f"Error in strategic application planner: {e}", exc_info=True)
            return f"Error creating strategic plan: {str(e)}"
    
    @mcp.tool
    async def optimize_portfolio(
        opportunity_ids: List[str],
        user_constraints: Optional[Dict] = None
    ) -> str:
        """
        Optimize a specific set of opportunities into a strategic portfolio.
        
        Args:
            opportunity_ids: List of specific opportunity IDs to optimize
            user_constraints: User constraints (max_applications, etc.)
            
        Returns:
            Optimized portfolio plan
        """
        try:
            # This would implement portfolio optimization for specific opportunities
            # For now, return a placeholder message
            return f"""
PORTFOLIO OPTIMIZATION (PLACEHOLDER)
====================================

This tool would optimize the following {len(opportunity_ids)} specific opportunities:
{', '.join(opportunity_ids[:3])}{'...' if len(opportunity_ids) > 3 else ''}

Features to implement:
• Mathematical optimization using linear programming
• Constraint satisfaction for user limits
• Risk-return optimization
• Timeline conflict resolution
• Resource allocation optimization

Use strategic_application_planner for full functionality.
"""
            
        except Exception as e:
            logger.error(f"Error in portfolio optimization: {e}")
            return f"Error optimizing portfolio: {str(e)}"
    
    logger.info("Registered strategic_application_planner and optimize_portfolio tools")