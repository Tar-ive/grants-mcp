"""Success Probability Score calculations adapted from NSF percentile methodology."""

import logging
import math
from typing import Dict, List, Optional, Tuple
import numpy as np

from mcp_server.models.grants_schemas import OpportunityV1
from mcp_server.models.analytics_schemas import ScoreBreakdown, IndustryConstants

logger = logging.getLogger(__name__)


class SuccessProbabilityCalculator:
    """
    Calculate Success Probability Score using NSF percentile methodology.
    
    Estimates the likelihood of success for a grant application based on
    historical data, eligibility fit, and technical alignment.
    """
    
    def __init__(self):
        self.constants = IndustryConstants()
    
    def calculate_base_success_probability(
        self,
        number_of_awards: int,
        estimated_applications: int
    ) -> float:
        """
        Calculate base success probability.
        
        Formula: Base_SPS = (Number_of_Awards / Expected_Applications) * 100
        
        Args:
            number_of_awards: Number of awards to be made
            estimated_applications: Estimated number of applications
            
        Returns:
            Base success probability (0-100)
        """
        if estimated_applications <= 0:
            return 0.0
        
        return min(100.0, (number_of_awards / estimated_applications) * 100)
    
    def calculate_eligibility_score(
        self,
        opportunity: OpportunityV1,
        user_profile: Optional[Dict] = None
    ) -> float:
        """
        Calculate eligibility alignment score.
        
        Args:
            opportunity: Grant opportunity
            user_profile: User research profile (optional)
            
        Returns:
            Eligibility score (0.0-1.0)
        """
        eligibility_score = 1.0  # Default to fully eligible
        
        # Check applicant types if user profile provided
        if user_profile and opportunity.summary.applicant_types:
            user_type = user_profile.get('applicant_type', 'university')
            applicant_types = [t.lower() for t in opportunity.summary.applicant_types]
            
            # Common type mappings
            type_matches = {
                'university': ['university', 'college', 'academic', 'education'],
                'nonprofit': ['nonprofit', 'non-profit', 'foundation'],
                'government': ['government', 'federal', 'state', 'local'],
                'industry': ['industry', 'business', 'commercial', 'for-profit'],
                'individual': ['individual', 'person', 'researcher']
            }
            
            matches = type_matches.get(user_type.lower(), [user_type.lower()])
            is_eligible = any(match in ' '.join(applicant_types) for match in matches)
            
            if not is_eligible:
                eligibility_score *= 0.3  # Significant penalty for type mismatch
        
        # Additional eligibility checks could be added here
        # (e.g., geographic restrictions, organizational size, etc.)
        
        return eligibility_score
    
    def calculate_technical_fit_score(
        self,
        opportunity: OpportunityV1,
        user_profile: Optional[Dict] = None
    ) -> float:
        """
        Calculate technical fit score based on keywords and categories.
        
        Args:
            opportunity: Grant opportunity
            user_profile: User research profile with keywords/expertise
            
        Returns:
            Technical fit score (0.0-1.0)
        """
        fit_score = 0.5  # Default neutral fit
        
        if not user_profile:
            return fit_score
        
        user_keywords = user_profile.get('research_keywords', [])
        user_categories = user_profile.get('research_categories', [])
        
        if not user_keywords and not user_categories:
            return fit_score
        
        # Combine grant text for keyword matching
        grant_text_parts = [
            opportunity.opportunity_title,
            opportunity.summary.summary_description or '',
            opportunity.summary.funding_category or '',
            opportunity.category or ''
        ]
        grant_text = ' '.join(filter(None, grant_text_parts)).lower()
        
        # Keyword matching
        keyword_matches = 0
        total_keywords = len(user_keywords)
        
        if total_keywords > 0:
            for keyword in user_keywords:
                if keyword.lower() in grant_text:
                    keyword_matches += 1
            
            keyword_score = keyword_matches / total_keywords
        else:
            keyword_score = 0.5  # Neutral if no keywords provided
        
        # Category alignment
        category_score = 0.5  # Default neutral
        
        if user_categories and opportunity.summary.funding_category:
            grant_category = opportunity.summary.funding_category.lower()
            
            for user_cat in user_categories:
                if user_cat.lower() in grant_category or grant_category in user_cat.lower():
                    category_score = 1.0
                    break
                # Partial matches
                elif any(word in grant_category for word in user_cat.lower().split()):
                    category_score = max(category_score, 0.7)
        
        # Agency focus alignment
        agency_score = 0.5  # Default neutral
        
        user_agencies = user_profile.get('preferred_agencies', [])
        if user_agencies:
            user_agency_codes = [a.upper() for a in user_agencies]
            if any(code in opportunity.agency_code for code in user_agency_codes):
                agency_score = 1.0
        
        # Combined technical fit (weighted average)
        fit_score = (keyword_score * 0.5 + category_score * 0.3 + agency_score * 0.2)
        
        return max(0.0, min(1.0, fit_score))
    
    def get_past_success_modifier(
        self,
        agency_code: str,
        user_profile: Optional[Dict] = None
    ) -> float:
        """
        Calculate past success modifier based on agency and user history.
        
        Args:
            agency_code: Agency code
            user_profile: User profile with grant history
            
        Returns:
            Success modifier (0.5-2.0)
        """
        modifier = 1.0  # Default neutral
        
        # Agency success rate modifiers (based on industry data)
        agency_success_rates = {
            'NIH': 0.20,    # 20% average
            'NSF': 0.25,    # 25% average  
            'DOE': 0.30,    # 30% average
            'DOD': 0.35,    # 35% average
            'NASA': 0.28,   # 28% average
            'EPA': 0.32,    # 32% average
            'USDA': 0.35,   # 35% average
        }
        
        main_agency = agency_code.split('-')[0] if agency_code else 'OTHER'
        agency_rate = agency_success_rates.get(main_agency, 0.25)
        
        # Modifier based on agency success rate relative to baseline (20%)
        modifier = math.sqrt(agency_rate / self.constants.NIH_AVERAGE_SUCCESS_RATE)
        
        # User-specific history modifier
        if user_profile:
            user_success_rate = user_profile.get('grant_success_rate')
            if user_success_rate is not None:
                # Boost modifier for users with good track record
                if user_success_rate > 0.3:
                    modifier *= 1.2
                elif user_success_rate < 0.1:
                    modifier *= 0.8
        
        return max(0.5, min(2.0, modifier))
    
    def calculate_success_probability_score(
        self,
        opportunity: OpportunityV1,
        estimated_applications: int,
        user_profile: Optional[Dict] = None
    ) -> ScoreBreakdown:
        """
        Calculate comprehensive Success Probability Score.
        
        Args:
            opportunity: Grant opportunity to score
            estimated_applications: Estimated number of applications
            user_profile: User research profile (optional)
            
        Returns:
            ScoreBreakdown with transparent calculation
        """
        try:
            # Extract key information
            awards = opportunity.summary.expected_number_of_awards or 1
            agency = opportunity.agency_code
            
            # Calculate base success probability
            base_sps = self.calculate_base_success_probability(awards, estimated_applications)
            
            # Calculate adjustment factors
            eligibility_score = self.calculate_eligibility_score(opportunity, user_profile)
            technical_fit_score = self.calculate_technical_fit_score(opportunity, user_profile)
            past_success_modifier = self.get_past_success_modifier(agency, user_profile)
            
            # Calculate adjusted success probability
            adjusted_sps = base_sps * eligibility_score * technical_fit_score * past_success_modifier
            
            # Ensure reasonable bounds
            final_score = max(1.0, min(90.0, adjusted_sps))
            
            # Build calculation explanation
            calculation_parts = [
                f"Base: {base_sps:.1f}%",
                f"× Eligibility: {eligibility_score:.2f}",
                f"× Technical Fit: {technical_fit_score:.2f}",
                f"× Success History: {past_success_modifier:.2f}",
                f"= {final_score:.1f}%"
            ]
            calculation = " ".join(calculation_parts)
            
            # Interpret the score
            if final_score >= 40:
                interpretation = "High success probability (excellent fit)"
            elif final_score >= 25:
                interpretation = "Good success probability (strong candidate)"
            elif final_score >= 15:
                interpretation = "Moderate success probability (worth pursuing)"
            elif final_score >= 8:
                interpretation = "Low success probability (challenging)"
            else:
                interpretation = "Very low success probability (high risk)"
            
            # Industry benchmark
            main_agency = agency.split('-')[0] if agency else 'OTHER'
            if main_agency in ['NIH', 'NSF']:
                benchmark = f"{main_agency} average: {self.constants.NIH_AVERAGE_SUCCESS_RATE * 100:.0f}%"
            else:
                benchmark = f"Industry average: {self.constants.NIH_AVERAGE_SUCCESS_RATE * 100:.0f}%"
            
            # Calculate percentile (higher success rate = higher percentile)
            percentile = min(99, max(1, (final_score / 40.0) * 100))  # Scale to percentile
            
            return ScoreBreakdown(
                value=final_score,
                calculation=calculation,
                components={
                    "base_success_probability": base_sps,
                    "eligibility_score": eligibility_score,
                    "technical_fit_score": technical_fit_score,
                    "past_success_modifier": past_success_modifier,
                    "adjusted_probability": adjusted_sps,
                    "number_of_awards": awards,
                    "estimated_applications": estimated_applications,
                    "formula": "Base × Eligibility × Technical_Fit × Success_History"
                },
                interpretation=interpretation,
                percentile=percentile,
                industry_benchmark=benchmark
            )
            
        except Exception as e:
            logger.error(f"Error calculating success probability score: {e}")
            return ScoreBreakdown(
                value=20.0,
                calculation="Error in calculation",
                components={"error": str(e)},
                interpretation="Unable to calculate success probability",
                percentile=None,
                industry_benchmark=None
            )