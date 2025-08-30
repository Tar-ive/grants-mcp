"""Unit tests for analytics scoring components."""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from mcp_server.models.grants_schemas import OpportunityV1, OpportunitySummary
from mcp_server.tools.analytics.metrics.competition_metrics import CompetitionIndexCalculator
from mcp_server.tools.analytics.metrics.success_metrics import SuccessProbabilityCalculator
from mcp_server.tools.analytics.metrics.roi_metrics import ROICalculator
from mcp_server.tools.analytics.metrics.timing_metrics import TimingCalculator
from mcp_server.tools.analytics.scoring_engine import GrantScoringEngine


@pytest.fixture
def sample_opportunity():
    """Create a sample grant opportunity for testing."""
    return OpportunityV1(
        opportunity_id="test-123",
        opportunity_number="TEST-2024-001",
        opportunity_title="Test Research Grant",
        opportunity_status="posted",
        agency="NSF",
        agency_code="NSF-BIO",
        agency_name="National Science Foundation",
        summary=OpportunitySummary(
            award_ceiling=500000.0,
            award_floor=100000.0,
            estimated_total_program_funding=2000000.0,
            expected_number_of_awards=4,
            post_date="2024-01-15",
            close_date="2024-06-15",
            summary_description="Research grant for innovative biological studies",
            funding_category="Science/Technology",
            applicant_types=["university", "research institution"]
        )
    )


@pytest.fixture
def user_profile():
    """Create a sample user profile for testing."""
    return {
        "research_keywords": ["biology", "research", "innovation"],
        "research_categories": ["Science/Technology", "Biology"],
        "career_stage": "mid-career",
        "preferred_agencies": ["NSF"],
        "grant_success_rate": 0.3,
        "familiar_agencies": ["NSF", "NIH"]
    }


class TestCompetitionIndexCalculator:
    """Test competition index calculations."""
    
    def setup_method(self):
        self.calculator = CompetitionIndexCalculator()
    
    def test_basic_competition_index_calculation(self):
        """Test basic CI calculation."""
        ci = self.calculator.calculate_basic_competition_index(100, 4)
        assert ci == 2500.0  # (100/4) * 100
        
        # Test edge case
        ci_zero_awards = self.calculator.calculate_basic_competition_index(100, 0)
        assert ci_zero_awards == 100.0  # Maximum competition
    
    def test_application_estimation(self):
        """Test application estimation from funding amounts."""
        estimated_apps = self.calculator.estimate_applications_from_funding(
            award_ceiling=500000.0,
            award_floor=100000.0,
            agency_code="NSF-BIO",
            funding_category="Science/Technology"
        )
        
        assert estimated_apps > 0
        assert isinstance(estimated_apps, int)
    
    def test_weighted_competition_index(self):
        """Test weighted CI calculation."""
        basic_ci = 45.0
        weighted_ci = self.calculator.calculate_weighted_competition_index(
            basic_ci, 500000.0, "NSF-BIO"
        )
        
        assert weighted_ci > 0
        assert weighted_ci != basic_ci  # Should be modified by weights
    
    def test_competition_score_calculation(self, sample_opportunity):
        """Test full competition score calculation."""
        score_breakdown = self.calculator.calculate_competition_score(sample_opportunity)
        
        assert score_breakdown.value >= 0
        assert score_breakdown.value <= 100
        assert "estimated_applications" in score_breakdown.components
        assert score_breakdown.interpretation is not None
        assert score_breakdown.calculation is not None


class TestSuccessProbabilityCalculator:
    """Test success probability calculations."""
    
    def setup_method(self):
        self.calculator = SuccessProbabilityCalculator()
    
    def test_base_success_probability(self):
        """Test base success probability calculation."""
        base_sps = self.calculator.calculate_base_success_probability(4, 100)
        assert base_sps == 4.0  # (4/100) * 100
        
        # Test edge case
        zero_apps = self.calculator.calculate_base_success_probability(4, 0)
        assert zero_apps == 0.0
    
    def test_eligibility_score_calculation(self, sample_opportunity, user_profile):
        """Test eligibility score calculation."""
        eligibility_score = self.calculator.calculate_eligibility_score(
            sample_opportunity, user_profile
        )
        
        assert 0.0 <= eligibility_score <= 1.0
    
    def test_technical_fit_calculation(self, sample_opportunity, user_profile):
        """Test technical fit calculation."""
        fit_score = self.calculator.calculate_technical_fit_score(
            sample_opportunity, user_profile
        )
        
        assert 0.0 <= fit_score <= 1.0
    
    def test_success_probability_score(self, sample_opportunity, user_profile):
        """Test full success probability score calculation."""
        score_breakdown = self.calculator.calculate_success_probability_score(
            sample_opportunity, 100, user_profile
        )
        
        assert score_breakdown.value >= 0
        assert score_breakdown.value <= 100
        assert "base_success_probability" in score_breakdown.components
        assert score_breakdown.interpretation is not None


class TestROICalculator:
    """Test ROI calculations."""
    
    def setup_method(self):
        self.calculator = ROICalculator()
    
    def test_application_cost_estimation(self):
        """Test application cost estimation."""
        cost_dollars, hours_required = self.calculator.estimate_application_cost(
            award_ceiling=500000.0,
            award_floor=100000.0,
            agency_code="NSF-BIO"
        )
        
        assert cost_dollars > 0
        assert hours_required > 0
        assert isinstance(hours_required, int)
    
    def test_basic_roi_calculation(self):
        """Test basic ROI calculation."""
        roi = self.calculator.calculate_basic_roi(500000.0, 10000.0)
        expected_roi = ((500000 - 10000) / 10000) * 100
        assert roi == expected_roi
    
    def test_roi_score_calculation(self, sample_opportunity, user_profile):
        """Test full ROI score calculation."""
        score_breakdown = self.calculator.calculate_roi_score(
            sample_opportunity, 25.0, user_profile
        )
        
        assert score_breakdown.value >= 0
        assert score_breakdown.value <= 100
        assert "award_amount" in score_breakdown.components
        assert score_breakdown.interpretation is not None


class TestTimingCalculator:
    """Test timing calculations."""
    
    def setup_method(self):
        self.calculator = TimingCalculator()
    
    def test_deadline_parsing(self):
        """Test various deadline formats."""
        # Test ISO format
        deadline = self.calculator.parse_deadline("2024-06-15")
        assert deadline is not None
        assert deadline.year == 2024
        assert deadline.month == 6
        assert deadline.day == 15
        
        # Test with time
        deadline_with_time = self.calculator.parse_deadline("2024-06-15T23:59:59")
        assert deadline_with_time is not None
        
        # Test invalid format
        invalid = self.calculator.parse_deadline("invalid-date")
        assert invalid is None
    
    def test_optimal_preparation_days(self):
        """Test optimal preparation time calculation."""
        optimal_days = self.calculator.get_optimal_preparation_days(
            award_ceiling=500000.0,
            agency_code="NSF-BIO"
        )
        
        assert optimal_days > 0
        assert isinstance(optimal_days, int)
    
    def test_preparation_adequacy_score(self):
        """Test preparation adequacy scoring."""
        # Adequate time
        score_adequate = self.calculator.calculate_preparation_adequacy_score(90, 60)
        assert score_adequate > 80
        
        # Insufficient time
        score_tight = self.calculator.calculate_preparation_adequacy_score(30, 90)
        assert score_tight < 50
        
        # Unknown deadline
        score_unknown = self.calculator.calculate_preparation_adequacy_score(None, 60)
        assert score_unknown == 50.0
    
    def test_timing_score_calculation(self, sample_opportunity, user_profile):
        """Test full timing score calculation."""
        score_breakdown = self.calculator.calculate_timing_score(
            sample_opportunity, user_profile
        )
        
        assert score_breakdown.value >= 0
        assert score_breakdown.value <= 100
        assert "close_date" in score_breakdown.components
        assert score_breakdown.interpretation is not None


class TestGrantScoringEngine:
    """Test the main scoring engine."""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        db_manager = AsyncMock()
        db_manager.get_grant_score = AsyncMock(return_value=None)
        db_manager.store_grant_score = AsyncMock(return_value=True)
        return db_manager
    
    def setup_method(self):
        self.scoring_engine = GrantScoringEngine()
    
    def test_custom_weights_default(self):
        """Test default weight calculation."""
        weights = self.scoring_engine.get_custom_weights()
        
        assert abs(sum(weights.values()) - 1.0) < 0.01  # Should sum to 1.0
        assert all(0 <= weight <= 1 for weight in weights.values())
        assert 'technical_fit' in weights
        assert 'competition' in weights
        assert 'roi' in weights
        assert 'timing' in weights
        assert 'success_probability' in weights
    
    def test_custom_weights_with_profile(self, user_profile):
        """Test weight calculation with user profile."""
        weights = self.scoring_engine.get_custom_weights(user_profile)
        
        assert abs(sum(weights.values()) - 1.0) < 0.01  # Should still sum to 1.0
        assert all(0 <= weight <= 1 for weight in weights.values())
    
    def test_recommendation_generation(self, sample_opportunity):
        """Test recommendation generation."""
        component_scores = {
            'technical_fit': 85.0,
            'competition': 45.0,
            'roi': 70.0,
            'timing': 60.0,
            'success_probability': 75.0
        }
        
        recommendation = self.scoring_engine.generate_recommendation(
            sample_opportunity, 67.0, component_scores
        )
        
        assert isinstance(recommendation, str)
        assert len(recommendation) > 0
        assert "RECOMMENDED" in recommendation or "PRIORITY" in recommendation or "CONDITIONAL" in recommendation
    
    @pytest.mark.asyncio
    async def test_single_opportunity_scoring(self, sample_opportunity, user_profile, mock_db_manager):
        """Test scoring a single opportunity."""
        self.scoring_engine.db_manager = mock_db_manager
        
        grant_score = await self.scoring_engine.score_single_opportunity(
            sample_opportunity, user_profile, use_cache=False
        )
        
        assert grant_score.opportunity_id == sample_opportunity.opportunity_id
        assert grant_score.opportunity_title == sample_opportunity.opportunity_title
        assert 0 <= grant_score.overall_score <= 100
        assert grant_score.technical_fit_score.value >= 0
        assert grant_score.competition_index.value >= 0
        assert grant_score.roi_score.value >= 0
        assert grant_score.timing_score.value >= 0
        assert grant_score.success_probability.value >= 0
        assert grant_score.recommendation is not None
    
    @pytest.mark.asyncio
    async def test_batch_scoring(self, sample_opportunity, user_profile, mock_db_manager):
        """Test batch scoring of opportunities."""
        self.scoring_engine.db_manager = mock_db_manager
        
        opportunities = [sample_opportunity]
        
        batch_result = await self.scoring_engine.batch_score_opportunities(
            opportunities, user_profile, include_hidden=True
        )
        
        assert batch_result.total_opportunities == 1
        assert len(batch_result.scores) <= 1
        assert batch_result.scoring_time_ms > 0
        assert isinstance(batch_result.cache_hit_rate, float)


@pytest.mark.asyncio
async def test_database_integration():
    """Test database integration components."""
    from mcp_server.tools.analytics.database.session_manager import AsyncSQLiteManager
    
    # Test database initialization
    db_manager = AsyncSQLiteManager(":memory:")  # Use in-memory DB for testing
    await db_manager.initialize()
    
    # Test storing and retrieving grant score
    stored = await db_manager.store_grant_score(
        "test-123",
        "Test Grant",
        75.5,
        {"technical_fit": 80.0, "competition": 70.0},
        {"test": "data"},
        "Good opportunity"
    )
    assert stored is True
    
    # Test retrieving score
    retrieved = await db_manager.get_grant_score("test-123", max_age_hours=24)
    assert retrieved is not None
    assert retrieved["opportunity_id"] == "test-123"
    assert retrieved["overall_score"] == 75.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])