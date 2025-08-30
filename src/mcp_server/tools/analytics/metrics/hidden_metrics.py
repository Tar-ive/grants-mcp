"""Hidden Opportunity Score calculations for undersubscribed grant detection."""

import logging
import math
from typing import Dict, List, Optional, Tuple
import numpy as np

from mcp_server.models.grants_schemas import OpportunityV1
from mcp_server.models.analytics_schemas import ScoreBreakdown, IndustryConstants, HiddenOpportunityScore

logger = logging.getLogger(__name__)


class HiddenOpportunityCalculator:
    """
    Calculate Hidden Opportunity Scores for identifying undersubscribed grants.
    
    Identifies grants that may have lower competition due to visibility,
    timing, or cross-category factors.
    """
    
    def __init__(self):
        self.constants = IndustryConstants()
    
    def calculate_visibility_index(
        self,
        opportunity: OpportunityV1,
        search_context: Optional[Dict] = None
    ) -> Tuple[float, Dict]:
        """
        Calculate how visible/discoverable this opportunity is.
        
        Lower visibility = higher hidden opportunity potential
        
        Args:
            opportunity: Grant opportunity
            search_context: Context about how this was found
            
        Returns:
            Tuple of (visibility_score, components)
        """
        visibility_factors = {
            'search_position': 50.0,  # Default middle position
            'title_clarity': 50.0,    # How clear the title is
            'category_specificity': 50.0,  # How specific the category is
            'keyword_density': 50.0,  # How many common keywords it has
        }
        
        # Search position factor (if available)
        if search_context and 'search_position' in search_context:
            position = search_context['search_position']
            # Higher position = higher visibility (lower hidden score)
            visibility_factors['search_position'] = min(100, position * 10)
        
        # Title clarity analysis
        title = opportunity.opportunity_title.lower()
        
        # Check for vague or overly technical titles
        vague_indicators = ['various', 'multiple', 'miscellaneous', 'other', 'general']
        technical_indicators = ['advanced', 'specialized', 'innovative', 'novel']
        
        if any(word in title for word in vague_indicators):
            visibility_factors['title_clarity'] = 30.0  # Vague = less visible
        elif any(word in title for word in technical_indicators):
            visibility_factors['title_clarity'] = 60.0  # Technical = moderately visible
        else:
            visibility_factors['title_clarity'] = 70.0  # Clear = more visible
        
        # Category specificity
        category = opportunity.summary.funding_category or "General"
        
        if category.lower() in ['general', 'other', 'miscellaneous']:
            visibility_factors['category_specificity'] = 20.0  # Very general = low visibility
        elif len(category.split()) > 3:
            visibility_factors['category_specificity'] = 40.0  # Very specific = lower visibility
        else:
            visibility_factors['category_specificity'] = 70.0  # Moderately specific = higher visibility
        
        # Keyword density analysis
        description = (opportunity.summary.summary_description or "").lower()
        common_grant_keywords = [
            'research', 'development', 'innovation', 'technology', 'science',
            'education', 'training', 'program', 'project', 'study'
        ]
        
        keyword_count = sum(1 for keyword in common_grant_keywords if keyword in title or keyword in description)
        visibility_factors['keyword_density'] = min(100, keyword_count * 20)
        
        # Calculate weighted visibility index
        weights = {
            'search_position': 0.3,
            'title_clarity': 0.3,
            'category_specificity': 0.2,
            'keyword_density': 0.2
        }
        
        visibility_index = sum(
            visibility_factors[factor] * weights[factor] 
            for factor in visibility_factors
        )
        
        return visibility_index, visibility_factors
    
    def calculate_undersubscription_score(
        self,
        opportunity: OpportunityV1,
        historical_data: Optional[Dict] = None
    ) -> Tuple[float, Dict]:
        """
        Calculate undersubscription score based on application patterns.
        
        Args:
            opportunity: Grant opportunity
            historical_data: Historical application data if available
            
        Returns:
            Tuple of (undersubscription_score, components)
        """
        components = {
            'awards_to_funding_ratio': 50.0,
            'agency_competition_level': 50.0,
            'award_size_appeal': 50.0,
            'deadline_advantage': 50.0,
        }
        
        # Awards to funding ratio analysis
        awards = opportunity.summary.expected_number_of_awards or 1
        total_funding = opportunity.summary.estimated_total_program_funding
        award_ceiling = opportunity.summary.award_ceiling
        
        if total_funding and award_ceiling:
            implied_awards = total_funding / award_ceiling
            if implied_awards > awards:
                # More funding available than expected awards suggests undersubscription
                components['awards_to_funding_ratio'] = min(100, (implied_awards / awards) * 50)
            else:
                components['awards_to_funding_ratio'] = 30.0
        
        # Agency competition level
        agency_code = opportunity.agency_code
        main_agency = agency_code.split('-')[0] if agency_code else 'OTHER'
        
        # Less competitive agencies score higher for undersubscription
        agency_competition = {
            'NIH': 20.0,     # Very competitive
            'NSF': 25.0,     # Very competitive
            'DOE': 40.0,     # Moderately competitive
            'NASA': 35.0,    # Moderately competitive
            'DOD': 50.0,     # Less competitive (more specialized)
            'EPA': 60.0,     # Less competitive
            'USDA': 65.0,    # Less competitive
            'DOT': 70.0,     # Less competitive
            'HHS': 30.0,     # Competitive (includes NIH)
        }
        
        components['agency_competition_level'] = agency_competition.get(main_agency, 50.0)
        
        # Award size appeal analysis
        if award_ceiling:
            if award_ceiling < 50000:
                # Small awards may be undersubscribed (not worth the effort for many)
                components['award_size_appeal'] = 70.0
            elif award_ceiling > 2000000:
                # Very large awards may be undersubscribed (too intimidating)
                components['award_size_appeal'] = 60.0
            elif 100000 <= award_ceiling <= 500000:
                # Sweet spot - likely well-subscribed
                components['award_size_appeal'] = 20.0
            else:
                components['award_size_appeal'] = 40.0
        
        # Deadline advantage analysis
        close_date = opportunity.summary.close_date
        if close_date:
            # Parse deadline to assess timing advantage
            try:
                from datetime import datetime
                deadline = datetime.strptime(close_date.split('T')[0], "%Y-%m-%d")
                now = datetime.utcnow()
                days_until = (deadline - now).days
                
                if days_until < 30:
                    # Very short deadline = potential undersubscription
                    components['deadline_advantage'] = 80.0
                elif days_until > 180:
                    # Very long deadline = more competition likely
                    components['deadline_advantage'] = 30.0
                else:
                    components['deadline_advantage'] = 50.0
                    
            except (ValueError, AttributeError):
                components['deadline_advantage'] = 50.0
        
        # Calculate weighted undersubscription score
        weights = {
            'awards_to_funding_ratio': 0.3,
            'agency_competition_level': 0.3,
            'award_size_appeal': 0.2,
            'deadline_advantage': 0.2
        }
        
        undersubscription_score = sum(
            components[factor] * weights[factor] 
            for factor in components
        )
        
        return undersubscription_score, components
    
    def calculate_cross_category_score(
        self,
        opportunity: OpportunityV1,
        user_profile: Optional[Dict] = None
    ) -> Tuple[float, Dict]:
        """
        Calculate cross-category matching potential.
        
        Args:
            opportunity: Grant opportunity
            user_profile: User research profile
            
        Returns:
            Tuple of (cross_category_score, components)
        """
        components = {
            'category_breadth': 50.0,
            'interdisciplinary_keywords': 50.0,
            'user_profile_match': 50.0,
            'novel_combination': 50.0
        }
        
        # Category breadth analysis
        category = opportunity.summary.funding_category or ""
        title = opportunity.opportunity_title
        description = opportunity.summary.summary_description or ""
        
        # Look for interdisciplinary indicators
        interdisciplinary_terms = [
            'interdisciplinary', 'multidisciplinary', 'cross-cutting', 'integrated',
            'collaborative', 'partnership', 'consortium', 'multi-sector'
        ]
        
        all_text = (category + " " + title + " " + description).lower()
        
        interdisciplinary_count = sum(1 for term in interdisciplinary_terms if term in all_text)
        components['interdisciplinary_keywords'] = min(100, interdisciplinary_count * 30)
        
        # Category breadth (multiple categories mentioned)
        category_keywords = [
            'health', 'education', 'technology', 'environment', 'energy',
            'agriculture', 'transportation', 'security', 'economics', 'social'
        ]
        
        category_count = sum(1 for cat in category_keywords if cat in all_text)
        if category_count >= 3:
            components['category_breadth'] = 80.0  # High cross-category potential
        elif category_count >= 2:
            components['category_breadth'] = 60.0
        else:
            components['category_breadth'] = 30.0
        
        # User profile cross-category match
        if user_profile:
            user_categories = user_profile.get('research_categories', [])
            user_keywords = user_profile.get('research_keywords', [])
            
            # Check if user's background spans multiple categories relevant to this grant
            relevant_categories = 0
            for user_cat in user_categories:
                if any(keyword in all_text for keyword in user_cat.lower().split()):
                    relevant_categories += 1
            
            if relevant_categories >= 2:
                components['user_profile_match'] = 80.0
            elif relevant_categories == 1:
                components['user_profile_match'] = 40.0
            else:
                components['user_profile_match'] = 20.0
        
        # Novel combination detection
        # Look for unusual combinations of terms
        unusual_combinations = [
            ('art', 'technology'), ('social', 'engineering'), ('health', 'economics'),
            ('education', 'manufacturing'), ('agriculture', 'artificial intelligence'),
            ('environment', 'business'), ('security', 'social science')
        ]
        
        combination_score = 0
        for term1, term2 in unusual_combinations:
            if term1 in all_text and term2 in all_text:
                combination_score += 20
        
        components['novel_combination'] = min(80, combination_score)
        
        # Calculate weighted cross-category score
        weights = {
            'category_breadth': 0.3,
            'interdisciplinary_keywords': 0.3,
            'user_profile_match': 0.2,
            'novel_combination': 0.2
        }
        
        cross_category_score = sum(
            components[factor] * weights[factor] 
            for factor in components
        )
        
        return cross_category_score, components
    
    def identify_opportunity_type(
        self,
        visibility_index: float,
        undersubscription_score: float,
        cross_category_score: float
    ) -> str:
        """
        Classify the type of hidden opportunity.
        
        Args:
            visibility_index: Visibility score (0-100)
            undersubscription_score: Undersubscription score (0-100)
            cross_category_score: Cross-category score (0-100)
            
        Returns:
            Opportunity type classification
        """
        # Low visibility = hidden gem
        if visibility_index < 40:
            if undersubscription_score > 60:
                return "Hidden Gem (Low Visibility + Undersubscribed)"
            else:
                return "Overlooked Opportunity (Low Visibility)"
        
        # High undersubscription = niche opportunity
        if undersubscription_score > 70:
            return "Niche Opportunity (Undersubscribed)"
        
        # High cross-category = interdisciplinary opportunity
        if cross_category_score > 70:
            return "Interdisciplinary Opportunity (Cross-Category Match)"
        
        # Moderate scores across multiple dimensions
        if (visibility_index < 60 and undersubscription_score > 50 and cross_category_score > 50):
            return "Multi-Factor Hidden Opportunity"
        
        return "Potential Hidden Opportunity"
    
    def generate_discovery_reason(
        self,
        components: Dict,
        opportunity_type: str,
        visibility_components: Dict,
        undersubscription_components: Dict,
        cross_category_components: Dict
    ) -> str:
        """
        Generate explanation for why this is flagged as a hidden opportunity.
        
        Args:
            components: Overall score components
            opportunity_type: Type of opportunity
            visibility_components: Visibility analysis components
            undersubscription_components: Undersubscription components  
            cross_category_components: Cross-category components
            
        Returns:
            Human-readable discovery reason
        """
        reasons = []
        
        # Visibility factors
        if visibility_components['title_clarity'] < 40:
            reasons.append("vague or technical title reducing discoverability")
        
        if visibility_components['category_specificity'] < 40:
            reasons.append("highly specific category limiting exposure")
        
        # Undersubscription factors
        if undersubscription_components['award_size_appeal'] > 60:
            reasons.append("award size may discourage some applicants")
        
        if undersubscription_components['deadline_advantage'] > 70:
            reasons.append("tight deadline creating timing advantage")
        
        if undersubscription_components['agency_competition_level'] > 60:
            reasons.append("less competitive agency with specialized focus")
        
        # Cross-category factors
        if cross_category_components['interdisciplinary_keywords'] > 60:
            reasons.append("interdisciplinary nature may limit traditional applicant pool")
        
        if cross_category_components['novel_combination'] > 50:
            reasons.append("unique combination of fields creating niche opportunity")
        
        if not reasons:
            reasons.append("multiple moderate factors combine to suggest reduced competition")
        
        return "Identified due to: " + "; ".join(reasons)
    
    def calculate_hidden_opportunity_score(
        self,
        opportunity: OpportunityV1,
        user_profile: Optional[Dict] = None,
        search_context: Optional[Dict] = None
    ) -> HiddenOpportunityScore:
        """
        Calculate comprehensive Hidden Opportunity Score.
        
        Args:
            opportunity: Grant opportunity to analyze
            user_profile: User research profile (optional)
            search_context: Search context information (optional)
            
        Returns:
            HiddenOpportunityScore with analysis breakdown
        """
        try:
            # Calculate component scores
            visibility_index, visibility_components = self.calculate_visibility_index(
                opportunity, search_context
            )
            
            undersubscription_score, undersubscription_components = self.calculate_undersubscription_score(
                opportunity
            )
            
            cross_category_score, cross_category_components = self.calculate_cross_category_score(
                opportunity, user_profile
            )
            
            # Calculate final Hidden Opportunity Score using weights from constants
            final_score = (
                undersubscription_score * self.constants.UNDERSUBSCRIPTION_WEIGHT +
                (100 - visibility_index) * self.constants.VISIBILITY_WEIGHT +  # Invert visibility
                cross_category_score * self.constants.CROSS_CATEGORY_WEIGHT
            )
            
            # Identify opportunity type
            opportunity_type = self.identify_opportunity_type(
                visibility_index, undersubscription_score, cross_category_score
            )
            
            # Generate discovery reason
            discovery_reason = self.generate_discovery_reason(
                {
                    'visibility_index': visibility_index,
                    'undersubscription_score': undersubscription_score,
                    'cross_category_score': cross_category_score
                },
                opportunity_type,
                visibility_components,
                undersubscription_components,
                cross_category_components
            )
            
            # Create detailed score breakdowns
            visibility_breakdown = ScoreBreakdown(
                value=100 - visibility_index,  # Invert for hidden opportunity context
                calculation=f"Hidden Visibility = 100 - {visibility_index:.1f} = {100 - visibility_index:.1f}",
                components=visibility_components,
                interpretation="Lower visibility = higher hidden opportunity potential",
                percentile=None,
                industry_benchmark="Typical grant visibility: 60-80"
            )
            
            undersubscription_breakdown = ScoreBreakdown(
                value=undersubscription_score,
                calculation=f"Undersubscription factors combined = {undersubscription_score:.1f}",
                components=undersubscription_components,
                interpretation="Higher score indicates likely undersubscription",
                percentile=None,
                industry_benchmark="Average competition varies by agency"
            )
            
            cross_category_breakdown = ScoreBreakdown(
                value=cross_category_score,
                calculation=f"Cross-category potential = {cross_category_score:.1f}",
                components=cross_category_components,
                interpretation="Higher score indicates interdisciplinary opportunity",
                percentile=None,
                industry_benchmark="Most grants are single-discipline focused"
            )
            
            return HiddenOpportunityScore(
                opportunity_id=opportunity.opportunity_id,
                opportunity_title=opportunity.opportunity_title,
                visibility_index=visibility_breakdown,
                undersubscription_score=undersubscription_breakdown,
                cross_category_score=cross_category_breakdown,
                hidden_opportunity_score=final_score,
                opportunity_type=opportunity_type,
                discovery_reason=discovery_reason
            )
            
        except Exception as e:
            logger.error(f"Error calculating hidden opportunity score: {e}")
            
            # Return neutral score on error
            neutral_breakdown = ScoreBreakdown(
                value=0.0,
                calculation="Error in calculation",
                components={"error": str(e)},
                interpretation="Unable to analyze hidden opportunity potential",
                percentile=None,
                industry_benchmark=None
            )
            
            return HiddenOpportunityScore(
                opportunity_id=opportunity.opportunity_id,
                opportunity_title=opportunity.opportunity_title,
                visibility_index=neutral_breakdown,
                undersubscription_score=neutral_breakdown,
                cross_category_score=neutral_breakdown,
                hidden_opportunity_score=0.0,
                opportunity_type="Analysis Error",
                discovery_reason=f"Error in analysis: {str(e)}"
            )