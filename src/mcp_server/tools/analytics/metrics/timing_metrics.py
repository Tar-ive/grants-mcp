"""Timing Score calculations for preparation adequacy assessment."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np

from mcp_server.models.grants_schemas import OpportunityV1
from mcp_server.models.analytics_schemas import ScoreBreakdown, IndustryConstants

logger = logging.getLogger(__name__)


class TimingCalculator:
    """
    Calculate Timing scores for grant opportunities.
    
    Evaluates whether there is adequate time to prepare a competitive application
    and considers deadline competition factors.
    """
    
    def __init__(self):
        self.constants = IndustryConstants()
    
    def parse_deadline(self, close_date: Optional[str]) -> Optional[datetime]:
        """
        Parse grant deadline from various date formats.
        
        Args:
            close_date: Close date string from grant data
            
        Returns:
            Parsed datetime object or None
        """
        if not close_date:
            return None
        
        # Common date formats in grant data
        date_formats = [
            "%Y-%m-%d",           # 2024-03-15
            "%m/%d/%Y",           # 03/15/2024
            "%d/%m/%Y",           # 15/03/2024
            "%Y-%m-%dT%H:%M:%S",  # 2024-03-15T23:59:59
            "%Y-%m-%d %H:%M:%S",  # 2024-03-15 23:59:59
            "%B %d, %Y",          # March 15, 2024
            "%b %d, %Y",          # Mar 15, 2024
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(close_date.strip(), fmt)
            except ValueError:
                continue
        
        # Try parsing just the date part if there's time information
        try:
            date_part = close_date.split('T')[0].split(' ')[0]
            return datetime.strptime(date_part, "%Y-%m-%d")
        except (ValueError, IndexError):
            pass
        
        logger.warning(f"Could not parse deadline: {close_date}")
        return None
    
    def calculate_days_until_deadline(self, close_date: Optional[str]) -> Optional[int]:
        """
        Calculate days remaining until deadline.
        
        Args:
            close_date: Grant close date string
            
        Returns:
            Number of days until deadline, or None if unparseable
        """
        deadline = self.parse_deadline(close_date)
        if not deadline:
            return None
        
        today = datetime.utcnow()
        days_remaining = (deadline - today).days
        
        return max(0, days_remaining)  # Don't return negative days
    
    def get_optimal_preparation_days(
        self,
        award_ceiling: Optional[float],
        agency_code: str,
        complexity_factors: Optional[Dict] = None
    ) -> int:
        """
        Determine optimal preparation time based on grant characteristics.
        
        Args:
            award_ceiling: Maximum award amount
            agency_code: Agency code
            complexity_factors: Additional complexity factors
            
        Returns:
            Optimal preparation days
        """
        award_amount = award_ceiling or 100000
        
        # Base optimal days by award size
        if award_amount < 100000:
            base_days = self.constants.OPTIMAL_PREP_DAYS_SMALL
        elif award_amount < 1000000:
            base_days = self.constants.OPTIMAL_PREP_DAYS_MEDIUM
        else:
            base_days = self.constants.OPTIMAL_PREP_DAYS_LARGE
        
        # Agency-specific adjustments
        agency_adjustments = {
            'NIH': 1.3,      # Complex requirements need more time
            'NSF': 1.1,      # Moderate additional time
            'DOE': 1.2,      # Technical complexity
            'DOD': 1.4,      # High compliance requirements
            'NASA': 1.2,     # Technical complexity
            'EPA': 1.1,      # Moderate requirements
            'USDA': 1.0,     # Standard time
        }
        
        main_agency = agency_code.split('-')[0] if agency_code else 'OTHER'
        adjustment = agency_adjustments.get(main_agency, 1.1)
        
        # Complexity factor adjustments
        if complexity_factors:
            if complexity_factors.get('requires_partnerships', False):
                adjustment *= 1.2
            if complexity_factors.get('requires_preliminary_data', False):
                adjustment *= 1.1
            if complexity_factors.get('first_submission', True):
                adjustment *= 1.1
        
        return int(base_days * adjustment)
    
    def calculate_preparation_adequacy_score(
        self,
        days_available: Optional[int],
        optimal_days: int
    ) -> float:
        """
        Calculate preparation adequacy score.
        
        Formula: Prep_Score = min(100, (Days_Available / Optimal_Prep_Days) * 100)
        
        Args:
            days_available: Days available until deadline
            optimal_days: Optimal preparation days
            
        Returns:
            Preparation adequacy score (0-100)
        """
        if days_available is None:
            return 50.0  # Neutral score if deadline unknown
        
        if optimal_days <= 0:
            return 100.0
        
        adequacy_ratio = days_available / optimal_days
        
        # Score with non-linear scaling (diminishing returns after optimal)
        if adequacy_ratio >= 1.0:
            # Bonus for extra time, but diminishing returns
            score = 100 - (10 * (1 / (1 + adequacy_ratio - 1)))
        else:
            # Penalty for insufficient time
            score = adequacy_ratio * 100
        
        return min(100, max(0, score))
    
    def assess_deadline_competition(
        self,
        close_date: Optional[str],
        concurrent_deadlines: Optional[List[str]] = None,
        max_concurrent_capacity: int = 3
    ) -> float:
        """
        Assess competition from concurrent deadlines.
        
        Args:
            close_date: This grant's deadline
            concurrent_deadlines: List of other deadlines in same period
            max_concurrent_capacity: Maximum grants user can handle simultaneously
            
        Returns:
            Deadline competition factor (0.0-1.0)
        """
        if not close_date:
            return 1.0  # Neutral if no deadline
        
        deadline = self.parse_deadline(close_date)
        if not deadline:
            return 1.0
        
        # Count concurrent deadlines within +/- 2 weeks
        concurrent_count = 0
        
        if concurrent_deadlines:
            for other_deadline in concurrent_deadlines:
                other_date = self.parse_deadline(other_deadline)
                if other_date:
                    days_diff = abs((deadline - other_date).days)
                    if days_diff <= 14:  # Within 2 weeks
                        concurrent_count += 1
        
        # Calculate competition factor
        if concurrent_count == 0:
            return 1.0  # No competition
        elif concurrent_count < max_concurrent_capacity:
            return 1.0 - (concurrent_count * 0.1)  # 10% penalty per concurrent deadline
        else:
            return max(0.3, 1.0 - (concurrent_count * 0.2))  # Higher penalty, minimum 30%
    
    def assess_resubmission_possibility(
        self,
        agency_code: str,
        close_date: Optional[str]
    ) -> float:
        """
        Assess whether resubmission is possible if first attempt fails.
        
        Args:
            agency_code: Agency code
            close_date: Grant deadline
            
        Returns:
            Resubmission possibility factor (0.8-1.2)
        """
        # Agencies with regular resubmission cycles
        resubmission_friendly = {
            'NIH': 1.2,      # Regular cycles, encourages resubmission
            'NSF': 1.1,      # Annual cycles usually
            'DOE': 1.0,      # Varies by program
            'DOD': 0.9,      # Often one-time opportunities
            'NASA': 0.9,     # Limited opportunities
            'EPA': 1.0,      # Varies by program
            'USDA': 1.1,     # Regular cycles
        }
        
        main_agency = agency_code.split('-')[0] if agency_code else 'OTHER'
        base_factor = resubmission_friendly.get(main_agency, 1.0)
        
        # Check if this appears to be a regular cycle vs one-time opportunity
        if close_date:
            deadline = self.parse_deadline(close_date)
            if deadline:
                # Heuristic: regular cycles often have deadlines at consistent times
                month = deadline.month
                if month in [3, 6, 9, 12]:  # Quarterly
                    base_factor *= 1.05
                elif month in [1, 7]:  # Semi-annual
                    base_factor *= 1.1
        
        return base_factor
    
    def calculate_timing_score(
        self,
        opportunity: OpportunityV1,
        user_profile: Optional[Dict] = None,
        concurrent_opportunities: Optional[List[OpportunityV1]] = None
    ) -> ScoreBreakdown:
        """
        Calculate comprehensive Timing score.
        
        Args:
            opportunity: Grant opportunity to score
            user_profile: User profile with preferences
            concurrent_opportunities: Other opportunities being considered
            
        Returns:
            ScoreBreakdown with transparent calculation
        """
        try:
            # Extract key information
            close_date = opportunity.summary.close_date
            award_ceiling = opportunity.summary.award_ceiling
            agency = opportunity.agency_code
            
            # Calculate days until deadline
            days_available = self.calculate_days_until_deadline(close_date)
            
            # Get optimal preparation time
            complexity_factors = {
                'first_submission': user_profile.get('first_time_applicant', True) if user_profile else True,
                'requires_partnerships': False,  # Would need to analyze description
                'requires_preliminary_data': False,  # Would need to analyze requirements
            }
            
            optimal_days = self.get_optimal_preparation_days(
                award_ceiling, agency, complexity_factors
            )
            
            # Calculate preparation adequacy
            prep_score = self.calculate_preparation_adequacy_score(days_available, optimal_days)
            
            # Assess deadline competition
            concurrent_deadlines = []
            if concurrent_opportunities:
                concurrent_deadlines = [opp.summary.close_date for opp in concurrent_opportunities if opp.summary.close_date]
            
            max_capacity = user_profile.get('max_concurrent_applications', 3) if user_profile else 3
            competition_factor = self.assess_deadline_competition(close_date, concurrent_deadlines, max_capacity)
            
            # Assess resubmission possibility
            resubmission_factor = self.assess_resubmission_possibility(agency, close_date)
            
            # Calculate final timing score
            final_score = prep_score * competition_factor * resubmission_factor
            final_score = min(100, max(0, final_score))
            
            # Build calculation explanation
            if days_available is not None:
                calculation = f"Timing: {days_available} days available / {optimal_days} optimal = {prep_score:.1f}%"
            else:
                calculation = f"Timing: Unknown deadline, using neutral score"
            
            # Interpret the score
            if final_score >= 80:
                interpretation = "Excellent timing (ample preparation time)"
            elif final_score >= 60:
                interpretation = "Good timing (adequate preparation time)"
            elif final_score >= 40:
                interpretation = "Tight timing (rushed preparation)"
            elif final_score >= 20:
                interpretation = "Poor timing (insufficient preparation time)"
            else:
                interpretation = "Critical timing (deadline too close)"
            
            # Calculate percentile
            percentile = final_score  # Use score directly as percentile approximation
            
            # Industry benchmark
            benchmark = f"Optimal preparation: {optimal_days} days for this grant type"
            
            return ScoreBreakdown(
                value=final_score,
                calculation=calculation,
                components={
                    "days_available": days_available,
                    "optimal_days": optimal_days,
                    "preparation_adequacy": prep_score,
                    "deadline_competition_factor": competition_factor,
                    "resubmission_factor": resubmission_factor,
                    "concurrent_deadlines": len(concurrent_deadlines),
                    "close_date": close_date,
                    "formula": "Prep_Score × Competition_Factor × Resubmission_Factor"
                },
                interpretation=interpretation,
                percentile=percentile,
                industry_benchmark=benchmark
            )
            
        except Exception as e:
            logger.error(f"Error calculating timing score: {e}")
            return ScoreBreakdown(
                value=50.0,
                calculation="Error in calculation",
                components={"error": str(e)},
                interpretation="Unable to calculate timing score",
                percentile=None,
                industry_benchmark=None
            )