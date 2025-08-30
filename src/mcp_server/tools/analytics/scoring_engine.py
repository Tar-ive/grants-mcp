"""Main scoring engine that orchestrates all grant scoring metrics."""

import logging
import time
from typing import Dict, List, Optional, Any
import numpy as np

from mcp_server.models.grants_schemas import OpportunityV1
from mcp_server.models.analytics_schemas import (
    GrantScore, HiddenOpportunityScore, BatchScoreResult, 
    ScoreCalculationRequest, IndustryConstants
)
from mcp_server.tools.analytics.metrics.competition_metrics import CompetitionIndexCalculator
from mcp_server.tools.analytics.metrics.success_metrics import SuccessProbabilityCalculator
from mcp_server.tools.analytics.metrics.roi_metrics import ROICalculator
from mcp_server.tools.analytics.metrics.timing_metrics import TimingCalculator
from mcp_server.tools.analytics.metrics.hidden_metrics import HiddenOpportunityCalculator
from mcp_server.tools.analytics.database.session_manager import AsyncSQLiteManager

logger = logging.getLogger(__name__)


class GrantScoringEngine:
    """
    Main orchestrator for grant scoring using multiple analytical dimensions.
    
    Combines competition analysis, success probability, ROI calculations,
    timing assessment, and hidden opportunity detection into comprehensive scores.
    """
    
    def __init__(self, db_manager: Optional[AsyncSQLiteManager] = None):
        """Initialize the scoring engine."""
        self.constants = IndustryConstants()
        
        # Initialize metric calculators
        self.competition_calculator = CompetitionIndexCalculator()
        self.success_calculator = SuccessProbabilityCalculator()
        self.roi_calculator = ROICalculator()
        self.timing_calculator = TimingCalculator()
        self.hidden_calculator = HiddenOpportunityCalculator()
        
        # Database manager for persistence
        self.db_manager = db_manager
        
        logger.info("Initialized Grant Scoring Engine with all metric calculators")
    
    def get_custom_weights(
        self, 
        user_profile: Optional[Dict] = None,
        scoring_weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """
        Get custom scoring weights based on user preferences.
        
        Args:
            user_profile: User research profile
            scoring_weights: Explicit custom weights
            
        Returns:
            Dictionary of scoring weights
        """
        # Start with default weights
        weights = {
            'technical_fit': self.constants.TECHNICAL_FIT_WEIGHT,
            'competition': self.constants.COMPETITION_WEIGHT,
            'roi': self.constants.ROI_WEIGHT,
            'timing': self.constants.TIMING_WEIGHT,
            'success_probability': self.constants.SUCCESS_PROB_WEIGHT
        }
        
        # Apply explicit custom weights if provided
        if scoring_weights:
            for key, value in scoring_weights.items():
                if key in weights and 0 <= value <= 1:
                    weights[key] = value
        
        # Adjust weights based on user profile preferences
        if user_profile:
            career_stage = user_profile.get('career_stage', 'mid-career')
            priorities = user_profile.get('scoring_priorities', {})
            
            # Early career researchers might prioritize success probability
            if career_stage == 'early-career':
                weights['success_probability'] *= 1.2
                weights['timing'] *= 1.1
                
            # Senior researchers might prioritize ROI and strategic fit
            elif career_stage == 'senior':
                weights['roi'] *= 1.2
                weights['technical_fit'] *= 1.1
            
            # Apply user-specified priorities
            for priority, multiplier in priorities.items():
                if priority in weights:
                    weights[priority] *= multiplier
        
        # Normalize weights to sum to 1.0
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}
        
        return weights
    
    def generate_recommendation(
        self,
        opportunity: OpportunityV1,
        overall_score: float,
        component_scores: Dict[str, float]
    ) -> str:
        """
        Generate strategic recommendation based on scores.
        
        Args:
            opportunity: Grant opportunity
            overall_score: Overall weighted score
            component_scores: Individual component scores
            
        Returns:
            Strategic recommendation string
        """
        recommendations = []
        
        # Overall assessment
        if overall_score >= 80:
            recommendations.append("🎯 HIGH PRIORITY - Excellent opportunity across multiple dimensions")
        elif overall_score >= 60:
            recommendations.append("✅ RECOMMENDED - Strong opportunity worth pursuing")
        elif overall_score >= 40:
            recommendations.append("⚠️ CONDITIONAL - Consider if it aligns with strategic goals")
        else:
            recommendations.append("❌ NOT RECOMMENDED - Significant challenges across multiple areas")
        
        # Specific dimension feedback
        if component_scores.get('competition', 0) < 30:
            recommendations.append("• High competition - prepare exceptional application")
        
        if component_scores.get('timing', 0) < 40:
            recommendations.append("• Tight deadline - ensure adequate preparation time")
        
        if component_scores.get('roi', 0) > 70:
            recommendations.append("• Excellent ROI - high value relative to effort")
        
        if component_scores.get('success_probability', 0) > 60:
            recommendations.append("• Good fit indicators - strong chance of success")
        elif component_scores.get('success_probability', 0) < 30:
            recommendations.append("• Low success probability - consider strengthening application")
        
        # Strategic insights
        award_ceiling = opportunity.summary.award_ceiling
        if award_ceiling and award_ceiling > 1000000:
            recommendations.append("• Large award - consider forming partnerships")
        
        return " ".join(recommendations)
    
    async def score_single_opportunity(
        self,
        opportunity: OpportunityV1,
        user_profile: Optional[Dict] = None,
        scoring_weights: Optional[Dict[str, float]] = None,
        concurrent_opportunities: Optional[List[OpportunityV1]] = None,
        use_cache: bool = True
    ) -> GrantScore:
        """
        Score a single grant opportunity across all dimensions.
        
        Args:
            opportunity: Grant opportunity to score
            user_profile: User research profile (optional)
            scoring_weights: Custom scoring weights (optional)
            concurrent_opportunities: Other opportunities for timing analysis
            use_cache: Whether to use database cache
            
        Returns:
            Comprehensive GrantScore
        """
        try:
            start_time = time.time()
            
            # Check cache first
            if use_cache and self.db_manager:
                cached_score = await self.db_manager.get_grant_score(opportunity.opportunity_id)
                if cached_score:
                    logger.info(f"Using cached score for {opportunity.opportunity_id}")
                    # Convert cached data back to GrantScore (simplified)
                    # In production, you'd want full deserialization
                    pass
            
            # Get custom weights
            weights = self.get_custom_weights(user_profile, scoring_weights)
            
            # Calculate competition score and get estimated applications for other metrics
            competition_score = self.competition_calculator.calculate_competition_score(
                opportunity
            )
            
            # Extract estimated applications for success probability calculation
            estimated_applications = competition_score.components.get('estimated_applications', 100)
            
            # Calculate success probability score
            success_score = self.success_calculator.calculate_success_probability_score(
                opportunity, estimated_applications, user_profile
            )
            
            # Calculate ROI score
            roi_score = self.roi_calculator.calculate_roi_score(
                opportunity, success_score.value, user_profile
            )
            
            # Calculate timing score
            timing_score = self.timing_calculator.calculate_timing_score(
                opportunity, user_profile, concurrent_opportunities
            )
            
            # Calculate technical fit score (simplified version)
            technical_fit_score = self._calculate_technical_fit_score(opportunity, user_profile)
            
            # Calculate overall weighted score
            component_scores = {
                'technical_fit': technical_fit_score.value,
                'competition': competition_score.value,
                'roi': roi_score.value,
                'timing': timing_score.value,
                'success_probability': success_score.value
            }
            
            overall_score = sum(
                component_scores[component] * weights[component]
                for component in component_scores
            )
            
            # Generate recommendation
            recommendation = self.generate_recommendation(
                opportunity, overall_score, component_scores
            )
            
            # Create comprehensive GrantScore
            grant_score = GrantScore(
                opportunity_id=opportunity.opportunity_id,
                opportunity_title=opportunity.opportunity_title,
                technical_fit_score=technical_fit_score,
                competition_index=competition_score,
                roi_score=roi_score,
                timing_score=timing_score,
                success_probability=success_score,
                overall_score=overall_score,
                recommendation=recommendation
            )
            
            # Store in database cache
            if self.db_manager:
                await self.db_manager.store_grant_score(
                    opportunity.opportunity_id,
                    opportunity.opportunity_title,
                    overall_score,
                    component_scores,
                    {
                        'technical_fit': technical_fit_score.dict(),
                        'competition': competition_score.dict(),
                        'roi': roi_score.dict(),
                        'timing': timing_score.dict(),
                        'success_probability': success_score.dict(),
                        'weights': weights
                    },
                    recommendation
                )
            
            scoring_time = time.time() - start_time
            logger.info(f"Scored opportunity {opportunity.opportunity_id} in {scoring_time:.2f}s")
            
            return grant_score
            
        except Exception as e:
            logger.error(f"Error scoring opportunity {opportunity.opportunity_id}: {e}")
            raise
    
    def _calculate_technical_fit_score(
        self,
        opportunity: OpportunityV1,
        user_profile: Optional[Dict] = None
    ) -> 'ScoreBreakdown':
        """
        Calculate technical fit score (simplified implementation).
        This is a basic implementation - could be enhanced with NLP/ML.
        """
        from mcp_server.models.analytics_schemas import ScoreBreakdown
        
        try:
            fit_score = 50.0  # Default neutral fit
            
            if user_profile:
                # Simple keyword matching
                user_keywords = user_profile.get('research_keywords', [])
                grant_text = (
                    opportunity.opportunity_title + " " +
                    (opportunity.summary.summary_description or "") + " " +
                    (opportunity.summary.funding_category or "")
                ).lower()
                
                if user_keywords:
                    keyword_matches = sum(
                        1 for keyword in user_keywords 
                        if keyword.lower() in grant_text
                    )
                    fit_score = min(100, max(20, (keyword_matches / len(user_keywords)) * 100))
            
            return ScoreBreakdown(
                value=fit_score,
                calculation=f"Technical fit based on keyword matching = {fit_score:.1f}%",
                components={
                    "keyword_matches": fit_score / 100,
                    "method": "Simple keyword matching"
                },
                interpretation="Higher score indicates better technical alignment",
                percentile=fit_score,
                industry_benchmark="Varies by research domain"
            )
            
        except Exception as e:
            logger.error(f"Error calculating technical fit: {e}")
            return ScoreBreakdown(
                value=50.0,
                calculation="Error in calculation",
                components={"error": str(e)},
                interpretation="Unable to calculate technical fit",
                percentile=None,
                industry_benchmark=None
            )
    
    async def batch_score_opportunities(
        self,
        opportunities: List[OpportunityV1],
        user_profile: Optional[Dict] = None,
        scoring_weights: Optional[Dict[str, float]] = None,
        include_hidden: bool = True,
        session_id: Optional[str] = None
    ) -> BatchScoreResult:
        """
        Score multiple opportunities in batch with optimization.
        
        Args:
            opportunities: List of opportunities to score
            user_profile: User research profile
            scoring_weights: Custom scoring weights
            include_hidden: Whether to include hidden opportunity analysis
            session_id: Session ID for tracking
            
        Returns:
            BatchScoreResult with all scores and analytics
        """
        try:
            start_time = time.time()
            
            logger.info(f"Starting batch scoring of {len(opportunities)} opportunities")
            
            # Score all opportunities
            scored_opportunities = []
            hidden_opportunities = []
            
            for i, opportunity in enumerate(opportunities):
                try:
                    # Score the opportunity
                    grant_score = await self.score_single_opportunity(
                        opportunity,
                        user_profile,
                        scoring_weights,
                        opportunities  # Pass all for timing analysis
                    )
                    scored_opportunities.append(grant_score)
                    
                    # Calculate hidden opportunity score if requested
                    if include_hidden:
                        hidden_score = self.hidden_calculator.calculate_hidden_opportunity_score(
                            opportunity, user_profile, {'search_position': i + 1}
                        )
                        
                        # Only include if score is above threshold
                        if hidden_score.hidden_opportunity_score > 40:
                            hidden_opportunities.append(hidden_score)
                    
                except Exception as e:
                    logger.error(f"Error scoring opportunity {opportunity.opportunity_id}: {e}")
                    continue
            
            # Calculate batch statistics
            total_opportunities = len(opportunities)
            scoring_time_ms = (time.time() - start_time) * 1000
            
            # Calculate cache hit rate (simplified)
            cache_hit_rate = 0.0  # Would be calculated from actual cache hits
            
            # Sort opportunities by overall score (descending)
            scored_opportunities.sort(key=lambda x: x.overall_score, reverse=True)
            hidden_opportunities.sort(key=lambda x: x.hidden_opportunity_score, reverse=True)
            
            # Update session statistics if database available
            if self.db_manager and session_id:
                avg_score = np.mean([score.overall_score for score in scored_opportunities]) if scored_opportunities else 0.0
                await self.db_manager.update_session_results(
                    session_id,
                    total_opportunities,
                    len(scored_opportunities),
                    len(hidden_opportunities),
                    avg_score
                )
            
            logger.info(f"Completed batch scoring in {scoring_time_ms:.0f}ms")
            
            return BatchScoreResult(
                scores=scored_opportunities,
                hidden_opportunities=hidden_opportunities,
                strategic_recommendation=None,  # Could implement portfolio optimization here
                total_opportunities=total_opportunities,
                scoring_time_ms=scoring_time_ms,
                cache_hit_rate=cache_hit_rate
            )
            
        except Exception as e:
            logger.error(f"Error in batch scoring: {e}")
            raise
    
    async def get_scoring_explanation(
        self,
        opportunity_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed explanation of how a score was calculated.
        
        Args:
            opportunity_id: ID of opportunity to explain
            
        Returns:
            Detailed scoring explanation
        """
        if not self.db_manager:
            return None
        
        try:
            score_data = await self.db_manager.get_grant_score(opportunity_id)
            if score_data:
                return {
                    'opportunity_id': opportunity_id,
                    'overall_score': score_data.get('overall_score'),
                    'component_scores': {
                        'technical_fit': score_data.get('technical_fit_score'),
                        'competition': score_data.get('competition_index'),
                        'roi': score_data.get('roi_score'),
                        'timing': score_data.get('timing_score'),
                        'success_probability': score_data.get('success_probability')
                    },
                    'calculation_details': score_data.get('score_breakdown'),
                    'recommendation': score_data.get('recommendation'),
                    'calculated_at': score_data.get('calculated_at')
                }
        except Exception as e:
            logger.error(f"Error getting scoring explanation: {e}")
            
        return None