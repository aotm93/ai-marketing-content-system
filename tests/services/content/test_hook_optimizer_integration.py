"""
Integration tests for HookOptimizer with SearchIntentAnalyzer
"""

import pytest
from src.services.content.hook_optimizer import HookOptimizer
from src.models.content_intelligence import ContentTopic, HookType


class TestHookOptimizerIntegration:
    """Test that HookOptimizer uses intent-based titles"""

    def test_generates_intent_based_titles_not_generic(self):
        """Should generate intent-based titles instead of generic templates"""
        optimizer = HookOptimizer()

        topic = ContentTopic(
            title="HDPE cracking in cold weather",
            angle="cold weather prevention",
            hook_type=HookType.PROBLEM,
            industry="plastics",
            target_audience="engineers",
            business_intent=0.8,
            trend_score=0.7,
            competition_score=0.5,
            differentiation_score=0.7,
            brand_alignment_score=0.8,
            value_score=0.75
        )

        titles = optimizer.generate_optimized_titles_sync(topic, count=3)

        # Verify no generic patterns
        for title_obj in titles:
            title = title_obj.title
            assert "What You Need to Know" not in title
            assert "Review" not in title
            assert "Best" not in title or "Best Practices" in title

    def test_problem_solving_intent_generates_specific_title(self):
        """Should detect problem-solving intent and generate specific title"""
        optimizer = HookOptimizer()

        topic = ContentTopic(
            title="preventing HDPE pipe failure",
            angle="failure prevention",
            hook_type=HookType.PROBLEM,
            industry="plastics",
            target_audience="engineers",
            business_intent=0.7,
            trend_score=0.6,
            competition_score=0.4,
            differentiation_score=0.6,
            brand_alignment_score=0.7,
            value_score=0.65
        )

        titles = optimizer.generate_optimized_titles_sync(topic, count=1)
        title = titles[0].title

        # Should be problem-focused, not generic
        assert any(word in title.lower() for word in ["prevent", "failure", "solution", "cause"])
