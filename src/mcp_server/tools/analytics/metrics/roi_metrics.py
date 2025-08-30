"""ROI Score calculations based on research funding efficiency metrics."""

import logging
from typing import Dict, List, Optional, Tuple
import numpy as np

from mcp_server.models.grants_schemas import OpportunityV1
from mcp_server.models.analytics_schemas import ScoreBreakdown, IndustryConstants

logger = logging.getLogger(__name__)


class ROICalculator:
    """
    Calculate Return on Investment (ROI) scores for grant opportunities.
    
    Evaluates the financial and strategic value of pursuing a grant application
    relative to the effort and resources required.
    """
    
    def __init__(self):
        self.constants = IndustryConstants()
    
    def estimate_application_cost(
        self,
        award_ceiling: Optional[float],
        award_floor: Optional[float],
        agency_code: str,
        complexity_factors: Optional[Dict] = None
    ) -> Tuple[float, int]:
        """
        Estimate the cost (in dollars and hours) to prepare an application.
        
        Args:
            award_ceiling: Maximum award amount
            award_floor: Minimum award amount
            agency_code: Agency code
            complexity_factors: Additional complexity factors
            
        Returns:
            Tuple of (cost_dollars, hours_required)
        """
        # Base hours by award size (empirical data from academic researchers)
        award_amount = award_ceiling or award_floor or 100000
        
        if award_amount < 50000:
            base_hours = 40    # Small grants
        elif award_amount < 100000:
            base_hours = 60    # Standard grants
        elif award_amount < 500000:
            base_hours = 100   # Medium grants
        elif award_amount < 1000000:
            base_hours = 150   # Large grants
        else:
            base_hours = 200   # Very large grants
        
        # Agency-specific complexity multipliers
        agency_multipliers = {
            'NIH': 1.5,      # Complex requirements, detailed budgets
            'NSF': 1.3,      # Moderate complexity
            'DOE': 1.4,      # Technical complexity
            'DOD': 1.6,      # High security/compliance requirements
            'NASA': 1.4,     # Technical complexity
            'EPA': 1.2,      # Moderate requirements
            'USDA': 1.1,     # Simpler applications
        }
        
        main_agency = agency_code.split('-')[0] if agency_code else 'OTHER'
        complexity_multiplier = agency_multipliers.get(main_agency, 1.2)
        
        # Additional complexity factors
        if complexity_factors:
            if complexity_factors.get('requires_partnerships', False):
                complexity_multiplier *= 1.2
            if complexity_factors.get('requires_preliminary_data', False):
                complexity_multiplier *= 1.1
            if complexity_factors.get('first_time_agency', False):
                complexity_multiplier *= 1.3
        
        total_hours = int(base_hours * complexity_multiplier)
        
        # Calculate dollar cost (using academic hourly rate)
        cost_dollars = total_hours * self.constants.ACADEMIC_HOURLY_RATE
        
        return cost_dollars, total_hours
    
    def calculate_basic_roi(
        self,
        award_amount: float,
        application_cost: float
    ) -> float:
        """
        Calculate basic ROI percentage.
        
        Formula: Grant_ROI = ((Award_Amount - Application_Cost) / Application_Cost) * 100
        
        Args:
            award_amount: Expected award amount
            application_cost: Cost to prepare application
            
        Returns:
            ROI percentage
        """
        if application_cost <= 0:
            return 0.0
        
        return ((award_amount - application_cost) / application_cost) * 100
    
    def calculate_effort_adjusted_roi(
        self,
        grant_roi: float,
        hours_required: int,
        hourly_opportunity_cost: float
    ) -> float:
        """
        Calculate effort-adjusted ROI.
        
        Formula: Effort_ROI = Grant_ROI / (Hours_Required * Opportunity_Cost_Per_Hour)
        
        Args:
            grant_roi: Basic grant ROI
            hours_required: Hours required for application
            hourly_opportunity_cost: Opportunity cost per hour
            
        Returns:
            Effort-adjusted ROI
        """
        total_opportunity_cost = hours_required * hourly_opportunity_cost
        
        if total_opportunity_cost <= 0:
            return grant_roi
        
        return grant_roi / total_opportunity_cost * 1000  # Scale for readability
    
    def calculate_risk_adjusted_roi(
        self,
        grant_roi: float,
        success_probability: float,
        risk_factors: Optional[Dict] = None
    ) -> float:
        """
        Calculate risk-adjusted ROI.
        
        Formula: Risk_Adjusted_ROI = Grant_ROI × Success_Probability × (1 - Risk_Factor)
        
        Args:
            grant_roi: Basic grant ROI
            success_probability: Probability of success (0.0-1.0)
            risk_factors: Additional risk factors
            
        Returns:
            Risk-adjusted ROI
        """
        # Base risk factor
        base_risk = 0.1  # 10% base risk
        
        # Additional risk factors
        additional_risk = 0.0
        
        if risk_factors:
            if risk_factors.get('new_agency', False):
                additional_risk += 0.1
            if risk_factors.get('tight_deadline', False):
                additional_risk += 0.05
            if risk_factors.get('high_competition', False):
                additional_risk += 0.1
            if risk_factors.get('complex_requirements', False):
                additional_risk += 0.05
        
        total_risk_factor = min(0.5, base_risk + additional_risk)  # Cap at 50%
        
        return grant_roi * success_probability * (1 - total_risk_factor)
    
    def calculate_strategic_value_multiplier(
        self,
        opportunity: OpportunityV1,
        user_profile: Optional[Dict] = None
    ) -> float:
        """
        Calculate strategic value multiplier beyond pure financial ROI.
        
        Args:
            opportunity: Grant opportunity
            user_profile: User research profile
            
        Returns:
            Strategic value multiplier (0.8-2.0)
        """
        multiplier = 1.0
        
        # Agency prestige factor
        prestige_multipliers = {
            'NIH': 1.3,      # High prestige
            'NSF': 1.2,      # High prestige
            'DOE': 1.1,      # Good prestige
            'NASA': 1.2,     # High prestige
            'DOD': 1.1,      # Good prestige
            'EPA': 1.0,      # Standard prestige
            'USDA': 1.0,     # Standard prestige
        }
        
        main_agency = opportunity.agency_code.split('-')[0] if opportunity.agency_code else 'OTHER'
        multiplier *= prestige_multipliers.get(main_agency, 1.0)
        
        # Career stage considerations
        if user_profile:
            career_stage = user_profile.get('career_stage', 'mid-career')
            
            if career_stage == 'early-career':
                # Early career researchers benefit more from prestigious grants
                multiplier *= 1.2
            elif career_stage == 'senior':
                # Senior researchers may value efficiency more
                multiplier *= 0.9
        
        # Multi-year funding bonus
        if opportunity.summary.award_ceiling and opportunity.summary.award_ceiling > 500000:
            multiplier *= 1.1  # Assume larger grants are multi-year
        
        # Collaboration opportunities
        description = opportunity.summary.summary_description or ""
        if any(word in description.lower() for word in ['collaboration', 'partnership', 'consortium']):
            multiplier *= 1.1
        
        return max(0.8, min(2.0, multiplier))
    
    def calculate_roi_score(
        self,
        opportunity: OpportunityV1,
        success_probability: float,
        user_profile: Optional[Dict] = None
    ) -> ScoreBreakdown:
        """
        Calculate comprehensive ROI score.
        
        Args:
            opportunity: Grant opportunity to score
            success_probability: Success probability (0-100)
            user_profile: User research profile (optional)
            
        Returns:
            ScoreBreakdown with transparent calculation
        """
        try:
            # Extract key information
            award_ceiling = opportunity.summary.award_ceiling or 100000
            award_floor = opportunity.summary.award_floor or 0
            agency = opportunity.agency_code
            
            # Use average award amount for calculations
            award_amount = (award_ceiling + award_floor) / 2 if award_floor else award_ceiling
            
            # Estimate application costs
            application_cost, hours_required = self.estimate_application_cost(
                award_ceiling, award_floor, agency
            )
            
            # Calculate basic ROI
            basic_roi = self.calculate_basic_roi(award_amount, application_cost)
            
            # Calculate effort-adjusted ROI
            hourly_rate = user_profile.get('hourly_opportunity_cost', self.constants.ACADEMIC_HOURLY_RATE) if user_profile else self.constants.ACADEMIC_HOURLY_RATE
            effort_roi = self.calculate_effort_adjusted_roi(basic_roi, hours_required, hourly_rate)
            
            # Risk factors assessment
            risk_factors = {
                'tight_deadline': False,  # Would need deadline analysis
                'high_competition': False,  # Would need competition data
                'new_agency': not user_profile.get('familiar_agencies', [agency]) if user_profile else False,
                'complex_requirements': agency.startswith(('NIH', 'DOD'))  # Heuristic
            }
            
            # Calculate risk-adjusted ROI
            risk_adjusted_roi = self.calculate_risk_adjusted_roi(
                basic_roi, success_probability / 100, risk_factors
            )
            
            # Apply strategic value multiplier
            strategic_multiplier = self.calculate_strategic_value_multiplier(opportunity, user_profile)
            final_roi = risk_adjusted_roi * strategic_multiplier
            
            # Convert to 0-100 score scale
            # Normalize based on typical ROI ranges (0-1000% basic ROI)
            roi_score = min(100, max(0, (final_roi / 1000) * 100))
            
            # Build calculation explanation
            calculation = f"ROI: ${award_amount:,.0f} award / ${application_cost:,.0f} cost = {basic_roi:.0f}%"
            
            # Interpret the score
            if roi_score >= 80:
                interpretation = "Excellent ROI (high value opportunity)"
            elif roi_score >= 60:
                interpretation = "Good ROI (worthwhile investment)"
            elif roi_score >= 40:
                interpretation = "Moderate ROI (consider other factors)"
            elif roi_score >= 20:
                interpretation = "Low ROI (high cost relative to benefit)"
            else:
                interpretation = "Poor ROI (not cost-effective)"
            
            # Calculate percentile
            percentile = roi_score  # Use score directly as percentile approximation
            
            # Industry benchmark
            benchmark = f"Typical academic grant ROI: 300-800%"
            
            return ScoreBreakdown(
                value=roi_score,
                calculation=calculation,
                components={
                    "award_amount": award_amount,
                    "application_cost": application_cost,
                    "hours_required": hours_required,
                    "basic_roi": basic_roi,
                    "effort_adjusted_roi": effort_roi,
                    "risk_adjusted_roi": risk_adjusted_roi,
                    "strategic_multiplier": strategic_multiplier,
                    "final_roi": final_roi,
                    "formula": "Risk_Adjusted_ROI × Strategic_Value_Multiplier"
                },
                interpretation=interpretation,
                percentile=percentile,
                industry_benchmark=benchmark
            )
            
        except Exception as e:
            logger.error(f"Error calculating ROI score: {e}")
            return ScoreBreakdown(
                value=50.0,
                calculation="Error in calculation",
                components={"error": str(e)},
                interpretation="Unable to calculate ROI",
                percentile=None,
                industry_benchmark=None
            )