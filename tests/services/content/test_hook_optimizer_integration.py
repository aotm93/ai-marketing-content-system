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

    def test_catalog_title_is_trimmed_for_seo_and_repetition(self):
        """Long repetitive product queries should be compacted to SEO-safe titles."""
        optimizer = HookOptimizer()

        topic = ContentTopic(
            title="30ml PET 30ml 60ml 100ml white black pump white lid plastic foam bottle empty shampoo container wholesale",
            angle="supplier comparison",
            hook_type=HookType.DATA,
            industry="packaging",
            target_audience="b2b buyers",
            business_intent=0.9,
            trend_score=0.6,
            competition_score=0.4,
            differentiation_score=0.8,
            brand_alignment_score=0.8,
            value_score=0.82,
        )

        titles = optimizer.generate_optimized_titles_sync(
            topic,
            count=3,
            catalog_context={
                "page_type": "wholesale_faq",
                "decision_questions": ["What MOQ and lead time should buyers compare?"],
            },
        )
        best = next(title for title in titles if title.hook_type == HookType.DATA)

        assert len(best.title) <= 68
        assert best.title.lower().count("30ml") <= 1
        assert "moq" in best.title.lower()
        assert "lead time" in best.title.lower()

    def test_catalog_title_compaction_preserves_hook_specific_tails(self):
        """Long commercial titles should not collapse different hooks into the same truncated string."""
        optimizer = HookOptimizer()

        topic = ContentTopic(
            title="30ml PET 30ml 60ml 100ml white black pump white lid plastic foam bottle empty shampoo container wholesale",
            angle="supplier comparison",
            hook_type=HookType.DATA,
            industry="packaging",
            target_audience="b2b buyers",
            business_intent=0.9,
            trend_score=0.6,
            competition_score=0.4,
            differentiation_score=0.8,
            brand_alignment_score=0.8,
            value_score=0.82,
        )

        titles = optimizer.generate_optimized_titles_sync(
            topic,
            count=5,
            catalog_context={
                "page_type": "wholesale_faq",
                "decision_questions": [
                    "What MOQ and lead time should buyers compare?",
                    "Which supplier questions should buyers ask before sampling?",
                ],
            },
        )

        rendered_titles = [title.title for title in titles]

        assert len(set(rendered_titles)) >= 3
        assert all(len(title) <= 68 for title in rendered_titles)
        assert all(not title.lower().endswith((" and", " or", " for", " to", " with")) for title in rendered_titles)
        assert any("buyer questions" in title.lower() for title in rendered_titles)
        assert any("buying risks" in title.lower() or "supplier risks" in title.lower() for title in rendered_titles)

    def test_traffic_entry_lane_avoids_procurement_template_tails(self):
        optimizer = HookOptimizer()

        topic = ContentTopic(
            title="glass vs pet dropper bottle for serum",
            angle="material comparison for serum packaging",
            hook_type=HookType.DATA,
            industry="packaging",
            target_audience="b2b buyers",
            business_intent=0.72,
            trend_score=0.6,
            competition_score=0.45,
            differentiation_score=0.75,
            brand_alignment_score=0.8,
            value_score=0.77,
        )

        titles = optimizer.generate_optimized_titles_sync(
            topic,
            count=5,
            catalog_context={
                "page_type": "spec_comparison",
                "content_lane": "traffic_entry",
                "search_stage": "consideration",
                "target_category_name": "Dropper Bottles",
            },
        )

        rendered_titles = [title.title.lower() for title in titles]
        assert any("tradeoff" in title or "fit" in title or "selection" in title for title in rendered_titles)
        assert all("buyer checks" not in title for title in rendered_titles)
        assert all("moq, lead time" not in title for title in rendered_titles)
