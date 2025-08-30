"""Pydantic models for analytics and scoring data."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from pydantic import BaseModel, Field
import numpy as np


class ScoreBreakdown(BaseModel):
    """Transparent breakdown of how a score was calculated."""
    
    value: float = Field(..., description="Final calculated score")
    calculation: str = Field(..., description="Human-readable calculation formula")
    components: Dict[str, Any] = Field(..., description="Individual calculation components")
    interpretation: str = Field(..., description="What this score means")
    percentile: Optional[float] = Field(None, description="Percentile ranking")
    industry_benchmark: Optional[str] = Field(None, description="Industry comparison")


class GrantScore(BaseModel):
    """Comprehensive scoring for a grant opportunity."""
    
    opportunity_id: str
    opportunity_title: str
    
    # Core scoring dimensions
    technical_fit_score: ScoreBreakdown
    competition_index: ScoreBreakdown
    roi_score: ScoreBreakdown
    timing_score: ScoreBreakdown
    success_probability: ScoreBreakdown
    
    # Composite scores
    overall_score: float = Field(..., description="Weighted overall score (0-100)")
    recommendation: str = Field(..., description="Strategic recommendation")
    
    # Metadata
    calculated_at: datetime = Field(default_factory=datetime.utcnow)
    calculation_version: str = Field(default="3.0.0")
    
    model_config = {"extra": "allow"}


class HiddenOpportunityScore(BaseModel):
    """Score for identifying hidden/undersubscribed opportunities."""
    
    opportunity_id: str
    opportunity_title: str
    
    # Hidden opportunity components
    visibility_index: ScoreBreakdown
    undersubscription_score: ScoreBreakdown
    cross_category_score: ScoreBreakdown
    
    # Final hidden opportunity score (0-100)
    hidden_opportunity_score: float
    opportunity_type: str = Field(..., description="Type of hidden opportunity")
    discovery_reason: str = Field(..., description="Why this was flagged as hidden")
    
    calculated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = {"extra": "allow"}


class StrategicRecommendation(BaseModel):
    """Strategic recommendation for grant application portfolio."""
    
    # Portfolio categorization
    reach_grants: List[str] = Field(..., description="High-reach opportunity IDs")
    match_grants: List[str] = Field(..., description="Good match opportunity IDs")
    safety_grants: List[str] = Field(..., description="Safety option opportunity IDs")
    
    # Timeline optimization
    optimal_timeline: Dict[str, Any] = Field(..., description="Recommended application timeline")
    resource_allocation: Dict[str, float] = Field(..., description="Resource distribution recommendations")
    
    # Collaboration opportunities
    collaboration_opportunities: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Strategic insights
    portfolio_diversity_score: float = Field(..., description="Portfolio diversity (0-100)")
    expected_success_rate: float = Field(..., description="Expected overall success rate")
    risk_assessment: str = Field(..., description="Portfolio risk assessment")
    
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = {"extra": "allow"}


@dataclass
class IndustryConstants:
    """Industry-standard constants for scoring calculations."""
    
    # NIH/NSF Competition Index Benchmarks
    NIH_AVERAGE_CI: float = 25.0
    NSF_AVERAGE_CI: float = 30.0
    HIGH_COMPETITION_THRESHOLD: float = 50.0
    LOW_COMPETITION_THRESHOLD: float = 15.0
    
    # Success Rate Benchmarks
    NIH_AVERAGE_SUCCESS_RATE: float = 0.20  # 20%
    NSF_AVERAGE_SUCCESS_RATE: float = 0.25  # 25%
    EXCELLENT_SUCCESS_RATE: float = 0.40   # 40%
    
    # ROI Calculation Constants
    AVERAGE_APPLICATION_COST_HOURS: float = 120.0
    ACADEMIC_HOURLY_RATE: float = 75.0  # Academic opportunity cost per hour
    INDUSTRY_HOURLY_RATE: float = 150.0  # Industry consultant rate
    
    # Timing Constants
    OPTIMAL_PREP_DAYS_SMALL: int = 30   # < $100K
    OPTIMAL_PREP_DAYS_MEDIUM: int = 60  # $100K - $1M
    OPTIMAL_PREP_DAYS_LARGE: int = 90   # > $1M
    
    # Scoring Weights (sum to 1.0)
    TECHNICAL_FIT_WEIGHT: float = 0.25
    COMPETITION_WEIGHT: float = 0.20
    ROI_WEIGHT: float = 0.20
    TIMING_WEIGHT: float = 0.15
    SUCCESS_PROB_WEIGHT: float = 0.20
    
    # Hidden Opportunity Weights
    UNDERSUBSCRIPTION_WEIGHT: float = 0.4
    VISIBILITY_WEIGHT: float = 0.3
    CROSS_CATEGORY_WEIGHT: float = 0.3


class ScoreCalculationRequest(BaseModel):
    """Request for score calculation."""
    
    opportunities: List[str] = Field(..., description="List of opportunity IDs to score")
    user_profile: Optional[Dict[str, Any]] = Field(None, description="User research profile")
    scoring_weights: Optional[Dict[str, float]] = Field(None, description="Custom scoring weights")
    include_hidden: bool = Field(True, description="Include hidden opportunity analysis")
    
    model_config = {"extra": "allow"}


class BatchScoreResult(BaseModel):
    """Result of batch scoring operation."""
    
    scores: List[GrantScore]
    hidden_opportunities: List[HiddenOpportunityScore]
    strategic_recommendation: Optional[StrategicRecommendation] = None
    
    # Batch statistics
    total_opportunities: int
    scoring_time_ms: float
    cache_hit_rate: float
    
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = {"extra": "allow"}