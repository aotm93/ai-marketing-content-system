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

    def test_buying_keyword_keeps_query_context(self):
        """Should not fall back to generic data-style titles for supplier queries"""
        optimizer = HookOptimizer()

        topic = ContentTopic(
            title="plastic bottles wholesale supplier",
            angle="supplier selection for bulk orders",
            hook_type=HookType.DATA,
            industry="packaging",
            target_audience="b2b buyers",
            business_intent=0.85,
            trend_score=0.6,
            competition_score=0.5,
            differentiation_score=0.7,
            brand_alignment_score=0.8,
            value_score=0.78
        )

        titles = optimizer.generate_optimized_titles_sync(
            topic,
            count=5,
            catalog_context={
                "page_type": "wholesale_faq",
                "target_category_name": "Plastic Bottles",
                "supporting_products": [
                    {
                        "name": "500ml PET Plastic Bottle",
                        "capacity": "500ml",
                        "material": "PET",
                        "closure_type": "Screw Cap",
                    }
                ],
                "decision_questions": [
                    "What MOQ, lead time, and certifications matter when choosing a plastic bottles wholesale supplier?"
                ],
            }
        )
        best = next(title for title in titles if title.hook_type == HookType.DATA)

        assert "data-driven insights" not in best.title.lower()
        assert "plastic bottles wholesale supplier" in best.title.lower()
        assert any(term in best.title.lower() for term in ["moq", "lead time", "certification", "buyer"])
