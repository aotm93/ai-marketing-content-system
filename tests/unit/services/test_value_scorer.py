"""
Unit tests for Value Scorer

Tests the value scoring algorithm and edge cases.
"""

import pytest
from datetime import datetime

from src.services.content_intelligence import ValueScorer
from src.models.content_intelligence import ContentTopic, HookType, ResearchSource


class TestValueScorer:
    """Unit tests for ValueScorer"""
    
    @pytest.fixture
    def scorer(self):
        """Create a ValueScorer instance"""
        return ValueScorer()
    
    @pytest.fixture
    def base_topic(self):
        """Create a base topic for testing"""
        return ContentTopic(
            title="Test Topic",
            angle="Test Angle",
            hook_type=HookType.HOW_TO,
            industry="packaging",
            target_audience="b2b"
        )
    
    def test_perfect_score_calculation(self, scorer, base_topic):
        """Test scoring with perfect metrics"""
        # Arrange
        base_topic.business_intent = 1.0
        base_topic.trend_score = 1.0
        base_topic.competition_score = 0.0  # Lower is better
        base_topic.differentiation_score = 1.0
        base_topic.brand_alignment_score = 1.0
        
        # Act
        score = scorer.score(base_topic)
        
        # Assert - Perfect weighted score
        expected = (1.0 * 0.30 + 1.0 * 0.25 + 1.0 * 0.20 + 1.0 * 0.15 + 1.0 * 0.10)
        assert abs(score - expected) < 0.001
        assert score > 0.95
    
    def test_minimum_score_calculation(self, scorer, base_topic):
        """Test scoring with minimum metrics"""
        # Arrange
        base_topic.business_intent = 0.0
        base_topic.trend_score = 0.0
        base_topic.competition_score = 1.0  # High competition = bad
        base_topic.differentiation_score = 0.0
        base_topic.brand_alignment_score = 0.0
        
        # Act
        score = scorer.score(base_topic)
        
        # Assert - Should be very low
        assert score < 0.1
    
    def test_average_score_calculation(self, scorer, base_topic):
        """Test scoring with average metrics"""
        # Arrange
        base_topic.business_intent = 0.5
        base_topic.trend_score = 0.5
        base_topic.competition_score = 0.5
        base_topic.differentiation_score = 0.5
        base_topic.brand_alignment_score = 0.5
        
        # Act
        score = scorer.score(base_topic)
        
        # Assert - Middle range
        assert 0.4 <= score <= 0.6
    
    def test_high_business_intent_boost(self, scorer, base_topic):
        """Test that high business intent significantly boosts score"""
        # Arrange
        base_topic.business_intent = 1.0  # Max business intent
        base_topic.trend_score = 0.3
        base_topic.competition_score = 0.5
        base_topic.differentiation_score = 0.3
        base_topic.brand_alignment_score = 0.3
        
        # Act
        score = scorer.score(base_topic)
        
        # Assert - Should still be decent due to business intent weight
        assert score > 0.5
    
    def test_high_competition_penalty(self, scorer, base_topic):
        """Test that high competition appropriately penalizes score"""
        # Arrange
        base_topic.business_intent = 0.8
        base_topic.trend_score = 0.8
        base_topic.competition_score = 1.0  # Saturated market
        base_topic.differentiation_score = 0.3
        base_topic.brand_alignment_score = 0.8
        
        # Act
        score = scorer.score(base_topic)
        
        # Assert - Competition penalty should reduce score
        # With high competition, score should be significantly lower
        assert score < 0.75
    
    def test_differentiation_importance(self, scorer, base_topic):
        """Test differentiation impact on score"""
        # Arrange - Two similar topics
        topic_low_diff = ContentTopic(
            title="Low Differentiation",
            angle="Generic",
            hook_type=HookType.HOW_TO,
            industry="packaging",
            target_audience="b2b",
            business_intent=0.7,
            trend_score=0.7,
            competition_score=0.5,
            differentiation_score=0.2,
            brand_alignment_score=0.7
        )
        
        topic_high_diff = ContentTopic(
            title="High Differentiation",
            angle="Unique",
            hook_type=HookType.DATA,
            industry="packaging",
            target_audience="b2b",
            business_intent=0.7,
            trend_score=0.7,
            competition_score=0.5,
            differentiation_score=0.9,
            brand_alignment_score=0.7
        )
        
        # Act
        score_low = scorer.score(topic_low_diff)
        score_high = scorer.score(topic_high_diff)
        
        # Assert
        assert score_high > score_low
        assert (score_high - score_low) > 0.1  # Significant difference
    
    def test_competition_inversion(self, scorer, base_topic):
        """Test that competition score is properly inverted (lower is better)"""
        # Arrange
        base_topic.business_intent = 0.7
        base_topic.trend_score = 0.7
        base_topic.competition_score = 0.2  # Low competition = good
        base_topic.differentiation_score = 0.5
        base_topic.brand_alignment_score = 0.7
        
        # Act
        score = scorer.score(base_topic)
        
        # Assert - With low competition, score should benefit
        # (1 - 0.2) * 0.20 = 0.16 contribution
        assert score > 0.6  # Should be reasonably high
    
    def test_score_bounds(self, scorer, base_topic):
        """Test that scores always stay within 0-1 bounds"""
        # Test various combinations
        test_cases = [
            (0.0, 0.0, 0.0, 0.0, 0.0),
            (1.0, 1.0, 1.0, 1.0, 1.0),
            (0.5, 0.5, 0.5, 0.5, 0.5),
            (0.2, 0.8, 0.3, 0.9, 0.1),
            (0.9, 0.1, 0.8, 0.2, 0.7),
        ]
        
        for bi, ts, cs, ds, bas in test_cases:
            base_topic.business_intent = bi
            base_topic.trend_score = ts
            base_topic.competition_score = cs
            base_topic.differentiation_score = ds
            base_topic.brand_alignment_score = bas
            
            score = scorer.score(base_topic)
            
            assert 0 <= score <= 1, f"Score {score} out of bounds for inputs ({bi}, {ts}, {cs}, {ds}, {bas})"
    
    def test_score_consistency(self, scorer, base_topic):
        """Test that same inputs produce same outputs"""
        # Arrange
        base_topic.business_intent = 0.75
        base_topic.trend_score = 0.65
        base_topic.competition_score = 0.4
        base_topic.differentiation_score = 0.8
        base_topic.brand_alignment_score = 0.7
        
        # Act
        scores = [scorer.score(base_topic) for _ in range(10)]
        
        # Assert - All scores should be identical
        assert all(s == scores[0] for s in scores)
    
    def test_weight_sum(self, scorer):
        """Verify weights sum to 1.0"""
        weights = scorer.weights
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.001, f"Weights sum to {total}, expected 1.0"
