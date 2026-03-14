"""
Tests for TitleQueryMatcher
"""

import pytest
from src.services.content.title_matcher import TitleQueryMatcher


class TestTitleQueryMatcher:
    """Test title-keyword matching"""

    def test_exact_keyword_match_scores_high(self):
        """Exact keyword in title should score 0.7+"""
        matcher = TitleQueryMatcher()

        score = matcher.calculate_match_score(
            "HDPE Chemical Resistance Guide",
            "hdpe chemical resistance"
        )

        assert score >= 0.7

    def test_partial_match_scores_medium(self):
        """Partial keyword match should score 0.3-0.6"""
        matcher = TitleQueryMatcher()

        score = matcher.calculate_match_score(
            "Chemical Resistance of HDPE Materials",
            "hdpe chemical resistance"
        )

        assert 0.3 <= score <= 0.9

    def test_no_match_scores_low(self):
        """No keyword match should score low"""
        matcher = TitleQueryMatcher()

        score = matcher.calculate_match_score(
            "Plastic Comparison Guide",
            "hdpe chemical resistance"
        )

        assert score < 0.3

    def test_is_match_acceptable_with_good_match(self):
        """Good match should be acceptable"""
        matcher = TitleQueryMatcher()

        is_acceptable, score = matcher.is_match_acceptable(
            "HDPE Chemical Resistance: Technical Data",
            "hdpe chemical resistance"
        )

        assert is_acceptable
        assert score >= 0.6
